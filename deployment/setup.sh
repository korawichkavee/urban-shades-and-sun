#!/bin/bash
# ABOUTME: Setup script for sunny/shade pipeline on GPU machine
# ABOUTME: Creates virtual environment and installs dependencies

set -e

echo "========================================"
echo "Sunny/Shade Pipeline Setup"
echo "========================================"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed"
    exit 1
fi

echo "Python version:"
python3 --version
echo ""

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "To activate the environment in the future, run:"
echo "  source venv/bin/activate"
echo ""
echo "To process images, run:"
echo "  python3 sunny_shade_pipeline.py <image_folder> -o <output.csv>"
echo ""
echo "For GPU acceleration, ensure CUDA is available."
echo "The pipeline will automatically use GPU if detected."
echo ""
