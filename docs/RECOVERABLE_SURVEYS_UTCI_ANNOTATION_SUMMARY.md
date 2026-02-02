# Recoverable Surveys UTCI Annotation Summary

## Overview

Successfully prepared and started UTCI annotation for 7 recoverable travel surveys with county-level or better geographic precision.

**Date**: 2026-01-29  
**Status**: UTCI annotation in progress (ETA: ~25 minutes)

---

## Data Quality Improvements

### Geographic Sampling Implementation

Implemented proper geographic sampling using `GeographicSampler` class with:
- **ZIP code sampling**: Random points within ZIP code boundaries (priority 1)
- **County sampling**: Random points within county boundaries (priority 2)  
- **State centroids**: Fallback for unmatched locations (priority 3)

### County Code Mapping

Created comprehensive mappings for survey-specific location codes:
- **Massachusetts** (boston-1991): Numeric county codes → FIPS
- **California** (los-angeles-2001, san-francisco-1990): County codes + tract extraction → FIPS
- **Idaho** (idaho-2002): County names → FIPS
- **Kentucky** (kentuckiana-2001): County abbreviations → FIPS
- **Utah** (salt-lake-city-1993): County abbreviations → FIPS
- **Alaska** (anchorage-2002): Direct county FIPS codes

### Date Sampling Implementation

Used household-based reproducible sampling across survey months:
- **With day_of_week** (3 surveys): Sample from matching weekdays in survey month
- **Without day_of_week** (8 surveys): Uniform sampling across survey month
- **Reproducibility**: Household ID-based random seed ensures consistent results

---

## Final Dataset

### Trips Retained
- **Total trips**: 335,671 (57.3% of original 585,444 trips)
- **Removed**: 249,773 trips (42.7%) with only state-level precision

### Geographic Quality
- **County-level precision**: 335,671 trips (100% of retained)
- **ZIP-level precision**: 0 trips (none of the surveys had usable ZIP codes)
- **State-level precision**: 0 trips (all filtered out)

### Surveys Included (7 surveys)
1. **los-angeles-2001**: 164,416 trips (100% county)
2. **san-francisco-1990**: 56,610 trips (89% of original survey)
3. **boston-1991**: 39,086 trips (100% county)
4. **idaho-2002**: 27,006 trips (99% of original survey)
5. **kentuckiana-2001**: 22,607 trips (79% of original survey)
6. **salt-lake-city-1993**: 13,920 trips (34% of original survey)
7. **anchorage-2002**: 12,026 trips (100% county)

### Surveys Excluded (4 surveys)
1. **washington-dc-1968**: 102,707 trips - 1968-era traffic zones only
2. **detroit-1994**: 68,671 trips - survey-specific area codes only
3. **philadelphia-2000**: 36,674 trips - CPA codes only
4. **baltimore-1977**: 2,098 trips - traffic zones only

---

## UTCI Annotation

### API Efficiency
- **Unique date+hour+location combinations**: 179,492
- **Deduplication rate**: 46.5% (down from 335,671 trips)
- **Processing rate**: ~200-230 combinations/second
- **Workers**: 15 parallel workers

### Output
- **Input**: `data/transit_surveys/processed/recoverable_surveys_ready_for_utci_clean.csv`
- **Output**: `data/transit_surveys/processed/recoverable_surveys_with_utci.csv`
- **Checkpoint**: Auto-saved every 1,000 combinations
- **Logs**: `logs/utci_recoverable_*.log`

---

## Next Steps (After UTCI Completes)

1. **Validate UTCI data**: Check for invalid/missing UTCI values
2. **Generate person-day data**: Aggregate trips to person-day level
3. **Merge with existing surveys**: Combine with the 785k existing trips
4. **Regenerate analysis plots**: Update city-specific walk rate plots
5. **Update documentation**: Final survey counts and coverage

---

## Key Files

### Scripts
- `scripts/travel_surveys/prepare_recoverable_for_utci.py` - Date/location sampling
- `scripts/travel_surveys/geographic_sampler.py` - Geographic sampling class
- `scripts/travel_surveys/recoverable_survey_field_mappings.py` - Field mappings
- `scripts/travel_surveys/run_utci_recoverable.sh` - Tmux runner

### Documentation
- `docs/SURVEYS_WITHOUT_COUNTY_LOCATION_DATA.md` - Analysis of excluded surveys
- `docs/SURVEY_RECOVERY_PLAN.md` - Original recovery plan

### Data
- `data/transit_surveys/processed/recoverable_surveys_standardized.csv` - Merged raw data (640k trips)
- `data/transit_surveys/processed/recoverable_surveys_ready_for_utci_clean.csv` - Filtered, ready for UTCI (336k trips)
- `data/transit_surveys/processed/recoverable_surveys_with_utci.csv` - With UTCI annotations (pending)
