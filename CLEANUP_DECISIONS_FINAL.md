# Final Cleanup Decisions

**Date**: 2026-04-21
**Status**: Approved by Dude - Ready for Phase 2 Execution

---

## Dude's Decisions

### 1. Dataset Versions: Keep Final 2 Only ✓

**Decision**: Keep only the final/revised versions per city

**NYC - KEEP**:
- `new-york-city_final_analysis_with_ipw_revised.csv` (105 MB)
- `new-york-city_final_analysis_with_seasonal_and_temp.csv` (119 MB)
- **Subtotal**: 224 MB

**NYC - ARCHIVE**:
- `new-york-city_final_analysis_with_ipw.csv` (115 MB) - superseded by revised
- `new-york-city_final_analysis_with_seasonal_no_temp.csv` (119 MB) - we want the temp version
- `new-york-city_shadow_annotated.csv` (460 MB) - intermediate
- `new-york-city_with_shadow_and_utci.csv` (993 MB) - intermediate
- `new-york-city_with_shadow_metrics.csv` (660 MB) - intermediate
- **Subtotal**: 2.3 GB to archive

**Seattle - KEEP**:
- `seattle_final_analysis_with_ipw_revised.csv` (319 MB)
- `seattle_final_analysis_with_seasonal_and_temp.csv` (361 MB)
- **Subtotal**: 680 MB

**Seattle - ARCHIVE**:
- `seattle_final_analysis_with_ipw.csv` (347 MB) - superseded by revised
- `seattle_final_analysis_with_seasonal_no_temp.csv` (361 MB) - we want the temp version
- `seattle_shadow_annotated.csv` (323 MB) - intermediate
- `seattle_with_shadow_and_utci.csv` (702 MB) - intermediate
- `seattle_with_shadow_metrics.csv` (472 MB) - intermediate
- **Subtotal**: 2.2 GB to archive

**Impact**:
- **KEEP**: 904 MB (vs original 5.5 GB)
- **ARCHIVE**: 4.5 GB additional savings
- **Total in final_run_outputs/**: Keep 904 MB + summary files

### 2. Intermediate Files: Archive ✓

**Decision**: Archive all intermediate shadow/UTCI files

**Files to Archive**:
- All `*_shadow_annotated.csv` files
- All `*_with_shadow_and_utci.csv` files
- All `*_with_shadow_metrics.csv` files
- Checkpoint JSON files

**Justification**: Final analysis files contain all needed data; intermediates can be regenerated if needed

**Savings**: 4.5 GB (already counted above)

### 3. Deployment Package: Keep ✓

**Decision**: Keep `nyc_seattle_municipal_deployment/` in publication repo for now

**Size**: 1.1 GB (633 MB compressed)

**Justification**:
- Self-contained standalone package
- Provides complete replication pathway
- Well-documented with own README
- Can be distributed with publication

**Future**: May move to separate distribution later, but keep for now

### 4. ViT Training Data: Keep ✓

**Decision**: Keep ViT sunny/not_sunny classifier training dataset

**Location (Current)**: `data/raw/city7sample/images_to_label/batch2/labeled/data/`
**Location (New)**: Will extract to `data/vit_training_dataset/`

**Contents**:
- `sunny/` - 843 images
- `not_sunny/` - 577 images
- Total: 1,420 training images
- Size: 706 MB (excluding the 262 MB sunny.zip duplicate)

**Action Required**:
1. Create `data/vit_training_dataset/`
2. Copy sunny/ and not_sunny/ folders from city7sample
3. Archive the rest of city7sample (99+ GB)

**Training Script**: `scripts/ml/binary_image_classification.py` (will need path update)

### 5. Plot Formats: Accept Existing Mix ✓

**Decision**: Keep existing mix of PDF (47) and PNG (519) for now

**No action**: Don't regenerate plots as PDFs in this phase

**Future**: Can regenerate specific plots as PDFs if needed for publication

**Classification from PLOT_MANIFEST.csv**:
- KEEP: 43 plots (75 MB) - publication-ready
- ARCHIVE: 334 plots (453 MB) - other cities, duplicates
- REVIEW: 189 plots (89 MB) - manual review later

---

## Updated Repository Size Targets

### Original Assessment:
- Current: 195 GB
- Target: 10-12 GB
- Archive: ~185 GB

### With Dude's Decisions:
- Current: 195 GB
- **Target: 7-9 GB** (better than expected!)
- **Archive: ~188 GB**

### Size Breakdown (Publication Package):

**Data (~2.5 GB)**:
- Final datasets (NYC/Seattle): **904 MB** (down from 5.5 GB)
- NYC/Seattle mobility surveys: 185 MB
- NYC/Seattle trips with UTCI: 98 MB
- YOLO training dataset: 195 MB
- **ViT training dataset: 706 MB** (new)
- Geographic boundaries: <10 MB
- Summary/metadata files: <10 MB

**Models (438 MB)**:
- ViT binary classifier: 328 MB
- YOLO best model: 110 MB

**Deployment Package (1.1 GB)**:
- nyc_seattle_municipal_deployment/: 1.1 GB (staying for now)

**Outputs (~100-150 MB)**:
- Publication plots: ~75 MB
- Analysis tables: <10 MB
- Model evaluation: ~50 MB

**Scripts + Docs (~50 MB)**:
- Production scripts: ~20 MB
- Documentation: ~10 MB
- Tests: ~5 MB
- Config: <5 MB

**Total**: ~4.2 GB core + 1.1 GB deployment = **~5.3 GB** (even better!)

### Additional Archive Savings:

**From final_run_outputs/** (new):
- Intermediate datasets: 4.5 GB

**From data/raw/** (updated):
- Raw SVI imagery: 129 GB total
  - Extract ViT training: 706 MB to keep
  - Archive remaining: ~128.3 GB

**Total Archive**: ~188 GB

---

## Action Items for Phase 2

### Critical Extraction Before Archive

**ViT Training Data**:
```bash
# Create new location
mkdir -p data/vit_training_dataset

# Copy training images (NOT the zip file)
rsync -av data/raw/city7sample/images_to_label/batch2/labeled/data/sunny/ \
    data/vit_training_dataset/sunny/
rsync -av data/raw/city7sample/images_to_label/batch2/labeled/data/not_sunny/ \
    data/vit_training_dataset/not_sunny/

# Verify
du -sh data/vit_training_dataset/
ls data/vit_training_dataset/sunny/ | wc -l    # Should be 843
ls data/vit_training_dataset/not_sunny/ | wc -l # Should be 577
```

**After extraction, archive entire data/raw/**:
```bash
rsync -av data/raw/ sunny_day_svi_archive/data/raw/
```

### Updated Archive Plan

**final_run_outputs/ Archive**:
```bash
# Archive intermediate/superseded files
rsync -av final_run_outputs/new-york-city/new-york-city_final_analysis_with_ipw.csv \
    sunny_day_svi_archive/final_run_outputs/new-york-city/
rsync -av final_run_outputs/new-york-city/new-york-city_final_analysis_with_seasonal_no_temp.csv \
    sunny_day_svi_archive/final_run_outputs/new-york-city/
rsync -av final_run_outputs/new-york-city/new-york-city_shadow_annotated.csv \
    sunny_day_svi_archive/final_run_outputs/new-york-city/
rsync -av final_run_outputs/new-york-city/new-york-city_with_shadow_and_utci.csv \
    sunny_day_svi_archive/final_run_outputs/new-york-city/
rsync -av final_run_outputs/new-york-city/new-york-city_with_shadow_metrics.csv \
    sunny_day_svi_archive/final_run_outputs/new-york-city/
rsync -av final_run_outputs/new-york-city/*.json \
    sunny_day_svi_archive/final_run_outputs/new-york-city/

# Same for Seattle
rsync -av final_run_outputs/seattle/seattle_final_analysis_with_ipw.csv \
    sunny_day_svi_archive/final_run_outputs/seattle/
rsync -av final_run_outputs/seattle/seattle_final_analysis_with_seasonal_no_temp.csv \
    sunny_day_svi_archive/final_run_outputs/seattle/
rsync -av final_run_outputs/seattle/seattle_shadow_annotated.csv \
    sunny_day_svi_archive/final_run_outputs/seattle/
rsync -av final_run_outputs/seattle/seattle_with_shadow_and_utci.csv \
    sunny_day_svi_archive/final_run_outputs/seattle/
rsync -av final_run_outputs/seattle/seattle_with_shadow_metrics.csv \
    sunny_day_svi_archive/final_run_outputs/seattle/
rsync -av final_run_outputs/seattle/*.json \
    sunny_day_svi_archive/final_run_outputs/seattle/
```

### Script Updates Required

**ViT Training Script**:
- File: `scripts/ml/binary_image_classification.py`
- Line 22: Update path from hardcoded to:
  ```python
  dataset = ImageFolder(ROOT / "data/vit_training_dataset", transform=transform)
  ```

---

## Final Publication Package Structure

```
sunny_day_svi/                                 # ~5.3 GB total
├── data/
│   ├── final_datasets/                        # 904 MB (final analyses)
│   │   ├── nyc_final_analysis_with_ipw_revised.csv
│   │   ├── nyc_final_analysis_with_seasonal_and_temp.csv
│   │   ├── seattle_final_analysis_with_ipw_revised.csv
│   │   └── seattle_final_analysis_with_seasonal_and_temp.csv
│   ├── mobility_surveys/                      # 185 MB (raw surveys)
│   │   ├── nyc/
│   │   └── seattle/
│   ├── analysis/                              # 98 MB (UTCI-annotated trips)
│   │   ├── nyc_trips_with_utci.csv
│   │   └── seattle_trips_with_utci.csv
│   ├── yolo_training_dataset/                 # 195 MB (YOLO training)
│   ├── vit_training_dataset/                  # 706 MB (ViT training)
│   │   ├── sunny/              # 843 images
│   │   └── not_sunny/          # 577 images
│   └── geographic/                            # <10 MB (boundaries)
│
├── models/                                    # 438 MB
│   ├── vit_binary.pth                         # 328 MB
│   └── yolo_best.pt                           # 110 MB
│
├── outputs/
│   ├── publication/                           # ~75 MB (plots)
│   ├── tables/                                # <10 MB
│   └── model_evaluation/                      # ~50 MB
│
├── scripts/                                   # ~40-50 production scripts
│   ├── processing/
│   ├── analysis/
│   ├── visualization/
│   ├── ml/
│   └── utils/
│
├── docs/                                      # ~15-20 essential docs
│
├── nyc_seattle_municipal_deployment/          # 1.1 GB
│
└── tests/
```

**Archive** (git-ignored subdirectory):
```
sunny_day_svi_archive/                         # ~188 GB
├── data/
│   ├── raw/                                   # 128.3 GB (after extracting ViT data)
│   ├── transit_surveys/                       # 27 GB
│   ├── metro_*/                               # ~30 GB (6 directories)
│   └── ...
├── final_run_outputs/
│   ├── intermediate_datasets/                 # 4.5 GB
│   └── checkpoints/
├── scripts/                                   # ~100+ exploratory scripts
├── outputs/                                   # ~450 MB archived plots
└── docs/                                      # ~60 archived docs
```

---

## Size Verification

**Expected Publication Package**: ~5.3 GB
- Data: 2.5 GB
- Models: 438 MB
- Deployment: 1.1 GB
- Outputs: 150 MB
- Scripts/Docs: 50 MB
- **Total**: ~4.2 GB + deployment 1.1 GB = **5.3 GB**

**Expected Archive**: ~188 GB
- Raw SVI (minus ViT data): 128.3 GB
- Transit surveys: 27 GB
- Metro SVI: 30 GB
- Intermediate datasets: 4.5 GB
- Other cities data: 1.5 GB
- Archived plots: 450 MB
- **Total**: ~188 GB

**Original**: 195 GB
**Final**: 5.3 GB + 188 GB archived = 193.3 GB (accounts for extraction duplication)

**Reduction**: 97% reduction in git-tracked files (195 GB → 5.3 GB)

---

## Phase 2 Execution Checklist

- [ ] Create `data/vit_training_dataset/` directory
- [ ] Extract ViT training images from city7sample
- [ ] Verify ViT extraction (1,420 images, 706 MB)
- [ ] Update `scripts/ml/binary_image_classification.py` path
- [ ] Create archive directory structure
- [ ] Archive data/raw/ (128.3 GB after extraction)
- [ ] Archive data/transit_surveys/ (27 GB)
- [ ] Archive data/metro_*/ directories (~30 GB)
- [ ] Archive final_run_outputs/ intermediates (4.5 GB)
- [ ] Archive other cities data (1.5 GB)
- [ ] Archive scripts (~100 files)
- [ ] Archive plots (334 files, 453 MB)
- [ ] Archive docs (~60 files)
- [ ] Generate checksums for large files
- [ ] Create archive README and index
- [ ] Update .gitignore to exclude archive/
- [ ] Verify archive completeness
- [ ] Test that publication package works

**Ready to proceed to Phase 2?**

---

## Document Status

- **Created**: 2026-04-21
- **Approved By**: Dude
- **Status**: Ready for Phase 2 Execution
- **Next**: Execute archive creation with these exact specifications
