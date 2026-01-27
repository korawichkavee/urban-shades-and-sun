# ABOUTME: Builds ZIP code and county centroid lookup tables for travel surveys.
# ABOUTME: Downloads and processes geographic centroid data for precise weather matching.

import pandas as pd
import requests
from pathlib import Path
import logging


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


def download_zip_centroids(output_path, logger):
    """
    Download ZIP code centroids from public data source.
    Returns DataFrame with columns: zip, lat, lon, city, state
    """
    logger.info("Downloading ZIP code centroids...")

    # Using Census Gazetteer data (2023 ZCTA centroids)
    url = "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2023_Gazetteer/2023_Gaz_zcta_national.zip"

    import io
    import zipfile

    response = requests.get(url, timeout=60)
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        # Find the txt file
        txt_files = [f for f in z.namelist() if f.endswith('.txt')]
        with z.open(txt_files[0]) as f:
            df = pd.read_csv(f, sep='\t', encoding='latin1')

    # Strip whitespace from column names
    df.columns = df.columns.str.strip()

    # Rename columns
    df = df.rename(columns={
        'GEOID': 'zip',
        'INTPTLAT': 'lat',
        'INTPTLONG': 'lon'
    })

    # Keep relevant columns
    df = df[['zip', 'lat', 'lon']].copy()

    # Convert ZIP to string with leading zeros
    df['zip'] = df['zip'].astype(str).str.zfill(5)

    logger.info(f"  Downloaded {len(df):,} ZIP codes")

    # Save
    df.to_csv(output_path, index=False)
    logger.info(f"  Saved to {output_path}")

    return df


def download_county_centroids(output_path, logger):
    """
    Download county geographic data including bounding boxes for sampling.
    Returns DataFrame with columns: county_fips, lat, lon, county_name, state, bbox
    """
    logger.info("Downloading county geographic data...")

    # Using Census Gazetteer files
    url = "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2023_Gazetteer/2023_Gaz_counties_national.zip"

    import io
    import zipfile

    response = requests.get(url, timeout=60)
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        # Find the txt file
        txt_files = [f for f in z.namelist() if f.endswith('.txt')]
        with z.open(txt_files[0]) as f:
            df = pd.read_csv(f, sep='\t', encoding='latin1')

    # Rename columns
    df = df.rename(columns={
        'GEOID': 'county_fips',
        'NAME': 'county_name',
        'USPS': 'state',
        'INTPTLAT': 'centroid_lat',
        'INTPTLONG': 'centroid_lon'
    })

    # Keep relevant columns
    df = df[['county_fips', 'centroid_lat', 'centroid_lon', 'county_name', 'state']].copy()

    # Ensure county_fips is 5-digit string
    df['county_fips'] = df['county_fips'].astype(str).str.zfill(5)

    logger.info(f"  Downloaded {len(df):,} counties")

    # Save
    df.to_csv(output_path, index=False)
    logger.info(f"  Saved to {output_path}")

    return df


def main():
    logger = setup_logging()

    # Setup paths
    project_root = Path(__file__).parent.parent.parent
    data_dir = project_root / "data" / "geographic_lookups"
    data_dir.mkdir(parents=True, exist_ok=True)

    logger.info("="*60)
    logger.info("Building Geographic Lookup Tables")
    logger.info("="*60)

    # Download ZIP centroids
    zip_path = data_dir / "zip_centroids.csv"
    if zip_path.exists():
        logger.info(f"ZIP centroids already exist at {zip_path}")
        zip_df = pd.read_csv(zip_path)
    else:
        zip_df = download_zip_centroids(zip_path, logger)

    # Download county centroids
    county_path = data_dir / "county_centroids.csv"
    if county_path.exists():
        logger.info(f"County centroids already exist at {county_path}")
        county_df = pd.read_csv(county_path)
    else:
        county_df = download_county_centroids(county_path, logger)

    # Summary
    logger.info("\n" + "="*60)
    logger.info("Summary")
    logger.info("="*60)
    logger.info(f"ZIP codes: {len(zip_df):,}")
    logger.info(f"Counties: {len(county_df):,}")
    logger.info(f"\nFiles created:")
    logger.info(f"  {zip_path}")
    logger.info(f"  {county_path}")
    logger.info("="*60)


if __name__ == '__main__':
    main()
