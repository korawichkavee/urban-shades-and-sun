# Complete SVI Analysis Package - Guide

## Overview

The complete deployment package includes EVERYTHING needed to download and analyze street view images on a remote server:

1. ✅ Filtered SVI metadata (8,354 Phoenix images, 8-10am/4-6pm local time)
2. ✅ Image download script (Mapillary + KartaView support)
3. ✅ Sunny/shade analysis pipeline
4. ✅ Trained model weights (ViT + YOLO, 406MB compressed)
5. ✅ Setup and execution scripts
6. ✅ Complete documentation

## Creating the Package

```bash
# Create complete package with models
bash deployment/create_complete_package.sh -c config/phoenix_az.yaml

# Or without models (for smaller package if models already on server)
bash deployment/create_complete_package.sh -c config/phoenix_az.yaml --no-models
```

## Package Contents

```
svi_complete_phoenix_az_TIMESTAMP.tar.gz (406MB)
└── svi_complete_package_phoenix_az/
    ├── data/
    │   └── Phoenix_1840020568.csv          # 8,354 filtered images
    ├── models/
    │   ├── vit_binary.pth                  # ViT sunny classifier
    │   └── yolo_best.pt                    # YOLO shade detector
    ├── scripts/
    │   ├── download_images_from_csv.py     # Image downloader
    │   └── sunny_shade_pipeline.py         # Analysis pipeline
    ├── config/
    │   └── phoenix_az.yaml                 # Configuration
    ├── setup.sh                             # Environment setup
    ├── 1_download_images.sh                # Download execution
    ├── 2_run_analysis.sh                   # Analysis execution
    ├── requirements.txt                    # Python dependencies
    ├── README.md                           # User documentation
    └── MANIFEST.txt                        # Package manifest
```

## Deployment Workflow

### On Local Machine

```bash
# 1. Create package
bash deployment/create_complete_package.sh -c config/phoenix_az.yaml

# 2. Transfer to remote server
scp svi_complete_phoenix_az_*.tar.gz user@gpu-server:~/
```

### On Remote Server

```bash
# 3. Extract package
tar -xzf svi_complete_phoenix_az_*.tar.gz
cd svi_complete_package_phoenix_az

# 4. Setup environment (creates venv, installs dependencies)
bash setup.sh

# 5. Download images from Mapillary/KartaView
bash 1_download_images.sh

# 6. Run sunny/shade analysis
bash 2_run_analysis.sh
```

## What Each Script Does

### `setup.sh`
- Creates Python virtual environment
- Installs all dependencies from requirements.txt
- One-time setup (5-10 minutes)

### `1_download_images.sh`
- Reads CSV metadata files
- Downloads actual JPEG images from Mapillary/KartaView
- Saves to `data/CityName_images/`
- Uses provided Mapillary token
- For Phoenix: ~8,354 images, estimated 2-5GB

### `2_run_analysis.sh`
- Loads ViT and YOLO models
- Classifies each image as sunny/not-sunny
- Detects people and classifies as in-shade/out-of-shade
- Saves results to `data/CityName_analyzed.csv`
- GPU recommended (10-30 minutes with GPU, hours on CPU)

## Output Format

After analysis, each city will have:

**`data/CityName_analyzed.csv`** with columns:
- Original metadata: `id`, `lat`, `lon`, `datetime_local`, `source`, etc.
- Sunny classification: `is_sunny`, `sunny_probability`
- Shade detection: `person_count`, `inshade_count`, `outshade_count`

## System Requirements

**Minimum:**
- Python 3.8+
- 8GB RAM
- 10GB disk space (more for images)

**Recommended:**
- CUDA-capable GPU (NVIDIA)
- 16GB RAM
- 50GB+ disk space

## Troubleshooting

### Setup Issues

**Problem:** `pip install` fails
**Solution:** Ensure Python 3.8+ and pip are updated
```bash
python3 --version
pip3 install --upgrade pip
```

### Download Issues

**Problem:** Mapillary downloads fail
**Solution:** Check token in `1_download_images.sh`
```bash
# Edit the script and verify MAPILLARY_TOKEN line
nano 1_download_images.sh
```

**Problem:** KartaView downloads fail
**Solution:** KartaView API may be unavailable; Mapillary-only is fine

### Analysis Issues

**Problem:** Out of memory during analysis
**Solution:** Process in smaller batches or use CPU with reduced batch size

**Problem:** No GPU detected
**Solution:** Analysis will run on CPU (slower but functional)

## Testing Locally

Before deploying to remote server, you can test locally:

```bash
# Extract package
tar -xzf svi_complete_phoenix_az_*.tar.gz
cd svi_complete_package_phoenix_az

# Setup
bash setup.sh

# Test with small subset
source venv/bin/activate
python3 scripts/download_images_from_csv.py \
    --input data/Phoenix_1840020568.csv \
    --output data/test_images \
    --max-images 10  # Only download 10 for testing

# Test analysis
python3 scripts/sunny_shade_pipeline.py \
    --images data/test_images \
    --csv data/Phoenix_1840020568.csv \
    --output data/test_results.csv \
    --vit-model models/vit_binary.pth \
    --yolo-model models/yolo_best.pt
```

## Customization

### Different Cities

Edit `config/phoenix_az.yaml` to add more cities:
```yaml
cities:
  - 1840020568  # Phoenix
  - 5128581     # New York
  - 1840013660  # Los Angeles
```

Then recreate the package:
```bash
bash deployment/create_complete_package.sh -c config/multi_city.yaml
```

### Different Time Windows

Edit the config to change date ranges:
```yaml
start_date: '2020-01-01'
end_date: '2023-12-31'
```

## Package Sizes

- **With models**: ~406MB compressed, ~439MB uncompressed
- **Without models** (`--no-models`): ~1MB compressed
- **After downloading images**: Varies (Phoenix ~2-5GB for 8,354 images)
- **After analysis**: Adds ~100KB per CSV

## Next Steps

After successful analysis:
1. Download results: `scp user@server:~/svi_complete_package_phoenix_az/data/*_analyzed.csv ./`
2. Further analysis: Load CSVs into pandas/R for statistical analysis
3. Visualization: Plot shade ratios, sunny distributions, etc.
4. Integration: Merge with weather data, UTCI calculations, etc.

## Support Files

- **PHOENIX_QUICKSTART.md** - Quick reference guide
- **PHOENIX_IMPLEMENTATION_SUMMARY.md** - Detailed implementation notes
- **README.md** (in package) - User-facing documentation
