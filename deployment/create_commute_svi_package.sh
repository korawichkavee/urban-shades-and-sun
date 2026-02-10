#!/bin/bash
# ABOUTME: Creates deployment package for commute-time metro SVI analysis (8-10am, 4-6pm local time)
# ABOUTME: Includes pre-filtered metadata to skip metadata fetching phase

set -e

echo "========================================"
echo "Creating Commute-Time Metro SVI Package"
echo "Filtered for: 8-10am & 4-6pm local time"
echo "========================================"
echo ""

# Set base directory
BASE_DIR="/home/kieran/Documents/Python/sunny_day_SVI"
DEPLOY_DIR="$BASE_DIR/deployment"
PACKAGE_DIR="$BASE_DIR/metro_commute_svi_package"
OUTPUT_TAR="metro_commute_svi_pipeline_$(date +%Y%m%d_%H%M%S).tar.gz"

# Clean up old package directory if it exists
if [ -d "$PACKAGE_DIR" ]; then
    echo "Cleaning up old package directory..."
    rm -rf "$PACKAGE_DIR"
fi

# Create package directory structure
echo "Creating package directory structure..."
mkdir -p "$PACKAGE_DIR/scripts/pipelines"
mkdir -p "$PACKAGE_DIR/scripts/data_collection"
mkdir -p "$PACKAGE_DIR/models"
mkdir -p "$PACKAGE_DIR/data/metro_cities_metadata"
mkdir -p "$PACKAGE_DIR/logs"
mkdir -p "$PACKAGE_DIR/outputs"

# Copy pipeline scripts
echo "Copying pipeline scripts..."
cp "$BASE_DIR/scripts/pipelines/sunny_shade_pipeline.py" "$PACKAGE_DIR/scripts/pipelines/"

# Copy data collection scripts
echo "Copying data collection scripts..."
cp "$BASE_DIR/scripts/data_collection/download_mly_points.py" "$PACKAGE_DIR/scripts/data_collection/"

# Copy model weights
echo "Copying ViT model weights..."
VIT_MODEL=""
if [ -f "$BASE_DIR/outputs/models/vit_binary.pth" ]; then
    cp "$BASE_DIR/outputs/models/vit_binary.pth" "$PACKAGE_DIR/models/"
    VIT_MODEL="outputs/models/vit_binary.pth"
elif [ -f "$BASE_DIR/vit_binary.pth" ]; then
    cp "$BASE_DIR/vit_binary.pth" "$PACKAGE_DIR/models/"
    VIT_MODEL="vit_binary.pth"
else
    echo "Error: vit_binary.pth not found!"
    echo "       This model is required for sunny/cloudy classification"
    exit 1
fi

echo "Copying YOLO model weights..."
if [ ! -f "$BASE_DIR/outputs/models/sunny_batch_train4/weights/best.pt" ]; then
    echo "Error: YOLO model weights not found at outputs/models/sunny_batch_train4/weights/best.pt!"
    exit 1
fi
cp "$BASE_DIR/outputs/models/sunny_batch_train4/weights/best.pt" "$PACKAGE_DIR/models/yolo_best.pt"

# Copy pre-filtered commute-time metadata
echo "Copying pre-filtered commute-time metadata..."
METADATA_DIR="$BASE_DIR/data/metro_cities_svi_commute"
if [ ! -d "$METADATA_DIR" ]; then
    echo "Error: Filtered metadata directory not found at $METADATA_DIR"
    echo "       Run generate_commute_filtered_metadata.py first!"
    exit 1
fi

# Copy all filtered metadata CSVs
CITY_COUNT=0
for city_dir in "$METADATA_DIR"/*; do
    if [ -d "$city_dir" ]; then
        city_name=$(basename "$city_dir")
        metadata_file="$city_dir/${city_name}_metadata_commute.csv"
        if [ -f "$metadata_file" ]; then
            mkdir -p "$PACKAGE_DIR/data/metro_cities_metadata/$city_name"
            cp "$metadata_file" "$PACKAGE_DIR/data/metro_cities_metadata/$city_name/"
            CITY_COUNT=$((CITY_COUNT + 1))
        else
            echo "Warning: Metadata file not found for $city_name"
        fi
    fi
done

echo "  Copied metadata for $CITY_COUNT cities"

# Create requirements.txt
echo "Creating requirements.txt..."
cat > "$PACKAGE_DIR/requirements.txt" << 'EOF'
# Core ML
torch>=2.0.0
torchvision>=0.15.0
ultralytics>=8.0.0

# Image processing
Pillow>=9.0.0
opencv-python>=4.7.0

# Data processing
pandas>=1.5.0
numpy>=1.24.0

# Mapillary API
mapillary>=1.0.0
aiohttp>=3.8.0

# Progress bars
tqdm>=4.65.0

# Geospatial (for city boundary filtering - optional)
geopandas>=0.12.0
shapely>=2.0.0

# Timezone support
pytz>=2023.0
EOF

# Create simplified pipeline script that uses pre-filtered metadata
echo "Creating commute-time pipeline script..."
cat > "$PACKAGE_DIR/scripts/pipelines/metro_commute_svi_pipeline.py" << 'EOFPYTHON'
#!/usr/bin/env python3
# ABOUTME: SVI analysis pipeline for metro cities - COMMUTE TIME ONLY (8-10am, 4-6pm local)
# ABOUTME: Uses pre-filtered metadata to analyze only commute-hour street view imagery

import sys
import asyncio
import aiohttp
import pandas as pd
from pathlib import Path
import time
from datetime import datetime
import logging
import argparse
from concurrent.futures import ThreadPoolExecutor
import shutil

# Import existing pipeline components
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'data_collection'))

from sunny_shade_pipeline import SunnyShadePipeline

BATCH_SIZE = 256
MAPILLARY_TOKEN = 'MLY|9798203303595429|e2d4e749e96af419787ec1ca33019e3f'


def setup_logging(output_dir):
    """Set up logging for the pipeline."""
    log_file = output_dir / f"commute_svi_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

    return logging.getLogger(__name__)


async def download_image_async(session, image_id, output_path, token, max_retries=3):
    """Download a single image asynchronously with rate limit handling."""
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            metadata_url = f"https://graph.mapillary.com/{image_id}?fields=thumb_2048_url&access_token={token}"
            async with session.get(metadata_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 429:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    return False, "Rate limit exceeded (429)"

                if response.status != 200:
                    return False, f"Metadata HTTP {response.status}"

                metadata = await response.json()
                if 'thumb_2048_url' not in metadata:
                    return False, "No thumb_2048_url in metadata"
                image_url = metadata['thumb_2048_url']

            async with session.get(image_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 429:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    return False, "Rate limit on download (429)"

                if response.status == 200:
                    content = await response.read()
                    output_path.write_bytes(content)
                    return True, None
                else:
                    return False, f"Download HTTP {response.status}"

        except asyncio.TimeoutError:
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
                continue
            return False, "Timeout"
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
                continue
            return False, str(e)

    return False, "Max retries exceeded"


async def download_batch_async(image_ids, output_dir, token, max_concurrent=100):
    """Download a batch of images concurrently."""
    output_dir.mkdir(parents=True, exist_ok=True)

    connector = aiohttp.TCPConnector(limit=max_concurrent, limit_per_host=50)
    timeout = aiohttp.ClientTimeout(total=300)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks = []
        for img_id in image_ids:
            output_path = output_dir / f"{img_id}.jpg"
            if not output_path.exists():
                tasks.append(download_image_async(session, img_id, output_path, token))
            else:
                tasks.append(asyncio.coroutine(lambda: (True, "Already exists"))())

        results = await asyncio.gather(*tasks)

    successful = sum(1 for success, _ in results if success)
    failed = len(results) - successful

    return successful, failed


def process_city_batch(city_name, metadata_df, batch_start, batch_size, output_dir,
                      pipeline, token, logger):
    """Process a batch of images for a city."""
    batch_end = min(batch_start + batch_size, len(metadata_df))
    batch_df = metadata_df.iloc[batch_start:batch_end]

    temp_dir = output_dir / city_name / f"temp_batch_{batch_start}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Download batch
        logger.info(f"  Downloading batch {batch_start//batch_size + 1}: {len(batch_df)} images...")
        successful, failed = asyncio.run(
            download_batch_async(batch_df['id'].tolist(), temp_dir, token)
        )

        if successful == 0:
            logger.warning(f"  No images downloaded for batch {batch_start//batch_size + 1}")
            return []

        # Process with pipeline
        logger.info(f"  Processing {successful} images...")
        results = pipeline.process_folder_batch(temp_dir)

        # Add metadata columns
        for result in results:
            img_id = Path(result['image_path']).stem
            row = batch_df[batch_df['id'] == int(img_id)]
            if not row.empty:
                result['lat'] = row.iloc[0]['lat']
                result['lon'] = row.iloc[0]['lon']
                result['captured_at'] = row.iloc[0]['captured_at']

        return results

    finally:
        # Clean up temp directory
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


def process_city(city_name, metadata_path, output_dir, pipeline, token, logger):
    """Process all images for a city using pre-filtered metadata."""
    logger.info(f"\n{'='*70}")
    logger.info(f"Processing {city_name.upper()}")
    logger.info(f"{'='*70}")

    # Load pre-filtered metadata
    metadata_df = pd.read_csv(metadata_path)
    total_images = len(metadata_df)
    logger.info(f"Pre-filtered commute-time images: {total_images:,}")

    # Check for existing results
    output_file = output_dir / city_name / f"{city_name}_svi_analyzed.csv"
    processed_ids = set()

    if output_file.exists():
        existing_df = pd.read_csv(output_file)
        processed_ids = set(existing_df['image_id'].astype(str))
        logger.info(f"Already processed: {len(processed_ids):,} images")

    # Filter to unprocessed images
    metadata_df = metadata_df[~metadata_df['id'].astype(str).isin(processed_ids)]

    if len(metadata_df) == 0:
        logger.info(f"All images already processed for {city_name}")
        return

    logger.info(f"Remaining to process: {len(metadata_df):,} images")

    # Process in batches
    all_results = []
    num_batches = (len(metadata_df) + BATCH_SIZE - 1) // BATCH_SIZE
    start_time = time.time()

    for batch_idx in range(num_batches):
        batch_start = batch_idx * BATCH_SIZE
        logger.info(f"\nBatch {batch_idx + 1}/{num_batches}")

        batch_results = process_city_batch(
            city_name, metadata_df, batch_start, BATCH_SIZE,
            output_dir, pipeline, token, logger
        )

        all_results.extend(batch_results)

        # Save incrementally
        if batch_results:
            batch_df = pd.DataFrame(batch_results)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            if output_file.exists():
                batch_df.to_csv(output_file, mode='a', header=False, index=False)
            else:
                batch_df.to_csv(output_file, index=False)

            logger.info(f"  Saved {len(batch_results)} results to {output_file.name}")

    elapsed = time.time() - start_time
    rate = len(all_results) / elapsed if elapsed > 0 else 0

    logger.info(f"\nCompleted {city_name}: {len(all_results):,} images in {elapsed/60:.1f} minutes ({rate:.2f} img/sec)")


def main():
    parser = argparse.ArgumentParser(description='Metro Commute-Time SVI Pipeline')
    parser.add_argument('--output-dir', default='outputs/metro_commute_svi',
                       help='Output directory for results')
    parser.add_argument('--metadata-dir', default='data/metro_cities_metadata',
                       help='Directory containing pre-filtered metadata CSVs')
    parser.add_argument('--cities', nargs='+',
                       help='Specific cities to process (default: all)')

    args = parser.parse_args()

    # Resolve paths
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent.parent
    output_dir = base_dir / args.output_dir
    metadata_dir = base_dir / args.metadata_dir

    # Setup
    output_dir.mkdir(parents=True, exist_ok=True)
    logger = setup_logging(output_dir)

    logger.info("="*70)
    logger.info("METRO COMMUTE-TIME SVI PIPELINE")
    logger.info("Filtered for: 8-10am & 4-6pm local time")
    logger.info("="*70)

    # Initialize pipeline
    vit_model_path = base_dir / "models" / "vit_binary.pth"
    yolo_model_path = base_dir / "models" / "yolo_best.pt"

    logger.info(f"Loading models...")
    logger.info(f"  ViT: {vit_model_path}")
    logger.info(f"  YOLO: {yolo_model_path}")

    pipeline = SunnyShadePipeline(
        vit_model_path=str(vit_model_path),
        yolo_model_path=str(yolo_model_path)
    )

    # Find cities
    city_metadata_files = list(metadata_dir.glob("*/*_metadata_commute.csv"))

    if args.cities:
        # Filter to requested cities
        requested = [c.lower() for c in args.cities]
        city_metadata_files = [
            f for f in city_metadata_files
            if f.parent.name.lower() in requested
        ]

    logger.info(f"\nFound {len(city_metadata_files)} cities to process")

    # Process each city
    for metadata_file in sorted(city_metadata_files):
        city_name = metadata_file.parent.name
        try:
            process_city(city_name, metadata_file, output_dir, pipeline, MAPILLARY_TOKEN, logger)
        except Exception as e:
            logger.error(f"Error processing {city_name}: {e}", exc_info=True)

    logger.info("\n" + "="*70)
    logger.info("PIPELINE COMPLETE")
    logger.info("="*70)


if __name__ == "__main__":
    main()
EOFPYTHON

chmod +x "$PACKAGE_DIR/scripts/pipelines/metro_commute_svi_pipeline.py"

# Create README
echo "Creating README..."
cat > "$PACKAGE_DIR/README.md" << 'EOFREADME'
# Metro Cities Commute-Time SVI Analysis Package

This package contains everything needed to analyze street view imagery during commute hours (8-10am and 4-6pm local time) for 19 US metro cities.

## What's Included

- **Pre-filtered Metadata**: 5.97M images filtered to commute hours only (27% of total)
- **ML Models**: Pre-trained ViT (sunny/cloudy) and YOLO (shade detection) models
- **Pipeline Script**: Automated processing pipeline
- **Dependencies**: Full requirements.txt

## Cities Included

19 US metro cities with travel survey data:
- Phoenix (1.84M commute-time images)
- Los Angeles (964K)
- Seattle (623K)
- Boston (443K)
- San Francisco (385K)
- And 14 more cities

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 2. Run Pipeline

Process all cities:
```bash
python scripts/pipelines/metro_commute_svi_pipeline.py
```

Process specific cities:
```bash
python scripts/pipelines/metro_commute_svi_pipeline.py --cities Boston Seattle
```

Custom output directory:
```bash
python scripts/pipelines/metro_commute_svi_pipeline.py --output-dir my_output
```

## Expected Performance

With RTX 4090 24GB GPU:
- **Conservative**: ~23 days (3 img/sec)
- **Typical**: ~17 days (4 img/sec)
- **Optimistic**: ~14 days (5 img/sec)

With 8GB GPU:
- **Typical**: ~46 days (1.5 img/sec)

CPU only (not recommended):
- ~346 days (0.2 img/sec)

## Output Format

Results are saved as CSV files per city:
- `{city}_svi_analyzed.csv`

Columns:
- `image_id`: Mapillary image ID
- `lat`, `lon`: Image coordinates
- `captured_at`: Timestamp
- `is_sunny`: Binary classification
- `has_shade`: Boolean
- `shade_percentage`: Float (0-100)
- `detection_count`: Number of shade objects detected

## Pre-Filtered Metadata Details

The metadata has been pre-filtered to include only images captured during:
- **Morning commute**: 8:00-10:00 local time
- **Evening commute**: 16:00-18:00 (4-6pm) local time

This reduces the dataset by ~73% while focusing on times when pedestrians are most active.

## System Requirements

**Minimum**:
- Python 3.8+
- 16GB RAM
- 100GB free disk space
- GPU with 8GB VRAM (or CPU mode)

**Recommended**:
- Python 3.10+
- 32GB+ RAM
- 200GB+ free disk space
- RTX 4090 24GB or similar GPU

## Troubleshooting

**Out of memory errors**:
- Reduce batch size in `sunny_shade_pipeline.py`
- Use smaller ViT/YOLO batch sizes (see METRO_SVI_OPTIMIZATIONS.md)

**Rate limiting**:
- Pipeline includes automatic retry with exponential backoff
- Max 100 concurrent downloads (configurable)

**Missing models**:
- Ensure `models/vit_binary.pth` and `models/yolo_best.pt` exist
- Re-extract the package if files are missing

## Citation

If you use this dataset/analysis in your research, please cite:
[Add your citation here]

## License

[Add license information]

## Support

For questions or issues, contact:
[Add contact information]
EOFREADME

# Create execution script
echo "Creating execution helper script..."
cat > "$PACKAGE_DIR/run_pipeline.sh" << 'EOFRUN'
#!/bin/bash
# Quick start script for running the pipeline

echo "Metro Commute-Time SVI Pipeline"
echo "================================"
echo ""
echo "This will process all 19 cities (~6M commute-time images)"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Run pipeline
python scripts/pipelines/metro_commute_svi_pipeline.py

echo ""
echo "Pipeline complete! Check outputs/metro_commute_svi/ for results."
EOFRUN

chmod +x "$PACKAGE_DIR/run_pipeline.sh"

# Create tarball
echo ""
echo "Creating tarball..."
cd "$BASE_DIR"
tar -czf "$DEPLOY_DIR/$OUTPUT_TAR" -C "$(dirname "$PACKAGE_DIR")" "$(basename "$PACKAGE_DIR")"

# Get size
TARBALL_SIZE=$(du -h "$DEPLOY_DIR/$OUTPUT_TAR" | cut -f1)

echo ""
echo "========================================"
echo "Package Created Successfully!"
echo "========================================"
echo ""
echo "Location: $DEPLOY_DIR/$OUTPUT_TAR"
echo "Size: $TARBALL_SIZE"
echo ""
echo "Contents:"
echo "  - Pre-filtered metadata for $CITY_COUNT cities"
echo "  - ViT sunny/cloudy model"
echo "  - YOLO shade detection model"
echo "  - Processing pipeline scripts"
echo "  - Complete requirements.txt"
echo ""
echo "To use:"
echo "  1. Extract: tar -xzf $OUTPUT_TAR"
echo "  2. Install: pip install -r metro_commute_svi_package/requirements.txt"
echo "  3. Run: cd metro_commute_svi_package && ./run_pipeline.sh"
echo ""
