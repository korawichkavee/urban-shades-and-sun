#!/bin/bash
# ABOUTME: Launches weather data processing in tmux session for overnight running
# ABOUTME: Creates detachable session that survives terminal disconnection

set -e

cd "$(dirname "$0")"

SESSION_NAME="weather_processing"

# Check if session already exists
if tmux has-session -t $SESSION_NAME 2>/dev/null; then
    echo "Session '$SESSION_NAME' already exists!"
    echo ""
    echo "Options:"
    echo "  1. Attach to existing session: tmux attach -t $SESSION_NAME"
    echo "  2. Kill and restart: tmux kill-session -t $SESSION_NAME && $0"
    exit 1
fi

echo "Creating tmux session: $SESSION_NAME"
echo ""
echo "The session will run in the background."
echo "To attach and view progress:"
echo "  tmux attach -t $SESSION_NAME"
echo ""
echo "To detach (leave running in background):"
echo "  Press Ctrl+B, then D"
echo ""
echo "Starting in 3 seconds..."
sleep 3

# Create new tmux session and run script
tmux new-session -d -s $SESSION_NAME "python3 add_weather_overnight.py; echo 'Processing complete. Press any key to exit.'; read"

echo ""
echo "Session started! Attaching now..."
echo "(Press Ctrl+B, then D to detach and leave running in background)"
sleep 2

# Attach to the session
tmux attach -t $SESSION_NAME
