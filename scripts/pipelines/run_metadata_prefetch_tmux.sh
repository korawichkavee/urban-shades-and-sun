#!/bin/bash
# ABOUTME: Run metadata prefetch phase in tmux to get time estimates
# ABOUTME: Fetches city boundaries and counts images for all metro cities

SESSION_NAME="metro_prefetch"

# Kill existing session if it exists
tmux kill-session -t $SESSION_NAME 2>/dev/null

# Create log directory
mkdir -p logs

# Create new tmux session
tmux new-session -d -s $SESSION_NAME

# Run metadata prefetch only
tmux send-keys -t $SESSION_NAME "cd /home/kieran/Documents/Python/sunny_day_SVI" C-m
tmux send-keys -t $SESSION_NAME "source .venv/bin/activate" C-m
tmux send-keys -t $SESSION_NAME "python3 scripts/pipelines/metro_cities_svi_pipeline.py \
  --output-dir data/metro_cities_svi \
  2>&1 | tee logs/metro_prefetch_\$(date +%Y%m%d_%H%M%S).log" C-m

echo "✓ Metadata prefetch started in tmux session '$SESSION_NAME'"
echo ""
echo "This will:"
echo "  1. Fetch actual city boundaries from OpenStreetMap (19 cities)"
echo "  2. Get bounding boxes for each city"
echo "  3. Fetch image metadata from Mapillary within boundaries"
echo "  4. Filter images to only those within city limits"
echo "  5. Calculate total image counts and provide time estimates"
echo ""
echo "Monitor with: tmux attach -t $SESSION_NAME"
echo "Check logs: tail -f logs/metro_prefetch_*.log"
echo ""
echo "Estimated time: 10-30 minutes for metadata prefetch"
echo ""
echo "After completion, press any key when prompted to see time estimates,"
echo "or Ctrl+C to abort before starting the full pipeline."
echo ""
