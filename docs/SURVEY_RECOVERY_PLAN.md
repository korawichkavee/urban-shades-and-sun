# Survey Recovery Plan: 12 Recoverable Surveys (677,430 trips)

## Overview

12 surveys were excluded from standardization despite having all required fields in their XML metadata. This plan details the specific steps to recover them.

**Target surveys:**
1. Los Angeles 2001 - 190,049 trips
2. Washington DC 1968 - 149,505 trips
3. San Francisco 1990 - 70,774 trips
4. Detroit 1994 - 65,535 trips
5. Salt Lake City 1993 - 49,282 trips
6. Boston 1991 - 39,300 trips
7. Kentuckiana 2001 - 30,891 trips
8. Baltimore 2001 - 27,366 trips
9. Idaho 2002 - 27,192 trips
10. Anchorage 2002 - 15,031 trips
11. Philadelphia 2000 - 10,391 trips
12. Baltimore 1977 - 2,114 trips

**Total recoverable:** 677,430 trips (+86% increase over current 785k)

## Step 1: Map XML Field Names to Actual CSV Columns

### 1.1 Extract Field Names from Each Survey's Data Files

```bash
# For each survey, list actual column names in CSV files
for survey in anchorage-2002 baltimore-1977 baltimore-2001 boston-1991 \
              detroit-1994 idaho-2002 kentuckiana-2001 los-angeles-2001 \
              philadelphia-2000 salt-lake-city-1993 san-francisco-1990 \
              washington-dc-1968; do
    echo "=== $survey ==="
    python3 << EOF
import pandas as pd
from pathlib import Path

data_dir = Path('data/transit_surveys/metro/extracted/$survey/data')
csv_files = list(data_dir.glob('*.csv'))
for f in csv_files:
    df = pd.read_csv(f, nrows=0)
    print(f"{f.name}: {list(df.columns)}")
EOF
done > docs/survey_field_mapping.txt
```

### 1.2 Create Field Mapping Dictionary

Create `scripts/travel_surveys/recoverable_survey_field_mappings.py`:

```python
FIELD_MAPPINGS = {
    'anchorage-2002': {
        'time': ['arrive', 'depart', 'dephour'],
        'location': ['ctfip', 'county', 'zip'],
        'mode': ['mode', 'o_mode'],
        'household_id': ['sampno']
    },
    'baltimore-1977': {
        'time': ['tlo', 'tad', 'htlo'],
        'location': ['oblock', 'otract', 'dblock'],
        'mode': ['mode'],
        'household_id': ['batch']
    },
    'baltimore-2001': {
        'time': ['strttime', 'trvlhrs', 'trvl_min'],
        'location': ['trpblock', 'hhcnty', 'dtdistrc'],
        'mode': ['pubtrans', 'trppub'],
        'household_id': ['houseid']
    },
    'boston-1991': {
        'time': ['begtime', 'fintime'],
        'location': ['ocounty', 'otract90', 'oblock90'],
        'mode': ['mode1', 'mode2', 'mode3'],
        'household_id': ['id']
    },
    'detroit-1994': {
        'time': ['dep_hr', 'dep_min', 'dep_ampm'],
        'location': ['atr_taz', 'area'],
        'mode': ['travmode', 'acc_mode'],
        'household_id': ['id']
    },
    'idaho-2002': {
        'time': ['dep_hr', 'dep_min', 'arr_hr'],
        'location': ['ocounty', 'ozip', 'oav_zone'],
        'mode': ['mode', 'othmode'],
        'household_id': ['sampno']
    },
    'kentuckiana-2001': {
        'time': ['Leavetime', 'Leaveamorpm', 'Arrivetime'],
        'location': ['tripstartcounty', 'TripendCnty'],
        'mode': ['Modeoftravel'],
        'household_id': ['Householdnumber']
    },
    'los-angeles-2001': {
        'time': ['arrive', 'depart'],
        'location': ['county', 'region', 'fipstract'],
        'mode': ['mode', 'othmode'],
        'household_id': ['sampno']
    },
    'philadelphia-2000': {
        'time': ['atime', 'dtime', 'Gend'],
        'location': ['CPA', 'PERCPA', 'FIPS'],
        'mode': ['tran1', 'tran2', 'tran3'],
        'household_id': ['sampno']
    },
    'salt-lake-city-1993': {
        'time': ['starttrv', 'endtrav', 'starthr'],
        'location': ['origcnty', 'destcnty'],
        'mode': ['mode1', 'mode2', 'mode3'],
        'household_id': ['id', 'keyid']
    },
    'san-francisco-1990': {
        'time': ['otime', 'dtime'],
        'location': ['otract', 'oblkgrp', 'dtract'],
        'mode': ['mode'],
        'household_id': ['id']
    },
    'washington-dc-1968': {
        'time': ['begtime', 'endtime'],
        'location': ['begwalk', 'endwalk'],
        'mode': ['mode', 'bustransit'],
        'household_id': ['hhinc']
    }
}
```

### 1.3 Verify Mappings Against Actual Data

```bash
python3 << 'EOF'
from recoverable_survey_field_mappings import FIELD_MAPPINGS
import pandas as pd
from pathlib import Path

for survey, mappings in FIELD_MAPPINGS.items():
    print(f"\n=== Verifying {survey} ===")
    data_dir = Path(f'data/transit_surveys/metro/extracted/{survey}/data')
    csv_files = list(data_dir.glob('*.csv'))

    for csv_file in csv_files:
        df = pd.read_csv(csv_file, nrows=0)
        cols = set(df.columns)

        for field_type, field_names in mappings.items():
            matches = [f for f in field_names if f in cols]
            if matches:
                print(f"  {csv_file.name}: {field_type} -> {matches}")
EOF
```

## Step 2: Extend Standardization Script Field Patterns

### 2.1 Update `scripts/travel_surveys/merge_metro_surveys.py`

Locate the field pattern matching section and add new patterns:

```python
# TIME FIELD PATTERNS (add these)
TIME_PATTERNS = [
    # Existing patterns
    'time', 'strttime', 'endtime', 'deptime', 'arrtime',
    # NEW patterns from XML analysis
    'arrive', 'depart', 'dephour',  # anchorage-2002
    'tlo', 'tad', 'htlo',  # baltimore-1977
    'trvlhrs', 'trvl_min',  # baltimore-2001
    'begtime', 'fintime',  # boston-1991, washington-dc-1968
    'dep_hr', 'dep_min', 'dep_ampm',  # detroit-1994, idaho-2002
    'arr_hr', 'arr_min',  # idaho-2002
    'leavetime', 'leaveamorpm', 'arrivetime',  # kentuckiana-2001
    'atime', 'dtime', 'gend',  # philadelphia-2000
    'starttrv', 'endtrav', 'starthr',  # salt-lake-city-1993
    'otime',  # san-francisco-1990
]

# LOCATION FIELD PATTERNS (add these)
LOCATION_PATTERNS = [
    # Existing patterns
    'zip', 'county', 'fips', 'cnty', 'geoid',
    # NEW patterns from XML analysis
    'ctfip',  # anchorage-2002
    'oblock', 'otract', 'dblock', 'dtract',  # baltimore-1977, san-francisco-1990
    'trpblock', 'hhcnty', 'dtdistrc',  # baltimore-2001
    'otract90', 'oblock90',  # boston-1991
    'atr_taz', 'area',  # detroit-1994
    'ozip', 'oav_zone',  # idaho-2002
    'tripstartcounty', 'tripendcnty',  # kentuckiana-2001
    'region', 'fipstract',  # los-angeles-2001
    'cpa', 'percpa',  # philadelphia-2000
    'origcnty', 'destcnty',  # salt-lake-city-1993
    'oblkgrp',  # san-francisco-1990
    'begwalk', 'endwalk',  # washington-dc-1968
]

# MODE FIELD PATTERNS (add these)
MODE_PATTERNS = [
    # Existing patterns
    'mode', 'tran', 'pubtrans',
    # NEW patterns from XML analysis
    'o_mode', 'o_getto',  # anchorage-2002
    'trandist', 'tranivt',  # baltimore-1977
    'trppub', 'pubtype',  # baltimore-2001
    'mode1', 'mode2', 'mode3',  # boston-1991, salt-lake-city-1993
    'travmode', 'acc_mode',  # detroit-1994
    'othmode',  # idaho-2002, los-angeles-2001
    'modeoftravel',  # kentuckiana-2001
    'tran1', 'tran2', 'tran3',  # philadelphia-2000
    'transrte',  # los-angeles-2001
    'tranoper',  # san-francisco-1990
    'bustransit', 'recmode',  # washington-dc-1968
]

# HOUSEHOLD ID PATTERNS (add these)
HHID_PATTERNS = [
    # Existing patterns
    'sampno', 'hhid', 'household', 'newid',
    # NEW patterns from XML analysis
    'hhmem', 'pertp',  # anchorage-2002
    'batch', 'cell',  # baltimore-1977
    'houseid', 'firstper',  # baltimore-2001
    'id', 'keyid',  # boston-1991, detroit-1994, salt-lake-city-1993, san-francisco-1990
    'householdnumber',  # kentuckiana-2001
    'hhvu',  # philadelphia-2000
    'hhinc',  # washington-dc-1968
]
```

### 2.2 Handle Split Time Fields

Some surveys have time split into hour/minute/am-pm. Add handler:

```python
def combine_split_time_fields(df):
    """Combine split time fields (hour, minute, am/pm) into single time field."""

    # Pattern 1: dep_hr, dep_min, dep_ampm (detroit-1994, idaho-2002)
    if all(col in df.columns for col in ['dep_hr', 'dep_min', 'dep_ampm']):
        df['time'] = df.apply(lambda row:
            convert_12hr_to_24hr(row['dep_hr'], row['dep_ampm']) * 60 + row['dep_min']
            if pd.notna(row['dep_hr']) else None, axis=1)

    # Pattern 2: Leavetime, Leaveamorpm (kentuckiana-2001)
    elif all(col in df.columns for col in ['Leavetime', 'Leaveamorpm']):
        # Parse time string with am/pm
        df['time'] = df.apply(lambda row:
            parse_time_with_ampm(row['Leavetime'], row['Leaveamorpm'])
            if pd.notna(row['Leavetime']) else None, axis=1)

    return df

def convert_12hr_to_24hr(hour_12, ampm):
    """Convert 12-hour format to 24-hour."""
    hour = int(hour_12)
    if ampm in ['PM', 'pm', 2]:
        if hour != 12:
            hour += 12
    elif hour == 12:
        hour = 0
    return hour
```

### 2.3 Handle Multiple Mode Columns

Some surveys have mode1, mode2, mode3. Add prioritization:

```python
def extract_primary_mode(df):
    """Extract primary mode from multiple mode columns."""

    if all(col in df.columns for col in ['mode1', 'mode2', 'mode3']):
        # Use mode1 as primary, fall back to mode2, then mode3
        df['mode'] = df['mode1'].fillna(df['mode2']).fillna(df['mode3'])
    elif all(col in df.columns for col in ['tran1', 'tran2', 'tran3']):
        df['mode'] = df['tran1'].fillna(df['tran2']).fillna(df['tran3'])

    return df
```

## Step 3: Test on 2 Sample Surveys

### 3.1 Test Boston-1991 (39,300 trips)

```bash
python3 << 'EOF'
import pandas as pd
from pathlib import Path

# Load Boston data
survey_dir = Path('data/transit_surveys/metro/extracted/boston-1991/data')
csv_files = list(survey_dir.glob('*.csv'))

print("Boston-1991 test:")
for csv_file in csv_files:
    df = pd.read_csv(csv_file)
    print(f"\n{csv_file.name}: {len(df)} rows")

    # Check for mapped fields
    time_fields = [c for c in df.columns if c.lower() in ['begtime', 'fintime']]
    loc_fields = [c for c in df.columns if c.lower() in ['ocounty', 'otract90', 'oblock90']]
    mode_fields = [c for c in df.columns if c.lower() in ['mode1', 'mode2', 'mode3']]
    hhid_fields = [c for c in df.columns if c.lower() in ['id', 'sampno']]

    print(f"  Time fields: {time_fields}")
    print(f"  Location fields: {loc_fields}")
    print(f"  Mode fields: {mode_fields}")
    print(f"  HH ID fields: {hhid_fields}")

    if time_fields and loc_fields and mode_fields and hhid_fields:
        print("  ✓ ALL REQUIRED FIELDS FOUND")

        # Check data quality
        for field in time_fields[:1]:
            pct = 100 * df[field].notna().sum() / len(df)
            print(f"  {field}: {pct:.1f}% non-null")
EOF
```

### 3.2 Test Baltimore-2001 (27,366 trips)

```bash
# Same process as Boston, checking for:
# - strttime, trvlhrs, trvl_min (time)
# - trpblock, hhcnty, dtdistrc (location)
# - pubtrans, trppub (mode)
# - houseid (household_id)
```

### 3.3 Verify Test Results

Expected output:
- All required fields found in CSV
- >90% non-null for time, location, household_id
- >70% non-null for mode (acceptable threshold)

## Step 4: Run Full Standardization

### 4.1 Update Standardization Script

Edit `scripts/travel_surveys/merge_metro_surveys.py`:

```python
# Add at top
from recoverable_survey_field_mappings import FIELD_MAPPINGS

# In standardization function, add special handling:
def standardize_survey(df, survey_name, logger):
    """Standardize survey fields using extended patterns."""

    # Check if this is a recoverable survey with custom mappings
    if survey_name in FIELD_MAPPINGS:
        logger.info(f"Using custom field mappings for {survey_name}")
        df = apply_custom_mappings(df, survey_name, FIELD_MAPPINGS[survey_name])

    # Handle split time fields
    df = combine_split_time_fields(df)

    # Handle multiple mode columns
    df = extract_primary_mode(df)

    # Continue with standard processing...
    return standardize_fields(df)
```

### 4.2 Run Standardization on All 12 Surveys

```bash
# Create new standardization output
python scripts/travel_surveys/merge_metro_surveys.py \
    --mode flexible \
    --output data/transit_surveys/processed/metro_surveys_standardized_flexible_v2.csv

# Check results
python3 << 'EOF'
import pandas as pd

df = pd.read_csv('data/transit_surveys/processed/metro_surveys_standardized_flexible_v2.csv')
print(f"Total trips: {len(df):,}")
print(f"Surveys: {df['survey'].nunique()}")

# Check for newly recovered surveys
new_surveys = ['anchorage-2002', 'baltimore-1977', 'baltimore-2001',
               'boston-1991', 'detroit-1994', 'idaho-2002',
               'kentuckiana-2001', 'los-angeles-2001', 'philadelphia-2000',
               'salt-lake-city-1993', 'san-francisco-1990', 'washington-dc-1968']

for survey in new_surveys:
    count = len(df[df['survey'] == survey])
    if count > 0:
        print(f"✓ {survey}: {count:,} trips")
    else:
        print(f"✗ {survey}: MISSING")
EOF
```

### 4.3 Validate Data Quality

```bash
python3 << 'EOF'
import pandas as pd

df = pd.read_csv('data/transit_surveys/processed/metro_surveys_standardized_flexible_v2.csv')

print("Data quality check:")
for col in ['lat', 'lon', 'datetime', 'walk_only']:
    pct = 100 * df[col].notna().sum() / len(df)
    print(f"  {col}: {pct:.1f}% non-null")

# Check for each recovered survey
recovered = ['boston-1991', 'baltimore-2001']  # Start with test surveys
for survey in recovered:
    subset = df[df['survey'] == survey]
    print(f"\n{survey}: {len(subset):,} trips")
    for col in ['lat', 'lon', 'datetime', 'walk_only']:
        pct = 100 * subset[col].notna().sum() / len(subset)
        print(f"  {col}: {pct:.1f}%")
EOF
```

## Step 5: Add UTCI Annotations

### 5.1 Run UTCI Annotation on New Standardized Data

```bash
python scripts/travel_surveys/add_utci_deduped.py \
    --input data/transit_surveys/processed/metro_surveys_standardized_flexible_v2.csv \
    --output data/transit_surveys/processed/metro_surveys_standardized_flexible_v2_with_utci.csv \
    --checkpoint data/transit_surveys/processed/utci_checkpoint_v2.csv
```

**Note:** This will take several hours for 677k new trips

### 5.2 Filter Invalid UTCI Values

```bash
python3 << 'EOF'
import pandas as pd

df = pd.read_csv('data/transit_surveys/processed/metro_surveys_standardized_flexible_v2_with_utci.csv')

print(f"Before filtering: {len(df):,} trips")

# Filter to reasonable UTCI range (-40 to 55°C)
df_filtered = df[(df['utci_C'] >= -40) & (df['utci_C'] <= 55)].copy()

print(f"After filtering: {len(df_filtered):,} trips")
print(f"Removed: {len(df) - len(df_filtered):,} trips ({100*(len(df)-len(df_filtered))/len(df):.2f}%)")

df_filtered.to_csv('data/transit_surveys/processed/metro_surveys_standardized_flexible_v2_with_utci_filtered.csv', index=False)
EOF
```

## Step 6: Regenerate Person-Day Data

### 6.1 Create New Person-Day Trip Rates

```bash
python3 << 'EOF'
import pandas as pd

df = pd.read_csv('data/transit_surveys/processed/metro_surveys_standardized_flexible_v2_with_utci_filtered.csv', low_memory=False)

# Parse datetime
df['datetime'] = pd.to_datetime(df['datetime'])
df['date'] = df['datetime'].dt.date

# Group by person-day
person_days = df.groupby(['survey', 'household_id', 'person_id', 'date']).agg({
    'utci_C': 'mean',
    'walk_only': 'sum',
    'contains_walk': 'sum'
}).reset_index()

# Add total trips
person_days['total_trips'] = df.groupby(['survey', 'household_id', 'person_id', 'date']).size().values

print(f"Person-days: {len(person_days):,}")
print(f"Mean trips/day: {person_days['total_trips'].mean():.2f}")
print(f"Mean walk trips/day: {person_days['walk_only'].mean():.2f}")

person_days.to_csv('data/transit_surveys/processed/person_day_trip_rates_v2.csv', index=False)
print("Saved to: person_day_trip_rates_v2.csv")
EOF
```

## Step 7: Regenerate City-Specific Walk Rate Plots

### 7.1 Run Plot Generation Script

```bash
python scripts/travel_surveys/plot_p_walk_by_city.py \
    --input data/transit_surveys/processed/person_day_trip_rates_v2.csv \
    --output-dir outputs/walk_rate_by_city_v2
```

### 7.2 Compare Old vs New

```bash
python3 << 'EOF'
import pandas as pd

old = pd.read_csv('data/transit_surveys/processed/person_day_trip_rates.csv')
new = pd.read_csv('data/transit_surveys/processed/person_day_trip_rates_v2.csv')

print("Comparison:")
print(f"Old: {len(old):,} person-days, {old['survey'].nunique()} surveys")
print(f"New: {len(new):,} person-days, {new['survey'].nunique()} surveys")
print(f"Gain: +{len(new)-len(old):,} person-days (+{100*(len(new)-len(old))/len(old):.1f}%)")

print("\nNew metro areas:")
old_surveys = set(old['survey'].unique())
new_surveys = set(new['survey'].unique())
added = new_surveys - old_surveys
for survey in sorted(added):
    count = len(new[new['survey'] == survey])
    print(f"  + {survey}: {count:,} person-days")
EOF
```

## Step 8: Update Summary Documentation

### 8.1 Create New Survey Summary

Update `docs/METRO_SURVEY_SUMMARY.md` with:
- New survey count (25 → 37 surveys)
- New trip count (785k → 1.46M trips)
- List of recovered surveys
- Geographic coverage expansion

### 8.2 Update Recovery Documentation

Update `docs/RECOVERY_COMPARISON.md` with:
- Actual recovery numbers
- Which surveys were successfully recovered
- Any surveys that failed and why

## Expected Outcomes

### Dataset Growth
- **Surveys:** 25 → 37 (+48%)
- **Trips:** 785,353 → 1,462,783 (+86%)
- **Person-days:** ~179k → ~300k (+67% estimated)

### Geographic Expansion
- **New metros:** Los Angeles, San Francisco, Washington DC, Boston, Detroit, Salt Lake City, Philadelphia, Baltimore, Anchorage, Idaho, Kentuckiana
- **Better climate diversity:** More cold climate (Anchorage, Idaho), more coastal cities, more major metros

### Analysis Improvements
- More robust city-specific temperature sensitivity estimates
- Better coverage of temperature ranges within cities
- Larger sample sizes for rare temperature conditions

## Troubleshooting

### Issue: Field not found in CSV
**Solution:** Check actual column name case-sensitivity, check if field is in different CSV file (e.g., person file vs trip file)

### Issue: Time field format incompatible
**Solution:** Add custom parser for that survey's time format in `combine_split_time_fields()`

### Issue: Location field doesn't geocode
**Solution:** May need county name → FIPS lookup, or use alternative location field (e.g., tract instead of ZIP)

### Issue: Mode values don't map to walk
**Solution:** Check XML for mode coding scheme, update mode mapping dictionary

### Issue: High missing data rate
**Solution:** If >30% missing for required field, may need to exclude survey or find alternative field

## Success Criteria

- ✓ All 12 surveys appear in standardized output
- ✓ Each survey has >90% non-null location data
- ✓ Each survey has >90% non-null time data
- ✓ Each survey has >70% non-null mode data
- ✓ UTCI annotation completes with <1% invalid values
- ✓ Person-day data shows reasonable trip rates (2-6 trips/day)
- ✓ City-specific plots show smooth temperature curves

## Estimated Timeline

- Step 1-2 (Mapping & Script Updates): 1-2 hours
- Step 3 (Testing): 30 minutes
- Step 4 (Full Standardization): 30 minutes
- Step 5 (UTCI Annotation): 3-6 hours (API dependent)
- Step 6-7 (Analysis & Plots): 30 minutes
- Step 8 (Documentation): 30 minutes

**Total:** 6-10 hours (mostly waiting for UTCI API)
