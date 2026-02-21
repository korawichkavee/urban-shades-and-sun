#!/usr/bin/env python3
# ABOUTME: SVI analysis pipeline for University Park, PA (Penn State area)
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
import shutil
import geopandas as gp

# Import existing pipeline components
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'data_collection'))

from sunny_shade_pipeline import SunnyShadePipeline
from fetch_city_boundaries import get_city_bbox

CITY_CONFIG = {
    "name": "State College",
    "country": "USA",
    "lat": 40.7934,
    "lon": -77.8600,
    "state": "PA",
}

BATCH_SIZE = 256
MAPILLARY_TOKEN = 'MLY|9798203303595429|e2d4e749e96af419787ec1ca33019e3f'


def setup_logging(output_dir):
    """Set up logging to file and console."""
    log_file = output_dir / f"university_park_svi_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

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

    Returns:
        Tuple of (success: bool, error_message: str or None)
    """
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
                    except Exception:
                        pass
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
                success += 1
                continue

            task = download_image_async(session, image_id, output_path, token)
            tasks.append((image_id, task))

        for image_id, task in tasks:
            is_success, error = await task
            if is_success:
                success += 1
            else:
                failed += 1
                if error and ('rate limit' in error.lower() or '429' in error):
                    rate_limited += 1
                if failed <= 5:
                    logger.debug(f"Failed to download {image_id}: {error}")

    if rate_limited > 0:
        logger.warning(f"Rate limiting detected: {rate_limited} images rate-limited out of {failed} failures")
        logger.warning(f"  Mapillary rate limits: Graph API 60k/min, Tiles API 50k/day")

    return success, failed


def fetch_metadata(output_dir, logger, bbox_size=0.15):
    """Fetch Mapillary metadata for University Park using OSM boundary or fallback bbox.

    Args:
        output_dir: Directory to save metadata CSV
        logger: Logger instance
        bbox_size: Fallback bbox size in degrees if OSM boundary unavailable

    Returns:
        Path to saved CSV or None if failed
    """
    logger.info(f"Fetching metadata for {CITY_CONFIG['name']}, {CITY_CONFIG['state']}")

    try:
        logger.info("  Getting city boundary...")
        boundary_result = get_city_bbox(CITY_CONFIG)
        bbox = boundary_result['bbox']
        boundary_gdf = boundary_result['boundary']

        logger.info(f"  Using {boundary_result['method']}")
        logger.info(f"  Bounding box: ({bbox['south']:.3f}, {bbox['west']:.3f}) to ({bbox['north']:.3f}, {bbox['east']:.3f})")

        if boundary_gdf is not None:
            area_km2 = boundary_gdf.to_crs(epsg=3857).area.sum() / 1e6
            logger.info(f"  Area: {area_km2:.2f} km²")

        mly.set_access_token(MAPILLARY_TOKEN)

        logger.info("  Fetching image metadata (may take a few minutes)...")
        data = mly.images_in_bbox(bbox=bbox)

        if not data:
            logger.warning("  No metadata found")
            return None

        try:
            geojson_dict = json.loads(data)
        except json.JSONDecodeError as e:
            if isinstance(data, str) and ('rate limit' in data.lower() or 'throttl' in data.lower()):
                logger.error("  Rate limit hit - wait and retry")
            else:
                logger.error(f"  JSON parse error: {e}")
            return None

        if 'features' not in geojson_dict or len(geojson_dict['features']) == 0:
            logger.warning("  No features found")
            return None

        gdf = gp.GeoDataFrame.from_features(geojson_dict, crs="EPSG:4326")

        initial_count = len(gdf)
        if boundary_gdf is not None:
            logger.info(f"  Filtering {initial_count:,} images to city boundary...")
            if boundary_gdf.crs is None:
                boundary_gdf = boundary_gdf.set_crs("EPSG:4326")
            if boundary_gdf.crs != gdf.crs:
                boundary_gdf = boundary_gdf.to_crs(gdf.crs)

            gdf = gp.sjoin(gdf, boundary_gdf, how='inner', predicate='within')
            gdf = gdf[[col for col in gdf.columns if not col.startswith('index_')]]

            filtered_count = len(gdf)
            logger.info(f"  Kept {filtered_count:,} images within boundary ({filtered_count/initial_count*100:.1f}%)")
        else:
            logger.info(f"  No boundary filter applied, keeping all {initial_count:,} images in bbox")

        gdf['lon'] = gdf.geometry.x
        gdf['lat'] = gdf.geometry.y
        df = pd.DataFrame(gdf.drop(columns='geometry'))

        if 'captured_at' in df.columns:
            df['captured_at'] = pd.to_datetime(df['captured_at'], unit='ms')

        city_slug = CITY_CONFIG['name'].replace(' ', '-').lower()
        csv_path = output_dir / f"{city_slug}_metadata.csv"
        df.to_csv(csv_path, index=False)

        logger.info(f"  Metadata saved: {len(df):,} images -> {csv_path}")
        return csv_path

    except Exception as e:
        logger.error(f"  Error fetching metadata: {e}")
        import traceback
        traceback.print_exc()
        return None


def process_images(base_output_dir, pipeline, logger, test_mode=False):
    """Download and analyze all images for University Park.

    Args:
        base_output_dir: Base output directory
        pipeline: Initialized SunnyShadePipeline
        logger: Logger instance
        test_mode: If True, process only first 5 images for validation

    Returns:
        Dict with processing stats
    """
    city_slug = CITY_CONFIG['name'].replace(' ', '-').lower()
    city_dir = base_output_dir / city_slug
    city_dir.mkdir(parents=True, exist_ok=True)

    start_time = time.time()
    stats = {
        'city': CITY_CONFIG['name'],
        'total_images': 0,
        'downloaded': 0,
        'analyzed': 0,
        'sunny': 0,
        'errors': 0,
        'duration_seconds': 0
    }

    logger.info("=" * 80)
    logger.info(f"Processing: {CITY_CONFIG['name']}, {CITY_CONFIG['state']}")
    logger.info("=" * 80)

    # Fetch or load metadata
    csv_path = city_dir / f"{city_slug}_metadata.csv"
    if not csv_path.exists():
        logger.info("Fetching metadata...")
        csv_path = fetch_metadata(city_dir, logger)

    if csv_path is None or not csv_path.exists():
        logger.error("No metadata available - cannot proceed")
        return stats

    df = pd.read_csv(csv_path)
    stats['total_images'] = len(df)

    if test_mode:
        logger.info(f"TEST MODE: Full dataset has {len(df):,} images")
        df = df.head(5)
        logger.info(f"TEST MODE: Limited to {len(df)} images")
    else:
        logger.info(f"Total images to process: {len(df):,}")

    images_dir = city_dir / "images_temp"
    images_dir.mkdir(parents=True, exist_ok=True)

    # Resume support: load already-processed image IDs
    output_csv = city_dir / f"{city_slug}_svi_analyzed.csv"
    existing_ids = set()
    if output_csv.exists():
        logger.info("Resuming from existing progress file...")
        existing_df = pd.read_csv(output_csv)
        existing_ids = set(existing_df['id'].astype(str).tolist())
        logger.info(f"  Already processed: {len(existing_ids):,} images")
        stats['analyzed'] = len(existing_ids)
        stats['sunny'] = existing_df['is_sunny'].sum() if 'is_sunny' in existing_df.columns else 0

    logger.info(f"Processing in batches of {BATCH_SIZE}")
    total_batches = (len(df) - 1) // BATCH_SIZE + 1

    for batch_idx in range(0, len(df), BATCH_SIZE):
        batch_num = batch_idx // BATCH_SIZE + 1
        batch_df = df.iloc[batch_idx:batch_idx + BATCH_SIZE]

        batch_df = batch_df[~batch_df['id'].astype(str).isin(existing_ids)]
        if len(batch_df) == 0:
            logger.info(f"  Batch {batch_num}/{total_batches}: All images already processed, skipping")
            continue

        logger.info(f"  Batch {batch_num}/{total_batches}: {len(batch_df)} images to process")

        download_tasks = []
        for _, row in batch_df.iterrows():
            image_id = str(row['id'])
            download_tasks.append((image_id, f"{image_id}.jpg"))

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

        logger.info("    Running sunny/shade analysis...")
        try:
            batch_results = pipeline.process_folder_batch(images_dir, output_csv=None)
            sunny_count = batch_results['is_sunny'].sum() if 'is_sunny' in batch_results.columns else 0
            stats['analyzed'] += len(batch_results)
            stats['sunny'] += sunny_count
            logger.info(f"    Analyzed: {len(batch_results)}, Sunny: {sunny_count}")

            batch_df = batch_df.copy()
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

            if output_csv.exists():
                existing_df = pd.read_csv(output_csv)
                combined_df = pd.concat([existing_df, batch_merged], ignore_index=True)
                combined_df.to_csv(output_csv, index=False)
                logger.info(f"    Saved incremental results ({len(combined_df):,} total images)")
            else:
                batch_merged.to_csv(output_csv, index=False)
                logger.info(f"    Created output file with {len(batch_merged):,} images")

        except Exception as e:
            logger.error(f"    Analysis error: {e}")
            import traceback
            traceback.print_exc()
            stats['errors'] += len(batch_df)

        logger.info("    Cleaning up batch images...")
        try:
            shutil.rmtree(images_dir)
            images_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"    Cleanup warning: {e}")

    # Final cleanup
    try:
        if images_dir.exists():
            shutil.rmtree(images_dir)
    except Exception as e:
        logger.warning(f"Final cleanup warning: {e}")

    stats['duration_seconds'] = time.time() - start_time
    logger.info(f"\nCompleted in {stats['duration_seconds']/60:.1f} minutes")
    if stats['analyzed'] > 0:
        rate = stats['analyzed'] / stats['duration_seconds']
        logger.info(f"Processing rate: {rate:.2f} images/second")

    return stats


def main():
    parser = argparse.ArgumentParser(description='University Park, PA SVI analysis pipeline')
    parser.add_argument('--output-dir', type=str, default='data/university_park_svi',
                       help='Base output directory')
    parser.add_argument('--vit-model', type=str, default='models/vit_binary.pth',
                       help='Path to ViT binary classification model')
    parser.add_argument('--yolo-model', type=str, default='models/yolo_best.pt',
                       help='Path to YOLO detection model')
    parser.add_argument('--test-mode', action='store_true',
                       help='Process only first 5 images to validate pipeline')
    parser.add_argument('--skip-metadata-fetch', action='store_true',
                       help='Skip metadata fetch (use existing metadata CSV)')

    args = parser.parse_args()

    base_output_dir = Path(args.output_dir)
    base_output_dir.mkdir(parents=True, exist_ok=True)

    logger = setup_logging(base_output_dir)
    mly.set_access_token(MAPILLARY_TOKEN)

    logger.info("=" * 80)
    logger.info("UNIVERSITY PARK, PA SVI ANALYSIS PIPELINE")
    logger.info("For p(shade preference | temperature) analysis")
    if args.test_mode:
        logger.info("TEST MODE: Processing only 5 images for validation")
    logger.info("=" * 80)
    logger.info("")

    # Metadata prefetch
    city_slug = CITY_CONFIG['name'].replace(' ', '-').lower()
    city_dir = base_output_dir / city_slug
    city_dir.mkdir(parents=True, exist_ok=True)
    csv_path = city_dir / f"{city_slug}_metadata.csv"

    if not args.skip_metadata_fetch and not csv_path.exists():
        logger.info("PHASE 1: METADATA FETCH")
        logger.info("=" * 80)
        csv_path = fetch_metadata(city_dir, logger)
        if csv_path is None:
            logger.error("Metadata fetch failed - cannot continue")
            return 1
    elif csv_path.exists():
        df = pd.read_csv(csv_path)
        logger.info(f"Using existing metadata: {len(df):,} images")

    # Estimate runtime
    if csv_path and csv_path.exists():
        df = pd.read_csv(csv_path)
        total_images = len(df)
        logger.info("")
        logger.info("Runtime estimates:")
        for label, rate in [("Conservative (0.5 img/sec)", 0.5), ("Typical (1.0 img/sec)", 1.0), ("Optimistic (2.0 img/sec)", 2.0)]:
            hours = total_images / (rate * 3600)
            logger.info(f"  {label}: {hours:.1f} hours")
        logger.info("")

    # Load models
    logger.info("PHASE 2: MODEL INITIALIZATION")
    logger.info("=" * 80)
    logger.info(f"  ViT: {args.vit_model}")
    logger.info(f"  YOLO: {args.yolo_model}")

    pipeline = SunnyShadePipeline(
        vit_model_path=args.vit_model,
        yolo_model_path=args.yolo_model
    )
    logger.info("Models loaded")
    logger.info("")

    # Process images
    logger.info("PHASE 3: IMAGE PROCESSING")
    logger.info("=" * 80)

    stats = process_images(base_output_dir, pipeline, logger, test_mode=args.test_mode)

    # Summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("PIPELINE COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Total images:    {stats['total_images']:,}")
    logger.info(f"Downloaded:      {stats['downloaded']:,}")
    logger.info(f"Analyzed:        {stats['analyzed']:,}")
    logger.info(f"Sunny:           {stats['sunny']:,}")
    logger.info(f"Errors:          {stats['errors']:,}")
    logger.info(f"Duration:        {stats['duration_seconds']/60:.1f} minutes")
    logger.info(f"Output:          {base_output_dir / city_slug / f'{city_slug}_svi_analyzed.csv'}")
    logger.info("=" * 80)

    # Save summary JSON
    summary_file = base_output_dir / "university_park_pipeline_summary.json"
    summary_data = {
        'timestamp': datetime.now().isoformat(),
        'city': CITY_CONFIG['name'],
        'state': CITY_CONFIG['state'],
        'duration_hours': float(stats['duration_seconds'] / 3600),
        'total_images': int(stats['total_images']),
        'total_analyzed': int(stats['analyzed']),
        'total_sunny': int(stats['sunny']),
        'errors': int(stats['errors']),
    }
    with open(summary_file, 'w') as f:
        json.dump(summary_data, f, indent=2)
    logger.info(f"Summary saved to: {summary_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
