#!/usr/bin/env python3
# ABOUTME: Downloads metadata only for Dallas and Los Angeles
# ABOUTME: Uses chunked/batched tile fetching to avoid memory issues

import sys
import json
import logging
from pathlib import Path
from datetime import datetime
import pandas as pd
import geopandas as gp
import mapillary.interface as mly

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'pipelines'))
from fetch_city_boundaries import get_city_bbox

MAPILLARY_TOKEN = 'MLY|9798203303595429|e2d4e749e96af419787ec1ca33019e3f'

# Cities to download
CITIES = [
    {"name": "Dallas", "country": "USA", "lat": 32.7936, "lon": -96.7662, "state": "TX"},
    {"name": "Los Angeles", "country": "USA", "lat": 34.11, "lon": -118.41, "state": "CA"},
]


def setup_logging(output_dir):
    """Set up logging."""
    log_file = output_dir / f"metadata_download_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

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


def fetch_metadata_chunked(bbox, boundary_gdf, city_name, logger):
    """Fetch metadata in chunks by subdividing the bounding box.

    This prevents memory issues with large cities by processing smaller areas at a time.
    """
    # Calculate reasonable chunk size based on bbox area
    lat_range = bbox['north'] - bbox['south']
    lon_range = bbox['east'] - bbox['west']

    # For very large cities (LA, Dallas), use 4x4 grid = 16 chunks
    # Each chunk will be ~1/16 of the total area
    n_lat_chunks = 4
    n_lon_chunks = 4

    lat_step = lat_range / n_lat_chunks
    lon_step = lon_range / n_lon_chunks

    logger.info(f"  Splitting bbox into {n_lat_chunks}x{n_lon_chunks} = {n_lat_chunks * n_lon_chunks} chunks")
    logger.info(f"  Each chunk is ~{lat_step:.3f}° lat × {lon_step:.3f}° lon")

    all_chunks = []
    chunk_num = 0
    total_chunks = n_lat_chunks * n_lon_chunks

    for i in range(n_lat_chunks):
        for j in range(n_lon_chunks):
            chunk_num += 1
            chunk_bbox = {
                'south': bbox['south'] + i * lat_step,
                'north': bbox['south'] + (i + 1) * lat_step,
                'west': bbox['west'] + j * lon_step,
                'east': bbox['west'] + (j + 1) * lon_step,
            }

            logger.info(f"  Fetching chunk {chunk_num}/{total_chunks}...")
            logger.info(f"    Bounds: ({chunk_bbox['south']:.3f}, {chunk_bbox['west']:.3f}) to ({chunk_bbox['north']:.3f}, {chunk_bbox['east']:.3f})")

            try:
                data = mly.images_in_bbox(bbox=chunk_bbox)

                if not data:
                    logger.info(f"    No data in chunk {chunk_num}")
                    continue

                # Parse GeoJSON
                try:
                    geojson_dict = json.loads(data)
                except json.JSONDecodeError as e:
                    if isinstance(data, str) and ('rate limit' in data.lower() or 'throttl' in data.lower()):
                        logger.error(f"    ⚠ Rate limit hit on chunk {chunk_num}")
                        logger.error(f"    Stopping here - retry later with remaining chunks")
                        break
                    else:
                        logger.error(f"    JSON parse error in chunk {chunk_num}: {e}")
                        continue

                if 'features' not in geojson_dict or len(geojson_dict['features']) == 0:
                    logger.info(f"    No features in chunk {chunk_num}")
                    continue

                # Create GeoDataFrame for this chunk
                chunk_gdf = gp.GeoDataFrame.from_features(geojson_dict, crs="EPSG:4326")
                logger.info(f"    Found {len(chunk_gdf):,} images in chunk {chunk_num}")

                # Filter to boundary if available
                if boundary_gdf is not None:
                    initial = len(chunk_gdf)
                    if boundary_gdf.crs is None:
                        boundary_gdf = boundary_gdf.set_crs("EPSG:4326")
                    if boundary_gdf.crs != chunk_gdf.crs:
                        boundary_gdf = boundary_gdf.to_crs(chunk_gdf.crs)

                    chunk_gdf = gp.sjoin(chunk_gdf, boundary_gdf, how='inner', predicate='within')
                    chunk_gdf = chunk_gdf[[col for col in chunk_gdf.columns if not col.startswith('index_')]]
                    logger.info(f"    Kept {len(chunk_gdf):,} within boundary ({len(chunk_gdf)/initial*100:.1f}%)")

                all_chunks.append(chunk_gdf)

                # Log progress
                total_so_far = sum(len(c) for c in all_chunks)
                logger.info(f"    Running total: {total_so_far:,} images from {len(all_chunks)} chunks")

            except Exception as e:
                logger.error(f"    Error fetching chunk {chunk_num}: {e}")
                continue

    if not all_chunks:
        logger.warning(f"  No data collected for {city_name}")
        return None

    # Concatenate all chunks
    logger.info(f"  Combining {len(all_chunks)} chunks...")
    combined_gdf = pd.concat(all_chunks, ignore_index=True)

    # Remove duplicates (images might appear in overlapping chunks)
    if 'id' in combined_gdf.columns:
        initial_count = len(combined_gdf)
        combined_gdf = combined_gdf.drop_duplicates(subset='id')
        logger.info(f"  Removed {initial_count - len(combined_gdf):,} duplicate images")

    logger.info(f"  Final total: {len(combined_gdf):,} unique images")

    return combined_gdf


def download_city_metadata(city_config, output_dir, logger):
    """Download metadata for a single city."""
    logger.info(f"=" * 80)
    logger.info(f"Processing: {city_config['name']}, {city_config['country']}")
    logger.info(f"=" * 80)

    city_name_slug = city_config['name'].lower().replace(' ', '-')
    city_dir = output_dir / city_name_slug
    city_dir.mkdir(parents=True, exist_ok=True)

    metadata_file = city_dir / f"{city_name_slug}_metadata.csv"

    # Check if already exists
    if metadata_file.exists():
        logger.info(f"Metadata already exists at {metadata_file}")
        existing = pd.read_csv(metadata_file)
        logger.info(f"Existing file has {len(existing):,} images")
        response = input(f"Overwrite? (y/n): ")
        if response.lower() != 'y':
            logger.info("Skipping...")
            return

    try:
        # Get city boundary
        logger.info(f"  Getting city boundary...")
        boundary_result = get_city_bbox(city_config)
        bbox = boundary_result['bbox']
        boundary_gdf = boundary_result['boundary']

        logger.info(f"  Using {boundary_result['method']}")
        logger.info(f"  Bounding box: ({bbox['south']:.3f}, {bbox['west']:.3f}) to ({bbox['north']:.3f}, {bbox['east']:.3f})")

        if boundary_gdf is not None:
            area_km2 = boundary_gdf.to_crs(epsg=3857).area.sum() / 1e6
            logger.info(f"  City area: {area_km2:.2f} km²")

        # Set token
        mly.set_access_token(MAPILLARY_TOKEN)

        # Fetch metadata in chunks
        logger.info(f"  Fetching metadata in chunks (this may take 30-60 minutes)...")
        gdf = fetch_metadata_chunked(bbox, boundary_gdf, city_config['name'], logger)

        if gdf is None:
            logger.error(f"Failed to fetch metadata for {city_config['name']}")
            return

        # Extract lat/lon and convert to DataFrame
        gdf['lon'] = gdf.geometry.x
        gdf['lat'] = gdf.geometry.y
        df = pd.DataFrame(gdf.drop(columns='geometry'))

        # Standardize column names
        if 'captured_at' in df.columns:
            df['captured_at'] = pd.to_datetime(df['captured_at'], unit='ms')

        # Save to CSV
        logger.info(f"  Saving to {metadata_file}...")
        df.to_csv(metadata_file, index=False)

        file_size_mb = metadata_file.stat().st_size / (1024 * 1024)
        logger.info(f"✓ Saved {len(df):,} images ({file_size_mb:.1f} MB)")

    except Exception as e:
        logger.error(f"Error processing {city_config['name']}: {e}")
        import traceback
        logger.error(traceback.format_exc())


def main():
    """Main function."""
    output_dir = Path('/home/kieran/Documents/Python/sunny_day_SVI/data/metro_cities_svi')
    output_dir.mkdir(parents=True, exist_ok=True)

    logger = setup_logging(output_dir)

    logger.info("=" * 80)
    logger.info("METADATA DOWNLOAD: Dallas and Los Angeles")
    logger.info("=" * 80)
    logger.info(f"Cities to process: {[c['name'] for c in CITIES]}")
    logger.info("")

    for city in CITIES:
        download_city_metadata(city, output_dir, logger)
        logger.info("")

    logger.info("=" * 80)
    logger.info("COMPLETE")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()
