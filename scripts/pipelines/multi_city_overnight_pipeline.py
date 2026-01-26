#!/usr/bin/env python3
# ABOUTME: Multi-city batched pipeline with async downloads - downloads, analyzes, cleans up sequentially
# ABOUTME: Designed for overnight runs with multiple cities in parallel

import sys
import asyncio
import aiohttp
import pandas as pd
from pathlib import Path
import mapillary.interface as mly
import time
from datetime import datetime
import logging
import json
import argparse
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import List, Dict, Tuple
import urllib.request
import shutil

# Import existing pipeline components
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'data_collection'))
sys.path.insert(0, str(Path(__file__).parent))

from sunny_shade_pipeline import SunnyShadePipeline
from download_mly_points import get_mly_gdf, save_csv


# Configuration
CITY_CONFIG = [
    {"name": "Madrid", "country": "ESP", "id": 1724616994},
    {"name": "Cape Town", "country": "ZAF", "id": 1710680650},
    {"name": "Istanbul", "country": "TUR", "id": 1792756324},
    {"name": "Osaka", "country": "JPN", "id": 1392419823},
    {"name": "Singapore", "country": "SGP", "id": 1702341327},
    {"name": "Buenos Aires", "country": "ARG", "id": 1032717330},
    {"name": "Mumbai", "country": "IND", "id": 1356226629},
]

MAX_CONCURRENT_CITIES = 3  # Number of cities to download images for in parallel
BATCH_SIZE = 100  # Process images in batches of this size
MAPILLARY_TOKEN = 'MLY|9798203303595429|e2d4e749e96af419787ec1ca33019e3f'


def setup_logging(output_dir):
    """Set up logging for the pipeline."""
    log_file = output_dir / f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

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


async def download_image_async(session, image_id, output_path, token):
    """Download a single image asynchronously."""
    try:
        # First get the image metadata with thumb_2048_url
        metadata_url = f"https://graph.mapillary.com/{image_id}?fields=thumb_2048_url&access_token={token}"
        async with session.get(metadata_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status != 200:
                return False, f"Metadata HTTP {response.status}"
            metadata = await response.json()
            if 'thumb_2048_url' not in metadata:
                return False, "No thumb_2048_url in metadata"
            image_url = metadata['thumb_2048_url']

        # Now download the actual image
        async with session.get(image_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status == 200:
                content = await response.read()
                output_path.write_bytes(content)
                return True, None
            else:
                return False, f"Image HTTP {response.status}"
    except Exception as e:
        return False, str(e)


async def download_images_batch_async(image_data_list, output_dir, logger, token):
    """Download a batch of images asynchronously.

    Args:
        image_data_list: List of (image_id, filename) tuples
        output_dir: Directory to save images
        logger: Logger instance
        token: Mapillary access token

    Returns:
        success_count, fail_count
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    success = 0
    failed = 0

    async with aiohttp.ClientSession() as session:
        tasks = []
        for image_id, filename in image_data_list:
            output_path = output_dir / filename
            if output_path.exists():
                success += 1  # Already downloaded
                continue

            task = download_image_async(session, image_id, output_path, token)
            tasks.append((image_id, task))

        # Execute downloads
        for image_id, task in tasks:
            is_success, error = await task
            if is_success:
                success += 1
            else:
                failed += 1
                if failed <= 5:  # Log first 5 errors
                    logger.debug(f"Failed to download {image_id}: {error}")

    return success, failed


def get_mapillary_image_url(image_id, size=2048):
    """Get Mapillary image download URL."""
    return f"https://graph.mapillary.com/{image_id}?fields=thumb_{size}_url"


def fetch_city_metadata(city_config, worldcities_csv, output_dir, logger):
    """Fetch metadata CSV for a city from Mapillary.

    Returns:
        Path to saved CSV or None if failed
    """
    logger.info(f"Fetching metadata for {city_config['name']}, {city_config['country']}")

    # Load worldcities database
    wc = pd.read_csv(worldcities_csv)
    city_row = wc[wc['id'] == city_config['id']].iloc[0]

    try:
        # Download metadata (no date restrictions)
        gdf = get_mly_gdf(city_row, start_date=None, end_date=None)

        if gdf is not None and not gdf.empty:
            # Save CSV
            csv_path = output_dir / f"{city_config['name'].replace(' ', '-')}_{city_config['id']}.csv"
            save_csv(gdf, city_row, output_dir)
            logger.info(f"  Metadata saved: {len(gdf)} images")
            return csv_path
        else:
            logger.warning(f"  No metadata found for {city_config['name']}")
            return None

    except Exception as e:
        logger.error(f"  Error fetching metadata for {city_config['name']}: {e}")
        return None


def process_city_batch(city_config, worldcities_csv, base_output_dir, pipeline, logger):
    """Process a single city: download metadata → download images in batches → analyze → cleanup.

    Args:
        city_config: City configuration dict
        worldcities_csv: Path to worldcities CSV
        base_output_dir: Base directory for outputs
        pipeline: Initialized SunnyShadePipeline
        logger: Logger instance

    Returns:
        Dict with processing stats
    """
    city_name = city_config['name'].replace(' ', '-')
    city_dir = base_output_dir / city_name
    city_dir.mkdir(parents=True, exist_ok=True)

    start_time = time.time()
    stats = {
        'city': city_config['name'],
        'total_images': 0,
        'downloaded': 0,
        'analyzed': 0,
        'sunny': 0,
        'errors': 0,
        'duration_seconds': 0
    }

    logger.info("=" * 80)
    logger.info(f"Processing City: {city_config['name']}, {city_config['country']}")
    logger.info("=" * 80)

    # Step 1: Fetch metadata
    csv_path = fetch_city_metadata(city_config, worldcities_csv, city_dir, logger)
    if csv_path is None or not csv_path.exists():
        logger.error(f"Skipping {city_config['name']} - no metadata")
        return stats

    # Load metadata
    df = pd.read_csv(csv_path)
    stats['total_images'] = len(df)
    logger.info(f"Total images to process: {len(df)}")

    # Prepare for batched processing
    images_dir = city_dir / "images_temp"
    images_dir.mkdir(parents=True, exist_ok=True)

    results_list = []

    # Step 2 & 3: Download and analyze in batches
    logger.info(f"Processing in batches of {BATCH_SIZE}")

    for batch_idx in range(0, len(df), BATCH_SIZE):
        batch_df = df.iloc[batch_idx:batch_idx + BATCH_SIZE]
        logger.info(f"  Batch {batch_idx//BATCH_SIZE + 1}/{(len(df)-1)//BATCH_SIZE + 1}: {len(batch_df)} images")

        # Prepare download tasks for this batch
        download_tasks = []
        for _, row in batch_df.iterrows():
            image_id = str(row['id'])
            filename = f"{image_id}.jpg"
            download_tasks.append((image_id, filename))

        # Download batch asynchronously
        logger.info(f"    Downloading {len(download_tasks)} images...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success, failed = loop.run_until_complete(
            download_images_batch_async(download_tasks, images_dir, logger, MAPILLARY_TOKEN)
        )
        loop.close()

        stats['downloaded'] += success
        stats['errors'] += failed
        logger.info(f"    Downloaded: {success}, Failed: {failed}")

        # Analyze batch
        logger.info(f"    Running sunny/shade analysis...")
        try:
            batch_results = pipeline.process_folder(
                images_dir,
                output_csv=None  # Don't save intermediate CSVs
            )
            results_list.append(batch_results)
            sunny_count = batch_results['is_sunny'].sum() if 'is_sunny' in batch_results.columns else 0
            stats['analyzed'] += len(batch_results)
            stats['sunny'] += sunny_count
            logger.info(f"    Analyzed: {len(batch_results)}, Sunny: {sunny_count}")
        except Exception as e:
            logger.error(f"    Analysis error: {e}")
            stats['errors'] += len(batch_df)

        # Cleanup batch images to save space
        logger.info(f"    Cleaning up batch images...")
        try:
            shutil.rmtree(images_dir)
            images_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"    Cleanup warning: {e}")

    # Step 4: Combine all batch results
    if results_list:
        logger.info("Combining all batch results...")
        combined_results = pd.concat(results_list, ignore_index=True)

        # Merge with original metadata
        df['id'] = df['id'].astype(str)
        combined_results['image_id'] = combined_results['image_id'].astype(str)

        merged_df = df.merge(
            combined_results,
            left_on='id',
            right_on='image_id',
            how='left'
        )

        if 'image_id' in merged_df.columns:
            merged_df = merged_df.drop(columns=['image_id'])

        # Save final analyzed CSV
        output_csv = city_dir / f"{city_name}_analyzed.csv"
        merged_df.to_csv(output_csv, index=False)
        logger.info(f"✓ Saved analyzed CSV: {output_csv}")
        logger.info(f"  Rows: {len(merged_df)}, Sunny: {stats['sunny']}")

    # Step 5: Final cleanup
    logger.info("Final cleanup...")
    try:
        if images_dir.exists():
            shutil.rmtree(images_dir)
    except Exception as e:
        logger.warning(f"Final cleanup warning: {e}")

    stats['duration_seconds'] = time.time() - start_time
    logger.info(f"✓ {city_config['name']} complete in {stats['duration_seconds']/60:.1f} minutes")
    logger.info("")

    return stats


def main():
    parser = argparse.ArgumentParser(description='Multi-city overnight SVI analysis pipeline')
    parser.add_argument('--output-dir', type=str, default='data/multi_city_output',
                       help='Base output directory')
    parser.add_argument('--worldcities-csv', type=str,
                       default='/home/kieran/Documents/Datasets/Global streetscapes/global-streetscapes/code/raw_download/data/worldcities.csv',
                       help='Path to worldcities CSV')
    parser.add_argument('--vit-model', type=str, default='outputs/models/vit_binary.pth',
                       help='Path to ViT model')
    parser.add_argument('--yolo-model', type=str, default='outputs/models/sunny_batch_train4/weights/best.pt',
                       help='Path to YOLO model')
    parser.add_argument('--cities', type=str, nargs='+',
                       help='City names to process (default: all configured cities)')
    parser.add_argument('--test-mode', action='store_true',
                       help='Test mode: process only first 200 images per city')

    args = parser.parse_args()

    # Setup
    base_output_dir = Path(args.output_dir)
    base_output_dir.mkdir(parents=True, exist_ok=True)

    logger = setup_logging(base_output_dir)
    mly.set_access_token(MAPILLARY_TOKEN)

    # Load pipeline (once for all cities)
    logger.info("=" * 80)
    logger.info("MULTI-CITY OVERNIGHT PIPELINE")
    logger.info("=" * 80)
    logger.info("Initializing models...")

    pipeline = SunnyShadePipeline(
        vit_model_path=args.vit_model,
        yolo_model_path=args.yolo_model
    )
    logger.info("✓ Models loaded")
    logger.info("")

    # Filter cities if specified
    cities_to_process = CITY_CONFIG
    if args.cities:
        cities_to_process = [c for c in CITY_CONFIG if c['name'] in args.cities]
        logger.info(f"Processing selected cities: {[c['name'] for c in cities_to_process]}")
    else:
        logger.info(f"Processing all {len(cities_to_process)} configured cities")

    logger.info("")

    # Process cities sequentially (download happens async within each city)
    all_stats = []
    overall_start = time.time()

    for city_config in cities_to_process:
        try:
            stats = process_city_batch(
                city_config,
                args.worldcities_csv,
                base_output_dir,
                pipeline,
                logger
            )
            all_stats.append(stats)
        except Exception as e:
            logger.error(f"Fatal error processing {city_config['name']}: {e}")
            import traceback
            traceback.print_exc()

    # Final summary
    overall_duration = time.time() - overall_start

    logger.info("=" * 80)
    logger.info("PIPELINE COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Total duration: {overall_duration/3600:.2f} hours")
    logger.info("")
    logger.info("City Summary:")
    logger.info("-" * 80)

    for stats in all_stats:
        logger.info(f"{stats['city']:20s} | Images: {stats['total_images']:6d} | "
                   f"Analyzed: {stats['analyzed']:6d} | Sunny: {stats['sunny']:5d} | "
                   f"Time: {stats['duration_seconds']/60:6.1f}min")

    total_images = sum(s['total_images'] for s in all_stats)
    total_analyzed = sum(s['analyzed'] for s in all_stats)
    total_sunny = sum(s['sunny'] for s in all_stats)

    logger.info("-" * 80)
    logger.info(f"{'TOTAL':20s} | Images: {total_images:6d} | "
               f"Analyzed: {total_analyzed:6d} | Sunny: {total_sunny:5d}")
    logger.info("")
    logger.info(f"Output directory: {base_output_dir}")
    logger.info("=" * 80)

    # Save summary JSON
    summary_file = base_output_dir / "pipeline_summary.json"

    # Convert numpy/pandas int64 to regular Python int for JSON serialization
    def convert_to_native_types(obj):
        """Recursively convert numpy/pandas types to native Python types."""
        if isinstance(obj, dict):
            return {k: convert_to_native_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_to_native_types(item) for item in obj]
        elif hasattr(obj, 'item'):  # numpy types
            return obj.item()
        elif isinstance(obj, (int, float, str, bool, type(None))):
            return obj
        else:
            return str(obj)

    summary_data = {
        'timestamp': datetime.now().isoformat(),
        'duration_hours': float(overall_duration / 3600),
        'cities_processed': len(all_stats),
        'total_images': int(total_images),
        'total_analyzed': int(total_analyzed),
        'total_sunny': int(total_sunny),
        'city_stats': convert_to_native_types(all_stats)
    }

    with open(summary_file, 'w') as f:
        json.dump(summary_data, f, indent=2)

    logger.info(f"Summary saved to: {summary_file}")


if __name__ == "__main__":
    main()
