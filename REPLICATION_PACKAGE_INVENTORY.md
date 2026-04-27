# Replication Package Inventory

**Purpose**: Define exactly what goes into the final publication replication package for NYC/Seattle shade preference analysis.

**Created**: 2026-04-21
**Status**: Phase 1 - Inventory
**Target Size**: ~15-20 GB (from current 195 GB)

---

## Archive Decisions Summary

**Geographic Scope**: NYC and Seattle ONLY
- Archive ALL other cities (Phoenix, State College, Boston, DC, Chicago, Dallas, LA, 21 metro cities)

**Data Retention**:
- ✅ KEEP: Processed/final datasets (shadow-annotated, UTCI-enriched, IPW-corrected)
- ✅ KEEP: ML model training datasets (195 MB YOLO, ViT training data)
- ✅ KEEP: NYC/Seattle mobility survey data (from final_cities/)
- ✅ KEEP: NYC/Seattle UTCI-annotated trips (98 MB total)
- ❌ ARCHIVE: Raw SVI imagery (129 GB in data/raw/)
- ❌ ARCHIVE: All metro transit surveys except NYC/Seattle subsets
- ❌ ARCHIVE: Test datasets, intermediate processing files
- ❌ ARCHIVE: OT-SVI module (29 files - used in different paper)

**Plot Retention**:
- ✅ KEEP: Vector format (.pdf, .svg) publication plots only
- ❌ ARCHIVE: Exploratory/diagnostic plots
- ❌ ARCHIVE: Raster-only plots (unless publication-ready)
- ❌ ARCHIVE: All other-city plots

**Code Retention**:
- ✅ KEEP: Production pipeline scripts (shadow → UTCI → IPW → seasonal)
- ✅ KEEP: Final visualization scripts for publication figures
- ✅ KEEP: Core utilities (enhanced_utci.py, salusshadow.py)
- ❌ ARCHIVE: Exploratory/diagnostic scripts (~100+ scripts)
- ❌ ARCHIVE: Other-city specific scripts (Phoenix: 5, State College: 20+, metro: 10+)

**Models**:
- ✅ KEEP: vit_binary.pth (328 MB - sunny/cloudy classifier)
- ✅ KEEP: Best YOLO model for person/shadow detection (110 MB from sunny_batch_train6)
- ❌ ARCHIVE: Alternative YOLO variants (yolo11n.pt, yolo11l.pt, yolo11s.pt)
- ❌ ARCHIVE: Training run artifacts (except best model)
- 📋 TODO: Git-LFS or external hosting (decision deferred)

---

## NYC/Seattle Data Inventory

### Final Processed Datasets (5.5 GB total)

**Location**: `/final_run_outputs/`

#### NYC Datasets (2.6 GB)
| File | Size | Description | Status |
|------|------|-------------|--------|
| `new-york-city_shadow_annotated.csv` | 460 MB | Shadow detection results for 3.36M images | ✅ KEEP |
| `new-york-city_with_shadow_and_utci.csv` | 993 MB | Full shadow + UTCI annotations | ✅ KEEP |
| `new-york-city_final_analysis_with_ipw.csv` | 115 MB | Triple IPW corrections applied | ✅ KEEP (primary) |
| `new-york-city_final_analysis_with_ipw_revised.csv` | 105 MB | Revised IPW version | ✅ KEEP |
| `new-york-city_final_analysis_with_seasonal_and_temp.csv` | 119 MB | Seasonal reweighting + temp IPW | ✅ KEEP (primary) |
| `new-york-city_final_analysis_with_seasonal_no_temp.csv` | 119 MB | Seasonal reweighting only | ✅ KEEP |
| `new-york-city_with_shadow_metrics.csv` | 660 MB | Intermediate shadow metrics | ⚠️ EVALUATE (may be redundant) |
| `new-york-city_ipw_summary_stats.csv` | 361 B | IPW summary statistics | ✅ KEEP |
| `new-york-city_ipw_revised_summary_stats.csv` | 366 B | Revised IPW summary | ✅ KEEP |
| `new-york-city_shadow_checkpoint.json` | 114 KB | Processing checkpoint | ❌ ARCHIVE |

#### Seattle Datasets (2.9 GB)
| File | Size | Description | Status |
|------|------|-------------|--------|
| `seattle_shadow_annotated.csv` | 323 MB | Shadow detection results for 2.35M images | ✅ KEEP |
| `seattle_with_shadow_and_utci.csv` | 702 MB | Full shadow + UTCI annotations | ✅ KEEP |
| `seattle_final_analysis_with_ipw.csv` | 347 MB | Triple IPW corrections applied | ✅ KEEP (primary) |
| `seattle_final_analysis_with_ipw_revised.csv` | 319 MB | Revised IPW version | ✅ KEEP |
| `seattle_final_analysis_with_seasonal_and_temp.csv` | 361 MB | Seasonal reweighting + temp IPW | ✅ KEEP (primary) |
| `seattle_final_analysis_with_seasonal_no_temp.csv` | 361 MB | Seasonal reweighting only | ✅ KEEP |
| `seattle_with_shadow_metrics.csv` | 472 MB | Intermediate shadow metrics | ⚠️ EVALUATE (may be redundant) |
| `seattle_ipw_summary_stats.csv` | 361 B | IPW summary statistics | ✅ KEEP |
| `seattle_ipw_revised_summary_stats.csv` | 362 B | Revised IPW summary | ✅ KEEP |
| `seattle_shadow_checkpoint.json` | 95 KB | Processing checkpoint | ❌ ARCHIVE |

#### Cross-City
| File | Size | Description | Status |
|------|------|-------------|--------|
| `seasonal_reweighting_summary.csv` | 642 B | Seasonal adjustment summary | ✅ KEEP |

**Decision Needed**:
- Keep both "ipw" and "ipw_revised" versions, or just revised?
- Keep both "seasonal_and_temp" and "seasonal_no_temp", or just one?
- Keep intermediate "with_shadow_metrics.csv" files (1.1 GB combined)?

### Raw Mobility Survey Data

**Location**: `/final_cities/`

#### NYC (52 MB)
- `NYC/2022 Citywide Mobility Survey - Trip Codebook.pdf` (224 KB)
- `NYC/2022 Citywide Mobility Survey - Data Dictionary.pdf` (173 KB)
- `NYC/2022_Citywide_Mobility_Survey_Public_Dataset_Trip_20240809.csv` (52 MB)
- **Source**: NYC Open Data Portal
- **Status**: ✅ KEEP (include download script for replication)

#### Seattle (133 MB)
- `seattle/Household_Travel_Survey_Trips_8962432402648352214.csv` (139 MB actual)
- **Source**: Puget Sound Regional Council
- **Status**: ✅ KEEP (include download script for replication)

#### Boston (1.8 MB) - ARCHIVE
- Contains Boston travel survey data
- **Decision**: Archive per geographic scope

#### Washington DC (36 MB) - ARCHIVE
- Contains DC travel survey data
- **Decision**: Archive per geographic scope

### Processed Mobility Survey Data

**Location**: `/outputs/analysis/`

| File | Size | Description | Status |
|------|------|-------------|--------|
| `nyc_trips_with_utci.csv` | 40 MB | NYC trips with UTCI annotations (~300k trips) | ✅ KEEP |
| `seattle_trips_with_utci.csv` | 58 MB | Seattle trips with UTCI annotations (~400k trips) | ✅ KEEP |

**Total**: 98 MB

### ML Models and Training Data

#### Production Models
| File | Size | Description | Status |
|------|------|-------------|--------|
| `outputs/models/vit_binary.pth` | 328 MB | ViT sunny/cloudy binary classifier | ✅ KEEP |
| `outputs/models/sunny_batch_train6/weights/best.pt` | 110 MB | YOLO11 person/shadow detector (best) | ✅ KEEP |

#### Training Datasets
| Directory | Size | Description | Status |
|-----------|------|-------------|--------|
| `data/yolo_training_dataset/` | 195 MB | YOLO training images + labels | ✅ KEEP |
| ViT training data | TBD | Sunny/cloudy training images | ⚠️ LOCATE |

**Decision Needed**: Where is the ViT training dataset? Should it be included?

#### Archive Models
| File | Size | Description | Status |
|------|------|-------------|--------|
| `outputs/models/yolo11n.pt` | 5.4 MB | YOLO nano variant | ❌ ARCHIVE |
| `outputs/models/yolo11s.pt` | 19 MB | YOLO small variant | ❌ ARCHIVE |
| `outputs/models/yolo11l.pt` | 50 MB | YOLO large variant | ❌ ARCHIVE |
| `outputs/models/sunny_batch_train4/` | ~110 MB | Earlier training run | ❌ ARCHIVE |
| `outputs/models/SAM2/` | varies | SAM2 segmentation (unused?) | ⚠️ EVALUATE |

### Geographic Data

**Needed**:
- NYC municipal boundary (simplified GeoJSON)
- Seattle municipal boundary (simplified GeoJSON)

**Current Location**: Likely in `/data/geographic_shapefiles/` (804 MB)

**Action Required**: Extract NYC/Seattle boundaries, create simplified versions (<1 MB each)

### Municipal Deployment Package

**Location**: `/nyc_seattle_municipal_deployment/`

**Size**: 1.1 GB (633 MB compressed)

**Contents**:
- Production-ready shadow analysis pipeline
- Municipal-only metadata (608 MB: NYC 357 MB, Seattle 251 MB)
- Models (438 MB)
- Complete documentation
- Shell scripts for deployment

**Status**: ✅ KEEP (this is a complete standalone package)

**Question**: Should this be included in replication package, or distributed separately?

---

## Plots and Figures Inventory

### Overall Statistics
- **Total plots across all outputs**: 566 files
- **Plots in outputs/plots/**: 296 files
- **NYC/Seattle-specific plots (filename match)**: 69 files
- **IPW diagnostic plots**: ~20 files in `outputs/analysis/ipw_plots/`
- **Seasonal adjustment plots**: ~20 files in `outputs/analysis/seasonally_adjusted_plots/`

### Key Plot Directories

#### `outputs/analysis/ipw_plots/`
Contains:
- Cross-city aggregate comparisons (NYC vs Seattle)
- Cross-city curve comparisons
- Data quality spatial/temporal diagnostics
- Weight distribution plots
- Effective sample size diagnostics

**Status**: ✅ KEEP (methodological figures)

#### `outputs/analysis/seasonally_adjusted_plots/`
Contains:
- Bootstrap aggregate comparisons (with/without temp IPW)
- Bootstrap curve comparisons
- Cross-city binned comparisons
- Seasonal adjustment effect visualizations

**Status**: ✅ KEEP (primary results + sensitivity)

#### `outputs/plots/`
Contains: 296 files (mixed cities, mixed purposes)

**Action Required**:
1. Classify each plot by city (NYC, Seattle, Other, Cross-city, Methods)
2. Classify by purpose (Main results, Validation, Sensitivity, Diagnostic, Exploratory)
3. Check file format (prefer vector .pdf/.svg over raster .png)
4. Create manifest with keep/archive decisions

### Preliminary Plot Classification

**KEEP Categories** (Publication-ready):
1. **Main Results**:
   - Final shade preference curves (NYC, Seattle, cross-city)
   - UTCI vs shade preference with confidence intervals
   - Binned estimates with sample sizes

2. **Validation**:
   - Walk rate validation (trips vs temperature)
   - Data quality diagnostics (spatial/temporal coverage)
   - Model performance metrics (YOLO/ViT)

3. **Methods**:
   - IPW weight distributions and diagnostics
   - Seasonal bias correction effects
   - Bootstrap resampling comparisons

4. **Sensitivity**:
   - Tau sensitivity analyses
   - Shadow ratio threshold sensitivity
   - Temperature IPW vs no temperature IPW

5. **Supplementary**:
   - Additional robustness checks
   - Extended sensitivity analyses
   - Detailed model evaluation

**ARCHIVE Categories**:
1. **Exploratory**: Curve pattern investigations, seasonal bias prescans
2. **Diagnostic**: Debugging plots, extreme value investigations
3. **Other Cities**: Phoenix, State College, metro cities, Chicago/Dallas/LA
4. **Intermediate**: Superseded versions, development iterations

---

## Transit Survey Data

**Location**: `/data/transit_surveys/`

**Current Structure**:
- `metro/extracted/` - 100+ metro survey datasets from various cities/years
- `processed/` - Merged and standardized surveys (1.2 GB)
- `NHTS/` - National Household Travel Survey data
- `documentation/` - Survey documentation
- `nextgen_addons/` - Additional data sources

### Key Processed Files

| File | Size | Description | NYC/SEA? |
|------|------|-------------|----------|
| `metro_surveys_standardized_flexible_with_utci.csv` | 154 MB | All metro surveys with UTCI | Mixed |
| `metro_surveys_standardized_flexible_with_utci_filtered.csv` | 154 MB | Filtered version | Mixed |
| `nhts_2017_standardized.csv` | 110 MB | National survey | National |
| `recoverable_surveys_with_utci.csv` | 67 MB | Recovered surveys with UTCI | Mixed |

### Action Required

**Task**: Extract NYC and Seattle subsets from merged survey files

**NYC Identification**:
- NYC Citywide Mobility Survey data
- Location: New York metro area
- Survey year: 2022
- Method: Filter by geography or survey name

**Seattle Identification**:
- Puget Sound Regional Council survey
- Location: Seattle metro area
- Survey name likely includes "puget" or "seattle"
- Method: Check `metro/extracted/` for Seattle-area surveys

**Next Steps**:
1. Examine `metro_surveys_standardized_flexible_with_utci.csv` to identify city/survey columns
2. Check `metro/extracted/` directory listing for NYC/Seattle surveys
3. Extract NYC/Seattle rows to separate files
4. Verify against raw `final_cities/` data for consistency
5. Archive remaining metro survey data

---

## Scripts and Code Inventory

### Production Pipeline Scripts (KEEP)

**Core Processing** (in `/scripts/processing/`):
- `add_shadow_to_final_cities_optimized.py` - Shadow annotation
- `add_utci_to_final_cities.py` - UTCI computation
- `apply_triple_ipw_final_cities_revised.py` - IPW corrections
- `apply_seasonal_reweighting.py` - Seasonal adjustment

**Core Analysis** (in `/scripts/analysis/`):
- `annotate_trips_with_utci.py` - Mobility survey UTCI annotation
- `analyze_walking_vs_utci.py` - Walk rate analysis

**Core Visualization** (in `/scripts/visualization/`):
- `plot_utci_shade_preference_final.py` - Main results
- `plot_seasonal_adjustment_effect.py` - Seasonal effects
- `plot_ipw_smooth_curves.py` - IPW-corrected curves
- `plot_cross_city_statistical_comparison.py` - NYC vs Seattle
- `plot_binned_estimates.py` - Binned preference curves
- `plot_walk_rate_validation.py` - Walk rate validation
- Plus ~10-15 more publication visualization scripts

**Core Utilities** (in `/scripts/utils/`):
- `enhanced_utci.py` - UTCI computation
- `salusshadow.py` - Shadow detection utilities
- Other core utility modules (TBD - needs import analysis)

**Estimated Total**: ~40-50 production scripts

### Archive Scripts (ARCHIVE)

**Exploratory/Diagnostic** (~50+ scripts):
- `analyze_chicago_dallas_la_seasonal_bias.py`
- `analyze_metro_seasonal_bias_prescan.py`
- `analyze_metro_seasonal_bias_graph_emd.py`
- `download_and_analyze_metro_seasonal_bias.py`
- `compute_spatial_emd_bias.py`
- `seasonal_bias_filtering_stages.py`
- `investigate_curve_patterns.py`
- Plus many more diagnostic/investigation scripts

**Phoenix-Specific** (5 scripts):
- All in `/scripts/visualization/` with "phoenix" in name

**State College-Specific** (20+ scripts):
- `/scripts/visualization/state_college/` entire directory
- `/scripts/processing/` State College processing scripts
- `/scripts/pipelines/university_park_svi_pipeline.py`

**Metro Cities** (15+ scripts):
- `metro_shadow_annotation_pipeline*.py` variants
- Metro-specific visualization scripts
- Metro pipeline scripts

**OT-SVI Module** (29 scripts):
- Entire `/scripts/ot_svi/` directory
- Note: Used in separate paper, not needed here

**Estimated Total**: ~100+ scripts to archive

### Script Dependency Analysis

**Status**: PENDING

**Required Actions**:
1. Trace imports for all production scripts
2. Identify which utilities are actually used
3. Find hard-coded file paths that need updating
4. Create dependency graph
5. Identify any circular dependencies or dead code

---

## Documentation Inventory

### Essential Documentation (KEEP)

**Methods Documentation**:
- IPW methodology (multiple files, consolidate?)
- DCWP method documentation
- Seasonal bias correction methods
- UTCI computation methods
- Shadow detection methods

**Data Documentation**:
- Data dictionary for variables
- Data sources and provenance
- Processing pipeline documentation

**Replication Documentation**:
- Step-by-step replication guide
- Computational requirements
- Expected runtime estimates
- Troubleshooting guide

**Supplementary**:
- Sensitivity analyses documentation
- Data quality assessment
- Cross-city comparison methods

**Estimated**: ~15-20 essential docs (from current 75+)

### Archive Documentation (ARCHIVE)

**Metro/Multi-City** (~15 files):
- Metro download tracking
- Metro shadow pipeline bugfixes
- Metro survey summaries
- Safe metro download plans

**Exploratory Analyses** (~20 files):
- Graph EMD seasonal bias results
- Spatial seasonal bias metrics
- Curve pattern analysis
- Seasonal bias filtering analysis

**Technical Notes** (~15 files):
- Bug fix logs (UTCI, IPW, datetime handling)
- Performance optimization notes
- Rate limiting improvements
- Recovery logs

**City-Specific** (~10 files):
- Phoenix documentation
- State College documentation
- Chicago/Dallas/LA notes

**Legacy/Obsolete** (~10 files):
- Old cleanup plans
- Deprecated model evaluation
- Superseded methodology notes
- Large debug files (weather_processing_output.txt: 67 MB)

---

## Size Estimates

### Current Repository: ~195 GB

**Breakdown**:
- `data/raw/`: 129 GB (raw SVI imagery)
- `data/transit_surveys/`: 27 GB (all cities)
- `data/metro_commute_svi/`: 23 GB (metro SVI)
- `data/metro_cities_svi_test/`: 6.7 GB (test data)
- `final_run_outputs/`: 5.5 GB (NYC/Seattle final)
- Other data: ~3 GB
- Total data: ~195 GB

### Target Replication Package: ~15-20 GB

**Estimated Breakdown**:

**Core Data** (~8-10 GB):
- Final datasets (NYC/Seattle): 5.5 GB (possibly reduce with selective retention)
- NYC/Seattle trips with UTCI: 98 MB
- Raw mobility surveys: 185 MB
- Geographic boundaries: <10 MB
- **Subtotal**: ~6-8 GB

**Models** (~700 MB):
- ViT binary classifier: 328 MB
- YOLO best model: 110 MB
- YOLO training dataset: 195 MB
- ViT training dataset: TBD (estimate 50-100 MB?)
- **Subtotal**: ~700 MB

**Outputs** (~200-500 MB):
- Publication plots (vector format): 100-200 MB estimate
- Analysis tables: <10 MB
- Model evaluation outputs: 50-100 MB
- **Subtotal**: 200-500 MB

**Code and Documentation** (~50 MB):
- Production scripts: ~20 MB
- Documentation: ~10 MB
- Tests: ~5 MB
- Config files: <5 MB
- **Subtotal**: ~50 MB

**Municipal Deployment Package** (optional):
- If included: +1.1 GB
- If separate distribution: 0 GB

**Total Estimate**:
- Without deployment package: **~8-10 GB**
- With deployment package: **~10-12 GB**
- With git-lfs models: **~6-8 GB** (models hosted externally)

### Archive: ~180-185 GB

**To Archive**:
- Raw SVI imagery: 129 GB
- Other cities transit surveys: ~25 GB
- Metro SVI data: ~30 GB (metro_commute_svi + metro_cities_svi + test)
- State College data: 97 MB
- Phoenix data: estimate ~1 GB
- Exploratory outputs: ~2-3 GB
- **Total**: ~185 GB

---

## Next Steps (Phase 1 Completion)

### Immediate Tasks

1. **Transit Survey Subsetting** ✓ In Progress
   - Examine metro survey structure
   - Identify NYC/Seattle datasets
   - Extract to separate files
   - Verify against raw data

2. **Plot Classification**
   - Generate comprehensive plot manifest
   - Classify by city, purpose, format
   - Identify publication-ready plots
   - Flag plots for archive

3. **Script Dependency Analysis**
   - Trace imports for production scripts
   - Identify required utilities
   - Document hard-coded paths
   - Create dependency graph

4. **ViT Training Data Location**
   - Find ViT training dataset
   - Assess size and necessity
   - Decide on inclusion

5. **Dataset Redundancy Resolution**
   - Decide: Keep ipw + ipw_revised, or just revised?
   - Decide: Keep seasonal_and_temp + seasonal_no_temp, or just one?
   - Decide: Keep intermediate with_shadow_metrics.csv files?

### Deliverables for Dude's Review

1. **REPLICATION_PACKAGE_INVENTORY.md** (this document) ✓
2. **ARCHIVE_MANIFEST.md** - Detailed listing of what gets archived
3. **PLOT_MANIFEST.csv** - Complete plot classification
4. **SCRIPT_DEPENDENCIES.md** - Production script dependency graph

### Questions for Dude

1. **Dataset Versions**: Keep all versions (ipw, ipw_revised, seasonal_and_temp, seasonal_no_temp) or pare down?
2. **Intermediate Files**: Keep `with_shadow_metrics.csv` files (1.1 GB) or can they be regenerated?
3. **Municipal Package**: Include in main replication package or distribute separately?
4. **ViT Training Data**: Once located, should it be included? How important for replication?
5. **Plot Format**: Convert all publication plots to vector format, or keep existing mix?

---

## Document Status

- **Created**: 2026-04-21
- **Last Updated**: 2026-04-21
- **Phase**: 1 - Inventory
- **Next Phase**: 2 - Archive Creation (pending Dude's review)
