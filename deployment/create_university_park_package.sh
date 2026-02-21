#!/bin/bash
# ABOUTME: Creates deployment package for University Park, PA (Penn State) SVI annotation
# ABOUTME: Packages ViT/YOLO models, pipeline scripts, and test scripts into a portable tarball

set -e

echo "========================================"
echo "Creating University Park, PA SVI Package"
echo "========================================"
echo ""

BASE_DIR="/home/kieran/Documents/Python/sunny_day_SVI"
DEPLOY_DIR="$BASE_DIR/deployment"
PACKAGE_NAME="university_park_svi_package"
PACKAGE_DIR="$BASE_DIR/$PACKAGE_NAME"
OUTPUT_TAR="$DEPLOY_DIR/university_park_svi_$(date +%Y%m%d_%H%M%S).tar.gz"

# Clean up old package directory if it exists
if [ -d "$PACKAGE_DIR" ]; then
    echo "Cleaning up old package directory..."
    rm -rf "$PACKAGE_DIR"
fi

# Create directory structure
echo "Creating package directory structure..."
mkdir -p "$PACKAGE_DIR/scripts/pipelines"
mkdir -p "$PACKAGE_DIR/scripts/data_collection"
mkdir -p "$PACKAGE_DIR/models"
mkdir -p "$PACKAGE_DIR/data"
mkdir -p "$PACKAGE_DIR/logs"
mkdir -p "$PACKAGE_DIR/outputs"

# Copy pipeline scripts
echo "Copying pipeline scripts..."
cp "$BASE_DIR/scripts/pipelines/university_park_svi_pipeline.py" "$PACKAGE_DIR/scripts/pipelines/"
cp "$BASE_DIR/scripts/pipelines/test_university_park_pipeline.py" "$PACKAGE_DIR/scripts/pipelines/"
cp "$BASE_DIR/scripts/pipelines/sunny_shade_pipeline.py" "$PACKAGE_DIR/scripts/pipelines/"
cp "$BASE_DIR/scripts/pipelines/fetch_city_boundaries.py" "$PACKAGE_DIR/scripts/pipelines/"

# Copy data collection scripts
echo "Copying data collection scripts..."
cp "$BASE_DIR/scripts/data_collection/download_mly_points.py" "$PACKAGE_DIR/scripts/data_collection/"

# Copy ViT model
echo "Copying ViT model weights..."
if [ -f "$BASE_DIR/outputs/models/vit_binary.pth" ]; then
    cp "$BASE_DIR/outputs/models/vit_binary.pth" "$PACKAGE_DIR/models/"
    echo "  Found at outputs/models/vit_binary.pth"
elif [ -f "$BASE_DIR/vit_binary.pth" ]; then
    cp "$BASE_DIR/vit_binary.pth" "$PACKAGE_DIR/models/"
    echo "  Found at vit_binary.pth"
else
    echo "ERROR: vit_binary.pth not found!"
    echo "       Required for sunny/cloudy classification"
    exit 1
fi

# Copy YOLO model
echo "Copying YOLO model weights..."
if [ -f "$BASE_DIR/outputs/models/sunny_batch_train4/weights/best.pt" ]; then
    cp "$BASE_DIR/outputs/models/sunny_batch_train4/weights/best.pt" "$PACKAGE_DIR/models/yolo_best.pt"
    echo "  Found at outputs/models/sunny_batch_train4/weights/best.pt"
else
    echo "ERROR: YOLO model weights not found at outputs/models/sunny_batch_train4/weights/best.pt"
    exit 1
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
pyogrio>=0.6.0

# Timezone support
pytz>=2023.0
EOF

# Create setup.sh
echo "Creating setup.sh..."
cat > "$PACKAGE_DIR/setup.sh" << 'EOF'
#!/bin/bash
# Setup script for University Park, PA SVI pipeline

echo "========================================"
echo "University Park SVI Pipeline Setup"
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
echo "  Python $python_version OK"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip -q

echo ""
echo "Installing requirements..."
pip install -r requirements.txt

echo ""
echo "========================================"
echo "Setup complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "  1. source venv/bin/activate"
echo "  2. python scripts/pipelines/test_university_park_pipeline.py"
echo "  3. If tests pass, run the full pipeline:"
echo "     python scripts/pipelines/university_park_svi_pipeline.py"
echo ""
EOF
chmod +x "$PACKAGE_DIR/setup.sh"

# Create run_pipeline.sh
echo "Creating run_pipeline.sh..."
cat > "$PACKAGE_DIR/run_pipeline.sh" << 'EOF'
#!/bin/bash
# Run the University Park, PA SVI analysis pipeline

echo "University Park, PA SVI Pipeline"
echo "================================="
echo ""

# Activate virtual environment if present
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run full pipeline
python scripts/pipelines/university_park_svi_pipeline.py \
    --output-dir data/university_park_svi \
    --vit-model models/vit_binary.pth \
    --yolo-model models/yolo_best.pt

echo ""
echo "Pipeline complete. Results: data/university_park_svi/"
EOF
chmod +x "$PACKAGE_DIR/run_pipeline.sh"

# Create run_pipeline_tmux.sh for overnight/background runs
echo "Creating run_pipeline_tmux.sh..."
cat > "$PACKAGE_DIR/run_pipeline_tmux.sh" << 'EOF'
#!/bin/bash
# Run University Park, PA SVI pipeline in a detached tmux session

SESSION="upk_svi"

# Kill existing session if present
tmux kill-session -t "$SESSION" 2>/dev/null || true

mkdir -p logs

echo "Starting pipeline in tmux session '$SESSION'..."
tmux new-session -d -s "$SESSION" \
    "source venv/bin/activate 2>/dev/null || true; \
     python scripts/pipelines/university_park_svi_pipeline.py \
       --output-dir data/university_park_svi \
       --vit-model models/vit_binary.pth \
       --yolo-model models/yolo_best.pt \
       2>&1 | tee logs/university_park_svi_$(date +%Y%m%d_%H%M%S).log"

echo ""
echo "Pipeline running in background."
echo ""
echo "Monitor with:"
echo "  tmux attach -t $SESSION"
echo "  tail -f logs/university_park_svi_*.log"
echo ""
echo "Stop with:"
echo "  tmux kill-session -t $SESSION"
EOF
chmod +x "$PACKAGE_DIR/run_pipeline_tmux.sh"

# Create run_test.sh
echo "Creating run_test.sh..."
cat > "$PACKAGE_DIR/run_test.sh" << 'EOF'
#!/bin/bash
# Run the small-scale validation test before the full pipeline

echo "University Park, PA SVI Pipeline Test"
echo "======================================"
echo ""
echo "This validates the full pipeline with ~5 images."
echo "Run this before the full pipeline to check setup."
echo ""

if [ -d "venv" ]; then
    source venv/bin/activate
fi

python scripts/pipelines/test_university_park_pipeline.py
EOF
chmod +x "$PACKAGE_DIR/run_test.sh"

# Create README.md
echo "Creating README.md..."
cat > "$PACKAGE_DIR/README.md" << 'EOFREADME'
# University Park, PA SVI Analysis Package

Analyzes Mapillary street view imagery in University Park, PA (Penn State area)
to classify images as sunny/not-sunny and detect people in/out of shade.

## What's Included

- **ML Models**: Pre-trained ViT (sunny/cloudy) and YOLO (shade detection)
- **Pipeline Script**: `university_park_svi_pipeline.py`
- **Test Script**: `test_university_park_pipeline.py` — validates setup before full run
- **Helper Scripts**: `setup.sh`, `run_test.sh`, `run_pipeline.sh`, `run_pipeline_tmux.sh`

## Quick Start

### 1. Install Dependencies

```bash
bash setup.sh
source venv/bin/activate
```

### 2. Run Tests (STRONGLY RECOMMENDED)

Before running the full pipeline, validate that everything works:

```bash
bash run_test.sh
```

This downloads ~5 images and runs the full analysis chain. Takes 2-5 minutes.
**Only proceed to the full run after tests pass.**

### 3. Run Full Pipeline

#### Option A: Direct (interactive)

```bash
bash run_pipeline.sh
```

#### Option B: Background with tmux (recommended for overnight)

```bash
bash run_pipeline_tmux.sh
```

Monitor progress:
```bash
tmux attach -t upk_svi
# or
tail -f logs/university_park_svi_*.log
```

#### Option C: Direct Python (custom options)

```bash
python scripts/pipelines/university_park_svi_pipeline.py \
    --output-dir data/university_park_svi \
    --vit-model models/vit_binary.pth \
    --yolo-model models/yolo_best.pt
```

## Pipeline Steps

1. **Metadata fetch** — downloads image IDs and coordinates from Mapillary
   for University Park, PA using the OSM boundary (or 10km bbox fallback)
2. **Image download** — async batch download from Mapillary Graph API
3. **ViT classification** — classifies each image as sunny/not-sunny (batch inference)
4. **YOLO detection** — detects people in/out of shade on sunny images (batch inference)
5. **Incremental save** — results saved after every batch; pipeline is resumable

## Output

Results are saved to `data/university_park_svi/university-park/`:

- `university-park_metadata.csv` — Mapillary metadata (image IDs, lat/lon, timestamps)
- `university-park_svi_analyzed.csv` — Analysis results

Output columns:
- `id` — Mapillary image ID
- `lat`, `lon` — GPS coordinates
- `captured_at` — Timestamp
- `is_sunny` — Boolean sunny classification
- `sunny_probability` — ViT confidence score [0-1]
- `person_count` — People detected
- `inshade_count` — People in shade
- `outshade_count` — People out of shade

A `university_park_pipeline_summary.json` is also saved with overall statistics.

## System Requirements

**Minimum:**
- Python 3.8+
- 8GB RAM
- 10GB free disk space
- GPU with 4GB VRAM (or CPU mode, much slower)

**Recommended:**
- Python 3.10+
- 16GB+ RAM
- GPU with 8GB+ VRAM

## Troubleshooting

**Out of GPU memory:** Reduce batch sizes in `scripts/pipelines/sunny_shade_pipeline.py`
(ViT default: 128, YOLO default: 32)

**Rate limiting (429 errors):** The pipeline retries with exponential backoff automatically.
If persistent, reduce `max_concurrent` in `download_images_batch_async`.

**Resume after interruption:** Re-run the same command. The pipeline checks for already-
processed images and skips them.

**No images found in test area:** University Park is a small borough. If OSM boundary
lookup fails, the pipeline falls back to a 0.15-degree (~10km) bounding box.
EOFREADME

# Create the tarball
echo ""
echo "Creating tarball..."
cd "$BASE_DIR"
tar -czf "$OUTPUT_TAR" -C "$BASE_DIR" "$PACKAGE_NAME"

TARBALL_SIZE=$(du -h "$OUTPUT_TAR" | cut -f1)

# Clean up staging directory
echo "Cleaning up staging directory..."
rm -rf "$PACKAGE_DIR"

echo ""
echo "========================================"
echo "Package Created Successfully!"
echo "========================================"
echo ""
echo "Location: $OUTPUT_TAR"
echo "Size:     $TARBALL_SIZE"
echo ""
echo "Contents:"
tar -tzf "$OUTPUT_TAR"
echo ""
echo "To deploy:"
echo "  1. Transfer $OUTPUT_TAR to target machine"
echo "  2. tar -xzf $(basename $OUTPUT_TAR)"
echo "  3. cd $PACKAGE_NAME"
echo "  4. bash setup.sh"
echo "  5. bash run_test.sh      # validate first"
echo "  6. bash run_pipeline_tmux.sh"
echo ""
