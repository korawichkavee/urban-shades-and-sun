#!/bin/bash
# ABOUTME: Overnight pipeline scheduler for Seattle and NYC shadow + UTCI + IPW processing
# ABOUTME: Runs tasks sequentially with delays to maximize success and minimize memory conflicts

set -e  # Exit on error (but we'll wrap each task in its own subshell to allow continuation)

PROJECT_ROOT="/home/kieran/Documents/Python/sunny_day_SVI"
cd "$PROJECT_ROOT"

PYTHON="${PROJECT_ROOT}/.venv/bin/python"
LOG_DIR="${PROJECT_ROOT}/logs/overnight_pipeline"
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
MAIN_LOG="${LOG_DIR}/pipeline_${TIMESTAMP}.log"

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$MAIN_LOG"
}

# Task execution with error handling
run_task() {
    local task_name="$1"
    local command="$2"

    log "========================================"
    log "STARTING: $task_name"
    log "Command: $command"
    log "========================================"

    start_time=$(date +%s)

    # Run in subshell so failure doesn't stop the script
    (
        eval "$command"
    )
    exit_code=$?

    end_time=$(date +%s)
    duration=$((end_time - start_time))
    duration_min=$((duration / 60))

    if [ $exit_code -eq 0 ]; then
        log "✓ COMPLETED: $task_name (${duration_min} minutes)"
    else
        log "✗ FAILED: $task_name (exit code: $exit_code, ${duration_min} minutes)"
    fi

    log ""

    return $exit_code
}

# Sleep with countdown
sleep_with_log() {
    local minutes=$1
    local reason="$2"
    log "Sleeping for ${minutes} minutes ($reason)..."
    sleep ${minutes}m
}


# ============================================================================
# PIPELINE START
# ============================================================================

log "╔════════════════════════════════════════════════════════════════════════╗"
log "║       OVERNIGHT PIPELINE: Seattle & NYC Shadow + UTCI + IPW           ║"
log "╚════════════════════════════════════════════════════════════════════════╝"
log ""
log "Start time: $(date)"
log "Main log: $MAIN_LOG"
log ""

# ============================================================================
# PHASE 1: SEATTLE PROCESSING
# ============================================================================

log "════════════════════════════════════════════════════════════════════════"
log "PHASE 1: SEATTLE PROCESSING"
log "════════════════════════════════════════════════════════════════════════"
log ""

# Task 1a: Seattle Shadow Annotation (OPTIMIZED with checkpoint resumption)
run_task "Seattle Shadow Annotation (Optimized)" \
    "$PYTHON scripts/processing/add_shadow_to_final_cities_optimized.py --city seattle 2>&1 | tee -a $MAIN_LOG"

SEATTLE_SHADOW_SUCCESS=$?

sleep_with_log 2 "buffer after Seattle shadow completion"

# Task 1b: Seattle UTCI Annotation
run_task "Seattle UTCI Annotation" \
    "$PYTHON scripts/processing/add_utci_to_final_cities.py --city seattle 2>&1 | tee -a $MAIN_LOG"

SEATTLE_UTCI_SUCCESS=$?

sleep_with_log 2 "buffer after Seattle UTCI"

# Task 1c: Seattle IPW Application (only if shadow and UTCI succeeded)
if [ $SEATTLE_SHADOW_SUCCESS -eq 0 ] && [ $SEATTLE_UTCI_SUCCESS -eq 0 ]; then
    run_task "Seattle IPW Application" \
        "$PYTHON scripts/processing/apply_triple_ipw_final_cities.py --city seattle 2>&1 | tee -a $MAIN_LOG"
else
    log "⊗ SKIPPING Seattle IPW (shadow or UTCI failed)"
fi

log ""
log "════════════════════════════════════════════════════════════════════════"
log "PHASE 1 COMPLETE: Seattle Processing"
log "════════════════════════════════════════════════════════════════════════"
log ""

sleep_with_log 3 "buffer before NYC processing + runtime flexibility"


# ============================================================================
# PHASE 2: NYC PROCESSING
# ============================================================================

log "════════════════════════════════════════════════════════════════════════"
log "PHASE 2: NYC PROCESSING"
log "════════════════════════════════════════════════════════════════════════"
log ""

# Task 2a: NYC Shadow Annotation (OPTIMIZED with checkpoint resumption)
run_task "NYC Shadow Annotation (Optimized)" \
    "$PYTHON scripts/processing/add_shadow_to_final_cities_optimized.py --city new-york-city 2>&1 | tee -a $MAIN_LOG"

NYC_SHADOW_SUCCESS=$?

sleep_with_log 2 "buffer after NYC shadow"

# Task 2b: NYC UTCI Annotation (only if shadow succeeded)
if [ $NYC_SHADOW_SUCCESS -eq 0 ]; then
    run_task "NYC UTCI Annotation" \
        "$PYTHON scripts/processing/add_utci_to_final_cities.py --city new-york-city 2>&1 | tee -a $MAIN_LOG"

    NYC_UTCI_SUCCESS=$?

    sleep_with_log 2 "buffer after NYC UTCI"

    # Task 2c: NYC IPW Application (only if UTCI succeeded)
    if [ $NYC_UTCI_SUCCESS -eq 0 ]; then
        run_task "NYC IPW Application" \
            "$PYTHON scripts/processing/apply_triple_ipw_final_cities.py --city new-york-city 2>&1 | tee -a $MAIN_LOG"
    else
        log "⊗ SKIPPING NYC IPW (UTCI failed)"
    fi
else
    log "⊗ SKIPPING NYC UTCI and IPW (shadow annotation failed)"
fi

log ""
log "════════════════════════════════════════════════════════════════════════"
log "PHASE 2 COMPLETE: NYC Processing"
log "════════════════════════════════════════════════════════════════════════"
log ""


# ============================================================================
# FINAL SUMMARY
# ============================================================================

log "╔════════════════════════════════════════════════════════════════════════╗"
log "║                        PIPELINE COMPLETE                               ║"
log "╚════════════════════════════════════════════════════════════════════════╝"
log ""
log "End time: $(date)"
log ""

# Check output files
log "Output file status:"
log "-------------------"

check_file() {
    local file=$1
    if [ -f "$file" ]; then
        local size=$(du -h "$file" | cut -f1)
        log "✓ $file ($size)"
    else
        log "✗ $file (NOT FOUND)"
    fi
}

log ""
log "Seattle outputs:"
check_file "final_run_outputs/seattle/seattle_with_shadow_metrics.csv"
check_file "final_run_outputs/seattle/seattle_with_shadow_and_utci.csv"
check_file "final_run_outputs/seattle/seattle_final_analysis_with_ipw.csv"

log ""
log "NYC outputs:"
check_file "final_run_outputs/new-york-city/new-york-city_with_shadow_metrics.csv"
check_file "final_run_outputs/new-york-city/new-york-city_with_shadow_and_utci.csv"
check_file "final_run_outputs/new-york-city/new-york-city_final_analysis_with_ipw.csv"

log ""
log "════════════════════════════════════════════════════════════════════════"
log "All tasks complete!"
log "Main log: $MAIN_LOG"
log "════════════════════════════════════════════════════════════════════════"
