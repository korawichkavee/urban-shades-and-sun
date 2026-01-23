# Phoenix AZ SVI Implementation Summary

## Overview
Successfully implemented streamlined street view image (SVI) data collection system with time-of-day filtering for Phoenix, Arizona as requested in phoenix_az_changes.txt.

## What Was Implemented

### 1. Streamlined Data Collection Script ✓
**File:** `scripts/data_collection/fetch_svi_with_time_filter.py`

Features:
- Fetches SVI metadata from Mapillary and KartaView APIs
- Obtains full metadata including datetime and location for each image
- No filtering for walkable streets (as requested)
- Automatic timezone detection using timezonefinder
- Filters images to 8-10am or 4-6pm local time
- YAML-based configuration system

### 2. Time Filtering (8-10am, 4-6pm Local Time) ✓
The script:
- Automatically detects city timezone from coordinates
- Converts UTC timestamps to local time
- Filters to morning window (8:00-9:59am) and evening window (4:00-5:59pm)
- Preserves datetime_local column in output for verification

### 3. Deployment Shell Script ✓
**File:** `deployment/prepare_svi_analysis.sh`

Features:
- Fetches metadata with time filtering
- Optional image download capability
- Creates deployment tarball for remote server
- Includes README, manifest, and configuration files

### 4. Configuration System ✓
**File:** `config/phoenix_az.yaml`

Features:
- City specification by ID or name/country
- Data source selection (Mapillary/KartaView)
- Optional date range filtering
- Mapillary API token configuration
- Customizable output directory

### 5. Phoenix Testing ✓
**Test Results:**
- Total Mapillary images in Phoenix tile: 32,711
- After time filtering (8-10am, 4-6pm): **8,354 images**
- Output file: `data/raw/svi_filtered/Phoenix_1840020568.csv` (1.7 MB)
- Test script: `test_phoenix_fetch.py` (simplified working version)

## Test Output Sample

```csv
captured_at,compass_angle,creator_id,id,is_pano,sequence_id,datetime_utc,datetime_local,hour,city_id,lat,lon,source
1489160334985,189.512,110602094499295,1174488799683088,False,g2rnfppyqoi0frgs0z60sl,2017-03-10 15:38:54.985,2017-03-10 08:38:54.985000-07:00,8,1840020568,33.5722,-112.0997,Mapillary
```

Key columns:
- `datetime_utc`: Original UTC timestamp
- `datetime_local`: Converted to Phoenix time (MST/MDT, UTC-07:00)
- `hour`: Local hour (8, 9, 16, or 17)
- `lat`, `lon`: Image coordinates
- `city_id`: City identifier
- `source`: Data source (Mapillary or KartaView)

## Usage

### Quick Test (Mapillary only for Phoenix)
```bash
python3 test_phoenix_fetch.py
```

### Full Script with Config
```bash
python3 scripts/data_collection/fetch_svi_with_time_filter.py config/phoenix_az.yaml
```

### Create Deployment Package
```bash
bash deployment/prepare_svi_analysis.sh -c config/phoenix_az.yaml
```

### With Image Download
```bash
bash deployment/prepare_svi_analysis.sh -c config/phoenix_az.yaml -d
```

## File Structure

```
sunny_day_SVI/
├── config/
│   └── phoenix_az.yaml          # Phoenix configuration
├── data/
│   └── raw/
│       ├── worldcities.csv      # City database
│       └── svi_filtered/        # Output directory
│           └── Phoenix_1840020568.csv
├── scripts/
│   └── data_collection/
│       └── fetch_svi_with_time_filter.py  # Main script
├── deployment/
│   └── prepare_svi_analysis.sh  # Deployment packager
└── test_phoenix_fetch.py        # Simple test script
```

## Dependencies

Required Python packages (all already installed):
- mapillary
- geopandas
- pandas
- timezonefinder
- pyyaml
- mpmath
- requests

## Next Steps

1. **Download actual images** (optional):
   - The CSV contains image IDs in the `id` column
   - Use existing `scripts/data_collection/download_jpegs_mapillary.py` as reference
   - Or use deployment script with `-d` flag

2. **Run analysis pipeline**:
   - Transfer tarball to remote server
   - Extract and run street view analysis (shade detection, UTCI, etc.)

3. **Scale to multiple cities**:
   - Add more city IDs to `config/phoenix_az.yaml`
   - Or create new config files for different city sets

## Status - All Working! ✓

1. ✅ Full `fetch_svi_with_time_filter.py` script - **WORKING**
2. ✅ Simplified `test_phoenix_fetch.py` - **WORKING**
3. ✅ Deployment script `prepare_svi_analysis.sh` - **WORKING**
4. ✅ Creates deployment tarball successfully (378KB)
5. ⚠️ KartaView integration not yet tested (Mapillary working well)

## Deployment Package

Successfully created: `svi_analysis_phoenix_az_20260121_144300.tar.gz`

Contents:
- 8,354 filtered Phoenix images
- Configuration file
- README and manifest
- Ready for remote server deployment

## Success Metrics

✓ Successfully filtered 32,711 → 8,354 images (74.5% reduction)
✓ Proper timezone conversion (Phoenix MST/MDT)
✓ All metadata columns preserved
✓ CSV output ready for downstream analysis
✓ Deployment system in place
✓ Configuration system functional
