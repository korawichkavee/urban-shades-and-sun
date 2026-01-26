# Phoenix AZ SVI Data Collection - Quick Start

## What Was Delivered

All tasks from `phoenix_az_changes.txt` have been completed:

1. ✅ **Streamlined script** to fetch street view images (no walkable filtering)
2. ✅ **Time filtering** for 8-10am and 4-6pm local time
3. ✅ **Deployment script** for creating analysis tarballs
4. ✅ **Config system** for targeting cities
5. ✅ **Phoenix testing** completed successfully

## Test Results

- **Input:** 32,711 Mapillary images from Phoenix, AZ
- **Output:** 8,354 images (filtered to 8-10am or 4-6pm local time)
- **File:** `data/raw/svi_filtered/Phoenix_1840020568.csv` (1.7 MB)

## Quick Usage

### Option 1: Simple Test Script (Fast)

```bash
python3 test_phoenix_fetch.py
```

### Option 2: Full Script with Config (Recommended)

```bash
python3 scripts/data_collection/fetch_svi_with_time_filter.py config/phoenix_az.yaml
```

Both will:
- Fetch all Mapillary images for Phoenix
- Filter to 8-10am or 4-6pm Phoenix local time (MST/MDT)
- Save to `data/raw/svi_filtered/Phoenix_1840020568.csv`

### Configuration

Edit `config/phoenix_az.yaml` to change:
- Cities (add more city IDs or names)
- Date ranges
- Data sources (Mapillary/KartaView)
- Output directory

### Create Deployment Package

```bash
# Metadata only
bash deployment/prepare_svi_analysis.sh -c config/phoenix_az.yaml

# With image downloads
bash deployment/prepare_svi_analysis.sh -c config/phoenix_az.yaml -d
```

## Output Format

The CSV includes:
- `id`: Mapillary image ID
- `captured_at`: Unix timestamp (ms)
- `datetime_utc`: UTC datetime
- `datetime_local`: Phoenix local time with timezone
- `hour`: Local hour (8, 9, 16, or 17)
- `lat`, `lon`: Image coordinates
- `sequence_id`: Sequence identifier
- `city_id`: City ID (1840020568 for Phoenix)
- `source`: 'Mapillary' or 'KartaView'

## Files Created

```
├── config/phoenix_az.yaml                    # Configuration
├── data/raw/worldcities.csv                  # City database
├── data/raw/svi_filtered/
│   └── Phoenix_1840020568.csv               # Filtered output
├── deployment/prepare_svi_analysis.sh       # Deployment packager
├── test_phoenix_fetch.py                    # Working test script
├── PHOENIX_IMPLEMENTATION_SUMMARY.md        # Detailed docs
└── PHOENIX_QUICKSTART.md                    # This file
```

## Next Steps

1. **Verify the data:** Check `data/raw/svi_filtered/Phoenix_1840020568.csv`
2. **Add more cities:** Edit `config/phoenix_az.yaml`
3. **Download images:** Add image download logic or use `-d` flag
4. **Deploy to remote:** Use `prepare_svi_analysis.sh` to create tarball

## Notes

- Working test script: `test_phoenix_fetch.py`
- Timezone detection is automatic (America/Phoenix)
- Time windows are exclusive: 8:00-9:59am and 4:00-5:59pm
- All required packages already installed in .venv
