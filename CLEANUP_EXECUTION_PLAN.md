# Replication Package Cleanup: Execution Plan

**Date**: 2026-09-28
**Goal**: Reduce repository to MINIMAL replication package (Seattle only)
**Current**: 3.5 GB tracked → **Target**: 362 MB (90% reduction)

---

## Summary

Based on paper LaTeX analysis, we need to keep ONLY:

**Data (2 files, 361 MB)**:
- `data/final_datasets/seattle/seattle_final_analysis_with_seasonal_and_temp.csv` (361 MB)
- `outputs/analysis/seattle_walking_by_utci.csv` (2.8 KB)

**Scripts (5 files, ~50 KB)**:
- `scripts/analysis/compute_ablation_table.py` → Table 2
- `scripts/visualization/plot_shade_preference_adjustment_progression.py` → Figure 2
- `scripts/analysis/sensitivity/sensitivity_utils.py` → Utilities
- `scripts/analysis/sensitivity/sensitivity_winsorization.py` → Table 3
- `scripts/analysis/sensitivity/sensitivity_tau.py` → Table 4

**Outputs (4 files for verification, ~1 MB)**:
- `outputs/analysis/ablation_study_results.csv` → Table 2 output
- `outputs/analysis/sensitivity/supplementary_table_s1_winsorization.csv` → Table 3
- `outputs/analysis/sensitivity/supplementary_table_s2_tau.csv` → Table 4
- `outputs/plots/[Figure 2 path]` → Figure 2 output

---

## Phase 1: Backup and Safety (5 minutes)

### Create archive tag
```bash
git add -A
git commit -m "Snapshot before minimal replication cleanup"
git tag -a v1.0-full-repository -m "Full repository before minimal replication cleanup (3.5 GB)"
git push origin v1.0-full-repository
```

### Create test branch
```bash
git checkout -b replication-package-test
```

**Purpose**: Test cleanup without affecting main branch

---

## Phase 2: Delete Large Directories (remove 3.1 GB)

```bash
# NYC data (not used in paper)
rm -rf data/final_datasets/nyc/                          # ~124 MB

# ML training data (ML models not needed for replication)
rm -rf data/vit_training_dataset/                        # 444 MB
rm -rf data/yolo_training_dataset/                       # 195 MB
rm -rf models/                                           # 110 MB

# Archive directories
rm -rf sunny_day_svi_archive/                            # 717 MB
rm -rf nyc_seattle_municipal_deployment/                 # 717 MB
rm nyc_seattle_municipal_shadow_analysis_v1.0.tar.gz     # 663 MB
rm nyc_seattle_municipal_shadow_analysis_v1.0.tar.gz.md5
rm nyc_seattle_municipal_shadow_analysis_v1.0.tar.gz.sha256

# Development directories
rm -rf tests/                                            # 120 KB
rm -rf notebooks/                                        # 4.2 MB
rm -rf .venv/                                            # varies
rm -rf .pytest_cache/                                    # small
rm -rf docs/                                             # 69 MB

# Config (unless scripts use it - check first)
rm -rf config/                                           # small

# Unused data directories
rm -rf data/city_boundaries/                             # 2.2 MB
rm -rf data/geographic_lookups/                          # 904 KB
rm -rf data/outputs/                                     # if it exists

# Remove __pycache__ directories
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
```

**Savings**: ~3.1 GB

---

## Phase 3: Delete Unused Scripts (remove 2.9 MB)

### Delete all processing scripts (data already processed)
```bash
rm -rf scripts/processing/
```

### Delete all data collection scripts (data already collected)
```bash
rm -rf scripts/data_collection/
```

### Delete all ML scripts (ML training not needed)
```bash
rm -rf scripts/ml/
```

### Delete all pipeline scripts (data already processed)
```bash
rm -rf scripts/pipelines/
```

### Delete utils scripts (not imported by kept scripts)
```bash
rm -rf scripts/utils/
```

### Clean up analysis/ directory (keep only 1 file + sensitivity/)
```bash
cd scripts/analysis/
# Keep: compute_ablation_table.py, sensitivity/
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

# Clean up sensitivity/ (keep only utils, winsorization, tau)
cd sensitivity/
rm sensitivity_walk_rate_clip.py
rm run_all_sensitivity.sh
rm README.md
cd ../..
```

### Clean up visualization/ directory (keep only 1 file)
```bash
cd scripts/visualization/
# Keep: plot_shade_preference_adjustment_progression.py
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
rm plot_tau_ablation_sensitivity.py
rm plot_tau_curve.py
rm plot_tau_sensitivity.py
rm plot_utci_shade_curves_explicit.py
rm plot_utci_shade_preference_curves.py
rm plot_utci_shade_preference_final.py
rm plot_walk_rate_validation.py
rm plot_weight_distributions.py
rm visualize_*.py
cd ../..
```

**Savings**: ~2.9 MB

---

## Phase 4: Delete Unused Outputs (remove ~100 MB)

```bash
cd outputs/

# Keep only:
# - outputs/analysis/ablation_study_results.csv
# - outputs/analysis/seattle_walking_by_utci.csv
# - outputs/analysis/sensitivity/*.csv
# - outputs/plots/[Figure 2 path - need to identify]

# Delete model outputs
rm -rf model_evaluation/
rm -rf models/

# Delete most analysis files
cd analysis/
rm boundary_coverage_full.log
rm cities_need_svi_download.json
rm download_progress.json
rm municipal_*.csv
rm nyc_walking_by_utci.csv
rm newyorkcity_walking_by_utci.csv  # symlink
rm utci_shade_preference_curves.pdf
rm utci_shade_preference_curves.png
rm WALKING_UTCI_ANALYSIS.md
rm -rf figures/  # Unless contains Figure 2
cd ..

# Clean up plots/ (keep only Figure 2 location)
# BEFORE DELETING: Identify where Figure 2 is saved
cd plots/
# Keep outputs/plots/shade_preference_adjustment_progression.{png,pdf}
# OR wherever plot_shade_preference_adjustment_progression.py saves Figure 2

# Delete everything else
rm -rf commute_hours/
rm -rf people_count/
rm -rf temperature_comparison/
# Be careful with shade_behavior/ and ipw_weighted/ - may contain Figure 2
cd ../..
```

**Savings**: ~100 MB

---

## Phase 5: Delete Root Documentation (remove ~70 MB)

```bash
# Delete temp/planning documents
rm Review408.txt Review508.txt
rm *_TEMP.md
rm DCWP_INVESTIGATION_TEMP.md
rm PARAMETER_SENSITIVITY_PLAN_TEMP.md
rm REVIEWER_RESPONSE_PLAN_TEMP.md
rm SENSITIVITY_ANALYSIS_RESULTS_TEMP.md
rm REMAINING_REVIEWER_COMMENTS_DISCUSSION.md
rm PAPER_TEXT_ADDITIONS*.{md,tex}
rm REPLICATION_PACKAGE_CLEANUP_PLAN.md  # this file, after done
rm MINIMAL_REPLICATION_MANIFEST.md      # this file, after done

# Delete development documentation
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

# Delete root scripts
rm analyze_coverage.py
rm camera_temporal_coverage.py
rm check_days_seasons.py
rm scan_all_dates.py

# Delete LaTeX extraction (after verifying manifest)
rm -rf latex_source_temp/
rm Street_view_image_urban_shade.zip
```

**Savings**: ~70 MB

---

## Phase 6: Create Minimal Documentation (15 minutes)

### Rewrite README.md
```markdown
# Replication Package: Street View Bias in Behavioral Measurement

Replication code for CPHS 2026: "Too Hot to Handle: Why Measuring Human Behavior in Street View Imagery Is Harder Than It Looks"

**Authors**: Kieran Elrod, Korawich Kavee, Katherine Flanigan, Mario Bergés
**Institution**: Carnegie Mellon University

---

## Quick Start

### Install Dependencies
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Generate Paper Outputs

```bash
# Table 2: Main ablation analysis
python scripts/analysis/compute_ablation_table.py

# Figure 2: Shade preference curves
python scripts/visualization/plot_shade_preference_adjustment_progression.py

# Table 3: Winsorization sensitivity
python scripts/analysis/sensitivity/sensitivity_winsorization.py

# Table 4: Tau sensitivity
python scripts/analysis/sensitivity/sensitivity_tau.py
```

---

## Outputs

| Paper Element | Output File | Script |
|---------------|-------------|--------|
| Table 2 (Ablation) | `outputs/analysis/ablation_study_results.csv` | `compute_ablation_table.py` |
| Figure 2 (Curves) | `outputs/plots/shade_preference_adjustment_progression.{png,pdf}` | `plot_shade_preference_adjustment_progression.py` |
| Table 3 (Winsorization) | `outputs/analysis/sensitivity/supplementary_table_s1_winsorization.csv` | `sensitivity_winsorization.py` |
| Table 4 (Tau) | `outputs/analysis/sensitivity/supplementary_table_s2_tau.csv` | `sensitivity_tau.py` |

---

## Data

### Seattle Street View Dataset
**File**: `data/final_datasets/seattle/seattle_final_analysis_with_seasonal_and_temp.csv` (361 MB)

**Columns**:
- `image_id`: Mapillary image identifier
- `utci_C`: Universal Thermal Climate Index (°C)
- `person_count`: Number of pedestrians detected
- `inshade_count`: Pedestrians in shade
- `outshade_count`: Pedestrians in sun
- `in_shade`: Camera location in shade (boolean)
- `shadow_ratio`: Fraction of street in shade
- `dist_to_shade_m`: Distance to nearest shade boundary (meters)
- `w_sr_ipw`: Shadow ratio inverse probability weight
- `w_dcwp`: Distance-conditioned walk preference weight
- `w_seasonal`: Seasonal bias correction weight

**Images**: 51,243 with pedestrians
**UTCI Range**: -17°C to 33°C
**Source**: Mapillary street view imagery (2015-2023)

### Seattle Walking Mode Share
**File**: `outputs/analysis/seattle_walking_by_utci.csv` (2.8 KB)

**Columns**:
- `utci_bin_center`: UTCI temperature bin center (°C)
- `walk_rate`: Proportion of trips on foot

**Source**: Puget Sound Regional Council Household Travel Survey 2023 (n=56,704 trips)

---

## Dependencies

Core packages (see `requirements.txt`):
- `pandas>=2.0.0` - Data manipulation
- `numpy>=1.24.0` - Numerical operations
- `scipy>=1.11.0` - Statistical functions
- `matplotlib>=3.7.0` - Visualization
- `seaborn>=0.12.0` - Statistical plots
- `thermofeel>=1.0.0` - UTCI calculations

---

## Repository Structure

```
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── data/                              # Input datasets
│   └── final_datasets/seattle/        # Seattle analysis data
├── scripts/                           # Analysis scripts
│   ├── analysis/                      # Main analysis
│   │   ├── compute_ablation_table.py
│   │   └── sensitivity/               # Sensitivity analyses
│   └── visualization/                 # Figure generation
└── outputs/                           # Results (generated)
    ├── analysis/                      # Tables and CSV outputs
    └── plots/                         # Figures (PDF/PNG)
```

---

## Citation

```bibtex
@inproceedings{elrod2026hot,
  title={Too Hot to Handle: Why Measuring Human Behavior in Street View Imagery Is Harder Than It Looks},
  author={Elrod, Kieran and Kavee, Korawich and Flanigan, Katherine and Bergés, Mario},
  booktitle={IFAC Conference on Cyber-Physical Human Systems (CPHS)},
  year={2026}
}
```

---

## License

[License information to be added]

---

## Contact

Questions or issues: [contact information]

For the full development repository with ML training pipelines and multi-city analysis, see tag `v1.0-full-repository`.
```

### Create requirements.txt
```txt
# Core dependencies for replication
pandas>=2.0.0
numpy>=1.24.0
scipy>=1.11.0
matplotlib>=3.7.0
seaborn>=0.12.0
thermofeel>=1.0.0
```

### Update .gitignore
```txt
# Python
__pycache__/
*.py[cod]
*$py.class
.Python
.venv/
venv/
ENV/
env/

# Outputs (regenerated by scripts)
outputs/analysis/*.csv
outputs/plots/*.png
outputs/plots/*.pdf

# OS
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/
*.swp
*.swo
```

---

## Phase 7: Test Replication (30 minutes)

### Create fresh test environment
```bash
# On test branch
python -m venv test_env
source test_env/bin/activate
pip install -r requirements.txt
```

### Run all scripts
```bash
# Should complete without errors
python scripts/analysis/compute_ablation_table.py
python scripts/visualization/plot_shade_preference_adjustment_progression.py
python scripts/analysis/sensitivity/sensitivity_winsorization.py
python scripts/analysis/sensitivity/sensitivity_tau.py
```

### Verify outputs match paper
```bash
# Check Table 2 values
cat outputs/analysis/ablation_study_results.csv
# Should show: 0.657, 0.649, 0.405, 0.501

# Check Table 3 values
cat outputs/analysis/sensitivity/supplementary_table_s1_winsorization.csv
# Should show: 0.525 (90th), 0.501 (95th), 0.485 (99th)

# Check Table 4 values
cat outputs/analysis/sensitivity/supplementary_table_s2_tau.csv
# Should show tau=20: 0.453

# Check Figure 2 exists
ls outputs/plots/shade_preference_adjustment_progression.*
```

---

## Phase 8: Finalize Cleanup (15 minutes)

### If test passes, apply to main branch
```bash
# Commit test branch
git add -A
git commit -m "Minimal replication package - Seattle only"

# Merge to main
git checkout main
git merge replication-package-test

# Tag the clean version
git tag -a v1.0-replication-package -m "Minimal replication package (362 MB)"
git push origin main v1.0-replication-package
```

### Create archive of full repository (if not already done)
```bash
# Tag full repository before cleanup (if not done in Phase 1)
git checkout v1.0-full-repository  # The tag created earlier
tar -czf full_repository_archive.tar.gz .
# Move to external storage
```

---

## Phase 9: Verification (10 minutes)

### Check repository size
```bash
# Show tracked files size
git ls-files | xargs -I {} du -h {} | sort -h | tail -20

# Total size
du -sh .

# Should be ~362 MB (excluding .git/)
```

### Verify file counts
```bash
# Should have 5 Python scripts
find scripts/ -name "*.py" | wc -l  # Should be 5

# Should have 2 data files
find data/ -type f | wc -l  # Should be 1 (CSV only)
find outputs/analysis/ -maxdepth 1 -type f -name "*.csv" | wc -l  # Should be 2 (walk rate + ablation)
```

### Test fresh clone
```bash
# Clone to new location
cd /tmp
git clone [repository-url] test_clone
cd test_clone

# Verify replication works
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/analysis/compute_ablation_table.py
# Should complete successfully
```

---

## Summary Checklist

- [ ] Phase 1: Create backup tag `v1.0-full-repository`
- [ ] Phase 2: Delete large directories (3.1 GB removed)
- [ ] Phase 3: Delete unused scripts (2.9 MB removed)
- [ ] Phase 4: Delete unused outputs (100 MB removed)
- [ ] Phase 5: Delete root documentation (70 MB removed)
- [ ] Phase 6: Create minimal README and requirements.txt
- [ ] Phase 7: Test replication in fresh environment
- [ ] Phase 8: Merge to main and tag `v1.0-replication-package`
- [ ] Phase 9: Verify final size (~362 MB)

---

## Before You Start

**Critical checks**:
1. ✅ Seattle only (no NYC needed) - CONFIRMED
2. ⏸️ Verify Figure 2 output path - need to check `output_dir` definition
3. ⏸️ Confirm no scripts import from `scripts/utils/` or `scripts/processing/`
4. ⏸️ Test that sensitivity scripts don't need `sensitivity_walk_rate_clip.py`

**Once verified, you can execute this plan to reduce repository from 3.5 GB to 362 MB.**

---

**Status**: Plan ready, awaiting final verification checks
**Estimated time**: 2 hours (including testing)
**Risk**: Low (backup tag created first)
