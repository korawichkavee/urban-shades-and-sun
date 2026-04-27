#!/bin/bash
# ABOUTME: Monitor script for metro SVI download progress
# ABOUTME: Shows current memory usage, process status, and result counts

echo "=== Metro SVI Download Monitor ==="
echo ""

# Check tmux session
if tmux has-session -t metro_prescan 2>/dev/null; then
    echo "✓ Tmux session 'metro_prescan' is running"
else
    echo "✗ Tmux session 'metro_prescan' not found"
    exit 1
fi

# Check process
PID=$(ps aux | grep -E 'download_and_analyze.*metro' | grep -v grep | awk '{print $2}')
if [ -n "$PID" ]; then
    echo "✓ Process running (PID: $PID)"

    # Memory usage
    MEM_PCT=$(ps aux | grep -E "^[^ ]+ +$PID" | awk '{print $4}')
    MEM_MB=$(ps aux | grep -E "^[^ ]+ +$PID" | awk '{print int($6/1024)}')
    echo "  Memory: ${MEM_MB}MB (${MEM_PCT}%)"
else
    echo "✗ No download process found"
fi

echo ""

# Check results file
RESULTS_FILE="/home/kieran/Documents/Python/sunny_day_SVI/outputs/analysis/metro_seasonal_bias_prescan.csv"
if [ -f "$RESULTS_FILE" ]; then
    echo "Results file: $RESULTS_FILE"
    echo "  Last modified: $(stat -c %y "$RESULTS_FILE" | cut -d'.' -f1)"

    # Count status
    python3 << EOF
import pandas as pd
df = pd.read_csv('$RESULTS_FILE')
print(f"  Total cities: {len(df)}")
print(f"  SUCCESS: {(df['status'] == 'SUCCESS').sum()}")
print(f"  NO_DATA: {(df['status'] == 'NO_DATA').sum()}")
print(f"  DOWNLOAD_FAILED: {(df['status'] == 'DOWNLOAD_FAILED').sum()}")
print(f"  Other: {(~df['status'].isin(['SUCCESS', 'NO_DATA', 'DOWNLOAD_FAILED'])).sum()}")
EOF
else
    echo "✗ Results file not found"
fi

echo ""

# Check for new SVI data files
echo "Recently created SVI files:"
find /home/kieran/Documents/Python/sunny_day_SVI/data/metro_commute_svi -name "*_svi.csv" -mmin -30 -exec ls -lh {} \; 2>/dev/null | head -5

echo ""
echo "To view live output: tmux attach -t metro_prescan"
echo "To check specific window: tmux capture-pane -t metro_prescan:0 -p | tail -30"
