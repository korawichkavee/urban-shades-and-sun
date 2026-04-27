#!/bin/bash
# Pre-flight test script

set -e

echo "=========================================="
echo "Running Pre-Flight Tests"
echo "=========================================="
echo ""

# Activate venv
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run tests
python scripts/pipelines/test_municipal_pipeline.py

echo ""
