# DCWP Computation Investigation (TEMP)

**Date**: 2026-09-28
**Issue**: Sensitivity analysis DCWP results (84%) don't match paper Table 1 (50%)

---

## Root Cause Identified ✓

The sensitivity analysis scripts **double-applied DCWP** and used a **different outcome variable** than the paper.

---

## Paper's Methodology (compute_ablation_table.py)

### Data Filtering
```python
# Line 32: Filter to images with people ONLY
df = df[df['person_count'] > 0].copy()
# Result: 51,243 images
```

### Outcome Variable
```python
# Line 86: Uses in_shade (camera shade BOOLEAN)
raw_pref = df['in_shade'].mean()
# Result: 0.657 (65.7%)
```

### DCWP Application
```python
# Lines 116-117: DCWP as a WEIGHT, not outcome adjustment
sr_dcwp_weight = df['w_sr_ipw'] * df['w_dcwp']
dcwp_weighted_pref = (df['in_shade'] * sr_dcwp_weight).sum() / sr_dcwp_weight.sum()
# Result: 0.501 (50.1%)
```

**Key**: Uses `in_shade` (camera shade boolean) throughout, applies `w_dcwp` as a weight.

---

## Sensitivity Script's Methodology (WRONG)

### Data Filtering
```python
# Filtered to shadow_ratio >= 0.05
df_filtered = df[df['shadow_ratio'] >= 0.05].copy()
# Result: 780,451 images (15× more data!)
```

### Outcome Variable
```python
# Used pedestrian counts
shade_pref = inshade_count / (inshade_count + outshade_count)
# Result: 0.440 (44.0%) mean across images with people
```

### DCWP Application (DOUBLE APPLICATION!)
```python
# Used shade_pref_dcwp (outcome-adjusted ratio)
# THEN also multiplied by w_dcwp (weight)
dcwp_weighted_pref = (shade_pref_dcwp * person_count * w_sr_ipw * w_dcwp).sum() / ...
# Result: 0.840 (84.0%) ← WRONG due to double application
```

**Problem**: Applied DCWP twice (once in `shade_pref_dcwp`, again via `w_dcwp`)

---

## Two DCWP Representations in Codebase

### 1. shade_pref_dcwp (Outcome Adjustment)
**Source**: `apply_triple_ipw_final_cities_revised.py` lines 111-132

```python
def compute_dcwp_adjustment(df, tau=20.0):
    # Downweight sun-standing by distance to shade
    effective_sun = df['outshade_count'] * np.exp(-df['dist_to_shade_m'] / tau)
    effective_shade = df['inshade_count']

    # DCWP-adjusted shade preference ratio
    shade_pref = effective_shade / (effective_shade + effective_sun + 1e-10)
    return shade_pref
```

**Stored in**: `shade_pref_dcwp` column
**Mean value**: 0.450 (vs 0.447 raw) → +0.3 pp difference
**Interpretation**: Adjusts the ratio by down-weighting sun observations far from shade

### 2. w_dcwp (Weight)
**Source**: `apply_seasonal_reweighting.py` lines 80-90

```python
def compute_dcwp_weight(df, tau=20.0):
    # Based on in_shade (camera boolean)
    w_dcwp = np.where(
        df['in_shade'] == 1,
        1.0,  # Shade-standers: full weight
        np.exp(-df['dist_to_shade_m'] / tau)  # Sun-standers: distance discount
    )
    return w_dcwp / w_dcwp.mean()  # Scale to mean = 1.0
```

**Stored in**: `w_dcwp` column
**Mean value**: 1.034
**Interpretation**: Weights images based on whether CAMERA is in shade

---

## Key Differences: Camera vs Pedestrian

### Camera-Based (`in_shade`)
- **Type**: Boolean (True/False)
- **Meaning**: Is the camera location in shade?
- **Mean** (images with people): 0.657
- **Used by**: Paper's ablation table

### Pedestrian-Based (`inshade_count / total`)
- **Type**: Float (0.0 to 1.0)
- **Meaning**: What proportion of detected pedestrians are in shade?
- **Mean** (images with people): 0.447
- **Used by**: METHODOLOGY_REVIEW.md says this is "correct"

**Difference**: 21.7 percentage points!

---

## Why Sensitivity Got 84% Instead of 50%

### Step-by-step breakdown:

1. **Started with pedestrian-based raw**: 0.440
2. **Applied temp adjustment**: -0.7 pp → 0.433
3. **Applied SR-IPW to pedestrian counts**: -3.8 pp → 0.395
4. **Applied DCWP incorrectly**:
   - Used `shade_pref_dcwp` (already DCWP-adjusted to ~0.45 mean)
   - Multiplied by `w_dcwp` (weight based on camera shade)
   - Combined with person_count and w_sr_ipw
   - Result: 0.840 (84%)

The formula used was:
```python
dcwp_result = (shade_pref_dcwp * person_count * w_sr_ipw * w_dcwp).sum() /
              (person_count * w_sr_ipw * w_dcwp).sum()
```

This is wrong because:
- `shade_pref_dcwp` already has DCWP baked in (outcome adjustment)
- `w_dcwp` applies DCWP again (as a weight)
- Double application!

---

## What Should Sensitivity Scripts Do?

### Option A: Match Paper Exactly ✓ **RECOMMENDED**

**Rationale**: Sensitivity analyses should test robustness of THE PAPER'S methodology to parameter choices, not redo the analysis with different methods.

**Changes needed**:
1. Use `in_shade` (camera boolean) as outcome variable
2. Filter to `person_count > 0` ONLY (no shadow_ratio filter)
3. Apply `w_dcwp` as a weight (don't use `shade_pref_dcwp`)
4. Should reproduce paper's Table 1 with default parameters

**Expected results with tau=20**:
- Raw: 0.657
- Temp: 0.649
- SR: 0.405
- DCWP: 0.501 ✓

### Option B: Use "Correct" Pedestrian-Based Method

**Rationale**: METHODOLOGY_REVIEW.md says `in_shade` is wrong and pedestrian counts are correct.

**Changes needed**:
1. Use pedestrian counts (inshade_count / total)
2. Apply `w_dcwp` as a weight (single application)
3. Do NOT use `shade_pref_dcwp` column

**Expected results** (need to verify):
- Raw: ~0.440
- Temp: ~0.433
- SR: ~0.395
- DCWP: ??? (need to compute correctly)

**Issue**: This would be testing a DIFFERENT methodology than the paper, which defeats the purpose of sensitivity analysis.

---

## Recommendation

**Use Option A** (match paper exactly) for the reviewer response because:

1. **Purpose of sensitivity analysis**: Show that paper's FINDINGS are robust to parameter choices
2. **Reviewers are asking about parameters** (tau, c_percentile, λ_min), not outcome variable choice
3. **Consistency**: Sensitivity results should align with paper's Table 1
4. **Scope**: Fixing the outcome variable is a separate issue (METHODOLOGY_REVIEW.md already identified it)

The fact that the paper uses `in_shade` (camera) instead of pedestrian counts is a **separate methodological issue**, not something for the sensitivity analysis to address.

---

## Fix Required

### Update sensitivity_utils.py

**Current (WRONG)**:
```python
def compute_ablation_table(df, w_sr_ipw, w_dcwp, shade_pref_dcwp, walk_rate_df=None):
    # Uses pedestrian counts
    # Uses shade_pref_dcwp (outcome adjustment)
    # Also multiplies by w_dcwp (weight)
    # → Double applies DCWP!
```

**Corrected (match paper)**:
```python
def compute_ablation_table(df, walk_rate_df=None):
    # Use in_shade (camera boolean) like paper
    # Filter to person_count > 0 only
    # Apply w_sr_ipw and w_dcwp as weights
    # Do NOT use shade_pref_dcwp

    # Level 1: Raw
    raw = df['in_shade'].mean()

    # Level 2: Temp adjustment
    temp_adj = raw + df['temp_adjustment'].mean()

    # Level 3: SR-IPW
    sr = (df['in_shade'] * df['w_sr_ipw']).sum() / df['w_sr_ipw'].sum()
    sr_temp = sr + df['temp_adjustment'].mean()

    # Level 4: DCWP (as weight)
    dcwp_weight = df['w_sr_ipw'] * df['w_dcwp']
    dcwp = (df['in_shade'] * dcwp_weight).sum() / dcwp_weight.sum()
    dcwp_temp = dcwp + df['temp_adjustment'].mean()
```

This matches the paper's `compute_ablation_table.py` exactly.

---

## Verification Test

After fixing, run with tau=20 and verify we get:
```
Raw:  0.657
Temp: 0.649 (Δ = -0.7 pp)
SR:   0.405 (Δ = -24.4 pp)
DCWP: 0.501 (Δ = +9.6 pp)
```

This should match paper's Table 1 exactly. ✓

Then tau sensitivity should show:
- DCWP effect varies with tau
- But total correction remains substantial
- SR-IPW dominates

---

## Summary

**Root cause**: Sensitivity scripts double-applied DCWP and used wrong outcome variable

**Fix**: Match paper's methodology exactly (use `in_shade`, apply `w_dcwp` as weight)

**Why this is correct**: Sensitivity analysis should test parameter robustness, not change methodology

**Separate issue**: Whether paper should use `in_shade` vs pedestrian counts (METHODOLOGY_REVIEW.md)

---

**Status**: Root cause identified, fix specified
**Next step**: Update sensitivity scripts to match paper methodology
