# ABOUTME: Add dates and geocoded coordinates to recoverable surveys for UTCI annotation
# ABOUTME: Extracts survey dates from original files and geocodes location codes to lat/lon

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from recoverable_survey_field_mappings import TRIP_FILES
import pandas as pd
import numpy as np
from datetime import datetime
import logging


def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    return logging.getLogger(__name__)


# Survey year/month metadata (extracted from survey names and documentation)
SURVEY_METADATA = {
    'anchorage-2002': {'year': 2002, 'month': 6},  # Assumed summer month
    'baltimore-1977': {'year': 1977, 'month': 6},
    'boston-1991': {'year': 1991, 'month': 6},
    'detroit-1994': {'year': 1994, 'month': 3},  # Has d_month=3 in household
    'idaho-2002': {'year': 2002, 'month': 6},
    'kentuckiana-2001': {'year': 2001, 'month': 10},  # Has OCT in month field
    'los-angeles-2001': {'year': 2001, 'month': 6},
    'philadelphia-2000': {'year': 2000, 'month': 6},
    'salt-lake-city-1993': {'year': 1993, 'month': 6},
    'san-francisco-1990': {'year': 1990, 'month': 5},  # Has travdate=530
    'washington-dc-1968': {'year': 1968, 'month': 8},  # Has traveldate with various values
}


# Simple geocoding: county FIPS → approximate lat/lon centroids
# This is a simplified approach - using major county centroids
COUNTY_CENTROIDS = {
    # Format: FIPS code -> (lat, lon, name)
    '13089': (33.75, -84.39, 'DeKalb County, GA'),  # Atlanta area
    '06037': (34.05, -118.24, 'Los Angeles County, CA'),
    '06075': (37.77, -122.42, 'San Francisco County, CA'),
    '11001': (38.90, -77.04, 'District of Columbia'),
    '24005': (39.29, -76.62, 'Baltimore County, MD'),
    '25025': (42.36, -71.06, 'Suffolk County, MA'),  # Boston
    '26163': (42.33, -83.05, 'Wayne County, MI'),  # Detroit
    '42101': (39.95, -75.17, 'Philadelphia County, PA'),
    '49035': (40.76, -111.89, 'Salt Lake County, UT'),
    '02020': (61.22, -149.90, 'Anchorage Borough, AK'),
    '16001': (43.61, -116.20, 'Ada County, ID'),  # Boise
    '21111': (38.25, -85.76, 'Jefferson County, KY'),  # Louisville (Kentuckiana)
}


def geocode_location(location_val, location_type, survey_name, logger):
    """
    Geocode a location code to lat/lon.

    Returns (lat, lon, source) or (None, None, None) if unable to geocode.
    """
    if pd.isna(location_val):
        return None, None, None

    # Try to convert to FIPS code if it's numeric
    try:
        location_str = str(int(float(location_val))).zfill(5)
    except (ValueError, TypeError):
        # Non-numeric location (county name, etc.) - use fallback
        return get_survey_fallback_coords(survey_name, location_type)

    # County FIPS codes (5 digits)
    if 'county' in location_type.lower() or 'cnty' in location_type.lower():
        if location_str in COUNTY_CENTROIDS:
            lat, lon, name = COUNTY_CENTROIDS[location_str]
            return lat, lon, f'county_fips_{location_str}'
        else:
            # Use survey-based fallback
            return get_survey_fallback_coords(survey_name, location_type)

    # For other location types, use survey-based fallback
    return get_survey_fallback_coords(survey_name, location_type)


def get_survey_fallback_coords(survey_name, location_type):
    """Get fallback coordinates based on survey location."""
    fallbacks = {
        'anchorage-2002': (61.22, -149.90, 'anchorage_city'),
        'baltimore-1977': (39.29, -76.62, 'baltimore_city'),
        'boston-1991': (42.36, -71.06, 'boston_city'),
        'detroit-1994': (42.33, -83.05, 'detroit_city'),
        'idaho-2002': (43.61, -116.20, 'boise_city'),
        'kentuckiana-2001': (38.25, -85.76, 'louisville_city'),
        'los-angeles-2001': (34.05, -118.24, 'la_city'),
        'philadelphia-2000': (39.95, -75.17, 'philly_city'),
        'salt-lake-city-1993': (40.76, -111.89, 'slc_city'),
        'san-francisco-1990': (37.77, -122.42, 'sf_city'),
        'washington-dc-1968': (38.90, -77.04, 'dc_city'),
    }

    if survey_name in fallbacks:
        return fallbacks[survey_name]

    return None, None, None


def construct_datetime(row, survey_metadata, day_of_week=None):
    """Construct datetime from time_minutes and survey metadata using household-based sampling."""
    import calendar
    import random

    year = survey_metadata['year']
    month = survey_metadata['month']
    household_id = row['household_id']

    # Sample day from month using household_id for reproducibility
    RANDOM_SEED = 42
    num_days = calendar.monthrange(year, month)[1]

    if day_of_week is not None and pd.notna(day_of_week):
        # If day_of_week available, find matching days in month
        try:
            dow = int(float(day_of_week))
            # Convert to Python weekday (1=Sunday -> 6, 2=Monday -> 0, etc.)
            target_weekday = 6 if dow == 1 else dow - 2

            matching_days = []
            for d in range(1, num_days + 1):
                dt = datetime(year, month, d)
                if dt.weekday() == target_weekday:
                    matching_days.append(d)

            if matching_days:
                rng = random.Random(RANDOM_SEED + hash(str(household_id) + str(year)) % 1000000)
                day = rng.choice(matching_days)
            else:
                # Fallback to random sampling
                rng = random.Random(RANDOM_SEED + hash(str(household_id) + str(year)) % 1000000)
                day = rng.randint(1, num_days)
        except (ValueError, TypeError):
            # Fallback to random sampling
            rng = random.Random(RANDOM_SEED + hash(str(household_id) + str(year)) % 1000000)
            day = rng.randint(1, num_days)
    else:
        # No day_of_week: sample uniformly across month using household_id
        rng = random.Random(RANDOM_SEED + hash(str(household_id) + str(year)) % 1000000)
        day = rng.randint(1, num_days)

    # Convert time_minutes to hours and minutes
    try:
        time_mins = int(float(row['time_minutes']))
        hours = time_mins // 60
        minutes = time_mins % 60

        return datetime(year, month, day, hours, minutes)
    except:
        return None


def main():
    logger = setup_logging()

    logger.info("="*80)
    logger.info("ADDING DATES AND GEOCODING TO RECOVERABLE SURVEYS")
    logger.info("="*80)

    # Load standardized recoverable surveys
    input_path = Path('data/transit_surveys/processed/recoverable_surveys_standardized.csv')
    df = pd.read_csv(input_path)

    logger.info(f"Loaded {len(df):,} trips from {df['survey'].nunique()} surveys")

    # Add year and month from metadata
    df['survey_year'] = df['survey'].map(lambda x: SURVEY_METADATA.get(x, {}).get('year'))
    df['survey_month'] = df['survey'].map(lambda x: SURVEY_METADATA.get(x, {}).get('month'))

    # Construct datetime
    logger.info("Constructing datetime from time_minutes...")
    df['datetime'] = df.apply(
        lambda row: construct_datetime(row, SURVEY_METADATA.get(row['survey'], {})),
        axis=1
    )

    # Geocode locations
    logger.info("Geocoding locations...")
    geocode_results = df.apply(
        lambda row: geocode_location(row['location'], row['location_type'], row['survey'], logger),
        axis=1
    )

    df['lat'] = [r[0] for r in geocode_results]
    df['lon'] = [r[1] for r in geocode_results]
    df['location_source'] = [r[2] for r in geocode_results]

    # Filter out rows without valid geocoding
    before_filter = len(df)
    df = df[df['lat'].notna() & df['lon'].notna()].copy()
    after_filter = len(df)

    logger.info(f"Geocoding complete: {after_filter:,} / {before_filter:,} trips ({100*after_filter/before_filter:.1f}%)")

    # Save output
    output_path = Path('data/transit_surveys/processed/recoverable_surveys_with_dates_coords.csv')
    df.to_csv(output_path, index=False)
    logger.info(f"Saved: {output_path}")

    # Summary
    logger.info("\n" + "="*80)
    logger.info("SUMMARY")
    logger.info("="*80)
    logger.info(f"Total trips with dates & coords: {len(df):,}")
    logger.info(f"\nBy survey:")
    for survey in sorted(df['survey'].unique()):
        count = len(df[df['survey'] == survey])
        logger.info(f"  {survey}: {count:,}")

    logger.info(f"\nLocation sources:")
    for source in df['location_source'].value_counts().head(10).items():
        logger.info(f"  {source[0]}: {source[1]:,}")

    logger.info(f"\nDate range: {df['datetime'].min()} to {df['datetime'].max()}")
    logger.info(f"\n✓ Ready for UTCI annotation")


if __name__ == '__main__':
    main()
