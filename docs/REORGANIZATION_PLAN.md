# Project Reorganization Plan

## Proposed Directory Structure

```
sunny_day_SVI/
├── scripts/                    # Active processing scripts
│   ├── data_collection/        # Download and collection scripts
│   ├── processing/             # Data processing pipelines
│   ├── visualization/          # Plotting and visualization
│   └── ml/                     # Machine learning scripts
├── notebooks/                  # Jupyter notebooks
├── data/                       # Data storage
│   ├── raw/                    # Raw downloaded data
│   ├── processed/              # Processed datasets
│   └── cache/                  # API cache
├── outputs/                    # Generated outputs
│   ├── plots/                  # Visualization outputs
│   └── models/                 # Trained models
├── tests/                      # Test scripts
├── deployment/                 # Deployment configurations
├── logs/                       # Processing logs
├── docs/                       # Documentation
└── archive/                    # Deprecated/old scripts
```

## Files NOT to Move (Active Batch Process)
- batch_add_enhanced_utci_optimized.py
- enhanced_utci.py
- quickhotpoint2.py
- city_estimate_outcomes/ (being processed)
- logs/ (being written)

## Migration Strategy
1. Create directory structure
2. Move files by category
3. Update any import paths if needed
4. Create symlinks for critical files if necessary
5. Update documentation

## Categories

### Data Collection Scripts
- download_*.py
- nas_download_svi.py
- map_hot_cities.py

### Processing Scripts
- add_weather_*.py
- process_*.py
- filter_*.py
- enrich_*.py
- append_osmnx.py
- analyze_temperature_adjustments.py

### Visualization Scripts
- visualize_shade_ratios.py
- Any plotting scripts

### ML Scripts
- binary_image_*.py
- yolo_*.py
- evaluate_yolo_model.py
- prepare_yolo_dataset.py
- package_yolo_dataset.py
- convert_json_to_yolo.py
- fix_label_names.py

### Pipeline Scripts
- hot_cities_full_pipeline.py
- sunny_shade_pipeline*.py
- prelim_filtering_tmux.py

### Test Scripts
- batch_add_*_test.py
- test_*.py

### Notebooks
- *.ipynb

### Data Directories
- city7sample/
- hot_cities/
- mapillary_city_data/
- cache/
- finetuning_yolo_test_imgs/
- hot_imgs_whole/

### Output Files
- *.png (plots)
- *.pth (models)
- sunny_batch_train*/
- plots/

### Documentation
- *.md
- LICENSE
- *.txt (documentation files)
