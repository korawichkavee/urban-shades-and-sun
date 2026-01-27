# Travel Survey Analysis Pipeline

This pipeline analyzes travel survey data to understand how pedestrian mode choice varies with temperature and thermal comfort conditions.

## Overview

The pipeline processes travel survey data through three main stages:

1. **Extraction & Standardization**: Converts survey-specific formats to a common schema
2. **UTCI Annotation**: Adds Universal Thermal Climate Index (UTCI) data using ERA5 weather reanalysis
3. **Visualization**: Creates plots showing pedestrian mode choice vs temperature

## Data Sources

### NHTS 2017 (National Household Travel Survey)

- **Location**: `data/transit_surveys/NHTS/`
- **Files**:
  - `trippub.csv` - 923k trip records
  - `hhpub.csv` - Household data
  - `perpub.csv` - Person data
  - `codebook.xlsx` / `codebook_*.csv` - Data dictionary
- **Coverage**: United States, 2016-2017
- **Geographic Resolution**: State-level centroids (approximate)

### NextGen Add-ons

- **Location**: `data/transit_surveys/nextgen_addons/`
- Regional supplements to NHTS (Georgia, Oahu)

## Pipeline Scripts

All scripts are in `scripts/travel_surveys/`:

### 1. extract_and_standardize.py

Converts survey-specific data to standardized format.

**Usage:**
```bash
python scripts/travel_surveys/extract_and_standardize.py \
    --survey nhts_2017 \
    --config config/travel_survey_config.yaml \
    --output-dir data/transit_surveys/processed
```

**Options:**
- `--survey`: Survey name from config (default: `nhts_2017`)
- `--config`: Path to config file
- `--output-dir`: Output directory
- `--sample N`: Process only first N trips (for testing)

**Output:**
- `data/transit_surveys/processed/nhts_2017_standardized.csv`

**Output Schema:**
| Column | Type | Description |
|--------|------|-------------|
| household_id | str | Household identifier |
| person_id | str | Person identifier |
| trip_num | int | Trip number |
| datetime | datetime | Trip start time (YYYY-MM-DD HH:MM:SS) |
| lat, lon | float | Approximate location (state centroid) |
| location_precision | str | Geographic precision level (`state`, `county`, etc.) |
| state | str | State abbreviation |
| mode_code | int | Numeric mode code |
| mode_label | str | Human-readable mode (e.g., "Walk", "SUV/Crossover") |
| is_full_walk | bool | Entire trip was walking |
| contains_walk | bool | Trip involved walking component |
| is_full_pedestrian | bool | Entire trip was pedestrian (walk/bike/e-scooter) |
| contains_pedestrian | bool | Trip involved pedestrian modes |
| trip_miles | float | Trip distance |
| trip_minutes | float | Trip duration |

### 2. add_utci.py

Adds UTCI thermal comfort data using existing ERA5 infrastructure.

**Usage:**
```bash
python scripts/travel_surveys/add_utci.py \
    --input data/transit_surveys/processed/nhts_2017_standardized.csv \
    --workers 20
```

**Options:**
- `--input`: Path to standardized CSV
- `--output`: Output path (default: adds `_with_utci` suffix)
- `--workers`: Number of parallel API workers (default: 20)
- `--sample N`: Process only first N trips

**Output:**
Adds these columns to the input data:
- `utci_K`, `utci_C`: UTCI thermal comfort temperature
- `utci_timestamp`: Matched weather timestamp
- `wind_speed_10m`: Wind speed (m/s)
- `temperature_2m`: Air temperature (°C)
- `dewpoint_2m`: Dew point (°C)
- `prior_day_utci_avg_C`: Average UTCI for previous day
- `next_day_utci_avg_C`: Average UTCI for next day
- `prior_day_rain`, `next_day_rain`: Rain indicators

**Performance Notes:**
- Uses multithreading (20 workers by default)
- Includes disk caching to avoid redundant API calls
- Processing rate: ~30-50 trips/sec (depending on cache hits)
- Expected time for full NHTS dataset: ~5-8 hours
- May hit rate limits with high worker counts; cache helps on retries

### 3. visualize_pedestrian_vs_temperature.py

Creates visualizations of mode choice vs temperature.

**Usage:**
```bash
python scripts/travel_surveys/visualize_pedestrian_vs_temperature.py \
    --input data/transit_surveys/processed/nhts_2017_standardized_with_utci.csv \
    --output-dir outputs/travel_surveys \
    --bin-width 5
```

**Options:**
- `--input`: Path to CSV with UTCI data
- `--output-dir`: Output directory for plots
- `--bin-width`: Temperature bin width in °C (default: 5)

**Outputs:**
- `pedestrian_mode_vs_temperature.png`: Mode share by temperature (4 subplots)
- `temperature_distribution_by_mode.png`: Temperature distributions for each mode type

### 4. pipeline_nhts_analysis.py

Master pipeline script that runs all steps in sequence.

**Usage:**
```bash
# Full pipeline
python scripts/travel_surveys/pipeline_nhts_analysis.py --survey nhts_2017

# Test with sample
python scripts/travel_surveys/pipeline_nhts_analysis.py --sample 1000 --workers 10

# Skip already-completed steps
python scripts/travel_surveys/pipeline_nhts_analysis.py --skip-extraction --skip-utci
```

**Options:**
- `--survey`: Survey name (default: `nhts_2017`)
- `--skip-extraction`: Skip extraction step
- `--skip-utci`: Skip UTCI annotation step
- `--sample N`: Process only N trips (testing)
- `--workers N`: Parallel workers for UTCI (default: 20)

## Configuration

The pipeline is designed to be extensible to other surveys via `config/travel_survey_config.yaml`.

### Adding a New Survey

1. Extract survey data to `data/transit_surveys/<survey_name>/`
2. Add configuration section to `config/travel_survey_config.yaml`:

```yaml
my_survey_2023:
  name: "My Travel Survey 2023"
  data_dir: "data/transit_surveys/my_survey"
  trip_file: "trips.csv"

  fields:
    # Map survey columns to standard fields
    state_abbr: "STATE"
    date_field: "SURVEY_DATE"
    start_time: "START_TIME"
    transport_mode: "MODE"
    # ... etc

  walking_modes:
    full_walk: [5]  # Mode codes for walking
    contains_walk: [5, 10, 11]  # Modes with walk component

  mode_labels:
    1: "Car"
    5: "Walk"
    # ... etc
```

3. Run extraction:
```bash
python scripts/travel_surveys/extract_and_standardize.py --survey my_survey_2023
```

## Mode Classifications

The pipeline classifies trips into four categories:

1. **Full Walk** (`is_full_walk`): Entire trip was walking
   - NHTS code 20

2. **Contains Walk** (`contains_walk`): Trip involved walking
   - Walk (20), Public bus (8), Streetcar (10), Subway (11), Commuter rail (12), Paratransit (17)

3. **Full Pedestrian** (`is_full_pedestrian`): Entire trip was active transportation
   - Bicycle (18), E-scooter (19), Walk (20)

4. **Contains Pedestrian** (`contains_pedestrian`): Trip involved active modes
   - Same as "Contains Walk" plus Bicycle and E-scooter

## Example Workflow

### Full Analysis

```bash
# 1. Run complete pipeline
python scripts/travel_surveys/pipeline_nhts_analysis.py

# 2. Check outputs
ls -lh data/transit_surveys/processed/
ls -lh outputs/travel_surveys/
```

### Testing with Sample

```bash
# Test with 5000 trips
python scripts/travel_surveys/pipeline_nhts_analysis.py --sample 5000 --workers 10
```

### Individual Steps

```bash
# Step 1: Extraction
python scripts/travel_surveys/extract_and_standardize.py --survey nhts_2017

# Step 2: UTCI annotation
python scripts/travel_surveys/add_utci.py \
    --input data/transit_surveys/processed/nhts_2017_standardized.csv \
    --workers 15

# Step 3: Visualization
python scripts/travel_surveys/visualize_pedestrian_vs_temperature.py \
    --input data/transit_surveys/processed/nhts_2017_standardized_with_utci.csv
```

## Output Files

### Standardized Data
- **Location**: `data/transit_surveys/processed/`
- **Files**:
  - `nhts_2017_standardized.csv` - Cleaned trip data
  - `nhts_2017_standardized_with_utci.csv` - With thermal comfort data

### Visualizations
- **Location**: `outputs/travel_surveys/`
- **Files**:
  - `pedestrian_mode_vs_temperature.png` - Mode share trends
  - `temperature_distribution_by_mode.png` - Temp distributions

### Logs
- **Location**: `logs/`
- **Files**:
  - `nhts_standardization.log` - Extraction logs
  - `utci_annotation_<timestamp>.log` - UTCI annotation logs

## Dependencies

Required Python packages (in `.venv`):
- pandas
- numpy
- matplotlib
- seaborn
- pyyaml
- requests
- thermofeel
- diskcache
- tqdm
- openpyxl

Already available in existing environment.

## Known Limitations

1. **Geographic Precision**: NHTS data uses state centroids, not exact trip locations
   - UTCI values represent state-level conditions, not trip-specific microclimates
   - Acceptable for large-scale patterns but not fine-grained analysis
   - Flagged with `location_is_placeholder=True`

2. **Temporal Resolution**: NHTS date field is YYYYMM (month-only)
   - Script uses TRAVDAY (day of week) to select matching day from month
   - Random selection with seed=42 for reproducibility (household ID adds variation)
   - Reduces uncertainty to ±7 days (within-week variation) vs ±15 days
   - Time-of-day is accurate (HHMM format)
   - Flagged with `datetime_is_approximate=True`

3. **API Rate Limits**: ERA5 API (Open-Meteo) has rate limits
   - Reduce `--workers` if hitting 429 errors
   - Disk cache minimizes redundant requests
   - Cached data persists in `cache/era5_cache/`

4. **Walking Mode Representation**: Only 0.5% of NHTS trips are full pedestrian
   - Reflects U.S. car-centric travel patterns
   - Consider larger sample or targeted surveys for pedestrian analysis

## References

- **NHTS 2017**: https://nhts.ornl.gov/
- **ERA5 Reanalysis**: https://www.ecmwf.int/en/forecasts/datasets/reanalysis-datasets/era5
- **Open-Meteo Archive API**: https://open-meteo.com/en/docs/historical-weather-api
- **UTCI**: https://www.utci.org/
