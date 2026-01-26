#!/bin/bash
# ABOUTME: Creates deployment package for overnight multi-city analysis
# ABOUTME: Includes models, scripts, and everything needed for unattended run

set -e

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BASE_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PACKAGE_NAME="svi_overnight_multicity_${TIMESTAMP}"
PACKAGE_DIR="$BASE_DIR/$PACKAGE_NAME"

echo "========================================"
echo "Multi-City Overnight Package Creator"
echo "========================================"
echo "Package: $PACKAGE_NAME"
echo ""

# Clean up old package if exists
if [ -d "$PACKAGE_DIR" ]; then
    echo "Cleaning up old package..."
    rm -rf "$PACKAGE_DIR"
fi

# Create directory structure
echo "Step 1: Creating directory structure..."
mkdir -p "$PACKAGE_DIR/scripts"
mkdir -p "$PACKAGE_DIR/models"
mkdir -p "$PACKAGE_DIR/data"
mkdir -p "$PACKAGE_DIR/config"

# Copy pipeline scripts
echo "Step 2: Copying pipeline scripts..."
cp scripts/pipelines/multi_city_overnight_pipeline.py "$PACKAGE_DIR/scripts/"
cp scripts/pipelines/test_multi_city_pipeline.py "$PACKAGE_DIR/scripts/"
cp scripts/pipelines/sunny_shade_pipeline.py "$PACKAGE_DIR/scripts/"
cp scripts/data_collection/download_mly_points.py "$PACKAGE_DIR/scripts/"

# Copy worldcities data
echo "Step 2b: Copying worldcities data..."
WORLDCITIES_PATH="/home/kieran/Documents/Datasets/Global streetscapes/global-streetscapes/code/raw_download/data/worldcities.csv"
if [ -f "$WORLDCITIES_PATH" ]; then
    echo "  - worldcities.csv"
    cp "$WORLDCITIES_PATH" "$PACKAGE_DIR/data/"
else
    echo "  WARNING: worldcities.csv not found at $WORLDCITIES_PATH"
fi

# Copy models
echo "Step 3: Copying model weights..."
if [ -f "outputs/models/vit_binary.pth" ]; then
    echo "  - ViT binary model"
    cp "outputs/models/vit_binary.pth" "$PACKAGE_DIR/models/"
else
    echo "  WARNING: vit_binary.pth not found"
fi

if [ -f "outputs/models/sunny_batch_train4/weights/best.pt" ]; then
    echo "  - YOLO shade detection (train4)"
    cp "outputs/models/sunny_batch_train4/weights/best.pt" "$PACKAGE_DIR/models/yolo_best.pt"
elif [ -f "outputs/models/sunny_batch_train6/weights/best.pt" ]; then
    echo "  - YOLO shade detection (train6)"
    cp "outputs/models/sunny_batch_train6/weights/best.pt" "$PACKAGE_DIR/models/yolo_best.pt"
else
    echo "  WARNING: YOLO model not found"
fi

# Create requirements.txt
echo "Step 4: Creating requirements.txt..."
cat > "$PACKAGE_DIR/requirements.txt" << 'EOF'
# Core ML dependencies
torch>=2.0.0
torchvision>=0.15.0
ultralytics>=8.0.0

# Data processing
pandas>=2.0.0
geopandas>=0.13.0
numpy>=1.24.0

# Image processing
Pillow>=10.0.0

# Async operations
aiohttp>=3.9.0
asyncio

# API and utilities
mapillary>=1.0.0
requests>=2.31.0
tqdm>=4.65.0
pyyaml>=6.0

# Optional but recommended
matplotlib>=3.7.0
EOF

# Create city configuration file
echo "Step 5: Creating city configuration..."
cat > "$PACKAGE_DIR/config/cities.json" << 'EOF'
{
  "cities": [
    {"name": "Madrid", "country": "ESP", "id": 1724616994},
    {"name": "Cape Town", "country": "ZAF", "id": 1710680650},
    {"name": "Istanbul", "country": "TUR", "id": 1792756324},
    {"name": "Osaka", "country": "JPN", "id": 1392419823},
    {"name": "Singapore", "country": "SGP", "id": 1702341327},
    {"name": "Buenos Aires", "country": "ARG", "id": 1032717330},
    {"name": "Mumbai", "country": "IND", "id": 1356226629}
  ],
  "mapillary_token": "MLY|9798203303595429|e2d4e749e96af419787ec1ca33019e3f",
  "max_concurrent_cities": 3,
  "batch_size": 100
}
EOF

# Create setup script
echo "Step 6: Creating setup script..."
cat > "$PACKAGE_DIR/setup.sh" << 'EOF'
#!/bin/bash
# Setup environment for multi-city overnight run

set -e

echo "========================================"
echo "Setting Up Overnight Pipeline"
echo "========================================"
echo ""

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "Installing requirements..."
pip install -r requirements.txt

echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "  1. Test: bash test_pipeline.sh"
echo "  2. Run: bash run_overnight.sh"
echo ""
EOF

# Create test script
echo "Step 7: Creating test script..."
cat > "$PACKAGE_DIR/test_pipeline.sh" << 'EOF'
#!/bin/bash
# Test pipeline with small dataset

set -e

echo "========================================"
echo "Testing Multi-City Pipeline"
echo "========================================"
echo ""

if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found"
    echo "Run: bash setup.sh"
    exit 1
fi

source venv/bin/activate

# Run test (script auto-detects paths)
python3 scripts/test_multi_city_pipeline.py

echo ""
echo "If test passed, you can run the full pipeline with:"
echo "  bash run_overnight.sh"
echo ""
EOF

# Create overnight run script
echo "Step 8: Creating overnight run script..."
cat > "$PACKAGE_DIR/run_overnight.sh" << 'EOF'
#!/bin/bash
# Run overnight multi-city analysis pipeline

set -e

echo "========================================"
echo "Starting Overnight Multi-City Pipeline"
echo "========================================"
echo ""
echo "Cities to process:"
echo "  - Madrid, ESP"
echo "  - Cape Town, ZAF"
echo "  - Istanbul, TUR"
echo "  - Osaka, JPN"
echo "  - Singapore, SGP"
echo "  - Buenos Aires, ARG"
echo "  - Mumbai, IND"
echo ""
echo "This will:"
echo "  1. Download metadata for each city"
echo "  2. Download images in batches (async)"
echo "  3. Run sunny/shade analysis"
echo "  4. Clean up images after each batch"
echo "  5. Save analyzed CSVs"
echo ""
echo "Expected duration: 8-12 hours"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled"
    exit 0
fi

if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found"
    echo "Run: bash setup.sh"
    exit 1
fi

source venv/bin/activate

# Run pipeline (script auto-detects paths)
echo "Starting pipeline at $(date)"
echo ""

python3 scripts/multi_city_overnight_pipeline.py \
    --output-dir data/multi_city_results \
    --worldcities-csv data/worldcities.csv \
    --vit-model models/vit_binary.pth \
    --yolo-model models/yolo_best.pt

echo ""
echo "========================================"
echo "Pipeline Complete!"
echo "========================================"
echo "Finished at $(date)"
echo ""
echo "Results saved to: data/multi_city_results/"
echo ""
EOF

# Create background run script
cat > "$PACKAGE_DIR/run_background.sh" << 'EOF'
#!/bin/bash
# Run pipeline in background with nohup

echo "Starting overnight pipeline in background..."
echo "Log file: overnight_pipeline.log"
echo ""

nohup bash run_overnight.sh > overnight_pipeline.log 2>&1 &

PID=$!
echo "Pipeline started with PID: $PID"
echo ""
echo "To monitor progress:"
echo "  tail -f overnight_pipeline.log"
echo ""
echo "To check if still running:"
echo "  ps aux | grep $PID"
echo ""
echo "To stop:"
echo "  kill $PID"
echo ""
EOF

# Make all scripts executable
chmod +x "$PACKAGE_DIR/setup.sh"
chmod +x "$PACKAGE_DIR/test_pipeline.sh"
chmod +x "$PACKAGE_DIR/run_overnight.sh"
chmod +x "$PACKAGE_DIR/run_background.sh"

# Create README
echo "Step 9: Creating README..."
cat > "$PACKAGE_DIR/README.md" << 'EOF'
# Overnight Multi-City SVI Analysis Package

Automated pipeline for downloading and analyzing street view images across multiple cities.

## Features

- **Batched Processing**: Downloads and analyzes images in batches to save disk space
- **Async Downloads**: Parallel image downloads for faster processing
- **Automatic Cleanup**: Removes images after analysis to conserve space
- **Multi-City Support**: Processes 7 cities sequentially
- **Unattended Operation**: Designed for overnight runs with comprehensive logging

## Cities Included

1. Madrid, Spain
2. Cape Town, South Africa
3. Istanbul, Turkey
4. Osaka, Japan
5. Singapore
6. Buenos Aires, Argentina
7. Mumbai, India

Note: Phoenix, AZ has been removed as it was already analyzed.

## Quick Start

### 1. Setup Environment

```bash
bash setup.sh
```

Creates Python virtual environment and installs all dependencies.

### 2. Test Pipeline (IMPORTANT!)

```bash
bash test_pipeline.sh
```

Runs small-scale test with ALL 7 cities (5 images per city = 35 images total) to verify everything works.

### 3. Run Overnight Pipeline

**Interactive mode** (waits for confirmation):
```bash
bash run_overnight.sh
```

**Background mode** (runs unattended):
```bash
bash run_background.sh
```

Monitor progress:
```bash
tail -f overnight_pipeline.log
```

## How It Works

### For Each City:

1. **Fetch Metadata**: Downloads CSV with image locations and metadata from Mapillary
2. **Batched Download & Analysis**:
   - Downloads 100 images at a time (async, parallel)
   - Runs sunny/shade classification (ViT model)
   - Detects people and shade (YOLO model)
   - **Deletes images** after analysis
3. **Combine Results**: Merges all batches into single analyzed CSV
4. **Final Cleanup**: Removes temporary files

### Why Batched?

Processing all images at once would require ~500GB-1TB disk space. Batching limits disk usage to ~10-20GB per city.

## Output

After completion, you'll find in `data/multi_city_results/`:

```
Madrid/
  Madrid_1724616994_analyzed.csv
Cape-Town/
  Cape-Town_1710680650_analyzed.csv
Istanbul/
  Istanbul_1792756324_analyzed.csv
...
pipeline_summary.json
```

### CSV Columns

Each analyzed CSV contains:
- **Original metadata**: lat, lon, datetime_utc, datetime_local, id, sequence_id
- **Sunny classification**: is_sunny, sunny_probability
- **Shade detection**: person_count, inshade_count, outshade_count

## Requirements

- Python 3.8+
- CUDA GPU (highly recommended, 8GB+ VRAM)
- 50GB free disk space
- Stable internet connection
- 8-12 hours of uninterrupted runtime

## Troubleshooting

### Test fails
- Check model files exist in `models/`
- Verify internet connection
- Check Mapillary token is valid

### Out of disk space
- Reduce BATCH_SIZE in config/cities.json
- Ensure cleanup is working (check logs)

### Download timeouts
- Increase timeout in multi_city_overnight_pipeline.py
- Check network stability

### GPU out of memory
- Reduce batch size in sunny_shade_pipeline.py
- Fall back to CPU (slower): export CUDA_VISIBLE_DEVICES=-1

## Monitoring

### Check Progress

```bash
# Watch log in real-time
tail -f overnight_pipeline.log

# Check if process is running
ps aux | grep multi_city

# Check disk usage
df -h
du -sh data/multi_city_results/
```

### Estimated Timeline

- Madrid: ~2 hours
- Cape Town: ~1-2 hours
- Istanbul: ~2-3 hours
- Osaka: ~1 hour
- Singapore: ~30 minutes
- Buenos Aires: ~1-2 hours
- Mumbai: ~2-3 hours

**Total**: 8-14 hours depending on image counts and network speed

## Safety Features

- Checkpointing: Each city saved independently
- Error handling: City failures don't stop other cities
- Comprehensive logging: All operations logged to file
- Automatic cleanup: Prevents disk overflow
- Resource monitoring: Logs progress and ETA

## After Completion

1. Check `pipeline_summary.json` for statistics
2. Verify all city CSVs were created
3. Compress results for transfer:
   ```bash
   tar -czf results.tar.gz data/multi_city_results/
   ```

## Support

If pipeline fails, check:
1. Log file for error messages
2. Disk space availability
3. Network connectivity
4. GPU availability (nvidia-smi)

All scripts are resumable - you can restart and already-processed cities will be skipped.
EOF

# Create NOTES file
cat > "$PACKAGE_DIR/DEPLOYMENT_NOTES.txt" << EOF
Deployment Package: $PACKAGE_NAME
Created: $(date)

IMPORTANT INSTRUCTIONS:

1. TRANSFER TO SERVER:
   scp $PACKAGE_NAME.tar.gz user@server:~/

2. ON SERVER:
   tar -xzf $PACKAGE_NAME.tar.gz
   cd $PACKAGE_NAME

3. SETUP (FIRST TIME):
   bash setup.sh

4. TEST (REQUIRED):
   bash test_pipeline.sh

5. IF TEST PASSES, RUN:
   bash run_background.sh

6. MONITOR:
   tail -f overnight_pipeline.log

ESTIMATED DURATION: 8-12 hours
DISK SPACE REQUIRED: ~50GB

CITIES PROCESSED:
- Madrid, ESP
- Cape Town, ZAF
- Istanbul, TUR
- Osaka, JPN
- Singapore, SGP
- Buenos Aires, ARG
- Mumbai, IND

(Phoenix removed - already processed)

OUTPUT:
- data/multi_city_results/[City]/[City]_analyzed.csv
- pipeline_summary.json
- Comprehensive logs

FEATURES:
- Async downloads (faster)
- Batched processing (saves space)
- Automatic cleanup
- Error recovery
- Progress logging

DO NOT INTERRUPT DURING RUN!
Allow 8-12 hours of uninterrupted operation.
EOF

# Create tarball
echo "Step 10: Creating tarball..."
TARBALL="${PACKAGE_NAME}.tar.gz"
tar -czf "$TARBALL" -C "$BASE_DIR" "$(basename "$PACKAGE_DIR")"

# Get sizes
TARBALL_SIZE=$(du -h "$TARBALL" | cut -f1)
PACKAGE_SIZE=$(du -sh "$PACKAGE_DIR" | cut -f1)

# Cleanup
rm -rf "$PACKAGE_DIR"

# Summary
echo ""
echo "========================================"
echo "Package Created Successfully!"
echo "========================================"
echo ""
echo "Output: $TARBALL"
echo "Compressed size: $TARBALL_SIZE"
echo "Uncompressed size: $PACKAGE_SIZE"
echo ""
echo "Package includes:"
echo "  - Multi-city overnight pipeline"
echo "  - Trained models (ViT + YOLO)"
echo "  - Test script for validation"
echo "  - Automated setup and run scripts"
echo "  - Complete documentation"
echo ""
echo "Next steps:"
echo "  1. Review DEPLOYMENT_NOTES.txt"
echo "  2. Transfer to server"
echo "  3. Run test before overnight run"
echo ""
echo "To extract:"
echo "  tar -xzf $TARBALL"
echo ""
