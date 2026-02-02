# ABOUTME: Prepare recoverable surveys for UTCI annotation with proper date sampling
# ABOUTME: Extracts day_of_week from source, uses household-based sampling for dates
# ABOUTME: Uses GeographicSampler for reproducible location sampling within ZIP/county boundaries

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from recoverable_survey_field_mappings import TRIP_FILES
from geographic_sampler import GeographicSampler
import pandas as pd
import numpy as np
from datetime import datetime
import calendar
import random
import logging


RANDOM_SEED = 42
MISSING_CODES = [-1, -7, -8, -9, -99, -999, -9999, -99999, -999999, -9999999,
                  99, 999, 9999, 99999, 999999, 9999999]


def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    return logging.getLogger(__name__)


# Survey metadata
SURVEY_METADATA = {
    'anchorage-2002': {'year': 2002, 'month': 6},
    'baltimore-1977': {'year': 1977, 'month': 6},
    'boston-1991': {'year': 1991, 'month': 6},
    'detroit-1994': {'year': 1994, 'month': 3},
    'idaho-2002': {'year': 2002, 'month': 6},
    'kentuckiana-2001': {'year': 2001, 'month': 10},
    'los-angeles-2001': {'year': 2001, 'month': 6},
    'philadelphia-2000': {'year': 2000, 'month': 6},
    'salt-lake-city-1993': {'year': 1993, 'month': 6},
    'san-francisco-1990': {'year': 1990, 'month': 5},
    'washington-dc-1968': {'year': 1968, 'month': 8},
}

# Day of week column names by survey (if available)
DAY_OF_WEEK_COLS = {
    'los-angeles-2001': 'dayno',
    'san-francisco-1990': 'travday',
    'washington-dc-1968': 'wrktravday',
}

# State abbreviations for each survey (for geographic sampler fallback)
SURVEY_STATES = {
    'anchorage-2002': 'AK',
    'baltimore-1977': 'MD',
    'boston-1991': 'MA',
    'detroit-1994': 'MI',
    'idaho-2002': 'ID',
    'kentuckiana-2001': 'KY',
    'los-angeles-2001': 'CA',
    'philadelphia-2000': 'PA',
    'salt-lake-city-1993': 'UT',
    'san-francisco-1990': 'CA',
    'washington-dc-1968': 'DC',
}

# State centroids for geographic sampler
STATE_CENTROIDS = pd.DataFrame([
    {'state': 'AK', 'lat': 64.2008, 'lon': -149.4937},  # Alaska
    {'state': 'MD', 'lat': 39.0458, 'lon': -76.6413},   # Maryland
    {'state': 'MA', 'lat': 42.4072, 'lon': -71.3824},   # Massachusetts
    {'state': 'MI', 'lat': 44.3148, 'lon': -85.6024},   # Michigan
    {'state': 'ID', 'lat': 44.0682, 'lon': -114.7420},  # Idaho
    {'state': 'KY', 'lat': 37.8393, 'lon': -84.2700},   # Kentucky
    {'state': 'CA', 'lat': 36.7783, 'lon': -119.4179},  # California
    {'state': 'PA', 'lat': 41.2033, 'lon': -77.1945},   # Pennsylvania
    {'state': 'UT', 'lat': 39.3210, 'lon': -111.0937},  # Utah
    {'state': 'DC', 'lat': 38.9072, 'lon': -77.0369},   # District of Columbia
])

# County code mappings for surveys that use abbreviations or non-FIPS codes
COUNTY_MAPPINGS = {
    # Massachusetts counties (boston-1991 uses numeric codes)
    'MA': {
        '1': '25001',   # Barnstable
        '3': '25003',   # Berkshire
        '5': '25005',   # Bristol
        '7': '25007',   # Dukes
        '9': '25009',   # Essex
        '11': '25011',  # Franklin
        '13': '25013',  # Hampden
        '15': '25015',  # Hampshire
        '17': '25017',  # Middlesex
        '19': '25019',  # Nantucket
        '21': '25021',  # Norfolk
        '23': '25023',  # Plymouth
        '25': '25025',  # Suffolk
        '27': '25027',  # Worcester
    },
    # California counties (los-angeles-2001 uses numeric codes 1-6)
    'CA': {
        '1': '06037',   # Los Angeles
        '2': '06059',   # Orange
        '3': '06065',   # Riverside
        '4': '06071',   # San Bernardino
        '5': '06111',   # Ventura
        '6': '06037',   # Los Angeles (additional areas)
    },
    # Idaho counties (idaho-2002 uses county names)
    'ID': {
        'ADA': '16001',
        'CANYON': '16027',
        'GEM': '16045',
        'OWYHEE': '16073',
        'PAYETTE': '16075',
        'BOISE': '16015',
    },
    # Kentucky/Indiana counties (kentuckiana-2001 uses abbreviations)
    'KY': {
        'JE': '21111',  # Jefferson (Louisville)
        'OL': '21185',  # Oldham
        'BU': '21029',  # Bullitt
        'SP': '21215',  # Spencer
        'SH': '21211',  # Shelby
    },
    # Utah counties (salt-lake-city-1993 uses abbreviations)
    'UT': {
        'SL': '49035',  # Salt Lake
        'DV': '49011',  # Davis
        'UT': '49049',  # Utah
        'WB': '49057',  # Weber
        'TO': '49045',  # Tooele
    },
    # California counties for San Francisco (hometrct -> county via first 5 digits)
    # Tract format: SSCCCTTTTTT where SS=state, CCC=county, TTTTTT=tract
    # For CA (06), tracts starting with 06075 = San Francisco County
}


def construct_datetime_with_sampling(household_id, year, month, time_minutes, day_of_week=None):
    """
    Construct datetime using household-based sampling across survey month.

    If day_of_week is available, samples from matching days.
    Otherwise, samples uniformly across all days in month.
    """
    num_days = calendar.monthrange(year, month)[1]

    if day_of_week is not None and day_of_week not in MISSING_CODES:
        # Find matching days for this day of week
        try:
            dow = int(float(day_of_week))
            if 1 <= dow <= 7:
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
                    # Fallback to uniform sampling
                    rng = random.Random(RANDOM_SEED + hash(str(household_id) + str(year)) % 1000000)
                    day = rng.randint(1, num_days)
            else:
                # Invalid dow, use uniform sampling
                rng = random.Random(RANDOM_SEED + hash(str(household_id) + str(year)) % 1000000)
                day = rng.randint(1, num_days)
        except (ValueError, TypeError):
            # Error parsing, use uniform sampling
            rng = random.Random(RANDOM_SEED + hash(str(household_id) + str(year)) % 1000000)
            day = rng.randint(1, num_days)
    else:
        # No day_of_week: uniform sampling
        rng = random.Random(RANDOM_SEED + hash(str(household_id) + str(year)) % 1000000)
        day = rng.randint(1, num_days)

    # Convert time_minutes to hour and minute
    try:
        time_mins = int(float(time_minutes))
        if time_mins < 0 or time_mins >= 1440:
            return None

        hours = time_mins // 60
        minutes = time_mins % 60

        return datetime(year, month, day, hours, minutes)
    except (ValueError, TypeError):
        return None


def parse_location_code(location, location_type, survey_name):
    """
    Parse location code to ZIP or county FIPS format.

    Returns: (zip_code, county_fips, state)
    """
    if pd.isna(location):
        return None, None, None

    state = SURVEY_STATES.get(survey_name)

    # County FIPS codes (5 digits) - direct FIPS like anchorage ctfip
    if 'ctfip' in location_type.lower():
        try:
            # Try to convert to FIPS (numeric codes)
            fips = str(int(float(location))).zfill(5)
            if len(fips) == 5:
                return None, fips, None
        except (ValueError, TypeError):
            pass

    # County codes that need mapping (boston, los-angeles, etc.)
    if 'county' in location_type.lower() or 'cnty' in location_type.lower():
        # Try direct numeric county code with state prefix
        try:
            county_num = str(int(float(location)))
            if state in COUNTY_MAPPINGS and county_num in COUNTY_MAPPINGS[state]:
                return None, COUNTY_MAPPINGS[state][county_num], None
        except (ValueError, TypeError):
            pass

        # Try county name (Idaho case - strip " COUNTY" suffix)
        try:
            county_name = str(location).strip().upper()
            # Remove " COUNTY" suffix if present
            county_name_clean = county_name.replace(' COUNTY', '').replace('COUNTY', '')
            if state in COUNTY_MAPPINGS and county_name_clean in COUNTY_MAPPINGS[state]:
                return None, COUNTY_MAPPINGS[state][county_name_clean], None
        except (ValueError, TypeError):
            pass

        # Try county abbreviation (kentuckiana, salt-lake-city)
        try:
            county_abbr = str(location).strip().upper()
            if state in COUNTY_MAPPINGS and county_abbr in COUNTY_MAPPINGS[state]:
                return None, COUNTY_MAPPINGS[state][county_abbr], None
        except (ValueError, TypeError):
            pass

    # ZIP codes (5 digits)
    if 'zip' in location_type.lower():
        try:
            zip_code = str(int(float(location))).zfill(5)
            if len(zip_code) == 5:
                return zip_code, None, None
        except (ValueError, TypeError):
            pass

    # Tract codes (extract county FIPS)
    if 'tract' in location_type.lower() or 'trct' in location_type.lower():
        try:
            tract_str = str(int(float(location)))
            # SF 1990 uses 6-digit tracts (CCTTTT) where CC is last 2 digits of county FIPS
            # For San Francisco (CA), we need to map to 06075
            if survey_name == 'san-francisco-1990' and len(tract_str) == 6:
                # All SF tracts map to San Francisco County (06075)
                return None, '06075', None
            # Standard 11-digit tracts (SSCCCTTTTTT)
            elif len(tract_str) >= 11:
                county_fips = tract_str[:5]
                return None, county_fips, None
        except (ValueError, TypeError):
            pass

    # For other location types, return None (will use state fallback)
    return None, None, None


def main():
    logger = setup_logging()

    logger.info("="*80)
    logger.info("PREPARING RECOVERABLE SURVEYS FOR UTCI ANNOTATION")
    logger.info("Using household-based date sampling")
    logger.info("Using geographic sampling within ZIP/county boundaries")
    logger.info("="*80)

    # Load standardized data
    input_path = Path('data/transit_surveys/processed/recoverable_surveys_standardized.csv')
    df = pd.read_csv(input_path, low_memory=False)
    logger.info(f"Loaded {len(df):,} trips from {df['survey'].nunique()} surveys")

    # Add survey metadata
    df['survey_year'] = df['survey'].map(lambda x: SURVEY_METADATA.get(x, {}).get('year'))
    df['survey_month'] = df['survey'].map(lambda x: SURVEY_METADATA.get(x, {}).get('month'))

    # Initialize geographic sampler
    logger.info("Initializing geographic sampler...")
    project_root = Path(__file__).parent.parent.parent
    zip_shapefile = project_root / "data" / "geographic_shapefiles" / "zcta" / "tl_2023_us_zcta520.shp"
    county_shapefile = project_root / "data" / "geographic_shapefiles" / "counties" / "cb_2023_us_county_500k.shp"

    sampler = GeographicSampler(
        zip_shapefile=zip_shapefile,
        county_shapefile=county_shapefile,
        state_centroids_df=STATE_CENTROIDS,
        base_seed=RANDOM_SEED
    )

    # Add coordinates using geographic sampling
    logger.info("Sampling geographic coordinates...")
    coords_results = []
    for _, row in df.iterrows():
        # Parse location code
        zip_code, county_fips, _ = parse_location_code(row['location'], row['location_type'], row['survey'])

        # Get state for fallback
        state = SURVEY_STATES.get(row['survey'])

        # Sample location using household_id as variation key
        variation_key = str(row['household_id'])
        lat, lon, source = sampler.get_location(
            zip_code=zip_code,
            county_fips=county_fips,
            state=state,
            variation_key=variation_key
        )

        coords_results.append((lat, lon, source))

    df['lat'] = [c[0] for c in coords_results]
    df['lon'] = [c[1] for c in coords_results]
    df['location_source'] = [c[2] for c in coords_results]

    logger.info(f"Geographic sampling complete:")
    logger.info(f"  {sum(1 for c in coords_results if c[2] == 'zip'):,} from ZIP codes")
    logger.info(f"  {sum(1 for c in coords_results if c[2] == 'county'):,} from counties")
    logger.info(f"  {sum(1 for c in coords_results if c[2] == 'state'):,} from state centroids")
    logger.info(f"  {sum(1 for c in coords_results if c[0] is None):,} failed to geocode")

    # Load day_of_week from source files where available
    logger.info("Loading day_of_week from source surveys...")
    df['day_of_week'] = None

    for survey_name, dow_col in DAY_OF_WEEK_COLS.items():
        logger.info(f"  {survey_name}: extracting {dow_col}")
        trip_file = TRIP_FILES[survey_name]
        data_path = Path(f'data/transit_surveys/metro/extracted/{survey_name}/data/{trip_file}')

        source_df = pd.read_csv(data_path, low_memory=False)
        if dow_col in source_df.columns:
            # Create temporary merge key
            source_df['_merge_key'] = (
                source_df['sampno'].astype(str) + '_' +
                source_df.get('perno', source_df.get('persno', 0)).astype(str)
            )
            df.loc[df['survey'] == survey_name, '_merge_key'] = (
                df.loc[df['survey'] == survey_name, 'household_id'].astype(str) + '_' +
                df.loc[df['survey'] == survey_name, 'person_id'].astype(str)
            )

            # Merge day_of_week
            dow_map = source_df.set_index('_merge_key')[dow_col].to_dict()
            df.loc[df['survey'] == survey_name, 'day_of_week'] = (
                df.loc[df['survey'] == survey_name, '_merge_key'].map(dow_map)
            )

    if '_merge_key' in df.columns:
        df.drop(columns=['_merge_key'], inplace=True)

    # Construct datetime with sampling
    logger.info("Constructing datetime with date sampling...")
    datetimes = []
    for _, row in df.iterrows():
        metadata = SURVEY_METADATA.get(row['survey'], {})
        dt = construct_datetime_with_sampling(
            household_id=row['household_id'],
            year=metadata.get('year'),
            month=metadata.get('month'),
            time_minutes=row['time_minutes'],
            day_of_week=row.get('day_of_week')
        )
        datetimes.append(dt)

    df['datetime'] = datetimes

    # Filter out invalid datetimes
    before = len(df)
    df = df[df['datetime'].notna()].copy()
    after = len(df)
    logger.info(f"Filtered {before - after:,} trips with invalid datetime ({100*(after/before):.1f}% retained)")

    # Save output
    output_path = Path('data/transit_surveys/processed/recoverable_surveys_ready_for_utci.csv')
    df.to_csv(output_path, index=False)
    logger.info(f"Saved: {output_path}")

    # Summary
    logger.info("\n" + "="*80)
    logger.info("SUMMARY")
    logger.info("="*80)
    logger.info(f"Total trips: {len(df):,}")
    logger.info(f"\nDate range: {df['datetime'].min()} to {df['datetime'].max()}")
    logger.info(f"Unique dates: {df['datetime'].dt.date.nunique():,}")

    logger.info(f"\nBy survey:")
    for survey in sorted(df['survey'].unique()):
        subset = df[df['survey'] == survey]
        unique_dates = subset['datetime'].dt.date.nunique()
        logger.info(f"  {survey}: {len(subset):,} trips, {unique_dates} unique dates")

    logger.info(f"\n✓ Ready for UTCI annotation")


if __name__ == '__main__':
    main()
