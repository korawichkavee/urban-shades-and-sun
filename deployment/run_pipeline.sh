#!/bin/bash
# ABOUTME: Runs the sunny/shade pipeline on all city walkable images
# ABOUTME: Processes images and merges results into walkable CSV files

set -e

echo "========================================"
echo "Running Sunny/Shade Analysis Pipeline"
echo "========================================"
echo ""

# Activate virtual environment
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found!"
    echo "Please run setup.sh first."
    exit 1
fi

source venv/bin/activate

# Check if data directory exists
if [ ! -d "data" ]; then
    echo "Error: data directory not found!"
    echo "Expected structure:"
    echo "  data/"
    echo "    Buenos-Airesimg/walkable_images/"
    echo "    Buenos-Aires_walkable_*.csv"
    echo "    ..."
    exit 1
fi

# Run the processing script
echo "Starting pipeline processing..."
echo "This will process all city walkable images."
echo "On GPU, this should take approximately 10-20 minutes."
echo ""

python3 process_walkable_cities.py

echo ""
echo "========================================"
echo "Processing Complete!"
echo "========================================"
echo ""
echo "Updated CSV files are in the data/ directory."
echo "Each walkable CSV now includes columns:"
echo "  - is_sunny: Boolean sunny classification"
echo "  - sunny_probability: Model confidence (0-1)"
echo "  - person_count: Count of person detections"
echo "  - inshade_count: People in shade"
echo "  - outshade_count: People out of shade"
echo ""
