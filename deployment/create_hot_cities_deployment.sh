#!/bin/bash
# ABOUTME: Creates deployment package for hot cities walkable street analysis
# ABOUTME: Packages CSVs, models, and on-demand processing pipeline for GPU deployment

set -e

echo "========================================"
echo "Hot Cities Analysis Deployment Package"
echo "========================================"
echo ""

# Set base directory
BASE_DIR="/home/kieran/Documents/Python/sunny_day_SVI"
PACKAGE_DIR="$BASE_DIR/hot_cities_deployment"
OUTPUT_TAR="hot_cities_deployment_$(date +%Y%m%d_%H%M%S).tar.gz"

# Clean up old package directory if it exists
if [ -d "$PACKAGE_DIR" ]; then
    echo "Cleaning up old package directory..."
    rm -rf "$PACKAGE_DIR"
fi

# Create package directory structure
echo "Creating package directory structure..."
mkdir -p "$PACKAGE_DIR/models"
mkdir -p "$PACKAGE_DIR/data"
mkdir -p "$PACKAGE_DIR/output"

# Copy full pipeline script (sunny/shade + weather)
echo "Copying pipeline scripts..."
if [ ! -f "$BASE_DIR/hot_cities_full_pipeline.py" ]; then
    echo "Error: hot_cities_full_pipeline.py not found!"
    exit 1
fi
cp "$BASE_DIR/hot_cities_full_pipeline.py" "$PACKAGE_DIR/"

# Copy model weights
echo "Copying ViT model weights..."
if [ ! -f "$BASE_DIR/vit_binary.pth" ]; then
    echo "Error: vit_binary.pth not found!"
    exit 1
fi
cp "$BASE_DIR/vit_binary.pth" "$PACKAGE_DIR/models/"

echo "Copying YOLO model weights..."
if [ ! -f "$BASE_DIR/sunny_batch_train4/weights/best.pt" ]; then
    echo "Error: YOLO model weights not found!"
    exit 1
fi
cp "$BASE_DIR/sunny_batch_train4/weights/best.pt" "$PACKAGE_DIR/models/yolo_best.pt"

# Copy all walkable CSVs from hot_cities
echo "Copying walkable CSVs..."
WALKABLE_COUNT=0
for csv in "$BASE_DIR/hot_cities/"*_walkable_*.csv; do
    if [ -f "$csv" ]; then
        cp "$csv" "$PACKAGE_DIR/data/"
        WALKABLE_COUNT=$((WALKABLE_COUNT + 1))
    fi
done
echo "  Copied $WALKABLE_COUNT walkable CSV files"

# Create requirements.txt
echo "Creating requirements.txt..."
cat > "$PACKAGE_DIR/requirements.txt" << 'EOF'
torch>=2.0.0
torchvision>=0.15.0
ultralytics>=8.0.0
Pillow>=9.0.0
pandas>=1.5.0
tqdm>=4.65.0
mapillary>=1.0.0
meteostat>=1.6.0
metpy>=1.5.0
tenacity>=8.2.0
EOF

# Create setup script
echo "Creating setup.sh..."
cat > "$PACKAGE_DIR/setup.sh" << 'EOF'
#!/bin/bash
# Setup script for hot cities analysis deployment

echo "=========================================="
echo "Setting up Hot Cities Analysis Pipeline"
echo "=========================================="
echo ""

# Check for GPU
if command -v nvidia-smi &> /dev/null; then
    echo "GPU detected:"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
    echo ""
else
    echo "WARNING: No GPU detected. Pipeline will run on CPU (much slower)"
    echo ""
fi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "To run the pipeline:"
echo "  1. Activate environment: source venv/bin/activate"
echo "  2. Run: bash run_pipeline.sh"
echo ""
EOF
chmod +x "$PACKAGE_DIR/setup.sh"

# Create run script (without tmux)
echo "Creating run_pipeline.sh..."
cat > "$PACKAGE_DIR/run_pipeline.sh" << 'EOF'
#!/bin/bash
# Run full pipeline on all walkable CSVs (sunny/shade + weather)

echo "=========================================="
echo "Running Hot Cities Analysis Pipeline"
echo "=========================================="
echo ""
echo "This pipeline will:"
echo "  1. Download images on-demand from Mapillary"
echo "  2. Classify sunny/not-sunny"
echo "  3. Detect people in/out of shade"
echo "  4. Add weather data (temperature, humidity)"
echo "  5. Delete images after processing"
echo ""
echo "Logs will be saved to pipeline.log"
echo "=========================================="
echo ""

# Activate virtual environment
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found. Run setup.sh first!"
    exit 1
fi

# Use absolute path for venv activation
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$SCRIPT_DIR/venv/bin/activate"

# Verify activation
if [ -z "$VIRTUAL_ENV" ]; then
    echo "ERROR: Failed to activate virtual environment!"
    exit 1
fi

echo "Virtual environment activated: $VIRTUAL_ENV"
echo ""

# Check that Python can import required packages
echo "Verifying package installation..."
python -c "import torch; import pandas; import mapillary; import meteostat; import ultralytics" 2>&1
if [ $? -ne 0 ]; then
    echo "ERROR: Required packages not installed. Run setup.sh first!"
    exit 1
fi

# Run full pipeline
python hot_cities_full_pipeline.py data output

echo ""
echo "=========================================="
echo "Pipeline Complete!"
echo "=========================================="
echo ""
echo "Annotated CSVs are in the output/ directory"
echo "Check pipeline.log for detailed logs"
echo ""
EOF
chmod +x "$PACKAGE_DIR/run_pipeline.sh"

# Create tmux wrapper script
echo "Creating run_pipeline_tmux.sh..."
cat > "$PACKAGE_DIR/run_pipeline_tmux.sh" << 'EOF'
#!/bin/bash
# Run pipeline in tmux session for long-running processing

SESSION_NAME="hot_cities_pipeline"

# Check if tmux is installed
if ! command -v tmux &> /dev/null; then
    echo "Error: tmux is not installed"
    echo "Install with: sudo apt-get install tmux (Ubuntu/Debian)"
    echo "           or: sudo yum install tmux (CentOS/RHEL)"
    exit 1
fi

# Check if session already exists
tmux has-session -t $SESSION_NAME 2>/dev/null

if [ $? == 0 ]; then
    echo "Session '$SESSION_NAME' already exists."
    echo ""
    echo "Options:"
    echo "  1. Attach to existing session: tmux attach -t $SESSION_NAME"
    echo "  2. Kill and restart: tmux kill-session -t $SESSION_NAME && $0"
    echo ""
    read -p "Attach to existing session? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        tmux attach -t $SESSION_NAME
    fi
    exit 0
fi

# Check that setup was run
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found. Run setup.sh first!"
    exit 1
fi

# Create new tmux session
echo "=========================================="
echo "Creating tmux session: $SESSION_NAME"
echo "=========================================="
echo ""

tmux new-session -d -s $SESSION_NAME -n "pipeline"

# Set working directory and run pipeline
CURRENT_DIR="$(pwd)"
tmux send-keys -t $SESSION_NAME:pipeline "cd '$CURRENT_DIR'" C-m
tmux send-keys -t $SESSION_NAME:pipeline "source '$CURRENT_DIR/venv/bin/activate'" C-m
tmux send-keys -t $SESSION_NAME:pipeline "echo 'Virtual environment:' \$VIRTUAL_ENV" C-m
tmux send-keys -t $SESSION_NAME:pipeline "echo 'Starting hot cities pipeline...'" C-m
tmux send-keys -t $SESSION_NAME:pipeline "echo 'This will process 170,904 images and may take 1-4 days'" C-m
tmux send-keys -t $SESSION_NAME:pipeline "echo 'Log will be saved to pipeline.log'" C-m
tmux send-keys -t $SESSION_NAME:pipeline "echo ''" C-m
tmux send-keys -t $SESSION_NAME:pipeline "bash '$CURRENT_DIR/run_pipeline.sh'" C-m

echo "Session created successfully!"
echo ""
echo "IMPORTANT: The pipeline will run for 1-4 days depending on GPU speed"
echo "           Estimated: ~95 hours on GPU, longer on CPU"
echo ""
echo "To monitor progress:"
echo "  Attach to session: tmux attach -t $SESSION_NAME"
echo "  View log: tail -f pipeline.log"
echo "  Quick check: tmux capture-pane -t $SESSION_NAME -p | tail -20"
echo ""
echo "To detach from session (keeps it running):"
echo "  Press: Ctrl+B, then D"
echo ""
echo "To kill the session:"
echo "  tmux kill-session -t $SESSION_NAME"
echo ""
echo "Progress is saved every 50 images in each CSV."
echo "If interrupted, rerun this script to resume."
echo ""
EOF
chmod +x "$PACKAGE_DIR/run_pipeline_tmux.sh"

# Create README
echo "Creating README.md..."
cat > "$PACKAGE_DIR/README.md" << 'EOF'
# Hot Cities Street View Analysis Pipeline

This package processes walkable street images from hot cities to classify sunny/not-sunny conditions and detect people in/out of shade.

## Contents

- `hot_cities_full_pipeline.py` - Main pipeline script with on-demand image download
- `models/` - Trained model weights (ViT for sunny classification, YOLO for shade detection)
- `data/` - Walkable CSV files for each city (image metadata, no images)
- `output/` - Output directory for annotated CSVs (created on first run)

## Requirements

- Python 3.8+
- CUDA-capable GPU (recommended)
- ~10GB disk space for models and temporary images
- Internet connection (to download images from Mapillary)

## Setup

1. Extract this package:
   ```bash
   tar -xzf hot_cities_deployment_YYYYMMDD_HHMMSS.tar.gz
   cd hot_cities_deployment
   ```

2. Run setup script:
   ```bash
   bash setup.sh
   ```

This will create a virtual environment and install all dependencies.

## Running the Pipeline

### RECOMMENDED: Run in tmux (for long-running processes)

**This pipeline may take 1-4 days to complete all 170,904 images.**

To run in tmux (so it continues even if you disconnect):

```bash
bash run_pipeline_tmux.sh
```

This will:
- Create a tmux session named `hot_cities_pipeline`
- Run the pipeline in the background
- Save output to `pipeline.log`
- Allow you to disconnect and reconnect anytime

**Monitor progress:**
- Attach to session: `tmux attach -t hot_cities_pipeline`
- View log: `tail -f pipeline.log`
- Quick check: `tmux capture-pane -t hot_cities_pipeline -p | tail -20`

**Detach (keep running):** Press `Ctrl+B`, then `D`

### Alternative: Run directly (stays in foreground)

To run directly without tmux:

```bash
source venv/bin/activate
bash run_pipeline.sh
```

⚠️ WARNING: If you disconnect, the process will stop!

### Process Single City

To process a specific city:

```bash
source venv/bin/activate
python hot_cities_full_pipeline.py \
    data/Manila_walkable_1608618140.csv \
    output/Manila_annotated.csv
```

## Pipeline Steps

For each city, the pipeline:
1. **Downloads images on-demand** from Mapillary (one at a time)
2. **Classifies sunny/not-sunny** using ViT model
3. **Detects people in/out of shade** using YOLO model (if sunny)
4. **Adds weather data** (wet bulb, dry bulb temp, humidity, sunshine)
5. **Deletes image** to save disk space
6. **Saves progress** every 50 images
7. **Moves to next city** after completion

## Output Format

Annotated CSVs will have these additional columns:

**Sunny/Shade annotations:**
- `is_sunny` - Boolean, whether image is classified as sunny
- `sunny_probability` - Float 0-1, probability of being sunny
- `person_count` - Integer, number of people detected
- `inshade_count` - Integer, number of people in shade
- `outshade_count` - Integer, number of people out of shade

**Weather data:**
- `wbulb` - Wet bulb temperature (°C)
- `dbulb` - Dry bulb temperature (°C)
- `tsun` - Sunshine duration (minutes)
- `rhum` - Relative humidity (%)

## Resource Usage

- **GPU Memory**: ~4-6GB
- **Disk Space**: ~2-3GB temporary (images downloaded and deleted)
- **Processing Speed**: ~5-10 images/second on GPU, ~1 image/second on CPU
- **Network**: Downloads ~2MB per image from Mapillary

## Logging

The pipeline creates comprehensive logs in `pipeline.log`:

- **Timestamped entries** for every operation
- **Progress reports** every 50 images with ETA
- **Error details** with full stack traces
- **Per-city summaries** when each completes
- **Final summary** with all statistics

**Log levels:**
- INFO: Progress, summaries, completions
- WARNING: Retry attempts, failed images
- ERROR: Fatal errors, city failures
- DEBUG: Detailed operations (file operations, model loading)

**Monitor progress:**
```bash
# View log in real-time
tail -f pipeline.log

# See last 50 lines
tail -50 pipeline.log

# Search for errors
grep ERROR pipeline.log

# Search for specific city
grep "Manila" pipeline.log
```

## Troubleshooting

### Out of Memory Errors
**Symptom:** GPU memory errors, process killed
**Solution:** Pipeline uses minimal memory by processing one image at a time. Check GPU has at least 4GB RAM.

### Network Errors
**Symptom:** Failed to download images
**Solution:** Pipeline retries each image 2 times. Check internet connection. Images that fail after retries are logged and skipped.

### Resuming Interrupted Process
**Symptom:** Process stopped mid-run
**Solution:** The pipeline saves progress every 50 images. Rerun `bash run_pipeline_tmux.sh` - it will skip already-processed images based on existing data in CSVs.

### Weather Data Missing
**Symptom:** Some images have no weather data (wbulb/dbulb = None)
**Expected:** Weather stations may not have data for all locations/times. This is normal and logged.

### Diagnosing Errors
1. Check `pipeline.log` for ERROR entries
2. Look for the city and image ID where error occurred
3. Check if error is transient (network) or permanent (missing data)
4. For persistent errors on one city, you can skip it and process others

## City Data

Total walkable images across all cities: 170,904

Top cities by walkable image count:
1. Manila - 59,273 images
2. Phnom Penh - 34,572 images
3. Panama City - 25,560 images
4. Willemstad - 19,131 images
5. George Town - 11,612 images

See individual CSV files for complete city list.

## Support

For issues or questions, contact the project maintainer.
EOF

# Create city list file
echo "Creating city_list.txt..."
find "$PACKAGE_DIR/data" -name "*_walkable_*.csv" -exec basename {} \; | cut -d'_' -f1 | sort > "$PACKAGE_DIR/city_list.txt"
CITY_COUNT=$(wc -l < "$PACKAGE_DIR/city_list.txt")

# Create tarball
echo "Creating tarball..."
cd "$BASE_DIR"
tar -czf "$OUTPUT_TAR" -C "$BASE_DIR" "hot_cities_deployment"

# Get package size
PACKAGE_SIZE=$(du -h "$BASE_DIR/$OUTPUT_TAR" | cut -f1)

# Clean up package directory
echo "Cleaning up..."
rm -rf "$PACKAGE_DIR"

# Show results
echo ""
echo "=========================================="
echo "Package Created Successfully!"
echo "=========================================="
echo ""
echo "Output file: $BASE_DIR/$OUTPUT_TAR"
echo "Size: $PACKAGE_SIZE"
echo ""
echo "Package contents:"
echo "  - $CITY_COUNT cities"
echo "  - $WALKABLE_COUNT walkable CSVs"
echo "  - 170,904 total walkable images"
echo "  - ViT model (sunny classification)"
echo "  - YOLO model (shade detection)"
echo "  - On-demand processing pipeline"
echo ""
echo "To deploy on GPU machine:"
echo "  1. Transfer $OUTPUT_TAR to GPU machine"
echo "  2. Extract: tar -xzf $(basename $OUTPUT_TAR)"
echo "  3. cd hot_cities_deployment"
echo "  4. Run: bash setup.sh"
echo "  5. Run: bash run_pipeline.sh"
echo ""
echo "The pipeline will:"
echo "  - Download images on-demand from Mapillary"
echo "  - Classify sunny/not-sunny and detect shade"
echo "  - Delete images after processing"
echo "  - Save annotated CSVs to output/"
echo ""
