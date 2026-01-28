# ABOUTME: Flexible survey loader that handles multi-file datasets and varied field names.
# ABOUTME: Automatically detects and joins related CSV files based on common keys.

import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import re


class FlexibleSurveyLoader:
    """
    Load survey data from various file formats and naming conventions.
    Handles multi-file datasets by automatically detecting and joining on common keys.
    """

    # Field name patterns for fuzzy matching
    FIELD_PATTERNS = {
        'household_id': [
            r'sampno', r'sampn', r'samp', r'household', r'hhid', r'hh_id',
            r'^id$', r'sample_?id', r'sample_?no', r'hhno', r'newid', r'diaryid'
        ],
        'person_id': [
            r'perno', r'per', r'person', r'pid', r'person_?id', r'member'
        ],
        'mode': [
            r'mode', r'transp', r'travel_?mode', r'trip_?mode',
            r'tran1', r'tran2', r'tran', r'^trans$',
            r'trppub', r'pubtype', r'pubtrans', r'trptrans',
            r'wk_mode', r'smode'
        ],
        'time': [
            r'time', r'hour', r'depart', r'arriv', r'start', r'end',
            r'strt', r'dep', r'arr', r'leave', r'gend',
            r'beg', r'begin', r'timearri', r'timedepa',
            r'actendhr', r'actendmn', r'starthr', r'endhr',
            r'strttime', r'endtime', r'begtime'
        ],
        'zip': [
            r'zip', r'zipcode', r'zip_?code', r'geozip', r'postal',
            r'hh_?zip', r'homezip', r'wrkzip', r'jzip'
        ],
        'county': [
            r'county', r'cnty', r'hhcnty', r'hh_?cnty', r'gccnty',
            r'origco', r'destco', r'homeco'
        ],
        'fips': [
            r'fips', r'ctfip', r'ct_?fip', r'tract',
            r'taz', r'zone', r'av_zone'
        ],
        'location_id': [
            r'locno', r'loc_?no', r'location', r'place_?no', r'plano',
            r'actno', r'origtype', r'desttype'
        ]
    }

    def __init__(self, survey_path: Path):
        self.survey_path = survey_path
        self.csv_files = list(survey_path.rglob('*.csv'))

    def find_field(self, df: pd.DataFrame, field_type: str) -> Optional[str]:
        """Find a field matching the given type using pattern matching."""
        patterns = self.FIELD_PATTERNS.get(field_type, [])
        cols_lower = {c.lower(): c for c in df.columns}

        for pattern in patterns:
            for col_lower, col_orig in cols_lower.items():
                if re.search(pattern, col_lower):
                    return col_orig
        return None

    def find_all_fields(self, df: pd.DataFrame, field_type: str) -> List[str]:
        """Find all fields matching the given type."""
        patterns = self.FIELD_PATTERNS.get(field_type, [])
        cols_lower = {c.lower(): c for c in df.columns}

        matches = []
        for pattern in patterns:
            for col_lower, col_orig in cols_lower.items():
                if re.search(pattern, col_lower) and col_orig not in matches:
                    matches.append(col_orig)
        return matches

    def detect_file_type(self, file_path: Path) -> Dict[str, bool]:
        """Detect what required fields are present in a file."""
        try:
            df = pd.read_csv(file_path, nrows=0)

            return {
                'household_id': self.find_field(df, 'household_id') is not None,
                'person_id': self.find_field(df, 'person_id') is not None,
                'mode': self.find_field(df, 'mode') is not None,
                'time': len(self.find_all_fields(df, 'time')) > 0,
                'zip': self.find_field(df, 'zip') is not None,
                'county': self.find_field(df, 'county') is not None,
                'fips': self.find_field(df, 'fips') is not None,
                'location_id': self.find_field(df, 'location_id') is not None,
                'file': file_path.name,
                'path': file_path
            }
        except Exception as e:
            return {'error': str(e), 'file': file_path.name, 'path': file_path}

    def analyze_survey(self) -> Dict:
        """Analyze all CSV files in survey directory."""
        analysis = {
            'files': [],
            'trip_files': [],
            'location_files': [],
            'household_files': []
        }

        for csv_file in self.csv_files:
            file_info = self.detect_file_type(csv_file)
            if 'error' not in file_info:
                analysis['files'].append(file_info)

                # Categorize files
                has_trip_data = file_info['mode'] or file_info['time']
                has_location = file_info['zip'] or file_info['county'] or file_info['fips']
                has_household = file_info['household_id']

                if has_trip_data and has_household:
                    analysis['trip_files'].append(file_info)
                if has_location and file_info['location_id']:
                    analysis['location_files'].append(file_info)
                if has_household and not has_trip_data:
                    analysis['household_files'].append(file_info)

        return analysis

    def find_common_keys(self, df1: pd.DataFrame, df2: pd.DataFrame) -> List[str]:
        """Find common columns that could be join keys."""
        common = []
        for col in df1.columns:
            if col in df2.columns:
                # Check if it looks like an ID field
                col_lower = col.lower()
                if any(x in col_lower for x in ['no', 'id', 'samp', 'loc', 'per']):
                    common.append(col)
        return common

    def load_and_merge(self) -> Tuple[Optional[pd.DataFrame], Dict]:
        """
        Load survey data, automatically merging multiple files if needed.

        Returns:
            (DataFrame or None, metadata dict with loading info)
        """
        analysis = self.analyze_survey()

        if not analysis['files']:
            return None, {'error': 'No CSV files found'}

        # Strategy 1: Try to find a single file with all required data
        for file_info in analysis['files']:
            has_required = (
                file_info['household_id'] and
                file_info['mode'] and
                file_info['time'] and
                (file_info['zip'] or file_info['county'] or file_info['fips'])
            )

            if has_required:
                df = pd.read_csv(file_info['path'])
                return df, {
                    'strategy': 'single_file',
                    'file': file_info['file'],
                    'rows': len(df)
                }

        # Strategy 2: Try to merge trip file with location file
        if analysis['trip_files'] and analysis['location_files']:
            trip_file = analysis['trip_files'][0]
            loc_file = analysis['location_files'][0]

            try:
                trip_df = pd.read_csv(trip_file['path'])
                loc_df = pd.read_csv(loc_file['path'])

                # Find join keys
                join_keys = self.find_common_keys(trip_df, loc_df)

                if join_keys:
                    # Use first common key (usually locno)
                    merged_df = trip_df.merge(loc_df, on=join_keys[0], how='left')

                    return merged_df, {
                        'strategy': 'trip_location_merge',
                        'trip_file': trip_file['file'],
                        'location_file': loc_file['file'],
                        'join_key': join_keys[0],
                        'rows': len(merged_df)
                    }
            except Exception as e:
                pass

        # Strategy 3: Try to merge household location onto trip data
        if analysis['trip_files'] and analysis['household_files']:
            trip_file = analysis['trip_files'][0]
            hh_file = analysis['household_files'][0]

            try:
                trip_df = pd.read_csv(trip_file['path'])
                hh_df = pd.read_csv(hh_file['path'])

                # Find household ID in both
                trip_hhid = self.find_field(trip_df, 'household_id')
                hh_hhid = self.find_field(hh_df, 'household_id')

                if trip_hhid and hh_hhid:
                    # Select location columns from household
                    loc_cols = []
                    for field_type in ['zip', 'county', 'fips']:
                        col = self.find_field(hh_df, field_type)
                        if col:
                            loc_cols.append(col)

                    if loc_cols:
                        hh_subset = hh_df[[hh_hhid] + loc_cols]
                        merged_df = trip_df.merge(hh_subset,
                                                 left_on=trip_hhid,
                                                 right_on=hh_hhid,
                                                 how='left')

                        return merged_df, {
                            'strategy': 'trip_household_merge',
                            'trip_file': trip_file['file'],
                            'household_file': hh_file['file'],
                            'join_key': trip_hhid,
                            'added_fields': loc_cols,
                            'rows': len(merged_df)
                        }
            except Exception as e:
                pass

        # Strategy 4: Return best available file even if incomplete
        if analysis['trip_files']:
            best_file = analysis['trip_files'][0]
            df = pd.read_csv(best_file['path'])
            return df, {
                'strategy': 'partial_data',
                'file': best_file['file'],
                'warning': 'Some required fields may be missing',
                'rows': len(df)
            }

        # Fallback: Return largest file
        if analysis['files']:
            largest = max(analysis['files'], key=lambda f: f['path'].stat().st_size)
            df = pd.read_csv(largest['path'])
            return df, {
                'strategy': 'largest_file',
                'file': largest['file'],
                'warning': 'Using largest file, may be incomplete',
                'rows': len(df)
            }

        return None, {'error': 'Could not load survey data'}

    def extract_standardized_fields(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        Extract and standardize field names from loaded dataframe.

        Returns dict mapping standard names to actual column names.
        """
        field_map = {}

        # Required fields
        field_map['household_id'] = self.find_field(df, 'household_id')
        field_map['person_id'] = self.find_field(df, 'person_id')
        field_map['mode'] = self.find_field(df, 'mode')

        # Time fields - get all and pick best
        time_fields = self.find_all_fields(df, 'time')
        if time_fields:
            # Prefer depart > arrive > other
            for preferred in ['depart', 'arriv', 'start', 'end']:
                for field in time_fields:
                    if preferred in field.lower():
                        field_map['time'] = field
                        break
                if 'time' in field_map:
                    break
            if 'time' not in field_map:
                field_map['time'] = time_fields[0]

        # Location fields - prefer ZIP > County > FIPS
        field_map['zip'] = self.find_field(df, 'zip')
        field_map['county'] = self.find_field(df, 'county')
        field_map['fips'] = self.find_field(df, 'fips')

        # Additional useful fields
        field_map['location_id'] = self.find_field(df, 'location_id')

        return field_map


def load_survey_flexible(survey_path: Path) -> Tuple[Optional[pd.DataFrame], Dict, Dict]:
    """
    Convenience function to load a survey using flexible loader.

    Returns:
        (DataFrame, metadata, field_mapping)
    """
    loader = FlexibleSurveyLoader(survey_path)
    df, metadata = loader.load_and_merge()

    if df is not None:
        field_map = loader.extract_standardized_fields(df)
        return df, metadata, field_map

    return None, metadata, {}


if __name__ == '__main__':
    # Test with a known survey
    import sys
    if len(sys.argv) > 1:
        survey_name = sys.argv[1]
        base_path = Path('data/transit_surveys/metro/extracted')
        survey_path = base_path / survey_name

        print(f"Testing flexible loader on: {survey_name}")
        print("="*70)

        df, metadata, field_map = load_survey_flexible(survey_path)

        print(f"\nMetadata: {metadata}")
        print(f"\nField mapping:")
        for std_name, actual_name in field_map.items():
            if actual_name:
                print(f"  {std_name} → {actual_name}")

        if df is not None:
            print(f"\nLoaded {len(df):,} rows")
            print(f"Columns: {list(df.columns)[:10]}...")
