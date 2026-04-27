# Weight Distribution Diagnostics - Revised IPW (No Spatial/Temporal)

**Date:** 2026-03-23
**Purpose:** Diagnostic analysis of weight distributions after removing spatial/temporal standardization
**Status:** ✅ RESOLVED - No negative weights, improved N_eff

---

## Summary

After removing spatial and temporal standardization from the IPW weighting scheme:

**✅ Major Improvements:**
1. Effective sample size improved dramatically (Seattle: 0.4% → 48.2%, NYC: 3.7% → 56.2%)
2. No negative weights in either city (after fixing walk rate clipping bug)
3. Maximum weights are reasonable (Seattle: 4.97, NYC: 3.14)
4. Weight distributions are well-behaved

**⚠️ Remaining Issue:**
- Seattle still shows negative combined IPW effect (-2.67 pp) due to inverted walk rate pattern from April-June survey coverage
- This is a data limitation issue, not a weighting bug

---

## Weight Distribution Statistics

### Seattle

**After SR filter (≥0.05):** 780,451 images (33.3% retention)

| Weight Component | Mean | Median | Std | Min | Max | P95 | P99 | N_eff | N_eff % |
|------------------|------|--------|-----|-----|-----|-----|-----|-------|---------|
| **w_sr_ipw** | 1.000 | 0.516 | 1.038 | 0.385 | 4.161 | 4.161 | 4.161 | 375,624 | 48.1% |
| **w_temp_ipw** | 1.017 | 1.028 | 0.092 | 0.640 | 1.195 | 1.164 | 1.180 | 774,145 | 99.2% |
| **w_combined** | 1.012 | 0.527 | 1.050 | 0.252 | 4.971 | 3.827 | 4.493 | 375,935 | 48.2% |

**Extreme weight analysis:**
- Weights > 5: 0 (0.00%)
- Weights < 0.2: 0 (0.00%)
- Negative weights: 0 ✅

**Key findings:**
- SR-IPW is primary driver of effective N loss (48.1%)
- Temp-IPW has minimal impact on effective N (99.2%)
- Combined N_eff dominated by SR-IPW component
- No extreme weights requiring capping

### New York City

**After SR filter (≥0.05):** 254,507 images (7.6% retention)

| Weight Component | Mean | Median | Std | Min | Max | P95 | P99 | N_eff | N_eff % |
|------------------|------|--------|-----|-----|-----|-----|-----|-------|---------|
| **w_sr_ipw** | 1.000 | 0.640 | 0.836 | 0.183 | 2.947 | 2.947 | 2.947 | 149,806 | 58.9% |
| **w_temp_ipw** | 0.931 | 0.981 | 0.203 | 0.640 | 1.067 | 1.044 | 1.062 | 242,948 | 95.5% |
| **w_combined** | 0.942 | 0.561 | 0.832 | 0.172 | 3.141 | 2.742 | 3.008 | 142,909 | 56.2% |

**Extreme weight analysis:**
- Weights > 5: 0 (0.00%)
- Weights < 0.2: 3,272 (1.3%) - low SR-IPW weights from high shadow ratio areas
- Negative weights: 0 ✅ (after fixing walk rate clipping bug)

**Key findings:**
- Combined N_eff (56.2%) better than Seattle (48.2%)
- Temp-IPW mean < 1.0 (downweighting overall, as expected for fall survey)
- SR-IPW drives most of the effective N loss
- Some very low weights (<0.2) but not problematic

---

## Bug Fix: Negative Weights

### Problem Discovered

Initial run showed:
- NYC: 13,484 negative Temp-IPW weights (5.3% of data)
- Min weight: -6.67
- All at very cold UTCI (-34°C to -11.8°C)

### Root Cause

NYC walk rate function has first bin at -11°C with 0 walk rate (0/3 trips).

**Original code (BUGGY):**
```python
# Did NOT clip walk rates before interpolation
f_lambda = interp1d(
    walk_rate_df['utci_bin_center'],  # First value at -11°C
    walk_rate_df['walk_rate'],        # First value = 0.0
    bounds_error=False,
    fill_value=(walk_rate_df['walk_rate'].iloc[0],  # = 0.0 !!!
                walk_rate_df['walk_rate'].iloc[-1])
)
```

For images with UTCI < -11°C:
- λ(UTCI) extrapolated to 0.0 (constant fill)
- λ(20°C) = 0.44 (from data)
- Weight = 0.0 / 0.44 = 0.0 (should be downweight close to zero)

But then later clipping attempted to fix:
```python
lambda_T = np.maximum(lambda_T, 0.1)  # Clip after interpolation
```

However, this created inconsistency because:
- Images at -34°C: λ = 0.0 → clipped to 0.1 → weight = 0.1 / 0.44 = 0.23
- But actual file had weight = -6.67

This suggested the OLD version didn't have the clipping at all, or applied it incorrectly.

### Fix Applied

**Fixed code:**
```python
# Clip walk rates BEFORE interpolation
walk_rate_df_clipped = walk_rate_df.copy()
walk_rate_df_clipped['walk_rate'] = np.maximum(
    walk_rate_df_clipped['walk_rate'],
    0.1  # Minimum walk rate to avoid division by zero
)

# Now interpolation uses clipped values
f_lambda = interp1d(
    walk_rate_df_clipped['utci_bin_center'],
    walk_rate_df_clipped['walk_rate'],  # First value now = 0.1
    bounds_error=False,
    fill_value=(walk_rate_df_clipped['walk_rate'].iloc[0],  # = 0.1 ✓
                walk_rate_df_clipped['walk_rate'].iloc[-1])
)

# Additional safety clipping
lambda_T = np.maximum(lambda_T, 0.1)
```

### Result

After re-running with fixed script:
- ✅ NYC: 0 negative weights
- ✅ Temp-IPW min: 0.640
- ✅ All weights positive and reasonable
- ✅ Combined IPW effect: -0.00 pp (essentially zero, as expected from flat NYC walk rate)

---

## Comparison: Original vs Revised

### NYC

| Metric | Original (with spatial/temp) | Revised (without) |
|--------|------------------------------|-------------------|
| N_eff combined | 9,381 (3.7%) | 142,909 (56.2%) |
| Max combined weight | Unknown | 3.14 |
| Negative weights | 13,484 (5.3%) ❌ | 0 (0.0%) ✅ |
| Combined IPW effect | -4.52 pp | -0.00 pp |

### Seattle

| Metric | Original (with spatial/temp) | Revised (without) |
|--------|------------------------------|-------------------|
| N_eff combined | 3,123 (0.4%) | 375,935 (48.2%) |
| Max combined weight | 771.6 | 4.97 |
| Negative weights | 0 | 0 |
| Combined IPW effect | -2.67 pp | -2.67 pp |

**Key insight:** Seattle's negative IPW effect persists because it's a real data issue (inverted walk rate from April-June survey), not a weighting bug.

---

## Weight Component Behavior

### Shadow Ratio IPW (SR-IPW)

**Purpose:** Correct for uneven shadow supply across observations

**Mechanism:**
- High shadow ratio (lots of shade available) → downweight
- Low shadow ratio (little shade available) → upweight
- Baseline: population mean shadow ratio

**Observations:**
- Seattle: More variation (std=1.04) due to higher shadow ratio range
- NYC: Less variation (std=0.84), tighter distribution
- Both cities: SR-IPW drives most effective N loss

**Interpretation:**
- Images from very shady areas get downweighted (redundant information)
- Images from sunny areas get upweighted (rare, valuable)

### Temperature Activity IPW (Temp-IPW)

**Purpose:** Correct for temperature-based self-selection into outdoor walking

**Mechanism:**
- Cold temps (< 20°C): downweight (hardy walkers non-representative)
- Hot temps (≥ 20°C): upweight (heat-adapted walkers underrepresent shade preference)

**Observations:**
- **Seattle:** Mean=1.017 (slight upweighting overall), std=0.09 (very stable)
  - Max weight = 1.195 (moderate)
  - N_eff = 99.2% (minimal information loss)
  - BUT: Produces negative effect (-2.67 pp) due to inverted walk rate

- **NYC:** Mean=0.931 (downweighting overall), std=0.20 (moderate variation)
  - Max weight = 1.067 (very conservative)
  - N_eff = 95.5% (minimal information loss)
  - Effect ≈ 0 pp (flat walk rate within narrow fall temp range)

**Interpretation:**
- NYC fall survey → mostly temps below 20°C → downweights overall
- Seattle spring survey → mostly temps below 20°C but inverted pattern → upweights cold
- Neither produces extreme weights (max ~1.2)

### Combined Weight (SR-IPW × Temp-IPW)

**Multiplication effect:**
- Temp-IPW is stable (std ~0.1-0.2) → doesn't amplify much
- SR-IPW has variation (std ~0.8-1.0) → dominates combined weight
- Combined N_eff ≈ SR-IPW N_eff (Temp-IPW contributes little loss)

**Final effective N:**
- Seattle: 48.2% (driven by SR-IPW 48.1%)
- NYC: 56.2% (driven by SR-IPW 58.9%)

---

## Implications for Analysis

### 1. Spatial/Temporal Standardization Should Be Excluded

**Evidence:**
- Including it caused N_eff collapse to <4%
- Excluding it improved to ~50-55%
- No theoretical justification for mechanical standardization when substantive corrections (SR-IPW, DCWP) address actual biases

**Recommendation:** Use revised approach (SR-IPW × Temp-IPW × DCWP) without spatial/temporal

### 2. Weight Distributions Are Now Well-Behaved

**Evidence:**
- No negative weights
- Max weights reasonable (<5)
- N_eff acceptable (48-56%)
- No extreme outliers requiring winsorization

**Recommendation:** No further weight trimming or capping needed

### 3. Seattle Negative IPW Effect Is Real Data Issue

**Evidence:**
- Effect persists after all bug fixes
- Walk rate pattern is inverted (April highest despite coldest)
- April-June survey insufficient for year-round temp response
- Mechanistically makes sense: upweights high shade pref at cold temps

**Recommendation:** See SEATTLE_WALK_RATE_ISSUE.md for proposed solutions

### 4. NYC Temp-IPW Effect Is Near Zero

**Evidence:**
- Combined effect: -0.00 pp
- Fall-only survey with narrow temp range (9-14°C)
- Walk rate essentially flat across observed range
- Sep-Nov 2022 insufficient for year-round temp response

**Recommendation:** See NYC_WALK_RATE_ISSUE.md; likely should exclude Temp-IPW for consistency

---

## Diagnostic Plots Needed

Based on these findings, create:

1. **Weight distribution histograms** (revised data)
   - Faceted by city and weight type
   - Show that distributions are well-behaved

2. **Weight vs UTCI scatter** (Temp-IPW specifically)
   - Show the asymmetric weighting pattern
   - Highlight that Seattle has slight upweighting, NYC has downweighting

3. **Weight vs Shadow Ratio scatter** (SR-IPW)
   - Show inverse relationship
   - Compare cities

4. **N_eff waterfall chart**
   - Start with total images
   - Show loss from SR filter
   - Show loss from SR-IPW
   - Show loss from Temp-IPW (minimal)
   - End with combined N_eff

---

## Files Updated

- `apply_triple_ipw_final_cities_revised.py` - Fixed walk rate clipping (lines 75-78)
- `final_run_outputs/seattle/seattle_final_analysis_with_ipw_revised.csv` - Regenerated with fix
- `final_run_outputs/new-york-city/new-york-city_final_analysis_with_ipw_revised.csv` - Regenerated with fix
- Summary stats files for both cities updated

---

**End of Document**
