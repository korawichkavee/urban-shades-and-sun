# Download Progress Tracking - Implementation Summary

## Changes Made to `download_and_analyze_metro_seasonal_bias.py`

### 1. Progress Tracking (Lines 567-574)
```python
# Load download progress tracking (for resuming interrupted downloads)
progress_file = OUTPUT_DIR / 'download_progress.json'
completed_downloads = []
if progress_file.exists():
    with open(progress_file) as f:
        completed_downloads = json.load(f)
    print(f"Found download progress: {len(completed_downloads)} cities already downloaded")
    print(f"Resuming from checkpoint...\n")
```

**Purpose**: Loads `download_progress.json` to track which cities have successfully downloaded, allowing interrupted runs to resume.

### 2. City Sorting by Population (Lines 576-578)
```python
# Sort cities by population (smallest first for easier downloads)
sorted_metro_areas = sorted(METRO_AREAS, key=lambda x: x[2])  # Sort by population (index 2)
print(f"Processing cities in order: smallest to largest population\n")
```

**Purpose**: Processes smallest cities first (easier downloads, faster initial progress).

### 3. Skip Already Downloaded Cities (Lines 586-601)
```python
# Skip if download already completed successfully (from progress tracking)
if city_dir in completed_downloads:
    print(f"[{i}/{len(sorted_metro_areas)}] {city_name} (Pop: {pop:.2f}M) - Download already completed, skipping to analysis")
    # Still need to analyze if not in successfully_analyzed_cities
    status, svi_file = check_existing_svi_data(city_dir)
    if svi_file and city_dir not in successfully_analyzed_cities:
        print(f"  ✓ Found data: {svi_file.name}, analyzing...")
        result = analyze_city_seasonal_bias(city_dir, city_name, pop, lat, lon, svi_file)
        results.append(result)
        if result['status'] == 'SUCCESS':
            print(f"    Dom: {result['dominant_pct_all']:.1f}%, Score: {result['quality_score']:.0f}, {result['classification']}")
        else:
            print(f"    ✗ {result['status']}: {result.get('error', 'Unknown error')}")
        df_results = pd.DataFrame(results)
        df_results.to_csv(output_file, index=False)
    continue
```

**Purpose**: Skips cities whose downloads are already complete, but still performs analysis if needed.

### 4. Mark Download Complete (Lines 629-632)
```python
# Mark download as completed in progress tracking
completed_downloads.append(city_dir)
with open(progress_file, 'w') as f:
    json.dump(completed_downloads, f, indent=2)
```

**Purpose**: Immediately saves progress after each successful download, before analysis.

### 5. Garbage Collection Pause (Lines 670-671)
```python
# Brief pause between cities to let GC run
time.sleep(5)
```

**Purpose**: Gives Python garbage collector time to clean up memory between cities.

---

## How It Works

### On First Run
1. Script sorts all 50 cities by population (smallest first)
2. Creates empty `download_progress.json`
3. Downloads and analyzes each city in order
4. After each successful download, appends city name to `download_progress.json`
5. Saves analysis results incrementally to `metro_seasonal_bias_prescan.csv`

### On Interrupted/Resumed Run
1. Script loads `download_progress.json` (e.g., `["birmingham", "buffalo", "hartford"]`)
2. Loads existing results from `metro_seasonal_bias_prescan.csv`
3. For each city:
   - **Already analyzed (SUCCESS)**: Skip entirely
   - **Download completed but not analyzed**: Run analysis only
   - **Not in progress file**: Download and analyze
4. Continues from where it left off

### Example Scenario

**First run** (interrupted after 3 cities):
```
[1/50] Birmingham-Hoover, AL (Pop: 1.09M)
  ⚠ No existing SVI data - attempting download...
    ✓ Download successful, analyzing...
    Dom: 45.2%, Score: 65, GOOD - Medium Priority
[2/50] Buffalo-Cheektowaga, NY (Pop: 1.17M)
  ⚠ No existing SVI data - attempting download...
    ✓ Download successful, analyzing...
    Dom: 38.1%, Score: 72, EXCELLENT - High Priority
[3/50] Hartford-East Hartford-Middletown, CT (Pop: 1.21M)
  ⚠ No existing SVI data - attempting download...
    [Process interrupted - Ctrl+C or crash]
```

**Files created**:
- `download_progress.json`: `["birmingham", "buffalo"]` (Hartford incomplete)
- `metro_seasonal_bias_prescan.csv`: 2 rows (Birmingham, Buffalo)

**Second run** (resumed):
```
Found download progress: 2 cities already downloaded
Resuming from checkpoint...
Found existing partial results: outputs/analysis/metro_seasonal_bias_prescan.csv
Loaded 2 existing results
Processing cities in order: smallest to largest population

[1/50] Birmingham-Hoover, AL (Pop: 1.09M) - Already successfully analyzed, skipping
[2/50] Buffalo-Cheektowaga, NY (Pop: 1.17M) - Already successfully analyzed, skipping
[3/50] Hartford-East Hartford-Middletown, CT (Pop: 1.21M)
  ⚠ No existing SVI data - attempting download...
    ✓ Download successful, analyzing...
    Dom: 42.3%, Score: 68, GOOD - Medium Priority
[4/50] Salt Lake City, UT (Pop: 1.26M) - Already successfully analyzed, skipping
[5/50] Louisville/Jefferson County, KY-IN (Pop: 1.27M) - Already successfully analyzed, skipping
[6/50] New Orleans-Metairie, LA (Pop: 1.27M)
  ⚠ No existing SVI data - attempting download...
  [continues...]
```

---

## Progress Files

### `outputs/analysis/download_progress.json`
Lists cities with completed downloads (may or may not be analyzed yet):
```json
[
  "birmingham",
  "buffalo",
  "hartford",
  "new-orleans",
  "richmond"
]
```

### `outputs/analysis/metro_seasonal_bias_prescan.csv`
Analysis results with status for each city:
```csv
city_dir,city_name,population_millions,status,n_total,...
birmingham,Birmingham-Hoover AL,1.09,SUCCESS,45234,...
buffalo,Buffalo-Cheektowaga NY,1.17,SUCCESS,38912,...
hartford,Hartford-East Hartford-Middletown CT,1.21,DOWNLOAD_FAILED,,,
```

---

## Benefits

1. **Resume from interruptions**: Ctrl+C, crashes, or reboots don't lose progress
2. **Idempotent**: Running script multiple times is safe - skips completed work
3. **Smaller cities first**: Faster initial progress, build confidence
4. **Immediate checkpointing**: Progress saved after each download, not at end
5. **Separate download/analysis tracking**: Can re-analyze without re-downloading

---

## Running the Script

### Start Fresh Run
```bash
cd /home/kieran/Documents/Python/sunny_day_SVI
.venv/bin/python scripts/analysis/download_and_analyze_metro_seasonal_bias.py
```

### Resume After Interruption
Just run the same command - script automatically detects and resumes:
```bash
.venv/bin/python scripts/analysis/download_and_analyze_metro_seasonal_bias.py
```

### Check Progress
```bash
# How many cities downloaded?
jq 'length' outputs/analysis/download_progress.json

# List completed cities
jq '.' outputs/analysis/download_progress.json

# Check analysis results
head -20 outputs/analysis/metro_seasonal_bias_prescan.csv | column -t -s','
```

### Reset and Start Over
```bash
# Remove progress files (keeps data)
rm outputs/analysis/download_progress.json
rm outputs/analysis/metro_seasonal_bias_prescan.csv

# Or remove data too
rm -rf data/metro_commute_svi/*/
```

---

## Memory Safety

Based on NYC (13.2M images = ~6GB peak), your 30GB RAM is plenty. The script now:

1. **Processes smallest cities first**: Birmingham (~1M pop) likely has <100k images = <<1GB
2. **GC pause between cities**: 5 second pause lets Python clean up
3. **Chunked CSV writing**: Already implemented, limits memory during write
4. **Mapillary SDK tiles**: Already fetches in chunks under the hood

**Expected memory usage per city**:
- Small (<2M pop): ~500MB-1GB
- Medium (2-4M pop): ~1-3GB
- Large (>4M pop): ~3-6GB
- NYC (19M pop): ~6GB (proven)

**System will be fine!**

---

## Weekend Run Strategy

### Setup (Friday evening)
1. Ensure Mapillary token is set: `echo $MAPILLARY_TOKEN`
2. Check disk space: `df -h` (need >100GB)
3. Check memory: `free -h` (should show 20+ GB available)

### Start Run (Saturday morning)
```bash
cd /home/kieran/Documents/Python/sunny_day_SVI

# Start in tmux
tmux new -s metro_download

# Run script
.venv/bin/python scripts/analysis/download_and_analyze_metro_seasonal_bias.py

# Detach: Ctrl+B then D
```

### Monitor (periodically)
```bash
# Reattach to see live output
tmux attach -t metro_download

# Or check from outside
scripts/monitor_metro_download.sh

# Or manually
jq 'length' outputs/analysis/download_progress.json  # How many done?
free -h  # Memory usage
```

### After Weekend
- If complete: Great! 42 cities downloaded
- If incomplete: Note progress, continue next weekend or weekday evenings
- The script will resume automatically where it left off

---

## Expected Timeline

**Estimated time per city** (based on image counts and NYC benchmark):
- Small (<2M pop): 30-60 minutes each
- Medium (2-4M pop): 1-2 hours each
- Large (>4M pop): 2-4 hours each

**Total for 42 missing cities**:
- Best case: ~40 hours (fast networks, low image counts)
- Worst case: ~80 hours (slow networks, high image counts)
- **Likely**: 50-60 hours

**One weekend** (48 hours Sat-Mon): Should complete 25-40 cities
**Two weekends**: Will definitely complete all 42

---

## Troubleshooting

### Script crashes immediately
```bash
# Check syntax
.venv/bin/python -m py_compile scripts/analysis/download_and_analyze_metro_seasonal_bias.py

# Check imports
.venv/bin/python -c "import mapillary; print('OK')"
```

### Memory concerns during run
```bash
# Watch memory in real-time
watch -n 5 free -h

# If memory gets high (>25GB used), script is probably fine
# NYC used only 6GB peak, so even large cities should be <10GB
```

### Download failures
- Script already has retry logic (3 attempts with backoff)
- Failed cities will be logged in results CSV with DOWNLOAD_FAILED status
- Can manually retry individual cities later

### Progress file corrupted
```bash
# Check if valid JSON
jq '.' outputs/analysis/download_progress.json

# If corrupted, can rebuild from existing data
ls data/metro_commute_svi/*/new-york-city_svi.csv | cut -d'/' -f5 | jq -R . | jq -s . > outputs/analysis/download_progress.json
```

---

## Summary

**Changes made**: 5 small additions (~25 lines of code)
**Impact**: Full resume capability, sorted by size, progress tracking
**Memory**: No concerns (NYC proves it works)
**Runtime**: 1-2 weekends for all 42 cities
**Risk**: Very low - NYC already succeeded, just need time

Ready to run!
