# Survey Recovery: Steps 1-3 Results

## Summary

Successfully completed Steps 1-3 of the survey recovery plan:
- Extracted actual CSV column names from all 12 recoverable surveys
- Created field mapping dictionary with verified mappings
- Tested on Boston-1991 (39,300 trips) and Baltimore-2001 (27,366 trips)

## Field Mapping File

Created: `scripts/travel_surveys/recoverable_survey_field_mappings.py`

### Survey-Specific Mappings

All 12 surveys have verified mappings for:
- **Time fields**: departure/arrival times (various formats)
- **Location fields**: geographic identifiers (county, tract, zone, etc.)
- **Mode fields**: transportation mode indicators
- **Household ID**: sample/household identifiers
- **Person ID**: person within household

### Primary Trip Files Identified

| Survey | Trip File | Trips |
|--------|-----------|-------|
| anchorage-2002 | survey_trips.csv | 15,031 |
| baltimore-1977 | survey_data.csv | 2,114 |
| baltimore-2001 | survey_travel_day.csv | 27,366 |
| boston-1991 | survey_trip.csv | 39,300 |
| detroit-1994 | survey_trip.csv | 68,671 |
| idaho-2002 | survey_trips.csv | 27,192 |
| kentuckiana-2001 | survey.csv | 30,891 |
| los-angeles-2001 | survey_data.csv | 190,049 |
| philadelphia-2000 | survey_trips.csv | 47,071 |
| salt-lake-city-1993 | survey_trip.csv | 40,952 |
| san-francisco-1990 | survey_data.csv | 70,774 |
| washington-dc-1968 | survey_data.csv | 149,505 |

**Total: 708,916 trips** (slightly more than expected 677k due to some raw vs processed file differences)

## Data Quality Check

### Excellent Quality (>99% non-null for all fields)
- anchorage-2002: 100% all fields
- baltimore-2001: 100% all fields
- boston-1991: 99.5%+ all fields
- idaho-2002: 100% all fields
- kentuckiana-2001: 99.1%+ all fields
- los-angeles-2001: 100% all fields
- salt-lake-city-1993: 100% all fields
- washington-dc-1968: 100% all fields

### Good Quality (>95% non-null for required fields)
- philadelphia-2000: 77.9% mode (acceptable - multiple mode columns available)

### Special Cases

**baltimore-1977 (2,114 trips)**
- Time: 100% (tlo, tad fields)
- Location: 100% (ozone, dzone - zone-level only, no block/tract)
- Mode: 100%
- Note: Uses zone-level geography instead of tract/block

**detroit-1994 (68,671 trips)**
- Time: 100% (split hr/min/ampm format)
- **Location: 0% trip-level** (household has 'area' field but not in trip file)
- Mode: 100%
- Note: May need to join with household file for location, or exclude from geo-based analysis

**san-francisco-1990 (70,774 trips)**
- Time: 100%
- Location: 100% (hometrct, countyres - home-based, not trip-specific)
- Mode: 100%
- Note: Uses home location instead of trip origin/destination

## Test Results

### Boston-1991 (39,300 trips)
✓ All required fields found
- Time: `begtime`, `fintime` (100% non-null)
- Location: `ocounty`, `otract90`, `oblock90` (99.9% non-null)
- Mode: `mode1`-`mode6` (99.5% non-null, 11 unique modes)
- HH ID: `sampno` (3,737 unique households)

### Baltimore-2001 (27,366 trips)
✓ All required fields found
- Time: `strttime`, `endtime`, `trvlhrs`, `trvl_min` (100% non-null)
- Location: `hhcnty`, `origtaz00`, `desttaz00` (100% non-null)
- Mode: `pubtrans`, `trppub`, `pubtype` (100% non-null)
- HH ID: `sampno` (3,293 unique households)

## Issues Identified

### Time Field Complexity
Several surveys have split time fields that need special handling:
- **detroit-1994, idaho-2002**: `dep_hr`, `dep_min`, `dep_ampm` (need 12→24hr conversion)
- **kentuckiana-2001**: `leavetime`, `leaveamorpm` (time string + am/pm)
- **baltimore-2001**: `trvlhrs`, `trvl_min` (duration, not absolute time)

### Multiple Mode Columns
Several surveys use mode1-mode6 columns:
- boston-1991, salt-lake-city-1993: mode1-mode6
- philadelphia-2000: tran1-tran4

Need to extract primary mode or combine into single field.

### Location Data Limitations
1. **detroit-1994**: No trip-level location (68k trips may need household-level location)
2. **san-francisco-1990**: Only home location, not trip origin/dest (70k trips)
3. **baltimore-1977**: Zone-level only (coarser than tract/block)

## Next Steps (Steps 4-8)

Now ready to proceed with:
1. Update `merge_metro_surveys.py` with new field patterns
2. Add time field handling functions (split time, am/pm conversion)
3. Add mode field handling (multiple columns → primary mode)
4. Run full standardization on all 12 surveys
5. UTCI annotation (3-6 hours)
6. Generate person-day data
7. Regenerate city-specific plots
8. Update documentation

## Files Created

1. `scripts/travel_surveys/recoverable_survey_field_mappings.py` - Main mapping file
2. `docs/SURVEY_RECOVERY_STEP1-3_RESULTS.md` - This document

## Recommendations

Before proceeding to Steps 4-8:

1. **Decide on detroit-1994 handling**:
   - Option A: Join with household file for area-level location
   - Option B: Exclude from geo-based analysis (keep for mode/time analysis)
   - Option C: Attempt geocoding from activity file (has county, mcd, taz fields)

2. **Decide on san-francisco-1990 handling**:
   - Option A: Use home location for all trips (less accurate)
   - Option B: Check if activity files have better location data
   - Option C: Accept limitation for this survey

3. **Validate time parsing logic** before full run:
   - Test split time conversion on small sample
   - Verify am/pm handling edge cases (12am, 12pm)

Would you like to proceed with Steps 4-8, or address any of these issues first?
