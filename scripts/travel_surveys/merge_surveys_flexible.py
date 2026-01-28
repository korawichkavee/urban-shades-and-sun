# ABOUTME: Merge metro surveys using flexible loader to recover more surveys.
# ABOUTME: Handles multi-file datasets and varied naming conventions automatically.

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from flexible_survey_loader import load_survey_flexible

import pandas as pd
import json
import logging
from datetime import datetime


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


def main():
    logger = setup_logging()
    project_root = Path(__file__).parent.parent.parent

    logger.info("="*70)
    logger.info("FLEXIBLE METRO SURVEY MERGER")
    logger.info("="*70)

    # Get all survey directories
    extracted_dir = project_root / "data" / "transit_surveys" / "metro" / "extracted"
    survey_dirs = [d for d in extracted_dir.iterdir() if d.is_dir()]

    logger.info(f"\nFound {len(survey_dirs)} survey directories")

    merged_data = []
    column_mappings = {}
    skipped_surveys = {}
    recovered_surveys = []

    for survey_dir in sorted(survey_dirs):
        survey_name = survey_dir.name
        logger.info(f"\n{'='*70}")
        logger.info(f"Processing: {survey_name}")
        logger.info(f"{'='*70}")

        # Try flexible loader
        df, metadata, field_map = load_survey_flexible(survey_dir)

        if df is None:
            reason = metadata.get('error', 'Unknown error')
            logger.warning(f"  ❌ Skipped: {reason}")
            skipped_surveys[survey_name] = reason
            continue

        # Check for required fields
        required_fields = ['household_id', 'mode', 'time']
        location_fields = ['zip', 'county', 'fips']

        missing_fields = []
        if not field_map.get('household_id'):
            missing_fields.append('household_id')
        if not field_map.get('mode'):
            missing_fields.append('mode')
        if not field_map.get('time'):
            missing_fields.append('time (depart or arrival)')

        has_location = any(field_map.get(f) for f in location_fields)
        if not has_location:
            missing_fields.append('location (zip or county)')

        if missing_fields:
            reason = f"Missing required fields: {', '.join(missing_fields)}"
            logger.warning(f"  ❌ Skipped: {reason}")
            skipped_surveys[survey_name] = reason
            continue

        # Extract and standardize columns
        rows = len(df)
        standard_df = pd.DataFrame()
        standard_df['survey'] = [survey_name] * rows
        standard_df['household_id'] = df[field_map['household_id']].values

        # Person ID (optional)
        if field_map.get('person_id'):
            standard_df['person_id'] = df[field_map['person_id']]
        else:
            standard_df['person_id'] = None

        # Mode
        standard_df['mode'] = df[field_map['mode']]

        # Time
        standard_df['time'] = df[field_map['time']]

        # Day of week (if available)
        day_col = None
        for col in df.columns:
            if 'day' in col.lower() and ('week' in col.lower() or 'no' in col.lower()):
                day_col = col
                break
        standard_df['day_of_week'] = df[day_col] if day_col else None

        # Location - prefer ZIP > County > FIPS
        if field_map.get('zip'):
            standard_df['zip'] = df[field_map['zip']]
        else:
            standard_df['zip'] = None

        if field_map.get('county'):
            standard_df['county'] = df[field_map['county']]
        else:
            standard_df['county'] = None

        # Store field mappings
        column_mappings[survey_name] = {
            'household_id': field_map['household_id'],
            'person_id': field_map.get('person_id'),
            'mode': field_map['mode'],
            'time': field_map['time'],
            'day_of_week': day_col,
            'zip': field_map.get('zip'),
            'county': field_map.get('county'),
            'fips': field_map.get('fips'),
            'loading_strategy': metadata['strategy'],
            'source_file': metadata.get('file', 'multiple files')
        }

        # Add to merged data
        merged_data.append(standard_df)

        # Track if this was a recovery
        if metadata['strategy'] != 'single_file' or 'survey_data.csv' not in metadata.get('file', ''):
            recovered_surveys.append({
                'survey': survey_name,
                'strategy': metadata['strategy'],
                'file': metadata.get('file'),
                'rows': len(standard_df)
            })

        logger.info(f"  ✓ Loaded: {len(standard_df):,} trips")
        logger.info(f"  Strategy: {metadata['strategy']}")
        logger.info(f"  File(s): {metadata.get('file', 'multiple')}")
        logger.info(f"  Fields: household_id={field_map['household_id']}, "
                   f"mode={field_map['mode']}, time={field_map['time']}, "
                   f"location={'Yes' if has_location else 'No'}")

    # Combine all data
    if merged_data:
        logger.info(f"\n{'='*70}")
        logger.info("COMBINING DATA")
        logger.info(f"{'='*70}")

        combined_df = pd.concat(merged_data, ignore_index=True)
        logger.info(f"Total trips: {len(combined_df):,}")
        logger.info(f"Total surveys: {len(merged_data)}")

        # Save merged data
        output_path = project_root / "data" / "transit_surveys" / "processed" / "metro_surveys_raw_merged_flexible.csv"
        combined_df.to_csv(output_path, index=False)
        logger.info(f"\nSaved merged data: {output_path}")

        # Save column mappings
        mapping_path = project_root / "data" / "transit_surveys" / "processed" / "metro_survey_column_mappings_flexible.json"
        with open(mapping_path, 'w') as f:
            json.dump(column_mappings, f, indent=2)
        logger.info(f"Saved column mappings: {mapping_path}")

        # Save skipped surveys
        skipped_path = project_root / "data" / "transit_surveys" / "processed" / "metro_surveys_skipped_flexible.json"
        with open(skipped_path, 'w') as f:
            json.dump(skipped_surveys, f, indent=2)
        logger.info(f"Saved skipped surveys: {skipped_path}")

        # Save recovered surveys report
        if recovered_surveys:
            recovered_path = project_root / "data" / "transit_surveys" / "processed" / "recovered_surveys_report.json"
            with open(recovered_path, 'w') as f:
                json.dump(recovered_surveys, f, indent=2)
            logger.info(f"Saved recovered surveys report: {recovered_path}")

    # Summary
    logger.info(f"\n{'='*70}")
    logger.info("SUMMARY")
    logger.info(f"{'='*70}")
    logger.info(f"Surveys processed: {len(merged_data)}")
    logger.info(f"Surveys skipped: {len(skipped_surveys)}")
    if recovered_surveys:
        logger.info(f"\n🎉 RECOVERED {len(recovered_surveys)} SURVEYS:")
        for rec in recovered_surveys:
            logger.info(f"  • {rec['survey']}: {rec['rows']:,} trips ({rec['strategy']})")
    logger.info(f"\nTotal trips: {len(combined_df):,}")
    logger.info(f"{'='*70}")


if __name__ == '__main__':
    main()
