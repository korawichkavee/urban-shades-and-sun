# Urban Shade Preference Analysis: Seattle

Analysis of shade-seeking behavior using street view imagery, thermal comfort metrics, and mobility survey data.

**Publication Package** | **Replication-Ready** | **Seattle Case Study**

---

## Overview

This repository contains the complete analysis pipeline for measuring how urban heat influences shade-seeking behavior using:
- **Street View Imagery**: Mapillary imagery from Seattle, WA
- **Shadow Detection**: Machine learning-based shadow and people detection
- **Thermal Comfort**: UTCI (Universal Thermal Climate Index) calculations
- **Mobility Data**: Seattle Household Travel Survey (Puget Sound Regional Council 2023)
- **Statistical Methods**: Inverse Probability Weighting (IPW) for bias correction

### Key Findings

Analysis of shade preference patterns across thermal comfort conditions, accounting for:
- Seasonal sampling bias
- Temperature confounding
- Shadow ratio effects on pedestrian behavior

---

## Repository Structure

```
├── data/                           # Analysis datasets (~5.5 GB)
│   ├── final_datasets/            # Seattle final analysis data (679 MB)
│   │   └── seattle/               # Seattle datasets with IPW corrections
│   ├── mobility_surveys/          # Travel survey data + UTCI annotations (281 MB)
│   │   └── seattle/               # Seattle Household Travel Survey
│   └── [additional data files]    # Supporting datasets
│
├── scripts/                        # Analysis pipeline (79 scripts)
│   ├── analysis/                  # Statistical analysis & sensitivity
│   ├── processing/                # Data enrichment
│   ├── visualization/             # Publication plots
│   ├── ml/                        # Model training
│   ├── pipelines/                 # End-to-end workflows
│   ├── data_collection/           # SVI download
│   └── utils/                     # Helper functions
│
└── outputs/                        # Results and figures
    ├── plots/                     # Publication-ready visualizations
    └── analysis/                  # Statistical results and reports
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
# Generate main ablation table (Paper Table 2)
python scripts/analysis/compute_ablation_table.py

# Generate main figure (Paper Figure 2)
python scripts/visualization/plot_shade_preference_adjustment_progression.py

# Generate sensitivity analyses (Supplementary Tables S1, S2)
python scripts/analysis/sensitivity/sensitivity_winsorization.py
python scripts/analysis/sensitivity/sensitivity_tau.py
```

---

## Data Description

### Final Datasets

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

**Location**: Street-level imagery for Seattle (2015-2023)

- **API Documentation**: [Mapillary API v4](https://www.mapillary.com/developer/api-documentation)
- **Getting Started**: [Mapillary Developer Portal](https://www.mapillary.com/developer)
- **Access**: Requires free API key (sign up at developer portal)
- **Data Collection Scripts**: See `scripts/data_collection/` for Mapillary download scripts
- **Coverage**: Street view images analyzed for Seattle, WA

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

### Analysis Scripts (7 files)

| Script | Purpose |
|--------|---------|
| `compute_ablation_table.py` | Generate main ablation study results (Table 2) |
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

### Visualization Scripts (10 files)

| Script | Purpose |
|--------|---------|
| `plot_shade_preference_adjustment_progression.py` | Main figure (Figure 2): IPW adjustment progression |
| `plot_utci_shade_preference_final.py` | Main shade preference curves |
| `plot_utci_shade_preference_curves.py` | Alternative shade preference visualizations |
| `plot_binned_estimates.py` | Binned shade preference with CIs |
| `plot_ipw_smooth_curves.py` | Smoothed IPW-corrected curves |
| `plot_cross_city_statistical_comparison.py` | Cross-city statistical comparison |
| `plot_seasonal_bootstrap_comparison.py` | Seasonal adjustment effects |
| `plot_data_quality_diagnostics.py` | Sample size & coverage diagnostics |
| `plot_weight_distributions.py` | IPW weight diagnostics |
| `plot_residual_diagnostics.py` | Model residual analysis |

### Machine Learning Scripts (15 files)

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

**Model**: `models/yolo_best.pt` (archived)
- Architecture: YOLO v11s
- Task: Detect people and shadows in street view images
- Training: Custom dataset (archived)

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
   ls data/final_datasets/seattle/

   # Check mobility surveys
   ls data/mobility_surveys/seattle/
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

---

## Project Statistics

### Data Coverage
- **City**: Seattle, WA
- **Images Analyzed**: 51,243 street view images (with pedestrians)
- **UTCI Range**: -17°C to 33°C
- **Time Range**: 2015-2023
- **Survey Data**: 56,704 trips from Puget Sound Regional Council Household Travel Survey (2023)

### Analysis Outputs
- **Final Datasets**: 2 Seattle analysis-ready files (680 MB)
- **Publication Plots**: Main figure + supplementary figures
- **Statistical Models**: Triple IPW correction (seasonal, temperature, shadow ratio)
- **Sensitivity Analyses**: Winsorization, tau decay parameter

### Repository Size
- **Total (working directory)**: ~5.5 GB
- **Code**: 79 Python scripts
- **Data**: Seattle dataset (680 MB) + mobility surveys (281 MB) + supporting files
- **Outputs**: Analysis results and plots

---

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
- Verify weather data completeness
- Check ERA5 API access and rate limits
- Review processing scripts in `scripts/processing/`

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
@inproceedings{elrod2026hot,
    title={Too Hot to Handle: Why Measuring Human Behavior in Street View
  Imagery Is Harder Than It Looks},
    author={Elrod, Kieran and Kavee, Korawich and Flanigan, Katherine A. and
   Berg{\'e}s, Mario},
    booktitle={IFAC Conference on Cyber-Physical Human Systems},
    volume={59},
    number={23},
    pages={1--8},
    year={2026},
    organization={IFAC},
    publisher={Elsevier},
    note={Code and data:
  \url{https://github.com/korawichkavee/urban-shades-and-sun}}
  }
```

---

## License
MIT License

---

## Contact

**Issues**: Create an issue in the GitHub repository

**Questions**:
- Check existing issues for similar problems
- Examine code comments and docstrings
- Review scripts in `scripts/` directory
- Contact the authors

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

**Last Updated**: 2026-04-27
**Repository**: https://github.com/korawichkavee/urban-shades-and-sun
