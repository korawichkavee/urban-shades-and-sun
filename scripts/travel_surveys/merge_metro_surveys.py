# ABOUTME: One-time merge of all metro surveys into standardized format.
# ABOUTME: Documents column mappings and skips surveys missing critical fields.

import pandas as pd
from pathlib import Path
import logging
import json


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
    if value in MISSING_CODES:
        return True
    if isinstance(value, str) and value.strip() in ['', 'NA', 'N/A', '-']:
        return True
    return False


def find_survey_files(survey_dir):
    """Find survey trip data file(s)."""
    data_dir = survey_dir / "data"
    if not data_dir.exists():
        return []

    possible_names = ['survey_data.csv', 'survey_trip.csv', 'survey_trips.csv']
    found = []
    for name in possible_names:
        path = data_dir / name
        if path.exists():
            found.append(path)
    return found


def detect_columns(df, logger):
    """
    Detect which columns correspond to our required fields.

    Returns dict with keys: household_id, mode, time, location, day_of_week
    Each value is either a column name or None if not found.
    """
    cols = df.columns.tolist()
    col_lower = {c.lower(): c for c in cols}

    mapping = {}

    # Household ID - try multiple patterns
    for pattern in ['sampno', 'sampn', 'hhid', 'houseid', 'hh_id', 'batch']:
        if pattern in col_lower:
            mapping['household_id'] = col_lower[pattern]
            break
    else:
        mapping['household_id'] = None

    # Person ID
    for pattern in ['perno', 'persno', 'perid', 'person', 'per_id']:
        if pattern in col_lower:
            mapping['person_id'] = col_lower[pattern]
            break
    else:
        mapping['person_id'] = None

    # Mode
    for pattern in ['mode', 'tripmode', 'tmode', 'modecode']:
        if pattern in col_lower:
            mapping['mode'] = col_lower[pattern]
            break
    else:
        mapping['mode'] = None

    # Time fields - departure time
    for pattern in ['deptm', 'deptime', 'starttime', 'start_time', 'tlo']:
        if pattern in col_lower:
            mapping['depart_time'] = col_lower[pattern]
            break
    else:
        mapping['depart_time'] = None

    # Time fields - arrival time
    for pattern in ['arrtm', 'arrtime', 'endtime', 'end_time', 'tad']:
        if pattern in col_lower:
            mapping['arrival_time'] = col_lower[pattern]
            break
    else:
        mapping['arrival_time'] = None

    # Day of week
    for pattern in ['dayno', 'dayofweek', 'day_of_week', 'dow', 'wkday']:
        if pattern in col_lower:
            mapping['day_of_week'] = col_lower[pattern]
            break
    else:
        mapping['day_of_week'] = None

    # Location - ZIP
    for pattern in ['geozip', 'zip1', 'zip', 'zipcode', 'ozip', 'dzip']:
        if pattern in col_lower:
            mapping['zip'] = col_lower[pattern]
            break
    else:
        mapping['zip'] = None

    # Location - County
    for pattern in ['county', 'cnty', 'countyfips', 'ocounty', 'dcounty', 'ocnty', 'dcnty']:
        if pattern in col_lower:
            mapping['county'] = col_lower[pattern]
            break
    else:
        mapping['county'] = None

    return mapping


def check_required_fields(mapping, logger):
    """
    Check if survey has minimum required fields.

    Required: household_id, mode, (depart_time OR arrival_time), (zip OR county)
    """
    has_household = mapping['household_id'] is not None
    has_mode = mapping['mode'] is not None
    has_time = mapping['depart_time'] is not None or mapping['arrival_time'] is not None
    has_location = mapping['zip'] is not None or mapping['county'] is not None

    missing = []
    if not has_household:
        missing.append('household_id')
    if not has_mode:
        missing.append('mode')
    if not has_time:
        missing.append('time (depart or arrival)')
    if not has_location:
        missing.append('location (zip or county)')

    return len(missing) == 0, missing


def standardize_survey_data(df, mapping, survey_name):
    """
    Extract and standardize data from survey using detected column mapping.

    Returns DataFrame with standardized columns.
    """
    rows = []

    for idx, row in df.iterrows():
        try:
            # Extract fields using mapping
            household_id = row[mapping['household_id']] if mapping['household_id'] else None
            if is_missing(household_id):
                continue

            mode = row[mapping['mode']] if mapping['mode'] else None
            if is_missing(mode):
                continue

            # Get time - prefer departure, fallback to arrival
            time_val = None
            if mapping['depart_time']:
                time_val = row[mapping['depart_time']]
            if (time_val is None or is_missing(time_val)) and mapping['arrival_time']:
                time_val = row[mapping['arrival_time']]
            if is_missing(time_val):
                continue

            # Get location
            zip_code = row[mapping['zip']] if mapping['zip'] else None
            if is_missing(zip_code):
                zip_code = None

            county = row[mapping['county']] if mapping['county'] else None
            if is_missing(county):
                county = None

            if zip_code is None and county is None:
                continue

            # Get person ID if available
            person_id = row[mapping['person_id']] if mapping['person_id'] else None
            if is_missing(person_id):
                person_id = None

            # Get day of week if available
            day_of_week = row[mapping['day_of_week']] if mapping['day_of_week'] else None
            if is_missing(day_of_week):
                day_of_week = None

            rows.append({
                'survey': survey_name,
                'household_id': str(household_id),
                'person_id': str(person_id) if person_id else '',
                'mode': str(mode),
                'time': str(time_val),
                'day_of_week': str(day_of_week) if day_of_week else None,
                'zip': str(int(float(zip_code))).zfill(5) if zip_code else None,
                'county': str(int(float(county))).zfill(5) if county else None,
            })
        except Exception as e:
            # Skip problematic rows
            continue

    return pd.DataFrame(rows)


def main():
    logger = setup_logging()

    project_root = Path(__file__).parent.parent.parent
    metro_dir = project_root / "data" / "transit_surveys" / "metro" / "extracted"
    output_dir = project_root / "data" / "transit_surveys" / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("="*70)
    logger.info("METRO SURVEY MERGE - ONE TIME PROCESSING")
    logger.info("="*70)

    survey_dirs = sorted([d for d in metro_dir.iterdir() if d.is_dir()])

    all_survey_data = []
    column_mappings = {}
    skipped_surveys = {}

    logger.info(f"\nFound {len(survey_dirs)} survey directories")
    logger.info("")

    for survey_dir in survey_dirs:
        survey_name = survey_dir.name
        logger.info(f"Processing {survey_name}...")

        # Find data files
        data_files = find_survey_files(survey_dir)
        if not data_files:
            skipped_surveys[survey_name] = "No data file found"
            logger.warning(f"  SKIP: No data file found")
            continue

        # Load data
        try:
            df = pd.read_csv(data_files[0], low_memory=False)
            logger.info(f"  Loaded {len(df):,} rows from {data_files[0].name}")
        except Exception as e:
            skipped_surveys[survey_name] = f"Error loading: {e}"
            logger.error(f"  SKIP: Error loading - {e}")
            continue

        # Detect columns
        mapping = detect_columns(df, logger)
        has_required, missing = check_required_fields(mapping, logger)

        if not has_required:
            skipped_surveys[survey_name] = f"Missing required fields: {', '.join(missing)}"
            logger.warning(f"  SKIP: Missing required fields: {', '.join(missing)}")
            continue

        logger.info(f"  Detected columns: {json.dumps(mapping, indent=4)}")

        # Standardize data
        std_df = standardize_survey_data(df, mapping, survey_name)
        logger.info(f"  Standardized to {len(std_df):,} valid trips")

        if len(std_df) > 0:
            all_survey_data.append(std_df)
            column_mappings[survey_name] = {
                'source_file': data_files[0].name,
                'mapping': mapping,
                'rows_loaded': len(df),
                'rows_standardized': len(std_df)
            }
            logger.info(f"  SUCCESS: {len(std_df):,} trips added")
        else:
            skipped_surveys[survey_name] = "No valid trips after standardization"
            logger.warning(f"  SKIP: No valid trips after standardization")

        logger.info("")

    # Combine all surveys
    if not all_survey_data:
        logger.error("No surveys were successfully processed!")
        return

    logger.info("="*70)
    logger.info("COMBINING SURVEYS")
    logger.info("="*70)

    combined_df = pd.concat(all_survey_data, ignore_index=True)
    logger.info(f"Combined: {len(combined_df):,} trips from {len(all_survey_data)} surveys")

    # Save merged data
    output_path = output_dir / "metro_surveys_raw_merged.csv"
    combined_df.to_csv(output_path, index=False)
    logger.info(f"\nSaved merged data: {output_path}")

    # Save column mappings
    mapping_path = output_dir / "metro_survey_column_mappings.json"
    with open(mapping_path, 'w') as f:
        json.dump(column_mappings, f, indent=2)
    logger.info(f"Saved column mappings: {mapping_path}")

    # Save skipped surveys
    skipped_path = output_dir / "metro_surveys_skipped.json"
    with open(skipped_path, 'w') as f:
        json.dump(skipped_surveys, f, indent=2)
    logger.info(f"Saved skipped surveys: {skipped_path}")

    # Summary
    logger.info("\n" + "="*70)
    logger.info("SUMMARY")
    logger.info("="*70)
    logger.info(f"Successfully processed: {len(all_survey_data)} surveys")
    logger.info(f"Skipped: {len(skipped_surveys)} surveys")
    logger.info(f"Total trips: {len(combined_df):,}")

    logger.info(f"\nTrips by survey (top 10):")
    survey_counts = combined_df['survey'].value_counts()
    for survey, count in survey_counts.head(10).items():
        logger.info(f"  {survey}: {count:,}")

    logger.info(f"\nLocation coverage:")
    has_zip = combined_df['zip'].notna().sum()
    has_county = combined_df['county'].notna().sum()
    logger.info(f"  ZIP codes: {has_zip:,} ({100*has_zip/len(combined_df):.1f}%)")
    logger.info(f"  Counties: {has_county:,} ({100*has_county/len(combined_df):.1f}%)")
    logger.info(f"  Either: {(has_zip | has_county):,} ({100*(has_zip | has_county)/len(combined_df):.1f}%)")

    logger.info("\n" + "="*70)
    logger.info("MERGE COMPLETE")
    logger.info("="*70)


if __name__ == '__main__':
    main()
