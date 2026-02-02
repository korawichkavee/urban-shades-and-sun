# ABOUTME: Merge 12 recoverable surveys using verified field mappings and time parsers
# ABOUTME: Outputs standardized format ready for UTCI annotation

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from recoverable_survey_field_mappings import FIELD_MAPPINGS, TRIP_FILES
from time_field_parsers import combine_split_time_fields, extract_primary_mode

import pandas as pd
import logging
import json
from datetime import datetime


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


MISSING_CODES = [
    -1, -7, -8, -9, -99, -999, -9999, -99999, -999999, -9999999,
    99, 999, 9999, 99999, 999999, 9999999
]


def is_missing(value):
    """Check if value represents missing data."""
    if pd.isna(value):
        return True
    if isinstance(value, (int, float)) and value in MISSING_CODES:
        return True
    if isinstance(value, str) and value.strip() in ['', 'NA', 'N/A', '-']:
        return True
    return False


def load_survey_data(survey_name, survey_dir, trip_file, logger):
    """Load trip data for a survey."""
    data_path = survey_dir / "data" / trip_file

    if not data_path.exists():
        logger.error(f"  File not found: {data_path}")
        return None

    try:
        df = pd.read_csv(data_path, low_memory=False)
        logger.info(f"  Loaded {len(df):,} rows from {trip_file}")
        return df
    except Exception as e:
        logger.error(f"  Error loading {trip_file}: {e}")
        return None


def join_household_location(df, survey_name, survey_dir, logger):
    """Join household location data for surveys that need it (e.g., detroit-1994)."""
    mapping = FIELD_MAPPINGS[survey_name]

    if 'household_file' not in mapping:
        return df

    hh_file = survey_dir / "data" / mapping['household_file']
    if not hh_file.exists():
        logger.warning(f"  Household file not found: {hh_file}")
        return df

    try:
        hh_df = pd.read_csv(hh_file, low_memory=False)
        logger.info(f"  Loading household location from {mapping['household_file']}")

        # Get household ID field
        hh_id = mapping['household_id'][0]
        loc_fields = mapping.get('household_location_fields', [])

        if not loc_fields:
            return df

        # Join on household ID
        join_cols = [hh_id] + loc_fields
        hh_subset = hh_df[join_cols].drop_duplicates(subset=[hh_id])

        df = df.merge(hh_subset, on=hh_id, how='left', suffixes=('', '_hh'))
        logger.info(f"  Joined household data: {len(df)} rows, added {loc_fields}")

        return df

    except Exception as e:
        logger.warning(f"  Error joining household data: {e}")
        return df


def standardize_survey(df, survey_name, logger):
    """Standardize a survey using verified field mappings."""
    mapping = FIELD_MAPPINGS[survey_name]

    # Apply time parsing
    df = combine_split_time_fields(df)

    # Apply mode extraction
    df = extract_primary_mode(df)

    rows = []

    for idx, row in df.iterrows():
        try:
            # Get household ID
            hh_id_field = mapping['household_id'][0]
            household_id = row[hh_id_field]
            if is_missing(household_id):
                continue

            # Get person ID
            person_id_field = mapping.get('person_id', [None])[0]
            person_id = row[person_id_field] if person_id_field else None
            if is_missing(person_id):
                person_id = None

            # Get time (from parsed time_minutes if available)
            time_val = row.get('time_minutes')
            if is_missing(time_val):
                # Fallback to first time field
                time_fields = mapping['time']
                for tf in time_fields:
                    if tf in df.columns:
                        time_val = row[tf]
                        if not is_missing(time_val):
                            break
                if is_missing(time_val):
                    continue

            # Get mode (from parsed primary_mode if available)
            mode_val = row.get('primary_mode')
            if is_missing(mode_val):
                # Fallback to first mode field
                mode_fields = mapping['mode']
                for mf in mode_fields:
                    if mf in df.columns:
                        mode_val = row[mf]
                        if not is_missing(mode_val):
                            break
                if is_missing(mode_val):
                    continue

            # Get location - try all location fields
            location_val = None
            location_type = None

            for loc_field in mapping['location']:
                if loc_field in df.columns:
                    val = row[loc_field]
                    if not is_missing(val):
                        location_val = val
                        location_type = loc_field
                        break

            # Check household location fields if needed
            if location_val is None and 'household_location_fields' in mapping:
                for loc_field in mapping['household_location_fields']:
                    if loc_field in df.columns:
                        val = row[loc_field]
                        if not is_missing(val):
                            location_val = val
                            location_type = f"{loc_field}_hh"
                            break

            if location_val is None:
                continue

            rows.append({
                'survey': survey_name,
                'household_id': str(household_id),
                'person_id': str(person_id) if person_id is not None else '',
                'time_minutes': int(time_val) if isinstance(time_val, (int, float)) else str(time_val),
                'mode': str(mode_val),
                'location': str(location_val),
                'location_type': location_type,
            })

        except Exception as e:
            # Skip problematic rows
            continue

    result_df = pd.DataFrame(rows)
    logger.info(f"  Standardized to {len(result_df):,} valid trips")

    return result_df


def main():
    logger = setup_logging()
    project_root = Path(__file__).parent.parent.parent

    logger.info("="*80)
    logger.info("RECOVERABLE SURVEYS MERGE")
    logger.info("="*80)
    logger.info(f"Target: 12 recoverable surveys (~709k trips)")
    logger.info("")

    metro_dir = project_root / "data" / "transit_surveys" / "metro" / "extracted"
    output_dir = project_root / "data" / "transit_surveys" / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    all_survey_data = []
    processing_log = {}
    failed_surveys = {}

    for survey_name in sorted(TRIP_FILES.keys()):
        logger.info(f"{'='*80}")
        logger.info(f"Processing: {survey_name}")
        logger.info(f"{'='*80}")

        survey_dir = metro_dir / survey_name
        if not survey_dir.exists():
            logger.error(f"  Survey directory not found: {survey_dir}")
            failed_surveys[survey_name] = "Directory not found"
            continue

        trip_file = TRIP_FILES[survey_name]

        # Load trip data
        df = load_survey_data(survey_name, survey_dir, trip_file, logger)
        if df is None:
            failed_surveys[survey_name] = "Failed to load trip file"
            continue

        # Join household data if needed
        df = join_household_location(df, survey_name, survey_dir, logger)

        # Standardize
        std_df = standardize_survey(df, survey_name, logger)

        if len(std_df) == 0:
            logger.warning(f"  No valid trips after standardization")
            failed_surveys[survey_name] = "No valid trips after standardization"
            continue

        # Add to collection
        all_survey_data.append(std_df)

        processing_log[survey_name] = {
            'source_file': trip_file,
            'rows_loaded': len(df),
            'rows_standardized': len(std_df),
            'success': True
        }

        logger.info(f"  ✓ SUCCESS: {len(std_df):,} trips")
        logger.info("")

    # Combine all surveys
    if not all_survey_data:
        logger.error("No surveys were successfully processed!")
        return

    logger.info("="*80)
    logger.info("COMBINING SURVEYS")
    logger.info("="*80)

    combined_df = pd.concat(all_survey_data, ignore_index=True)
    logger.info(f"Total trips: {len(combined_df):,}")
    logger.info(f"Total surveys: {len(all_survey_data)}")

    # Save merged data
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / "recoverable_surveys_standardized.csv"
    combined_df.to_csv(output_path, index=False)
    logger.info(f"\nSaved: {output_path}")

    # Save processing log
    log_path = output_dir / "recoverable_surveys_processing_log.json"
    with open(log_path, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'successful': processing_log,
            'failed': failed_surveys
        }, f, indent=2)
    logger.info(f"Saved log: {log_path}")

    # Summary
    logger.info("\n" + "="*80)
    logger.info("SUMMARY")
    logger.info("="*80)
    logger.info(f"Successful: {len(all_survey_data)} surveys")
    logger.info(f"Failed: {len(failed_surveys)} surveys")
    logger.info(f"Total trips: {len(combined_df):,}")

    logger.info(f"\nTrips by survey:")
    survey_counts = combined_df['survey'].value_counts()
    for survey, count in survey_counts.items():
        logger.info(f"  {survey}: {count:,}")

    logger.info(f"\nLocation coverage:")
    loc_types = combined_df['location_type'].value_counts()
    for loc_type, count in loc_types.items():
        pct = 100 * count / len(combined_df)
        logger.info(f"  {loc_type}: {count:,} ({pct:.1f}%)")

    logger.info("\n" + "="*80)
    logger.info("MERGE COMPLETE")
    logger.info("="*80)


if __name__ == '__main__':
    main()
