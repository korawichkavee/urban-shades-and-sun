# Phase 2 Status Report

**Date**: 2026-04-21
**Status**: PAUSED - Memory concerns
**Action**: Do NOT run continue_archive.sh without checking disk space

---

## What's Been Completed ✓

### 1. ViT Training Data Extracted (444 MB)
- **Location**: `data/vit_training_dataset/`
- **Contents**: 1,420 images (843 sunny + 577 not_sunny)
- **Script updated**: `scripts/ml/binary_image_classification.py` now uses correct path
- **Status**: ✅ COMPLETE

### 2. Archive Directory Created
- **Location**: `sunny_day_svi_archive/`
- **Current size**: 53 GB
- **Status**: ✅ Created

### 3. Data Archived (53 GB total)

#### data/raw/ (24 GB archived)
- **Original size**: 129 GB
- **Archived so far**: 24 GB
- **Status**: ⚠️ INCOMPLETE (only 19% complete)
- **Action needed**: Verify if we need ALL raw data or can be selective

#### data/transit_surveys/ (27 GB)
- **Original size**: 27 GB
- **Archived**: 27 GB
- **Status**: ✅ COMPLETE

#### final_run_outputs/new-york-city/ (2.3 GB)
Archived intermediate files:
- `new-york-city_final_analysis_with_ipw.csv` (115 MB)
- `new-york-city_final_analysis_with_seasonal_no_temp.csv` (119 MB)
- `new-york-city_shadow_annotated.csv` (460 MB)
- `new-york-city_with_shadow_and_utci.csv` (993 MB)
- `new-york-city_with_shadow_metrics.csv` (660 MB)
- `new-york-city_shadow_checkpoint.json` (116 KB)
- **Status**: ✅ COMPLETE

---

## What Remains (NOT YET DONE)

### Critical Data (Need Decision)

**data/raw/ remaining (~105 GB)**
- Currently only 24 GB / 129 GB archived
- **Question**: Do we need ALL raw imagery, or can we skip it entirely?
- **Recommendation**: SKIP - raw imagery can be re-downloaded from Mapillary if needed
- **Savings**: 105 GB if we stop the archive here

**final_run_outputs/seattle/ intermediates (~2.2 GB)**
- Not yet archived (some files may not exist based on errors encountered)
- **Action**: Manually check what Seattle intermediate files exist and archive selectively

### Other Data (~30 GB)
- `data/metro_commute_svi/` (23 GB)
- `data/metro_cities_svi/` (4.3 GB)
- `data/metro_cities_svi_test/` (6.7 GB)
- `data/metro_cities_svi_commute/` (1.9 GB)
- `data/metro_commute_svi_with_shadow/` (288 MB)
- `data/metro_commute_svi_with_utci/` (219 MB)
- **Status**: NOT ARCHIVED
- **Priority**: Low - can archive later if disk space allows

### Small Items
- State College data (97 MB)
- Boston/DC mobility surveys (38 MB)
- Multi-city results (137 MB)
- Cache (250 MB)
- **Status**: NOT ARCHIVED
- **Priority**: Medium - small enough to do manually

### Scripts (~100 files, <100 MB total)
- Phoenix scripts (5 files)
- State College scripts (20+ files)
- Metro cities scripts (15+ files)
- OT-SVI module (29 files)
- Exploratory scripts (30+ files)
- **Status**: NOT ARCHIVED
- **Action**: Use continue_archive.sh script (it has the logic) OR do manually

### Plots (334 files, ~450 MB)
- Based on PLOT_MANIFEST.csv classifications
- **Status**: NOT ARCHIVED
- **Priority**: Medium

### Documentation (~60 files, ~70 MB)
- Metro, exploratory, technical docs
- **Status**: NOT ARCHIVED
- **Priority**: Low

---

## Disk Space Analysis

### Current Situation
- **Repository**: 195 GB total
- **Archive created**: 53 GB (mostly transit_surveys + partial raw)
- **Publication target**: ~5-10 GB

### Problem
- **data/raw/** is 129 GB and only 19% archived (24 GB)
- Completing data/raw/ archive would require **+105 GB disk space**
- **Total archive target was ~185 GB**, which may exceed available disk space

### Recommended Strategy: SELECTIVE ARCHIVAL

**Instead of archiving everything, DELETE non-essential large directories:**

1. **data/raw/** (129 GB) → **DELETE** (can re-download from Mapillary if needed)
   - Keep only: ViT training data (already extracted to `data/vit_training_dataset/`)
   - Savings: 129 GB

2. **data/transit_surveys/** (27 GB) → **ALREADY ARCHIVED** ✓
   - Safe to delete from main repo after verification

3. **data/metro_*** (30+ GB) → **DELETE** (exploratory, not publication)
   - Savings: 30 GB

4. **final_run_outputs/ intermediates** (4.5 GB) → **ARCHIVE** (small enough)
   - Keep: Final 2 versions per city (904 MB)
   - Archive: Intermediate files (4.5 GB)
   - Then delete intermediates

**Total savings: ~160 GB deleted, ~30 GB archived**

This avoids needing 185 GB of extra disk space for a complete archive.

---

## Updated Approach: Delete > Archive

### Phase 2A: Selective Archive (What We Need)

**Archive ONLY**:
1. ✅ transit_surveys/ (27 GB) - DONE
2. ✅ NYC intermediates (2.3 GB) - DONE
3. ⚠️ Seattle intermediates (2.2 GB) - PARTIAL
4. Scripts (~100 MB) - scripts are small, can archive
5. Important documentation (~10 MB) - small, can archive
6. Selected plots from PLOT_MANIFEST (~200 MB of 450 MB)

**Total to archive**: ~32 GB (we have ~53 GB already, so we're good)

### Phase 2B: Direct Deletion (What We Don't Need)

**DELETE without archiving**:
1. data/raw/ (129 GB) - EXCEPT keep what's already partially archived
2. data/metro_* (30 GB total)
3. data/cache/ (250 MB)
4. data/multi_city_results/ (137 MB)
5. Remaining plots not marked for publication (~250 MB)

**Total to delete: ~160 GB**

---

## Action Plan for You, Dude

### Option 1: Conservative (Verify then Delete)

1. **Verify transit_surveys archive is complete**:
   ```bash
   du -sh data/transit_surveys
   du -sh sunny_day_svi_archive/data/transit_surveys
   # Should both be ~27 GB
   ```

2. **Verify NYC intermediates archived**:
   ```bash
   ls -lh sunny_day_svi_archive/final_run_outputs/new-york-city/
   # Should see all 6 files
   ```

3. **Stop the data/raw archive** (already stopped, but clean up partial):
   ```bash
   # Kill any remaining rsync
   pkill -f "rsync.*data/raw"

   # Decision: Keep the 24 GB partial archive or delete it?
   # Recommendation: DELETE - we don't need raw imagery
   rm -rf sunny_day_svi_archive/data/raw
   ```

4. **Archive Seattle intermediates manually** (check what exists first):
   ```bash
   ls -lh final_run_outputs/seattle/
   # Then archive what exists
   ```

5. **Skip archiving remaining large data**, just delete:
   ```bash
   # After backing up what we have, delete large dirs
   rm -rf data/metro_commute_svi
   rm -rf data/metro_cities_svi
   rm -rf data/metro_cities_svi_test
   # etc.
   ```

### Option 2: Aggressive (Delete Now)

Just proceed with cleanup based on CLEANUP_DECISIONS_FINAL.md:

1. Keep final 2 datasets per city (904 MB)
2. Keep ViT training (444 MB)
3. Keep YOLO training (195 MB)
4. Keep mobility surveys (185 MB)
5. Keep deployment package (1.1 GB)

Delete everything else in data/ except geographic boundaries.

---

## Scripts Created

### continue_archive.sh
- **Location**: `scripts/continue_archive.sh`
- **Purpose**: Complete the archive process
- **WARNING**: Will try to archive ~155 GB more data
- **Recommendation**: DO NOT RUN without modifying to skip data/raw and metro_*

### monitor_archive.sh
- **Location**: `scripts/monitor_archive.sh`
- **Purpose**: Monitor archive progress
- **Status**: Can use to check current state

---

## Immediate Next Steps

**Before doing anything else**:

1. **Check available disk space**:
   ```bash
   df -h /home/kieran/Documents/Python/sunny_day_SVI
   ```

2. **Decide on strategy**:
   - **If disk space > 200 GB available**: Can continue archiving
   - **If disk space < 200 GB available**: Use selective deletion strategy

3. **Review what's in the 24 GB partial data/raw/ archive**:
   ```bash
   ls -lh sunny_day_svi_archive/data/raw/
   ```
   Decide if we keep it or delete it.

4. **Manually archive Seattle intermediates** (small, safe):
   ```bash
   cd /home/kieran/Documents/Python/sunny_day_SVI
   ls -lh final_run_outputs/seattle/
   # Copy the intermediate files that exist
   ```

---

## Summary

**Completed**:
- ✅ ViT training data extracted (444 MB)
- ✅ Archive directory created
- ✅ transit_surveys archived (27 GB)
- ✅ NYC intermediates archived (2.3 GB)
- ✅ Scripts created for continuation

**Status**: 53 GB in archive (target was ~185 GB, but that may be too much)

**Recommendation**:
- STOP full archive approach
- Keep the 53 GB we have (transit_surveys + NYC intermediates)
- DELETE large directories instead of archiving them
- This gets us to the 5-10 GB target without needing 185+ GB of archive space

**Next**: Check disk space and choose strategy above.
