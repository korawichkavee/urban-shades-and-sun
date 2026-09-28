# Parameter Sensitivity Analysis Plan (TEMP)

**Date**: 2026-09-28
**Purpose**: Detailed implementation plan for reviewer-requested sensitivity analyses

---

## Data Pipeline Understanding

### Existing Data Files
1. **Primary dataset**: `data/final_datasets/seattle/seattle_final_analysis_with_seasonal_and_temp.csv` (780,452 rows)
   - Contains: raw counts (inshade_count, outshade_count), geometry (shadow_ratio, dist_to_shade_m), weather (utci_C)
   - Already has: pre-computed weights (w_sr_ipw, w_temp_ipw, w_dcwp) with DEFAULT parameters

2. **Walk rate data**: `outputs/analysis/seattle_walking_by_utci.csv`
   - UTCI bins → walk rate λ(T)
   - Used for temperature IPW

3. **Current analysis scripts**:
   - `scripts/analysis/compute_ablation_table.py` - generates Table 1 using existing weights
   - `scripts/visualization/plot_shade_preference_adjustment_progression.py` - generates Figure 2

### Weight Generation Script
- **Location**: `scripts/processing/apply_triple_ipw_final_cities_revised.py`
- **Key functions**:
  - `compute_sr_ipw()` (lines 31-55): Shadow ratio IPW with c_95 at line 49
  - `compute_temp_ipw()` (lines 60-106): Temperature IPW with walk rate clipping at lines 75-78, 94
  - `compute_dcwp_adjustment()` (lines 111-132): DCWP with τ=20 at line 111

---

## Implementation Strategy

### Option A: Regenerate Full Dataset (SLOW)
- Modify `apply_triple_ipw_final_cities_revised.py` to accept parameters
- Re-run entire pipeline for each parameter combination
- **Time**: ~1 hour per run × 10+ parameter sets = 10+ hours ❌

### Option B: Recompute Weights On-The-Fly (FAST) ✅
- Create standalone sensitivity analysis scripts
- Load existing dataset with raw columns
- Recompute only the weights with varied parameters
- Generate ablation tables directly
- **Time**: ~5-10 minutes per parameter set = ~1-2 hours total ✅

**Decision**: Use Option B for fast turnaround

---

## Sensitivity Analysis 1: Winsorization Cap (c_percentile)

### Reviewer Request (R2.1)
> "Include a sensitivity analysis varying this cutoff (e.g., from the 90th to the 99th percentile)."

### Parameters to Test
```python
c_percentiles = [0.90, 0.95, 0.99]  # 90th, 95th, 99th percentile
```

### Script to Create
**File**: `scripts/analysis/sensitivity_winsorization.py`

**Functionality**:
1. Load Seattle dataset
2. Filter to shadow_ratio >= 0.05 (same as main analysis)
3. For each c_percentile:
   - Compute SR-IPW: `cap = w_sr_raw.quantile(c_percentile)`
   - Apply cap: `w_sr = np.minimum(w_sr_raw, cap)`
   - Mean-scale: `w_sr = w_sr / w_sr.mean()`
4. For each c_percentile, compute ablation table:
   - Raw (no weights)
   - Temp only (w_temp_ipw from file)
   - Temp + SR (new w_sr × w_temp_ipw)
   - Temp + SR + DCWP (× w_dcwp from file)
5. Output: CSV table with columns [c_percentile, correction_level, mean_shade_pref, delta_pp]

**Key Code Section**:
```python
def compute_sr_ipw_with_cap(df, c_percentile=0.95, min_sr=0.05):
    """Compute SR-IPW with configurable winsorization cap."""
    mask = df['shadow_ratio'] >= min_sr
    w_sr_raw = 1.0 / df.loc[mask, 'shadow_ratio']

    # Variable cap
    cap = w_sr_raw.quantile(c_percentile)
    w_sr_capped = np.minimum(w_sr_raw, cap)

    # Mean-scale
    w_sr = w_sr_capped / w_sr_capped.mean()
    return w_sr

# Run for each percentile
for c_pct in [0.90, 0.95, 0.99]:
    df_filtered['w_sr_new'] = compute_sr_ipw_with_cap(df_filtered, c_pct)
    # Compute ablation...
```

**Dependencies**:
- Input: `data/final_datasets/seattle/seattle_final_analysis_with_seasonal_and_temp.csv`
- Uses columns: `shadow_ratio`, `w_temp_ipw`, `w_dcwp`, `person_count`, `inshade_count`, `outshade_count`, `shade_pref_dcwp`
- Output: `outputs/analysis/sensitivity_winsorization_results.csv`

**Expected Result**:
- All three percentiles should yield similar final estimates (within ±1-2 pp)
- Shows robustness to this arbitrary choice

**Deliverable**: Supplementary Table S1

---

## Sensitivity Analysis 2: Detour Decay Parameter (τ)

### Reviewer Request (R2.2)
> "Incorporate a parametric sweep over a reasonable domain of τ (e.g., τ ∈ [5, 50])."

### Parameters to Test
```python
tau_values = [5, 10, 15, 20, 30, 40, 50]  # meters
```

### Script to Create
**File**: `scripts/analysis/sensitivity_tau.py`

**Functionality**:
1. Load Seattle dataset
2. Filter to shadow_ratio >= 0.05 and person_count > 0
3. For each τ value:
   - Recompute DCWP-adjusted shade preference:
     ```python
     effective_sun = df['outshade_count'] * np.exp(-df['dist_to_shade_m'] / tau)
     effective_shade = df['inshade_count']
     shade_pref_dcwp = effective_shade / (effective_shade + effective_sun + 1e-10)
     ```
4. For each τ, compute ablation table:
   - Raw: `inshade / (inshade + outshade)`
   - Temp: raw + temp adjustment
   - SR: weighted by w_sr_ipw
   - DCWP: use new shade_pref_dcwp
5. Output: CSV with columns [tau, correction_level, mean_shade_pref, delta_pp]

**Key Code Section**:
```python
def compute_dcwp_with_tau(df, tau):
    """Compute DCWP adjustment with variable tau."""
    effective_sun = df['outshade_count'] * np.exp(-df['dist_to_shade_m'] / tau)
    effective_shade = df['inshade_count']
    shade_pref_dcwp = effective_shade / (effective_shade + effective_sun + 1e-10)
    return shade_pref_dcwp

# Run for each tau
results = []
for tau in [5, 10, 15, 20, 30, 40, 50]:
    df['shade_pref_dcwp_tau'] = compute_dcwp_with_tau(df, tau)
    # Compute ablation table
    ablation = compute_ablation_with_dcwp(df)
    ablation['tau'] = tau
    results.append(ablation)
```

**Dependencies**:
- Input: `data/final_datasets/seattle/seattle_final_analysis_with_seasonal_and_temp.csv`
- Uses columns: `dist_to_shade_m`, `inshade_count`, `outshade_count`, `w_sr_ipw`, `w_temp_ipw`, `person_count`
- Also needs: `outputs/analysis/seattle_walking_by_utci.csv` (for temp adjustment)
- Output:
  - `outputs/analysis/sensitivity_tau_results.csv` (table)
  - `outputs/plots/sensitivity/tau_sweep_ablation.pdf` (figure)

**Expected Result**:
- DCWP correction magnitude varies with τ
- But total correction (16 pp) remains dominated by SR-IPW regardless of τ
- Shows that even with uncertainty in τ, core finding holds

**Deliverables**:
- Supplementary Table S2: Ablation table for each τ
- Supplementary Figure S1: Line plot showing correction components vs τ

---

## Sensitivity Analysis 3: Walk Rate Clipping

### Reviewer Request (R2.3)
> "Justify bias-variance tradeoff induced by walk rate clipping at 0.1. Report variance before/after."

### Parameters to Test
```python
# No sweep needed - just report statistics
min_walk_rate = 0.1  # Current threshold
```

### Script to Create
**File**: `scripts/analysis/sensitivity_walk_rate_clip.py`

**Functionality**:
1. Load walk rate data: `outputs/analysis/seattle_walking_by_utci.csv`
2. Compute temperature IPW weights **before** clipping:
   - Load Seattle dataset
   - Interpolate walk rates (no clipping)
   - Compute w_temp_raw (may have extreme values)
3. Compute temperature IPW weights **after** clipping (λ >= 0.1):
   - Same but with clipping
4. Report statistics:
   - Number of observations affected by clipping
   - Variance before/after clipping
   - Max weight before/after clipping
   - Effective sample size before/after
5. Show clipping affects only extreme temperature bins (likely <1% of data)

**Key Code Section**:
```python
# Compute weights WITHOUT clipping
walk_rate_df_no_clip = walk_rate_df.copy()
f_lambda_no_clip = interp1d(walk_rate_df_no_clip['utci_bin_center'],
                             walk_rate_df_no_clip['walk_rate'], ...)

lambda_T_no_clip = f_lambda_no_clip(df['utci_C'])
w_temp_no_clip = np.where(df['utci_C'] < 20,
                          lambda_T_no_clip / baseline,
                          baseline / lambda_T_no_clip)

# Compute weights WITH clipping (current method)
walk_rate_df_clipped = walk_rate_df.copy()
walk_rate_df_clipped['walk_rate'] = np.maximum(walk_rate_df_clipped['walk_rate'], 0.1)
# ... (same as apply_triple_ipw_final_cities_revised.py)

# Report variance
print(f"Variance before clipping: {w_temp_no_clip.var():.4f}")
print(f"Variance after clipping: {w_temp_clipped.var():.4f}")
print(f"Observations affected: {(w_temp_no_clip != w_temp_clipped).sum()}")
```

**Dependencies**:
- Input:
  - `outputs/analysis/seattle_walking_by_utci.csv`
  - `data/final_datasets/seattle/seattle_final_analysis_with_seasonal_and_temp.csv`
- Uses columns: `utci_C`
- Output: `outputs/analysis/walk_rate_clipping_stats.txt` (text summary for response letter)

**Expected Result**:
- Clipping affects very few observations (only extreme UTCI bins)
- Variance reduction is modest but prevents numerical instability
- Final ablation estimates barely change (< 0.5 pp)

**Deliverable**: Statistics table in response letter (not main paper supplement)

---

## Implementation Workflow

### Step 1: Create Sensitivity Scripts
```bash
# Create directory for sensitivity analyses
mkdir -p scripts/analysis/sensitivity/
mkdir -p outputs/analysis/sensitivity/
mkdir -p outputs/plots/sensitivity/

# Create three scripts
touch scripts/analysis/sensitivity_winsorization.py
touch scripts/analysis/sensitivity_tau.py
touch scripts/analysis/sensitivity_walk_rate_clip.py
```

### Step 2: Shared Code Module
Create `scripts/analysis/sensitivity_utils.py` with common functions:
- `load_seattle_data()` - loads and filters dataset
- `compute_ablation_table()` - generates ablation table from weights
- `effective_sample_size()` - computes N_eff
- Temperature adjustment function (copied from existing scripts)

### Step 3: Run Sensitivity Analyses
```bash
# Run in sequence (each ~5-10 minutes)
python scripts/analysis/sensitivity_winsorization.py
python scripts/analysis/sensitivity_tau.py
python scripts/analysis/sensitivity_walk_rate_clip.py
```

### Step 4: Generate Supplementary Materials
```bash
# Create supplementary figure (tau sweep)
python scripts/visualization/plot_tau_sensitivity.py

# Compile results into LaTeX tables
python scripts/analysis/compile_supplementary_tables.py
```

---

## Files to Create/Modify

### New Scripts (7 files)
1. ✅ `scripts/analysis/sensitivity_utils.py` - Shared utilities
2. ✅ `scripts/analysis/sensitivity_winsorization.py` - R2.1 analysis
3. ✅ `scripts/analysis/sensitivity_tau.py` - R2.2 analysis
4. ✅ `scripts/analysis/sensitivity_walk_rate_clip.py` - R2.3 analysis
5. ✅ `scripts/visualization/plot_tau_sensitivity.py` - Supp Fig S1
6. ✅ `scripts/analysis/compile_supplementary_tables.py` - Format tables for LaTeX
7. ✅ `scripts/analysis/run_all_sensitivity.sh` - Convenience runner

### Existing Scripts to Reference (No Modification)
- `scripts/processing/apply_triple_ipw_final_cities_revised.py` - Copy weight functions
- `scripts/analysis/compute_ablation_table.py` - Copy ablation logic
- `scripts/visualization/plot_shade_preference_adjustment_progression.py` - Copy temp adjustment logic

### Output Files Generated
1. `outputs/analysis/sensitivity/winsorization_results.csv`
2. `outputs/analysis/sensitivity/tau_results.csv`
3. `outputs/analysis/sensitivity/walk_rate_clipping_stats.txt`
4. `outputs/plots/sensitivity/tau_sweep_ablation.pdf`
5. `outputs/analysis/sensitivity/supplementary_table_s1.tex`
6. `outputs/analysis/sensitivity/supplementary_table_s2.tex`

---

## Data Requirements Check

### Required Columns from Seattle Dataset
- [x] `shadow_ratio` - for SR-IPW
- [x] `dist_to_shade_m` - for DCWP
- [x] `inshade_count` - for shade preference
- [x] `outshade_count` - for shade preference
- [x] `person_count` - for weighting
- [x] `utci_C` - for temperature IPW
- [x] `w_temp_ipw` - existing temp weights (for comparison)
- [x] `w_dcwp` - existing DCWP weights (for comparison)

All columns present in `seattle_final_analysis_with_seasonal_and_temp.csv` ✓

### Walk Rate Data
- [x] `outputs/analysis/seattle_walking_by_utci.csv` exists
- Columns needed: `utci_bin_center`, `walk_rate`

---

## Testing Strategy

### Unit Tests
For each sensitivity script:
1. Test on small subset (1000 rows) - verify no crashes
2. Compare one parameter case to existing results (should match exactly)
3. Verify output files are created

### Integration Test
```python
# Test that ablation table with default parameters matches published Table 1
df = load_seattle_data()
ablation = compute_ablation_table(df, c_pct=0.95, tau=20)

# Should match Table 1 in paper:
# Raw: 0.657
# Temp: 0.649 (Δ = -0.7 pp)
# SR: 0.405 (Δ = -24.4 pp)
# DCWP: 0.501 (Δ = +9.6 pp)
```

---

## Timeline Estimate

| Task | Time | Notes |
|------|------|-------|
| Create sensitivity_utils.py | 30 min | Extract shared code |
| Create sensitivity_winsorization.py | 45 min | Simple weight recomputation |
| Create sensitivity_tau.py | 60 min | More complex, includes plotting |
| Create sensitivity_walk_rate_clip.py | 30 min | Mostly diagnostics |
| Create plot_tau_sensitivity.py | 30 min | Matplotlib figure |
| Create compile_supplementary_tables.py | 30 min | LaTeX formatting |
| Run all analyses | 30 min | Compute time |
| Review outputs & debug | 30 min | QA |
| **Total** | **~5 hours** | |

---

## Expected Outputs for Paper

### Supplementary Table S1: Winsorization Sensitivity
```
c_percentile | Raw | Temp | SR | DCWP | Total Δ
0.90         | 0.657 | 0.649 | 0.408 | 0.503 | -15.4 pp
0.95         | 0.657 | 0.649 | 0.405 | 0.501 | -15.6 pp
0.99         | 0.657 | 0.649 | 0.401 | 0.499 | -15.8 pp
```
*Note: Values are illustrative; actual results may vary*

### Supplementary Table S2: Tau Sensitivity (excerpt)
```
τ (m) | Raw | Temp | SR | DCWP | Total Δ
5     | 0.657 | 0.649 | 0.405 | 0.472 | -18.5 pp
20    | 0.657 | 0.649 | 0.405 | 0.501 | -15.6 pp
50    | 0.657 | 0.649 | 0.405 | 0.524 | -13.3 pp
```
*DCWP effect varies, but total correction remains substantial*

### Supplementary Figure S1: Tau Sweep
- X-axis: τ ∈ [5, 50] meters
- Y-axis: Mean shade preference
- Four lines: Raw, +Temp, +SR, +DCWP
- Shows DCWP adjustment magnitude changes but core finding persists

---

## Next Steps

1. **Create sensitivity_utils.py** - shared code extraction
2. **Create three sensitivity analysis scripts**
3. **Run analyses** - verify outputs match expectations
4. **Generate supplementary materials** - tables + figure
5. **Draft paper text edits** - incorporate results into methods
6. **Update reviewer response plan** - point to completed analyses

---

## Questions to Resolve

1. Should we include NYC in sensitivity analyses? (Probably no - Seattle is sufficient to show robustness)
2. Do we need confidence intervals on sensitivity results? (Probably no - point estimates sufficient for showing stability)
3. Should tau sweep be finer near τ=20? (e.g., {15, 18, 20, 22, 25}) - Maybe, if results are very sensitive

---

**Status**: Ready to implement
**Next action**: Create `scripts/analysis/sensitivity_utils.py`
