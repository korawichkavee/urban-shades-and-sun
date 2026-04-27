#!/bin/bash
# Tmux script to analyze metro areas for seasonal bias in parallel
# Runs pre-scan analysis to identify cities with good seasonal balance

SESSION_NAME="metro_prescan"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/analysis/download_and_analyze_metro_seasonal_bias.py"
VENV_PYTHON="$SCRIPT_DIR/../.venv/bin/python"

# Check if session already exists
tmux has-session -t $SESSION_NAME 2>/dev/null

if [ $? == 0 ]; then
    echo "Session '$SESSION_NAME' already exists. Attaching..."
    tmux attach-session -t $SESSION_NAME
    exit 0
fi

# Create new session
echo "Creating tmux session: $SESSION_NAME"
tmux new-session -d -s $SESSION_NAME -n "main"

# Window 0: Main analysis (runs all cities sequentially)
tmux send-keys -t $SESSION_NAME:0 "cd $SCRIPT_DIR/.." C-m
tmux send-keys -t $SESSION_NAME:0 "echo 'Running full metro seasonal bias pre-scan...'" C-m
tmux send-keys -t $SESSION_NAME:0 "$VENV_PYTHON $PYTHON_SCRIPT" C-m

# Window 1: Monitor output
tmux new-window -t $SESSION_NAME:1 -n "monitor"
tmux send-keys -t $SESSION_NAME:1 "cd $SCRIPT_DIR/.." C-m
tmux send-keys -t $SESSION_NAME:1 "echo 'Waiting for results...'" C-m
tmux send-keys -t $SESSION_NAME:1 "watch -n 5 'ls -lh outputs/analysis/metro_seasonal_bias_*.csv 2>/dev/null || echo \"Results not yet available\"'" C-m

# Window 2: Results viewer (top 20)
tmux new-window -t $SESSION_NAME:2 -n "top20"
tmux send-keys -t $SESSION_NAME:2 "cd $SCRIPT_DIR/.." C-m
tmux send-keys -t $SESSION_NAME:2 "echo 'Top 20 cities will appear here once analysis completes...'" C-m
tmux send-keys -t $SESSION_NAME:2 "while [ ! -f outputs/analysis/metro_seasonal_bias_priority_list.csv ]; do sleep 5; done; head -30 outputs/analysis/metro_seasonal_bias_priority_list.csv | column -t -s','" C-m

# Window 3: Classification summary
tmux new-window -t $SESSION_NAME:3 -n "summary"
tmux send-keys -t $SESSION_NAME:3 "cd $SCRIPT_DIR/.." C-m
tmux send-keys -t $SESSION_NAME:3 "echo 'Summary statistics will appear here...'" C-m
tmux send-keys -t $SESSION_NAME:3 "while [ ! -f outputs/analysis/metro_seasonal_bias_prescan.csv ]; do sleep 5; done; $VENV_PYTHON -c \"
import pandas as pd
df = pd.read_csv('outputs/analysis/metro_seasonal_bias_prescan.csv')
df_success = df[df['status'] == 'SUCCESS']
print('\\n=== CLASSIFICATION SUMMARY ===')
print(df_success['classification'].value_counts())
print('\\n=== DOMINANT SEASON DISTRIBUTION ===')
print(df_success['dominant_season_all'].value_counts())
print('\\n=== QUALITY SCORE STATISTICS ===')
print(df_success['quality_score'].describe())
\"" C-m

# Window 4: Failed cities
tmux new-window -t $SESSION_NAME:4 -n "failures"
tmux send-keys -t $SESSION_NAME:4 "cd $SCRIPT_DIR/.." C-m
tmux send-keys -t $SESSION_NAME:4 "echo 'Failed analyses will appear here...'" C-m
tmux send-keys -t $SESSION_NAME:4 "while [ ! -f outputs/analysis/metro_seasonal_bias_prescan.csv ]; do sleep 5; done; $VENV_PYTHON -c \"
import pandas as pd
df = pd.read_csv('outputs/analysis/metro_seasonal_bias_prescan.csv')
df_failed = df[df['status'] != 'SUCCESS']
if len(df_failed) > 0:
    print('\\n=== FAILED ANALYSES ===')
    for _, row in df_failed.iterrows():
        print(f\\\"{row['city_name']}: {row['status']} - {row.get('error', 'N/A')}\\\")
else:
    print('\\n=== ALL ANALYSES SUCCESSFUL ===')
\"" C-m

# Select main window
tmux select-window -t $SESSION_NAME:0

echo ""
echo "Tmux session '$SESSION_NAME' created with 5 windows:"
echo "  0: main    - Running full analysis"
echo "  1: monitor - File watcher"
echo "  2: top20   - Top 20 cities by quality score"
echo "  3: summary - Classification and statistics"
echo "  4: failures - Failed analyses"
echo ""
echo "Attach with: tmux attach -t $SESSION_NAME"
echo "Detach with: Ctrl+B, then D"
echo "Navigate windows: Ctrl+B, then 0-4"
echo ""

# Auto-attach
tmux attach-session -t $SESSION_NAME
