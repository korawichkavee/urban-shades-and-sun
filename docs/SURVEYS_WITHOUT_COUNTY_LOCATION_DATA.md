# Surveys Without County-Level Location Data

## Summary

Of the 11 recoverable surveys (585,444 trips after datetime filtering), **249,773 trips (42.7%)** cannot be mapped to county-level coordinates and would rely on coarse state-level centroids for UTCI annotation.

**Recommendation**: Exclude these state-level trips from UTCI annotation to avoid wasting API calls on low-quality geographic data.

---

## Surveys with 100% State-Level Data (Cannot Use)

### 1. baltimore-1977 (2,098 trips)
- **Location type**: `ozone`, `dzone` (traffic analysis zones)
- **Issue**: Zone codes (e.g., 325, 45, 86) don't map to modern geographic identifiers
- **Geographic precision**: State centroid only (Maryland)

### 2. detroit-1994 (68,671 trips)
- **Location type**: `area_hh` (household area codes)
- **Issue**: Area codes (e.g., 8) are arbitrary survey-specific regions, not standard geographic codes
- **Geographic precision**: State centroid only (Michigan)
- **Note**: This is the largest survey losing all geographic detail

### 3. philadelphia-2000 (36,674 trips)
- **Location type**: `cpa` (Community Planning Area codes)
- **Issue**: CPA codes (e.g., 58) are Philadelphia-specific planning regions without standard FIPS mappings
- **Geographic precision**: State centroid only (Pennsylvania)

### 4. washington-dc-1968 (102,707 trips)
- **Location type**: `origzone`, `destzone` (traffic analysis zones)
- **Issue**: 1968-era zone codes (e.g., 3) don't map to modern geographic identifiers
- **Geographic precision**: State centroid only (DC)
- **Note**: Second largest survey, very old data with obsolete zone system

---

## Surveys with Partial County-Level Data (Mixed Quality)

### 5. idaho-2002 (27,192 trips - 99% county, 1% state)
- **Location type**: `ocounty` (county names)
- **County mapping**: Successfully mapped ADA, CANYON, GEM, OWYHEE, PAYETTE, BOISE counties
- **State fallback**: 186 trips (0.7%) with unrecognized county names (e.g., "TWIN FALLS", "PAYETTECOUNTY" without space)
- **Recommendation**: **Keep** - 99% coverage is excellent

### 6. kentuckiana-2001 (28,626 trips - 79% county, 21% state)
- **Location type**: `tripstartcounty`, `tripendcnty` (county abbreviations)
- **County mapping**: Successfully mapped JE (Jefferson/Louisville), OL, BU, SP, SH counties
- **State fallback**: 6,019 trips (21%) with unmapped county codes
- **Recommendation**: **Keep county-level trips**, consider dropping state-level trips

### 7. salt-lake-city-1993 (40,599 trips - 34% county, 66% state)
- **Location type**: `origcnty`, `destcnty` (county abbreviations)
- **County mapping**: Successfully mapped SL (Salt Lake), DV, UT, WB, TO counties
- **State fallback**: 26,679 trips (66%) with unmapped county codes
- **Recommendation**: **Keep county-level trips**, drop state-level trips (loses 66% of survey)

### 8. san-francisco-1990 (63,349 trips - 89% county, 11% state)
- **Location type**: `hometrct` (census tract codes)
- **County mapping**: 6-digit tract codes mapped to San Francisco County (06075)
- **State fallback**: 6,739 trips (11%) - likely missing/invalid tract codes
- **Recommendation**: **Keep county-level trips**, consider dropping state-level trips

---

## Impact Summary

### If we exclude ALL state-level trips:
- **Lost**: 249,773 trips (42.7% of recoverable surveys)
- **Retained**: 335,671 trips (57.3%) with county-level precision
- **Unique UTCI combinations**: ~60k-70k (estimated, reduced from 106,660)

### Major losses by survey:
1. **washington-dc-1968**: -102,707 trips (entire survey)
2. **detroit-1994**: -68,671 trips (entire survey)
3. **philadelphia-2000**: -36,674 trips (entire survey)
4. **salt-lake-city-1993**: -26,679 trips (66% of survey)
5. **san-francisco-1990**: -6,739 trips (11% of survey)
6. **kentuckiana-2001**: -6,019 trips (21% of survey)
7. **baltimore-1977**: -2,098 trips (entire survey)
8. **idaho-2002**: -186 trips (1% of survey)

### Surveys fully retained (100% county-level):
- **anchorage-2002**: 12,026 trips
- **boston-1991**: 39,086 trips
- **los-angeles-2001**: 164,416 trips
- **idaho-2002**: 27,006 trips (99%)

---

## Recommendation

**Option 1 (Conservative)**: Keep only county-level trips
- Filter: `location_source == 'county'`
- Trips: 335,671
- Quality: High geographic precision for all trips

**Option 2 (Moderate)**: Keep surveys with >90% county coverage
- Keep: anchorage, boston, los-angeles, idaho, san-francisco
- Drop: baltimore-1977, detroit-1994, kentuckiana-2001, philadelphia-2000, salt-lake-city-1993, washington-dc-1968
- Trips: ~306,000
- Quality: High precision, loses fewer large surveys

**Option 3 (Aggressive)**: Use all data including state-level
- Trips: 585,444
- Quality: Mixed - 42.7% of trips have very coarse location data
- UTCI calls: 106,660
- Not recommended due to poor geographic quality for nearly half the data
