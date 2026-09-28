# Minimal Replication Package Manifest

**Date**: 2026-09-28
**Source**: Street_view_image_urban_shade.zip (paper LaTeX)
**Scope**: Seattle only, no NYC

---

## Paper Contents (from LaTeX)

### Figures

**Figure 1** (`figur/Figure1.png`): Data processing pipeline diagram
- **Type**: Conceptual diagram (not code-generated)
- **Status**: ✅ Static image, already in LaTeX package
- **Replication**: NOT NEEDED (diagram, not analysis output)

**Figure 2** (`figur/Figure2.png`): Shade preference estimates with progressive bias corrections
- **Description**: Shows raw, +temp, +SR-IPW, +DCWP curves with error bars
- **Script**: `scripts/visualization/plot_shade_preference_adjustment_progression.py`
- **Status**: ✅ KEEP - generates main paper figure

### Tables

**Table 1** (`tab:model-performance`): Model validation performance (ViT, YOLO)
- **Type**: Manually created from ML training results
- **Replication**: NOT NEEDED (ML training is out of scope)
- **Status**: Static table in LaTeX

**Table 2** (`tab:ablation`): Ablation analysis of bias corrections
- **Script**: `scripts/analysis/compute_ablation_table.py`
- **Status**: ✅ KEEP - generates main analysis table

**Table 3** (`tab:sensitivity-winsorization`): Winsorization sensitivity (R2.1)
- **Script**: `scripts/analysis/sensitivity/sensitivity_winsorization.py`
- **Status**: ✅ KEEP - generates sensitivity table

**Table 4** (`tab:sensitivity-tau`): Tau sensitivity (R2.2)
- **Script**: `scripts/analysis/sensitivity/sensitivity_tau.py`
- **Status**: ✅ KEEP - generates sensitivity table

---

## Replication Package Contents

### Data Files (Seattle only)

```
data/
├── final_datasets/
│   └── seattle/
│       └── seattle_final_analysis_with_seasonal_and_temp.csv  (~361 MB)
└── mobility_surveys/
    └── seattle/
        └── [walk rate file - need to identify exact filename]
```

**OR** (if walk rate is derived):
```
outputs/analysis/
└── seattle_walking_by_utci.csv  (~2 KB, if pre-computed)
```

**Estimated data size**: ~361 MB (Seattle dataset only)

---

### Scripts to Keep (5 core files)

```
scripts/
├── analysis/
│   ├── compute_ablation_table.py                    # Table 2 (main ablation)
│   └── sensitivity/
│       ├── sensitivity_utils.py                     # Shared utilities
│       ├── sensitivity_winsorization.py             # Table 3
│       └── sensitivity_tau.py                       # Table 4
└── visualization/
    └── plot_shade_preference_adjustment_progression.py  # Figure 2
```

**Plus dependencies** (if these scripts import from elsewhere):
- Check imports in each script
- Keep only the imported utility modules
- Likely needs: None (scripts are self-contained with sensitivity_utils.py)

**Estimated script size**: ~50 KB

---

### Outputs (for verification)

```
outputs/
├── analysis/
│   ├── ablation_study_results.csv                   # Table 2 output
│   └── sensitivity/
│       ├── supplementary_table_s1_winsorization.csv # Table 3 output
│       └── supplementary_table_s2_tau.csv           # Table 4 output
└── plots/
    └── [Figure 2 output path - need to identify]
```

**Estimated output size**: ~1 MB

---

### Documentation

```
README.md                      # Replication instructions (rewrite)
requirements.txt               # Python dependencies (minimal)
.gitignore                     # Standard Python ignores
LICENSE                        # License file
```

**Estimated doc size**: ~10 KB

---

## Total Package Size Estimate

| Component | Size |
|-----------|------|
| Data | 361 MB |
| Scripts | 50 KB |
| Outputs (verification) | 1 MB |
| Documentation | 10 KB |
| **Total** | **~362 MB** |

**Reduction**: 3.5 GB → 362 MB (90% reduction)

---

## Files to DELETE (by category)

### 1. Delete NYC data entirely
```bash
rm -rf data/final_datasets/nyc/
rm outputs/analysis/nyc_walking_by_utci.csv  # if exists
```
**Savings**: ~124 MB

### 2. Delete ML training data
```bash
rm -rf data/vit_training_dataset/      # 444 MB
rm -rf data/yolo_training_dataset/     # 195 MB
rm -rf models/                         # 110 MB (YOLO model)
```
**Savings**: ~749 MB
**Justification**: ML model performance (Table 1) is static in LaTeX; training not needed for replication

### 3. Delete unused data directories
```bash
rm -rf data/city_boundaries/          # Only if not used by scripts
rm -rf data/geographic_lookups/       # Only if not used by scripts
rm -rf data/outputs/                  # Duplicate of outputs/?
```
**Savings**: ~3 MB (if unused)

### 4. Delete large archive directories
```bash
rm -rf sunny_day_svi_archive/         # 717 MB old code
rm -rf nyc_seattle_municipal_deployment/  # 717 MB deployment
rm nyc_seattle_municipal_shadow_analysis_v1.0.tar.gz  # 663 MB
rm nyc_seattle_municipal_shadow_analysis_v1.0.tar.gz.{md5,sha256}
```
**Savings**: ~2.1 GB

### 5. Delete development/test directories
```bash
rm -rf tests/
rm -rf notebooks/
rm -rf .pytest_cache/
rm -rf .venv/
rm -rf config/  # Unless scripts import from it
find . -type d -name "__pycache__" -exec rm -rf {} +
```
**Savings**: ~50 MB

### 6. Delete unused scripts

**Keep only these 5 scripts:**
- `scripts/analysis/compute_ablation_table.py`
- `scripts/analysis/sensitivity/sensitivity_utils.py`
- `scripts/analysis/sensitivity/sensitivity_winsorization.py`
- `scripts/analysis/sensitivity/sensitivity_tau.py`
- `scripts/visualization/plot_shade_preference_adjustment_progression.py`

**Delete everything else in scripts/**:
```bash
# Delete unused analysis scripts (keep only compute_ablation_table.py + sensitivity/)
cd scripts/analysis/
rm analyze_walking_vs_utci.py
rm annotate_trips_with_utci.py
rm check_municipal_boundary_coverage.py
rm check_shadow_temp_correlation.py
rm compute_spatial_emd_bias.py
rm create_municipal_only_datasets.py
rm filter_utci_by_wind.py
rm generate_graph_emd_report.py
rm generate_seasonal_bias_report.py
rm investigate_curve_patterns.py
rm investigate_extreme_utci.py
rm seasonal_bias_filtering_stages.py
rm sr_ipw_investigation.py

# Delete sensitivity walk rate clip (not in paper)
rm sensitivity/sensitivity_walk_rate_clip.py
rm sensitivity/run_all_sensitivity.sh
rm sensitivity/README.md

# Delete unused visualization scripts (keep only plot_shade_preference_adjustment_progression.py)
cd ../visualization/
rm calculate_person_probability_weights.py
rm plot_binned_estimates.py
rm plot_cross_city_statistical_comparison.py
rm plot_data_quality_diagnostics.py
rm plot_effect_decomposition.py
rm plot_ipw_smooth_curves.py
rm plot_pedestrian_mode_choice_vs_temp.py
rm plot_person_capture_probability.py
rm plot_residual_diagnostics.py
rm plot_sample_sizes_presentation.py
rm plot_seasonal_adjustment_effect.py
rm plot_seasonal_bootstrap_comparison.py
rm plot_seasonally_adjusted_curves.py
rm plot_sr_threshold_sensitivity.py
rm plot_tau_ablation_sensitivity.py  # Generates supp figure, not in paper
rm plot_tau_curve.py
rm plot_tau_sensitivity.py
rm plot_utci_shade_curves_explicit.py
rm plot_utci_shade_preference_curves.py
rm plot_utci_shade_preference_final.py
rm plot_walk_rate_validation.py
rm plot_weight_distributions.py
rm visualize_*.py  # All exploratory visualization scripts

# Delete ALL processing scripts (data already processed)
rm -rf ../processing/

# Delete ALL data collection scripts (data already collected)
rm -rf ../data_collection/

# Delete ALL ML scripts (ML training not needed)
rm -rf ../ml/

# Delete ALL pipeline scripts (data already processed)
rm -rf ../pipelines/

# Delete ALL utils (unless imported by kept scripts - check first)
# Probably can delete, but verify imports first
```

**Savings**: ~2.5 MB

### 7. Delete unused outputs

**Keep only**:
- `outputs/analysis/ablation_study_results.csv`
- `outputs/analysis/seattle_walking_by_utci.csv`
- `outputs/analysis/sensitivity/*.csv`
- `outputs/plots/[Figure 2 path]`

**Delete**:
```bash
rm -rf outputs/plots/shade_behavior/  # Unless contains Figure 2
rm -rf outputs/plots/ipw_weighted/    # Unless contains Figure 2
rm -rf outputs/plots/commute_hours/
rm -rf outputs/plots/people_count/
rm -rf outputs/plots/temperature_comparison/
rm -rf outputs/model_evaluation/
rm -rf outputs/models/
rm outputs/analysis/boundary_coverage_full.log
rm outputs/analysis/cities_need_svi_download.json
rm outputs/analysis/download_progress.json
rm outputs/analysis/municipal_*.csv
rm outputs/analysis/utci_shade_preference_curves.{pdf,png}  # Unless this IS Figure 2
rm outputs/analysis/WALKING_UTCI_ANALYSIS.md
rm outputs/analysis/figures/  # Unless contains Figure 2
```

**Savings**: ~100 MB

### 8. Delete documentation (except README)

**Delete from root**:
```bash
rm Review408.txt Review508.txt
rm *_TEMP.md
rm DCWP_INVESTIGATION_TEMP.md
rm PARAMETER_SENSITIVITY_PLAN_TEMP.md
rm REVIEWER_RESPONSE_PLAN_TEMP.md
rm SENSITIVITY_ANALYSIS_RESULTS_TEMP.md
rm REMAINING_REVIEWER_COMMENTS_DISCUSSION.md
rm PAPER_TEXT_ADDITIONS*.{md,tex}
rm ARCHIVE_MANIFEST.md
rm CLEANUP_*.md
rm CODEBASE_INVENTORY.md
rm PACKAGE_CREATION_SUMMARY.md
rm PHASE_*.md
rm OVERLAPPING_CI_SOLUTIONS.md
rm PLOT_IMPROVEMENT_OPTIONS.md
rm PAPER_CONTRIBUTION_FRAMING_REVIEW.md
rm REPLICATION_PACKAGE_INVENTORY.md
rm PROJECT_STRUCTURE.md
rm PLOT_MANIFEST.csv

# Root scripts (not needed)
rm analyze_coverage.py
rm camera_temporal_coverage.py
rm check_days_seasons.py
rm scan_all_dates.py
```

**Delete docs/ entirely** (rebuild minimal version if needed):
```bash
rm -rf docs/
```

**Savings**: ~70 MB

---

## Script Dependency Check

Before deleting, verify imports in kept scripts:

```bash
# Check what each script imports
grep -n "^import\|^from" scripts/analysis/compute_ablation_table.py
grep -n "^import\|^from" scripts/analysis/sensitivity/sensitivity_utils.py
grep -n "^import\|^from" scripts/analysis/sensitivity/sensitivity_winsorization.py
grep -n "^import\|^from" scripts/analysis/sensitivity/sensitivity_tau.py
grep -n "^import\|^from" scripts/visualization/plot_shade_preference_adjustment_progression.py
```

**If any import from `scripts/utils/` or `scripts/processing/`:**
- Keep only the imported module
- Delete the rest

---

## Minimal README.md (rewrite)

```markdown
# Replication Package: Street View Bias in Behavioral Measurement

Replication code for CPHS 2026 paper: "Too Hot to Handle: Why Measuring Human Behavior in Street View Imagery Is Harder Than It Looks"

## Quick Start

```bash
# Install dependencies
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Generate Table 2 (main ablation)
python scripts/analysis/compute_ablation_table.py

# Generate Figure 2 (shade preference curves)
python scripts/visualization/plot_shade_preference_adjustment_progression.py

# Generate Table 3 (winsorization sensitivity)
python scripts/analysis/sensitivity/sensitivity_winsorization.py

# Generate Table 4 (tau sensitivity)
python scripts/analysis/sensitivity/sensitivity_tau.py
```

## Outputs

- **Table 2**: `outputs/analysis/ablation_study_results.csv`
- **Figure 2**: `outputs/plots/[path]`
- **Table 3**: `outputs/analysis/sensitivity/supplementary_table_s1_winsorization.csv`
- **Table 4**: `outputs/analysis/sensitivity/supplementary_table_s2_tau.csv`

## Data

- Seattle street view analysis dataset: `data/final_datasets/seattle/seattle_final_analysis_with_seasonal_and_temp.csv` (361 MB)
- Walking mode share data: `outputs/analysis/seattle_walking_by_utci.csv` (2 KB)

## Dependencies

See `requirements.txt`. Core packages:
- pandas, numpy, scipy
- matplotlib, seaborn
- thermofeel (UTCI calculations)

## Citation

[Citation info]

## License

[License info]
```

---

## Minimal requirements.txt

```txt
# Core data processing
pandas>=2.0.0
numpy>=1.24.0
scipy>=1.11.0

# Visualization
matplotlib>=3.7.0
seaborn>=0.12.0

# UTCI calculations
thermofeel>=1.0.0

# Utilities
pathlib
```

**Remove from requirements.txt**:
- torch, ultralytics, transformers, torchvision (ML)
- geopandas, osmnx, shapely (geospatial processing)
- requests (API calls)
- plotly, jupyter, pytest (development)

---

## Actions Before Cleanup

1. **Identify Figure 2 output path**:
   ```bash
   grep -n "savefig\|plt.save" scripts/visualization/plot_shade_preference_adjustment_progression.py
   ```

2. **Identify walk rate data source**:
   ```bash
   grep -n "read_csv\|pd.read" scripts/analysis/compute_ablation_table.py | grep walking
   ```

3. **Verify script imports** (check if utils/ or processing/ needed):
   ```bash
   grep "from scripts" scripts/analysis/compute_ablation_table.py
   grep "from scripts" scripts/visualization/plot_shade_preference_adjustment_progression.py
   ```

4. **Test replication on clean branch**:
   - Create new branch
   - Copy only files in this manifest
   - Run all 4 scripts
   - Verify outputs match paper tables/figures

---

## Next Steps

1. ✅ You confirm: Seattle only, no NYC
2. ⏸️ Identify Figure 2 output path
3. ⏸️ Identify walk rate data file
4. ⏸️ Check script imports for dependencies
5. ⏸️ Create test branch with minimal files
6. ⏸️ Test replication
7. ⏸️ Execute cleanup on main branch

---

**Status**: Manifest complete, awaiting verification checks
**Estimated final size**: 362 MB (90% reduction from 3.5 GB)
