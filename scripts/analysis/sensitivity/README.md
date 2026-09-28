# Sensitivity Analysis Scripts

**Purpose**: Parameter sensitivity analyses for reviewer response

**Date**: 2026-09-28

---

## Overview

This directory contains scripts for conducting parameter sensitivity analyses requested by reviewers of the CPHS 2026 submission.

**IMPORTANT**: These scripts are READ-ONLY. They load existing data files and compute results with varied parameters, but **do not modify any source data or existing analysis results**.

---

## Scripts

### Core Analysis Scripts

1. **`sensitivity_utils.py`** - Shared utility functions
   - Data loading (READ-ONLY)
   - Weight computation functions
   - Ablation table computation
   - Output helpers

2. **`sensitivity_winsorization.py`** - Addresses Reviewer 2, Comment 1
   - Tests winsorization caps: 90th, 95th, 99th percentile
   - Generates Supplementary Table S1
   - Output: `outputs/analysis/sensitivity/supplementary_table_s1_*`

3. **`sensitivity_tau.py`** - Addresses Reviewer 2, Comment 2
   - Tests tau ∈ {5, 10, 15, 20, 30, 40, 50} meters
   - Generates Supplementary Table S2
   - Output: `outputs/analysis/sensitivity/supplementary_table_s2_*`

4. **`sensitivity_walk_rate_clip.py`** - Addresses Reviewer 2, Comment 3
   - Justifies walk rate clipping at λ_min = 0.1
   - Reports variance before/after clipping
   - Output: `outputs/analysis/sensitivity/walk_rate_clipping_*`

### Convenience Runner

**`run_all_sensitivity.sh`** - Runs all analyses in sequence
```bash
./run_all_sensitivity.sh
```

---

## Usage

### Run All Analyses (Recommended)

```bash
cd scripts/analysis/sensitivity
./run_all_sensitivity.sh
```

**Estimated time**: ~5-10 minutes
**Estimated output size**: ~2 MB

### Run Individual Analyses

```bash
# Winsorization sensitivity
python3 sensitivity_winsorization.py

# Tau sensitivity
python3 sensitivity_tau.py

# Walk rate clipping
python3 sensitivity_walk_rate_clip.py
```

### Generate Visualizations

After running tau sensitivity:
```bash
python3 ../../visualization/plot_tau_ablation_sensitivity.py
```

---

## Output Files

### Analysis Results

Located in: `outputs/analysis/sensitivity/`

**Winsorization:**
- `winsorization_sensitivity_detailed.csv` - Full results
- `supplementary_table_s1_winsorization.csv` - Summary table
- `supplementary_table_s1_winsorization.tex` - LaTeX table

**Tau:**
- `tau_sensitivity_detailed.csv` - Full results
- `supplementary_table_s2_tau.csv` - Summary table
- `supplementary_table_s2_tau.tex` - LaTeX table
- `tau_sensitivity_for_plotting.csv` - Data for plots

**Walk Rate Clipping:**
- `walk_rate_clipping_stats.csv` - Statistics
- `walk_rate_clipping_response.txt` - Formatted response text

### Figures

Located in: `outputs/plots/sensitivity/`

- `supplementary_figure_s1_tau_sensitivity.pdf` - Main tau plot (vector)
- `supplementary_figure_s1_tau_sensitivity.png` - Main tau plot (raster)
- `supplementary_figure_s1b_tau_deltas.pdf` - Correction magnitudes
- `supplementary_figure_s1b_tau_deltas.png` - Correction magnitudes

---

## Data Dependencies

**All scripts are READ-ONLY**. They require:

### Input Data (not modified)
- `data/final_datasets/seattle/seattle_final_analysis_with_seasonal_and_temp.csv`
- `outputs/analysis/seattle_walking_by_utci.csv`

### Required Columns
From Seattle dataset:
- `shadow_ratio` - For SR-IPW
- `dist_to_shade_m` - For DCWP
- `inshade_count`, `outshade_count` - For shade preference
- `person_count` - For weighting
- `utci_C` - For temperature bins
- `w_sr_ipw`, `w_temp_ipw`, `w_dcwp` - Existing weights (for comparison)
- `shade_pref_dcwp` - Existing DCWP adjustment (for comparison)

From walk rate data:
- `utci_bin_center` - UTCI temperature bins
- `walk_rate` - Walking mode share

---

## Methodology

### Approach

Rather than regenerating the full 780K row dataset (which would take 10+ hours), these scripts:

1. **Load existing data** (with default parameters)
2. **Recompute only the relevant weights/adjustments** with varied parameters
3. **Generate ablation tables** using the varied parameters
4. **Save results** to new output files

This approach is:
- **Fast**: ~5-10 minutes vs 10+ hours
- **Safe**: Never modifies source data
- **Accurate**: Uses same computation logic as main pipeline

### Parameters Tested

**Winsorization (c_percentile):**
- Default: 0.95 (95th percentile)
- Tested: {0.90, 0.95, 0.99}

**Detour decay (tau):**
- Default: 20 meters
- Tested: {5, 10, 15, 20, 30, 40, 50} meters

**Walk rate clipping (λ_min):**
- Default: 0.1 (10% minimum)
- Analysis: Compare with vs without clipping

---

## Expected Results

### Winsorization Sensitivity

Final estimates should be **stable** across percentiles (vary by < 2 pp), demonstrating robustness.

**Expected:** All three caps yield ~0.50 final estimate (±0.01)

### Tau Sensitivity

DCWP correction magnitude should **vary with tau**, but SR-IPW should **dominate** at all values.

**Expected:**
- Total correction: ~15-16 pp regardless of tau
- SR-IPW contribution: ~24 pp (constant)
- DCWP contribution: varies from +6 to +12 pp

### Walk Rate Clipping

Clipping should affect **< 1% of observations** (only extreme temperatures) with **modest variance reduction**.

**Expected:**
- Observations affected: < 1%
- Variance reduction: 20-40%
- N_eff improvement: 10-20%

---

## Troubleshooting

### "Data file not found"

Ensure you've run the main analysis pipeline first:
```bash
ls data/final_datasets/seattle/seattle_final_analysis_with_seasonal_and_temp.csv
ls outputs/analysis/seattle_walking_by_utci.csv
```

### "Module not found: sensitivity_utils"

Run scripts from project root or ensure PYTHONPATH is set:
```bash
cd /path/to/sunny_day_SVI
python3 scripts/analysis/sensitivity/sensitivity_winsorization.py
```

### Visualization fails

Ensure tau sensitivity has been run first:
```bash
python3 scripts/analysis/sensitivity/sensitivity_tau.py
python3 scripts/visualization/plot_tau_ablation_sensitivity.py
```

---

## Integration with Paper

### Supplementary Materials

**Table S1**: Winsorization sensitivity
- Location: `outputs/analysis/sensitivity/supplementary_table_s1_winsorization.tex`
- Caption: "Sensitivity to winsorization threshold in shadow ratio inverse probability weighting."

**Table S2**: Tau sensitivity
- Location: `outputs/analysis/sensitivity/supplementary_table_s2_tau.tex`
- Caption: "Sensitivity to detour decay parameter τ in DCWP adjustment."

**Figure S1**: Tau plots
- Main: `outputs/plots/sensitivity/supplementary_figure_s1_tau_sensitivity.pdf`
- Deltas: `outputs/plots/sensitivity/supplementary_figure_s1b_tau_deltas.pdf`

### Text Additions

**Section 2.5.1 (SR-IPW)**: Add 2 sentences referencing Table S1

**Section 2.5.2 (Temp-IPW)**: Add 2 sentences on walk rate clipping

**Section 2.5.3 (DCWP)**: Add 3 sentences referencing Table S2 and Figure S1

---

## Safety Features

### Read-Only Design

All scripts include these safety measures:

1. **No file modifications**: Only read from existing data files
2. **Separate output directory**: All results go to `outputs/analysis/sensitivity/`
3. **Explicit output paths**: No overwriting of main analysis results
4. **Copy-on-modify**: Data filtering creates copies, never modifies originals

### Testing

Before running, verify safety:
```bash
# Check that scripts don't write to data/ directory
grep -r "to_csv.*data/" sensitivity_*.py   # Should return no matches
grep -r "\.to_csv" sensitivity_*.py | grep -v "outputs/"  # Should return no matches
```

---

## Citation

If using these sensitivity analyses, cite the main paper:

```bibtex
@article{sunny_day_svi_2024,
  title={Too Hot to Handle: Why Measuring Human Behavior in Street View Imagery Is Harder Than It Looks},
  author={Elrod, Kieran and Kavee, Korawich and Flanigan, Katherine A. and Bergés, Mario},
  journal={CPHS},
  year={2026}
}
```

---

## Contact

Questions about these sensitivity analyses:
- Review planning documents: `REVIEWER_RESPONSE_PLAN_TEMP.md` and `PARAMETER_SENSITIVITY_PLAN_TEMP.md`
- Check main documentation: `docs/` directory
- Examine existing analysis scripts: `scripts/analysis/compute_ablation_table.py`

---

**Last Updated**: 2026-09-28
