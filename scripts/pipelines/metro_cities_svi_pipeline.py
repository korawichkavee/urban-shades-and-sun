#!/usr/bin/env python3
# ABOUTME: SVI analysis pipeline for metro cities with travel survey data
# ABOUTME: Downloads and analyzes street view imagery for shade preference analysis

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
from concurrent.futures import ThreadPoolExecutor
import shutil
import geopandas as gp

# Import existing pipeline components
sys.path.insert(0, str(Path(__file__).parent.parent / 'data_collection'))
sys.path.insert(0, str(Path(__file__).parent))

from sunny_shade_pipeline import SunnyShadePipeline
from download_mly_points import get_mly_gdf, save_csv


# Metro cities configuration based on travel survey data
# Coordinates from worldcities.csv, all cities with UTCI-annotated metro survey data
METRO_CITIES = [
    # Recoverable surveys (UTCI annotation in progress - 7 cities)
    {"name": "Anchorage", "country": "USA", "lat": 61.15, "lon": -149.11, "state": "AK"},
    {"name": "Boston", "country": "USA", "lat": 42.32, "lon": -71.08, "state": "MA"},
    {"name": "Boise", "country": "USA", "lat": 43.60, "lon": -116.23, "state": "ID"},
    {"name": "Louisville", "country": "USA", "lat": 38.17, "lon": -85.65, "state": "KY"},
    {"name": "Los Angeles", "country": "USA", "lat": 34.11, "lon": -118.41, "state": "CA"},
    {"name": "Salt Lake City", "country": "USA", "lat": 40.78, "lon": -111.93, "state": "UT"},
    {"name": "San Francisco", "country": "USA", "lat": 37.76, "lon": -122.44, "state": "CA"},

    # Existing metro surveys (UTCI already annotated - 13 cities)
    {"name": "Atlanta", "country": "USA", "lat": 33.76, "lon": -84.42, "state": "GA"},
    {"name": "Cleveland", "country": "USA", "lat": 41.48, "lon": -81.68, "state": "OH"},
    {"name": "Columbia", "country": "USA", "lat": 34.04, "lon": -80.90, "state": "SC"},
    {"name": "Denver", "country": "USA", "lat": 39.76, "lon": -104.88, "state": "CO"},
    {"name": "Evansville", "country": "USA", "lat": 37.99, "lon": -87.53, "state": "IN"},
    {"name": "Honolulu", "country": "USA", "lat": 21.33, "lon": -157.85, "state": "HI"},
    {"name": "Minneapolis", "country": "USA", "lat": 44.96, "lon": -93.27, "state": "MN"},
    {"name": "Phoenix", "country": "USA", "lat": 33.57, "lon": -112.09, "state": "AZ"},
    {"name": "Raleigh", "country": "USA", "lat": 35.83, "lon": -78.64, "state": "NC"},
    {"name": "Seattle", "country": "USA", "lat": 47.62, "lon": -122.32, "state": "WA"},
    {"name": "St. Louis", "country": "USA", "lat": 38.64, "lon": -90.25, "state": "MO"},
    {"name": "Tucson", "country": "USA", "lat": 32.15, "lon": -110.88, "state": "AZ"},
]

# Note: Some cities have multiple survey years (e.g., Atlanta 1991 & 2001, Seattle multiple years)
# but we only need SVI data from one representative sample per city

BATCH_SIZE = 100  # Process images in batches to manage memory
MAPILLARY_TOKEN = 'MLY|9798203303595429|e2d4e749e96af419787ec1ca33019e3f'


def setup_logging(output_dir):
    """Set up logging for the pipeline."""
    log_file = output_dir / f"metro_svi_pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

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
    """Download a single image asynchronously with rate limit handling.

    Args:
        session: aiohttp ClientSession
        image_id: Mapillary image ID
        output_path: Path to save image
        token: Mapillary API token
        max_retries: Maximum number of retry attempts for rate limits

    Returns:
        Tuple of (success: bool, error_message: str or None)
    """
    retry_delay = 2  # Initial retry delay in seconds

    for attempt in range(max_retries):
        try:
            # Get image metadata with thumb_2048_url
            metadata_url = f"https://graph.mapillary.com/{image_id}?fields=thumb_2048_url&access_token={token}"
            async with session.get(metadata_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                # Check for rate limiting
                if response.status == 429:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    return False, "Rate limit exceeded (429)"

                if response.status != 200:
                    # Try to parse error message for rate limit indicators
                    try:
                        error_data = await response.json()
                        if 'error' in error_data:
                            error_msg = error_data.get('error', {})
                            if isinstance(error_msg, dict):
                                msg_text = error_msg.get('message', '')
                                if 'rate limit' in msg_text.lower() or 'throttl' in msg_text.lower():
                                    if attempt < max_retries - 1:
                                        await asyncio.sleep(retry_delay)
                                        retry_delay *= 2
                                        continue
                                    return False, f"Rate limited: {msg_text}"
                    except:
                        pass
                    return False, f"Metadata HTTP {response.status}"

                metadata = await response.json()
                if 'thumb_2048_url' not in metadata:
                    return False, "No thumb_2048_url in metadata"
                image_url = metadata['thumb_2048_url']

            # Download the actual image
            async with session.get(image_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 429:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    return False, "Rate limit exceeded on image download (429)"

                if response.status == 200:
                    content = await response.read()
                    output_path.write_bytes(content)
                    return True, None
                else:
                    return False, f"Image HTTP {response.status}"

        except asyncio.TimeoutError:
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
                continue
            return False, "Timeout"
        except Exception as e:
            return False, str(e)

    return False, "Max retries exceeded"


async def download_images_batch_async(image_data_list, output_dir, logger, token):
    """Download a batch of images asynchronously."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    success = 0
    failed = 0
    rate_limited = 0

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
                # Check if it's a rate limit error
                if error and ('rate limit' in error.lower() or '429' in error):
                    rate_limited += 1
                if failed <= 5:  # Log first 5 errors
                    logger.debug(f"Failed to download {image_id}: {error}")

    # Log rate limit summary if any occurred
    if rate_limited > 0:
        logger.warning(f"⚠ Rate limiting detected: {rate_limited} images rate-limited out of {failed} failures")
        logger.warning(f"  Mapillary rate limits: Graph API 60k/min, Tiles API 50k/day")
        logger.warning(f"  Consider reducing batch size or adding delays between batches")

    return success, failed


def fetch_city_metadata_bbox(city_config, output_dir, logger, bbox_size=0.15):
    """Fetch metadata for a city using bounding box around city center.

    Args:
        city_config: City configuration dict with name, lat, lon
        output_dir: Directory to save metadata CSV
        logger: Logger instance
        bbox_size: Size of bounding box in degrees (default 0.15 = ~10km radius)
                   Use smaller values (e.g., 0.01 = ~1km) for testing

    Returns:
        Path to saved CSV or None if failed
    """
    logger.info(f"Fetching metadata for {city_config['name']}, {city_config['country']}")

    try:
        # Create bounding box around city center
        # bbox_size: 0.15 = ~10km radius, 0.01 = ~1km radius at mid-latitudes
        min_lon = city_config['lon'] - bbox_size
        max_lon = city_config['lon'] + bbox_size
        min_lat = city_config['lat'] - bbox_size
        max_lat = city_config['lat'] + bbox_size

        # Fetch Mapillary points
        logger.info(f"  Bounding box: ({min_lat:.3f}, {min_lon:.3f}) to ({max_lat:.3f}, {max_lon:.3f})")

        # Use download_mly_points logic with bbox
        mly.set_access_token(MAPILLARY_TOKEN)

        # Get image data (returns GeoJSON string)
        # NOTE: images_in_bbox uses Tiles API (50,000 requests/day limit)
        data = mly.images_in_bbox(
            bbox={'west': min_lon, 'south': min_lat, 'east': max_lon, 'north': max_lat}
        )

        if not data:
            logger.warning(f"  No metadata found for {city_config['name']}")
            return None

        # Parse GeoJSON string and convert to DataFrame
        try:
            geojson_dict = json.loads(data)
        except json.JSONDecodeError as e:
            # Check if data contains rate limit error message
            if isinstance(data, str) and ('rate limit' in data.lower() or 'throttl' in data.lower()):
                logger.error(f"  ⚠ Rate limit hit for {city_config['name']}")
                logger.error(f"  Mapillary Tiles API limit: 50,000 requests/day")
                logger.error(f"  Wait and retry later, or reduce number of cities processed per day")
            else:
                logger.error(f"  JSON parse error: {e}")
            return None
        if 'features' not in geojson_dict or len(geojson_dict['features']) == 0:
            logger.warning(f"  No features found for {city_config['name']}")
            return None

        # Create GeoDataFrame then convert to regular DataFrame
        gdf = gp.GeoDataFrame.from_features(geojson_dict)
        df = pd.DataFrame(gdf.drop(columns='geometry'))

        # Standardize column names
        if 'captured_at' in df.columns:
            df['captured_at'] = pd.to_datetime(df['captured_at'], unit='ms')

        # Save CSV
        city_name_safe = city_config['name'].replace(' ', '-').lower()
        csv_path = output_dir / f"{city_name_safe}_metadata.csv"
        df.to_csv(csv_path, index=False)

        logger.info(f"  Metadata saved: {len(df)} images")
        return csv_path

    except Exception as e:
        logger.error(f"  Error fetching metadata for {city_config['name']}: {e}")
        import traceback
        traceback.print_exc()
        return None


def process_city_batch(city_config, base_output_dir, pipeline, logger, test_mode=False):
    """Process a single city: download metadata → download images → analyze → cleanup.

    Args:
        city_config: City configuration dict
        base_output_dir: Base directory for outputs
        pipeline: Initialized SunnyShadePipeline
        logger: Logger instance
        test_mode: If True, process only first 5 images for validation

    Returns:
        Dict with processing stats
    """
    city_name = city_config['name'].replace(' ', '-').lower()
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
    csv_path = fetch_city_metadata_bbox(city_config, city_dir, logger)
    if csv_path is None or not csv_path.exists():
        logger.error(f"Skipping {city_config['name']} - no metadata")
        return stats

    # Load metadata
    df = pd.read_csv(csv_path)
    stats['total_images'] = len(df)

    # Apply test mode limiting
    if test_mode:
        logger.info(f"TEST MODE: Full dataset has {len(df)} images")
        df = df.head(5)
        logger.info(f"TEST MODE: Limited to {len(df)} images for validation")
    else:
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

        # Prepare download tasks
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
        output_csv = city_dir / f"{city_name}_svi_analyzed.csv"
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
    parser = argparse.ArgumentParser(description='Metro cities SVI analysis pipeline for shade preference study')
    parser.add_argument('--output-dir', type=str, default='data/metro_cities_svi',
                       help='Base output directory')
    parser.add_argument('--vit-model', type=str, default='outputs/models/vit_binary.pth',
                       help='Path to ViT binary classification model')
    parser.add_argument('--yolo-model', type=str, default='outputs/models/sunny_batch_train4/weights/best.pt',
                       help='Path to YOLO detection model')
    parser.add_argument('--cities', type=str, nargs='+',
                       help='City names to process (default: all metro cities)')
    parser.add_argument('--test-mode', action='store_true',
                       help='Test mode: process only first 5 images per city to validate pipeline')

    args = parser.parse_args()

    # Setup
    base_output_dir = Path(args.output_dir)
    base_output_dir.mkdir(parents=True, exist_ok=True)

    logger = setup_logging(base_output_dir)
    mly.set_access_token(MAPILLARY_TOKEN)

    # Load pipeline (once for all cities)
    logger.info("=" * 80)
    logger.info("METRO CITIES SVI ANALYSIS PIPELINE")
    logger.info("For p(shade preference | temperature) analysis")
    if args.test_mode:
        logger.info("⚠ TEST MODE: Processing only 5 images per city for validation")
    logger.info("=" * 80)
    logger.info("Initializing models...")

    pipeline = SunnyShadePipeline(
        vit_model_path=args.vit_model,
        yolo_model_path=args.yolo_model
    )
    logger.info("✓ Models loaded")
    logger.info("")

    # Filter cities if specified
    cities_to_process = METRO_CITIES
    if args.cities:
        cities_to_process = [c for c in METRO_CITIES if c['name'] in args.cities]
        logger.info(f"Processing selected cities: {[c['name'] for c in cities_to_process]}")
    else:
        logger.info(f"Processing all {len(cities_to_process)} metro cities")

    logger.info("")

    # Process cities sequentially
    all_stats = []
    overall_start = time.time()

    for city_config in cities_to_process:
        try:
            stats = process_city_batch(
                city_config,
                base_output_dir,
                pipeline,
                logger,
                test_mode=args.test_mode
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
    summary_file = base_output_dir / "metro_pipeline_summary.json"

    summary_data = {
        'timestamp': datetime.now().isoformat(),
        'duration_hours': float(overall_duration / 3600),
        'cities_processed': len(all_stats),
        'total_images': int(total_images),
        'total_analyzed': int(total_analyzed),
        'total_sunny': int(total_sunny),
        'city_stats': all_stats
    }

    with open(summary_file, 'w') as f:
        json.dump(summary_data, f, indent=2)

    logger.info(f"Summary saved to: {summary_file}")


if __name__ == "__main__":
    main()
