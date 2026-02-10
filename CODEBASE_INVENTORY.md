# Codebase Inventory: sunny_day_SVI

## Project Overview
A comprehensive analysis of shade usage patterns across US metropolitan areas using street view imagery and travel survey data, with UTCI thermal comfort integration.

---

## 1. Metro Commute SVI Package

### Directory Structure
Location: `/home/kieran/Documents/Python/sunny_day_SVI/metro_commute_svi_package/`

### Files:
- **requirements.txt** (364 bytes)
- **run_pipeline.sh** (630 bytes) - Executable pipeline runner
- **README.md** (3.0 KB)
- **scripts/pipelines/sunny_shade_pipeline.py** (15 KB)
- **scripts/pipelines/metro_commute_svi_pipeline.py** (11 KB) - Main pipeline
- **scripts/data_collection/download_mly_points.py** (6.1 KB)
- **models/yolo_best.pt** (110 MB) - YOLO detection model
- **models/vit_binary.pth** (328 MB) - Vision transformer binary classifier

### Metro Cities Metadata (Commute-filtered, 8-10am & 4-6pm local time)
**19 metro areas covered**, organized as: `data/metro_cities_metadata/{city}/{city}_metadata_commute.csv`

#### CSV Structure (23 columns):
```
captured_at, compass_angle, creator_id, id, is_pano, sequence_id, organization_id,
bbox_west, bbox_south, bbox_east, bbox_north, place_id, osm_type, osm_id,
lat, lon, class, type, place_rank, importance, addresstype, name, display_name
```

#### City Breakdown:
| City | Size | Images |
|------|------|--------|
| Phoenix | 568.0 MB | Largest dataset |
| Los Angeles | 308.6 MB | |
| Boston | 138.0 MB | |
| Seattle | 191.1 MB | |
| San Francisco | 117.4 MB | |
| Atlanta | 91.1 MB | |
| Raleigh | 85.7 MB | |
| Denver | 61.9 MB | |
| Columbia | 56.9 MB | |
| Salt Lake City | 52.0 MB | |
| Louisville | 43.0 MB | |
| St. Louis | 34.8 MB | |
| Minneapolis | 31.0 MB | |
| Cleveland | 23.5 MB | |
| Anchorage | 11.7 MB | |
| Honolulu | 10.5 MB | |
| Boise | 10.3 MB | |
| Tucson | 6.2 MB | |
| Evansville | 4.6 MB | |

**IMPORTANT: None of these CSV files currently contain UTCI columns** - they only have MapillaryLocation metadata (coordinates, timestamps, imagery info).

Total Package Size: ~715 MB (tar.gz)

---

## 2. Transit Surveys (data/transit_surveys/processed/)

### Survey Files with Row Counts:

#### Main Survey Data:
1. **metro_surveys_standardized.csv** 
   - Rows: 182,420
   - Size: 24 MB
   - Columns (18): `survey, household_id, person_id, mode, time, day_of_week, zip, county, minute, survey_year, survey_month, datetime, walk_only, contains_walk, lat, lon, location_source, [baseline columns]`

2. **metro_surveys_standardized_with_utci.csv**
   - Rows: 182,420
   - Size: 35 MB
   - Columns (23): Adds UTCI + weather columns
   - Added Columns: `utci_K, utci_C, utci_timestamp, wind_speed_10m, temperature_2m, dewpoint_2m`

3. **metro_surveys_standardized_flexible_with_utci.csv**
   - Rows: 785,902
   - Size: 154 MB
   - Columns (23): Same as above (expanded survey coverage)

4. **metro_surveys_with_utci_checkpoint.csv**
   - Rows: Not listed (appears to be intermediate checkpoint)
   - Size: 30 MB
   - Columns (28): Checkpoint version WITH additional fields:
     - `prior_day_utci_avg_C, next_day_utci_avg_C, prior_day_rain, next_day_rain, hour` (in addition to base columns)

#### Recoverable Surveys:
5. **recoverable_surveys_with_utci.csv**
   - Rows: 335,671
   - Size: 67 MB
   - Columns (22): Survey records that were recoverable after initial processing
   - Columns: `survey, household_id, person_id, time_minutes, mode, day_of_week, lat, lon, county, hour, minute, survey_year, survey_month, utci_K, utci_C, utci_timestamp, wind_speed_10m, temperature_2m, dewpoint_2m, prior_day_utci_avg_C, next_day_utci_avg_C, prior_day_rain`

6. **recoverable_surveys_with_dates_coords.csv**
   - Rows: 60 MB
   - Similar to above with additional coordinate/date info

#### Raw/Merged Data:
7. **metro_surveys_raw_merged.csv** (7.4 MB, 182,420 rows)
8. **metro_surveys_raw_merged_flexible.csv** (88 MB)

#### Processed Output:
9. **nhts_2017_standardized_with_utci.csv** (19 KB - small summary)
10. **nhts_2017_standardized.csv** (110 MB - full NHTS 2017 data)
11. **nhts_2017_standardized_with_utci_checkpoint.csv** (120 MB)

#### Supporting Files:
- **person_day_trip_rates.csv** (11 MB)
- **p_walk_given_temp_population_exposure.csv** (1.6 KB)
- **p_walk_given_temp_final.csv** (1.2 KB)
- **excluded_survey_analysis.csv** (4.2 KB)
- **metro_survey_column_mappings.json** (2.2 KB)
- **metro_survey_column_mappings_flexible.json** (14 KB)
- **metro_surveys_skipped.json** (5.0 KB)
- **metro_surveys_skipped_flexible.json** (1.8 KB)
- **recovered_surveys_report.json** (3.0 KB)
- **recoverable_surveys_processing_log.json** (1.8 KB)
- **survey_locations.csv** (2.1 KB) - City-location mappings

---

## 3. UTCI Annotation Scripts

### Key Scripts:

#### 3a. **add_utci.py**
**File:** `/home/kieran/Documents/Python/sunny_day_SVI/scripts/travel_surveys/add_utci.py`

**Purpose:** Single-threaded UTCI annotation using enhanced_utci infrastructure

**Key Features:**
- Uses `enhanced_utci.get_enhanced_utci_data()` helper
- Multithreaded with up to 20 workers (configurable)
- Adds these columns to each trip:
  ```
  utci_K, utci_C, utci_timestamp,
  wind_speed_10m, temperature_2m, dewpoint_2m,
  prior_day_utci_avg_C, next_day_utci_avg_C,
  prior_day_rain, next_day_rain
  ```
- Rate: ~20 trips/sec with 20 workers
- Logs progress with ETA
- Graceful error handling with detailed logging

**Usage:**
```bash
python scripts/travel_surveys/add_utci.py \
  --input data/transit_surveys/processed/nhts_2017_standardized.csv \
  --output data/transit_surveys/processed/nhts_2017_standardized_with_utci.csv \
  --workers 20
```

#### 3b. **add_utci_bulk.py**
**File:** `/home/kieran/Documents/Python/sunny_day_SVI/scripts/travel_surveys/add_utci_bulk.py`

**Purpose:** Bulk batching with up to 100 locations per API call (~50x reduction in API calls)

**Key Features:**
- Batches up to 100 locations per Open-Meteo API call (tested successfully)
- Single worker to precisely control rate limiting
- BATCH_SIZE: 100 locations per API call
- INTER_BATCH_DELAY: 10 seconds between batches (respects 600 calls/min limit)
- Uses Open-Meteo customer archive API endpoint
- Deduplicates: Groups by unique (date + lat_rounded + lon_rounded)
- Checkpoint system: Saves every 50 batches
- Graceful interrupt handling with state preservation

**Algorithm:**
1. Identify unique date+location combinations
2. Group into batches of 100
3. For each batch, fetch ERA5 hourly data for prior/current/next day
4. Calculate UTCI from meteorological variables using thermofeel library
5. Extract daily averages and rainfall info
6. Join results back to original trips

**Efficiency:**
- API calls: ~1 call per 100 locations instead of 1 per location
- ~75% reduction in API calls vs naive approach

**Usage:**
```bash
python scripts/travel_surveys/add_utci_bulk.py \
  --input metro_surveys_standardized.csv \
  --batch-size 100 \
  --workers 1 \
  --resume
```

#### 3c. **add_utci_deduped.py**
**File:** `/home/kieran/Documents/Python/sunny_day_SVI/scripts/travel_surveys/add_utci_deduped.py`

**Purpose:** Deduplication approach - fetch unique combinations only then join back

**Key Features:**
- Creates unique keys from: date + hour + lat_rounded(2 decimals) + lon_rounded
- Reduces API calls by ~75% (only fetch unique combos once)
- Multithreaded with 20 workers
- Checkpoint every 1000 unique fetches
- INTER_CHUNK_DELAY: 5 seconds between chunks for rate limiting
- Graceful interrupt handling with resumable checkpoints
- Uses `get_enhanced_utci_data()` from enhanced_utci module

**Algorithm:**
1. Parse trips and identify unique date+hour+location combinations
2. Fetch UTCI data for each unique combo with multithreading
3. Save periodic checkpoints of fetched results
4. Join results back to all original trips (many trips → one unique combo)

**Result columns added:**
```
utci_K, utci_C, utci_timestamp,
wind_speed_10m, temperature_2m, dewpoint_2m
```
(Note: This version doesn't include prior/next day averages like add_utci_bulk.py does)

**Usage:**
```bash
python scripts/travel_surveys/add_utci_deduped.py \
  --input metro_surveys_standardized.csv \
  --output metro_surveys_standardized_with_utci.csv \
  --workers 20 \
  --checkpoint-interval 1000 \
  --resume
```

#### 3d. **add_utci_chunked.py**
**File:** `/home/kieran/Documents/Python/sunny_day_SVI/scripts/travel_surveys/add_utci_chunked.py`
(Exists but not fully reviewed)

#### Other Related Scripts:
- **prepare_recoverable_for_utci.py** - Prepares recoverable survey subset
- **scripts/processing/batch_add_enhanced_utci_optimized.py** - Optimized batch processing
- **scripts/processing/add_utci_to_multicity.py** - Multi-city UTCI annotation
- **scripts/processing/prep_multicity_for_utci.py** - Prepare multi-city data

---

## 4. Visualization & Analysis Scripts

### 4a. **calculate_person_probability_weights.py**
**File:** `/home/kieran/Documents/Python/sunny_day_SVI/scripts/visualization/calculate_person_probability_weights.py`

**Purpose:** Calculate inverse probability weights (IPW) to account for differential person presence based on temperature and time of day

**Key Functions:**

1. **calculate_person_probabilities(df)**
   - Input: DataFrame with `temperature, hour, has_person, person_count`
   - Calculates probabilities by:
     - 2°C temperature bins (filters bins with <10 observations)
     - Hour bins (0-23)
     - Combined probability assuming independence
   - Uses linear interpolation to smooth probabilities
   - Applies epsilon (0.001) to avoid division by zero
   - Normalizes weights to mean of 1.0
   - Caps extreme weights at 95th percentile for stability
   - Returns: Original DF + 6 weight columns

2. **prepare_data_with_weights(all_data)**
   - Combines multiple DataFrames from different cities
   - Standardizes column names (handles _x/_y suffixes)
   - Parses datetime from `datetime-local` column
   - Handles both `dbulb` and `utci_C` for temperature
   - Removes rows with missing temperature/hour
   - Returns combined DF with weights

3. **get_weight_statistics(df)**
   - Prints summary statistics for all IPW columns

**Output Columns:**
```
ipw_temp        - Inverse probability weight based on temperature
ipw_hour        - Inverse probability weight based on hour
ipw_combined    - Combined IPW (normalized, capped at 95th percentile)

Also includes:
prob_person_temp, prob_person_hour, prob_person_combined
```

**Data Requirements:**
- Must have: `inshade_count`, `outshade_count`, `is_sunny`, `temperature`, `hour`, `datetime-local`
- Optional: `dbulb` (preferred over `utci_C`)

### 4b. **visualize_shade_ratios_ipw.py**
**File:** `/home/kieran/Documents/Python/sunny_day_SVI/scripts/visualization/visualize_shade_ratios_ipw.py`

**Purpose:** Create IPW-weighted shade ratio visualizations comparing unweighted vs weighted analyses

**Key Features:**

1. **filter_extreme_values(df, temp_column='utci_C')**
   - Filters UTCI range: -50°C to 60°C
   - Removes invalid/extreme values

2. **calculate_shade_percentage_with_weights(df, weight_column=None)**
   - Filters for: sunny rows with valid shade counts and ≥1 person
   - Calculates: shade_percent = inshade_count / (inshade_count + outshade_count) * 100
   - Adds weight column (default: 1.0 if not specified)

3. **create_balanced_sample_with_weights(...)**
   - Balances datasets so each city has equal representation
   - Preserves IPW weights during sampling
   - Supports stratified resampling

4. **create_comparison_loess_plot(...)**
   - Creates side-by-side comparison: Unweighted vs IPW-Weighted
   - Left panel: Unweighted LOESS fit
   - Right panel: IPW-Weighted LOESS fit
   - Both with 95% bootstrap confidence intervals (100 bootstrap samples)
   - Plots: Temperature (UTCI) vs % in Shade

5. **create_weight_distribution_plot(...)**
   - Histograms of ipw_temp, ipw_hour, ipw_combined
   - Shows mean and median lines

6. **create_time_of_day_comparison(...)**
   - Same as temperature comparison but for Hour of Day (0-24)
   - Unweighted vs IPW-weighted LOESS

7. **load_city_data(data_dir)**
   - Loads all *_with_utci.csv files from directory
   - Extracts city name from filename
   - Calls `prepare_data_with_weights()` to add IPW columns
   - Prints weight statistics
   - Returns city_data dict split by city

**Output Files:**
- `ipw_weight_distributions.png` - Weight distribution histograms
- `ipw_utci_comparison_ipw_temp.png` - Temp-based IPW comparison
- `ipw_utci_comparison_ipw_hour.png` - Hour-based IPW comparison
- `ipw_utci_comparison_ipw_combined.png` - Combined IPW comparison
- `ipw_timeofday_comparison_ipw_*.png` - Time-of-day variants

**Data Directory:** `data/processed/city_estimate_outcomes/`

---

## 5. Generate Commute Filtered Metadata Script

**File:** `/home/kieran/Documents/Python/sunny_day_SVI/generate_commute_filtered_metadata.py`

**Purpose:** Filter MapillaryLocation metadata to only include commute-time images (8-10am & 4-6pm local time)

**Key Features:**

1. **City Timezone Mapping:** 19 US metro cities with their respective timezones
   - Eastern: Boston, Atlanta, Cleveland, Columbia, Raleigh, Louisville, Evansville
   - Central: Minneapolis, St. Louis, Denver (special: Denver uses Mountain)
   - Mountain: Denver, Salt Lake City, Phoenix, Tucson, Boise
   - Pacific: Los Angeles, San Francisco, Seattle
   - Alaska: Anchorage
   - Hawaii: Honolulu

2. **is_commute_hour(hour):** 
   - Returns True if hour in [8,9] (8-10am) or [16,17] (4-6pm)

3. **filter_city_metadata(csv_file, city_name, timezone_str, output_dir)**
   - Loads metadata CSV
   - Converts UTC `captured_at` to local time
   - Filters by commute hours
   - Saves filtered CSV to: `output_dir/{city}/{city}_metadata_commute.csv`
   - Returns stats: total images, filtered count, percentage

**Input:**
- Source: `data/metro_cities_svi_test/{city}/{city}_metadata.csv`

**Output:**
- Destination: `data/metro_cities_svi_commute/{city}/{city}_metadata_commute.csv`

**Processing:**
- Parses `captured_at` timestamp (UTC)
- Localizes to city timezone
- Extracts hour and filters
- Removes temporary timezone columns before saving

**Current Status:**
- Script has already been run - filtered CSVs exist in metro_commute_svi_package/

---

## 6. UTCI Annotation Status & Coverage

### Current State:

**UTCI Annotated Datasets (Ready to Use):**
1. ✓ **metro_surveys_standardized_with_utci.csv** (182,420 rows)
   - Full metro survey data with UTCI
   
2. ✓ **metro_surveys_standardized_flexible_with_utci.csv** (785,902 rows)
   - Expanded survey coverage with UTCI

3. ✓ **metro_surveys_with_utci_checkpoint.csv** (checkpoint version)
   - Includes prior/next day UTCI averages and rainfall

4. ✓ **recoverable_surveys_with_utci.csv** (335,671 rows)
   - Recovered survey records with UTCI

5. ✓ **nhts_2017_standardized_with_utci.csv** (19 KB - summary)
   - NHTS 2017 sample with UTCI

6. ✓ **nhts_2017_standardized_with_utci_checkpoint.csv** (120 MB)
   - Full NHTS 2017 data with UTCI

### NOT YET UTCI-ANNOTATED:

⚠️ **metro_commute_svi_package/** - Street view metadata CSVs
- All 19 cities have commute-filtered metadata (geographic/imagery info only)
- These contain: timestamp, lat/lon, MapillaryID, OSM place info
- NO UTCI columns in any city file
- Would need to annotate these to analyze shade usage by temperature

**To Annotate Metro Cities:**
Would need to:
1. Extract lat/lon from each metro city CSV
2. Run add_utci_bulk.py or add_utci_deduped.py on the timestamps
3. Add 6-10 UTCI columns to each city's CSV
4. Then can correlate shade observations with thermal comfort

---

## 7. API & Configuration

**File:** `/home/kieran/Documents/Python/sunny_day_SVI/config/config.json`

```json
{
  "api_key": "wP4YbYGM1pflDrtF",
  "monthly_limit": 5000000,
  "notes": "Open-Meteo commercial API - 5 million calls/month"
}
```

**API Details:**
- Provider: Open-Meteo
- Endpoint: `https://customer-archive-api.open-meteo.com/v1/era5`
- Hourly data: temperature_2m, dewpoint_2m, wind_speed_10m, precipitation
- Rate limit: 600 API calls/minute (~10 calls/sec max)
- Monthly limit: 5,000,000 API calls
- Supports: Bulk requests up to 100 locations per call

---

## 8. Enhanced UTCI Module

**File:** `/home/kieran/Documents/Python/sunny_day_SVI/scripts/utils/enhanced_utci.py`

**Key Functions:**
- `get_enhanced_utci_data(lat, lon, timestamp)` - Main entry point
- Fetches ERA5 hourly weather data
- Calculates UTCI from T, Td, wind speed
- Returns dict with: utci_K, utci_C, utci_timestamp, wind_speed_10m, temperature_2m, dewpoint_2m, prior_day_utci_avg_C, next_day_utci_avg_C, prior_day_rain, next_day_rain
- Uses thermofeel library for UTCI calculations

---

## Summary Table

| Category | Details |
|----------|---------|
| **Total Metro Cities** | 19 (largest: Phoenix 568 MB, smallest: Evansville 4.6 MB) |
| **Survey Records with UTCI** | 785,902 flexible + 182,420 standard = 968,322 rows |
| **Additional Recoverable Surveys** | 335,671 rows |
| **NHTS 2017 Data** | ~full dataset available with UTCI |
| **UTCI Scripts** | 3 main approaches (standard, bulk batch, deduped) |
| **IPW Capability** | Yes - calculate person probability weights by temp/hour |
| **Metro Metadata Status** | Commute-filtered but NOT UTCI-annotated yet |
| **API Provider** | Open-Meteo (5M calls/month limit) |
| **Models Included** | YOLO11s (110 MB) + ViT binary classifier (328 MB) |

