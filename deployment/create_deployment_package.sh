#!/bin/bash
# ABOUTME: Creates portable deployment tarball for sunny/shade pipeline
# ABOUTME: Packages models, scripts, and dependencies for GPU machine deployment

set -e

echo "========================================"
echo "Creating Sunny/Shade Pipeline Package"
echo "========================================"
echo ""

# Set base directory
BASE_DIR="/home/kieran/Documents/Python/sunny_day_SVI"
DEPLOY_DIR="$BASE_DIR/deployment"
PACKAGE_DIR="$BASE_DIR/sunny_shade_pipeline_package"
OUTPUT_TAR="sunny_shade_pipeline_$(date +%Y%m%d_%H%M%S).tar.gz"

# Clean up old package directory if it exists
if [ -d "$PACKAGE_DIR" ]; then
    echo "Cleaning up old package directory..."
    rm -rf "$PACKAGE_DIR"
fi

# Create package directory structure
echo "Creating package directory structure..."
mkdir -p "$PACKAGE_DIR/models"
mkdir -p "$PACKAGE_DIR/data"

# Copy pipeline script
echo "Copying pipeline script..."
if [ ! -f "$BASE_DIR/sunny_shade_pipeline.py" ]; then
    echo "Error: sunny_shade_pipeline.py not found!"
    exit 1
fi
cp "$BASE_DIR/sunny_shade_pipeline.py" "$PACKAGE_DIR/"

# Copy processing script
echo "Copying processing script..."
cp "$DEPLOY_DIR/process_walkable_cities.py" "$PACKAGE_DIR/"

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

# Copy walkable images and CSVs for each city
echo "Copying city data (images and CSVs)..."
CITY_SAMPLE="$BASE_DIR/city7sample"

# Buenos Aires
if [ -d "$CITY_SAMPLE/Buenos-Airesimg/walkable_images" ]; then
    echo "  - Buenos Aires images..."
    mkdir -p "$PACKAGE_DIR/data/Buenos-Airesimg"
    cp -r "$CITY_SAMPLE/Buenos-Airesimg/walkable_images" "$PACKAGE_DIR/data/Buenos-Airesimg/"
    cp "$CITY_SAMPLE/Buenos-Aires_walkable_"*.csv "$PACKAGE_DIR/data/" 2>/dev/null || echo "    Warning: Buenos Aires CSV not found"
fi

# Cape Town
if [ -d "$CITY_SAMPLE/Cape-Townimg/walkable_images" ]; then
    echo "  - Cape Town images..."
    mkdir -p "$PACKAGE_DIR/data/Cape-Townimg"
    cp -r "$CITY_SAMPLE/Cape-Townimg/walkable_images" "$PACKAGE_DIR/data/Cape-Townimg/"
    cp "$CITY_SAMPLE/Cape-Town_walkable_"*.csv "$PACKAGE_DIR/data/" 2>/dev/null || echo "    Warning: Cape Town CSV not found"
fi

# Istanbul
if [ -d "$CITY_SAMPLE/Istanbulimg/walkable_images" ]; then
    echo "  - Istanbul images..."
    mkdir -p "$PACKAGE_DIR/data/Istanbulimg"
    cp -r "$CITY_SAMPLE/Istanbulimg/walkable_images" "$PACKAGE_DIR/data/Istanbulimg/"
    cp "$CITY_SAMPLE/Istanbul_walkable_"*.csv "$PACKAGE_DIR/data/" 2>/dev/null || echo "    Warning: Istanbul CSV not found"
fi

# Madrid
if [ -d "$CITY_SAMPLE/Madridimg/walkable_images" ]; then
    echo "  - Madrid images..."
    mkdir -p "$PACKAGE_DIR/data/Madridimg"
    cp -r "$CITY_SAMPLE/Madridimg/walkable_images" "$PACKAGE_DIR/data/Madridimg/"
    cp "$CITY_SAMPLE/Madrid_walkable_"*.csv "$PACKAGE_DIR/data/" 2>/dev/null || echo "    Warning: Madrid CSV not found"
fi

# Mumbai
if [ -d "$CITY_SAMPLE/Mumbaiimg/walkable_images" ]; then
    echo "  - Mumbai images..."
    mkdir -p "$PACKAGE_DIR/data/Mumbaiimg"
    cp -r "$CITY_SAMPLE/Mumbaiimg/walkable_images" "$PACKAGE_DIR/data/Mumbaiimg/"
    cp "$CITY_SAMPLE/Mumbai_walkable_"*.csv "$PACKAGE_DIR/data/" 2>/dev/null || echo "    Warning: Mumbai CSV not found"
fi

# Singapore
if [ -d "$CITY_SAMPLE/Singaporeimg/walkable_images" ]; then
    echo "  - Singapore images..."
    mkdir -p "$PACKAGE_DIR/data/Singaporeimg"
    cp -r "$CITY_SAMPLE/Singaporeimg/walkable_images" "$PACKAGE_DIR/data/Singaporeimg/"
    cp "$CITY_SAMPLE/Singapore_walkable_"*.csv "$PACKAGE_DIR/data/" 2>/dev/null || echo "    Warning: Singapore CSV not found"
fi

# Copy deployment files
echo "Copying deployment files..."
cp "$DEPLOY_DIR/requirements.txt" "$PACKAGE_DIR/"
cp "$DEPLOY_DIR/setup.sh" "$PACKAGE_DIR/"
cp "$DEPLOY_DIR/run_pipeline.sh" "$PACKAGE_DIR/"
cp "$DEPLOY_DIR/README.md" "$PACKAGE_DIR/"

# Make scripts executable
chmod +x "$PACKAGE_DIR/setup.sh"
chmod +x "$PACKAGE_DIR/run_pipeline.sh"

# Update sunny_shade_pipeline.py to use relative model paths
echo "Updating model paths in pipeline script..."
sed -i 's|vit_binary.pth|models/vit_binary.pth|g' "$PACKAGE_DIR/sunny_shade_pipeline.py"
sed -i 's|sunny_batch_train4/weights/best.pt|models/yolo_best.pt|g' "$PACKAGE_DIR/sunny_shade_pipeline.py"

# Create tarball
echo "Creating tarball..."
cd "$BASE_DIR"
tar -czf "$OUTPUT_TAR" -C "$BASE_DIR" "sunny_shade_pipeline_package"

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
echo "Size: $(du -h "$BASE_DIR/$OUTPUT_TAR" | cut -f1)"
echo ""
echo "Contents:"
tar -tzf "$BASE_DIR/$OUTPUT_TAR" | head -20
echo ""
echo "To deploy on GPU machine:"
echo "  1. Transfer $OUTPUT_TAR to GPU machine"
echo "  2. Extract: tar -xzf $(basename $OUTPUT_TAR)"
echo "  3. cd sunny_shade_pipeline_package"
echo "  4. Run: bash setup.sh"
echo "  5. Run: bash run_pipeline.sh"
echo ""
echo "The pipeline will process all city images and update the CSVs in data/"
echo ""
