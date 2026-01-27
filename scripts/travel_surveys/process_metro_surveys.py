# ABOUTME: Process metro travel surveys with geographic sampling and UTCI annotation.
# ABOUTME: Aggregates all metro surveys into standardized format with precise locations.

import sys
from pathlib import Path

# Add utils and other modules to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'utils'))
from enhanced_utci import get_enhanced_utci_data

# Add geographic sampler to path
sys.path.insert(0, str(Path(__file__).parent))
from geographic_sampler import GeographicSampler

import pandas as pd
import logging
from datetime import datetime, timedelta
import calendar
import random
import numpy as np
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed


# Missing value codes (commonly used in travel surveys)
MISSING_CODES = [
    -1, -7, -8, -9, -99, -999, -9999, -99999, -999999, -9999999,
    99, 999, 9999, 99999, 999999, 9999999,
    '', ' ', 'NA', 'na', 'N/A', 'n/a', None
]

RANDOM_SEED = 42


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


def is_missing(value):
    """Check if a value is a missing/sentinel value."""
    if pd.isna(value):
        return True
    if value in MISSING_CODES:
        return True
    if isinstance(value, str) and value.strip() in ['', 'NA', 'N/A']:
        return True
    return False


def parse_time_field(time_val):
    """
    Parse time field (HHMM format like 1340 = 13:40).
    Returns hour and minute, or None if invalid.
    """
    if is_missing(time_val):
        return None, None

    try:
        time_int = int(time_val)
        hour = time_int // 100
        minute = time_int % 100

        if 0 <= hour < 24 and 0 <= minute < 60:
            return hour, minute
    except (ValueError, TypeError):
        pass

    return None, None


def infer_survey_year_month(survey_name):
    """
    Infer survey year and month from directory name.
    Returns (year, month) or (None, None) if unable to parse.
    """
    parts = survey_name.split('-')

    # Extract year from name (e.g., 'atlanta-2001' -> 2001)
    year = None
    for part in parts:
        if part.isdigit() and len(part) == 4 and 1900 <= int(part) <= 2100:
            year = int(part)
            break

    # Default to mid-year (June) if no month information
    month = 6

    return year, month


def generate_trip_datetime(survey_year, survey_month, day_of_week, hour, minute, household_id, seed=RANDOM_SEED):
    """
    Generate trip datetime using survey period and day of week.

    Args:
        survey_year: Year of survey
        survey_month: Month of survey (or representative month)
        day_of_week: Day of week (1=Sunday, 2=Monday, ..., 7=Saturday) or None
        hour: Hour of day (0-23)
        minute: Minute (0-59)
        household_id: Household ID for reproducible variation
        seed: Random seed base

    Returns:
        datetime object or None
    """
    if not all([survey_year, survey_month, hour is not None, minute is not None]):
        return None

    # If we have day of week, select matching day from month
    if day_of_week is not None and 1 <= day_of_week <= 7:
        # Convert survey format (1=Sunday) to Python weekday (0=Monday)
        if day_of_week == 1:
            target_weekday = 6  # Sunday
        else:
            target_weekday = day_of_week - 2

        # Find all matching days in month
        num_days = calendar.monthrange(survey_year, survey_month)[1]
        matching_days = []
        for day in range(1, num_days + 1):
            try:
                dt = datetime(survey_year, survey_month, day)
                if dt.weekday() == target_weekday:
                    matching_days.append(day)
            except ValueError:
                continue

        if matching_days:
            # Select day reproducibly using household ID
            rng = random.Random(seed + hash(str(household_id) + str(survey_year) + str(survey_month)) % 1000000)
            day = rng.choice(matching_days)
        else:
            # Fallback to mid-month
            day = 15
    else:
        # No day of week info, use mid-month
        day = 15

    try:
        return datetime(survey_year, survey_month, day, hour, minute)
    except ValueError:
        return None


def identify_walking_modes(row):
    """
    Identify if trip involves walking.
    Returns (is_walk_only, contains_walk)

    Mode codes vary by survey, but typically:
    - 1 = walk
    - Other codes for various transit modes
    """
    mode = row.get('mode')

    # Check primary mode
    is_walk = False
    if not is_missing(mode):
        try:
            mode_int = int(mode)
            # Mode 1 is typically walk in most surveys
            if mode_int == 1:
                is_walk = True
        except (ValueError, TypeError):
            pass

    # For now, walk_only = contains_walk (we'd need mode chain data for contains_walk)
    return is_walk, is_walk


def load_survey(survey_dir, logger):
    """
    Load a single metro survey.

    Returns DataFrame with standardized columns or None if unable to load.
    """
    survey_name = survey_dir.name
    data_file = survey_dir / "data" / "survey_data.csv"

    if not data_file.exists():
        logger.warning(f"  No survey_data.csv found for {survey_name}")
        return None

    try:
        df = pd.read_csv(data_file, low_memory=False)
        logger.info(f"  Loaded {survey_name}: {len(df):,} rows")
        return df, survey_name
    except Exception as e:
        logger.error(f"  Error loading {survey_name}: {e}")
        return None


def standardize_survey(df, survey_name, logger):
    """
    Standardize a survey to common format.

    Returns DataFrame with columns:
    - survey
    - household_id
    - person_id
    - day_of_week (if available)
    - hour, minute
    - mode
    - county, zip
    - walk_only, contains_walk
    """
    rows = []

    # Infer survey period
    survey_year, survey_month = infer_survey_year_month(survey_name)

    for idx, row in df.iterrows():
        # Extract household ID
        household_id = row.get('sampno') or row.get('sampn') or row.get('hhid')
        if is_missing(household_id):
            continue

        # Extract person ID
        person_id = row.get('perno') or row.get('persno') or row.get('perid')

        # Extract day of week (if available)
        day_of_week = row.get('dayno')
        if is_missing(day_of_week):
            day_of_week = None

        # Extract time - try both departure and arrival
        deptm = row.get('deptm')
        arrtm = row.get('arrtm')

        # Prefer departure time, fall back to arrival
        hour, minute = parse_time_field(deptm)
        if hour is None:
            hour, minute = parse_time_field(arrtm)

        if hour is None:
            continue  # Skip trips without time

        # Extract mode
        mode = row.get('mode')
        if is_missing(mode):
            continue

        # Extract location - prefer geozip, fall back to zip1, then county
        zip_code = row.get('geozip') or row.get('zip1') or row.get('zip')
        if is_missing(zip_code):
            zip_code = None

        county = row.get('county') or row.get('cnty')
        if is_missing(county):
            county = None

        # Identify walking
        walk_only, contains_walk = identify_walking_modes(row)

        rows.append({
            'survey': survey_name,
            'household_id': str(household_id),
            'person_id': str(person_id) if not is_missing(person_id) else '',
            'survey_year': survey_year,
            'survey_month': survey_month,
            'day_of_week': day_of_week,
            'hour': hour,
            'minute': minute,
            'mode': mode,
            'zip': str(int(zip_code)).zfill(5) if zip_code and not is_missing(zip_code) else None,
            'county': str(int(county)).zfill(5) if county and not is_missing(county) else None,
            'walk_only': walk_only,
            'contains_walk': contains_walk
        })

    result_df = pd.DataFrame(rows)
    logger.info(f"  Standardized to {len(result_df):,} valid trips")

    return result_df


def add_geographic_locations(df, sampler, logger):
    """
    Add geographic locations using sampler.

    Adds columns: lat, lon, location_source
    """
    logger.info("Adding geographic locations...")

    lats = []
    lons = []
    sources = []

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="  Sampling locations"):
        zip_code = row['zip']
        county = row['county']
        variation_key = f"{row['household_id']}_{row['person_id']}"

        # Get location (priority: ZIP > County > None)
        lat, lon, source = sampler.get_location(
            zip_code=zip_code,
            county_fips=county,
            state=None,  # We don't have state fallback for metro surveys
            variation_key=variation_key
        )

        lats.append(lat)
        lons.append(lon)
        sources.append(source if lat is not None else None)

    df['lat'] = lats
    df['lon'] = lons
    df['location_source'] = sources

    valid_locations = df['lat'].notna().sum()
    logger.info(f"  Valid locations: {valid_locations:,} / {len(df):,} ({100*valid_locations/len(df):.1f}%)")

    # Count by source
    source_counts = df['location_source'].value_counts()
    for source, count in source_counts.items():
        logger.info(f"    {source}: {count:,} ({100*count/len(df):.1f}%)")

    return df


def add_datetimes(df, logger):
    """
    Add datetime column based on survey period and time fields.
    """
    logger.info("Generating trip datetimes...")

    datetimes = []
    for idx, row in df.iterrows():
        dt = generate_trip_datetime(
            survey_year=row['survey_year'],
            survey_month=row['survey_month'],
            day_of_week=row['day_of_week'],
            hour=row['hour'],
            minute=row['minute'],
            household_id=row['household_id'],
            seed=RANDOM_SEED
        )
        datetimes.append(dt)

    df['datetime'] = pd.to_datetime(datetimes)

    valid_dates = df['datetime'].notna().sum()
    logger.info(f"  Valid datetimes: {valid_dates:,} / {len(df):,} ({100*valid_dates/len(df):.1f}%)")

    return df


def main():
    logger = setup_logging()

    project_root = Path(__file__).parent.parent.parent
    metro_dir = project_root / "data" / "transit_surveys" / "metro" / "extracted"
    output_dir = project_root / "data" / "transit_surveys" / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("="*70)
    logger.info("METRO TRAVEL SURVEY PROCESSING PIPELINE")
    logger.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*70)

    # Initialize geographic sampler
    logger.info("\nInitializing geographic sampler...")
    zip_shapefile = project_root / "data" / "geographic_shapefiles" / "zcta" / "tl_2023_us_zcta520.shp"
    county_shapefile = project_root / "data" / "geographic_shapefiles" / "counties" / "cb_2023_us_county_500k.shp"

    # Create minimal state centroids (not used for metro surveys, but required by sampler)
    state_centroids = pd.DataFrame([{'state': 'XX', 'lat': 0, 'lon': 0}])

    sampler = GeographicSampler(
        zip_shapefile=zip_shapefile,
        county_shapefile=county_shapefile,
        state_centroids_df=state_centroids,
        base_seed=RANDOM_SEED
    )

    # Process all surveys
    logger.info("\n" + "="*70)
    logger.info("LOADING AND STANDARDIZING SURVEYS")
    logger.info("="*70)

    all_surveys = []
    survey_dirs = sorted([d for d in metro_dir.iterdir() if d.is_dir()])

    for survey_dir in survey_dirs:
        logger.info(f"\nProcessing {survey_dir.name}...")

        result = load_survey(survey_dir, logger)
        if result is None:
            continue

        df, survey_name = result

        # Standardize
        std_df = standardize_survey(df, survey_name, logger)
        if len(std_df) > 0:
            all_surveys.append(std_df)

    if not all_surveys:
        logger.error("No surveys were successfully processed!")
        return

    # Combine all surveys
    logger.info("\n" + "="*70)
    logger.info("COMBINING SURVEYS")
    logger.info("="*70)

    combined_df = pd.concat(all_surveys, ignore_index=True)
    logger.info(f"Combined: {len(combined_df):,} trips from {len(all_surveys)} surveys")

    # Add geographic locations
    logger.info("\n" + "="*70)
    logger.info("ADDING GEOGRAPHIC LOCATIONS")
    logger.info("="*70)

    combined_df = add_geographic_locations(combined_df, sampler, logger)

    # Add datetimes
    logger.info("\n" + "="*70)
    logger.info("GENERATING DATETIMES")
    logger.info("="*70)

    combined_df = add_datetimes(combined_df, logger)

    # Filter to valid trips (have location and datetime)
    valid_df = combined_df[
        combined_df['lat'].notna() &
        combined_df['datetime'].notna()
    ].copy()

    logger.info(f"\nValid trips for UTCI annotation: {len(valid_df):,} / {len(combined_df):,} ({100*len(valid_df)/len(combined_df):.1f}%)")

    # Save intermediate result
    intermediate_path = output_dir / "metro_surveys_standardized.csv"
    valid_df.to_csv(intermediate_path, index=False)
    logger.info(f"\nSaved standardized surveys: {intermediate_path}")

    # Summary statistics
    logger.info("\n" + "="*70)
    logger.info("SUMMARY STATISTICS")
    logger.info("="*70)

    logger.info(f"\nTotal trips: {len(valid_df):,}")
    logger.info(f"Walking trips: {valid_df['walk_only'].sum():,} ({100*valid_df['walk_only'].sum()/len(valid_df):.1f}%)")
    logger.info(f"Trips with walk segment: {valid_df['contains_walk'].sum():,} ({100*valid_df['contains_walk'].sum()/len(valid_df):.1f}%)")

    logger.info(f"\nTrips by survey:")
    survey_counts = valid_df['survey'].value_counts()
    for survey, count in survey_counts.head(10).items():
        logger.info(f"  {survey}: {count:,}")
    if len(survey_counts) > 10:
        logger.info(f"  ... and {len(survey_counts) - 10} more surveys")

    logger.info(f"\nDate range: {valid_df['datetime'].min()} to {valid_df['datetime'].max()}")

    logger.info("\n" + "="*70)
    logger.info("PROCESSING COMPLETE")
    logger.info(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*70)

    logger.info(f"\nNext step: Annotate with UTCI using add_utci_chunked.py")
    logger.info(f"  python scripts/travel_surveys/add_utci_chunked.py \\")
    logger.info(f"    --input {intermediate_path} \\")
    logger.info(f"    --output {output_dir}/metro_surveys_with_utci.csv")


if __name__ == '__main__':
    main()
