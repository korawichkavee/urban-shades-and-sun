#!/bin/bash
# ABOUTME: Launch metro shadow annotation pipeline in tmux session
# ABOUTME: This runs over the weekend to process all 13 metro areas

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
PIPELINE_SCRIPT="$PROJECT_ROOT/scripts/processing/metro_shadow_annotation_pipeline.py"

# Check if tmux session already exists
if tmux has-session -t metro_shadow 2>/dev/null; then
    echo "ERROR: tmux session 'metro_shadow' already exists"
    echo "Attach to it with: tmux attach -t metro_shadow"
    echo "Or kill it with: tmux kill-session -t metro_shadow"
    exit 1
fi

# Create new tmux session and run pipeline
echo "Starting metro shadow annotation pipeline in tmux session 'metro_shadow'..."
tmux new-session -d -s metro_shadow "cd '$PROJECT_ROOT' && '$VENV_PYTHON' '$PIPELINE_SCRIPT'"

echo ""
echo "✓ Pipeline started in background tmux session"
echo ""
echo "To monitor progress:"
echo "  tmux attach -t metro_shadow        # Attach to session (Ctrl+B, D to detach)"
echo "  tail -f logs/metro_shadow_annotation/metro_shadow_pipeline_*.log"
echo ""
echo "To check if still running:"
echo "  tmux ls                             # List sessions"
echo "  ps aux | grep metro_shadow          # Check process"
echo ""
echo "To stop pipeline:"
echo "  tmux kill-session -t metro_shadow"
echo ""
