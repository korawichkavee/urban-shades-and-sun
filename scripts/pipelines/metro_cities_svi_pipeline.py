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

    # Step 1: Fetch metadata (should already be done in prefetch phase)
    csv_path = city_dir / f"{city_name}_metadata.csv"
    if not csv_path.exists():
        logger.warning(f"Metadata not found, fetching now...")
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

    # Load existing progress if resuming
    output_csv = city_dir / f"{city_name}_svi_analyzed.csv"
    existing_ids = set()
    if output_csv.exists():
        logger.info(f"Resuming from existing progress file...")
        existing_df = pd.read_csv(output_csv)
        existing_ids = set(existing_df['id'].astype(str).tolist())
        logger.info(f"  Already processed: {len(existing_ids)} images")
        stats['analyzed'] = len(existing_ids)
        stats['sunny'] = existing_df['is_sunny'].sum() if 'is_sunny' in existing_df.columns else 0

    # Step 2 & 3: Download and analyze in batches
    logger.info(f"Processing in batches of {BATCH_SIZE}")
    total_batches = (len(df) - 1) // BATCH_SIZE + 1

    for batch_idx in range(0, len(df), BATCH_SIZE):
        batch_num = batch_idx // BATCH_SIZE + 1
        batch_df = df.iloc[batch_idx:batch_idx + BATCH_SIZE]

        # Skip already processed images
        batch_df = batch_df[~batch_df['id'].astype(str).isin(existing_ids)]
        if len(batch_df) == 0:
            logger.info(f"  Batch {batch_num}/{total_batches}: All images already processed, skipping")
            continue

        logger.info(f"  Batch {batch_num}/{total_batches}: {len(batch_df)} images to process")

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
            batch_results = pipeline.process_folder_batch(
                images_dir,
                output_csv=None  # Don't save intermediate CSVs from pipeline
            )
            sunny_count = batch_results['is_sunny'].sum() if 'is_sunny' in batch_results.columns else 0
            stats['analyzed'] += len(batch_results)
            stats['sunny'] += sunny_count
            logger.info(f"    Analyzed: {len(batch_results)}, Sunny: {sunny_count}")

            # IMPORTANT: Save incremental results after EACH batch
            # Merge batch results with metadata
            batch_df['id'] = batch_df['id'].astype(str)
            batch_results['image_id'] = batch_results['image_id'].astype(str)

            batch_merged = batch_df.merge(
                batch_results,
                left_on='id',
                right_on='image_id',
                how='left'
            )

            if 'image_id' in batch_merged.columns:
                batch_merged = batch_merged.drop(columns=['image_id'])

            # Append to existing CSV or create new one
            if output_csv.exists():
                existing_df = pd.read_csv(output_csv)
                combined_df = pd.concat([existing_df, batch_merged], ignore_index=True)
                combined_df.to_csv(output_csv, index=False)
            else:
                batch_merged.to_csv(output_csv, index=False)

            logger.info(f"    ✓ Saved incremental results to {output_csv.name}")

        except Exception as e:
            logger.error(f"    Analysis error: {e}")
            import traceback
            traceback.print_exc()
            stats['errors'] += len(batch_df)

        # Cleanup batch images to save space
        logger.info(f"    Cleaning up batch images...")
        try:
            shutil.rmtree(images_dir)
            images_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"    Cleanup warning: {e}")

    # Step 4: Final cleanup
    logger.info("Final cleanup...")
    try:
        if images_dir.exists():
            shutil.rmtree(images_dir)
    except Exception as e:
        logger.warning(f"Final cleanup warning: {e}")

    stats['duration_seconds'] = time.time() - start_time
    logger.info(f"✓ {city_config['name']} complete in {stats['duration_seconds']/60:.1f} minutes")

    # Calculate processing rate
    if stats['analyzed'] > 0:
        rate = stats['analyzed'] / stats['duration_seconds']
        logger.info(f"  Processing rate: {rate:.2f} images/second")

    logger.info("")

    return stats


def prefetch_all_metadata(cities_to_process, base_output_dir, logger):
    """Prefetch metadata for all cities to estimate total work and runtime.

    Args:
        cities_to_process: List of city configs to process
        base_output_dir: Base output directory
        logger: Logger instance

    Returns:
        Dict with metadata summary: {city_name: {count: int, csv_path: Path}, ...}
    """
    logger.info("=" * 80)
    logger.info("PHASE 1: METADATA PREFETCH")
    logger.info("=" * 80)
    logger.info(f"Fetching metadata for {len(cities_to_process)} cities...")
    logger.info("This will determine total image count and estimate runtime")
    logger.info("")

    metadata_summary = {}
    prefetch_start = time.time()

    for idx, city_config in enumerate(cities_to_process, 1):
        city_name = city_config['name'].replace(' ', '-').lower()
        city_dir = base_output_dir / city_name
        city_dir.mkdir(parents=True, exist_ok=True)
        csv_path = city_dir / f"{city_name}_metadata.csv"

        logger.info(f"[{idx}/{len(cities_to_process)}] {city_config['name']}, {city_config['state']}")

        # Check if metadata already exists
        if csv_path.exists():
            logger.info(f"  Metadata already exists, loading...")
            try:
                df = pd.read_csv(csv_path)
                image_count = len(df)
                logger.info(f"  ✓ Found {image_count:,} images")
                metadata_summary[city_config['name']] = {
                    'count': image_count,
                    'csv_path': csv_path
                }
                continue
            except Exception as e:
                logger.warning(f"  Could not load existing metadata: {e}")

        # Fetch new metadata
        try:
            fetched_csv = fetch_city_metadata_bbox(city_config, city_dir, logger)
            if fetched_csv and fetched_csv.exists():
                df = pd.read_csv(fetched_csv)
                image_count = len(df)
                logger.info(f"  ✓ Fetched {image_count:,} images")
                metadata_summary[city_config['name']] = {
                    'count': image_count,
                    'csv_path': fetched_csv
                }
            else:
                logger.warning(f"  ⚠ No metadata available for {city_config['name']}")
                metadata_summary[city_config['name']] = {
                    'count': 0,
                    'csv_path': None
                }
        except Exception as e:
            logger.error(f"  ✗ Error fetching metadata: {e}")
            metadata_summary[city_config['name']] = {
                'count': 0,
                'csv_path': None
            }

    prefetch_duration = time.time() - prefetch_start

    # Calculate totals and estimates
    total_images = sum(m['count'] for m in metadata_summary.values())
    cities_with_data = sum(1 for m in metadata_summary.values() if m['count'] > 0)

    logger.info("")
    logger.info("=" * 80)
    logger.info("METADATA PREFETCH COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Prefetch duration: {prefetch_duration/60:.1f} minutes")
    logger.info("")
    logger.info("Per-City Breakdown:")
    logger.info("-" * 80)

    for city_name, meta in sorted(metadata_summary.items(), key=lambda x: x[1]['count'], reverse=True):
        if meta['count'] > 0:
            logger.info(f"{city_name:20s} | {meta['count']:>10,} images")

    logger.info("-" * 80)
    logger.info(f"{'TOTAL':20s} | {total_images:>10,} images")
    logger.info("")
    logger.info(f"Cities with data: {cities_with_data}/{len(cities_to_process)}")

    # Estimate runtime based on benchmark performance
    # Conservative estimates based on typical performance:
    # - Download: 1-2 sec/image (async parallel)
    # - ViT classification: 0.1 sec/image (GPU)
    # - YOLO detection: 0.15 sec/image (GPU), but only on ~50% sunny images
    # - Total: ~2-3 sec/image worst case, ~1-1.5 sec/image typical
    images_per_second_conservative = 0.5  # Conservative estimate
    images_per_second_typical = 1.0  # Typical with good GPU
    images_per_second_optimistic = 2.0  # Best case scenario

    estimated_hours_conservative = total_images / (images_per_second_conservative * 3600)
    estimated_hours_typical = total_images / (images_per_second_typical * 3600)
    estimated_hours_optimistic = total_images / (images_per_second_optimistic * 3600)

    logger.info("")
    logger.info("Runtime Estimates:")
    logger.info("-" * 80)
    logger.info(f"Conservative (0.5 img/sec): {estimated_hours_conservative:>6.1f} hours ({estimated_hours_conservative/24:>5.1f} days)")
    logger.info(f"Typical (1.0 img/sec):      {estimated_hours_typical:>6.1f} hours ({estimated_hours_typical/24:>5.1f} days)")
    logger.info(f"Optimistic (2.0 img/sec):   {estimated_hours_optimistic:>6.1f} hours ({estimated_hours_optimistic/24:>5.1f} days)")
    logger.info("")
    logger.info("Note: Estimates assume continuous processing with no interruptions")
    logger.info("      Actual time may vary based on:")
    logger.info("      - GPU performance (CUDA vs CPU)")
    logger.info("      - Network speed for downloads")
    logger.info("      - API rate limits")
    logger.info("      - Sunny image percentage (affects YOLO workload)")
    logger.info("=" * 80)
    logger.info("")

    return metadata_summary


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
    parser.add_argument('--skip-prefetch', action='store_true',
                       help='Skip metadata prefetch phase (use existing metadata)')

    args = parser.parse_args()

    # Setup
    base_output_dir = Path(args.output_dir)
    base_output_dir.mkdir(parents=True, exist_ok=True)

    logger = setup_logging(base_output_dir)
    mly.set_access_token(MAPILLARY_TOKEN)

    # Header
    logger.info("=" * 80)
    logger.info("METRO CITIES SVI ANALYSIS PIPELINE")
    logger.info("For p(shade preference | temperature) analysis")
    if args.test_mode:
        logger.info("⚠ TEST MODE: Processing only 5 images per city for validation")
    logger.info("=" * 80)
    logger.info("")

    # Filter cities if specified
    cities_to_process = METRO_CITIES
    if args.cities:
        cities_to_process = [c for c in METRO_CITIES if c['name'] in args.cities]
        logger.info(f"Selected cities: {[c['name'] for c in cities_to_process]}")
    else:
        logger.info(f"Processing all {len(cities_to_process)} metro cities")

    logger.info("")

    # PHASE 1: Prefetch all metadata and estimate runtime
    if not args.skip_prefetch:
        metadata_summary = prefetch_all_metadata(cities_to_process, base_output_dir, logger)

        # Ask user to confirm before proceeding
        if not args.test_mode:
            logger.info("Press Ctrl+C to abort, or any key to continue...")
            try:
                input()
            except KeyboardInterrupt:
                logger.info("\nAborted by user")
                return
    else:
        logger.info("Skipping metadata prefetch (using existing metadata)")
        logger.info("")

    # PHASE 2: Load models
    logger.info("=" * 80)
    logger.info("PHASE 2: MODEL INITIALIZATION")
    logger.info("=" * 80)
    logger.info("Loading ML models...")

    pipeline = SunnyShadePipeline(
        vit_model_path=args.vit_model,
        yolo_model_path=args.yolo_model
    )
    logger.info("✓ Models loaded")
    logger.info("")

    # PHASE 3: Process all cities
    logger.info("=" * 80)
    logger.info("PHASE 3: IMAGE PROCESSING")
    logger.info("=" * 80)
    logger.info("")

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
    logger.info(f"Total processing duration: {overall_duration/3600:.2f} hours")
    logger.info("")
    logger.info("City Summary:")
    logger.info("-" * 80)

    for stats in all_stats:
        rate = stats['analyzed'] / stats['duration_seconds'] if stats['duration_seconds'] > 0 else 0
        logger.info(f"{stats['city']:20s} | Images: {stats['total_images']:>8,} | "
                   f"Analyzed: {stats['analyzed']:>8,} | Sunny: {stats['sunny']:>6,} | "
                   f"Time: {stats['duration_seconds']/60:>6.1f}min | Rate: {rate:>4.2f} img/s")

    total_images = sum(s['total_images'] for s in all_stats)
    total_analyzed = sum(s['analyzed'] for s in all_stats)
    total_sunny = sum(s['sunny'] for s in all_stats)
    avg_rate = total_analyzed / overall_duration if overall_duration > 0 else 0

    logger.info("-" * 80)
    logger.info(f"{'TOTAL':20s} | Images: {total_images:>8,} | "
               f"Analyzed: {total_analyzed:>8,} | Sunny: {total_sunny:>6,} | "
               f"Avg Rate: {avg_rate:>4.2f} img/s")
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
        'avg_processing_rate': float(avg_rate),
        'city_stats': all_stats
    }

    with open(summary_file, 'w') as f:
        json.dump(summary_data, f, indent=2)

    logger.info(f"Summary saved to: {summary_file}")


if __name__ == "__main__":
    main()
