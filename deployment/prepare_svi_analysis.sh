#!/bin/bash
# ABOUTME: Prepares street view image data for analysis pipeline deployment
# ABOUTME: Downloads images and creates tarball for processing on remote server

set -e

# Parse command line arguments
CONFIG_FILE=""
OUTPUT_NAME=""
DOWNLOAD_IMAGES=false

usage() {
    echo "Usage: $0 -c CONFIG_FILE [-o OUTPUT_NAME] [-d]"
    echo ""
    echo "Arguments:"
    echo "  -c CONFIG_FILE    YAML config file (e.g., config/phoenix_az.yaml)"
    echo "  -o OUTPUT_NAME    Optional output name (default: derived from config)"
    echo "  -d                Download images (not just metadata)"
    echo ""
    echo "Examples:"
    echo "  $0 -c config/phoenix_az.yaml"
    echo "  $0 -c config/phoenix_az.yaml -o phoenix_test -d"
    exit 1
}

while getopts "c:o:dh" opt; do
    case $opt in
        c) CONFIG_FILE="$OPTARG" ;;
        o) OUTPUT_NAME="$OPTARG" ;;
        d) DOWNLOAD_IMAGES=true ;;
        h) usage ;;
        *) usage ;;
    esac
done

if [ -z "$CONFIG_FILE" ]; then
    echo "Error: Config file is required"
    usage
fi

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Config file not found: $CONFIG_FILE"
    exit 1
fi

# Set base directory
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BASE_DIR"

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
elif [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "Warning: No virtual environment found. Using system Python."
fi

# Derive output name from config if not specified
if [ -z "$OUTPUT_NAME" ]; then
    OUTPUT_NAME=$(basename "$CONFIG_FILE" .yaml)
fi

echo "========================================"
echo "SVI Analysis Preparation"
echo "========================================"
echo "Config: $CONFIG_FILE"
echo "Output: $OUTPUT_NAME"
echo "Download images: $DOWNLOAD_IMAGES"
echo ""

# Step 1: Fetch metadata with time filtering
echo "Step 1: Fetching street view metadata with time filtering..."
echo "----------------------------------------"
python3 scripts/data_collection/fetch_svi_with_time_filter.py "$CONFIG_FILE"

if [ $? -ne 0 ]; then
    echo "Error: Failed to fetch metadata"
    exit 1
fi

echo ""
echo "Metadata fetching complete!"
echo ""

# Step 2: Download images if requested
if [ "$DOWNLOAD_IMAGES" = true ]; then
    echo "Step 2: Downloading images..."
    echo "----------------------------------------"

    # Check if filtered CSV files exist
    OUTPUT_DIR=$(grep "output_dir:" "$CONFIG_FILE" | awk '{print $2}' | tr -d "'\"")
    if [ -z "$OUTPUT_DIR" ]; then
        OUTPUT_DIR="data/raw/svi_filtered"
    fi

    CSV_FILES=("$OUTPUT_DIR"/*.csv)
    if [ ! -e "${CSV_FILES[0]}" ]; then
        echo "Error: No CSV files found in $OUTPUT_DIR"
        exit 1
    fi

    for csv_file in "${CSV_FILES[@]}"; do
        echo "  Processing: $(basename "$csv_file")"

        # Extract city name for output directory
        city_name=$(basename "$csv_file" .csv | sed 's/_[0-9]*$//')
        image_dir="$OUTPUT_DIR/${city_name}_images"
        mkdir -p "$image_dir"

        # Run image download script
        # Note: This uses the existing download_jpegs_mapillary.py as a base
        # but we need a version that handles both sources
        python3 scripts/data_collection/download_jpegs.py \
            --input "$csv_file" \
            --output "$image_dir" \
            || echo "  Warning: Download failed for $csv_file"
    done

    echo ""
    echo "Image download complete!"
    echo ""
fi

# Step 3: Create deployment package
echo "Step 3: Creating deployment package..."
echo "----------------------------------------"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PACKAGE_DIR="$BASE_DIR/svi_analysis_package_${OUTPUT_NAME}"
OUTPUT_TAR="svi_analysis_${OUTPUT_NAME}_${TIMESTAMP}.tar.gz"

# Clean up old package directory if it exists
if [ -d "$PACKAGE_DIR" ]; then
    echo "Cleaning up old package directory..."
    rm -rf "$PACKAGE_DIR"
fi

# Create package directory structure
echo "Creating package directory structure..."
mkdir -p "$PACKAGE_DIR/data"
mkdir -p "$PACKAGE_DIR/config"

# Copy filtered data
echo "Copying filtered data..."
OUTPUT_DIR=$(grep "output_dir:" "$CONFIG_FILE" | awk '{print $2}' | tr -d "'\"")
if [ -z "$OUTPUT_DIR" ]; then
    OUTPUT_DIR="data/raw/svi_filtered"
fi

if [ -d "$OUTPUT_DIR" ]; then
    cp -r "$OUTPUT_DIR"/* "$PACKAGE_DIR/data/" || echo "Warning: No data files found"
else
    echo "Warning: Output directory not found: $OUTPUT_DIR"
fi

# Copy config file
echo "Copying config file..."
cp "$CONFIG_FILE" "$PACKAGE_DIR/config/"

# Copy necessary scripts (if needed for further processing)
echo "Copying processing scripts..."
mkdir -p "$PACKAGE_DIR/scripts"

# Copy any relevant processing scripts
if [ -f "scripts/processing/enrich_svi_metadata.py" ]; then
    cp "scripts/processing/enrich_svi_metadata.py" "$PACKAGE_DIR/scripts/"
fi

# Create README
cat > "$PACKAGE_DIR/README.md" << 'EOF'
# Street View Image Analysis Package

This package contains filtered street view image metadata ready for analysis.

## Contents

- `data/`: Filtered CSV files with street view metadata
- `config/`: Configuration files used for data collection
- `scripts/`: Processing scripts for further analysis

## Data Filtering

All images have been filtered to:
- Time of day: 8-10am or 4-6pm local time
- Sources: Mapillary and/or KartaView (as specified in config)

## Metadata Columns

Each CSV contains:
- Location data: lat, lon, city_id
- Datetime data: captured_at (Mapillary) or shotDate (KartaView), datetime_local
- Image IDs: id, sequence_id (Mapillary) or sequenceId (KartaView)
- Source: 'Mapillary' or 'KartaView'
- Additional source-specific metadata

## Next Steps

1. Run your analysis pipeline on the filtered data
2. Optionally download actual images using the image IDs
3. Perform street view image analysis (e.g., shade detection, UTCI calculations)

EOF

# Create a manifest file
echo "Creating manifest..."
cat > "$PACKAGE_DIR/MANIFEST.txt" << EOF
Package: SVI Analysis Data - $OUTPUT_NAME
Created: $(date)
Config: $(basename "$CONFIG_FILE")

Contents:
$(find "$PACKAGE_DIR/data" -name "*.csv" -exec basename {} \; | sort)

Total CSV files: $(find "$PACKAGE_DIR/data" -name "*.csv" | wc -l)
Total data rows: $(find "$PACKAGE_DIR/data" -name "*.csv" -exec wc -l {} + | tail -1 | awk '{print $1}')
EOF

# Create tarball
echo "Creating tarball..."
tar -czf "$OUTPUT_TAR" -C "$BASE_DIR" "$(basename "$PACKAGE_DIR")"

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
echo "Contents preview:"
tar -tzf "$BASE_DIR/$OUTPUT_TAR" | head -20
echo ""
echo "To deploy on remote server:"
echo "  1. Transfer $OUTPUT_TAR to remote machine"
echo "  2. Extract: tar -xzf $(basename "$OUTPUT_TAR")"
echo "  3. cd $(basename "$PACKAGE_DIR")"
echo "  4. Run your analysis pipeline on the data/ directory"
echo ""
