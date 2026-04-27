#!/bin/bash
# ABOUTME: Continues Phase 2 archive process in background with monitoring
# ABOUTME: Archives remaining data, scripts, plots, and docs to sunny_day_svi_archive/

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ROOT="/home/kieran/Documents/Python/sunny_day_SVI"
ARCHIVE="$ROOT/sunny_day_svi_archive"
LOG_DIR="$ROOT/archive_logs"

# Create log directory
mkdir -p "$LOG_DIR"

echo -e "${GREEN}=== Phase 2 Archive Continuation ===${NC}"
echo "Started: $(date)"
echo "Logs will be written to: $LOG_DIR"
echo ""

# Function to log with timestamp
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_DIR/archive_main.log"
}

# Function to run rsync with logging
run_rsync() {
    local source="$1"
    local dest="$2"
    local log_file="$3"
    local description="$4"

    log "Starting: $description"
    echo -e "${YELLOW}Archiving: $source${NC}"

    rsync -av --info=progress2 "$source" "$dest" > "$log_file" 2>&1

    if [ $? -eq 0 ]; then
        log "✓ Completed: $description"
        echo -e "${GREEN}✓ $description${NC}"
        return 0
    else
        log "✗ FAILED: $description"
        echo -e "${RED}✗ FAILED: $description${NC}"
        return 1
    fi
}

cd "$ROOT"

log "=== PHASE 2: ARCHIVE CONTINUATION ==="

# Wait for background jobs to complete
log "Checking background archive jobs..."
if pgrep -f "rsync.*data/raw.*sunny_day_svi_archive" > /dev/null; then
    echo -e "${YELLOW}data/raw/ archive still running in background...${NC}"
    log "data/raw/ archive in progress (PID: $(pgrep -f 'rsync.*data/raw.*sunny_day_svi_archive'))"
fi

if pgrep -f "rsync.*data/transit_surveys.*sunny_day_svi_archive" > /dev/null; then
    echo -e "${YELLOW}data/transit_surveys/ archive still running in background...${NC}"
    log "data/transit_surveys/ archive in progress (PID: $(pgrep -f 'rsync.*data/transit_surveys.*sunny_day_svi_archive'))"
fi

# ============================================================================
# METRO DATA (~30 GB)
# ============================================================================

log "=== Archiving Metro Data (~30 GB) ==="

mkdir -p "$ARCHIVE/data"

# Metro commute SVI (23 GB)
if [ -d "data/metro_commute_svi" ]; then
    run_rsync "data/metro_commute_svi/" \
              "$ARCHIVE/data/metro_commute_svi/" \
              "$LOG_DIR/metro_commute_svi.log" \
              "Metro commute SVI (23 GB)"
fi

# Metro cities SVI (4.3 GB)
if [ -d "data/metro_cities_svi" ]; then
    run_rsync "data/metro_cities_svi/" \
              "$ARCHIVE/data/metro_cities_svi/" \
              "$LOG_DIR/metro_cities_svi.log" \
              "Metro cities SVI (4.3 GB)"
fi

# Metro cities SVI test (6.7 GB)
if [ -d "data/metro_cities_svi_test" ]; then
    run_rsync "data/metro_cities_svi_test/" \
              "$ARCHIVE/data/metro_cities_svi_test/" \
              "$LOG_DIR/metro_cities_svi_test.log" \
              "Metro cities SVI test (6.7 GB)"
fi

# Metro cities SVI commute (1.9 GB)
if [ -d "data/metro_cities_svi_commute" ]; then
    run_rsync "data/metro_cities_svi_commute/" \
              "$ARCHIVE/data/metro_cities_svi_commute/" \
              "$LOG_DIR/metro_cities_svi_commute.log" \
              "Metro cities SVI commute (1.9 GB)"
fi

# Metro commute SVI with shadow (288 MB)
if [ -d "data/metro_commute_svi_with_shadow" ]; then
    run_rsync "data/metro_commute_svi_with_shadow/" \
              "$ARCHIVE/data/metro_commute_svi_with_shadow/" \
              "$LOG_DIR/metro_commute_svi_with_shadow.log" \
              "Metro commute SVI with shadow (288 MB)"
fi

# Metro commute SVI with UTCI (219 MB)
if [ -d "data/metro_commute_svi_with_utci" ]; then
    run_rsync "data/metro_commute_svi_with_utci/" \
              "$ARCHIVE/data/metro_commute_svi_with_utci/" \
              "$LOG_DIR/metro_commute_svi_with_utci.log" \
              "Metro commute SVI with UTCI (219 MB)"
fi

# ============================================================================
# SEATTLE INTERMEDIATE DATASETS (if not already done)
# ============================================================================

log "=== Archiving Seattle Intermediate Datasets ==="

mkdir -p "$ARCHIVE/final_run_outputs/seattle"

# Check which Seattle files exist and archive them
if [ -f "final_run_outputs/seattle/seattle_final_analysis_with_ipw.csv" ]; then
    rsync -av final_run_outputs/seattle/seattle_final_analysis_with_ipw.csv \
        "$ARCHIVE/final_run_outputs/seattle/" >> "$LOG_DIR/seattle_intermediates.log" 2>&1
    log "✓ Archived seattle_final_analysis_with_ipw.csv"
fi

if [ -f "final_run_outputs/seattle/seattle_final_analysis_with_seasonal_no_temp.csv" ]; then
    rsync -av final_run_outputs/seattle/seattle_final_analysis_with_seasonal_no_temp.csv \
        "$ARCHIVE/final_run_outputs/seattle/" >> "$LOG_DIR/seattle_intermediates.log" 2>&1
    log "✓ Archived seattle_final_analysis_with_seasonal_no_temp.csv"
fi

if [ -f "final_run_outputs/seattle/seattle_shadow_annotated.csv" ]; then
    rsync -av final_run_outputs/seattle/seattle_shadow_annotated.csv \
        "$ARCHIVE/final_run_outputs/seattle/" >> "$LOG_DIR/seattle_intermediates.log" 2>&1
    log "✓ Archived seattle_shadow_annotated.csv"
fi

if [ -f "final_run_outputs/seattle/seattle_with_shadow_and_utci.csv" ]; then
    rsync -av final_run_outputs/seattle/seattle_with_shadow_and_utci.csv \
        "$ARCHIVE/final_run_outputs/seattle/" >> "$LOG_DIR/seattle_intermediates.log" 2>&1
    log "✓ Archived seattle_with_shadow_and_utci.csv"
fi

if [ -f "final_run_outputs/seattle/seattle_with_shadow_metrics.csv" ]; then
    rsync -av final_run_outputs/seattle/seattle_with_shadow_metrics.csv \
        "$ARCHIVE/final_run_outputs/seattle/" >> "$LOG_DIR/seattle_intermediates.log" 2>&1
    log "✓ Archived seattle_with_shadow_metrics.csv"
fi

if [ -f "final_run_outputs/seattle/seattle_shadow_checkpoint.json" ]; then
    rsync -av final_run_outputs/seattle/seattle_shadow_checkpoint.json \
        "$ARCHIVE/final_run_outputs/seattle/" >> "$LOG_DIR/seattle_intermediates.log" 2>&1
    log "✓ Archived seattle_shadow_checkpoint.json"
fi

# ============================================================================
# OTHER CITIES DATA
# ============================================================================

log "=== Archiving Other Cities Data ==="

# State College (97 MB)
if [ -d "data/state-college" ]; then
    run_rsync "data/state-college/" \
              "$ARCHIVE/data/state-college/" \
              "$LOG_DIR/state_college.log" \
              "State College data (97 MB)"
fi

# Boston metadata (419 MB)
if [ -f "data/boston_metadata.csv" ]; then
    rsync -av data/boston_metadata.csv "$ARCHIVE/data/" >> "$LOG_DIR/boston.log" 2>&1
    log "✓ Archived boston_metadata.csv"
fi

# Boston mobility survey
if [ -d "final_cities/Boston" ]; then
    mkdir -p "$ARCHIVE/final_cities"
    run_rsync "final_cities/Boston/" \
              "$ARCHIVE/final_cities/Boston/" \
              "$LOG_DIR/boston_survey.log" \
              "Boston mobility survey (1.8 MB)"
fi

# Washington DC mobility survey
if [ -d "final_cities/Washington DC" ]; then
    mkdir -p "$ARCHIVE/final_cities"
    run_rsync "final_cities/Washington DC/" \
              "$ARCHIVE/final_cities/Washington DC/" \
              "$LOG_DIR/dc_survey.log" \
              "Washington DC mobility survey (36 MB)"
fi

# Multi-city results (137 MB)
if [ -d "data/multi_city_results" ]; then
    run_rsync "data/multi_city_results/" \
              "$ARCHIVE/data/multi_city_results/" \
              "$LOG_DIR/multi_city_results.log" \
              "Multi-city results (137 MB)"
fi

# Cache (250 MB)
if [ -d "data/cache" ]; then
    run_rsync "data/cache/" \
              "$ARCHIVE/data/cache/" \
              "$LOG_DIR/cache.log" \
              "Data cache (250 MB)"
fi

# ============================================================================
# SCRIPTS (~100 files)
# ============================================================================

log "=== Archiving Scripts ==="

mkdir -p "$ARCHIVE/scripts"/{phoenix,state_college,metro_cities,ot_svi,exploratory,root_scripts}

# Phoenix scripts
log "Archiving Phoenix scripts..."
find scripts/visualization -name "*phoenix*" -type f -exec rsync -av {} "$ARCHIVE/scripts/phoenix/" \; 2>> "$LOG_DIR/scripts.log"

# State College scripts
log "Archiving State College scripts..."
if [ -d "scripts/visualization/state_college" ]; then
    rsync -av scripts/visualization/state_college/ "$ARCHIVE/scripts/state_college/visualization/" >> "$LOG_DIR/scripts.log" 2>&1
fi
find scripts/processing -name "*state_college*" -type f -exec rsync -av {} "$ARCHIVE/scripts/state_college/processing/" \; 2>> "$LOG_DIR/scripts.log"
find scripts/analysis -name "*state_college*" -type f -exec rsync -av {} "$ARCHIVE/scripts/state_college/analysis/" \; 2>> "$LOG_DIR/scripts.log"
find scripts/pipelines -name "*university_park*" -type f -exec rsync -av {} "$ARCHIVE/scripts/state_college/pipelines/" \; 2>> "$LOG_DIR/scripts.log"

# Metro cities scripts
log "Archiving Metro cities scripts..."
find scripts/processing -name "metro_*" -type f -exec rsync -av {} "$ARCHIVE/scripts/metro_cities/processing/" \; 2>> "$LOG_DIR/scripts.log"
find scripts/analysis -name "*metro*" -o -name "*chicago*" -o -name "*dallas*" -type f -exec rsync -av {} "$ARCHIVE/scripts/metro_cities/analysis/" \; 2>> "$LOG_DIR/scripts.log"
find scripts/pipelines -name "metro_*" -type f -exec rsync -av {} "$ARCHIVE/scripts/metro_cities/pipelines/" \; 2>> "$LOG_DIR/scripts.log"
find scripts/data_collection -name "*dallas*" -type f -exec rsync -av {} "$ARCHIVE/scripts/metro_cities/data_collection/" \; 2>> "$LOG_DIR/scripts.log"
if [ -d "scripts/visualization/metro" ]; then
    rsync -av scripts/visualization/metro/ "$ARCHIVE/scripts/metro_cities/visualization/" >> "$LOG_DIR/scripts.log" 2>&1
fi
find scripts/visualization -name "*metro*" -type f -exec rsync -av {} "$ARCHIVE/scripts/metro_cities/visualization/" \; 2>> "$LOG_DIR/scripts.log"

# OT-SVI module (29 files)
if [ -d "scripts/ot_svi" ]; then
    run_rsync "scripts/ot_svi/" \
              "$ARCHIVE/scripts/ot_svi/" \
              "$LOG_DIR/ot_svi.log" \
              "OT-SVI module (29 files)"
fi

# Exploratory scripts
log "Archiving exploratory scripts..."
mkdir -p "$ARCHIVE/scripts/exploratory"/{seasonal_bias,diagnostics}
find scripts/analysis -name "*seasonal_bias*" -o -name "*emd*" -o -name "*prescan*" -type f -exec rsync -av {} "$ARCHIVE/scripts/exploratory/seasonal_bias/" \; 2>> "$LOG_DIR/scripts.log"
find scripts/analysis -name "*filter*" -o -name "*investigate*" -o -name "*sr_ipw*" -type f -exec rsync -av {} "$ARCHIVE/scripts/exploratory/diagnostics/" \; 2>> "$LOG_DIR/scripts.log"

# Root scripts
log "Archiving root directory scripts..."
[ -f "analyze_commute_time_images.py" ] && rsync -av analyze_commute_time_images.py "$ARCHIVE/scripts/root_scripts/" 2>> "$LOG_DIR/scripts.log"
[ -f "generate_commute_filtered_metadata.py" ] && rsync -av generate_commute_filtered_metadata.py "$ARCHIVE/scripts/root_scripts/" 2>> "$LOG_DIR/scripts.log"
[ -f "plot_all_metro_temporal.py" ] && rsync -av plot_all_metro_temporal.py "$ARCHIVE/scripts/root_scripts/" 2>> "$LOG_DIR/scripts.log"
[ -f "plot_temporal_distribution.py" ] && rsync -av plot_temporal_distribution.py "$ARCHIVE/scripts/root_scripts/" 2>> "$LOG_DIR/scripts.log"

# ============================================================================
# PLOTS (334 files to archive)
# ============================================================================

log "=== Archiving Plots ==="

mkdir -p "$ARCHIVE/outputs/plots"

# Use PLOT_MANIFEST.csv to archive plots marked for archival
if [ -f "PLOT_MANIFEST.csv" ]; then
    log "Using PLOT_MANIFEST.csv to archive plots..."

    # Extract paths of plots to archive
    grep "^outputs/.*,ARCHIVE" PLOT_MANIFEST.csv | cut -d',' -f1 | while read plot_path; do
        if [ -f "$plot_path" ]; then
            # Create parent directory structure in archive
            plot_dir=$(dirname "$plot_path")
            mkdir -p "$ARCHIVE/$plot_dir"
            rsync -av "$plot_path" "$ARCHIVE/$plot_path" 2>> "$LOG_DIR/plots.log"
        fi
    done

    log "✓ Archived plots based on PLOT_MANIFEST.csv"
else
    log "WARNING: PLOT_MANIFEST.csv not found, archiving by pattern..."

    # Fallback: archive by pattern
    [ -d "outputs/plots/phoenix_seasonal" ] && rsync -av outputs/plots/phoenix_seasonal/ "$ARCHIVE/outputs/plots/phoenix_seasonal/" >> "$LOG_DIR/plots.log" 2>&1
    [ -d "outputs/plots/state_college" ] && rsync -av outputs/plots/state_college/ "$ARCHIVE/outputs/plots/state_college/" >> "$LOG_DIR/plots.log" 2>&1
    [ -d "outputs/plots/global_comparison_filtered" ] && rsync -av outputs/plots/global_comparison_filtered/ "$ARCHIVE/outputs/plots/global_comparison_filtered/" >> "$LOG_DIR/plots.log" 2>&1
    [ -d "outputs/plots/multi_city_comparison" ] && rsync -av outputs/plots/multi_city_comparison/ "$ARCHIVE/outputs/plots/multi_city_comparison/" >> "$LOG_DIR/plots.log" 2>&1
fi

# ============================================================================
# DOCUMENTATION (~60 files)
# ============================================================================

log "=== Archiving Documentation ==="

mkdir -p "$ARCHIVE/docs"/{metro,exploratory,technical,debug,legacy}

# Metro documentation
log "Archiving metro documentation..."
find docs -name "*METRO*" -o -name "*metro*" -type f -exec rsync -av {} "$ARCHIVE/docs/metro/" \; 2>> "$LOG_DIR/docs.log"

# Exploratory documentation
log "Archiving exploratory documentation..."
find docs -name "*SEASONAL_BIAS*" -o -name "*EMD*" -o -name "*CURVE_PATTERN*" -o -name "*SPATIAL_SEASONAL*" -type f -exec rsync -av {} "$ARCHIVE/docs/exploratory/" \; 2>> "$LOG_DIR/docs.log"

# Technical documentation
log "Archiving technical documentation..."
find docs -name "*FIX*" -o -name "*PERFORMANCE*" -o -name "*DATETIME*" -o -name "*RATE_LIMITING*" -type f -exec rsync -av {} "$ARCHIVE/docs/technical/" \; 2>> "$LOG_DIR/docs.log"

# Debug files
if [ -f "docs/weather_processing_output.txt" ]; then
    rsync -av docs/weather_processing_output.txt "$ARCHIVE/docs/debug/" >> "$LOG_DIR/docs.log" 2>&1
    log "✓ Archived weather_processing_output.txt (67 MB)"
fi

# Legacy/cleanup documentation
find docs -name "*CLEANUP*" -type f -exec rsync -av {} "$ARCHIVE/docs/legacy/" \; 2>> "$LOG_DIR/docs.log"

# ============================================================================
# ROOT ARTIFACTS
# ============================================================================

log "=== Archiving Root Artifacts ==="

mkdir -p "$ARCHIVE/root_artifacts"

[ -f "temporal_distribution_boston_svi.png" ] && rsync -av temporal_distribution_boston_svi.png "$ARCHIVE/root_artifacts/" 2>> "$LOG_DIR/root.log"
[ -f "yolo11s.pt" ] && rsync -av yolo11s.pt "$ARCHIVE/root_artifacts/" 2>> "$LOG_DIR/root.log"
[ -f "metro_commute_svi_package.tar.gz" ] && rsync -av metro_commute_svi_package.tar.gz "$ARCHIVE/root_artifacts/" 2>> "$LOG_DIR/root.log"

# Archive legacy archive directory
if [ -d "archive" ]; then
    run_rsync "archive/" \
              "$ARCHIVE/archive_legacy/" \
              "$LOG_DIR/archive_legacy.log" \
              "Legacy archive directory"
fi

# ============================================================================
# CREATE ARCHIVE README
# ============================================================================

log "=== Creating Archive Documentation ==="

cat > "$ARCHIVE/README_ARCHIVE.md" << 'ARCHIVE_README'
# Sunny Day SVI Archive

**Created**: $(date)
**Purpose**: Archived exploratory and non-publication materials from sunny_day_SVI repository

## Archive Organization

This archive contains ~185 GB of data, scripts, plots, and documentation that were removed from the main publication repository to focus on NYC and Seattle only.

### Data (~188 GB)

- `data/raw/` (128.3 GB) - Raw street view imagery (all cities)
- `data/transit_surveys/` (27 GB) - Historical metro surveys (1968-2008)
- `data/metro_commute_svi/` (23 GB) - Full metro area SVI data
- `data/metro_cities_svi/` (4.3 GB) - Chicago, Dallas, LA metadata
- `data/metro_cities_svi_test/` (6.7 GB) - Test datasets
- `data/state-college/` (97 MB) - State College methodological testbed
- `data/multi_city_results/` (137 MB) - Multi-city comparisons
- `data/cache/` (250 MB) - API response cache

### Final Run Outputs

- `final_run_outputs/new-york-city/` - NYC intermediate datasets (2.3 GB)
- `final_run_outputs/seattle/` - Seattle intermediate datasets (2.2 GB)

Includes superseded IPW versions, shadow-only annotations, and checkpoint files.

### Scripts (~100 files)

- `scripts/phoenix/` - Phoenix-specific analysis (5 scripts)
- `scripts/state_college/` - State College testbed (20+ scripts)
- `scripts/metro_cities/` - Metro cities analysis (15+ scripts)
- `scripts/ot_svi/` - Optimal transport module (29 files)
- `scripts/exploratory/` - Seasonal bias and diagnostic scripts
- `scripts/root_scripts/` - Root directory utility scripts

### Outputs

- `outputs/plots/` - Archived plots (334 files, ~450 MB)
  - Phoenix plots
  - State College plots
  - Global/multi-city comparisons
  - Raster duplicates of vector plots

### Documentation (~60 files)

- `docs/metro/` - Metro cities documentation
- `docs/exploratory/` - Exploratory analysis documentation
- `docs/technical/` - Bug fixes and optimization logs
- `docs/debug/` - Large debug files (67 MB)
- `docs/legacy/` - Old cleanup plans and legacy docs

### Root Artifacts

- Legacy scripts, plots, and package archives from root directory

## What Was Kept in Publication Repo

The main repository (~/sunny_day_SVI) now contains only:

- NYC and Seattle final datasets (~904 MB)
- NYC and Seattle mobility surveys (185 MB)
- NYC and Seattle trips with UTCI (98 MB)
- ML models and training data (1.1 GB)
- Production scripts (~50 files)
- Publication plots (~75 MB)
- Essential documentation (~20 files)
- Municipal deployment package (1.1 GB)

**Total**: ~5.3 GB (vs. original 195 GB)

## Accessing Archive Materials

All materials in this archive are preserved and can be restored if needed for future research or methodological reference.

To restore a specific file or directory:
```bash
rsync -av sunny_day_svi_archive/path/to/file ~/sunny_day_SVI/path/to/file
```

## Archive Integrity

SHA256 checksums for large files (>100 MB) are available in:
- `ARCHIVE_CHECKSUMS.txt`

Verify with:
```bash
sha256sum -c ARCHIVE_CHECKSUMS.txt
```

## Notes

- This archive is NOT git-tracked (in .gitignore)
- Archive location: ~/sunny_day_SVI/sunny_day_svi_archive/
- Archive remains on local machine for easy access
- Consider creating external backup for long-term preservation
ARCHIVE_README

log "✓ Created README_ARCHIVE.md"

# ============================================================================
# GENERATE CHECKSUMS FOR LARGE FILES
# ============================================================================

log "=== Generating Checksums for Large Files ==="

find "$ARCHIVE" -type f -size +100M -exec sha256sum {} \; > "$ARCHIVE/ARCHIVE_CHECKSUMS.txt" 2>> "$LOG_DIR/checksums.log" &
CHECKSUM_PID=$!
log "Checksum generation started in background (PID: $CHECKSUM_PID)"

# ============================================================================
# CREATE ARCHIVE INDEX
# ============================================================================

log "=== Creating Archive Index ==="

cat > "$ARCHIVE/ARCHIVE_INDEX.md" << 'INDEX_HEADER'
# Archive Index

Complete listing of all archived files and directories.

**Generated**: $(date)

INDEX_HEADER

# Generate directory tree
tree -h -L 3 "$ARCHIVE" >> "$ARCHIVE/ARCHIVE_INDEX.md" 2>> "$LOG_DIR/index.log" || \
    find "$ARCHIVE" -type d | sort >> "$ARCHIVE/ARCHIVE_INDEX.md"

log "✓ Created ARCHIVE_INDEX.md"

# ============================================================================
# UPDATE .gitignore
# ============================================================================

log "=== Updating .gitignore ==="

if ! grep -q "sunny_day_svi_archive" "$ROOT/.gitignore" 2>/dev/null; then
    echo "" >> "$ROOT/.gitignore"
    echo "# Phase 2 Archive (created $(date +%Y-%m-%d))" >> "$ROOT/.gitignore"
    echo "sunny_day_svi_archive/" >> "$ROOT/.gitignore"
    echo "archive_logs/" >> "$ROOT/.gitignore"
    log "✓ Updated .gitignore to exclude archive"
else
    log "✓ .gitignore already excludes archive"
fi

# ============================================================================
# FINAL SUMMARY
# ============================================================================

log "=== Archive Process Complete ==="

# Calculate archive size
ARCHIVE_SIZE=$(du -sh "$ARCHIVE" | cut -f1)
log "Archive size: $ARCHIVE_SIZE"

# Count files
FILE_COUNT=$(find "$ARCHIVE" -type f | wc -l)
log "Total files archived: $FILE_COUNT"

# Wait for checksum generation if still running
if ps -p $CHECKSUM_PID > /dev/null 2>&1; then
    log "Waiting for checksum generation to complete..."
    wait $CHECKSUM_PID
    log "✓ Checksums generated"
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Phase 2 Archive Process Complete!                     ║${NC}"
echo -e "${GREEN}╠════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  Archive Location: $ARCHIVE${NC}"
echo -e "${GREEN}║  Archive Size: $ARCHIVE_SIZE${NC}"
echo -e "${GREEN}║  Files Archived: $FILE_COUNT${NC}"
echo -e "${GREEN}║  Logs: $LOG_DIR${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

log "Completed: $(date)"
log "Next Steps:"
log "  1. Review archive completeness: ls -lh $ARCHIVE"
log "  2. Check logs for any errors: ls -lh $LOG_DIR"
log "  3. Verify checksums: sha256sum -c $ARCHIVE/ARCHIVE_CHECKSUMS.txt"
log "  4. Proceed to Phase 3: Repository reorganization"

echo ""
echo -e "${YELLOW}Note: data/raw/ and data/transit_surveys/ may still be copying in background${NC}"
echo -e "${YELLOW}Check progress with: tail -f /tmp/archive_raw.log /tmp/archive_transit.log${NC}"
echo ""
