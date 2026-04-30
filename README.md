# Urban Shade Preference Analysis: NYC and Seattle

Analysis of shade-seeking behavior in New York City and Seattle using street view imagery, thermal comfort metrics, and mobility survey data.

**Publication Package** | **Replication-Ready** | **NYC & Seattle Focus**

---

## Overview

This repository contains the complete analysis pipeline for measuring how urban heat influences shade-seeking behavior using:
- **Street View Imagery**: Mapillary imagery across NYC and Seattle
- **Shadow Detection**: Machine learning-based shadow and people detection
- **Thermal Comfort**: UTCI (Universal Thermal Climate Index) calculations
- **Mobility Data**: NYC Citywide Mobility Survey 2022 and Seattle Household Travel Survey
- **Statistical Methods**: Inverse Probability Weighting (IPW) for bias correction

### Key Findings

Analysis of shade preference patterns across thermal comfort conditions, accounting for:
- Seasonal sampling bias
- Temperature confounding
- Shadow ratio effects on pedestrian behavior

---

## Repository Structure

```
├── data/                           # Analysis datasets (1.8 GB)
│   ├── final_datasets/            # NYC & Seattle final analysis data (903 MB)
│   │   ├── nyc/                   # NYC final datasets with IPW corrections
│   │   └── seattle/               # Seattle final datasets with IPW corrections
│   ├── mobility_surveys/          # Travel survey data + UTCI annotations (281 MB)
│   │   ├── nyc/                   # NYC 2022 Citywide Mobility Survey
│   │   └── seattle/               # Seattle Household Travel Survey
│   ├── vit_training_dataset/      # Binary classification training (444 MB)
│   ├── yolo_training_dataset/     # Object detection training (195 MB)
│   ├── city_boundaries/           # NYC & Seattle geographic boundaries (2.2 MB)
│   └── geographic_lookups/        # ZIP/county centroids (904 KB)
│
├── models/                         # Machine learning models (110 MB)
│   └── yolo_best.pt               # YOLO v11 people detection model
│
├── scripts/                        # Analysis pipeline (3.0 MB, 103 scripts)
│   ├── analysis/                  # Statistical analysis (12 scripts)
│   ├── processing/                # Data enrichment (23 scripts)
│   ├── visualization/             # Publication plots (32 scripts)
│   ├── ml/                        # Model training (14 scripts)
│   ├── pipelines/                 # End-to-end workflows (7 scripts)
│   ├── data_collection/           # SVI download (9 scripts)
│   └── utils/                     # Helper functions (6 scripts)
│
├── outputs/                        # Results and figures (108 MB)
│   ├── plots/                     # Publication-ready visualizations (101 MB)
│   └── analysis/                  # Statistical results and reports (7 MB)
│
├── docs/                           # Documentation (69 MB, 64 files)
│   ├── 01_GETTING_STARTED.md      # Project setup and overview
│   ├── 02_DATA_COLLECTION.md      # SVI data download guide
│   ├── 03_PROCESSING.md           # Weather/UTCI enrichment
│   ├── 04_MACHINE_LEARNING.md     # Model training guide
│   ├── 05_VISUALIZATION.md        # Plotting workflows
│   ├── 06_PIPELINES.md            # End-to-end pipelines
│   └── [Analysis guides]          # IPW, seasonal bias, diagnostics
│
├── nyc_seattle_municipal_deployment/  # Self-contained deployment package (717 MB)
│   ├── scripts/                   # Municipal shadow analysis pipeline
│   ├── docs/                      # Deployment guides
│   └── [pipeline files]           # Ready-to-run workflows
│
├── notebooks/                      # Jupyter notebooks (4.2 MB)
│   └── [Exploratory analysis]     # Interactive analysis notebooks
│
└── tests/                          # Test suite (120 KB)
    └── [Unit tests]               # Code validation tests
```

---

## Quick Start

### Prerequisites

```bash
# Python 3.10+ required
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Core Dependencies

- **Data Processing**: `pandas`, `geopandas`, `numpy`
- **Machine Learning**: `torch`, `ultralytics`, `transformers`
- **Visualization**: `matplotlib`, `seaborn`, `plotly`
- **Weather/Climate**: `thermofeel` (UTCI calculations), `requests`
- **Geospatial**: `osmnx`, `shapely`

### Running the Analysis

```bash
# 1. Annotate mobility survey trips with UTCI
python scripts/analysis/annotate_trips_with_utci.py

# 2. Analyze walking behavior vs UTCI
python scripts/analysis/analyze_walking_vs_utci.py

# 3. Generate publication plots
python scripts/visualization/plot_utci_shade_preference_final.py
python scripts/visualization/plot_binned_estimates.py
python scripts/visualization/plot_ipw_smooth_curves.py

# 4. Create cross-city comparison
python scripts/visualization/plot_cross_city_statistical_comparison.py
```

---

## Data Description

### Final Datasets

**NYC** (`data/final_datasets/nyc/`):
- `new-york-city_final_analysis_with_ipw_revised.csv` (105 MB)
  - IPW-corrected shade preference with seasonal + shadow ratio adjustments
- `new-york-city_final_analysis_with_seasonal_and_temp.csv` (119 MB)
  - Triple IPW: seasonal + temperature + shadow ratio corrections

**Seattle** (`data/final_datasets/seattle/`):
- `seattle_final_analysis_with_ipw_revised.csv` (319 MB)
  - IPW-corrected shade preference
- `seattle_final_analysis_with_seasonal_and_temp.csv` (361 MB)
  - Triple IPW corrections

### Key Variables

**Street View Data**:
- `image_id`: Mapillary image identifier
- `lat`, `lon`: Geographic coordinates
- `captured_at`: Image timestamp
- `camera_type`: Device used for capture
- `compass_angle`: Heading direction

**Shadow Metrics**:
- `shadow_ratio`: Proportion of image in shadow (YOLO-detected)
- `people_count`: Number of people detected
- `people_in_shade`: Count of people in shadowed areas
- `shade_preference`: Ratio of people in shade / total people

**Thermal Comfort**:
- `utci`: Universal Thermal Climate Index (°C)
- `temperature_2m`: Air temperature
- `relative_humidity_2m`: Humidity (%)
- `wind_speed_10m`: Wind speed (m/s)
- `surface_solar_radiation`: Solar radiation (W/m²)

**IPW Weights**:
- `seasonal_weight`: Corrects for temporal sampling bias
- `temp_weight`: Corrects for temperature confounding
- `sr_weight`: Corrects for shadow ratio propensity
- `combined_weight`: Product of all three weights

### Data Sources & APIs

This project integrates multiple data sources. Below are the APIs and data portals used:

#### Street View Imagery - Mapillary

**Location**: Street-level imagery for NYC and Seattle (2015-2023)

- **API Documentation**: [Mapillary API v4](https://www.mapillary.com/developer/api-documentation)
- **Getting Started**: [Mapillary Developer Portal](https://www.mapillary.com/developer)
- **Access**: Requires free API key (sign up at developer portal)
- **Data Collection Scripts**: See `scripts/data_collection/` for Mapillary download scripts
- **Coverage**: ~1.1 million street view images analyzed across NYC and Seattle

#### Weather & Climate Data - Open-Meteo / ERA5

**Location**: Historical weather data for UTCI calculations

- **Open-Meteo API**: [https://open-meteo.com/](https://open-meteo.com/)
- **API Documentation**: [Open-Meteo API Docs](https://open-meteo.com/en/docs)
- **Historical Weather API**: [Historical Weather Endpoint](https://open-meteo.com/en/docs/historical-weather-api)
- **ERA5 Reanalysis**: [ECMWF ERA5 Data](https://www.ecmwf.int/en/forecasts/datasets/reanalysis-datasets/era5)
- **Access**: Free, no API key required for Open-Meteo
- **Data Variables**: Temperature, humidity, wind speed, solar radiation (hourly, 1940-present)
- **Processing Scripts**: See `scripts/processing/add_weather_data.py` and `scripts/processing/add_utci_to_final_cities.py`

#### Geographic Data - OpenStreetMap

**Location**: Geographic boundaries and spatial data

- **OpenStreetMap**: [https://www.openstreetmap.org/](https://www.openstreetmap.org/)
- **API Documentation**: [OSM API](https://wiki.openstreetmap.org/wiki/API)
- **Python Access**: Uses [OSMnx library](https://osmnx.readthedocs.io/) for programmatic access
- **Data Types**: City boundaries, street networks, geographic features
- **Usage**: Boundary definitions, spatial joins, geographic context

#### Mobility Survey Data

**NYC** (`data/mobility_surveys/nyc/`):
- **Survey**: 2022 NYC Citywide Mobility Survey (52 MB)
- **Source**: NYC Department of Transportation (NYC DOT)
- **Download**: [NYC Citywide Mobility Survey Data](https://www.nyc.gov/html/dot/html/about/citywide-mobility-survey.shtml)
- **Documentation**: User guide and codebook included in `data/mobility_surveys/nyc/`
- **Survey Period**: September 28 - November 17, 2022
- **Respondents**: 2,966 NYC residents
- **UTCI-annotated trips**: `nyc_trips_with_utci.csv` (40 MB)

**Seattle** (`data/mobility_surveys/seattle/`):
- **Survey**: 2017 Puget Sound Regional Council Household Travel Survey (133 MB)
- **Source**: Puget Sound Regional Council (PSRC)
- **Download**: [PSRC Household Travel Survey Program](https://www.psrc.org/our-work/household-travel-survey-program)
- **Data Portal**: [PSRC Open Data Portal](https://psrc-psregcncl.hub.arcgis.com/)
- **Survey Year**: 2017
- **Households**: 11,310 households surveyed
- **Persons**: 19,573 persons
- **Trips**: 191,992 trip records
- **Coverage**: Puget Sound region including Seattle
- **UTCI-annotated trips**: `seattle_trips_with_utci.csv` (58 MB)

---

## Scripts Overview

### Analysis Scripts (12 files)

| Script | Purpose |
|--------|---------|
| `analyze_walking_vs_utci.py` | Walking mode choice vs thermal comfort |
| `annotate_trips_with_utci.py` | Add UTCI to mobility survey trips |
| `investigate_curve_patterns.py` | Analyze shade preference curve shapes |
| `seasonal_bias_filtering_stages.py` | Multi-stage bias correction analysis |
| `sr_ipw_investigation.py` | Shadow ratio IPW diagnostics |
| `filter_utci_by_wind.py` | Wind speed sensitivity analysis |

### Processing Scripts (23 files)

| Script | Purpose |
|--------|---------|
| `add_shadow_to_final_cities.py` | Shadow annotation using YOLO |
| `add_shadow_to_final_cities_optimized.py` | Faster shadow detection |
| `add_utci_to_final_cities.py` | UTCI calculation from weather data |
| `apply_triple_ipw_final_cities.py` | Apply IPW corrections |
| `apply_triple_ipw_final_cities_revised.py` | Revised IPW with diagnostics |
| `apply_seasonal_reweighting.py` | Seasonal bias correction |
| `add_weather_data.py` | ERA5 weather enrichment |

### Visualization Scripts (32 files)

| Script | Purpose |
|--------|---------|
| `plot_utci_shade_preference_final.py` | Main shade preference curves |
| `plot_binned_estimates.py` | Binned shade preference with CIs |
| `plot_ipw_smooth_curves.py` | Smoothed IPW-corrected curves |
| `plot_cross_city_statistical_comparison.py` | NYC vs Seattle comparison |
| `plot_seasonal_bootstrap_comparison.py` | Seasonal adjustment effects |
| `plot_data_quality_diagnostics.py` | Sample size & coverage diagnostics |
| `plot_weight_distributions.py` | IPW weight diagnostics |
| `plot_residual_diagnostics.py` | Model residual analysis |

### Machine Learning Scripts (14 files)

| Script | Purpose |
|--------|---------|
| `binary_image_classification.py` | ViT sunny/cloudy classifier training |
| `yolo_train_portable.py` | YOLO people detection training |
| `evaluate_yolo_model.py` | Model performance evaluation |
| `generate_annotated_samples.py` | Create visualization samples |

---

## Key Methodologies

### 1. Shadow Detection

**Models**:
- **YOLO v11**: Detects people and shadows in street view images
- **Vision Transformer (ViT)**: Binary classifier for sunny vs cloudy conditions

**Pipeline**:
1. Load Mapillary street view image
2. Run YOLO inference to detect people bounding boxes
3. Segment shadow regions using threshold-based detection
4. Calculate overlap between people and shadows
5. Compute `shade_preference = people_in_shade / total_people`

### 2. UTCI Calculation

**Universal Thermal Climate Index** integrates:
- Air temperature (°C)
- Relative humidity (%)
- Wind speed (m/s)
- Mean radiant temperature (from solar radiation)

**Data Sources**:
- ERA5 reanalysis: Hourly historical weather (1940-present)
- Open-Meteo API: High-resolution climate data
- Thermofeel Python package: UTCI calculation implementation

### 3. Inverse Probability Weighting (IPW)

**Purpose**: Correct for non-random sampling biases

**Three-Stage Correction**:

1. **Seasonal Weight**: Corrects temporal sampling bias
   ```
   P(photo | month, day_of_week) → seasonal_weight
   ```

2. **Temperature Weight**: Corrects temperature confounding
   ```
   P(photo | utci_bin, season) → temp_weight
   ```

3. **Shadow Ratio Weight**: Corrects shadow ratio propensity
   ```
   P(photo | shadow_ratio_bin, utci) → sr_weight
   ```

**Combined Weight**:
```
combined_weight = seasonal_weight × temp_weight × sr_weight
```

**Implementation**: See `scripts/processing/apply_triple_ipw_final_cities_revised.py`

### 4. Statistical Analysis

**Binned Estimates**:
- UTCI binned into 2°C intervals
- Weighted means with 95% confidence intervals
- Bootstrap resampling for uncertainty quantification

**Smooth Curves**:
- Lowess smoothing with IPW-weighted observations
- Cross-validation for bandwidth selection
- Comparison across correction stages

---

## Outputs

### Publication Plots

Located in `outputs/plots/`:

**Main Results**:
- `shade_behavior/` - Shade preference vs UTCI curves
- `ipw_weighted/` - IPW-corrected comparisons
- `commute_hours/` - Commute time filtering effects

**Diagnostics**:
- `people_count/` - Sample size distributions
- `temperature_comparison/` - UTCI vs dry bulb comparison
- Data quality plots in `outputs/analysis/figures/`

### Analysis Results

Located in `outputs/analysis/`:

**Statistical Outputs**:
- `utci_shade_preference_curves.pdf` - Main publication figure
- `figures/` - Individual diagnostic plots (PDF format)
- `WALKING_UTCI_ANALYSIS.md` - Mobility survey results

**Summary Statistics**:
- `data/final_datasets/{city}/{city}_ipw_revised_summary_stats.csv`
- Binned estimates with confidence intervals
- Sample sizes per UTCI bin

---

## Machine Learning Models

### YOLO People Detection

**Model**: `models/yolo_best.pt` (110 MB)
- Architecture: YOLO v11s
- Task: Detect people and shadows in street view images
- Training: 195 MB custom dataset (`data/yolo_training_dataset/`)
- Performance: See `docs/END_TO_END_ACCURACY_ANALYSIS.md`

### ViT Binary Classifier

**Model**: `vit_binary.pth` (**Not in repository** - see below)
- Architecture: Vision Transformer
- Task: Binary classification (sunny vs cloudy)
- Training: 444 MB dataset (`data/vit_training_dataset/`)
  - 843 sunny images
  - 577 not_sunny images
- Training script: `scripts/ml/binary_image_classification.py`

**Note**: Model file (328 MB) excluded from repository due to GitHub size limits.
Will be available via Hugging Face Hub: [link to be added]

---

## Replication Guide

### Full Pipeline

1. **Setup Environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Download ViT Model** (when available)
   ```bash
   # To be added: Hugging Face download instructions
   # Place in models/vit_binary.pth
   ```

3. **Verify Data**
   ```bash
   # Check final datasets exist
   ls data/final_datasets/nyc/
   ls data/final_datasets/seattle/

   # Check mobility surveys
   ls data/mobility_surveys/*/
   ```

4. **Run Analysis**
   ```bash
   # Annotate trips with UTCI
   python scripts/analysis/annotate_trips_with_utci.py

   # Analyze walking patterns
   python scripts/analysis/analyze_walking_vs_utci.py

   # Generate all publication plots
   python scripts/visualization/plot_utci_shade_preference_final.py
   python scripts/visualization/plot_binned_estimates.py
   python scripts/visualization/plot_ipw_smooth_curves.py
   python scripts/visualization/plot_seasonal_bootstrap_comparison.py
   python scripts/visualization/plot_cross_city_statistical_comparison.py
   ```

5. **Review Outputs**
   ```bash
   # Check plots
   ls outputs/plots/shade_behavior/
   ls outputs/plots/ipw_weighted/

   # Check analysis results
   ls outputs/analysis/figures/
   ```

### Processing New Cities (Advanced)

See `docs/02_DATA_COLLECTION.md` and `docs/03_PROCESSING.md` for:
- Mapillary API data download
- Weather data enrichment
- Shadow annotation pipeline
- IPW weight calculation

---

## Documentation

### Getting Started
- **[01_GETTING_STARTED.md](docs/01_GETTING_STARTED.md)** - Project overview, setup, and workflows
- **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)** - Complete directory structure
- **[PHASE_3_COMPLETE.md](PHASE_3_COMPLETE.md)** - Repository organization details

### Data Collection & Processing
- **[02_DATA_COLLECTION.md](docs/02_DATA_COLLECTION.md)** - Mapillary SVI download
- **[03_PROCESSING.md](docs/03_PROCESSING.md)** - Weather and UTCI enrichment
- **[WEATHER_PROCESSING_README.md](docs/WEATHER_PROCESSING_README.md)** - Overnight processing guide

### Machine Learning
- **[04_MACHINE_LEARNING.md](docs/04_MACHINE_LEARNING.md)** - Model training workflows
- **[END_TO_END_ACCURACY_ANALYSIS.md](docs/END_TO_END_ACCURACY_ANALYSIS.md)** - Model evaluation

### Analysis Methods
- **[IPW_RESULTS_INTERPRETATION.md](docs/IPW_RESULTS_INTERPRETATION.md)** - IPW methodology
- **[IPW_ADJUSTMENT_REVIEW_AND_CRITICAL_BUG.md](docs/IPW_ADJUSTMENT_REVIEW_AND_CRITICAL_BUG.md)** - Correction details
- **[SEASONAL_ADJUSTMENT_SUMMARY.md](docs/SEASONAL_ADJUSTMENT_SUMMARY.md)** - Temporal bias correction
- **[WEIGHT_DIAGNOSTICS_REVISED.md](docs/WEIGHT_DIAGNOSTICS_REVISED.md)** - IPW diagnostics

### Visualization
- **[05_VISUALIZATION.md](docs/05_VISUALIZATION.md)** - Plotting workflows
- **[BINNED_SAMPLE_SIZE_SUMMARY.md](docs/BINNED_SAMPLE_SIZE_SUMMARY.md)** - Sample size details

### Workflows
- **[06_PIPELINES.md](docs/06_PIPELINES.md)** - End-to-end pipelines
- **[07_NOTEBOOKS.md](docs/07_NOTEBOOKS.md)** - Jupyter notebook guide

---

## Project Statistics

### Data Coverage
- **Cities**: New York City, Seattle
- **Images Analyzed**: ~1.1 million street view images
- **Unique Locations**: ~500,000 geographic points
- **Time Range**: 2015-2023
- **Survey Respondents**: ~100,000 (NYC + Seattle combined)

### Analysis Outputs
- **Final Datasets**: 4 analysis-ready files (903 MB)
- **Publication Plots**: ~40 vector figures
- **Statistical Models**: 2 IPW correction schemes per city
- **ML Models**: 2 (YOLO people detection, ViT classification)

### Repository Size
- **Total (tracked in git)**: ~3.5 GB
- **Code**: 3.0 MB (103 Python scripts)
- **Data**: 1.8 GB (final datasets + training data)
- **Models**: 110 MB (YOLO only)
- **Outputs**: 108 MB (plots + analysis)
- **Documentation**: 69 MB (64 markdown files)

---

## Municipal Deployment Package

A self-contained package for municipalities is available in `nyc_seattle_municipal_deployment/` (717 MB):

**Contents**:
- Shadow annotation pipeline
- Pre-configured scripts for NYC and Seattle
- Deployment documentation
- Sample outputs and test scripts

**Usage**:
```bash
cd nyc_seattle_municipal_deployment
bash run_pipeline.sh
```

See `nyc_seattle_municipal_deployment/docs/MUNICIPAL_DEPLOYMENT_PACKAGE_GUIDE.md` for details.

---

## Technology Stack

### Core Libraries
- **pandas** (2.0+): Data manipulation and analysis
- **geopandas** (0.13+): Geospatial data processing
- **numpy** (1.24+): Numerical operations
- **scipy** (1.11+): Statistical functions

### Visualization
- **matplotlib** (3.7+): Publication-quality plots
- **seaborn** (0.12+): Statistical visualizations
- **plotly** (5.14+): Interactive charts

### Machine Learning
- **PyTorch** (2.0+): Deep learning framework
- **ultralytics** (8.0+): YOLO object detection
- **transformers** (4.30+): Vision Transformer models
- **torchvision** (0.15+): Computer vision utilities

### Geospatial & Weather
- **osmnx** (1.5+): OpenStreetMap data access
- **shapely** (2.0+): Geometric operations
- **thermofeel** (1.0+): UTCI calculations
- **requests** (2.31+): API client with retry logic

### Development
- **pytest** (7.4+): Testing framework
- **jupyter** (1.0+): Interactive notebooks
- **black**: Code formatting
- **pylint**: Code linting

---

## Common Issues & Troubleshooting

### Missing Model File

**Problem**: `models/vit_binary.pth` not found

**Solution**: Model excluded from repository due to size limits (328 MB)
- Download from Hugging Face Hub: [link to be added]
- Or retrain using `scripts/ml/binary_image_classification.py`

### Memory Errors

**Problem**: Out of memory when processing large datasets

**Solutions**:
- Process one city at a time
- Use chunked processing in scripts (see `--chunk-size` parameters)
- Reduce batch size for ML inference

### UTCI Calculation Errors

**Problem**: Missing or invalid UTCI values

**Solutions**:
- Verify weather data completeness: `python scripts/analysis/investigate_extreme_utci.py`
- Check ERA5 API access and rate limits
- See `docs/03_PROCESSING.md` for troubleshooting

### Plot Generation Errors

**Problem**: Figures not generating correctly

**Solutions**:
- Verify input data exists in `data/final_datasets/`
- Check IPW weights are calculated
- Review sample sizes with `scripts/visualization/plot_data_quality_diagnostics.py`

---

## Citation

If you use this code or data in your research, please cite:

```bibtex
@article{sunny_day_svi_2024,
  title={Urban Shade Preference and Thermal Comfort: Evidence from New York City and Seattle},
  author={[Authors]},
  journal={[Journal]},
  year={2024},
  note={Data and code: https://github.com/korawichkavee/urban-shades-and-sun}
}
```

---

## License

[License information to be added]

---

## Contact & Support

**Issues**: Create an issue in the GitHub repository

**Questions**:
- Review relevant documentation in `docs/`
- Check existing issues for similar problems
- Examine code comments and docstrings

**Contributing**:
- Fork the repository
- Create a feature branch
- Submit a pull request with clear description

---

## Acknowledgments

### Data Sources & APIs

**Street View Imagery**:
- **Mapillary**: Street view imagery (2015-2023), ~1.1M images
  - API: https://www.mapillary.com/developer/api-documentation
  - Developer Portal: https://www.mapillary.com/developer

**Weather & Climate Data**:
- **Open-Meteo API**: Historical weather data (hourly reanalysis, 1940-present)
  - API: https://open-meteo.com/
  - Documentation: https://open-meteo.com/en/docs
- **ECMWF ERA5**: Reanalysis datasets
  - Info: https://www.ecmwf.int/en/forecasts/datasets/reanalysis-datasets/era5

**Mobility Surveys**:
- **NYC DOT**: 2022 Citywide Mobility Survey (Sept-Nov 2022, 2,966 respondents)
  - Download: https://www.nyc.gov/html/dot/html/about/citywide-mobility-survey.shtml
- **Puget Sound Regional Council (PSRC)**: 2017 Household Travel Survey (11,310 households, 19,573 persons)
  - Download: https://www.psrc.org/our-work/household-travel-survey-program
  - Data Portal: https://psrc-psregcncl.hub.arcgis.com/

**Geographic Data**:
- **OpenStreetMap**: Geographic boundaries and street networks
  - Website: https://www.openstreetmap.org/
  - API: https://wiki.openstreetmap.org/wiki/API
  - Python Access: https://osmnx.readthedocs.io/ (OSMnx library)

### Tools & Libraries
- PyTorch and Hugging Face teams
- Ultralytics YOLO team
- GeoPandas and OSMnx developers
- Thermofeel package authors

---

## Version History

**Latest Release** (Phase 3 Complete):
- Repository reorganized for publication
- NYC and Seattle focus (removed exploratory cities)
- 195 GB → 3.5 GB tracked repository size
- 103 production scripts (from 205)
- Complete IPW methodology implementation
- Publication-ready visualization suite

See [PHASE_3_COMPLETE.md](PHASE_3_COMPLETE.md) for detailed changelog.

---

**Last Updated**: 2026-04-27
**Repository**: https://github.com/korawichkavee/urban-shades-and-sun
