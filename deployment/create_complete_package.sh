#!/bin/bash
# ABOUTME: Creates complete deployment package with data, scripts, models for SVI analysis
# ABOUTME: Includes everything needed to download images and run sunny/shade pipeline on remote server

set -e

# Parse command line arguments
CONFIG_FILE=""
OUTPUT_NAME=""
INCLUDE_MODELS=true

usage() {
    echo "Usage: $0 -c CONFIG_FILE [-o OUTPUT_NAME] [--no-models]"
    echo ""
    echo "Arguments:"
    echo "  -c CONFIG_FILE    YAML config file (e.g., config/phoenix_az.yaml)"
    echo "  -o OUTPUT_NAME    Optional output name (default: derived from config)"
    echo "  --no-models       Skip model weights (reduces package size)"
    echo ""
    echo "Examples:"
    echo "  $0 -c config/phoenix_az.yaml"
    echo "  $0 -c config/phoenix_az.yaml -o phoenix_complete"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -c) CONFIG_FILE="$2"; shift 2 ;;
        -o) OUTPUT_NAME="$2"; shift 2 ;;
        --no-models) INCLUDE_MODELS=false; shift ;;
        -h|--help) usage ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

if [ -z "$CONFIG_FILE" ]; then
    echo "Error: Config file is required"
    usage
fi

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Config file not found: $CONFIG_FILE"
    exit 1
fi

# Set base directory
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BASE_DIR"

# Derive output name from config if not specified
if [ -z "$OUTPUT_NAME" ]; then
    OUTPUT_NAME=$(basename "$CONFIG_FILE" .yaml)
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PACKAGE_DIR="$BASE_DIR/svi_complete_package_${OUTPUT_NAME}"
OUTPUT_TAR="svi_complete_${OUTPUT_NAME}_${TIMESTAMP}.tar.gz"

echo "========================================"
echo "Complete SVI Analysis Package Creator"
echo "========================================"
echo "Config: $CONFIG_FILE"
echo "Output: $OUTPUT_NAME"
echo "Include models: $INCLUDE_MODELS"
echo ""

# Step 1: Check if filtered data exists, if not, fetch it
OUTPUT_DIR_FROM_CONFIG=$(grep "output_dir:" "$CONFIG_FILE" | awk '{print $2}' | tr -d "'\"")
if [ -z "$OUTPUT_DIR_FROM_CONFIG" ]; then
    OUTPUT_DIR_FROM_CONFIG="data/raw/svi_filtered"
fi

if [ ! -d "$OUTPUT_DIR_FROM_CONFIG" ] || [ -z "$(ls -A "$OUTPUT_DIR_FROM_CONFIG" 2>/dev/null)" ]; then
    echo "Step 1: Fetching filtered SVI metadata..."
    echo "----------------------------------------"
    source .venv/bin/activate 2>/dev/null || source venv/bin/activate 2>/dev/null || true
    python3 scripts/data_collection/fetch_svi_with_time_filter.py "$CONFIG_FILE"
    echo ""
else
    echo "Step 1: Using existing filtered data in $OUTPUT_DIR_FROM_CONFIG"
    echo ""
fi

# Step 2: Create package directory structure
echo "Step 2: Creating package directory structure..."
echo "----------------------------------------"

# Clean up old package directory if it exists
if [ -d "$PACKAGE_DIR" ]; then
    echo "Cleaning up old package directory..."
    rm -rf "$PACKAGE_DIR"
fi

mkdir -p "$PACKAGE_DIR/data"
mkdir -p "$PACKAGE_DIR/config"
mkdir -p "$PACKAGE_DIR/scripts"
mkdir -p "$PACKAGE_DIR/models"

# Step 3: Copy filtered data
echo "Step 3: Copying filtered data..."
cp -r "$OUTPUT_DIR_FROM_CONFIG"/* "$PACKAGE_DIR/data/" 2>/dev/null || echo "Warning: No data files found"

# Step 4: Copy configuration
echo "Step 4: Copying configuration..."
cp "$CONFIG_FILE" "$PACKAGE_DIR/config/"

# Extract Mapillary token from config for later use
MAPILLARY_TOKEN=$(grep "mapillary_token:" "$CONFIG_FILE" | awk '{print $2}' | tr -d "'\"")

# Step 5: Copy scripts
echo "Step 5: Copying analysis scripts..."
cp scripts/data_collection/download_images_from_csv.py "$PACKAGE_DIR/scripts/"
cp scripts/pipelines/sunny_shade_pipeline.py "$PACKAGE_DIR/scripts/" 2>/dev/null || echo "Warning: sunny_shade_pipeline.py not found"

# Step 6: Copy model weights if requested
if [ "$INCLUDE_MODELS" = true ]; then
    echo "Step 6: Copying model weights..."

    # Copy ViT model
    if [ -f "outputs/models/vit_binary.pth" ]; then
        echo "  - ViT binary classification model"
        cp "outputs/models/vit_binary.pth" "$PACKAGE_DIR/models/"
    else
        echo "  Warning: vit_binary.pth not found"
    fi

    # Copy YOLO model (use train4 as default)
    if [ -f "outputs/models/sunny_batch_train4/weights/best.pt" ]; then
        echo "  - YOLO shade detection model (train4)"
        cp "outputs/models/sunny_batch_train4/weights/best.pt" "$PACKAGE_DIR/models/yolo_best.pt"
    elif [ -f "outputs/models/sunny_batch_train6/weights/best.pt" ]; then
        echo "  - YOLO shade detection model (train6)"
        cp "outputs/models/sunny_batch_train6/weights/best.pt" "$PACKAGE_DIR/models/yolo_best.pt"
    else
        echo "  Warning: YOLO model weights not found"
    fi
else
    echo "Step 6: Skipping model weights (--no-models specified)"
fi

# Step 7: Create requirements.txt
echo "Step 7: Creating requirements.txt..."
cat > "$PACKAGE_DIR/requirements.txt" << 'EOF'
# Core dependencies
torch>=2.0.0
torchvision>=0.15.0
ultralytics>=8.0.0
pandas>=2.0.0
geopandas>=0.13.0
Pillow>=10.0.0
tqdm>=4.65.0
pyyaml>=6.0
mapillary>=1.0.0
timezonefinder>=6.0.0
requests>=2.31.0
mpmath>=1.3.0

# Optional but recommended
numpy>=1.24.0
matplotlib>=3.7.0
EOF

# Step 8: Create run scripts
echo "Step 8: Creating execution scripts..."

# Script 1: Download images
cat > "$PACKAGE_DIR/1_download_images.sh" << EOF
#!/bin/bash
# Download street view images from filtered metadata

set -e

echo "========================================"
echo "Downloading Street View Images"
echo "========================================"
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Set Mapillary token
export MAPILLARY_TOKEN="$MAPILLARY_TOKEN"

# Download images for each CSV file
for csv_file in data/*.csv; do
    if [ -f "\$csv_file" ]; then
        city_name=\$(basename "\$csv_file" .csv)
        output_dir="data/\${city_name}_images"

        echo "Processing: \$csv_file"
        echo "Output: \$output_dir"
        echo ""

        python3 scripts/download_images_from_csv.py \\
            --input "\$csv_file" \\
            --output "\$output_dir" \\
            --mapillary-token "\$MAPILLARY_TOKEN"

        echo ""
    fi
done

echo "========================================"
echo "Download Complete!"
echo "========================================"
EOF

# Script 2: Run sunny/shade analysis
cat > "$PACKAGE_DIR/2_run_analysis.sh" << 'EOF'
#!/bin/bash
# Run sunny/shade analysis pipeline on downloaded images

set -e

echo "========================================"
echo "Running Sunny/Shade Analysis Pipeline"
echo "========================================"
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Check if models exist
if [ ! -f "models/vit_binary.pth" ]; then
    echo "Error: ViT model not found at models/vit_binary.pth"
    exit 1
fi

if [ ! -f "models/yolo_best.pt" ]; then
    echo "Error: YOLO model not found at models/yolo_best.pt"
    exit 1
fi

# Run analysis for each image directory
for image_dir in data/*_images; do
    if [ -d "$image_dir" ]; then
        city_name=$(basename "$image_dir" _images)
        output_csv="data/${city_name}_analyzed.csv"

        echo "Analyzing: $image_dir"
        echo "Output: $output_csv"
        echo ""

        python3 scripts/sunny_shade_pipeline.py \
            "$image_dir" \
            --output "$output_csv" \
            --vit-model models/vit_binary.pth \
            --yolo-model models/yolo_best.pt

        echo ""

        # Merge with original metadata if CSV exists
        csv_file="data/${city_name}.csv"
        if [ -f "$csv_file" ]; then
            echo "Merging with original metadata..."
            python3 -c "
import pandas as pd
import sys

try:
    # Read original metadata
    orig = pd.read_csv('$csv_file')

    # Read analysis results
    results = pd.read_csv('$output_csv')

    # Merge on image ID
    # The results use 'image_id', original uses 'id'
    merged = orig.merge(results, left_on='id', right_on='image_id', how='left')

    # Drop duplicate image_id column
    if 'image_id' in merged.columns:
        merged = merged.drop(columns=['image_id'])

    # Save merged results
    merged.to_csv('$output_csv', index=False)
    print(f'Merged {len(merged)} rows to $output_csv')
except Exception as e:
    print(f'Warning: Could not merge metadata: {e}')
    print('Analysis results saved without metadata merge')
"
            echo ""
        fi
    fi
done

echo "========================================"
echo "Analysis Complete!"
echo "========================================"
echo ""
echo "Results saved to data/*_analyzed.csv"
echo "Each file contains:"
echo "  - Original metadata (location, datetime, etc.)"
echo "  - Sunny classification (is_sunny, sunny_probability)"
echo "  - Shade detection (person_count, inshade_count, outshade_count)"
echo ""
EOF

# Script 3: Setup environment
cat > "$PACKAGE_DIR/setup.sh" << 'EOF'
#!/bin/bash
# Setup Python environment for SVI analysis

set -e

echo "========================================"
echo "Setting Up SVI Analysis Environment"
echo "========================================"
echo ""

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "Installing requirements..."
pip install -r requirements.txt

echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "To activate the environment:"
echo "  source venv/bin/activate"
echo ""
echo "To download images:"
echo "  bash 1_download_images.sh"
echo ""
echo "To run analysis:"
echo "  bash 2_run_analysis.sh"
echo ""
EOF

chmod +x "$PACKAGE_DIR/setup.sh"
chmod +x "$PACKAGE_DIR/1_download_images.sh"
chmod +x "$PACKAGE_DIR/2_run_analysis.sh"

# Step 9: Create README
echo "Step 9: Creating README..."
cat > "$PACKAGE_DIR/README.md" << 'EOF'
# Complete SVI Analysis Package

This package contains everything needed to download and analyze street view images.

## Contents

- `data/`: Filtered CSV files with SVI metadata
- `config/`: Configuration files
- `scripts/`: Analysis scripts
- `models/`: Trained model weights (ViT + YOLO)
- `requirements.txt`: Python dependencies
- `setup.sh`: Environment setup script
- `1_download_images.sh`: Image download script
- `2_run_analysis.sh`: Analysis pipeline script

## Quick Start

### 1. Setup Environment

```bash
bash setup.sh
```

This creates a virtual environment and installs all dependencies.

### 2. Download Images

```bash
bash 1_download_images.sh
```

Downloads actual street view images from Mapillary/KartaView based on the filtered metadata.

### 3. Run Analysis

```bash
bash 2_run_analysis.sh
```

Runs the sunny/shade classification and people detection pipeline on all downloaded images.

## Output

After running the analysis, you'll have:
- `data/CityName_images/`: Downloaded JPEG images
- `data/CityName_analyzed.csv`: Results with sunny classification and shade detection

## Requirements

- Python 3.8+
- CUDA-capable GPU (recommended for faster processing)
- ~2GB disk space for models
- Sufficient disk space for images (varies by city)

## Metadata Columns

Input CSV contains:
- Location: `lat`, `lon`, `city_id`
- Datetime: `datetime_utc`, `datetime_local` (8-10am or 4-6pm local time)
- Image IDs: `id`, `sequence_id`
- Source: `Mapillary` or `KartaView`

Output CSV adds:
- `is_sunny`: Boolean sunny classification
- `sunny_probability`: Model confidence (0-1)
- `person_count`: Number of people detected
- `inshade_count`: People in shade
- `outshade_count`: People out of shade

## Manual Usage

If you prefer to run components separately:

```bash
source venv/bin/activate

# Download images
python3 scripts/download_images_from_csv.py \
    --input data/CityName.csv \
    --output data/CityName_images

# Run analysis
python3 scripts/sunny_shade_pipeline.py \
    data/CityName_images \
    --output data/CityName_analyzed.csv \
    --vit-model models/vit_binary.pth \
    --yolo-model models/yolo_best.pt
```

## Troubleshooting

- **No GPU**: Analysis will run on CPU (slower but functional)
- **Out of memory**: Reduce batch size in pipeline script
- **Download failures**: Check Mapillary token in `1_download_images.sh`

EOF

# Step 10: Create manifest
echo "Step 10: Creating manifest..."
CSV_COUNT=$(find "$PACKAGE_DIR/data" -name "*.csv" | wc -l)
CSV_FILES=$(find "$PACKAGE_DIR/data" -name "*.csv" -exec basename {} \; | sort)

cat > "$PACKAGE_DIR/MANIFEST.txt" << EOF
Package: Complete SVI Analysis Package - $OUTPUT_NAME
Created: $(date)
Config: $(basename "$CONFIG_FILE")

Contents:
$CSV_FILES

Statistics:
- CSV files: $CSV_COUNT
- Models included: $INCLUDE_MODELS

Package includes:
- Filtered SVI metadata (CSVs)
- Image download script
- Sunny/shade analysis pipeline
$(if [ "$INCLUDE_MODELS" = true ]; then echo "- Trained model weights (ViT + YOLO)"; fi)
- Setup and execution scripts
- Complete documentation

Ready for deployment to GPU server.
EOF

# Step 11: Create tarball
echo "Step 11: Creating tarball..."
tar -czf "$OUTPUT_TAR" -C "$BASE_DIR" "$(basename "$PACKAGE_DIR")"

# Step 12: Calculate sizes
TARBALL_SIZE=$(du -h "$OUTPUT_TAR" | cut -f1)
PACKAGE_SIZE=$(du -sh "$PACKAGE_DIR" | cut -f1)

# Clean up package directory
echo "Step 12: Cleaning up..."
rm -rf "$PACKAGE_DIR"

# Show results
echo ""
echo "========================================"
echo "Package Created Successfully!"
echo "========================================"
echo ""
echo "Output file: $BASE_DIR/$OUTPUT_TAR"
echo "Compressed size: $TARBALL_SIZE"
echo "Uncompressed size: $PACKAGE_SIZE"
echo ""
echo "Contents preview:"
tar -tzf "$BASE_DIR/$OUTPUT_TAR" | head -25
echo ""
echo "To deploy on GPU server:"
echo "  1. Transfer: scp $OUTPUT_TAR user@server:~/"
echo "  2. Extract: tar -xzf $(basename "$OUTPUT_TAR")"
echo "  3. cd $(basename "$PACKAGE_DIR")"
echo "  4. Setup: bash setup.sh"
echo "  5. Download: bash 1_download_images.sh"
echo "  6. Analyze: bash 2_run_analysis.sh"
echo ""
