#!/bin/bash
# ABOUTME: Runs hot cities metadata download process in tmux session
# ABOUTME: Downloads only CSV metadata files, not the actual images

SESSION_NAME="hot_cities_download"

# Check if session already exists
tmux has-session -t $SESSION_NAME 2>/dev/null

if [ $? == 0 ]; then
    echo "Session '$SESSION_NAME' already exists. Attaching..."
    tmux attach -t $SESSION_NAME
    exit 0
fi

# Create new tmux session
echo "Creating tmux session: $SESSION_NAME"
echo "================================"

# Create session and run metadata download
tmux new-session -d -s $SESSION_NAME -n "metadata"

# Set working directory and run metadata download
tmux send-keys -t $SESSION_NAME:metadata "cd /home/kieran/Documents/Python/sunny_day_SVI" C-m
tmux send-keys -t $SESSION_NAME:metadata "source .venv/bin/activate" C-m
tmux send-keys -t $SESSION_NAME:metadata "echo 'Starting metadata download...'" C-m
tmux send-keys -t $SESSION_NAME:metadata "python download_hot_cities.py 2>&1 | tee hot_cities_metadata.log" C-m
tmux send-keys -t $SESSION_NAME:metadata "echo 'Metadata download complete!'" C-m

echo "Session created successfully!"
echo ""
echo "To attach to the session, run:"
echo "  tmux attach -t $SESSION_NAME"
echo ""
echo "To detach from the session while it's running:"
echo "  Press Ctrl+B, then D"
echo ""
echo "To check status without attaching:"
echo "  tmux capture-pane -t $SESSION_NAME -p"
echo ""
echo "To kill the session:"
echo "  tmux kill-session -t $SESSION_NAME"
