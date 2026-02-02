#!/bin/bash
# ABOUTME: Run metro cities SVI analysis pipeline in tmux session
# ABOUTME: Processes street view imagery for all metro cities with travel survey data

SESSION_NAME="metro_svi"

# Kill existing session if it exists
tmux kill-session -t $SESSION_NAME 2>/dev/null

# Create log directory
mkdir -p logs

# Create new tmux session
tmux new-session -d -s $SESSION_NAME

# Run metro SVI pipeline
tmux send-keys -t $SESSION_NAME "cd /home/kieran/Documents/Python/sunny_day_SVI" C-m
tmux send-keys -t $SESSION_NAME "source .venv/bin/activate" C-m
tmux send-keys -t $SESSION_NAME "python3 scripts/pipelines/metro_cities_svi_pipeline.py \
  --output-dir data/metro_cities_svi \
  --vit-model outputs/models/vit_binary.pth \
  --yolo-model outputs/models/sunny_batch_train4/weights/best.pt \
  2>&1 | tee logs/metro_svi_\$(date +%Y%m%d_%H%M%S).log" C-m

echo "✓ Metro cities SVI pipeline started in tmux session '$SESSION_NAME'"
echo ""
echo "Monitor with: tmux attach -t $SESSION_NAME"
echo "Check status: tmux capture-pane -t $SESSION_NAME -p | tail -20"
echo "View logs: tail -f logs/metro_svi_*.log"
echo ""
echo "Cities being processed (20 total):"
echo "  Recoverable surveys (7):"
echo "    - Anchorage, AK"
echo "    - Boston, MA"
echo "    - Boise, ID"
echo "    - Louisville, KY"
echo "    - Los Angeles, CA"
echo "    - Salt Lake City, UT"
echo "    - San Francisco, CA"
echo ""
echo "  Existing surveys (13):"
echo "    - Atlanta, GA"
echo "    - Cleveland, OH"
echo "    - Columbia, SC"
echo "    - Denver, CO"
echo "    - Evansville, IN"
echo "    - Honolulu, HI"
echo "    - Minneapolis, MN"
echo "    - Phoenix, AZ"
echo "    - Raleigh, NC"
echo "    - Seattle, WA"
echo "    - St. Louis, MO"
echo "    - Tucson, AZ"
