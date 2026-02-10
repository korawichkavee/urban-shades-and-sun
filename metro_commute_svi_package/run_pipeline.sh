#!/bin/bash
# Quick start script for running the pipeline

echo "Metro Commute-Time SVI Pipeline"
echo "================================"
echo ""
echo "This will process all 19 cities (~6M commute-time images)"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Run pipeline
python scripts/pipelines/metro_commute_svi_pipeline.py

echo ""
echo "Pipeline complete! Check outputs/metro_commute_svi/ for results."
