#!/bin/bash
# Main pipeline execution script for NYC & Seattle municipal shadow analysis

set -e  # Exit on error

echo "=========================================="
echo "NYC & Seattle Municipal Shadow Analysis"
echo "=========================================="
echo ""

# Activate virtual environment if exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Check Python
python --version || { echo "Python not found!"; exit 1; }

# Check GPU
if command -v nvidia-smi &> /dev/null; then
    echo "GPU detected:"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
else
    echo "WARNING: No GPU detected, will use CPU (very slow)"
fi

echo ""

# Run pipeline
python scripts/pipelines/municipal_shadow_pipeline.py "$@"
