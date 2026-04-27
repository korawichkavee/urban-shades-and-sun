#!/bin/bash
# ABOUTME: Monitors the archive process progress with live updates
# ABOUTME: Shows current operations, speeds, and estimated completion times

ROOT="/home/kieran/Documents/Python/sunny_day_SVI"
ARCHIVE="$ROOT/sunny_day_svi_archive"
LOG_DIR="$ROOT/archive_logs"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

clear
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          Archive Process Monitor                       ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to check if process is running
is_running() {
    pgrep -f "$1" > /dev/null
}

# Function to get last log line
get_last_log() {
    if [ -f "$1" ]; then
        tail -1 "$1" 2>/dev/null || echo "No data yet"
    else
        echo "Log not started"
    fi
}

# Function to get archive size
get_size() {
    if [ -d "$1" ]; then
        du -sh "$1" 2>/dev/null | cut -f1
    else
        echo "0"
    fi
}

# Main monitoring loop
echo -e "${BLUE}Monitoring archive processes... (Ctrl+C to exit)${NC}"
echo ""

while true; do
    # Clear previous output (keep header)
    tput cup 5 0
    tput ed

    echo "Current Time: $(date)"
    echo ""

    # Check background rsync processes
    echo -e "${YELLOW}=== Background Archive Jobs ===${NC}"

    if is_running "rsync.*data/raw"; then
        echo -e "${GREEN}✓${NC} data/raw/ (129 GB) - IN PROGRESS"
        echo "   Current: $(get_last_log /tmp/archive_raw.log)"
        echo "   Archived: $(get_size $ARCHIVE/data/raw)"
    else
        if [ -d "$ARCHIVE/data/raw" ]; then
            echo -e "${GREEN}✓${NC} data/raw/ (129 GB) - COMPLETE"
            echo "   Final size: $(get_size $ARCHIVE/data/raw)"
        else
            echo -e "  data/raw/ - NOT STARTED"
        fi
    fi
    echo ""

    if is_running "rsync.*data/transit_surveys"; then
        echo -e "${GREEN}✓${NC} data/transit_surveys/ (27 GB) - IN PROGRESS"
        echo "   Current: $(get_last_log /tmp/archive_transit.log)"
        echo "   Archived: $(get_size $ARCHIVE/data/transit_surveys)"
    else
        if [ -d "$ARCHIVE/data/transit_surveys" ]; then
            echo -e "${GREEN}✓${NC} data/transit_surveys/ (27 GB) - COMPLETE"
            echo "   Final size: $(get_size $ARCHIVE/data/transit_surveys)"
        else
            echo -e "  data/transit_surveys/ - NOT STARTED"
        fi
    fi
    echo ""

    # Check main archive script
    echo -e "${YELLOW}=== Main Archive Script ===${NC}"

    if is_running "continue_archive.sh"; then
        echo -e "${GREEN}✓${NC} continue_archive.sh - RUNNING"
        if [ -f "$LOG_DIR/archive_main.log" ]; then
            echo "   Last action:"
            tail -3 "$LOG_DIR/archive_main.log" | sed 's/^/   /'
        fi
    else
        if [ -f "$LOG_DIR/archive_main.log" ]; then
            echo -e "  continue_archive.sh - COMPLETED or NOT RUNNING"
            echo "   Check logs at: $LOG_DIR/"
        else
            echo -e "  continue_archive.sh - NOT YET STARTED"
        fi
    fi
    echo ""

    # Archive summary
    echo -e "${YELLOW}=== Archive Summary ===${NC}"
    echo "Archive location: $ARCHIVE"
    if [ -d "$ARCHIVE" ]; then
        TOTAL_SIZE=$(du -sh "$ARCHIVE" | cut -f1)
        FILE_COUNT=$(find "$ARCHIVE" -type f 2>/dev/null | wc -l)
        echo "Current size: $TOTAL_SIZE"
        echo "Files archived: $FILE_COUNT"
    else
        echo "Archive not yet created"
    fi
    echo ""

    # Instructions
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo "View detailed logs:"
    echo "  • Raw data: tail -f /tmp/archive_raw.log"
    echo "  • Transit surveys: tail -f /tmp/archive_transit.log"
    echo "  • Main script: tail -f $LOG_DIR/archive_main.log"
    echo ""
    echo "Press Ctrl+C to exit monitor"

    sleep 5
done
