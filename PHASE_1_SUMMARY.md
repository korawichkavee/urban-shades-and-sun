# Phase 1 Summary: Repository Cleanup Assessment

**Completed**: 2026-04-21
**Status**: Ready for your review
**Next**: Phase 2 - Archive Creation (pending your approval)

---

## What Was Accomplished

Phase 1 created a comprehensive assessment of the repository and detailed plans for cleanup. Three key documents were produced:

1. **REPLICATION_PACKAGE_INVENTORY.md** - What stays in publication repo
2. **ARCHIVE_MANIFEST.md** - What gets archived (detailed file listings)
3. **PLOT_MANIFEST.csv** - Classification of all 566 plots

---

## Key Findings

### Repository Size Reduction
- **Current**: 195 GB (204 scripts, 566 plots, 75+ docs)
- **Target**: 10-12 GB publication package
- **Archive**: ~185 GB to non-git-tracked subdirectory

### Critical Discovery: Transit Surveys
The 27 GB `data/transit_surveys/` directory contains **historical metro surveys (1968-2008)** and is NOT used in the final analysis. The actual mobility data comes from:
- NYC: 2022 Citywide Mobility Survey (in `final_cities/NYC/`)
- Seattle: Recent Household Travel Survey (in `final_cities/seattle/`)
- Already extracted: `nyc_trips_with_utci.csv` (40 MB) and `seattle_trips_with_utci.csv` (58 MB)

**Action**: Archive entire `data/transit_surveys/` directory (27 GB savings)

### Data Breakdown

**To Archive (~185 GB)**:
- Raw SVI imagery: 129 GB (`data/raw/`)
- Transit surveys: 27 GB (`data/transit_surveys/`)
- Metro SVI data: ~30 GB (6 directories with metro_* names)
- Other cities: ~1.5 GB (State College, Boston, DC, multi-city results)
- Test/cache: ~500 MB

**To Keep (~7-8 GB core data)**:
- NYC/Seattle final datasets: 5.5 GB (`final_run_outputs/`)
- NYC/Seattle mobility surveys: 185 MB (`final_cities/NYC/`, `final_cities/seattle/`)
- NYC/Seattle trips with UTCI: 98 MB (`outputs/analysis/`)
- YOLO training dataset: 195 MB (`data/yolo_training_dataset/`)
- Geographic boundaries: <10 MB (to be extracted)

**Models (438 MB)**:
- ViT binary classifier: 328 MB
- YOLO best model: 110 MB

### Scripts Breakdown

**To Archive (~100+ scripts)**:
- Phoenix: 5 scripts
- State College: 20+ scripts
- Metro cities: 15+ scripts
- OT-SVI module: 29 scripts (used in different paper)
- Seasonal bias investigation: 8+ scripts
- Diagnostic/exploratory: 10+ scripts
- Root directory: 4 scripts

**To Keep (~40-50 production scripts)**:
- Final cities processing: `add_shadow_to_final_cities_optimized.py`, `add_utci_to_final_cities.py`, etc.
- IPW corrections: `apply_triple_ipw_final_cities_revised.py`
- Seasonal adjustment: `apply_seasonal_reweighting.py`
- Mobility survey analysis: `annotate_trips_with_utci.py`, `analyze_walking_vs_utci.py`
- Publication visualization: ~15 final plot scripts
- Core utilities: `enhanced_utci.py`, `salusshadow.py`, etc.

### Plots Breakdown

**Total**: 566 plots (617.5 MB)

**Automated Classification**:
- KEEP: 43 plots (75 MB) - Publication-ready vector formats
- ARCHIVE: 334 plots (453 MB) - Other cities, raster duplicates
- REVIEW: 189 plots (89 MB) - Need manual classification

**By City**:
- NYC: 25 plots
- Seattle: 50 plots
- NYC+Seattle cross-city: Many in "Unknown/Generic" category (conservative classifier)
- State College: 77 plots (archive)
- Global/Multi-City: 136 plots (archive)
- Phoenix: 8 plots (archive)

**Key Publication Plot Directories**:
- `outputs/analysis/ipw_plots/` - IPW diagnostic plots (NYC vs Seattle)
- `outputs/analysis/seasonally_adjusted_plots/` - Seasonal adjustment and bootstrap comparisons
- Both contain cross-city comparisons that are publication-ready

### Documentation Breakdown

**To Archive (~60 files)**:
- Metro/multi-city: ~15 files
- Exploratory analyses: ~20 files (seasonal bias, EMD, curve patterns)
- Technical notes: ~15 files (bug fixes, performance logs)
- Debug files: 1 massive file (67 MB)
- Legacy: ~10 files

**To Keep (~15-20 essential docs)**:
- IPW methodology
- DCWP method documentation
- Seasonal bias correction methods
- UTCI computation methods
- Shadow detection methods
- Data dictionary and sources
- Replication guide
- Computational requirements

---

## Outstanding Questions for You

### Dataset Versions
In `final_run_outputs/`, there are multiple versions for each city:

**NYC**:
- `new-york-city_final_analysis_with_ipw.csv` (115 MB)
- `new-york-city_final_analysis_with_ipw_revised.csv` (105 MB)
- `new-york-city_final_analysis_with_seasonal_and_temp.csv` (119 MB)
- `new-york-city_final_analysis_with_seasonal_no_temp.csv` (119 MB)

**Seattle**:
- Similar set of 4 files

**Question**: Should we keep all versions, or pare down to just the final ones you're using in the paper?
- **If keeping all**: ~5.5 GB
- **If keeping just 2 (revised IPW + seasonal_and_temp)**: ~2.8 GB

**Recommendation**: Keep `ipw_revised` and `seasonal_and_temp` versions, archive the others

### Intermediate Files

**Files**:
- `new-york-city_with_shadow_metrics.csv` (660 MB)
- `seattle_with_shadow_metrics.csv` (472 MB)
- **Total**: 1.1 GB

**Question**: Are these needed, or are they superseded by the final analysis files?
- If redundant: Archive and save 1.1 GB
- If needed for some diagnostic: Keep

### Municipal Deployment Package

**File**: `nyc_seattle_municipal_deployment/` (1.1 GB)

**Question**: Include in main replication package or distribute separately?
- **Include**: Adds 1.1 GB but provides complete standalone tool
- **Separate**: Keep replication package smaller, distribute deployment package as separate artifact

**Recommendation**: Distribute separately (it's already a self-contained package with its own README)

### ViT Training Data

**Question**: Where is the ViT sunny/cloudy classifier training dataset?
- YOLO training data is at `data/yolo_training_dataset/` (195 MB)
- ViT training data location unknown

**Action needed**: Find ViT training images if they should be included for reproducibility

### Plot Format Conversion

**Current**: Mix of PNG (519 plots) and PDF (47 plots)

**Your preference**: Vector only for publication plots

**Question**: Should I:
- A) Keep only existing PDF/SVG plots, archive PNG versions
- B) Regenerate PNG plots as PDFs by re-running visualization scripts
- C) Accept PNG for some plots if they're publication-ready quality

**Recommendation**: Option A for Phase 2 (quick), then Option B for Phase 3 if needed

---

## Deliverables Created

### 1. REPLICATION_PACKAGE_INVENTORY.md
Comprehensive inventory of what stays in the publication repo:
- NYC/Seattle data breakdown with file-by-file listings
- Model inventory
- Expected replication package size: 10-12 GB
- Git-tracked vs git-lfs vs download-links strategy
- Open questions clearly identified

### 2. ARCHIVE_MANIFEST.md
Detailed archive plan with exact commands:
- ~185 GB to archive
- File-by-file listing organized by category
- Rsync commands ready to execute
- Archive directory structure designed
- Verification checklist included

### 3. PLOT_MANIFEST.csv
Automated classification of all 566 plots:
- Columns: path, size_bytes, size_mb, format, city, purpose, recommendation
- Sorted by recommendation then city
- Can be manually reviewed and adjusted
- Generated by `scripts/classify_plots.py` (reusable)

### 4. scripts/classify_plots.py
Reusable Python script that:
- Finds all plots in outputs/
- Classifies by city (NYC, Seattle, Phoenix, etc.)
- Classifies by purpose (Main Results, Methods, Diagnostic, etc.)
- Recommends KEEP/ARCHIVE/REVIEW
- Generates summary statistics
- Outputs CSV manifest

---

## Next Steps (Pending Your Approval)

### Your Review Required

1. **Review REPLICATION_PACKAGE_INVENTORY.md**
   - Are the dataset versions correct?
   - Should we pare down to final versions only?
   - Is intermediate data needed?

2. **Review ARCHIVE_MANIFEST.md**
   - Does the archive organization make sense?
   - Any scripts/data we should keep that I marked for archive?

3. **Review PLOT_MANIFEST.csv**
   - Spot-check the REVIEW category plots (189 files)
   - Confirm archive decisions look correct
   - Identify any misclassifications

4. **Answer Outstanding Questions Above**

### Phase 2: Archive Creation (Ready When You Are)

Once you approve Phase 1:

1. Create archive directory: `sunny_day_svi_archive/`
2. Copy (not move) all data using rsync
3. Generate checksums for large files
4. Verify archive completeness
5. Create archive README and index
6. Update `.gitignore` to exclude archive
7. Test that archived files are accessible

**Estimated Time**: 4-6 hours (mostly copying 185 GB)

### Phase 3: Repository Reorganization

After archive is verified:

1. Create new publication directory structure
2. Move/rename scripts with numerical prefixes
3. Reorganize plots into publication/ subdirectories
4. Extract NYC/Seattle geographic boundaries
5. Update documentation
6. Create replication scripts
7. Test end-to-end replication

**Estimated Time**: 1-2 days

### Phase 4: Cleanup

After reorganization is tested:

1. Remove archived files from main repo
2. Git commit with detailed message
3. Create final replication package
4. Generate package checksums

**Estimated Time**: 4 hours

---

## Summary Statistics

**Current Repository**:
- Size: 195 GB
- Scripts: 204 files
- Plots: 566 files (617.5 MB)
- Documentation: 75+ files (67 MB)
- Cities: 21+ metros analyzed

**Target Publication Package**:
- Size: 10-12 GB (94% reduction)
- Scripts: ~50 production files (75% reduction)
- Plots: ~50-100 publication-ready (90% reduction)
- Documentation: ~20 essential files (73% reduction)
- Cities: 2 (NYC + Seattle)

**Archive**:
- Size: ~185 GB
- Preserved in local subdirectory (not git-tracked)
- Fully documented and indexed
- Accessible for future reference

---

## Risk Mitigation

All Phase 1 work is **read-only analysis**. Nothing has been moved, deleted, or modified (except creating new documentation files). The repository is in exactly the same state as when we started.

Phase 2 will use **copy-first** strategy:
- Archive uses `rsync -av` to copy (not move)
- Original files remain until verification complete
- Checksums verify integrity
- Can abort at any time without data loss

Phase 3 will be tested in separate directory first:
- Create test directory for reorganization
- Verify replication works
- Only then apply to main repo

**Rollback Plan**: Git tag `pre-publication-cleanup` will be created before any destructive operations.

---

## Files Created

1. `/home/kieran/Documents/Python/sunny_day_SVI/REPLICATION_PACKAGE_INVENTORY.md`
2. `/home/kieran/Documents/Python/sunny_day_SVI/ARCHIVE_MANIFEST.md`
3. `/home/kieran/Documents/Python/sunny_day_SVI/PLOT_MANIFEST.csv`
4. `/home/kieran/Documents/Python/sunny_day_SVI/scripts/classify_plots.py`
5. `/home/kieran/Documents/Python/sunny_day_SVI/PHASE_1_SUMMARY.md` (this file)

All files are ready for your review.

---

## What I Need From You, Dude

1. **Read through the three main documents** (inventory, archive manifest, this summary)
2. **Answer the outstanding questions** (dataset versions, intermediate files, deployment package, ViT training data, plot formats)
3. **Spot-check PLOT_MANIFEST.csv** for any obvious misclassifications
4. **Give me the go-ahead for Phase 2** or let me know what needs adjustment

I'm ready to proceed when you are. This is a big cleanup, but we have a solid plan now.
