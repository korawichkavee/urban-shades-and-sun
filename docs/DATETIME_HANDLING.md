# NHTS Datetime Handling

## The Problem

NHTS 2017 data provides limited temporal information:
- **TDAYDATE**: Year-month only (YYYYMM format, e.g., 201608)
- **TRAVDAY**: Day of week (1=Sunday, 2=Monday, ..., 7=Saturday)
- **STRTTIME**: Start time in 24-hour HHMM format (e.g., 1430 = 2:30 PM)

The exact day of the month is **not recorded**.

## Solution

### Weekday-Constrained Random Sampling

The extraction script uses the following approach:

1. **Parse month and year** from TDAYDATE
2. **Find all days in that month** matching TRAVDAY
   - Example: August 2016 (TDAYDATE=201608), Monday (TRAVDAY=2)
   - Possible days: 1, 8, 15, 22, 29 (5 Mondays in Aug 2016)

3. **Randomly select one matching day** using:
   - Base seed: 42 (for overall reproducibility)
   - Household-specific variation: `hash(household_id + date)`
   - Result: Same household always gets same day for same month
   - Different households get varied days within constraints

4. **Combine with exact time** from STRTTIME

### Example

```
TDAYDATE=201608, TRAVDAY=2 (Monday), STRTTIME=1430
↓
Mondays in Aug 2016: [1, 8, 15, 22, 29]
↓
Random selection (seeded by household): 22
↓
Final datetime: 2016-08-22 14:30:00
```

## Reproducibility

The approach is fully reproducible:
- **Same seed (42)** used for all runs
- **Household ID** incorporated into per-trip seed
- Running extraction twice produces identical dates
- Different households get different (but consistent) day selections

## Temporal Uncertainty

### Reduced Uncertainty
- **Old approach (day=15)**: ±15 days uncertainty
- **New approach (weekday match)**: ±7 days uncertainty (within-week variation)

Weather conditions are more similar within the same week than across a full month, so this reduces weather matching error.

### What We Know
✓ **Month** (accurate)
✓ **Day of week** (accurate)
✓ **Time of day** (accurate)
✗ **Specific date** (approximated)

## Data Quality Flags

Two boolean flags document approximations:

### datetime_is_approximate
- **True**: Date sampled from month (NHTS)
- **False**: Exact date known (future surveys)

### location_is_placeholder
- **True**: Using state centroid (NHTS)
- **False**: Actual trip coordinates (future surveys)

## Impact on Analysis

For the pedestrian mode vs temperature analysis:

### Acceptable
- **Aggregate patterns**: Monthly/seasonal trends
- **Temperature distributions**: Overall relationships
- **Mode choice correlations**: General temperature effects

### Not Suitable For
- **Specific event analysis**: "Was it raining on this exact trip?"
- **Daily variation studies**: Hour-by-hour weather impacts
- **Microclimate effects**: Localized temperature variations

## Verification

The extraction script logs verify correctness:

```python
# Example verification code
TDAYDATE=201608, TRAVDAY=2 -> 2016-08-15 (Mon) ✓
TDAYDATE=201607, TRAVDAY=5 -> 2016-07-21 (Thu) ✓
```

All generated dates match their specified weekday.

## Alternative Approaches Considered

### 1. Fixed mid-month (day=15)
- **Pro**: Simple, explicit
- **Con**: 15-day uncertainty, ignores weekday info

### 2. Uniform random sampling
- **Pro**: Uses all days equally
- **Con**: Ignores weekday, adds noise, not reproducible

### 3. Weekday-constrained with distribution weighting
- **Pro**: Could match typical survey timing patterns
- **Con**: No distribution data available, complex

### Selected: Weekday-constrained random (seed=42)
- **Pro**: Uses available info, reproducible, reduces uncertainty
- **Con**: Still approximate (but best possible given data)

## Code Location

Implementation: `scripts/travel_surveys/extract_and_standardize.py`

Key function:
```python
def parse_datetime(row, config, random_seed=42):
    """
    Parse survey date and time fields into a datetime object.

    For NHTS: TDAYDATE is YYYYMM (no day), STRTTIME is HHMM,
    TRAVDAY is day of week. We sample a random day from the
    month matching the day of week using fixed seed.
    """
    # ... implementation details
```

## References

- NHTS 2017 Codebook: `data/transit_surveys/NHTS/codebook_Trip.csv`
- Field definitions:
  - TDAYDATE: "Date of travel day (YYYYMM)"
  - TRAVDAY: "Travel day - day of week"
  - STRTTIME: "24 hour local start time of trip"
