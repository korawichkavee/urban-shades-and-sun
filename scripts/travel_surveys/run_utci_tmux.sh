#!/bin/bash
# ABOUTME: Launches UTCI annotation in tmux with completion notification.
# ABOUTME: Creates detachable session with logging and sends notification when done.

set -e

PROJECT_ROOT="/home/kieran/Documents/Python/sunny_day_SVI"
SESSION_NAME="nhts_utci_annotation"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$PROJECT_ROOT/logs/tmux_utci_$TIMESTAMP.log"

cd "$PROJECT_ROOT"

# Check if session already exists
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "Session '$SESSION_NAME' already exists!"
    echo "Options:"
    echo "  1. Attach to existing session: tmux attach -t $SESSION_NAME"
    echo "  2. Kill existing session: tmux kill-session -t $SESSION_NAME"
    exit 1
fi

echo "============================================================"
echo "Starting UTCI annotation in tmux session: $SESSION_NAME"
echo "Started: $(date)"
echo "Log file: $LOG_FILE"
echo "============================================================"
echo ""
echo "Commands:"
echo "  Attach to session:  tmux attach -t $SESSION_NAME"
echo "  Detach: Press Ctrl+B, then D"
echo "  Kill session: tmux kill-session -t $SESSION_NAME"
echo ""
echo "The session will run in background. You'll be notified on completion."
echo ""

# Create tmux session and run the pipeline
tmux new-session -d -s "$SESSION_NAME" bash -c "
    cd '$PROJECT_ROOT'
    source .venv/bin/activate

    echo '============================================================'
    echo 'NHTS UTCI Annotation Pipeline'
    echo 'Started: \$(date)'
    echo '============================================================'
    echo ''

    # Run the chunked UTCI annotation
    python scripts/travel_surveys/add_utci_chunked.py \
        --input data/transit_surveys/processed/nhts_2017_standardized.csv \
        --workers 12 \
        --checkpoint-interval 5000 2>&1 | tee '$LOG_FILE'

    EXIT_CODE=\${PIPESTATUS[0]}

    echo ''
    echo '============================================================'
    echo 'Pipeline finished'
    echo 'Completed: \$(date)'
    echo 'Exit code: '\$EXIT_CODE
    echo '============================================================'

    # Send notification
    if [ \$EXIT_CODE -eq 0 ]; then
        notify-send -u normal 'NHTS Pipeline Complete' 'UTCI annotation finished successfully' 2>/dev/null || true
        echo ''
        echo 'SUCCESS: Pipeline completed. Output ready for visualization.'
    else
        notify-send -u critical 'NHTS Pipeline Failed' 'Check logs for details' 2>/dev/null || true
        echo ''
        echo 'FAILED: Pipeline encountered errors. Check log: $LOG_FILE'
    fi

    echo ''
    echo 'Press Enter to close this tmux session, or Ctrl+B D to detach...'
    read
"

echo "Session started! Log file: $LOG_FILE"
echo ""
echo "Monitor progress:"
echo "  tail -f $LOG_FILE"
echo ""
echo "Or attach to the session:"
echo "  tmux attach -t $SESSION_NAME"
