# Archive Manifest

**Purpose**: Comprehensive listing of all files and directories to be moved to `/sunny_day_svi_archive/` (git-ignored).

**Created**: 2026-04-21
**Status**: Phase 1 - Planning
**Total Archive Size**: ~185 GB (from 195 GB total repository)

---

## Archive Strategy

**Archive Location**: `/home/kieran/Documents/Python/sunny_day_SVI/sunny_day_svi_archive/`
- Will be added to `.gitignore`
- Remains accessible on local machine
- Separate backup recommended (external drive)

**Archive Method**:
- COPY first (using `rsync -av`), never move
- Verify archive completeness with checksums
- Only remove from main repo after verification
- Document everything in archive README

---

## Data to Archive (~185 GB)

### Raw SVI Imagery (129 GB)

**Directory**: `data/raw/`

**Contents**: Raw street view imagery downloads for all cities

**Justification**:
- Replication uses processed CSVs with shadow annotations
- Raw imagery can be re-downloaded from Mapillary if needed
- Saves 129 GB from git tracking

**Action**:
```bash
rsync -av data/raw/ sunny_day_svi_archive/data/raw/
```

**Verification**: Check total size matches 129 GB

---

### Transit Survey Data (27 GB)

**Directory**: `data/transit_surveys/`

**Subdirectories to Archive**:
- `metro/` - All metro city surveys (100+ cities, 1968-2008)
- `NHTS/` - National Household Travel Survey
- `documentation/` - Survey documentation
- `nextgen_addons/` - Additional data sources
- `processed/` - Merged/standardized surveys (all cities combined)

**Justification**:
- Final analysis uses direct downloads from `final_cities/NYC/` and `final_cities/seattle/`
- `outputs/analysis/nyc_trips_with_utci.csv` (40 MB) already extracted
- `outputs/analysis/seattle_trips_with_utci.csv` (58 MB) already extracted
- Metro surveys are historical data (1968-2008), not current mobility surveys
- Can be regenerated from source if needed

**NYC/Seattle Note**:
- Metro surveys contain old data: `new-york-1998`, `seattle-1989` through `seattle-2002`
- **NOT** the same as final analysis data (NYC 2022, Seattle recent)
- Final mobility surveys are in `final_cities/` and will be kept

**Action**:
```bash
rsync -av data/transit_surveys/ sunny_day_svi_archive/data/transit_surveys/
```

**Verification**: Check 27 GB archived

---

### Metro SVI Data (~30 GB)

**Directories**:
- `data/metro_commute_svi/` (23 GB) - Full metro area SVI for multiple cities
- `data/metro_cities_svi/` (4.3 GB) - Chicago, Dallas, LA metadata
- `data/metro_cities_svi_test/` (6.7 GB) - Test datasets
- `data/metro_cities_svi_commute/` (1.9 GB) - Commute-filtered metro SVI
- `data/metro_commute_svi_with_shadow/` (288 MB) - Shadow-annotated
- `data/metro_commute_svi_with_utci/` (219 MB) - UTCI-annotated

**Justification**:
- Publication focuses on NYC/Seattle only
- Metro-wide data includes areas beyond municipal boundaries
- NYC/Seattle municipal-only data already in `nyc_seattle_municipal_deployment/`
- Used for exploratory seasonal bias analysis, not final publication

**Action**:
```bash
rsync -av data/metro_commute_svi/ sunny_day_svi_archive/data/metro_commute_svi/
rsync -av data/metro_cities_svi/ sunny_day_svi_archive/data/metro_cities_svi/
rsync -av data/metro_cities_svi_test/ sunny_day_svi_archive/data/metro_cities_svi_test/
rsync -av data/metro_cities_svi_commute/ sunny_day_svi_archive/data/metro_cities_svi_commute/
rsync -av data/metro_commute_svi_with_shadow/ sunny_day_svi_archive/data/metro_commute_svi_with_shadow/
rsync -av data/metro_commute_svi_with_utci/ sunny_day_svi_archive/data/metro_commute_svi_with_utci/
```

**Verification**: Check ~30 GB total archived

---

### Other City Data (~1.5 GB)

#### State College (97 MB)
**Directory**: `data/state-college/`

**Justification**: Methodological testbed, not in publication scope

**Action**:
```bash
rsync -av data/state-college/ sunny_day_svi_archive/data/state-college/
```

#### Boston Metadata (419 MB)
**File**: `data/boston_metadata.csv`

**Justification**: Not publishing Boston results (NYC/Seattle only)

**Action**:
```bash
rsync -av data/boston_metadata.csv sunny_day_svi_archive/data/boston_metadata.csv
```

#### Boston & DC Mobility Surveys (38 MB)
**Directories**:
- `final_cities/Boston/` (1.8 MB)
- `final_cities/Washington DC/` (36 MB)

**Justification**: Not in publication scope

**Action**:
```bash
rsync -av final_cities/Boston/ sunny_day_svi_archive/final_cities/Boston/
rsync -av "final_cities/Washington DC/" sunny_day_svi_archive/final_cities/Washington\ DC/
```

#### Multi-City Results (137 MB)
**Directory**: `data/multi_city_results/`

**Justification**: Exploratory multi-city comparisons, superseded by final NYC/Seattle analysis

**Action**:
```bash
rsync -av data/multi_city_results/ sunny_day_svi_archive/data/multi_city_results/
```

#### Test/Development Data (~500 MB)
**Directories**:
- `data/cache/` (250 MB) - API response cache (if not needed for replication)
- `data/pipeline_test/` - Pipeline testing artifacts
- `data/people_detection_test/` - Detection model testing
- `data/yolo_training_dataset/` - **WAIT: Keep this for publication (195 MB)**

**Note**: `data/yolo_training_dataset/` should be KEPT for model training documentation

**Action**:
```bash
rsync -av data/cache/ sunny_day_svi_archive/data/cache/
rsync -av data/pipeline_test/ sunny_day_svi_archive/data/pipeline_test/
rsync -av data/people_detection_test/ sunny_day_svi_archive/data/people_detection_test/
```

---

### Data Archive Summary

| Category | Size | Directories |
|----------|------|-------------|
| Raw SVI imagery | 129 GB | `data/raw/` |
| Transit surveys | 27 GB | `data/transit_surveys/` (entire directory) |
| Metro SVI data | ~30 GB | `data/metro_*` (6 directories) |
| State College | 97 MB | `data/state-college/` |
| Boston metadata | 419 MB | `data/boston_metadata.csv` |
| Boston/DC surveys | 38 MB | `final_cities/Boston/`, `final_cities/Washington DC/` |
| Multi-city results | 137 MB | `data/multi_city_results/` |
| Test/cache data | ~500 MB | `data/cache/`, `data/pipeline_test/`, etc. |
| **TOTAL** | **~187 GB** | |

---

## Scripts to Archive (~100+ scripts)

### City-Specific Scripts

#### Phoenix Scripts (5 files)
**Location**: `scripts/visualization/`

**Files**:
- `visualize_phoenix_seasonal_utci.py`
- `visualize_phoenix_seasonal_utci_gam.py`
- `visualize_phoenix_alternative_methods.py`
- `visualize_global_comparison_with_phoenix.py`
- `visualize_sunny_vs_temp_with_phoenix.py`

**Archive Path**: `sunny_day_svi_archive/scripts/phoenix/`

**Action**:
```bash
mkdir -p sunny_day_svi_archive/scripts/phoenix/
rsync -av scripts/visualization/*phoenix* sunny_day_svi_archive/scripts/phoenix/
```

#### State College Scripts (20+ files)
**Location**: `scripts/visualization/state_college/` (entire directory)

**Additional State College Scripts**:
- `scripts/processing/add_shadow_to_state_college.py`
- `scripts/processing/add_utci_to_state_college.py`
- `scripts/processing/add_road_bearing_to_state_college.py`
- `scripts/processing/snap_state_college_to_osm.py`
- `scripts/analysis/state_college_bias_correction_diagnostics.py`
- `scripts/pipelines/university_park_svi_pipeline.py`
- `scripts/pipelines/test_university_park_pipeline.py`

**Archive Path**: `sunny_day_svi_archive/scripts/state_college/`

**Action**:
```bash
rsync -av scripts/visualization/state_college/ sunny_day_svi_archive/scripts/state_college/visualization/
rsync -av scripts/processing/*state_college* sunny_day_svi_archive/scripts/state_college/processing/
rsync -av scripts/pipelines/*university_park* sunny_day_svi_archive/scripts/state_college/pipelines/
rsync -av scripts/analysis/*state_college* sunny_day_svi_archive/scripts/state_college/analysis/
```

#### Metro Cities Scripts (15+ files)
**Processing Scripts**:
- `scripts/processing/metro_shadow_annotation_pipeline.py`
- `scripts/processing/metro_shadow_annotation_pipeline_optimized.py`
- `scripts/processing/metro_shadow_annotation_pipeline_resume.py`
- `scripts/processing/metro_bias_corrected_analysis.py`
- `scripts/processing/add_utci_to_metro_svi.py`

**Analysis Scripts**:
- `scripts/analysis/analyze_chicago_dallas_la_seasonal_bias.py`
- `scripts/analysis/analyze_metro_seasonal_bias_prescan.py`
- `scripts/analysis/analyze_metro_seasonal_bias_graph_emd.py`
- `scripts/analysis/download_and_analyze_metro_seasonal_bias.py`
- `scripts/analysis/compute_spatial_emd_bias.py`
- `scripts/analysis/generate_seasonal_bias_report.py`
- `scripts/analysis/generate_graph_emd_report.py`

**Pipeline Scripts**:
- `scripts/pipelines/metro_cities_svi_pipeline.py`
- `scripts/pipelines/test_metro_cities_svi_pipeline.py`

**Data Collection**:
- `scripts/data_collection/download_dallas_la_metadata.py`

**Visualization**:
- `scripts/visualization/visualize_metro_svi_shade_ipw.py`
- `scripts/visualization/metro/` (entire directory)

**Archive Path**: `sunny_day_svi_archive/scripts/metro_cities/`

**Action**:
```bash
mkdir -p sunny_day_svi_archive/scripts/metro_cities/{processing,analysis,pipelines,visualization,data_collection}
rsync -av scripts/processing/metro_* sunny_day_svi_archive/scripts/metro_cities/processing/
rsync -av scripts/analysis/*metro* sunny_day_svi_archive/scripts/metro_cities/analysis/
rsync -av scripts/analysis/*chicago* sunny_day_svi_archive/scripts/metro_cities/analysis/
rsync -av scripts/analysis/*dallas* sunny_day_svi_archive/scripts/metro_cities/analysis/
rsync -av scripts/pipelines/metro_* sunny_day_svi_archive/scripts/metro_cities/pipelines/
rsync -av scripts/data_collection/*dallas* sunny_day_svi_archive/scripts/metro_cities/data_collection/
rsync -av scripts/visualization/metro/ sunny_day_svi_archive/scripts/metro_cities/visualization/
rsync -av scripts/visualization/*metro* sunny_day_svi_archive/scripts/metro_cities/visualization/
```

### Exploratory/Diagnostic Scripts

#### Seasonal Bias Investigation (8+ files)
**Files**:
- `scripts/analysis/seasonal_bias_filtering_stages.py`
- `scripts/analysis/investigate_curve_patterns.py`
- `scripts/analysis/compute_spatial_emd_bias.py`
- And others with "seasonal_bias", "emd", "prescan" in names

**Archive Path**: `sunny_day_svi_archive/scripts/exploratory/seasonal_bias/`

#### Diagnostic Scripts (10+ files)
**Files**:
- `scripts/analysis/filter_utci_by_wind.py`
- `scripts/analysis/investigate_extreme_utci.py`
- `scripts/analysis/sr_ipw_investigation.py`
- Various debugging and diagnostic scripts

**Archive Path**: `sunny_day_svi_archive/scripts/exploratory/diagnostics/`

### OT-SVI Module (29 files)

**Directory**: `scripts/ot_svi/` (entire directory)

**Justification**: Used in separate paper, not needed for NYC/Seattle publication

**Archive Path**: `sunny_day_svi_archive/scripts/ot_svi/`

**Action**:
```bash
rsync -av scripts/ot_svi/ sunny_day_svi_archive/scripts/ot_svi/
```

### Root Directory Scripts (Archive)

**Files**:
- `analyze_commute_time_images.py`
- `generate_commute_filtered_metadata.py`
- `plot_all_metro_temporal.py`
- `plot_temporal_distribution.py`

**Archive Path**: `sunny_day_svi_archive/scripts/root_scripts/`

**Action**:
```bash
mkdir -p sunny_day_svi_archive/scripts/root_scripts/
rsync -av analyze_commute_time_images.py sunny_day_svi_archive/scripts/root_scripts/
rsync -av generate_commute_filtered_metadata.py sunny_day_svi_archive/scripts/root_scripts/
rsync -av plot_all_metro_temporal.py sunny_day_svi_archive/scripts/root_scripts/
rsync -av plot_temporal_distribution.py sunny_day_svi_archive/scripts/root_scripts/
```

### Scripts Archive Summary

| Category | Count | Archive Path |
|----------|-------|--------------|
| Phoenix | 5 | `scripts/phoenix/` |
| State College | 20+ | `scripts/state_college/` |
| Metro cities | 15+ | `scripts/metro_cities/` |
| OT-SVI module | 29 | `scripts/ot_svi/` |
| Seasonal bias investigation | 8+ | `scripts/exploratory/seasonal_bias/` |
| Diagnostic scripts | 10+ | `scripts/exploratory/diagnostics/` |
| Root scripts | 4 | `scripts/root_scripts/` |
| **TOTAL** | **~100+** | |

---

## Outputs to Archive

### Plots and Figures (~450 MB)

**From PLOT_MANIFEST.csv**:
- **Total plots**: 566 files (617.5 MB)
- **To ARCHIVE**: 334 files (453.4 MB)
- **To KEEP**: 43 files (75.2 MB)
- **To REVIEW**: 189 files (88.9 MB - manual classification needed)

**Archive Categories**:

1. **Other Cities** (224 plots)
   - Phoenix plots (8 files in `outputs/plots/phoenix_seasonal/`)
   - State College plots (77 files)
   - Global/Multi-City plots (136 files)
   - Other metro plots (3 files)

2. **Raster Methods Plots** (108 plots)
   - Model training plots (confusion matrices, batch samples)
   - Raster-format IPW/seasonal plots where vector version exists

3. **Exploratory Plots** (2 plots)
   - Wind filtering analysis
   - Extreme UTCI investigations

**Archive Path**: `sunny_day_svi_archive/outputs/plots/`

**Action**: See PLOT_MANIFEST.csv for detailed file-by-file listing

### Model Training Artifacts

#### Alternative YOLO Models (74 MB)
**Files**:
- `outputs/models/yolo11n.pt` (5.4 MB)
- `outputs/models/yolo11s.pt` (19 MB)
- `outputs/models/yolo11l.pt` (50 MB)

**Archive Path**: `sunny_day_svi_archive/outputs/models/alternative_yolo/`

**Action**:
```bash
mkdir -p sunny_day_svi_archive/outputs/models/alternative_yolo/
rsync -av outputs/models/yolo11*.pt sunny_day_svi_archive/outputs/models/alternative_yolo/
```

#### Earlier Training Runs (~110 MB)
**Directories**:
- `outputs/models/sunny_batch_train4/`

**Note**: Keep `sunny_batch_train6/` in publication package (contains best model)

**Archive Path**: `sunny_day_svi_archive/outputs/models/training_runs/`

**Action**:
```bash
rsync -av outputs/models/sunny_batch_train4/ sunny_day_svi_archive/outputs/models/training_runs/train4/
```

#### SAM2 Model (?)
**Directory**: `outputs/models/SAM2/`

**Question**: Is this used in the pipeline? If not, archive.

**Action**: Investigate usage before archiving

### Intermediate Analysis Outputs

**Files to Evaluate**:
- Checkpoint files in `final_run_outputs/` (209 KB total)
- `with_shadow_metrics.csv` files (1.1 GB) - if redundant with other datasets
- Graph EMD cache files
- Seasonal bias diagnostic outputs

**Archive Path**: `sunny_day_svi_archive/outputs/intermediate/`

---

## Documentation to Archive

### Metro/Multi-City Documentation (~15 files)

**Files**:
- `docs/DOWNLOAD_PROGRESS_TRACKING.md`
- `docs/SAFE_METRO_DOWNLOAD_PLAN.md`
- `docs/METRO_DOWNLOAD_MEMORY_FIX.md`
- `docs/METRO_SHADOW_PIPELINE_BUGFIXES.md`
- `docs/METRO_SURVEY_SUMMARY.md`
- `docs/METRO_SVI_FINDINGS.md`
- `docs/METRO_SVI_OPTIMIZATIONS.md`
- And other metro-related docs

**Archive Path**: `sunny_day_svi_archive/docs/metro/`

### Exploratory Analysis Documentation (~20 files)

**Files**:
- `docs/GRAPH_EMD_SEASONAL_BIAS_RESULTS.md` (29 KB)
- `docs/MEASURING_SEASONAL_BIAS.md`
- `docs/SEASONAL_BIAS_FILTERING_ANALYSIS.md`
- `docs/SPATIAL_SEASONAL_BIAS_METRICS.md` (34 KB)
- `docs/CURVE_PATTERN_ANALYSIS.md`
- And other diagnostic/exploratory documentation

**Archive Path**: `sunny_day_svi_archive/docs/exploratory/`

### Technical Notes (~15 files)

**Files**:
- `docs/UTCI_FIX_SUMMARY.md`
- `docs/UTCI_WIND_SPEED_FIX.md`
- `docs/DATETIME_HANDLING.md`
- `docs/RATE_LIMITING_IMPROVEMENTS.md`
- `docs/PERFORMANCE_ANALYSIS.md`
- `docs/PERFORMANCE_IMPROVEMENTS_IMPLEMENTED.md`
- Bug fix logs, recovery documentation

**Archive Path**: `sunny_day_svi_archive/docs/technical/`

### Large Debug Files

**File**: `docs/weather_processing_output.txt` (67 MB)

**Archive Path**: `sunny_day_svi_archive/docs/debug/`

**Action**:
```bash
mkdir -p sunny_day_svi_archive/docs/debug/
rsync -av docs/weather_processing_output.txt sunny_day_svi_archive/docs/debug/
```

### Old Cleanup Plans

**Files**:
- `docs/CLEANUP_SUMMARY.md`
- `docs/CLEANUP_TODO.md`

**Archive Path**: `sunny_day_svi_archive/docs/legacy/`

### Documentation Archive Summary

| Category | Count | Archive Path |
|----------|-------|--------------|
| Metro/multi-city | ~15 | `docs/metro/` |
| Exploratory analyses | ~20 | `docs/exploratory/` |
| Technical notes | ~15 | `docs/technical/` |
| Debug files | 1 (67 MB) | `docs/debug/` |
| Legacy | ~10 | `docs/legacy/` |
| **TOTAL** | **~60** | |

---

## Other Files to Archive

### Root Directory Files

**Files**:
- `temporal_distribution_boston_svi.png` (632 KB)
- `yolo11s.pt` (19 MB) - if duplicate of outputs/models/ version
- `metro_commute_svi_package.tar.gz` (715 MB) - earlier multi-city package

**Archive Path**: `sunny_day_svi_archive/root_artifacts/`

**Action**:
```bash
mkdir -p sunny_day_svi_archive/root_artifacts/
rsync -av temporal_distribution_boston_svi.png sunny_day_svi_archive/root_artifacts/
rsync -av yolo11s.pt sunny_day_svi_archive/root_artifacts/  # if duplicate
rsync -av metro_commute_svi_package.tar.gz sunny_day_svi_archive/root_artifacts/
```

### Archive Directories

**Existing Archives**:
- `archive/phoenix_specific/`
- `archive/phoenix_results/`
- Other archived materials

**Action**: Move to new archive structure
```bash
rsync -av archive/ sunny_day_svi_archive/archive_legacy/
```

---

## Archive Directory Structure

```
sunny_day_svi_archive/
├── README_ARCHIVE.md                      # Archive organization guide
├── ARCHIVE_INDEX.md                       # Complete index of archived files
├── ARCHIVE_CHECKSUMS.txt                  # SHA256 checksums for verification
│
├── data/
│   ├── raw/                               # 129 GB - Raw SVI imagery
│   ├── transit_surveys/                   # 27 GB - All metro surveys
│   ├── metro_commute_svi/                 # 23 GB - Metro SVI data
│   ├── metro_cities_svi/                  # 4.3 GB - Chicago/Dallas/LA
│   ├── metro_cities_svi_test/             # 6.7 GB - Test datasets
│   ├── metro_cities_svi_commute/          # 1.9 GB - Commute-filtered
│   ├── metro_commute_svi_with_shadow/     # 288 MB - Shadow-annotated
│   ├── metro_commute_svi_with_utci/       # 219 MB - UTCI-annotated
│   ├── state-college/                     # 97 MB - State College data
│   ├── boston_metadata.csv                # 419 MB
│   ├── multi_city_results/                # 137 MB
│   ├── cache/                             # 250 MB - API cache
│   ├── pipeline_test/                     # Test artifacts
│   └── people_detection_test/             # Detection tests
│
├── final_cities/
│   ├── Boston/                            # 1.8 MB
│   └── Washington DC/                     # 36 MB
│
├── scripts/
│   ├── phoenix/                           # 5 Phoenix scripts
│   ├── state_college/                     # 20+ State College scripts
│   ├── metro_cities/                      # 15+ Metro scripts
│   ├── ot_svi/                            # 29 OT-SVI module files
│   ├── exploratory/
│   │   ├── seasonal_bias/                 # 8+ investigation scripts
│   │   └── diagnostics/                   # 10+ diagnostic scripts
│   └── root_scripts/                      # 4 root directory scripts
│
├── outputs/
│   ├── plots/                             # ~450 MB archived plots
│   │   ├── phoenix/
│   │   ├── state_college/
│   │   ├── global_multi_city/
│   │   ├── exploratory/
│   │   └── raster_duplicates/
│   ├── models/
│   │   ├── alternative_yolo/              # 74 MB alternate models
│   │   └── training_runs/                 # ~110 MB earlier runs
│   └── intermediate/                      # Checkpoint files, etc.
│
├── docs/
│   ├── metro/                             # ~15 metro documentation files
│   ├── exploratory/                       # ~20 exploratory analysis docs
│   ├── technical/                         # ~15 bug fix/optimization logs
│   ├── debug/                             # weather_processing_output.txt (67 MB)
│   └── legacy/                            # Old cleanup plans, etc.
│
├── root_artifacts/
│   ├── temporal_distribution_boston_svi.png
│   ├── yolo11s.pt                         # If duplicate
│   └── metro_commute_svi_package.tar.gz   # 715 MB
│
└── archive_legacy/                        # Existing archive/ directory
```

---

## Archive Verification Checklist

Before removing files from main repository:

- [ ] All data directories copied with `rsync -av`
- [ ] Checksums generated for files >100 MB
- [ ] Archive directory size verified: ~185 GB
- [ ] Archive README created with navigation guide
- [ ] Archive index created listing all files
- [ ] Sample files spot-checked for integrity
- [ ] Archive backup created on external drive
- [ ] Archive path added to `.gitignore`

---

## Post-Archive Main Repository Contents

### What Remains in Main Repo (Publication Package)

**Data** (~7-8 GB):
- `final_run_outputs/` - NYC/Seattle final datasets (5.5 GB)
- `final_cities/NYC/` - NYC 2022 mobility survey (52 MB)
- `final_cities/seattle/` - Seattle travel survey (133 MB)
- `outputs/analysis/nyc_trips_with_utci.csv` (40 MB)
- `outputs/analysis/seattle_trips_with_utci.csv` (58 MB)
- `data/yolo_training_dataset/` - YOLO training data (195 MB)
- Geographic boundaries (TBD, <10 MB)

**Models** (~438 MB):
- `outputs/models/vit_binary.pth` (328 MB)
- `outputs/models/sunny_batch_train6/weights/best.pt` (110 MB)

**Outputs** (~100-150 MB):
- `outputs/publication/` - Publication-ready plots (~75 MB)
- `outputs/tables/` - Analysis tables
- Model evaluation outputs

**Scripts** (~50 production scripts):
- Core processing pipeline
- Final analysis scripts
- Publication visualization scripts
- Core utilities

**Documentation** (~15-20 docs):
- Methods documentation
- Replication guide
- Data dictionary
- Computational requirements

**Deployment Package**:
- `nyc_seattle_municipal_deployment/` (1.1 GB) - Optional

**Total**: ~10-12 GB (vs. current 195 GB)

---

## Document Status

- **Created**: 2026-04-21
- **Last Updated**: 2026-04-21
- **Phase**: 1 - Planning
- **Next Phase**: 2 - Execute Archive Creation
