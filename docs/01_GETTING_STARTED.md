# Getting Started with Sunny Day SVI Project

## Project Overview

This project analyzes street view imagery (SVI) to understand how people respond to heat by seeking shade. It combines:
- Street view image downloads (Mapillary/KartaView)
- Weather data enrichment (UTCI thermal comfort indices)
- Computer vision (YOLO object detection for people/shadows)
- Statistical analysis of shade-seeking behavior

## Quick Start

### 1. Environment Setup

```bash
cd /home/kieran/Documents/Python/sunny_day_SVI

# Install dependencies
pip install -r requirements.txt

# Set up Mapillary API token (if not already configured)
# Token is embedded in scripts - see scripts/data_collection/download_*.py
```

### 2. Key Directories

- **`data/`** - All data files (raw downloads, processed datasets)
- **`scripts/`** - Processing scripts organized by function
- **`outputs/`** - Generated plots and trained models
- **`notebooks/`** - Jupyter notebooks for analysis
- **`tests/`** - Test scripts to validate functionality
- **`logs/`** - Processing logs with timestamps

### 3. Typical Workflow

```bash
# 1. Download street view imagery for hot cities
python scripts/data_collection/download_hot_cities.py

# 2. Add weather data (UTCI) to the images
python batch_add_enhanced_utci_optimized.py

# 3. Run ML pipeline (classify sunny/shade, detect people)
python scripts/pipelines/hot_cities_full_pipeline.py

# 4. Generate visualizations
python scripts/visualization/visualize_shade_ratios.py
```

## Project Structure

See [PROJECT_STRUCTURE.md](../PROJECT_STRUCTURE.md) for complete directory layout.

## Core Concepts

### UTCI (Universal Thermal Climate Index)
- Accounts for temperature, humidity, wind speed, and radiation
- More accurate than simple temperature for perceived heat
- Calculated using ERA5 reanalysis data

### Shade-Seeking Behavior
- Measured as ratio: people_in_shade / total_people
- Analyzed against multiple temperature measures
- Per-city and cross-city comparisons

### Data Flow
1. **Raw downloads** → `data/raw/`
2. **Weather enrichment** → Adds UTCI columns
3. **ML processing** → Adds people/shadow annotations
4. **Analysis** → `outputs/plots/`

## Next Steps

- See [02_DATA_COLLECTION.md](02_DATA_COLLECTION.md) for downloading data
- See [03_PROCESSING.md](03_PROCESSING.md) for data processing pipelines
- See [04_MACHINE_LEARNING.md](04_MACHINE_LEARNING.md) for ML workflows
- See [05_VISUALIZATION.md](05_VISUALIZATION.md) for generating plots

## Common Commands

```bash
# Check for running batch jobs
tmux list-sessions

# View recent logs
tail -f logs/utci_batch_*.log

# View processed data
head data/processed/city_estimate_outcomes/*_with_utci.csv

# Run tests
python tests/batch_add_enhanced_utci_test.py
```

## Troubleshooting

- **API rate limits**: Open-Meteo and Mapillary have rate limits. Scripts include retry logic.
- **Long processing times**: Use tmux sessions for overnight jobs (see `deployment/` folder)
- **Memory issues**: Batch processing scripts save progress incrementally
- **Path errors**: Check that files are in expected locations per PROJECT_STRUCTURE.md

## Support

- Check `logs/` directory for detailed error messages
- Review existing documentation in `docs/` folder
- Examine test scripts in `tests/` for examples
