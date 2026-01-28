# ABOUTME: Annotate merged metro surveys with datetime, geographic locations, and UTCI.
# ABOUTME: Takes merged CSV and adds all required fields for analysis.

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'utils'))
sys.path.insert(0, str(Path(__file__).parent))

from geographic_sampler import GeographicSampler

import pandas as pd
import logging
from datetime import datetime
import calendar
import random
import argparse
from tqdm import tqdm


RANDOM_SEED = 42
MISSING_CODES = [-1, -7, -8, -9, -99, -999, -9999, -99999, -999999, -9999999,
                  99, 999, 9999, 99999, 999999, 9999999]


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


def parse_time(time_str):
    """Parse time string (HHMM format) to hour and minute."""
    try:
        time_int = int(float(time_str))
        if time_int in MISSING_CODES:
            return None, None
        hour = time_int // 100
        minute = time_int % 100
        if 0 <= hour < 24 and 0 <= minute < 60:
            return hour, minute
    except (ValueError, TypeError):
        pass
    return None, None


def infer_survey_period(survey_name):
    """Extract year from survey name."""
    parts = survey_name.split('-')
    for part in parts:
        if part.isdigit() and len(part) == 4:
            return int(part), 6  # Year, default to June
    return None, None


def generate_datetime(year, month, day_of_week_str, hour, minute, household_id):
    """Generate datetime with reproducible day selection."""
    if not all([year, month, hour is not None, minute is not None]):
        return None

    # Parse day of week if available
    day = 15  # Default mid-month
    if day_of_week_str and day_of_week_str not in ['', 'None', 'nan']:
        try:
            dow = int(float(day_of_week_str))
            if dow not in MISSING_CODES and 1 <= dow <= 7:
                # Convert to Python weekday
                target_weekday = 6 if dow == 1 else dow - 2

                # Find matching days
                num_days = calendar.monthrange(year, month)[1]
                matching_days = []
                for d in range(1, num_days + 1):
                    dt = datetime(year, month, d)
                    if dt.weekday() == target_weekday:
                        matching_days.append(d)

                if matching_days:
                    rng = random.Random(RANDOM_SEED + hash(str(household_id) + str(year)) % 1000000)
                    day = rng.choice(matching_days)
        except (ValueError, TypeError):
            pass

    try:
        return datetime(int(year), int(month), int(day), int(hour), int(minute))
    except (ValueError, TypeError):
        return None


def identify_walk_mode(mode_str):
    """Identify if trip mode is walking. Mode 1 is typically walk."""
    try:
        mode = int(float(mode_str))
        if mode == 1:
            return True
    except (ValueError, TypeError):
        pass
    return False


def main():
    parser = argparse.ArgumentParser(description='Annotate merged metro surveys with datetime, locations, and prepare for UTCI')
    parser.add_argument('--input', type=str, help='Input CSV file path (default: metro_surveys_raw_merged.csv)')
    parser.add_argument('--output', type=str, help='Output CSV file path (default: metro_surveys_standardized.csv)')
    args = parser.parse_args()

    logger = setup_logging()
    project_root = Path(__file__).parent.parent.parent

    logger.info("="*70)
    logger.info("ANNOTATING MERGED METRO SURVEYS")
    logger.info("="*70)

    # Load merged data
    if args.input:
        input_path = Path(args.input)
        if not input_path.is_absolute():
            input_path = project_root / input_path
    else:
        input_path = project_root / "data" / "transit_surveys" / "processed" / "metro_surveys_raw_merged.csv"

    logger.info(f"\nLoading merged data from {input_path}...")
    df = pd.read_csv(input_path)
    logger.info(f"  Loaded {len(df):,} trips from {df['survey'].nunique()} surveys")

    # Parse times
    logger.info("\nParsing trip times...")
    hours = []
    minutes = []
    for time_str in tqdm(df['time'], desc="  Parsing times"):
        h, m = parse_time(time_str)
        hours.append(h)
        minutes.append(m)
    df['hour'] = hours
    df['minute'] = minutes

    valid_times = df['hour'].notna().sum()
    logger.info(f"  Valid times: {valid_times:,} / {len(df):,} ({100*valid_times/len(df):.1f}%)")

    # Infer survey periods
    logger.info("\nInferring survey periods...")
    survey_periods = {}
    for survey in df['survey'].unique():
        year, month = infer_survey_period(survey)
        survey_periods[survey] = (year, month)
        logger.info(f"  {survey}: {year}-{month:02d}")

    df['survey_year'] = df['survey'].map(lambda s: survey_periods[s][0])
    df['survey_month'] = df['survey'].map(lambda s: survey_periods[s][1])

    # Generate datetimes
    logger.info("\nGenerating trip datetimes...")
    datetimes = []
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="  Generating datetimes"):
        dt = generate_datetime(
            row['survey_year'],
            row['survey_month'],
            row['day_of_week'],
            row['hour'],
            row['minute'],
            row['household_id']
        )
        datetimes.append(dt)

    df['datetime'] = pd.to_datetime(datetimes)
    valid_dt = df['datetime'].notna().sum()
    logger.info(f"  Valid datetimes: {valid_dt:,} / {len(df):,} ({100*valid_dt/len(df):.1f}%)")

    # Identify walking trips
    logger.info("\nIdentifying walking trips...")
    df['walk_only'] = df['mode'].apply(identify_walk_mode)
    df['contains_walk'] = df['walk_only']  # For now, same as walk_only

    walk_trips = df['walk_only'].sum()
    logger.info(f"  Walking trips: {walk_trips:,} ({100*walk_trips/len(df):.1f}%)")

    # Initialize geographic sampler
    logger.info("\nInitializing geographic sampler...")
    zip_shapefile = project_root / "data" / "geographic_shapefiles" / "zcta" / "tl_2023_us_zcta520.shp"
    county_shapefile = project_root / "data" / "geographic_shapefiles" / "counties" / "cb_2023_us_county_500k.shp"
    state_centroids = pd.DataFrame([{'state': 'XX', 'lat': 0, 'lon': 0}])

    sampler = GeographicSampler(
        zip_shapefile=zip_shapefile,
        county_shapefile=county_shapefile,
        state_centroids_df=state_centroids,
        base_seed=RANDOM_SEED
    )

    # Add geographic locations
    logger.info("\nAdding geographic locations...")
    lats = []
    lons = []
    sources = []

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="  Sampling locations"):
        variation_key = f"{row['household_id']}_{row['person_id']}"

        # Convert ZIP and county to strings (they may be floats from CSV)
        zip_code = None
        if pd.notna(row['zip']):
            try:
                zip_code = str(int(float(row['zip']))).zfill(5)
            except (ValueError, TypeError):
                pass

        county_fips = None
        if pd.notna(row['county']):
            try:
                county_fips = str(int(float(row['county']))).zfill(5)
            except (ValueError, TypeError):
                # County might be a name instead of FIPS code - skip it
                pass

        lat, lon, source = sampler.get_location(
            zip_code=zip_code,
            county_fips=county_fips,
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

    # Filter to valid rows for UTCI
    valid_df = df[df['lat'].notna() & df['datetime'].notna()].copy()
    logger.info(f"\nTrips ready for UTCI annotation: {len(valid_df):,} / {len(df):,} ({100*len(valid_df)/len(df):.1f}%)")

    # Save standardized data
    if args.output:
        output_path = Path(args.output)
        if not output_path.is_absolute():
            output_path = project_root / output_path
    else:
        output_path = project_root / "data" / "transit_surveys" / "processed" / "metro_surveys_standardized.csv"

    valid_df.to_csv(output_path, index=False)
    logger.info(f"\nSaved standardized data: {output_path}")

    # Summary
    logger.info("\n" + "="*70)
    logger.info("SUMMARY")
    logger.info("="*70)
    logger.info(f"Total trips: {len(valid_df):,}")
    logger.info(f"Surveys: {valid_df['survey'].nunique()}")
    logger.info(f"Walking trips: {valid_df['walk_only'].sum():,} ({100*valid_df['walk_only'].sum()/len(valid_df):.1f}%)")
    logger.info(f"Date range: {valid_df['datetime'].min()} to {valid_df['datetime'].max()}")
    logger.info(f"\nNext step: Annotate with UTCI")
    logger.info("="*70)


if __name__ == '__main__':
    main()
