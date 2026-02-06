#!/bin/bash
# ABOUTME: Creates portable deployment tarball for metro cities SVI pipeline
# ABOUTME: Packages models, scripts, and dependencies for shade preference analysis

set -e

echo "========================================"
echo "Creating Metro Cities SVI Package"
echo "========================================"
echo ""

# Set base directory
BASE_DIR="/home/kieran/Documents/Python/sunny_day_SVI"
DEPLOY_DIR="$BASE_DIR/deployment"
PACKAGE_DIR="$BASE_DIR/metro_svi_package"
OUTPUT_TAR="metro_svi_pipeline_$(date +%Y%m%d_%H%M%S).tar.gz"

# Clean up old package directory if it exists
if [ -d "$PACKAGE_DIR" ]; then
    echo "Cleaning up old package directory..."
    rm -rf "$PACKAGE_DIR"
fi

# Create package directory structure
echo "Creating package directory structure..."
mkdir -p "$PACKAGE_DIR/scripts/pipelines"
mkdir -p "$PACKAGE_DIR/scripts/data_collection"
mkdir -p "$PACKAGE_DIR/models"
mkdir -p "$PACKAGE_DIR/data"
mkdir -p "$PACKAGE_DIR/logs"

# Copy pipeline scripts
echo "Copying pipeline scripts..."
cp "$BASE_DIR/scripts/pipelines/metro_cities_svi_pipeline.py" "$PACKAGE_DIR/scripts/pipelines/"
cp "$BASE_DIR/scripts/pipelines/test_metro_cities_svi_pipeline.py" "$PACKAGE_DIR/scripts/pipelines/"
cp "$BASE_DIR/scripts/pipelines/sunny_shade_pipeline.py" "$PACKAGE_DIR/scripts/pipelines/"
cp "$BASE_DIR/scripts/pipelines/fetch_city_boundaries.py" "$PACKAGE_DIR/scripts/pipelines/"
cp "$BASE_DIR/scripts/pipelines/run_metro_svi_tmux.sh" "$PACKAGE_DIR/scripts/pipelines/"

# Copy data collection scripts
echo "Copying data collection scripts..."
cp "$BASE_DIR/scripts/data_collection/download_mly_points.py" "$PACKAGE_DIR/scripts/data_collection/"

# Copy model weights
echo "Copying ViT model weights..."
VIT_MODEL=""
if [ -f "$BASE_DIR/outputs/models/vit_binary.pth" ]; then
    cp "$BASE_DIR/outputs/models/vit_binary.pth" "$PACKAGE_DIR/models/"
    VIT_MODEL="outputs/models/vit_binary.pth"
elif [ -f "$BASE_DIR/vit_binary.pth" ]; then
    cp "$BASE_DIR/vit_binary.pth" "$PACKAGE_DIR/models/"
    VIT_MODEL="vit_binary.pth"
else
    echo "Warning: vit_binary.pth not found - you'll need to train or provide this model"
    echo "         The model is needed for sunny/cloudy classification"
    echo "         Create an empty placeholder for now"
    touch "$PACKAGE_DIR/models/vit_binary.pth"
    VIT_MODEL="NOT_FOUND"
fi

echo "Copying YOLO model weights..."
if [ ! -f "$BASE_DIR/outputs/models/sunny_batch_train4/weights/best.pt" ]; then
    echo "Error: YOLO model weights not found!"
    exit 1
fi
cp "$BASE_DIR/outputs/models/sunny_batch_train4/weights/best.pt" "$PACKAGE_DIR/models/yolo_best.pt"

# Copy worldcities database (needed for metadata fetching)
echo "Copying worldcities database..."
if [ -f "$BASE_DIR/data/worldcities.csv" ]; then
    cp "$BASE_DIR/data/worldcities.csv" "$PACKAGE_DIR/data/"
else
    echo "Warning: worldcities.csv not found, will use bbox-based fetching"
fi

# Create requirements.txt
echo "Creating requirements.txt..."
cat > "$PACKAGE_DIR/requirements.txt" << 'EOF'
# Core ML
torch>=2.0.0
torchvision>=0.15.0
ultralytics>=8.0.0

# Image processing
Pillow>=9.0.0
opencv-python>=4.7.0

# Data processing
pandas>=1.5.0
numpy>=1.24.0

# Mapillary API
mapillary>=1.0.0
aiohttp>=3.8.0

# Progress bars
tqdm>=4.65.0

# Geospatial
geopandas>=0.12.0
shapely>=2.0.0
osmnx>=2.0.0

# Geospatial backends
pyogrio>=0.6.0
EOF

# Create setup script
echo "Creating setup.sh..."
cat > "$PACKAGE_DIR/setup.sh" << 'EOF'
#!/bin/bash
# Setup script for metro cities SVI pipeline

echo "========================================"
echo "Metro Cities SVI Pipeline Setup"
echo "========================================"
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
major=$(echo $python_version | cut -d. -f1)
minor=$(echo $python_version | cut -d. -f2)
if [ "$major" -lt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -lt 8 ]; }; then
    echo "Error: Python 3.8+ required (found $python_version)"
    exit 1
fi
echo "✓ Python $python_version"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo ""
echo "Installing requirements..."
pip install -r requirements.txt

echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "To run the pipeline:"
echo "  1. source venv/bin/activate"
echo "  2. cd scripts/pipelines"
echo "  3. bash run_metro_svi_tmux.sh"
echo ""
echo "Or for direct execution:"
echo "  python3 scripts/pipelines/metro_cities_svi_pipeline.py"
echo ""
EOF

chmod +x "$PACKAGE_DIR/setup.sh"

# Create README
echo "Creating README.md..."
cat > "$PACKAGE_DIR/README.md" << 'EOF'
# Metro Cities SVI Analysis Pipeline

**Purpose**: Analyze street view imagery from metro cities with travel survey data to estimate shade preference rates for p(shade preference | temperature) analysis.

## Quick Start

### 1. Setup

```bash
bash setup.sh
source venv/bin/activate
```

### 2. Test Pipeline (RECOMMENDED FIRST STEP)

**Before running the full pipeline, validate everything works:**

```bash
python3 scripts/pipelines/test_metro_cities_svi_pipeline.py
```

This will:
- Test **all 19 cities** with **5 images each** (~95 images total)
- Validate metadata fetch, download, analysis, and output formatting
- **Fail fast** if there are systematic errors
- Take ~5-10 minutes

**Only proceed to full run after tests pass!**

### 3. Run Full Pipeline

#### Option A: Tmux (recommended for overnight)

```bash
cd scripts/pipelines
bash run_metro_svi_tmux.sh
```

Monitor:
```bash
tmux attach -t metro_svi
# or
tail -f ../../logs/metro_svi_*.log
```

#### Option B: Direct execution

```bash
python3 scripts/pipelines/metro_cities_svi_pipeline.py \
  --output-dir ../../data/metro_cities_svi \
  --vit-model ../../models/vit_binary.pth \
  --yolo-model ../../models/yolo_best.pt
```

#### Option C: Specific cities

```bash
python3 scripts/pipelines/metro_cities_svi_pipeline.py \
  --cities "Los Angeles" "San Francisco"
```

#### Option D: Quick test mode (5 images/city, resilient)

```bash
python3 scripts/pipelines/metro_cities_svi_pipeline.py --test-mode
```

Note: Unlike the dedicated test script, this uses the same resilient error handling as the full pipeline (skips failed cities and continues).

## Cities Included (20 total)

### Recoverable surveys (7 cities):
1. **Anchorage, AK**
2. **Boston, MA**
3. **Boise, ID**
4. **Louisville, KY**
5. **Los Angeles, CA**
6. **Salt Lake City, UT**
7. **San Francisco, CA**

### Existing metro surveys (13 cities):
8. **Atlanta, GA**
9. **Cleveland, OH**
10. **Columbia, SC**
11. **Denver, CO**
12. **Evansville, IN**
13. **Honolulu, HI**
14. **Minneapolis, MN**
15. **Phoenix, AZ**
16. **Raleigh, NC**
17. **Seattle, WA**
18. **St. Louis, MO**
19. **Tucson, AZ**

## Pipeline Steps (3 Phases)

### Phase 1: Metadata Prefetch (NEW!)
- Fetches metadata for all cities upfront
- Shows total image count per city
- Provides runtime estimates (conservative/typical/optimistic)
- Waits for user confirmation before proceeding

### Phase 2: Model Initialization
- Loads ViT binary classification model
- Loads YOLO shade detection model

### Phase 3: Image Processing (with optimizations)
1. **Download images** in batches of 100 (async parallel downloads)
2. **Binary classification** using ViT model with **batch inference** (32 images at once)
3. **Shade detection** using YOLO model with **batch inference** (8 images at once, only on sunny images)
4. **Save results** incrementally after each batch
5. **Cleanup** temporary image files
6. **Resume support** - skips already-processed images if interrupted

## Output Structure

```
data/metro_cities_svi/
├── anchorage/
│   ├── anchorage_metadata.csv          # Mapillary metadata
│   └── anchorage_svi_analyzed.csv      # Analysis results
├── boston/
├── boise/
├── louisville/
├── los-angeles/
├── salt-lake-city/
├── san-francisco/
├── atlanta/
├── metro_pipeline_summary.json         # Overall statistics
└── logs/
    └── metro_svi_pipeline_*.log
```

## Output Columns

Each `{city}_svi_analyzed.csv`:

- `id` - Mapillary image ID
- `lat`, `lon` - GPS coordinates
- `captured_at` - Timestamp
- `compass_angle` - Camera direction
- `is_sunny` - Boolean sunny classification
- `sunny_probability` - Confidence score [0-1]
- `person_count` - Number of people detected
- `inshade_count` - People in shade
- `outshade_count` - People out of shade

## Performance (UPDATED with optimizations)

### Old Pipeline (sequential processing)
- ~0.1-0.3 images/second
- Would take weeks/months for millions of images

### New Pipeline (batch processing + incremental saves)
- **Download**: ~1-2 seconds/image (parallel, batches of 100)
- **Binary classification**: Batch inference on 32 images simultaneously (GPU)
- **YOLO detection**: Batch inference on 8 images simultaneously (GPU, only sunny images)
- **Overall**: ~1-2 images/second with good GPU
- **Speedup**: **5-15x faster** than old pipeline

### Estimated Runtime (20 cities, millions of images)
- **Conservative** (0.5 img/sec): ~5-23 days depending on total count
- **Typical** (1.0 img/sec): ~3-11 days with good GPU
- **Optimistic** (2.0 img/sec): ~1.5-6 days with excellent hardware

**Note**: Pipeline now shows actual estimates after metadata prefetch phase

### Key Features
- **Incremental saves**: Results saved after every 100 images
- **Resume support**: Can interrupt and restart without losing progress
- **Progress tracking**: Shows processing rate and ETA per city

## Troubleshooting

### No images found
- Increase `bbox_size` in `metro_cities_svi_pipeline.py`
- Check Mapillary coverage at https://www.mapillary.com/app/

### High download failures
- Check API rate limiting in logs
- Reduce `BATCH_SIZE`
- Verify Mapillary token

### Out of memory (GPU)
- Reduce ViT batch size in `sunny_shade_pipeline.py` (default: 32)
- For 4GB GPU: use batch_size=16
- For 8GB GPU: use batch_size=32
- For 16GB+ GPU: can try batch_size=64

### Out of memory (Disk)
- Pipeline auto-cleans after each batch (only 200MB temp storage needed)
- Check that cleanup is working properly

### Pipeline crashed / interrupted
- Simply restart with same command
- Pipeline will automatically resume from last checkpoint
- Already-processed images are skipped

### Pipeline hangs
```bash
tmux kill-session -t metro_svi
bash run_metro_svi_tmux.sh
```

### Want to skip prefetch phase
```bash
python3 scripts/pipelines/metro_cities_svi_pipeline.py --skip-prefetch
```

## Requirements

- Python 3.8+
- CUDA-capable GPU (recommended, 4GB+ VRAM)
- ~20GB free disk space (temporary)
- Internet connection for Mapillary API

## Next Steps

After pipeline completes:

1. **Calculate shade preference rates** per city
2. **Merge with travel survey UTCI data**
3. **Model p(shade preference | temperature)**
4. **Update walking behavior model**

## Support

Check logs at `logs/metro_svi_*.log` for detailed error messages.
EOF

# Update model paths in pipeline script to use relative paths
echo "Updating model paths in pipeline script..."
sed -i "s|'outputs/models/vit_binary.pth'|'../../models/vit_binary.pth'|g" "$PACKAGE_DIR/scripts/pipelines/metro_cities_svi_pipeline.py"
sed -i "s|'outputs/models/sunny_batch_train4/weights/best.pt'|'../../models/yolo_best.pt'|g" "$PACKAGE_DIR/scripts/pipelines/metro_cities_svi_pipeline.py"

# Update tmux script paths
sed -i "s|/home/kieran/Documents/Python/sunny_day_SVI|$(pwd)/../..|g" "$PACKAGE_DIR/scripts/pipelines/run_metro_svi_tmux.sh"
sed -i "s|scripts/pipelines/metro_cities_svi_pipeline.py|metro_cities_svi_pipeline.py|g" "$PACKAGE_DIR/scripts/pipelines/run_metro_svi_tmux.sh"
sed -i "s|logs/metro_svi|../../logs/metro_svi|g" "$PACKAGE_DIR/scripts/pipelines/run_metro_svi_tmux.sh"
sed -i "s|data/metro_cities_svi|../../data/metro_cities_svi|g" "$PACKAGE_DIR/scripts/pipelines/run_metro_svi_tmux.sh"
sed -i "s|outputs/models/vit_binary.pth|../../models/vit_binary.pth|g" "$PACKAGE_DIR/scripts/pipelines/run_metro_svi_tmux.sh"
sed -i "s|outputs/models/sunny_batch_train4/weights/best.pt|../../models/yolo_best.pt|g" "$PACKAGE_DIR/scripts/pipelines/run_metro_svi_tmux.sh"

# Create tarball
echo ""
echo "Creating tarball..."
cd "$BASE_DIR"
tar -czf "$OUTPUT_TAR" -C "$BASE_DIR" "metro_svi_package"

# Get file size
TARBALL_SIZE=$(du -h "$BASE_DIR/$OUTPUT_TAR" | cut -f1)

# Clean up package directory
echo "Cleaning up..."
rm -rf "$PACKAGE_DIR"

# Show results
echo ""
echo "========================================"
echo "Package Created Successfully!"
echo "========================================"
echo ""
echo "Output file: $BASE_DIR/$OUTPUT_TAR"
echo "Size: $TARBALL_SIZE"
echo ""
echo "Contents:"
tar -tzf "$BASE_DIR/$OUTPUT_TAR" | head -30
echo "..."
echo ""
echo "To deploy:"
echo "  1. Transfer $OUTPUT_TAR to target machine"
echo "  2. Extract: tar -xzf $(basename $OUTPUT_TAR)"
echo "  3. cd metro_svi_package"
echo "  4. bash setup.sh"
echo "  5. cd scripts/pipelines && bash run_metro_svi_tmux.sh"
echo ""
echo "The pipeline will:"
echo "  - Download SVI imagery for 8 metro cities"
echo "  - Classify images as sunny/not sunny"
echo "  - Detect people in shade vs out of shade"
echo "  - Save results to data/metro_cities_svi/"
echo ""
echo "Expected runtime: 8-16 hours (overnight run recommended)"
echo ""
