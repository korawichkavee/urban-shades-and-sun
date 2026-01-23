# Cleanup and Consolidation TODO

## Overview

This document identifies files/scripts that can be merged, archived, or removed to streamline the project.

**Status**: Generated on 2026-01-21 based on current project state

---

## Root Level Files

### Python Scripts

#### Keep (Active Development)
- ✅ `enhanced_utci.py` - Core UTCI data collection module
- ✅ `quickhotpoint2.py` - UTCI calculation utilities
- ✅ `batch_add_enhanced_utci_optimized.py` - Primary batch processor (RECOMMENDED)

#### Consider Archiving
- 🔶 `batch_add_utci.py` - **ACTION**: Archive or remove
  - **Reason**: Superseded by `batch_add_enhanced_utci.py` (lacks multi-day context)
  - **Dependencies**: Uses `quickhotpoint2.py`
  - **Recommendation**: Keep only if simple UTCI (without prior/next day) is needed

- 🔶 `batch_add_enhanced_utci.py` - **ACTION**: Archive
  - **Reason**: Superseded by optimized version (10x slower)
  - **Dependencies**: Uses `enhanced_utci.py`
  - **Recommendation**: Keep for reference but use `_optimized.py` version

#### Test/Development Scripts
- 🔶 `test_phoenix_fetch.py` - **ACTION**: Move to `tests/` or archive
  - **Reason**: Appears to be a Phoenix-specific test
  - **Recommendation**: Move to `tests/test_phoenix_fetch.py` or document as temporary

---

### Markdown Documentation

#### Keep at Root
- ✅ `README.md` - Main project README
- ✅ `PROJECT_STRUCTURE.md` - Directory layout guide

#### Move to docs/
- 🔶 `AGENTS.md` - **ACTION**: Already in `docs/`, remove root copy
  - **Note**: Appears to be duplicate - verify content is identical

- 🔶 `WORKFLOW_SUMMARY.md` - **ACTION**: Move to `docs/WORKFLOW_SUMMARY.md`
  - **Reason**: Better organization with other documentation

- 🔶 `UTCI_FIX_SUMMARY.md` - **ACTION**: Move to `docs/UTCI_FIX_SUMMARY.md`
  - **Reason**: Historical documentation, belongs in docs

- 🔶 `VISUALIZATION_IMPROVEMENTS.md` - **ACTION**: Move to `docs/VISUALIZATION_IMPROVEMENTS.md`
  - **Reason**: Implementation notes, belongs in docs

#### Phoenix-Specific Docs (Consider Archiving)
- 🔶 `PHOENIX_QUICKSTART.md` - **ACTION**: Move to `docs/phoenix/` or archive
  - **Reason**: Phoenix-specific, may not be relevant to main workflow
  - **Recommendation**: Create `docs/phoenix/` subdirectory if Phoenix is ongoing work

- 🔶 `PHOENIX_IMPLEMENTATION_SUMMARY.md` - **ACTION**: Move to `docs/phoenix/` or archive
  - **Reason**: Implementation notes for Phoenix-specific work

- 🔶 `COMPLETE_PACKAGE_GUIDE.md` - **ACTION**: Move to `docs/deployment/` or `docs/phoenix/`
  - **Reason**: Deployment-specific guide

---

## Git Deleted Files (52 files marked for deletion)

These files are marked as deleted in git but not committed:

### Notebooks (Should be in `notebooks/` directory)
- ✅ Already moved: `02_metadata.ipynb`, `city_pop_histogram.ipynb`, `df_aggregator.ipynb`
- **ACTION**: `git add -u` to confirm deletions

### Test Images/Directories
- `SAM2/test/`, `SAM2/test2/`, `YOLO/test*/` directories with test images
- **ACTION**: `git add -u` to confirm deletions (test images not needed in repo)

### Old Data Directories
- `city7sample/`, `city_data/`, `cache/` - Raw data in old locations
- **ACTION**: `git add -u` to confirm deletions (moved to `data/` structure)

### Legacy Scripts (Already Moved)
- `download_jpegs.py`, `download_kv_points.py`, `download_mly_points.py`, etc.
- **ACTION**: `git add -u` to confirm deletions (now in `scripts/data_collection/`)

### Temporary Files
- `finetuning_yolo_test_imgs/project-8/` - Training artifacts
- **ACTION**: `git add -u` to confirm deletions

**Recommendation**: Run `git add -u` to stage all deletions, then commit with message:
```bash
git add -u
git commit -m "Clean up: Confirm deletion of moved and obsolete files"
```

---

## Scripts Directory

### Potential Duplicates/Overlaps

#### Data Collection (`scripts/data_collection/`)

- 🔶 `download_jpegs.py` vs `download_jpegs_mapillary.py` vs `download_jpegs_kartaview.py`
  - **ACTION**: Document differences or merge into single script with source parameter
  - **Recommendation**: Keep separate if APIs differ significantly, add ABOUTME comments

- 🔶 `nas_download_svi.py` - **ACTION**: Verify if still used
  - **Reason**: NAS-specific, may not be relevant without NAS mount
  - **Recommendation**: Archive if NAS workflow not active

- 🔶 `raw_download.py` - **ACTION**: Archive or document
  - **Reason**: Marked as "legacy" in docs
  - **Recommendation**: Archive to `archive/legacy/` if superseded

#### Processing (`scripts/processing/`)

- 🔶 `add_weather_data.py` vs `add_weather_overnight.py` vs `add_weather_to_walkable.py`
  - **ACTION**: Document differences clearly
  - **Differences**:
    - `add_weather_data.py` - Basic weather enrichment
    - `add_weather_overnight.py` - Tmux-compatible with checkpointing
    - `add_weather_to_walkable.py` - Combined walkability + weather
  - **Recommendation**: Keep all but add clear ABOUTME comments

- 🔶 `time_metadata_enrichment.py` - **ACTION**: Check if superseded by `enrich_hot_cities_datetime.py`
  - **Recommendation**: Archive if duplicate functionality

- 🔶 `process_all_cities_osm.py` vs `process_hot_cities_osm.py` vs `process_walkable_cities.py`
  - **ACTION**: Document when to use each
  - **Recommendation**: Keep separate but document use cases in ABOUTME

#### Pipelines (`scripts/pipelines/`)

- 🔶 `sunny_shade_pipeline.py` vs `sunny_shade_pipeline_ondemand.py`
  - **Differences**: Pre-downloaded vs on-demand image fetching
  - **Recommendation**: Keep both, clearly documented in 06_PIPELINES.md ✅

- 🔶 `prelim_filtering_tmux.py` - **ACTION**: Move to `scripts/processing/` if primarily a processing step?
  - **Recommendation**: Keep in pipelines if it orchestrates multiple steps

---

## Notebooks Directory

### Notebooks to Archive

- 🔶 `zen_svi_test.ipynb` - **ACTION**: Archive
  - **Reason**: Marked as "experimental, not used in main pipeline"
  - **Recommendation**: Move to `archive/experimental_notebooks/`

### Notebooks Needing Organization

Most notebooks are properly documented in `docs/07_NOTEBOOKS.md` ✅

---

## Tests Directory

Currently has 4 test files - all appear to be active and relevant ✅

**Recommendation**: Keep all tests as-is

---

## Deployment Directory

Review deployment scripts for Phoenix-specific vs general usage:

- 🔶 Check if Phoenix-specific scripts should be in `deployment/phoenix/` subdirectory
- 🔶 Separate general deployment scripts from city-specific ones

---

## Action Plan

### Priority 1: Quick Wins (Do First)

1. **Commit Git Deletions** (5 minutes)
   ```bash
   git add -u
   git commit -m "Clean up: Confirm deletion of moved files from reorganization"
   ```

2. **Move Root-Level Documentation to docs/** (10 minutes)
   ```bash
   # Move files
   mv WORKFLOW_SUMMARY.md docs/
   mv UTCI_FIX_SUMMARY.md docs/
   mv VISUALIZATION_IMPROVEMENTS.md docs/

   # Create Phoenix subdirectory if keeping Phoenix work
   mkdir -p docs/phoenix
   mv PHOENIX_*.md docs/phoenix/
   mv COMPLETE_PACKAGE_GUIDE.md docs/phoenix/

   # Remove duplicate AGENTS.md from root if identical to docs/AGENTS.md
   diff AGENTS.md docs/AGENTS.md && rm AGENTS.md
   ```

3. **Move Test Script** (2 minutes)
   ```bash
   mv test_phoenix_fetch.py tests/
   ```

### Priority 2: Archive Legacy Scripts (Do When Time Permits)

1. **Create Archive Structure**
   ```bash
   mkdir -p archive/legacy_scripts
   mkdir -p archive/superseded
   mkdir -p archive/experimental_notebooks
   ```

2. **Archive Superseded UTCI Scripts**
   ```bash
   # Keep _optimized version, archive others
   git mv batch_add_utci.py archive/superseded/
   git mv batch_add_enhanced_utci.py archive/superseded/
   ```

3. **Archive Experimental Notebooks**
   ```bash
   git mv notebooks/zen_svi_test.ipynb archive/experimental_notebooks/
   ```

4. **Archive Legacy Download Script**
   ```bash
   git mv scripts/data_collection/raw_download.py archive/legacy_scripts/
   ```

### Priority 3: Documentation Improvements (Ongoing)

1. **Add ABOUTME comments to ambiguous scripts**
   - Clarify differences between similar download/processing scripts
   - Document when to use each variant

2. **Update README.md if needed**
   - Reflect any major file movements
   - Update quick start commands if paths changed

3. **Create archive/README.md**
   - Document what's in archive and why
   - Provide context for historical scripts

### Priority 4: Consider Merging (Future Work)

These could potentially be merged but require careful analysis:

1. **Download Scripts**
   - Merge `download_jpegs_*.py` into single script with `--source` flag?
   - Requires API compatibility check

2. **Weather Processing Scripts**
   - Could have single script with `--mode` flag (basic/overnight/walkable)?
   - May reduce code duplication

3. **OSM Processing Scripts**
   - Could consolidate into single script with city type parameter?

**Recommendation**: Only merge if it genuinely simplifies maintenance. Having separate scripts is fine if they serve distinct purposes.

---

## Summary Statistics

**Files to Move**:
- 6 markdown files (root → docs/)
- 1 Python test file (root → tests/)

**Files to Archive**:
- 2-3 Python scripts (superseded UTCI batch processors)
- 1 notebook (experimental)
- 1-2 legacy download scripts

**Git Deletions to Confirm**:
- 52 files (already moved/obsolete)

**Files to Keep As-Is**:
- Core UTCI scripts (3 files)
- All scripts in `scripts/` directory (documented)
- Most notebooks (active)
- All tests
- Documentation in `docs/` (newly created) ✅

---

## Notes

### Why Keep Multiple Similar Scripts?

It's often better to keep separate scripts rather than merge if:
- They serve different use cases (basic vs advanced)
- They have different performance characteristics (fast vs thorough)
- They target different environments (local vs tmux vs NAS)
- Merging would add complexity (too many flags/options)

### When to Archive vs Delete?

**Archive** (move to `archive/` directory):
- Scripts that may be referenced for historical context
- Experimental work that shows what was tried
- Legacy implementations that document evolution

**Delete** (remove entirely):
- True duplicates with no differences
- Test files/temporary files
- Files that serve no historical purpose

**Commit Deletion in Git** (git add -u):
- Files that were already moved in reorganization
- Confirms previous reorganization work

---

## Validation Checklist

Before finalizing cleanup:

- [ ] Run tests to ensure nothing broke: `pytest tests/`
- [ ] Verify active scripts still work:
  - [ ] `python batch_add_enhanced_utci_optimized.py` (on small sample)
  - [ ] `python scripts/visualization/visualize_shade_ratios.py`
  - [ ] `python scripts/pipelines/hot_cities_full_pipeline.py --help`
- [ ] Check that documentation links are correct
- [ ] Ensure no hard-coded paths reference moved files
- [ ] Review git status to confirm intended changes
- [ ] Create backup before major deletions

---

## Future Maintenance

### Regular Cleanup Tasks (Every 3-6 months)

1. Review `logs/` directory - archive old logs
2. Check `cache/` directory - clear expired cache
3. Review `outputs/plots/` - archive old plot versions
4. Scan for new test/temporary files in root
5. Update documentation for new scripts
6. Review archive directory - remove truly obsolete files

### Keep Project Clean

- Add new scripts to appropriate `scripts/` subdirectory
- Add documentation when creating new features
- Use descriptive names and ABOUTME comments
- Test scripts before committing
- Keep root directory minimal

---

## Questions for Dude

Before proceeding with cleanup:

1. **Phoenix Work**: Is the Phoenix-specific work ongoing? Should we create `docs/phoenix/` or archive it entirely?

2. **NAS Workflow**: Is `nas_download_svi.py` still relevant? Archive if NAS not in use?

3. **Legacy Scripts**: Do you want to keep `batch_add_utci.py` and `batch_add_enhanced_utci.py` for reference, or archive them since the optimized version exists?

4. **Test Scripts**: Is `test_phoenix_fetch.py` a temporary test or should it stay as a permanent test case?

5. **Git Deletions**: Should we commit the 52 deleted files from the previous reorganization?

6. **Archive Strategy**: Prefer keeping superseded scripts in `archive/` or removing them entirely from repo?
