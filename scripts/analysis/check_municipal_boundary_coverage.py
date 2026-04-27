#!/usr/bin/env python3
"""
Check how many SVI images are outside municipal boundaries.

Compares SVI metadata against OSM city boundaries for NYC and Seattle.
"""

from pathlib import Path
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import osmnx as ox
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Paths
ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / 'data/metro_commute_svi'
OUTPUT_DIR = ROOT / 'outputs/analysis'

CITIES = {
    'new-york-city': {
        'file': DATA_DIR / 'new-york-city/new-york-city_svi.csv',
        'osm_query': 'New York City, New York, USA',
        'display_name': 'New York City'
    },
    'seattle': {
        'file': DATA_DIR / 'seattle/seattle_svi.csv',
        'osm_query': 'Seattle, Washington, USA',
        'display_name': 'Seattle'
    }
}


def get_city_boundary(city_name: str, osm_query: str) -> gpd.GeoDataFrame:
    """
    Fetch municipal boundary from OpenStreetMap.

    Args:
        city_name: City name for caching
        osm_query: OSM query string

    Returns:
        GeoDataFrame with city boundary polygon
    """
    logger.info(f"Fetching OSM boundary for {city_name}...")

    try:
        # Try to get city boundary
        gdf = ox.geocode_to_gdf(osm_query)
        logger.info(f"  ✓ Retrieved boundary for {city_name}")
        logger.info(f"  Boundary type: {gdf.geometry.iloc[0].geom_type}")
        logger.info(f"  Area: {gdf.geometry.iloc[0].area:.6f} deg²")
        return gdf
    except Exception as e:
        logger.error(f"  ✗ Failed to fetch boundary: {e}")
        return None


def check_boundary_coverage(city_key: str, config: dict, sample_size: int = None) -> dict:
    """
    Check what percentage of images fall within municipal boundary.

    Args:
        city_key: City identifier
        config: City configuration dict
        sample_size: Optional - sample N images for faster testing

    Returns:
        Dictionary with coverage statistics
    """
    logger.info(f"\nProcessing {config['display_name']}...")
    logger.info("=" * 80)

    # Load SVI metadata
    logger.info(f"Loading metadata from {config['file']}...")

    # Load with sampling if requested
    if sample_size:
        # Count total rows first
        total_rows = sum(1 for _ in open(config['file'])) - 1  # -1 for header
        skip_rows = range(1, total_rows + 1)
        keep_rows = set(range(0, total_rows, total_rows // sample_size))
        skip_rows = [i for i in skip_rows if i not in keep_rows]

        df = pd.read_csv(config['file'], skiprows=skip_rows)
        logger.info(f"  Loaded {len(df):,} sampled images (from {total_rows:,} total)")
    else:
        df = pd.read_csv(config['file'])
        logger.info(f"  Loaded {len(df):,} images")

    # Check for required columns (handle both lon/lat and longitude/latitude)
    lon_col = 'lon' if 'lon' in df.columns else 'longitude'
    lat_col = 'lat' if 'lat' in df.columns else 'latitude'

    if lon_col not in df.columns or lat_col not in df.columns:
        logger.error(f"  ✗ Missing coordinate columns. Found: {df.columns.tolist()}")
        return None

    # Get municipal boundary
    boundary_gdf = get_city_boundary(config['display_name'], config['osm_query'])
    if boundary_gdf is None:
        return None

    boundary_geom = boundary_gdf.geometry.iloc[0]

    # Convert image coordinates to GeoDataFrame
    logger.info("Converting image coordinates to geometry...")
    geometry = [Point(lon, lat) for lon, lat in zip(df[lon_col], df[lat_col])]
    images_gdf = gpd.GeoDataFrame(df, geometry=geometry, crs='EPSG:4326')

    # Ensure same CRS
    if boundary_gdf.crs != images_gdf.crs:
        logger.info(f"Reprojecting boundary from {boundary_gdf.crs} to {images_gdf.crs}")
        boundary_gdf = boundary_gdf.to_crs(images_gdf.crs)
        boundary_geom = boundary_gdf.geometry.iloc[0]

    # Check which images are within boundary
    logger.info("Checking which images fall within municipal boundary...")
    within_boundary = images_gdf.geometry.within(boundary_geom)

    n_total = len(df)
    n_inside = within_boundary.sum()
    n_outside = n_total - n_inside
    pct_inside = (n_inside / n_total) * 100
    pct_outside = (n_outside / n_total) * 100

    # Add boundary classification to original dataframe
    df['in_municipal_boundary'] = within_boundary

    # Save annotated metadata back to file
    if sample_size is None:  # Only save if processing full dataset
        output_file = config['file'].parent / f"{config['file'].stem}_boundary_annotated.csv"
        logger.info(f"Saving boundary-annotated metadata to {output_file}...")
        df.to_csv(output_file, index=False)
        logger.info(f"  ✓ Saved {len(df):,} records with boundary classification")

    results = {
        'city': config['display_name'],
        'total_images': n_total,
        'images_inside': n_inside,
        'images_outside': n_outside,
        'pct_inside': pct_inside,
        'pct_outside': pct_outside,
        'boundary_area_deg2': boundary_geom.area,
        'sampled': sample_size is not None,
        'annotated_file': output_file if sample_size is None else None
    }

    logger.info(f"\nResults for {config['display_name']}:")
    logger.info(f"  Total images: {n_total:,}")
    logger.info(f"  Inside boundary: {n_inside:,} ({pct_inside:.1f}%)")
    logger.info(f"  Outside boundary: {n_outside:,} ({pct_outside:.1f}%)")

    return results


def main():
    """Main execution."""
    logger.info("MUNICIPAL BOUNDARY COVERAGE ANALYSIS")
    logger.info("=" * 80)
    logger.info("Checking SVI image coverage within OSM city boundaries")
    logger.info("")

    # Process both cities with full data (no sampling)
    sample_size = None  # Process all images

    all_results = []

    for city_key, config in CITIES.items():
        if not config['file'].exists():
            logger.warning(f"Skipping {city_key} - file not found: {config['file']}")
            continue

        results = check_boundary_coverage(city_key, config, sample_size=sample_size)
        if results:
            all_results.append(results)

    # Create summary DataFrame
    if all_results:
        summary_df = pd.DataFrame(all_results)

        # Save results
        output_file = OUTPUT_DIR / 'municipal_boundary_coverage.csv'
        summary_df.to_csv(output_file, index=False)
        logger.info(f"\n✓ Saved results to {output_file}")

        # Print summary table
        logger.info("\n" + "=" * 80)
        logger.info("SUMMARY")
        logger.info("=" * 80)
        print(summary_df.to_string(index=False))

        # Total wastage
        total_images = summary_df['total_images'].sum()
        total_outside = summary_df['images_outside'].sum()
        overall_pct_outside = (total_outside / total_images) * 100

        logger.info(f"\nOVERALL:")
        logger.info(f"  Total images (sampled): {total_images:,}")
        logger.info(f"  Outside boundaries: {total_outside:,} ({overall_pct_outside:.1f}%)")

        if sample_size:
            logger.info(f"\nNOTE: These are estimates based on {sample_size:,} sampled images per city")
            logger.info(f"      Run without sampling for exact counts (will take longer)")


if __name__ == '__main__':
    main()
