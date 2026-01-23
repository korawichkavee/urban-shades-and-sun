# Data Processing Guide

## Overview

Scripts for enriching raw street view imagery with weather data, temporal information, and geographic context.

Located in: `scripts/processing/`

## Core Processing Scripts

### Weather Data Enrichment

#### `add_weather_data.py`
Adds basic weather variables to image metadata.

**Purpose**: Enrich images with temperature, humidity, and precipitation data.

**Usage**:
```bash
python scripts/processing/add_weather_data.py --input data/raw/city.csv
```

**Data Source**: Meteostat API

**Output Columns**:
- `wbulb` - Wet bulb temperature (°C)
- `dbulb` - Dry bulb temperature (°C)
- `tsun` - Sunshine duration (minutes)
- `rhum` - Relative humidity (%)

**Processing Time**: ~2 seconds per image (API calls)

---

#### `add_weather_overnight.py`
Overnight batch version with checkpointing.

**Purpose**: Process large datasets with resume capability.

**Usage**:
```bash
./deployment/run_weather_tmux.sh
# Or directly:
python scripts/processing/add_weather_overnight.py
```

**Features**:
- Progress checkpointing every 50 rows
- Tmux-compatible for background processing
- Detailed logging

See [WEATHER_PROCESSING_README.md](WEATHER_PROCESSING_README.md) for detailed instructions.

---

### UTCI Processing (Root Level)

These active development scripts are in the project root for easy access.

#### `batch_add_utci.py`
Simple UTCI batch processor.

**Purpose**: Add basic UTCI temperature data.

**Usage**:
```bash
python batch_add_utci.py
```

**Output Columns**:
- `utci_kelvin` - UTCI temperature in Kelvin
- `utci_celsius` - UTCI temperature in Celsius

**Dependencies**: `quickhotpoint2.py` for UTCI calculation

---

#### `batch_add_enhanced_utci.py`
Enhanced UTCI with multi-day context.

**Purpose**: Add UTCI plus prior/next day averages and precipitation.

**Usage**:
```bash
python batch_add_enhanced_utci.py
```

**Output Columns**:
- `utci_kelvin`, `utci_celsius` - Current UTCI
- `utci_prior_day_avg` - Previous day average UTCI
- `utci_next_day_avg` - Next day average UTCI
- `prior_day_rain` - Boolean: rain >1mm previous day
- `next_day_rain` - Boolean: rain >1mm next day

**Processing Time**: ~0.5-1 second per row (single-threaded)

**Dependencies**:
- `enhanced_utci.py` - Core UTCI fetch logic
- `quickhotpoint2.py` - UTCI calculations

---

#### `batch_add_enhanced_utci_optimized.py` ⭐ RECOMMENDED
Multithreaded version with 10x speedup.

**Purpose**: Fast UTCI processing for large datasets.

**Usage**:
```bash
# Test first (recommended)
python tests/batch_add_enhanced_utci_test.py

# Full run
python batch_add_enhanced_utci_optimized.py

# Or via tmux for overnight
./deployment/run_utci_tmux.sh
```

**Performance**:
- 10 concurrent workers
- ~100 rows/second (with cache hits)
- Geographic/temporal caching

**Features**:
- Progress bar with ETA
- Comprehensive logging to `logs/`
- Automatic cache management

**Example Output**:
```
Processing: 100%|████████████| 234000/234000 [37:00<00:00, 107.00 rows/s]
```

---

### Temporal Enrichment

#### `enrich_hot_cities_datetime.py`
Adds timezone-aware datetime columns.

**Purpose**: Convert Unix timestamps to local time with timezone info.

**Usage**:
```bash
python scripts/processing/enrich_hot_cities_datetime.py
```

**Output Columns**:
- `local_datetime` - Timezone-aware datetime
- `timezone` - IANA timezone string
- `hour_of_day` - Hour (0-23)
- `time_of_day` - Category: morning/afternoon/evening

---

#### `time_metadata_enrichment.py`
Legacy temporal enrichment script.

**Status**: May be superseded by `enrich_hot_cities_datetime.py`.

---

#### `hourly_weather_finder.py`
Finds weather data for specific hours.

**Purpose**: Match image timestamps to hourly weather observations.

**Usage**:
```bash
python scripts/processing/hourly_weather_finder.py
```

---

### Geographic Context (OSM Integration)

#### `append_osmnx.py`
Adds OpenStreetMap street network data.

**Purpose**: Enrich images with street type, width, surface type.

**Usage**:
```bash
python scripts/processing/append_osmnx.py --input city.csv
```

**Output Columns**:
- `highway` - OSM highway classification
- `width` - Street width (meters)
- `surface` - Surface type (asphalt, concrete, etc.)
- `lanes` - Number of lanes

**Processing Time**: Varies by city size, uses local OSM cache.

---

#### `process_all_cities_osm.py`
Batch OSM processing for multiple cities.

**Purpose**: Add OSM data to all cities in dataset.

**Usage**:
```bash
python scripts/processing/process_all_cities_osm.py
```

---

#### `process_hot_cities_osm.py`
OSM processing specifically for hot cities dataset.

**Purpose**: Optimized for hot cities workflow.

**Usage**:
```bash
python scripts/processing/process_hot_cities_osm.py
```

---

### Filtering Scripts

#### `filter_walkable_streets.py`
Filters images to walkable street types only.

**Purpose**: Remove highways, private roads, and non-walkable areas.

**Usage**:
```bash
python scripts/processing/filter_walkable_streets.py
```

**Criteria**:
- OSM highway types: residential, pedestrian, footway, path
- Excludes: motorway, trunk, motorway_link
- Quality thresholds

---

#### `filter_hot_cities_walkable.py`
Hot cities-specific walkability filter.

**Purpose**: Apply walkability criteria to hot cities dataset.

**Usage**:
```bash
python scripts/processing/filter_hot_cities_walkable.py
```

---

#### `add_weather_to_walkable.py`
Combines walkability filtering with weather enrichment.

**Purpose**: Single-step walkable streets + weather data.

**Usage**:
```bash
python scripts/processing/add_weather_to_walkable.py
```

---

### Utility Scripts

#### `unpack_data_csv.py`
Unpacks compressed or complex CSV structures.

**Purpose**: Normalize CSV format for downstream processing.

---

#### `process_walkable_cities.py`
Batch processing for walkable cities analysis.

**Purpose**: Full processing pipeline for walkability analysis.

---

#### `analyze_temperature_adjustments.py`
Analyzes temperature adjustments and corrections.

**Purpose**: Quality control and validation of weather data.

**Usage**:
```bash
python scripts/processing/analyze_temperature_adjustments.py
```

**Output**: Statistical summaries and diagnostic plots.

---

## Core Modules (Root Level)

### `quickhotpoint2.py`
UTCI calculation utilities.

**Purpose**: Core thermal comfort calculations.

**Functions**:
- `calculate_utci()` - Compute UTCI from weather params
- `_fetch_era5_hourly()` - ERA5 API interface with caching

**Data Source**: Open-Meteo ERA5 archive API

---

### `enhanced_utci.py`
Multi-day UTCI data collection.

**Purpose**: Enhanced UTCI with temporal context.

**Functions**:
- `get_enhanced_utci_data()` - Fetch current + prior/next day
- `_fetch_era5_multi_day()` - Multi-day ERA5 queries
- Cache management

**Key Features**:
- 3-day data windows (prior, current, next)
- Precipitation detection
- Intelligent coordinate rounding for cache hits

---

## Common Workflows

### Full Processing Pipeline

```bash
# 1. Add basic weather
python scripts/processing/add_weather_data.py

# 2. Add UTCI (optimized)
python batch_add_enhanced_utci_optimized.py

# 3. Add OSM context
python scripts/processing/append_osmnx.py

# 4. Filter to walkable streets
python scripts/processing/filter_walkable_streets.py

# 5. Add temporal enrichment
python scripts/processing/enrich_hot_cities_datetime.py
```

### Testing Before Full Run

Always test on small samples first:

```bash
# Test UTCI processing
python tests/batch_add_enhanced_utci_test.py

# Test weather addition
python tests/test_weather_sample.py
```

### Monitoring Long-Running Jobs

```bash
# Attach to tmux session
tmux attach -t utci_processing

# View logs in real-time
tail -f logs/utci_batch_*.log

# Check progress
wc -l data/processed/city_estimate_outcomes/*.csv
```

## Performance Tips

### UTCI Processing
- Use `batch_add_enhanced_utci_optimized.py` for 10x speedup
- Cache hits dramatically improve performance
- Process geographically/temporally clustered data together

### Weather Enrichment
- API calls are the bottleneck (~2 sec/image)
- Use tmux for overnight processing
- Progress saved every 50 rows

### OSM Integration
- First run downloads OSM data (slow)
- Subsequent runs use cache (fast)
- Process by city for better cache utilization

## Output File Locations

- **Processed data**: `data/processed/city_estimate_outcomes/`
- **Logs**: `logs/`
- **Checkpoints**: Root directory (`.checkpoint` files)

## Troubleshooting

### API Errors
- **Meteostat**: No historical data for location → Try nearby station
- **Open-Meteo ERA5**: Rate limit → Add delays between batches
- **OSM**: Area too large → Process smaller geographic bounds

### Performance Issues
- Long processing times → Use optimized scripts
- Memory usage → Process in batches, clear cache periodically
- Cache misses → Check coordinate rounding settings

### Data Quality
- Missing weather data → Check station availability
- UTCI outliers → Validate input weather parameters
- Timestamp mismatches → Check timezone handling

## Data Quality Checks

```bash
# Check for missing UTCI values
python -c "import pandas as pd; df = pd.read_csv('city_with_utci.csv'); print(df['utci_celsius'].isna().sum())"

# Validate temperature ranges
python scripts/processing/analyze_temperature_adjustments.py

# Check processing logs
grep -i error logs/utci_batch_*.log
```
