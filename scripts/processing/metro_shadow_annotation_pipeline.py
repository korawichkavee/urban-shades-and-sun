#!/usr/bin/env python3
# ABOUTME: Annotate all metro areas with shadow data (buildings + trees from OSM)
# ABOUTME: Computes shadow_ratio, dist_to_shade_m, and pedestrian shadow ratios
# ABOUTME: This is Step 1 before bias-corrected analysis
# ABOUTME: WARNING: This takes hours per city - designed for overnight/weekend runs

import sys
import math
import logging
import traceback
import time
from datetime import timezone, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from shapely.ops import unary_union
import osmnx as ox
from tqdm import tqdm

# Add salusshadow to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'data_collection'))
from salusshadow import (
    get_sun,
    estimate_building_height,
    building_shadow,
    tree_shadow_geom,
    shaded_fraction,
    SUN_ELEV_MIN_DEG,
    DEFAULT_BUILDING_HEIGHT_M,
    DEFAULT_TREE_HEIGHT_M,
    DEFAULT_CROWN_RADIUS_M,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
INPUT_DIR = ROOT / 'data' / 'metro_commute_svi_with_utci'
OUTPUT_DIR = ROOT / 'data' / 'metro_commute_svi_with_shadow'
LOG_DIR = ROOT / 'logs' / 'metro_shadow_annotation'

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Parameters
MARGIN_DEG = 0.01
INCLUDE_TREES = True
LOCAL_SHADE_RADIUS_25M = 25.0
LOCAL_SHADE_RADIUS_50M = 50.0
ROAD_WINDOW_M = 50.0
SIDEWALK_WIDTH_M = 1.5
LANE_WIDTH_M = 3.0

# Error handling parameters
MAX_OSM_RETRIES = 3
OSM_RETRY_DELAY_SEC = 10
MAX_POINT_FAILURES_PERCENT = 10.0  # Skip city if >10% of points fail

# Timezone mapping (add more as needed)
CITY_TIMEZONES = {
    'denver': 'America/Denver',
    'salt-lake-city': 'America/Denver',
    'phoenix': 'America/Phoenix',
    'tucson': 'America/Phoenix',
    'minneapolis': 'America/Chicago',
    'st.-louis': 'America/Chicago',
    'evansville': 'America/Chicago',
    'cleveland': 'America/New_York',
    'atlanta': 'America/New_York',
    'columbia': 'America/New_York',
    'louisville': 'America/New_York',
    'boise': 'America/Boise',
    'anchorage': 'America/Anchorage',
    'honolulu': 'Pacific/Honolulu',
}

# Setup logging
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
log_file = LOG_DIR / f'metro_shadow_pipeline_{timestamp}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def fetch_osm_data(bbox, logger):
    """Fetch OSM buildings, trees, and roads for a bounding box with retry logic."""
    logger.info(f'  Fetching OSM data for bbox...')

    for attempt in range(1, MAX_OSM_RETRIES + 1):
        try:
            # Buildings
            logger.info(f'    Downloading buildings... (attempt {attempt}/{MAX_OSM_RETRIES})')
            buildings_gdf = ox.features_from_bbox(
                bbox=bbox,
                tags={'building': True}
            )
            buildings_gdf = buildings_gdf[buildings_gdf.geom_type.isin(['Polygon', 'MultiPolygon'])].copy()
            buildings_gdf = buildings_gdf.to_crs('EPSG:4326')
            logger.info(f'      Found {len(buildings_gdf):,} buildings')

            # Trees (if enabled)
            if INCLUDE_TREES:
                logger.info('    Downloading trees...')
                trees_gdf = ox.features_from_bbox(
                    bbox=bbox,
                    tags={'natural': 'tree'}
                )
                trees_gdf = trees_gdf[trees_gdf.geom_type == 'Point'].copy()
                trees_gdf = trees_gdf.to_crs('EPSG:4326')
                logger.info(f'      Found {len(trees_gdf):,} trees')
            else:
                trees_gdf = gpd.GeoDataFrame()

            # Roads
            logger.info('    Downloading road network...')
            G = ox.graph_from_bbox(bbox=bbox, network_type='all')
            roads_gdf = ox.graph_to_gdfs(G, nodes=False)
            roads_gdf = roads_gdf.reset_index(drop=True)
            logger.info(f'      Found {len(roads_gdf):,} road segments')

            return buildings_gdf, trees_gdf, roads_gdf

        except Exception as e:
            logger.warning(f'    Attempt {attempt} failed: {e}')
            if attempt < MAX_OSM_RETRIES:
                logger.info(f'    Retrying in {OSM_RETRY_DELAY_SEC} seconds...')
                time.sleep(OSM_RETRY_DELAY_SEC)
            else:
                logger.error(f'    Failed after {MAX_OSM_RETRIES} attempts')
                return None, None, None

    return None, None, None


def compute_shadow_union(buildings_gdf, trees_gdf, datetime_utc, logger):
    """Compute union of all building and tree shadows for a given datetime."""
    lat_center = (buildings_gdf.total_bounds[1] + buildings_gdf.total_bounds[3]) / 2
    lon_center = (buildings_gdf.total_bounds[0] + buildings_gdf.total_bounds[2]) / 2

    sun = get_sun(datetime_utc, lat_center, lon_center)

    if sun['elevation'] < SUN_ELEV_MIN_DEG:
        return None  # Sun too low, no meaningful shadows

    shadow_polys = []

    # Building shadows
    for _, row in buildings_gdf.iterrows():
        geom = row.geometry
        height = estimate_building_height(row)
        shadow = building_shadow(geom, height, sun['azimuth'], sun['elevation'])
        if shadow is not None:
            shadow_polys.append(shadow)

    # Tree shadows
    if INCLUDE_TREES and len(trees_gdf) > 0:
        for _, row in trees_gdf.iterrows():
            pt = row.geometry
            # tree_shadow_geom(geom, h_m, crown_r_m, az_deg, elev_deg)
            shadow = tree_shadow_geom(
                pt,
                DEFAULT_TREE_HEIGHT_M,
                DEFAULT_CROWN_RADIUS_M,
                sun['azimuth'],
                sun['elevation']
            )
            if shadow is not None:
                shadow_polys.append(shadow)

    if not shadow_polys:
        return None

    return unary_union(shadow_polys)


def annotate_city(city_name, timezone_str):
    """Annotate a single city with shadow data."""
    city_start_time = time.time()

    logger.info('')
    logger.info('=' * 70)
    logger.info(f'ANNOTATING: {city_name}')
    logger.info('=' * 70)

    # Find input CSV
    city_input_dir = INPUT_DIR / city_name
    csv_files = list(city_input_dir.glob('*.csv'))

    if not csv_files:
        logger.warning(f'{city_name}: No CSV files found')
        return False

    input_csv = csv_files[0]
    logger.info(f'  Input: {input_csv}')

    # Load data
    logger.info('  Loading data...')
    df = pd.read_csv(input_csv, low_memory=False)
    logger.info(f'    Loaded {len(df):,} rows')

    # Parse datetime
    df['datetime-local'] = pd.to_datetime(df['datetime-local'])

    # Get bounding box
    bounds = (
        df['lon'].min() - MARGIN_DEG,
        df['lat'].min() - MARGIN_DEG,
        df['lon'].max() + MARGIN_DEG,
        df['lat'].max() + MARGIN_DEG
    )
    logger.info(f'  Bounding box: ({bounds[1]:.4f}, {bounds[0]:.4f}) to ({bounds[3]:.4f}, {bounds[2]:.4f})')

    # Fetch OSM data
    buildings_gdf, trees_gdf, roads_gdf = fetch_osm_data(bounds, logger)

    if buildings_gdf is None:
        logger.error(f'{city_name}: Failed to fetch OSM data')
        return False

    # Project to local UTM
    utm_crs = buildings_gdf.estimate_utm_crs()
    buildings_utm = buildings_gdf.to_crs(utm_crs)
    if INCLUDE_TREES and len(trees_gdf) > 0:
        trees_utm = trees_gdf.to_crs(utm_crs)
    else:
        trees_utm = gpd.GeoDataFrame()
    roads_utm = roads_gdf.to_crs(utm_crs)
    logger.info(f'  Projected to {utm_crs}')

    # Get unique date+hour combinations
    df['date_hour'] = df['datetime-local'].dt.floor('H')
    unique_datetimes = df['date_hour'].drop_duplicates().sort_values()
    logger.info(f'  Unique date+hour combinations: {len(unique_datetimes):,}')

    # Compute shadow union for each date+hour
    logger.info('  Computing shadow unions...')
    shadow_cache = {}

    for dt_local in tqdm(unique_datetimes, desc='  Shadow unions'):
        # Convert to UTC
        dt_utc = dt_local.tz_localize(timezone_str).astimezone(timezone.utc)

        shadow_union = compute_shadow_union(buildings_utm, trees_utm, dt_utc, logger)
        shadow_cache[dt_local] = shadow_union

    logger.info(f'    Computed {len(shadow_cache):,} shadow unions')

    # Annotate each row
    logger.info('  Annotating rows with shadow metrics...')

    shadow_ratio_arr = []
    dist_to_shade_arr = []
    local_shade_25m_arr = []
    local_shade_50m_arr = []
    sun_azimuth_arr = []
    sun_elevation_arr = []

    gdf = gpd.GeoDataFrame(
        df, geometry=gpd.points_from_xy(df['lon'], df['lat']), crs='EPSG:4326'
    )
    gdf_utm = gdf.to_crs(utm_crs)

    failed_points = 0
    for i, row in tqdm(gdf_utm.iterrows(), total=len(gdf_utm), desc='  Annotating'):
        dt_local = df.loc[i, 'date_hour']
        shadow_union = shadow_cache.get(dt_local)

        if shadow_union is None:
            # Sun too low
            shadow_ratio_arr.append(np.nan)
            dist_to_shade_arr.append(np.nan)
            local_shade_25m_arr.append(np.nan)
            local_shade_50m_arr.append(np.nan)
            sun_azimuth_arr.append(np.nan)
            sun_elevation_arr.append(np.nan)
            continue

        pt = row.geometry

        # Get sun position
        dt_utc = dt_local.tz_localize(timezone_str).astimezone(timezone.utc)
        sun = get_sun(dt_utc, row['lat'], row['lon'])
        sun_azimuth_arr.append(sun['azimuth'])
        sun_elevation_arr.append(sun['elevation'])

        # Find nearest road
        try:
            result = roads_utm.sindex.nearest(pt, return_all=False)
            tree_idx = result[1][0] if hasattr(result[1], '__len__') else result[1]
            nearest_road = roads_utm.iloc[int(tree_idx)]
            road_geom = nearest_road.geometry
        except Exception as e:
            failed_points += 1
            if failed_points <= 3:  # Only log first 3 failures
                logger.warning(f'    Point {i} failed (nearest road lookup): {e}')
            shadow_ratio_arr.append(np.nan)
            dist_to_shade_arr.append(np.nan)
            local_shade_25m_arr.append(np.nan)
            local_shade_50m_arr.append(np.nan)
            continue

        # Shadow ratio (road centerline)
        try:
            sr = shaded_fraction(road_geom, shadow_union)
            shadow_ratio_arr.append(sr)
        except Exception as e:
            failed_points += 1
            if failed_points <= 3:
                logger.warning(f'    Point {i} failed (shadow fraction): {e}')
            shadow_ratio_arr.append(np.nan)

        # Distance to shade
        try:
            if shadow_union.contains(pt):
                dist_to_shade_arr.append(0.0)
            else:
                dist_to_shade_arr.append(pt.distance(shadow_union))
        except Exception as e:
            failed_points += 1
            if failed_points <= 3:
                logger.warning(f'    Point {i} failed (distance to shade): {e}')
            dist_to_shade_arr.append(np.nan)

        # Local shade (circular buffers)
        try:
            circle_25m = pt.buffer(LOCAL_SHADE_RADIUS_25M)
            circle_50m = pt.buffer(LOCAL_SHADE_RADIUS_50M)
            local_shade_25m_arr.append(shaded_fraction(circle_25m, shadow_union))
            local_shade_50m_arr.append(shaded_fraction(circle_50m, shadow_union))
        except Exception as e:
            failed_points += 1
            if failed_points <= 3:
                logger.warning(f'    Point {i} failed (local shade): {e}')
            local_shade_25m_arr.append(np.nan)
            local_shade_50m_arr.append(np.nan)

    # Check failure rate
    failure_rate = (failed_points / len(gdf_utm)) * 100
    logger.info(f'  Point annotation failure rate: {failure_rate:.2f}% ({failed_points:,}/{len(gdf_utm):,})')

    if failure_rate > MAX_POINT_FAILURES_PERCENT:
        logger.error(f'{city_name}: ✗ Failure rate {failure_rate:.2f}% exceeds threshold {MAX_POINT_FAILURES_PERCENT}%')
        logger.error(f'  Skipping city due to excessive failures')
        return False

    # Add columns
    df['shadow_ratio'] = shadow_ratio_arr
    df['dist_to_shade_m'] = dist_to_shade_arr
    df['local_shade_25m'] = local_shade_25m_arr
    df['local_shade_50m'] = local_shade_50m_arr
    df['sun_azimuth'] = sun_azimuth_arr
    df['sun_elevation'] = sun_elevation_arr

    # Drop temporary column
    df = df.drop(columns=['date_hour'])

    # Save
    city_output_dir = OUTPUT_DIR / city_name
    city_output_dir.mkdir(parents=True, exist_ok=True)
    output_csv = city_output_dir / f'{city_name}_svi_with_shadow.csv'

    df.to_csv(output_csv, index=False)

    # Time tracking
    city_elapsed = time.time() - city_start_time
    elapsed_str = str(timedelta(seconds=int(city_elapsed)))

    logger.info(f'  Saved {len(df):,} rows -> {output_csv}')
    logger.info(f'{city_name}: ✓ Complete in {elapsed_str}')

    return True


def main():
    """Main pipeline."""
    pipeline_start_time = time.time()

    logger.info('=' * 70)
    logger.info('METRO SHADOW ANNOTATION PIPELINE')
    logger.info('=' * 70)

    # Get list of cities
    cities = sorted([d.name for d in INPUT_DIR.iterdir() if d.is_dir()])
    logger.info(f'Found {len(cities)} cities to process')
    logger.info(f'Start time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

    success_count = 0
    fail_count = 0
    city_times = []

    for i, city_name in enumerate(cities, 1):
        timezone_str = CITY_TIMEZONES.get(city_name)

        if timezone_str is None:
            logger.warning(f'{city_name}: No timezone mapping found, skipping')
            fail_count += 1
            continue

        logger.info(f'\nProcessing {city_name} ({i}/{len(cities)}) - Timezone: {timezone_str}')

        city_start = time.time()
        try:
            success = annotate_city(city_name, timezone_str)
            if success:
                success_count += 1
                city_elapsed = time.time() - city_start
                city_times.append(city_elapsed)

                # Estimate remaining time
                if len(city_times) >= 2:
                    avg_time_per_city = np.mean(city_times)
                    remaining_cities = len(cities) - i
                    estimated_remaining_sec = avg_time_per_city * remaining_cities
                    eta = datetime.now() + timedelta(seconds=estimated_remaining_sec)
                    logger.info(f'  Estimated completion: {eta.strftime("%Y-%m-%d %H:%M:%S")} '
                                f'({str(timedelta(seconds=int(estimated_remaining_sec)))} remaining)')
            else:
                fail_count += 1
        except Exception as e:
            logger.error(f'{city_name}: ✗ Failed with error: {e}')
            logger.error(traceback.format_exc())
            fail_count += 1

    # Final summary
    pipeline_elapsed = time.time() - pipeline_start_time
    pipeline_elapsed_str = str(timedelta(seconds=int(pipeline_elapsed)))

    logger.info('')
    logger.info('=' * 70)
    logger.info('PIPELINE COMPLETE')
    logger.info(f'Total time: {pipeline_elapsed_str}')
    logger.info(f'Success: {success_count}/{len(cities)}')
    logger.info(f'Failed: {fail_count}/{len(cities)}')
    if city_times:
        logger.info(f'Average time per city: {str(timedelta(seconds=int(np.mean(city_times))))}')
    logger.info(f'Output directory: {OUTPUT_DIR}')
    logger.info(f'Log file: {log_file}')
    logger.info('=' * 70)


if __name__ == '__main__':
    main()
