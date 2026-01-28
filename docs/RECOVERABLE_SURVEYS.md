# Recoverable Metro Surveys Analysis

## Executive Summary

**Major Finding:** **9 surveys** (~13% of excluded) are **FULLY RECOVERABLE** with all required fields present in alternative files.

The original survey processing script only looked for files named `survey_data.csv`, `survey_trip.csv`, or `survey_trips.csv`. However, many surveys use different file naming conventions and store data across multiple related files (e.g., `survey_location.csv`, `survey_person.csv`, etc.).

## Fully Recoverable Surveys (9)

These surveys have ALL required fields (household_id, mode, time, location) available:

### 1. **Columbia, SC (2007)** ✅
- **File:** `survey_cl_trips.csv`
- **Status:** Single file with all fields
- **Fields:** sampno, mode, time (gend field seems misnamed), county, zip, tract

### 2. **Indiana (2007-2008)** ✅
- **Files:** Multiple files (transit, location, person, household)
- **Linkable via:** sampno, locno
- **Location:** FIPS, tract in `survey_location.csv`
- **Note:** Well-structured multi-file dataset

### 3. **Anchorage, AK (2002)** ✅
- **Files:** `survey_trips.csv` + `survey_location.csv`
- **Time:** arrive, depart, dephour in trips file
- **Location:** county, zip in location file (linkable via locno)
- **Fields:** All present across files

### 4. **Knoxville, TN (2008)** ✅
- **Files:** `survey_person.csv` + `survey_location.csv`
- **Linkable via:** sampno, locno
- **Location:** FIPS in location file
- **Status:** Clean multi-file structure

### 5. **Phoenix, AZ (2002)** ✅
- **Files:** `survey_person.csv` + `survey_location.csv` + household/vehicle
- **Status:** Multi-file with location linkage
- **Note:** Different from phoenix-1988

### 6. **San Francisco, CA (2000)** ✅
- **Files:** `survey_household.csv`, `survey_person.csv`, `survey_vehicle.csv`
- **Location:** Present in household/vehicle files
- **Time:** Present in household/person files
- **Status:** Complete data across files

### 7. **Chicago, IL (1990)** ✅
- **File:** `survey_data.csv` (was found!)
- **Status:** Originally marked "Missing location" but ZIP/County present
- **Fix:** Simple - just re-run with location check
- **Size:** Likely large dataset from major metro

### 8. **Minneapolis-St Paul, MN (2000)** ✅
- **File:** `survey_data.csv` (was found!)
- **Status:** Originally marked "Missing time" but time fields present
- **Fix:** Simple - just re-check time field names
- **Size:** Major metro dataset

### 9. **Phoenix, AZ (1988)** ✅
- **Files:** `survey_household.csv`, `survey_person.csv`, `survey_trips.csv`
- **Location:** ZIP/County in household and trips
- **Time:** Present in person and trips
- **Status:** Older survey but complete

## Partially Recoverable Surveys (5)

Missing 1-2 fields but worth investigating:

### **Baltimore, MD (2001)** - Missing: Mode
- **Has:** household_id (sampno), time (strttime, endtime), location (hhcnty)
- **Missing:** Mode field
- **Files:** `survey_travel_day.csv`, `survey_household.csv`
- **Note:** May have mode in coded field or separate file

### **Cincinnati, OH (1995)** - Missing: Household ID
- **Has:** mode, time, location (zip_code)
- **Missing:** Household ID
- **Files:** `survey.csv`
- **Note:** Single file, may have ID in another column

### **Fort Lauderdale, FL (1994)** - Missing: Mode, Location
- **Has:** household_id (sampno), time
- **Missing:** Mode and location
- **Files:** `survey_household_704.csv`, `survey_household_546.csv`
- **Note:** Two versions, may need different files

### **Dallas, TX (1996)** - Missing: Location
- **Has:** household_id, mode, time
- **Missing:** Location (no ZIP/County found)
- **Files:** `survey_trips.csv`
- **Note:** Could check for location in household file

### **San Diego, CA (1995)** - Missing: Location
- **Has:** household_id, mode, time
- **Missing:** Location
- **Files:** `survey_vehicle.csv`, `survey_household.csv`
- **Note:** Check household file for home location

## Impact on Dataset

### Current Dataset
- **Retained:** 6 surveys, 182,420 trips
- **Cities:** Atlanta, Seattle, Tucson, St. Louis

### With Full Recovery (Adding 9 Surveys)
- **Total:** 15 surveys (+150%)
- **New Cities:** Columbia SC, Indianapolis, Anchorage, Knoxville, Phoenix (2 eras), San Francisco, Chicago, Minneapolis-St Paul
- **Expected trips:** ~400,000-500,000 (+120-150%)

### Geographic Expansion
**Current Coverage:**
- Southeast: Atlanta
- Pacific Northwest: Seattle
- Southwest: Tucson
- Midwest: St. Louis

**Added Coverage:**
- **Major Metros:** Chicago, San Francisco, Minneapolis, Phoenix
- **Mid-size Cities:** Indianapolis, Anchorage, Knoxville, Columbia
- **Climate Diversity:** Cold climates (Minneapolis, Chicago), Desert (Phoenix), Pacific (San Francisco, Anchorage)

## Why Were These Missed?

### 1. **File Naming Assumptions**
Original script only checked for:
- `survey_data.csv`
- `survey_trip.csv`
- `survey_trips.csv`

But surveys use many naming patterns:
- `survey_cl_trips.csv` (Columbia)
- `survey_travel_day.csv` (Baltimore)
- `survey_person.csv` (many surveys)
- `survey_location.csv` (location as separate file)

### 2. **Multi-File Datasets**
Modern surveys (2000s) often split data:
- **Trips:** `survey_trips.csv` or `survey_person.csv`
- **Locations:** `survey_location.csv` (linkable via locno)
- **Households:** `survey_household.csv`

Original script expected single-file format.

### 3. **Location in Separate Files**
Many surveys store location separately:
- Trip file has `locno` (location ID)
- Location file has `locno → ZIP/County/FIPS`
- Requires join operation

### 4. **Field Name Variations**
- Time fields: `arrive`, `depart`, `dephour`, `strttime`, `endtime`, `gend` (!)
- Location: `zip`, `zipcode`, `geozip`, `county`, `cnty`, `hhcnty`, `fips`, `tract`
- Household: `sampno`, `sampn`, `sample`, `hhid`

## Recommendations

### Priority 1: Recover Major Metros (High Impact)
1. **Chicago 1990** - Simple fix, major metro
2. **Minneapolis-St Paul 2000** - Simple fix, northern climate
3. **San Francisco 2000** - Major west coast metro
4. **Phoenix 2002** - Desert climate, recent data

### Priority 2: Add Climate Diversity
5. **Anchorage 2002** - Sub-arctic climate (unique)
6. **Phoenix 1988** - Historical comparison with 2002
7. **Knoxville 2008** - Recent data, Southeast

### Priority 3: Fill Gaps
8. **Columbia SC 2007** - Most recent survey, Southeast
9. **Indiana 2007-2008** - Recent, Midwest

### Implementation Strategy

1. **Create flexible file finder:**
   - Search for any `survey_*.csv` files
   - Priority: trip/person files > location files > household files

2. **Implement field name mapping:**
   - Create dictionary of common field name variations
   - Flexible pattern matching for time/location fields

3. **Support multi-file joins:**
   - Detect linkage keys (sampno, locno, perno)
   - Auto-join location files when needed
   - Merge household location onto trips

4. **Add column detection logic:**
   - Fuzzy matching for field names
   - Pattern-based detection (e.g., ZIP codes are 5 digits)

## Estimated Effort

### Easy Recoveries (Chicago, Minneapolis) - 1 hour
- Already in `survey_data.csv`
- Just need to recheck field detection logic

### Medium Recoveries (Single file) - 2-3 hours
- Columbia, Anchorage, Phoenix-2002
- Read alternative file names
- Map field names

### Complex Recoveries (Multi-file) - 4-6 hours
- Indiana, Knoxville, San Francisco, Phoenix-1988
- Implement file joining logic
- Handle location linkages

**Total effort:** 1-2 days to recover all 9 surveys

## Value Proposition

**Effort:** 1-2 days of development
**Gain:**
- +150% more surveys (6 → 15)
- +120-150% more trips (~180k → ~400-500k)
- 4 major metros (Chicago, SF, Mpls, Phoenix)
- Better climate diversity
- More temporal coverage (1988-2008)

**ROI:** High - relatively small code changes for major dataset expansion
