#!/bin/bash
# ABOUTME: Start UTCI annotation for recoverable surveys in tmux session
# ABOUTME: Uses 15 workers with API key from config for rate limit compliance

SESSION_NAME="utci_recoverable"
WORKERS=15

# Kill existing session if it exists
tmux kill-session -t $SESSION_NAME 2>/dev/null

# Create log directory
mkdir -p logs

# Create new tmux session
tmux new-session -d -s $SESSION_NAME

# Run UTCI annotation
tmux send-keys -t $SESSION_NAME "cd /home/kieran/Documents/Python/sunny_day_SVI" C-m
tmux send-keys -t $SESSION_NAME "source .venv/bin/activate" C-m
tmux send-keys -t $SESSION_NAME "python3 scripts/travel_surveys/add_utci_deduped.py \
  --input data/transit_surveys/processed/recoverable_surveys_ready_for_utci_clean.csv \
  --output data/transit_surveys/processed/recoverable_surveys_with_utci.csv \
  --workers $WORKERS \
  --checkpoint-interval 1000 \
  2>&1 | tee logs/utci_recoverable_\$(date +%Y%m%d_%H%M%S).log" C-m

echo "✓ UTCI annotation started in tmux session '$SESSION_NAME' with $WORKERS workers"
echo ""
echo "Monitor with: tmux attach -t $SESSION_NAME"
echo "Check status: tmux capture-pane -t $SESSION_NAME -p | tail -20"
echo "View logs: tail -f logs/utci_recoverable_*.log"
