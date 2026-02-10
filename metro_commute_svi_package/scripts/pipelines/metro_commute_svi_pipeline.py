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
        results_df = pipeline.process_folder_batch(temp_dir)

        # Add metadata columns
        results_list = []
        for _, row_result in results_df.iterrows():
            img_id = str(row_result['image_id'])
            row = batch_df[batch_df['id'] == int(img_id)]
            if not row.empty:
                result_dict = row_result.to_dict()
                result_dict['lat'] = row.iloc[0]['lat']
                result_dict['lon'] = row.iloc[0]['lon']
                result_dict['captured_at'] = row.iloc[0]['captured_at']
                results_list.append(result_dict)

        return results_list

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

    # Sort by image count (smallest first) for faster initial results
    city_sizes = []
    for f in city_metadata_files:
        df = pd.read_csv(f)
        city_sizes.append((f, len(df)))

    city_metadata_files = [f for f, _ in sorted(city_sizes, key=lambda x: x[1])]

    logger.info(f"\nFound {len(city_metadata_files)} cities to process")
    logger.info("Processing order: smallest to largest (for faster initial results)\n")

    # Process each city
    for metadata_file in city_metadata_files:
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
