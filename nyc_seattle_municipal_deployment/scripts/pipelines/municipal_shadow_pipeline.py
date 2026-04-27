#!/usr/bin/env python3
# ABOUTME: Shadow analysis pipeline for NYC & Seattle municipal boundaries only
# ABOUTME: Download → Analyze → Delete pattern for storage efficiency

import sys
import asyncio
import aiohttp
import pandas as pd
from pathlib import Path
import time
from datetime import datetime
import logging
import argparse
import shutil

# Import pipeline components
sys.path.insert(0, str(Path(__file__).parent))
from sunny_shade_pipeline import SunnyShadePipeline

# Configuration
BATCH_SIZE = 500  # Images per batch
DOWNLOAD_WORKERS = 50  # Concurrent downloads
ANALYSIS_BATCH_SIZE = 32  # GPU batch size
CHECKPOINT_INTERVAL = 1000  # Save checkpoint every N images
DELETE_AFTER_PROCESSING = True  # CRITICAL: Delete images after analysis
MAX_DOWNLOAD_RETRIES = 5
MAPILLARY_TOKEN = 'MLY|9798203303595429|e2d4e749e96af419787ec1ca33019e3f'

# Cities configuration
CITIES = {
    'new-york-city': {
        'metadata_file': 'data/metadata/new-york-city_svi_municipal_only.csv',
        'display_name': 'New York City'
    },
    'seattle': {
        'metadata_file': 'data/metadata/seattle_svi_municipal_only.csv',
        'display_name': 'Seattle'
    }
}


def setup_logging(output_dir):
    """Set up logging for the pipeline."""
    log_file = output_dir / f"municipal_shadow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

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


async def download_image_async(session, image_id, output_path, token, max_retries=MAX_DOWNLOAD_RETRIES):
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


async def download_batch_async(image_ids, output_dir, token, max_concurrent=DOWNLOAD_WORKERS):
    """Download a batch of images concurrently."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    connector = aiohttp.TCPConnector(limit=max_concurrent, limit_per_host=50)
    timeout = aiohttp.ClientTimeout(total=300)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks = []
        for img_id in image_ids:
            output_path = output_dir / f"{img_id}.jpg"
            if not output_path.exists():
                task = download_image_async(session, img_id, output_path, token)
                tasks.append(task)
            else:
                tasks.append(asyncio.sleep(0, result=(True, "Already exists")))

        results = await asyncio.gather(*tasks)

    successful = sum(1 for success, _ in results if success)
    failed = len(results) - successful

    return successful, failed


def process_city_batch(city_name, metadata_df, batch_start, batch_size, output_dir,
                      pipeline, token, logger):
    """Process a batch of images for a city.

    Uses download → analyze → delete pattern to minimize storage.
    """
    batch_end = min(batch_start + batch_size, len(metadata_df))
    batch_df = metadata_df.iloc[batch_start:batch_end]

    # Create temp directory for THIS BATCH ONLY
    temp_dir = output_dir / city_name / f"temp_batch_{batch_start}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 1. Download batch
        logger.info(f"  Downloading batch {batch_start//batch_size + 1}: {len(batch_df)} images...")
        successful, failed = asyncio.run(
            download_batch_async(batch_df['id'].tolist(), temp_dir, token)
        )

        if successful == 0:
            logger.warning(f"  No images downloaded for batch {batch_start//batch_size + 1}")
            return []

        # 2. Process with pipeline (ViT + YOLO)
        logger.info(f"  Processing {successful} images...")
        results_df = pipeline.process_folder_batch(temp_dir)

        # 3. Merge with metadata
        results_list = []
        for _, row_result in results_df.iterrows():
            img_id = str(row_result['image_id'])
            row = batch_df[batch_df['id'] == int(img_id)]
            if not row.empty:
                result_dict = row_result.to_dict()
                result_dict['lat'] = row.iloc[0]['lat']
                result_dict['lon'] = row.iloc[0]['lon']
                result_dict['captured_at'] = row.iloc[0]['captured_at']
                result_dict['compass_angle'] = row.iloc[0].get('compass_angle', None)
                result_dict['sequence_id'] = row.iloc[0].get('sequence_id', None)
                result_dict['is_pano'] = row.iloc[0].get('is_pano', False)
                results_list.append(result_dict)

        return results_list

    finally:
        # 4. CRITICAL: Clean up temp directory IMMEDIATELY
        # This deletes ~1GB of images after each batch
        if DELETE_AFTER_PROCESSING and temp_dir.exists():
            shutil.rmtree(temp_dir)
            logger.debug(f"  Cleaned up {temp_dir}")


def process_city(city_name, metadata_path, output_dir, pipeline, token, logger):
    """Process all images for a city using municipal-only metadata."""
    logger.info(f"\n{'='*70}")
    logger.info(f"Processing {CITIES[city_name]['display_name']}")
    logger.info(f"{'='*70}")

    # Load metadata
    metadata_df = pd.read_csv(metadata_path)
    total_images = len(metadata_df)
    logger.info(f"Municipal images: {total_images:,}")

    # Check for existing results
    output_file = output_dir / city_name / f"{city_name}_shadow_annotated.csv"
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

        # Save incrementally (checkpoint)
        if batch_results:
            batch_df = pd.DataFrame(batch_results)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            if output_file.exists():
                batch_df.to_csv(output_file, mode='a', header=False, index=False)
            else:
                batch_df.to_csv(output_file, index=False)

            logger.info(f"  Saved {len(batch_results)} results to {output_file.name}")

        # Progress update
        elapsed = time.time() - start_time
        rate = len(all_results) / elapsed if elapsed > 0 else 0
        pct = ((batch_idx + 1) / num_batches) * 100
        logger.info(f"  Progress: {pct:.1f}% ({len(all_results):,} images at {rate:.2f} img/sec)")

    elapsed = time.time() - start_time
    rate = len(all_results) / elapsed if elapsed > 0 else 0

    logger.info(f"\nCompleted {city_name}: {len(all_results):,} images in {elapsed/60:.1f} minutes ({rate:.2f} img/sec)")


def main():
    parser = argparse.ArgumentParser(description='NYC & Seattle Municipal Shadow Analysis Pipeline')
    parser.add_argument('--output-dir', default='outputs',
                       help='Output directory for results')
    parser.add_argument('--cities', nargs='+', choices=list(CITIES.keys()),
                       help='Specific cities to process (default: all)')
    parser.add_argument('--resume', action='store_true',
                       help='Resume from existing checkpoint')

    args = parser.parse_args()

    # Resolve paths
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent.parent
    output_dir = base_dir / args.output_dir

    # Setup
    output_dir.mkdir(parents=True, exist_ok=True)
    logger = setup_logging(base_dir / 'logs')

    logger.info("="*70)
    logger.info("NYC & SEATTLE MUNICIPAL SHADOW ANALYSIS PIPELINE")
    logger.info("Municipal boundaries only (73.9% size reduction)")
    logger.info("="*70)
    logger.info(f"Storage mode: {'Delete after processing' if DELETE_AFTER_PROCESSING else 'Keep all images'}")
    logger.info("")

    # Initialize pipeline
    vit_model_path = base_dir / "models" / "vit_binary.pth"
    yolo_model_path = base_dir / "models" / "yolo_best.pt"

    logger.info(f"Loading models...")
    logger.info(f"  ViT: {vit_model_path}")
    logger.info(f"  YOLO: {yolo_model_path}")

    try:
        pipeline = SunnyShadePipeline(
            vit_model_path=str(vit_model_path),
            yolo_model_path=str(yolo_model_path)
        )
        logger.info("✓ Models loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load models: {e}")
        return 1

    # Process cities
    cities_to_process = args.cities if args.cities else list(CITIES.keys())

    for city_key in cities_to_process:
        config = CITIES[city_key]
        metadata_path = base_dir / config['metadata_file']

        if not metadata_path.exists():
            logger.warning(f"Skipping {city_key} - metadata not found: {metadata_path}")
            continue

        try:
            process_city(city_key, metadata_path, output_dir, pipeline, MAPILLARY_TOKEN, logger)
        except Exception as e:
            logger.error(f"Error processing {city_key}: {e}")
            import traceback
            traceback.print_exc()

    logger.info("\n" + "="*70)
    logger.info("Pipeline complete!")
    logger.info("="*70)

    return 0


if __name__ == '__main__':
    sys.exit(main())
