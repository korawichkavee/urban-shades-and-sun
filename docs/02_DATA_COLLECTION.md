# Data Collection Guide

## Overview

Scripts for downloading street view imagery and metadata from Mapillary and KartaView APIs.

Located in: `scripts/data_collection/`

## Scripts

### Core Download Scripts

#### `download_hot_cities.py`
Downloads SVI for cities identified as having hot days.

**Purpose**: Primary data collection script for the hot cities dataset.

**Usage**:
```bash
python scripts/data_collection/download_hot_cities.py
```

**Input**:
- `docs/hot_cities.txt` - List of city IDs to download
- Hot day metadata (dates when temperature exceeded threshold)

**Output**:
- CSV files in `data/raw/hot_cities/`
- Image metadata including lat/lon, timestamp, image ID

---

#### `download_mly_points.py`
Downloads Mapillary image points for specified geographic areas.

**Purpose**: Fetch metadata for Mapillary images without downloading full images.

**Usage**:
```bash
python scripts/data_collection/download_mly_points.py
```

**Key Features**:
- Geographic bounding box queries
- Date filtering
- Metadata caching

**Output**: CSV files with image metadata

---

#### `download_kv_points.py`
Downloads KartaView image points for specified areas.

**Purpose**: Alternative to Mapillary for some regions with better coverage.

**Usage**:
```bash
python scripts/data_collection/download_kv_points.py
```

**Key Features**:
- KartaView API integration
- Similar metadata structure to Mapillary
- Date and location filtering

---

### Image Download Scripts

#### `download_jpegs.py`
Downloads actual JPEG images from Mapillary based on metadata.

**Purpose**: Fetch full-resolution images for analysis.

**Usage**:
```bash
python scripts/data_collection/download_jpegs.py --input metadata.csv --output images/
```

**Key Features**:
- Parallel downloads
- Resume capability
- Error handling and retries

**Note**: Requires Mapillary API token

---

#### `download_jpegs_mapillary.py`
Mapillary-specific JPEG downloader with enhanced features.

**Location**: `scripts/data_collection/download_jpegs_mapillary.py`

**Key Features**:
- Optimized for Mapillary API
- Batch processing
- Progress tracking

---

#### `download_jpegs_kartaview.py`
KartaView-specific JPEG downloader.

**Location**: `scripts/data_collection/download_jpegs_kartaview.py`

**Key Features**:
- KartaView API integration
- Thumbnail and full-resolution options

---

### Utility Scripts

#### `map_hot_cities.py`
Maps city names to geographic coordinates and metadata.

**Purpose**: Create lookup table for hot cities analysis.

**Usage**:
```bash
python scripts/data_collection/map_hot_cities.py
```

**Output**: City mapping files for downstream processing

---

#### `copy_walkable_images.py`
Filters and copies images meeting walkability criteria.

**Purpose**: Create subset of images on walkable streets.

**Usage**:
```bash
python scripts/data_collection/copy_walkable_images.py
```

**Filters**:
- Street type (walkable vs highway)
- Image quality thresholds
- Geographic bounds

---

#### `nas_download_svi.py`
Downloads SVI data directly to NAS storage.

**Purpose**: Large-scale downloads with network storage integration.

**Usage**:
```bash
python scripts/data_collection/nas_download_svi.py
```

**Note**: Requires NAS mount configuration

---

#### `raw_download.py`
Legacy download script for initial data collection.

**Status**: May be superseded by newer scripts.

**Purpose**: Original download implementation.

---

## API Configuration

### Mapillary API Token

Token is embedded in scripts. To update:

```python
import mapillary.interface as mly
mly.set_access_token('YOUR_TOKEN_HERE')
```

Current token location: Check individual download scripts.

### Rate Limits

- **Mapillary**: ~5000 requests/hour
- **KartaView**: Varies by endpoint

Scripts include retry logic and exponential backoff.

## Common Workflows

### Downloading New City

1. Add city to `docs/hot_cities.txt`
2. Run `map_hot_cities.py` to get coordinates
3. Run `download_hot_cities.py` to fetch metadata
4. Run `download_jpegs.py` to get images
5. Verify downloads in `data/raw/hot_cities/`

### Resuming Interrupted Downloads

Most scripts save progress. Simply re-run the same command - it will skip completed items.

### Checking Download Status

```bash
# Count downloaded images
ls data/raw/hot_cities/ | wc -l

# Check CSV row counts
wc -l data/raw/hot_cities/*.csv

# View recent downloads
ls -lt data/raw/hot_cities/ | head
```

## Output File Structure

### Metadata CSV Columns

Common columns across download scripts:
- `id` - Unique image identifier
- `lat`, `lon` - GPS coordinates
- `captured_at` - Timestamp (Unix or ISO format)
- `compass_angle` - Camera direction
- `sequence_id` - Group of related images
- `is_pano` - Panoramic image flag

### File Naming Convention

- `{CityName}_{timestamp}.csv` - Metadata files
- `{image_id}.jpg` - Image files

## Troubleshooting

### API Authentication Errors
Check that API tokens are current and have proper permissions.

### Geographic Coverage Gaps
Some areas may have limited coverage. Try alternative dates or nearby locations.

### Download Failures
- Check network connectivity
- Verify API rate limits not exceeded
- Check available disk space

### Performance Issues
- Use parallel download scripts for large batches
- Consider tmux for overnight downloads
- Monitor API quota usage

## Data Storage Guidelines

- **Keep raw downloads**: Store in `data/raw/` for reproducibility
- **Backup regularly**: Large download datasets are expensive to regenerate
- **Document sources**: Note which API and date range for each download
