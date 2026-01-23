# Sunny/Shade Image Classification Pipeline

This package contains a portable deployment of the sunny/shade image classification pipeline, designed for GPU-accelerated processing of street view images.

## What it does

The pipeline performs two-stage classification on street view images:
1. **Sunny Classification**: Uses a ViT (Vision Transformer) model to classify images as sunny or not sunny
2. **Shade Detection**: For sunny images, uses a YOLO model to detect people and classify them as in shade or out of shade

## Contents

- `sunny_shade_pipeline.py` - Main pipeline script
- `process_walkable_cities.py` - Batch processing script for all cities
- `models/` - Directory containing trained model weights
  - `vit_binary.pth` - ViT model for sunny classification (91-95% accuracy)
  - `yolo_best.pt` - YOLO model for shade detection
- `data/` - City walkable images and CSV files
  - `Buenos-Airesimg/walkable_images/` - Street view images
  - `Buenos-Aires_walkable_*.csv` - City metadata with weather
  - (Additional cities: Cape Town, Istanbul, Madrid, Mumbai, Singapore)
- `requirements.txt` - Python dependencies
- `setup.sh` - Setup script for installation
- `run_pipeline.sh` - Script to process all cities
- `README.md` - This file

## System Requirements

- Python 3.8+
- CUDA-capable GPU (recommended) or CPU
- ~500MB disk space for models
- ~2GB RAM minimum, ~4GB recommended

## Quick Start

Process all city images and generate annotated CSVs:

```bash
# 1. Extract the package
tar -xzf sunny_shade_pipeline_*.tar.gz
cd sunny_shade_pipeline_package

# 2. Run setup (installs dependencies)
bash setup.sh

# 3. Run the pipeline (processes all cities)
bash run_pipeline.sh
```

That's it! The script will process ~45,000 images and update all CSV files in `data/` with the sunny/shade columns.

## Installation

1. Extract the tarball:
   ```bash
   tar -xzf sunny_shade_pipeline_*.tar.gz
   cd sunny_shade_pipeline_package
   ```

2. Run the setup script:
   ```bash
   bash setup.sh
   ```

3. Activate the virtual environment:
   ```bash
   source venv/bin/activate
   ```

## Usage

### Basic Usage

Process a folder of images and save results to CSV:

```bash
python3 sunny_shade_pipeline.py /path/to/images -o results.csv
```

### Options

```
positional arguments:
  image_folder          Path to folder containing images to process

optional arguments:
  -o, --output         Output CSV file path (default: <folder_name>_results.csv)
  --vit-model          Path to ViT model weights (default: models/vit_binary.pth)
  --yolo-model         Path to YOLO model weights (default: models/yolo_best.pt)
```

### Output Format

The output CSV contains the following columns:
- `image_id` - Image filename without extension (used as join key)
- `is_sunny` - Boolean indicating if image is sunny
- `sunny_probability` - ViT model confidence (0-1)
- `person_count` - Count of generic person detections
- `inshade_count` - Count of people detected in shade
- `outshade_count` - Count of people detected out of shade

### Example Workflow

```bash
# Activate environment
source venv/bin/activate

# Process images from a city
python3 sunny_shade_pipeline.py /data/street_images/tokyo -o tokyo_results.csv

# Process multiple folders in a loop
for city in buenos_aires cape_town istanbul; do
    python3 sunny_shade_pipeline.py /data/street_images/$city -o ${city}_results.csv
done
```

## Performance

**GPU (NVIDIA A100):**
- ~10-15 images/second
- ~3,000 images in 3-5 minutes

**CPU (modern Intel/AMD):**
- ~2-3 images/second
- ~3,000 images in 15-20 minutes

The pipeline automatically detects and uses GPU if available via PyTorch CUDA.

## Model Information

### ViT Binary Classifier
- Architecture: Vision Transformer (vit_b_16)
- Training: 5-fold cross-validation on 1,420 labeled images
- Accuracy: 91-95% validation accuracy
- Classes: sunny, not_sunny

### YOLO Shade Detector
- Architecture: YOLOv11s
- Classes: person, inshade, outshade
- Trained on custom-labeled street view dataset

## Troubleshooting

**CUDA out of memory:**
- The pipeline processes images one at a time, so CUDA OOM is unlikely
- If it occurs, ensure no other GPU processes are running

**Slow performance:**
- Verify GPU is being used: Check initial output for "Using device: cuda"
- Ensure CUDA drivers are properly installed
- Try with smaller image resolution if processing very large images

**Missing dependencies:**
- Reinstall: `pip install -r requirements.txt`
- For CUDA support: Install PyTorch with CUDA from https://pytorch.org

## Support

For issues or questions, contact the project maintainer or refer to the source repository.

## License

This pipeline uses:
- PyTorch (BSD License)
- Ultralytics YOLO (AGPL-3.0)
- Custom trained models

Please ensure compliance with all relevant licenses for your use case.
