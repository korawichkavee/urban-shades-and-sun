# Project Structure

## Directory Organization

```
sunny_day_SVI/
├── README.md                               # Project overview
├── batch_add_enhanced_utci_optimized.py    # Active: UTCI processing script
├── batch_add_enhanced_utci.py              # Active: UTCI processing script
├── batch_add_utci.py                       # Active: UTCI processing script (simple version)
├── enhanced_utci.py                        # Active: Enhanced UTCI data collection module
├── quickhotpoint2.py                       # Active: UTCI calculation utilities
│
├── data/                                   # All data files
│   ├── cache/                             # API response cache
│   ├── processed/                         # Processed datasets
│   │   └── city_estimate_outcomes/       # City analysis results with UTCI
│   └── raw/                               # Raw downloaded data
│       ├── city7sample/                   # Sample city data
│       ├── hot_cities/                    # Hot cities dataset
│       ├── mapillary_city_data/          # Mapillary downloads
│       ├── finetuning_yolo_test_imgs/    # YOLO test images
│       ├── hot_imgs_whole/               # Complete hot city images
│       └── *.csv                          # Raw CSV files
│
├── scripts/                               # All processing scripts
│   ├── data_collection/                  # Download and collection
│   │   ├── download_*.py                 # Various data downloaders
│   │   ├── nas_download_svi.py          # NAS street view download
│   │   ├── map_hot_cities.py            # City mapping
│   │   └── copy_walkable_images.py      # Image management
│   │
│   ├── processing/                       # Data processing pipelines
│   │   ├── add_weather_*.py             # Weather data enrichment
│   │   ├── process_*.py                 # Various processors
│   │   ├── filter_*.py                  # Data filtering
│   │   ├── enrich_*.py                  # Data enrichment
│   │   ├── append_osmnx.py              # OSM data integration
│   │   ├── analyze_temperature_adjustments.py
│   │   └── hourly_weather_finder.py
│   │
│   ├── visualization/                    # Plotting and visualization
│   │   └── visualize_shade_ratios.py    # Shade analysis plots
│   │
│   ├── ml/                               # Machine learning
│   │   ├── binary_image_*.py            # Binary classification
│   │   ├── *yolo*.py                    # YOLO model scripts
│   │   ├── evaluate_yolo_model.py       # Model evaluation
│   │   ├── prepare_yolo_dataset.py      # Dataset preparation
│   │   └── convert_json_to_yolo.py      # Format conversion
│   │
│   └── pipelines/                        # End-to-end pipelines
│       ├── hot_cities_full_pipeline.py  # Complete hot cities workflow
│       ├── sunny_shade_pipeline*.py     # Shade analysis pipelines
│       └── prelim_filtering_tmux.py     # Preliminary filtering
│
├── notebooks/                            # Jupyter notebooks
│   ├── 02_metadata.ipynb                # Metadata analysis
│   ├── 10_osm.ipynb                     # OSM data exploration
│   ├── prelim_data_analysis.ipynb       # Preliminary analysis
│   └── *.ipynb                          # Other analysis notebooks
│
├── outputs/                              # Generated outputs
│   ├── plots/                           # Visualization outputs
│   │   ├── overall_loess_*.png         # LOESS regression plots
│   │   ├── people_count_*.png          # People count analyses
│   │   └── shade_ratio_*.png           # Shade ratio plots
│   │
│   └── models/                          # Trained models
│       ├── sunny_batch_train*/         # Training runs
│       ├── vit_binary.pth              # ViT binary classifier
│       ├── yolo11*.pt                  # YOLO pretrained weights
│       ├── YOLO/                       # YOLO model files
│       └── SAM2/                       # Segment Anything model
│
├── tests/                               # Test scripts
│   ├── batch_add_*_test.py            # Batch processing tests
│   └── test_*.py                       # Unit tests
│
├── deployment/                          # Deployment configurations
│   ├── run_utci_tmux.sh               # UTCI batch processing launcher
│   ├── run_*_tmux.sh                  # Other tmux launchers
│   ├── create_*_deployment.sh         # Deployment packagers
│   └── setup.sh                       # Environment setup
│
├── logs/                                # Processing logs
│   ├── utci_batch_*.log               # UTCI processing logs
│   ├── hot_cities_*.log               # Hot cities logs
│   └── *.log                           # Other processing logs
│
├── docs/                                # Documentation
│   ├── AGENTS.md                       # Agent instructions
│   ├── FORECAST_DATA_NOTE.md          # Forecast data notes
│   ├── WEATHER_PROCESSING_README.md   # Weather processing guide
│   ├── REORGANIZATION_PLAN.md         # This reorganization plan
│   ├── LICENSE                         # Project license
│   └── *.txt                           # Other documentation
│
└── archive/                             # Deprecated/old files
```

## Key Files

### Active Processing Scripts (Root Level)
These remain in the root for easy access during active development:
- `batch_add_enhanced_utci_optimized.py` - Multithreaded UTCI batch processor with ETA
- `enhanced_utci.py` - Enhanced UTCI data collection (current + prior/next day)
- `quickhotpoint2.py` - UTCI calculation utilities

### Data Flow
1. **Raw data** → `data/raw/` (downloads, original CSVs)
2. **Processing** → Uses scripts in `scripts/` directories
3. **Processed data** → `data/processed/city_estimate_outcomes/`
4. **Visualizations** → `outputs/plots/`
5. **Models** → `outputs/models/`

### Logs
All processing logs are stored in `logs/` with timestamps for tracking batch jobs.

## Important Notes

### Path Updates Required
If scripts reference hardcoded paths, they may need updates:
- `city_estimate_outcomes/` → `data/processed/city_estimate_outcomes/`
- `plots/` → `outputs/plots/`
- `cache/` → `data/cache/`

### Active Batch Jobs
Always check for running tmux sessions before moving files:
```bash
tmux list-sessions
```

## Maintenance

- Keep root directory clean - only active development files
- Move completed scripts to appropriate `scripts/` subdirectories
- Archive old/deprecated scripts to `archive/`
- Document major changes in `docs/`
