# Final Cities Analysis Guide: Seattle & NYC Triple IPW Implementation

**Last Updated:** 2026-03-17
**Purpose:** Complete reference for implementing triple IPW (Inverse Probability Weighting) corrections on Seattle and NYC street view imagery datasets.

---

## Overview

This guide documents the complete pipeline for applying triple IPW corrections (Shadow Ratio IPW, Temperature Activity IPW, Distance-Conditioned Walk Preference) plus spatial/temporal standardization to Seattle and NYC final analysis datasets.

---

## Data Locations

### Input Data

**Street View Imagery (SVI) Data:**
- **Seattle:** `/home/kieran/Documents/Python/sunny_day_SVI/final_run_outputs/seattle/seattle_shadow_annotated.csv`
  - **Rows:** 2,347,104 images
  - **Columns:** `image_id, is_sunny, sunny_probability, person_count, inshade_count, outshade_count, lat, lon, captured_at, compass_angle, sequence_id, is_pano`
  - **Note:** `captured_at` is milliseconds since epoch (UTC)

- **NYC:** `/home/kieran/Documents/Python/sunny_day_SVI/final_run_outputs/new-york-city/new-york-city_shadow_annotated.csv`
  - **Rows:** 3,363,344 images
  - **Columns:** Same as Seattle

**Mobility Data (Pre-processed with UTCI):**
- **Seattle:** `/home/kieran/Documents/Python/sunny_day_SVI/outputs/analysis/seattle_trips_with_utci.csv`
  - **Key columns:** `utci` (°C), `is_walk` (bool), `trip_weight`, `mode_1`, `travel_date`, `depart_time_hour`
  - **Rows:** ~400k trips
  - **UTCI range:** -16.7°C to 29.1°C
  - **Walk rate:** 19.7%

- **NYC:** `/home/kieran/Documents/Python/sunny_day_SVI/outputs/analysis/nyc_trips_with_utci.csv`
  - **Key columns:** Same as Seattle
  - **Rows:** ~300k trips
  - **UTCI range:** -11.0°C to 25.0°C
  - **Walk rate:** ~40%

**Walk Rate Functions (Already Computed):**
- **Seattle:** `/home/kieran/Documents/Python/sunny_day_SVI/outputs/analysis/seattle_walking_by_utci.csv`
  - **Columns:** `utci_bin_center, walk_count, total_count, walk_rate, mean_utci, walk_rate_se, walk_rate_ci_lower, walk_rate_ci_upper`
  - **UTCI bins:** 2°C width from -16°C to 30°C

- **NYC:** `/home/kieran/Documents/Python/sunny_day_SVI/outputs/analysis/nyc_walking_by_utci.csv`
  - **Columns:** Same as Seattle
  - **UTCI bins:** 2°C width from -11°C to 25°C

**Raw Mobility Survey Data (Original):**
- **Seattle:** `/home/kieran/Documents/Python/sunny_day_SVI/final_cities/seattle/Household_Travel_Survey_Trips_8962432402648352214.csv`
- **NYC:** `/home/kieran/Documents/Python/sunny_day_SVI/final_cities/NYC/Citywide_Mobility_Survey_-_Trip_2022_20260313.csv`

---

## Processing Pipeline Status

### Step 1: Shadow Metrics Annotation ⏳ IN PROGRESS

**Script:** `/home/kieran/Documents/Python/sunny_day_SVI/scripts/processing/add_shadow_to_final_cities.py`

**Usage:**
```bash
python scripts/processing/add_shadow_to_final_cities.py --city seattle
python scripts/processing/add_shadow_to_final_cities.py --city new-york-city
```

**What it does:**
1. Downloads OSM buildings, trees, road network for city bounding box
2. Groups images by unique date+hour (UTC) buckets
3. For each bucket:
   - Computes sun position (azimuth, elevation)
   - Generates shadow union from buildings/trees
   - Annotates each image with shadow metrics
4. Outputs shadow-annotated CSV

**Output columns added:**
- `in_shade` (bool): Point is within shadow polygon
- `shadow_ratio` (float 0-1): Fraction of nearest road segment in shadow
- `dist_to_shade_m` (float): Distance to nearest shadow boundary (0 if in shade)
- `local_shade_25m` (float 0-1): Shade fraction in 25m radius circle
- `local_shade_50m` (float 0-1): Shade fraction in 50m radius circle
- `shadow_ratio_50m` (float 0-1): Road shade fraction within ±50m of snap point
- `shadow_ratio_bldg` (float 0-1): Building-only shadow fraction
- `shadow_ratio_tree` (float 0-1): Tree-only shadow fraction
- `solar_street_angle` (float 0-90°): Angle between sun and street bearing
- `shadow_ratio_ped_l` (float 0-1): Left sidewalk shadow fraction
- `shadow_ratio_ped_r` (float 0-1): Right sidewalk shadow fraction
- `sun_azimuth` (float): Sun azimuth in degrees
- `sun_elevation` (float): Sun elevation in degrees

**Output files:**
- Seattle: `final_run_outputs/seattle/seattle_with_shadow_metrics.csv`
- NYC: `final_run_outputs/new-york-city/new-york-city_with_shadow_metrics.csv`

**Current status:**
- Seattle: Running (569,180 roads fetched, processing 2917 date+hour buckets, ~2-3 hours remaining)
- NYC: Pending

**Key functions:**
- `load_osm_data(gdf_points)` → dict with buildings/trees/roads GeoDataFrames
- `compute_shadow_union(dt_utc, lat_c, lon_c, osm_data)` → shadow polygons + sun position
- `lookup_points(gdf_subset, shadow_union, ..., roads_utm)` → arrays of shadow metrics

---

### Step 2: UTCI Annotation 🔜 READY

**Script:** `/home/kieran/Documents/Python/sunny_day_SVI/scripts/processing/add_utci_to_final_cities.py`

**Usage:**
```bash
python scripts/processing/add_utci_to_final_cities.py --city seattle
python scripts/processing/add_utci_to_final_cities.py --city new-york-city
```

**Requirements:**
- Input must be shadow-annotated CSV from Step 1
- Requires `enhanced_utci.py` module (in `scripts/utils/`)

**What it does:**
1. Deduplicates by date+hour+location (rounded to 0.01° lat/lon)
2. Fetches ERA5 weather data from Open-Meteo API in batches
3. Computes UTCI (Universal Thermal Climate Index)
4. Joins results back to all images
5. Checkpoint-based resumable processing

**Output columns added:**
- `utci_K` (float): UTCI in Kelvin
- `utci_C` (float): UTCI in Celsius
- `utci_timestamp` (str): ISO timestamp of weather data
- `wind_speed_10m` (float): Wind speed at 10m height (m/s)
- `temperature_2m` (float): Air temperature at 2m (°C)
- `dewpoint_2m` (float): Dewpoint at 2m (°C)
- `datetime_local` (str): Local datetime string (city timezone)

**Output files:**
- Seattle: `final_run_outputs/seattle/seattle_with_shadow_and_utci.csv`
- NYC: `final_run_outputs/new-york-city/new-york-city_with_shadow_and_utci.csv`

**Performance:**
- ~20 parallel workers
- ~10-20 requests/sec
- Checkpoint every 1000 unique combinations
- Estimated time: ~30-60 minutes per city

**Key functions:**
- `add_local_datetime(df, timezone_str)` → adds `datetime_local` column
- `fetch_utci_for_unique(unique_key, lat, lon, timestamp_str)` → single UTCI fetch
- `process_chunk(chunk_df, ...)` → batch fetch with ThreadPoolExecutor

---

### Step 3: Triple IPW Weights Computation ⏸️ NOT STARTED

**Script:** `/home/kieran/Documents/Python/sunny_day_SVI/scripts/processing/apply_triple_ipw_final_cities.py` (**TO BE CREATED**)

**Required inputs:**
1. Shadow + UTCI annotated SVI data from Steps 1-2
2. Walk rate functions: `outputs/analysis/{city}_walking_by_utci.csv`

**What it needs to compute:**

#### 3.1 Shadow Ratio IPW (SR-IPW)

**Formula:** `w_sr = 1 / shadow_ratio` (capped at 95th percentile)

**Implementation:**
```python
def compute_sr_ipw(df, min_shadow_ratio=0.05):
    """
    Compute shadow ratio inverse probability weights.

    Args:
        df: DataFrame with 'shadow_ratio' column
        min_shadow_ratio: Minimum SR threshold (default 0.05)

    Returns:
        Series of SR-IPW weights (mean-scaled to 1.0)
    """
    # Filter: shadow_ratio >= 0.05 (logical requirement, not arbitrary)
    mask = df['shadow_ratio'] >= min_shadow_ratio

    # Compute raw weights
    w_sr_raw = 1.0 / df.loc[mask, 'shadow_ratio']

    # Winsorize at 95th percentile to prevent extreme leverage
    cap = w_sr_raw.quantile(0.95)
    w_sr_capped = np.minimum(w_sr_raw, cap)

    # Scale to mean = 1.0
    w_sr = w_sr_capped / w_sr_capped.mean()

    return w_sr
```

**Key considerations:**
- **Filter requirement:** Images with `shadow_ratio < 0.05` must be excluded (weight undefined at SR=0)
- **Expected data loss:** ~65-70% of images (based on State College analysis)
- **Interpretation:** Upweights observations from locations with less shade availability

#### 3.2 Temperature Activity IPW (Temp-IPW)

**Formula (Asymmetric):**
```
T < 20°C:  w_temp = λ(T) / λ(20°C)      [downweight cold-hardy walkers]
T ≥ 20°C:  w_temp = λ(20°C) / λ(T)      [upweight heat-adapted walkers]
```

Where `λ(T)` = walk rate at temperature T (from walk rate functions)

**Implementation:**
```python
def compute_temp_ipw(df, walk_rate_df, baseline_utci=20.0):
    """
    Compute temperature activity inverse probability weights.

    Args:
        df: SVI DataFrame with 'utci_C' column
        walk_rate_df: Walk rate function with columns:
                      ['utci_bin_center', 'walk_rate']
        baseline_utci: Baseline temperature in °C (default 20.0)

    Returns:
        Series of Temp-IPW weights
    """
    # Interpolate walk rates to match SVI UTCI values
    from scipy.interpolate import interp1d

    # Clip extreme values to avoid infinite weights
    walk_rate_df_clipped = walk_rate_df.copy()
    walk_rate_df_clipped['walk_rate'] = np.maximum(
        walk_rate_df_clipped['walk_rate'],
        0.1  # Minimum walk rate to avoid division by zero
    )

    # Create interpolation function
    f_lambda = interp1d(
        walk_rate_df_clipped['utci_bin_center'],
        walk_rate_df_clipped['walk_rate'],
        kind='linear',
        fill_value='extrapolate'
    )

    # Get lambda values for each observation
    lambda_T = f_lambda(df['utci_C'])
    lambda_baseline = f_lambda(baseline_utci)

    # Asymmetric weighting
    w_temp = np.where(
        df['utci_C'] < baseline_utci,
        lambda_T / lambda_baseline,      # < 20°C: downweight
        lambda_baseline / lambda_T       # ≥ 20°C: upweight
    )

    # Both branches equal 1.0 at baseline
    return w_temp
```

**Key considerations:**
- **Asymmetry rationale:** Cold walkers are self-selected hardy individuals (non-representative), hot walkers would prefer more shade if forced outside
- **Baseline:** 20°C chosen as "comfortable" reference point
- **Clipping:** Extreme temperatures (>40°C) should clip walk rate to minimum 0.1 to avoid infinite weights

#### 3.3 Distance-Conditioned Walk Preference (DCWP)

**Formula:** `effective_sun = outshade_count × exp(-d/τ)`
Where `d` = `dist_to_shade_m`, `τ` = decay constant (20m)

**Implementation:**
```python
def compute_dcwp_weights(df, tau=20.0):
    """
    Compute distance-conditioned walk preference adjustments.

    Args:
        df: DataFrame with 'dist_to_shade_m', 'inshade_count', 'outshade_count'
        tau: Decay constant in meters (default 20.0)

    Returns:
        Series of DCWP-adjusted outcome ratios
    """
    # DCWP adjustment: downweight sun-standing by distance to shade
    effective_sun = df['outshade_count'] * np.exp(-df['dist_to_shade_m'] / tau)
    effective_shade = df['inshade_count']  # No adjustment for shade standing

    # Shade preference ratio
    shade_pref = effective_shade / (effective_shade + effective_sun + 1e-10)

    return shade_pref
```

**Key considerations:**
- **Interpretation:** At d=0m (shade adjacent), full weight. At d=20m, weight=0.37. At d=60m, weight≈0.05.
- **Grounding:** Based on pedestrian route deviation studies (10-30% acceptable detour for amenities)
- **Superadditivity:** SR-IPW and DCWP interact non-additively (correlation: -0.499)

#### 3.4 Combined Weights

**Formula:**
```
w_final = w_sr_ipw × w_temp_ipw × w_spatial × w_temp_range
```

Where:
- `w_spatial` = spatial post-stratification weight
- `w_temp_range` = temperature range standardization weight (KDE-based)

**Implementation:**
```python
def apply_combined_ipw(df, walk_rate_df):
    """
    Apply full triple IPW + corrections.

    Returns:
        DataFrame with weight columns and adjusted metrics
    """
    # Filter: shadow_ratio >= 0.05
    df_filtered = df[df['shadow_ratio'] >= 0.05].copy()

    # 1. Shadow Ratio IPW
    df_filtered['w_sr_ipw'] = compute_sr_ipw(df_filtered)

    # 2. Temperature Activity IPW
    df_filtered['w_temp_ipw'] = compute_temp_ipw(df_filtered, walk_rate_df)

    # 3. DCWP adjustment (operates on outcomes, not weights)
    df_filtered['shade_pref_dcwp'] = compute_dcwp_weights(df_filtered)

    # 4. Spatial post-stratification (see Step 4)
    df_filtered['w_spatial'] = compute_spatial_weights(df_filtered)

    # 5. Temperature range standardization (see Step 4)
    df_filtered['w_temp_range'] = compute_temp_range_weights(df_filtered)

    # Combined weight
    df_filtered['w_combined'] = (
        df_filtered['w_sr_ipw'] *
        df_filtered['w_temp_ipw'] *
        df_filtered['w_spatial'] *
        df_filtered['w_temp_range']
    )

    return df_filtered
```

**Output columns to add:**
- `w_sr_ipw` (float): Shadow ratio weight
- `w_temp_ipw` (float): Temperature activity weight
- `shade_pref_dcwp` (float 0-1): DCWP-adjusted shade preference
- `w_spatial` (float): Spatial post-stratification weight
- `w_temp_range` (float): Temperature range weight
- `w_combined` (float): Final combined weight
- `n_eff_sr` (float): Effective sample size after SR-IPW
- `n_eff_combined` (float): Effective sample size after all weights

---

### Step 4: Spatial & Temporal Standardization ⏸️ NOT STARTED

**To be implemented in:** `scripts/processing/apply_triple_ipw_final_cities.py`

#### 4.1 Spatial Post-Stratification

**Purpose:** Correct for uneven geographic sampling within city

**Implementation:**
```python
def compute_spatial_weights(df, grid_size_deg=0.01):
    """
    Compute spatial post-stratification weights.

    Creates spatial grid, compares overall vs. season-specific coverage.

    Args:
        df: DataFrame with 'lat', 'lon', 'season' columns
        grid_size_deg: Grid cell size in degrees (default 0.01 ≈ 1km)

    Returns:
        Series of spatial weights
    """
    # Create grid cells
    df['grid_lat'] = (df['lat'] / grid_size_deg).round() * grid_size_deg
    df['grid_lon'] = (df['lon'] / grid_size_deg).round() * grid_size_deg
    df['grid_cell'] = df['grid_lat'].astype(str) + '_' + df['grid_lon'].astype(str)

    # Overall spatial distribution
    overall_spatial = df.groupby('grid_cell').size() / len(df)

    # Season-specific distribution
    spatial_weights = []
    for season in df['season'].unique():
        season_mask = df['season'] == season
        season_spatial = df[season_mask].groupby('grid_cell').size() / season_mask.sum()

        # Weight = overall / season (reweights season to match overall)
        w_season = overall_spatial / season_spatial
        spatial_weights.append(df[season_mask]['grid_cell'].map(w_season))

    return pd.concat(spatial_weights)
```

#### 4.2 Temperature Range Standardization

**Purpose:** Correct for different temperature distributions across seasons

**Implementation:**
```python
from scipy.stats import gaussian_kde

def compute_temp_range_weights(df):
    """
    Compute temperature range standardization weights using KDE.

    Args:
        df: DataFrame with 'utci_C', 'season' columns

    Returns:
        Series of temperature range weights
    """
    # Target distribution: all seasons pooled
    kde_target = gaussian_kde(df['utci_C'].dropna())

    # Season-specific weights
    temp_weights = []
    for season in df['season'].unique():
        season_mask = df['season'] == season
        season_utci = df.loc[season_mask, 'utci_C'].dropna()

        # Season-specific KDE
        kde_season = gaussian_kde(season_utci)

        # Weight = target density / season density
        w_temp = kde_target(season_utci) / (kde_season(season_utci) + 1e-10)

        temp_weights.append(pd.Series(w_temp, index=season_utci.index))

    return pd.concat(temp_weights)
```

#### 4.3 Season Assignment

**Rule:** Meteorological seasons based on capture date
```python
def assign_season(df):
    """Assign meteorological seasons based on capture month."""
    df['capture_date'] = pd.to_datetime(df['captured_at'], unit='ms', utc=True)
    df['month'] = df['capture_date'].dt.month

    season_map = {
        12: 'winter', 1: 'winter', 2: 'winter',
        3: 'spring', 4: 'spring', 5: 'spring',
        6: 'summer', 7: 'summer', 8: 'summer',
        9: 'fall', 10: 'fall', 11: 'fall'
    }
    df['season'] = df['month'].map(season_map)
    return df
```

#### 4.4 Seasonal Balance Check

**Recommendation tiers:**
- **Balanced** (≤60% dominant season): Show overall plots with standard corrections
- **Moderately imbalanced** (60-70%): Show plots with caution warnings
- **Severely imbalanced** (>70%): Seasonal-specific plots only; no overall plot

```python
def check_seasonal_balance(df):
    """Check seasonal imbalance and return recommendation."""
    season_counts = df['season'].value_counts()
    dominant_pct = season_counts.max() / len(df) * 100

    if dominant_pct <= 60:
        return 'balanced', dominant_pct
    elif dominant_pct <= 70:
        return 'moderate', dominant_pct
    else:
        return 'severe', dominant_pct
```

---

### Step 5: Final Output & Analysis ⏸️ NOT STARTED

**Output file structure:**

`final_run_outputs/{city}/{city}_final_analysis_with_ipw.csv`

**Required columns in final output:**
- All original SVI columns
- All shadow metrics from Step 1
- All UTCI metrics from Step 2
- All IPW weights from Step 3
- All correction weights from Step 4
- Derived metrics:
  - `season` (str): winter/spring/summer/fall
  - `n_eff_sr` (float): Effective N after SR-IPW
  - `n_eff_combined` (float): Effective N after all weights
  - `shade_pref_raw` (float 0-1): Unadjusted shade preference
  - `shade_pref_dcwp` (float 0-1): DCWP-adjusted shade preference
  - `shade_pref_ipw` (float 0-1): Weighted shade preference

**Summary statistics to compute:**
```python
def generate_summary_stats(df):
    """Generate summary statistics report."""
    stats = {
        'total_images': len(df),
        'images_after_sr_filter': (df['shadow_ratio'] >= 0.05).sum(),
        'data_retention_pct': (df['shadow_ratio'] >= 0.05).mean() * 100,

        # Effective sample sizes
        'n_eff_sr_ipw': (df['w_sr_ipw'].sum() ** 2) / (df['w_sr_ipw'] ** 2).sum(),
        'n_eff_combined': (df['w_combined'].sum() ** 2) / (df['w_combined'] ** 2).sum(),

        # Shade preference estimates
        'shade_pref_raw': df['inshade_count'].sum() / (df['inshade_count'].sum() + df['outshade_count'].sum()),
        'shade_pref_dcwp': (df['shade_pref_dcwp'] * df['person_count']).sum() / df['person_count'].sum(),
        'shade_pref_ipw': (df['shade_pref_dcwp'] * df['w_combined']).sum() / df['w_combined'].sum(),

        # Effect sizes
        'sr_ipw_effect_pp': None,  # To be computed as difference from raw
        'temp_ipw_effect_pp': None,
        'dcwp_effect_pp': None,
        'combined_effect_pp': None,

        # Seasonal balance
        'season_balance': df['season'].value_counts().to_dict(),
        'dominant_season_pct': df['season'].value_counts().max() / len(df) * 100,
    }

    # Compute effect sizes
    stats['sr_ipw_effect_pp'] = (stats['shade_pref_ipw'] - stats['shade_pref_raw']) * 100

    return stats
```

---

## Key Methodological Points

### Asymmetric Temperature Weighting Rationale

**Cold weather (T < 20°C):**
- Observed walkers are self-selected "hardy" individuals who tolerate cold
- Their shade preferences are NOT representative of the general population
- **Solution:** Downweight their observations (w < 1.0)

**Hot weather (T ≥ 20°C):**
- Observed walkers are heat-adapted but would prefer MORE shade if forced outside
- Self-selection bias underestimates true shade demand
- **Solution:** Upweight their observations (w ≥ 1.0)

**Baseline at 20°C:** Both branches equal exactly 1.0 at the comfortable reference temperature.

### Shadow Ratio Filter Necessity

**Why filter `shadow_ratio >= 0.05`?**
- Mathematical: Weight `w = 1/SR` is undefined at SR=0
- Substantive: Images with no shadow availability provide no information about shade preference
- Not arbitrary: This is a logical requirement, not a statistical choice

**Expected impact:**
- State College data: Removed 65.9% of images
- Retained sample skews toward denser urban fabric with meaningful shadow access
- This is acceptable: we're measuring shade preference where shade is available

### SR-IPW and DCWP Superadditivity

**Correlation:** `shadow_ratio` and `dist_to_shade_m` are negatively correlated (-0.499)

**Mechanism:**
- SR-IPW upweights low shadow_ratio images
- DCWP downweights large distance_to_shade images
- Same images are targeted by both corrections → amplification

**State College example:**
- SR-IPW alone: +1.2 percentage points
- DCWP alone: +1.8 percentage points
- Combined: +5.7 percentage points (NOT 3.0 pp!)

**Recommendation:** Report IPW and DCWP effects separately; use combined estimate cautiously

### Identifiability Limitations

**What we CAN'T identify:**
- True structural preference independent of all confounds
- Seasonal effects without strong assumptions (different streets, different populations, different temperature ranges)
- Causality (this is observational/behavioral data)

**What we CAN identify:**
- Weighted summary of observed behavior corrected for measured confounds (shadow availability, temperature activity, access cost)
- Comparative estimates across cities with similar methods
- Upper/lower bounds on preference given stated assumptions

---

## Code References

### Existing Implementations to Reference

**State College triple IPW:**
- `/home/kieran/Documents/Python/sunny_day_SVI/scripts/visualization/state_college/visualize_state_college_triple_ipw.py`
- Shows complete SR-IPW + Temp-IPW + DCWP implementation
- Uses pooled travel survey data (not city-specific)

**Metro cities IPW (partial):**
- `/home/kieran/Documents/Python/sunny_day_SVI/scripts/processing/metro_bias_corrected_analysis.py`
- Has per-city walk rate functions
- May have temperature IPW implementation

**Seasonal bias correction:**
- `/home/kieran/Documents/Python/sunny_day_SVI/docs/SEASONAL_BIAS_CORRECTION_DISCUSSION.md`
- Documents spatial post-stratification + KDE temperature range standardization

**Walk rate computation:**
- `/home/kieran/Documents/Python/sunny_day_SVI/scripts/analysis/analyze_walking_vs_utci.py`
- Function: `compute_walking_rate_by_utci(df, bin_width=2.0)`
- Shows how walk rates were binned and computed

### Key Python Modules

**Shadow computation:**
- `/home/kieran/Documents/Python/sunny_day_SVI/scripts/data_collection/salusshadow.py`
- Functions: `get_sun()`, `building_shadow()`, `tree_shadow_geom()`, `shaded_fraction()`

**UTCI computation:**
- `/home/kieran/Documents/Python/sunny_day_SVI/scripts/utils/enhanced_utci.py`
- Function: `get_enhanced_utci_data(lat, lon, timestamp_str)`

---

## Timezones

**Seattle:** `America/Los_Angeles` (Pacific Time)
**NYC:** `America/New_York` (Eastern Time)

---

## Performance Estimates

| Step | Seattle | NYC | Total |
|------|---------|-----|-------|
| Shadow annotation | 2-3 hrs | 3-4 hrs | 5-7 hrs |
| UTCI annotation | 30-60 min | 45-90 min | 1.5-2.5 hrs |
| IPW computation | 10-20 min | 15-30 min | 25-50 min |
| **Total** | **3-4 hrs** | **4-6 hrs** | **7-10 hrs** |

---

## Checklist for Implementation

- [ ] Seattle shadow annotation complete
- [ ] NYC shadow annotation complete
- [ ] Seattle UTCI annotation complete
- [ ] NYC UTCI annotation complete
- [ ] Create `apply_triple_ipw_final_cities.py` script
- [ ] Implement SR-IPW computation
- [ ] Implement Temp-IPW computation (asymmetric)
- [ ] Implement DCWP adjustment
- [ ] Implement spatial post-stratification
- [ ] Implement temperature range standardization (KDE)
- [ ] Implement season assignment
- [ ] Implement seasonal balance check
- [ ] Generate summary statistics
- [ ] Create visualization scripts
- [ ] Validate against State College results (cross-check methodology)
- [ ] Document final results

---

## Questions for Future Work

1. Should we use **city-specific** or **pooled** walk rate functions?
   - Current: Using city-specific (`seattle_walking_by_utci.csv`, `nyc_walking_by_utci.csv`)
   - Alternative: Use pooled function from 25 metro areas (larger sample, more stable)

2. Should we implement **time-of-day filtering** (commute hours only)?
   - State College used commute-hour filtering to reduce confounds
   - Mapillary SVI has `captured_at` timestamp (can filter by hour of day)

3. How to handle **sidewalk vs. street** distinction?
   - Current shadow metrics include `shadow_ratio_ped_l` / `shadow_ratio_ped_r`
   - Should SR-IPW use pedestrian-specific shadow ratio instead of centerline?

4. Should we compute **confidence intervals** on final estimates?
   - Bootstrap resampling over images?
   - Delta method for IPW standard errors?

5. How to present **seasonal-specific** results?
   - Separate plots for winter/spring/summer/fall?
   - Only overall plot if balanced, seasonal plots if imbalanced?

---

**End of Guide**
