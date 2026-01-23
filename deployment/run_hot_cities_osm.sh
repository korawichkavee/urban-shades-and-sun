#!/bin/bash
# ABOUTME: Runs OSM road snapping for hot cities in tmux session
# ABOUTME: Downloads OSM road data and snaps street view images to roads

SESSION_NAME="hot_cities_osm"

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

# Create session and run OSM snapping
tmux new-session -d -s $SESSION_NAME -n "osm_snap"

# Set working directory and run
tmux send-keys -t $SESSION_NAME:osm_snap "cd /home/kieran/Documents/Python/sunny_day_SVI" C-m
tmux send-keys -t $SESSION_NAME:osm_snap "source .venv/bin/activate" C-m
tmux send-keys -t $SESSION_NAME:osm_snap "echo 'Starting OSM road snapping for hot cities...'" C-m
tmux send-keys -t $SESSION_NAME:osm_snap "python -u process_hot_cities_osm.py 2>&1 | tee hot_cities_osm.log" C-m
tmux send-keys -t $SESSION_NAME:osm_snap "echo 'OSM snapping complete!'" C-m

echo "Session created successfully!"
echo ""
echo "To attach to the session, run:"
echo "  tmux attach -t $SESSION_NAME"
echo ""
echo "To detach from the session while it's running:"
echo "  Press Ctrl+B, then D"
echo ""
echo "To check status without attaching:"
echo "  tmux capture-pane -t $SESSION_NAME -p | tail -20"
echo ""
echo "To kill the session:"
echo "  tmux kill-session -t $SESSION_NAME"
