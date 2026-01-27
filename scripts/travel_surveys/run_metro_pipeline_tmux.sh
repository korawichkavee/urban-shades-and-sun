#!/bin/bash
# ABOUTME: Runs complete metro survey pipeline in tmux with logging and notifications.
# ABOUTME: Processes surveys, annotates with UTCI, and creates visualizations.

set -e

PROJECT_ROOT="/home/kieran/Documents/Python/sunny_day_SVI"
SESSION_NAME="metro_survey_pipeline"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$PROJECT_ROOT/logs/metro_pipeline_$TIMESTAMP.log"

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
echo "Starting Metro Survey Pipeline in tmux session: $SESSION_NAME"
echo "Started: $(date)"
echo "Log file: $LOG_FILE"
echo "============================================================"
echo ""
echo "Pipeline steps:"
echo "  1. Process and standardize all metro surveys"
echo "  2. Add geographic locations using random sampling"
echo "  3. Annotate trips with UTCI data (with exponential backoff)"
echo "  4. Create scatter plots by city"
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
    echo 'METRO SURVEY PIPELINE'
    echo 'Started: '\$(date)
    echo '============================================================'
    echo ''

    # Step 1: Annotate merged surveys with datetime and location
    echo '============================================================'
    echo 'STEP 1: Annotating Merged Surveys'
    echo '============================================================'
    python scripts/travel_surveys/annotate_merged_surveys.py 2>&1 | tee '$LOG_FILE'
    STEP1_EXIT=\${PIPESTATUS[0]}

    if [ \$STEP1_EXIT -ne 0 ]; then
        echo ''
        echo 'ERROR: Survey annotation failed!'
        notify-send -u critical 'Metro Pipeline Failed' 'Survey annotation error' 2>/dev/null || true
        exit 1
    fi

    echo ''
    echo 'Survey annotation complete!'
    echo ''

    # Step 2: Annotate with UTCI (chunked with checkpointing)
    echo '============================================================'
    echo 'STEP 2: Annotating with UTCI Data'
    echo '============================================================'
    python scripts/travel_surveys/add_utci_chunked.py \\
        --input data/transit_surveys/processed/metro_surveys_standardized.csv \\
        --output data/transit_surveys/processed/metro_surveys_with_utci.csv \\
        --workers 12 \\
        --checkpoint-interval 5000 2>&1 | tee -a '$LOG_FILE'
    STEP2_EXIT=\${PIPESTATUS[0]}

    if [ \$STEP2_EXIT -ne 0 ]; then
        echo ''
        echo 'ERROR: UTCI annotation failed!'
        notify-send -u critical 'Metro Pipeline Failed' 'UTCI annotation error' 2>/dev/null || true
        exit 1
    fi

    echo ''
    echo 'UTCI annotation complete!'
    echo ''

    # Step 3: Create visualizations
    echo '============================================================'
    echo 'STEP 3: Creating Visualizations'
    echo '============================================================'
    python scripts/travel_surveys/visualize_metro_surveys.py \\
        --input data/transit_surveys/processed/metro_surveys_with_utci.csv \\
        --output-dir results/metro_surveys 2>&1 | tee -a '$LOG_FILE'
    STEP3_EXIT=\${PIPESTATUS[0]}

    if [ \$STEP3_EXIT -ne 0 ]; then
        echo ''
        echo 'WARNING: Visualization failed, but data is ready'
        notify-send -u normal 'Metro Pipeline Partial Success' 'Data ready, visualization failed' 2>/dev/null || true
    else
        echo ''
        echo 'Visualizations complete!'
    fi

    echo ''
    echo '============================================================'
    echo 'PIPELINE COMPLETE'
    echo 'Completed: '\$(date)
    echo '============================================================'
    echo ''
    echo 'Output files:'
    echo '  - data/transit_surveys/processed/metro_surveys_standardized.csv'
    echo '  - data/transit_surveys/processed/metro_surveys_with_utci.csv'
    echo '  - results/metro_surveys/*.png'
    echo ''
    echo 'Log file: $LOG_FILE'
    echo ''

    # Send notification
    notify-send -u normal 'Metro Survey Pipeline Complete' 'All steps finished successfully' 2>/dev/null || true

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
