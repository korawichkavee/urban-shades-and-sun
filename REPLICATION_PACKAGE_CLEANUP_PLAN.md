# Replication Package Cleanup Plan

**Date**: 2026-09-28
**Goal**: Create MINIMAL replication package with ONLY what's needed for paper
**Current Size**: ~3.5 GB tracked + archives
**Target Size**: <500 MB (data + code only)

---

## Current State Analysis

### Repository Structure Issues

**Root directory clutter** (22 temp/planning docs):
```
❌ DELETE: Review408.txt, Review508.txt
❌ DELETE: *_TEMP.md (8 files: DCWP_INVESTIGATION, PARAMETER_SENSITIVITY_PLAN, etc.)
❌ DELETE: *_PLAN*.md, *_STATUS.md, *_SUMMARY.md (planning docs from development)
❌ DELETE: PAPER_TEXT_ADDITIONS* (reviewer response prep, not in paper)
❌ DELETE: OVERLAPPING_CI_SOLUTIONS.md, PLOT_IMPROVEMENT_OPTIONS.md (dev notes)
❌ DELETE: *.py files in root (analyze_coverage.py, camera_temporal_coverage.py, etc.)
✅ KEEP: README.md (needs rewrite for minimal replication focus)
```

**Large directories to address**:
```
❌ DELETE ENTIRE: sunny_day_svi_archive/ (717 MB of old code/outputs)
❌ DELETE ENTIRE: nyc_seattle_municipal_deployment/ (717 MB deployment package)
❌ DELETE ENTIRE: tests/ (unit tests, not needed for replication)
❌ DELETE ENTIRE: notebooks/ (exploratory, not in paper)
❌ DELETE ENTIRE: .venv/ (virtual environment, users create their own)
❌ DELETE ENTIRE: .pytest_cache/, __pycache__/ directories
⚠️  REDUCE: docs/ (69 MB, 64 files → keep only essential replication guide)
⚠️  REDUCE: scripts/ (103 scripts → keep only ~10-15 used in paper)
⚠️  REDUCE: outputs/ (108 MB → keep only paper figures)
```

**Sensitivity analysis (just created)**:
```
⚠️  SUPPLEMENTARY: scripts/analysis/sensitivity/ (for supp materials, not main replication)
⚠️  SUPPLEMENTARY: outputs/analysis/sensitivity/ (supp tables/figs)
⚠️  SUPPLEMENTARY: scripts/visualization/plot_tau_ablation_sensitivity.py
```

**Data files**:
```
✅ KEEP: data/final_datasets/seattle/ (Seattle analysis dataset)
✅ KEEP: data/final_datasets/nyc/ (NYC analysis dataset - if used in paper)
✅ KEEP: data/mobility_surveys/ (walking rate data for temperature adjustment)
❌ DELETE: data/vit_training_dataset/ (444 MB, ML training only)
❌ DELETE: data/yolo_training_dataset/ (195 MB, ML training only)
❌ LIKELY DELETE: data/city_boundaries/, data/geographic_lookups/ (only if not used)
```

---

## What's Actually Needed for Paper Replication?

### Core Question: What figures/tables are in the paper?

**Need to identify**:
1. Main paper figures (likely 3-5 figures)
2. Main paper tables (likely 1-2 tables)
3. Supplementary figures (S1, S1b from sensitivity)
4. Supplementary tables (S1, S2 from sensitivity)

**Once identified, keep ONLY**:
- Scripts that generate those exact outputs
- Data files those scripts require
- Minimal documentation to run them

---

## Minimal Replication Package Structure

```
sunny_day_svi_replication/
├── README.md                           # Replication instructions ONLY
├── requirements.txt                    # Python dependencies
│
├── data/                               # Input data ONLY
│   ├── final_datasets/
│   │   └── seattle/                    # Seattle analysis dataset
│   │       └── seattle_final_analysis_with_seasonal_and_temp.csv
│   └── mobility_surveys/
│       └── seattle/                    # Walk rate data
│           └── seattle_walking_by_utci.csv  (or whatever file is actually used)
│
├── scripts/                            # ONLY scripts that make paper outputs
│   ├── analysis/
│   │   └── compute_ablation_table.py   # Main analysis (Table 1)
│   ├── visualization/
│   │   ├── plot_shade_preference_adjustment_progression.py  # Main figure
│   │   └── [2-3 other scripts for paper figures]
│   └── supplementary/                  # If needed
│       ├── sensitivity_winsorization.py
│       ├── sensitivity_tau.py
│       ├── sensitivity_utils.py
│       └── plot_tau_ablation_sensitivity.py
│
└── outputs/                            # Paper outputs (READ-ONLY, for verification)
    ├── main/
    │   ├── ablation_table.csv          # Paper Table 1
    │   └── main_figure.pdf             # Paper main figure
    └── supplementary/
        ├── supplementary_table_s1.tex
        ├── supplementary_table_s2.tex
        ├── supplementary_figure_s1.pdf
        └── supplementary_figure_s1b.pdf
```

**Estimated size**:
- Data: ~400 MB (Seattle dataset + mobility survey)
- Scripts: ~100 KB (5-10 Python files)
- Outputs: ~5 MB (reference figures/tables)
- Docs: ~10 KB (minimal README)
- **Total**: ~405 MB

---

## Cleanup Strategy

### Phase 1: Identify Paper Dependencies (30 minutes)

**Tasks**:
1. List all figures in paper manuscript
2. List all tables in paper manuscript
3. For each figure/table, trace back to:
   - Which script generates it?
   - Which data file(s) does that script require?
   - Which other scripts/utils does it import?

**Deliverable**: `PAPER_FIGURE_TABLE_MANIFEST.md` with:
```markdown
Figure 1: Shade preference adjustment progression
- Script: scripts/visualization/plot_shade_preference_adjustment_progression.py
- Data: data/final_datasets/seattle/seattle_final_analysis_with_seasonal_and_temp.csv
- Data: outputs/analysis/seattle_walking_by_utci.csv
- Output: outputs/plots/[whatever the actual path is]

Table 1: Ablation study results
- Script: scripts/analysis/compute_ablation_table.py
- Data: [same as above]
- Output: outputs/analysis/ablation_study_results.csv

[etc for all figures/tables]
```

### Phase 2: Create Clean Replication Branch (1 hour)

**Steps**:

1. **Create new orphan branch** (no git history):
   ```bash
   git checkout --orphan replication-package
   git rm -rf .
   ```

2. **Copy ONLY needed files**:
   ```bash
   # Based on manifest from Phase 1
   mkdir -p data/final_datasets/seattle
   mkdir -p data/mobility_surveys/seattle
   mkdir -p scripts/analysis
   mkdir -p scripts/visualization
   mkdir -p outputs/main
   mkdir -p outputs/supplementary

   # Copy identified files
   cp [source_path]/seattle_final_analysis_with_seasonal_and_temp.csv data/final_datasets/seattle/
   cp [source_path]/compute_ablation_table.py scripts/analysis/
   # etc for each file from manifest
   ```

3. **Create minimal README.md**:
   - Installation instructions
   - How to run each script to reproduce each figure/table
   - Expected outputs
   - No theory, no background, just "run this, get that"

4. **Create requirements.txt**:
   - Extract ONLY the packages actually used by kept scripts
   - Remove ML deps if no ML scripts kept
   - Minimal set: pandas, numpy, matplotlib, scipy, thermofeel

5. **Test replication**:
   ```bash
   # Fresh virtual environment
   python -m venv test_env
   source test_env/bin/activate
   pip install -r requirements.txt

   # Run each script
   python scripts/analysis/compute_ablation_table.py
   python scripts/visualization/plot_shade_preference_adjustment_progression.py
   # etc

   # Verify outputs match
   ```

### Phase 3: Handle Supplementary Materials (30 minutes)

**Decision point**: Where do supplementary materials go?

**Option A: Include in main replication package**
- Add `scripts/supplementary/` directory
- Add `outputs/supplementary/` directory
- Document in README under "Supplementary Materials" section

**Option B: Separate supplementary package**
- Create `replication-package-supplementary` branch
- Contains only sensitivity analysis scripts/outputs
- Minimal README pointing to main package

**Recommendation**: Option A (easier for reviewers/readers)

### Phase 4: Archive Original Repository (15 minutes)

**On main branch**:

1. **Create archive tag**:
   ```bash
   git checkout main
   git tag -a v1.0-full-development -m "Full development repository before replication cleanup"
   git push origin v1.0-full-development
   ```

2. **Document what was removed**:
   ```markdown
   # ARCHIVE_NOTICE.md

   This repository has been cleaned to a minimal replication package.

   The full development repository (195 GB) with:
   - All exploratory cities (Phoenix, LA, etc.)
   - Machine learning training pipelines
   - 205 development scripts
   - Municipal deployment packages

   is archived at tag: v1.0-full-development

   For the minimal replication package (paper figures/tables only), use branch: replication-package
   ```

---

## Specific Files to Keep/Delete

### DELETE from root (22 files):
```bash
rm Review408.txt Review508.txt
rm *_TEMP.md
rm DCWP_INVESTIGATION_TEMP.md
rm PARAMETER_SENSITIVITY_PLAN_TEMP.md
rm REVIEWER_RESPONSE_PLAN_TEMP.md
rm SENSITIVITY_ANALYSIS_RESULTS_TEMP.md
rm REMAINING_REVIEWER_COMMENTS_DISCUSSION.md
rm PAPER_TEXT_ADDITIONS*.{md,tex}
rm ARCHIVE_MANIFEST.md CLEANUP_*.md CODEBASE_INVENTORY.md
rm PACKAGE_CREATION_SUMMARY.md
rm PHASE_*.md
rm OVERLAPPING_CI_SOLUTIONS.md PLOT_IMPROVEMENT_OPTIONS.md
rm PAPER_CONTRIBUTION_FRAMING_REVIEW.md
rm REPLICATION_PACKAGE_INVENTORY.md
rm PROJECT_STRUCTURE.md  # Rebuild minimal version
rm PLOT_MANIFEST.csv
rm analyze_coverage.py camera_temporal_coverage.py check_days_seasons.py scan_all_dates.py
```

### DELETE entire directories:
```bash
rm -rf sunny_day_svi_archive/
rm -rf nyc_seattle_municipal_deployment/
rm -rf tests/
rm -rf notebooks/
rm -rf .venv/
rm -rf .pytest_cache/
rm -rf config/  # Unless scripts actually use it
rm -rf models/  # Unless needed for replication (likely not)
```

### KEEP (scripts - pending manifest):
```
scripts/analysis/compute_ablation_table.py
scripts/analysis/analyze_walking_vs_utci.py  # If generates walking rate data
scripts/visualization/plot_shade_preference_adjustment_progression.py
scripts/visualization/[2-4 other paper figure scripts]
scripts/processing/[any dependency scripts if needed]

# Supplementary
scripts/analysis/sensitivity/sensitivity_utils.py
scripts/analysis/sensitivity/sensitivity_winsorization.py
scripts/analysis/sensitivity/sensitivity_tau.py
scripts/analysis/sensitivity/sensitivity_walk_rate_clip.py
scripts/visualization/plot_tau_ablation_sensitivity.py
```

### KEEP (data):
```
data/final_datasets/seattle/seattle_final_analysis_with_seasonal_and_temp.csv
data/mobility_surveys/seattle/[whatever file has walk rates]
outputs/analysis/seattle_walking_by_utci.csv  # If generated, not raw
```

### KEEP (outputs - for verification):
```
outputs/analysis/ablation_study_results.csv
outputs/plots/[paper figures]
outputs/analysis/sensitivity/supplementary_table_s1*.{csv,tex}
outputs/analysis/sensitivity/supplementary_table_s2*.{csv,tex}
outputs/plots/sensitivity/supplementary_figure_s1*.pdf
```

---

## Questions to Answer Before Cleanup

### 1. Which city is actually in the paper?
- **Seattle only?** Delete NYC data entirely
- **Both NYC and Seattle?** Keep both, but verify both are used
- **Cross-city comparison?** Keep both + comparison scripts

### 2. Which figures/tables are in the paper?
**Main paper**:
- [ ] Figure 1: [description] → script: [?]
- [ ] Figure 2: [description] → script: [?]
- [ ] Table 1: Ablation study → script: compute_ablation_table.py ✓
- [ ] [list all]

**Supplementary**:
- [ ] Table S1: Winsorization sensitivity
- [ ] Table S2: Tau sensitivity
- [ ] Figure S1: Tau ablation curves
- [ ] [list all]

### 3. What data files are actually read by kept scripts?
Run dependency check:
```bash
# For each script we're keeping
grep -n "read_csv\|read_excel\|pd.read" script.py
# List all data files actually loaded
```

### 4. Are ML models needed?
- If no figures show ML predictions → DELETE models/, data/*training_dataset/
- If paper discusses ML but doesn't show predictions → DELETE training data, keep model description
- If figures include detection visualizations → KEEP models/yolo_best.pt

### 5. Is NYC used in paper?
- If paper is Seattle-only → DELETE data/final_datasets/nyc/
- If paper mentions NYC for context but no NYC figures → DELETE NYC data
- If paper has NYC vs Seattle comparison → KEEP both

---

## Recommended Next Steps

1. **STOP** - Don't delete anything yet

2. **Create manifest** (30 min):
   - Open paper PDF/LaTeX
   - List every figure and table
   - Trace each to source script
   - Document all data dependencies

3. **Review manifest with you** (confirm what to keep)

4. **Create test branch** (1 hour):
   - Copy only manifest-identified files to new clean branch
   - Test that scripts run and produce correct outputs

5. **Final cleanup** (30 min):
   - Archive main branch
   - Make replication branch default
   - Update README

---

## Size Reduction Estimate

**Current**:
- Tracked in git: ~3.5 GB
- Untracked (archives): ~650 MB

**After cleanup**:
- Data: ~400 MB (Seattle final dataset + mobility)
- Scripts: ~100 KB (10-15 files)
- Outputs: ~5 MB (reference figures)
- Docs: ~10 KB (minimal README)
- **Total: ~405 MB** (90% reduction)

**If Seattle only** (no NYC):
- Data: ~360 MB
- **Total: ~365 MB** (95% reduction)

---

## Next Action

**I need from you**:

1. **Which city/cities are actually in the paper?**
   - Seattle only?
   - Both Seattle and NYC?

2. **List of paper figures/tables** (or send me the LaTeX/PDF)
   - Main paper: Figure 1, Figure 2, Table 1, etc.
   - Supplementary: Table S1, S2, Figure S1, etc.

3. **Should I create the manifest first?**
   - Option A: You tell me which figures, I trace dependencies
   - Option B: I look at paper and create manifest myself

Once I have this info, I can:
- Create precise file manifest
- Test clean replication package
- Estimate exact final size
- Execute cleanup

---

**Status**: Ready for your input on scope
**Estimated cleanup time**: 2-3 hours after manifest is confirmed
