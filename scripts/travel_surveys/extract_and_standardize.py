# ABOUTME: Extracts and standardizes travel survey data to common format.
# ABOUTME: Converts survey-specific fields to datetime, location, and mode annotations.

import pandas as pd
import yaml
from pathlib import Path
from datetime import datetime, timedelta
import argparse
import logging


def setup_logging():
    """Configure logging to console."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)


def load_config(config_path, survey_name):
    """Load configuration for a specific survey."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    if survey_name not in config:
        raise ValueError(f"Survey '{survey_name}' not found in config. Available: {list(config.keys())}")

    return config[survey_name]


def parse_datetime(row, config, random_seed=42):
    """
    Parse survey date and time fields into a datetime object.

    For NHTS: TDAYDATE is YYYYMM (no day), STRTTIME is HHMM, TRAVDAY is day of week.
    We sample a random day from the month matching the day of week using fixed seed.
    """
    import calendar
    import random

    fields = config['fields']

    # Get date (YYYYMM format)
    date_val = str(int(row[fields['date_field']]))
    year = int(date_val[:4])
    month = int(date_val[4:6])

    # Get day of week (1=Sunday, 2=Monday, ..., 7=Saturday)
    day_of_week = int(row[fields['day_of_week']])

    # Convert to Python weekday (0=Monday, 6=Sunday)
    if day_of_week == 1:  # Sunday
        target_weekday = 6
    else:
        target_weekday = day_of_week - 2

    # Find all days in the month matching this weekday
    num_days = calendar.monthrange(year, month)[1]
    matching_days = []
    for day in range(1, num_days + 1):
        dt_test = datetime(year, month, day)
        if dt_test.weekday() == target_weekday:
            matching_days.append(day)

    # Select one randomly using household ID as seed component for reproducibility
    household_id = str(row[fields['household_id']])
    seed = random_seed + hash(household_id + date_val) % 1000000
    rng = random.Random(seed)
    day = rng.choice(matching_days)

    # Get time (HHMM format)
    time_val = str(int(row[fields['start_time']])).zfill(4)
    hour = int(time_val[:2])
    minute = int(time_val[2:4])

    try:
        dt = datetime(year, month, day, hour, minute)
        return dt
    except ValueError as e:
        logging.warning(f"Invalid datetime for row: {e}")
        return None


def get_location(row, config):
    """
    Extract location information for UTCI lookup.
    Returns (lat, lon, location_precision, is_placeholder) tuple.

    is_placeholder=True indicates approximate location (state centroid)
    rather than actual trip location.
    """
    fields = config['fields']
    state_abbr = row[fields['state_abbr']]

    # Use state centroid as approximation
    if state_abbr in config['state_centroids']:
        lat, lon = config['state_centroids'][state_abbr]
        return lat, lon, 'state_centroid', True
    else:
        logging.warning(f"Unknown state: {state_abbr}")
        return None, None, 'unknown', True


def classify_pedestrian_mode(row, config):
    """
    Classify whether trip is pedestrian-based.
    Returns tuple: (is_full_pedestrian, contains_pedestrian)
    """
    fields = config['fields']
    mode = int(row[fields['transport_mode']])

    is_full_ped = mode in config['pedestrian_modes']['full_pedestrian']
    contains_ped = mode in config['pedestrian_modes']['contains_pedestrian']

    return is_full_ped, contains_ped


def classify_walking_mode(row, config):
    """
    Classify whether trip involves walking.
    Returns tuple: (is_full_walk, contains_walk)
    """
    fields = config['fields']
    mode = int(row[fields['transport_mode']])

    is_full_walk = mode in config['walking_modes']['full_walk']
    contains_walk = mode in config['walking_modes']['contains_walk']

    return is_full_walk, contains_walk


def get_mode_label(mode_code, config):
    """Get human-readable mode label."""
    return config['mode_labels'].get(int(mode_code), 'Unknown')


def standardize_trips(trips_df, config, logger):
    """
    Convert survey-specific trip data to standardized format.

    Output columns:
    - datetime: Parsed datetime of trip start
    - datetime_is_approximate: Boolean - True if date sampled from month (not exact)
    - lat, lon: Approximate location
    - location_precision: Precision level (state_centroid, county, etc.)
    - location_is_placeholder: Boolean - True if using approximate centroid vs actual location
    - mode_code: Original mode code
    - mode_label: Human-readable mode
    - is_full_walk: Boolean - entire trip was walking
    - contains_walk: Boolean - trip involved walking
    - is_full_pedestrian: Boolean - entire trip was pedestrian (walk/bike/escooter)
    - contains_pedestrian: Boolean - trip involved pedestrian modes
    - trip_miles: Trip distance
    - trip_minutes: Trip duration
    - household_id, person_id, trip_num: Identifiers
    """
    logger.info(f"Standardizing {len(trips_df)} trips...")

    fields = config['fields']

    # Filter out invalid trips
    valid_mask = (
        (trips_df[fields['date_field']] > 0) &
        (trips_df[fields['start_time']] >= 0) &
        (trips_df[fields['transport_mode']] > 0)
    )
    trips_df = trips_df[valid_mask].copy()
    logger.info(f"  {len(trips_df)} trips after filtering invalid records")

    # Parse datetime
    logger.info("  Parsing datetime...")
    trips_df['datetime'] = trips_df.apply(lambda row: parse_datetime(row, config), axis=1)
    # For NHTS, datetime is approximate (day sampled from month matching weekday)
    trips_df['datetime_is_approximate'] = True

    # Get location
    logger.info("  Extracting location...")
    location_data = trips_df.apply(lambda row: get_location(row, config), axis=1, result_type='expand')
    trips_df['lat'] = location_data[0]
    trips_df['lon'] = location_data[1]
    trips_df['location_precision'] = location_data[2]
    trips_df['location_is_placeholder'] = location_data[3]

    # Classify modes
    logger.info("  Classifying modes...")
    trips_df['mode_code'] = trips_df[fields['transport_mode']].astype(int)
    trips_df['mode_label'] = trips_df['mode_code'].apply(lambda x: get_mode_label(x, config))

    # Walking classification
    walk_data = trips_df.apply(lambda row: classify_walking_mode(row, config), axis=1, result_type='expand')
    trips_df['is_full_walk'] = walk_data[0]
    trips_df['contains_walk'] = walk_data[1]

    # Pedestrian classification
    ped_data = trips_df.apply(lambda row: classify_pedestrian_mode(row, config), axis=1, result_type='expand')
    trips_df['is_full_pedestrian'] = ped_data[0]
    trips_df['contains_pedestrian'] = ped_data[1]

    # Copy trip characteristics
    trips_df['trip_miles'] = trips_df[fields['trip_miles']]
    trips_df['trip_minutes'] = trips_df[fields['trip_minutes']]

    # Copy identifiers
    trips_df['household_id'] = trips_df[fields['household_id']]
    trips_df['person_id'] = trips_df[fields['person_id']]
    trips_df['trip_num'] = trips_df[fields['trip_num']]
    trips_df['state'] = trips_df[fields['state_abbr']]

    # Select final columns
    output_cols = [
        'household_id', 'person_id', 'trip_num',
        'datetime', 'datetime_is_approximate',
        'lat', 'lon', 'location_precision', 'location_is_placeholder', 'state',
        'mode_code', 'mode_label',
        'is_full_walk', 'contains_walk',
        'is_full_pedestrian', 'contains_pedestrian',
        'trip_miles', 'trip_minutes'
    ]

    result = trips_df[output_cols].copy()

    # Drop rows with invalid datetime
    result = result[result['datetime'].notna()]
    logger.info(f"  {len(result)} trips with valid datetime")

    return result


def main():
    parser = argparse.ArgumentParser(
        description='Extract and standardize travel survey data'
    )
    parser.add_argument(
        '--survey',
        type=str,
        default='nhts_2017',
        help='Survey name from config (default: nhts_2017)'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config/travel_survey_config.yaml',
        help='Path to config file'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='data/transit_surveys/processed',
        help='Output directory for standardized data'
    )
    parser.add_argument(
        '--sample',
        type=int,
        default=None,
        help='Process only first N trips (for testing)'
    )

    args = parser.parse_args()
    logger = setup_logging()

    # Load config
    logger.info(f"Loading config for survey: {args.survey}")
    config = load_config(args.config, args.survey)

    # Build paths
    project_root = Path(__file__).parent.parent.parent
    data_dir = project_root / config['data_dir']
    trip_file = data_dir / config['trip_file']
    output_dir = project_root / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load trips
    logger.info(f"Loading trips from {trip_file}...")
    if args.sample:
        trips_df = pd.read_csv(trip_file, nrows=args.sample)
        logger.info(f"  Loaded {len(trips_df)} trips (sample)")
    else:
        trips_df = pd.read_csv(trip_file)
        logger.info(f"  Loaded {len(trips_df)} trips")

    # Standardize
    standardized = standardize_trips(trips_df, config, logger)

    # Save
    output_file = output_dir / f"{args.survey}_standardized.csv"
    standardized.to_csv(output_file, index=False)
    logger.info(f"Saved standardized data to {output_file}")

    # Print summary stats
    logger.info("\n=== Summary Statistics ===")
    logger.info(f"Total trips: {len(standardized):,}")
    logger.info(f"Date range: {standardized['datetime'].min()} to {standardized['datetime'].max()}")
    logger.info(f"Unique states: {standardized['state'].nunique()}")
    logger.info(f"\nMode distribution:")
    mode_dist = standardized['mode_label'].value_counts()
    for mode, count in mode_dist.head(10).items():
        pct = 100 * count / len(standardized)
        logger.info(f"  {mode}: {count:,} ({pct:.1f}%)")

    logger.info(f"\nWalking trips:")
    logger.info(f"  Full walk: {standardized['is_full_walk'].sum():,} ({100*standardized['is_full_walk'].mean():.1f}%)")
    logger.info(f"  Contains walk: {standardized['contains_walk'].sum():,} ({100*standardized['contains_walk'].mean():.1f}%)")

    logger.info(f"\nPedestrian trips:")
    logger.info(f"  Full pedestrian: {standardized['is_full_pedestrian'].sum():,} ({100*standardized['is_full_pedestrian'].mean():.1f}%)")
    logger.info(f"  Contains pedestrian: {standardized['contains_pedestrian'].sum():,} ({100*standardized['contains_pedestrian'].mean():.1f}%)")


if __name__ == '__main__':
    main()
