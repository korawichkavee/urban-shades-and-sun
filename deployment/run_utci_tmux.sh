#!/bin/bash
# ABOUTME: Launches enhanced UTCI batch processing in tmux for overnight runs.
# ABOUTME: Includes logging to logs/ folder with multi-day UTCI data and precipitation.

SESSION_NAME="utci_batch"
WORK_DIR="/home/kieran/Documents/Python/sunny_day_SVI"

# Check if session already exists
tmux has-session -t $SESSION_NAME 2>/dev/null

if [ $? == 0 ]; then
    echo "Session '$SESSION_NAME' already exists."
    echo "Attach with: tmux attach -t $SESSION_NAME"
    echo "Or kill it with: tmux kill-session -t $SESSION_NAME"
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p "$WORK_DIR/logs"

# Create new detached session
echo "Creating tmux session: $SESSION_NAME"
tmux new-session -d -s $SESSION_NAME

# Send commands to the session
tmux send-keys -t $SESSION_NAME "cd $WORK_DIR" C-m
tmux send-keys -t $SESSION_NAME "echo '==========================================='" C-m
tmux send-keys -t $SESSION_NAME "echo 'Enhanced UTCI Batch Processing'" C-m
tmux send-keys -t $SESSION_NAME "echo 'Started at: \$(date)'" C-m
tmux send-keys -t $SESSION_NAME "echo '==========================================='" C-m
tmux send-keys -t $SESSION_NAME "echo ''" C-m
tmux send-keys -t $SESSION_NAME "python batch_add_enhanced_utci_optimized.py" C-m

echo "Session created successfully!"
echo ""
echo "Enhanced UTCI features:"
echo "  - Current UTCI temperature"
echo "  - Prior day UTCI average"
echo "  - Next day UTCI average"
echo "  - Prior day rain (yes/no)"
echo "  - Next day rain (yes/no)"
echo ""
echo "To monitor progress:"
echo "  tmux attach -t $SESSION_NAME"
echo ""
echo "To detach from session (while inside):"
echo "  Press Ctrl+B then D"
echo ""
echo "To check if still running:"
echo "  tmux list-sessions"
echo ""
echo "Logs will be saved in: $WORK_DIR/logs/"
echo "Log files: logs/utci_batch_*.log"
