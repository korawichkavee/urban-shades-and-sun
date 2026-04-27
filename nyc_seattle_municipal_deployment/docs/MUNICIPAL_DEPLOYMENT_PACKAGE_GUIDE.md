# Deployment Package Guide: NYC & Seattle Municipal-Only Analysis

**Target**: Analyze street view imagery within municipal boundaries only for New York City and Seattle
**Date**: 2026-03-13
**Dataset**: 5.7M images (NYC: 3.4M, Seattle: 2.3M) - 73.9% reduction from full metro data

---

## Executive Summary

This deployment package processes SVI imagery for NYC and Seattle, **using only images within official municipal boundaries** to eliminate 73.9% of extraneous suburban/commuter zone images. This focused approach provides:

- **Faster processing**: 5 days instead of 20 days (50 parallel workers)
- **Reduced storage**: ~11 TB instead of ~40 TB
- **Municipal-specific results**: Analysis focused on actual city boundaries

### Performance Estimates

**With 50 parallel workers (recommended):**
- Download time: ~5.2 days
- Shadow annotation: ~4.1 days
- **Total**: ~5.2 days (download is limiting factor)

**Sequential processing (not recommended):**
- Download time: ~264 days
- Shadow annotation: ~49 days

---

## Package Contents

### Directory Structure

```
nyc_seattle_municipal_deployment/
├── README.md                      # Quick start guide
├── requirements.txt               # Python dependencies
├── run_pipeline.sh                # Main execution script
├── test_pipeline.sh               # Pre-flight test script
├── data/
│   ├── metadata/
│   │   ├── new-york-city_svi_municipal_only.csv  # 3.36M images
│   │   └── seattle_svi_municipal_only.csv         # 2.35M images
│   └── boundaries/                # OSM city boundaries (for verification)
├── models/
│   ├── vit_binary.pth            # Sunny/cloudy classifier
│   └── yolo_best.pt              # Shadow detection model
├── scripts/
│   ├── pipelines/
│   │   ├── municipal_shadow_pipeline.py          # Main pipeline
│   │   ├── test_municipal_pipeline.py            # Pre-flight tests
│   │   └── verify_municipal_boundaries.py        # Boundary validation
│   ├── data_collection/
│   │   └── download_mly_municipal.py             # Municipal-filtered downloader
│   └── monitoring/
│       ├── check_progress.py                     # Progress tracker
│       └── estimate_remaining_time.py            # ETA estimator
├── logs/                          # Log files (created during run)
└── outputs/                       # Results (created during run)
    ├── new-york-city/
    │   ├── new-york-city_shadow_annotated.csv
    │   └── checkpoint_YYYYMMDD_HHMMSS.csv
    └── seattle/
        ├── seattle_shadow_annotated.csv
        └── checkpoint_YYYYMMDD_HHMMSS.csv
```

---

## Pre-Flight Testing

**CRITICAL**: Always run the test script before starting the multi-day production run.

### Test Script Features

The `test_municipal_pipeline.py` script validates all components with minimal data:

1. **Component Tests** (5-10 images per city):
   - Metadata loading and validation
   - Boundary filtering (verify in_municipal_boundary column)
   - Mapillary API connectivity
   - Async download functionality
   - ViT model inference
   - YOLO model inference
   - CSV output format
   - Checkpoint/resume logic
   - Error handling and retries

2. **Integration Test** (100 images per city):
   - Full pipeline flow
   - Batch processing
   - Memory usage monitoring
   - Download rate measurement
   - Processing throughput
   - Disk space verification

3. **Validation Tests**:
   - All images have `in_municipal_boundary=True`
   - GPS coordinates within expected bounds
   - Timestamps are valid
   - No duplicate image IDs
   - All required CSV columns present

### Running Pre-Flight Tests

```bash
# 1. Install dependencies
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Verify models are present
ls models/vit_binary.pth models/yolo_best.pt

# 3. Run component tests (fast: ~2 minutes)
python scripts/pipelines/test_municipal_pipeline.py --mode component

# 4. Run integration test (medium: ~5 minutes)
python scripts/pipelines/test_municipal_pipeline.py --mode integration

# 5. Run full validation (slow: ~10 minutes)
python scripts/pipelines/test_municipal_pipeline.py --mode full

# Check test results
cat logs/test_municipal_pipeline.log
```

**Expected Output:**
```
=============================================================================
MUNICIPAL PIPELINE PRE-FLIGHT TESTS
=============================================================================

Component Tests:
  ✓ Metadata loading (NYC: 3,363,405 images, Seattle: 2,347,486 images)
  ✓ Boundary validation (100% municipal-only)
  ✓ Mapillary API authentication
  ✓ Async download (10/10 images, avg 250ms/image)
  ✓ ViT inference (10 images, 32ms/image)
  ✓ YOLO inference (5 sunny images, 128ms/image)
  ✓ CSV output format
  ✓ Checkpoint save/restore
  ✓ Error retry logic

Integration Test (100 images per city):
  ✓ NYC pipeline (100 images, 45s total, 2.2 img/sec)
  ✓ Seattle pipeline (100 images, 42s total, 2.4 img/sec)
  ✓ Memory usage: 4.2 GB peak (within 16 GB limit)
  ✓ Disk space: 850 MB used (11 TB available)

Validation Tests:
  ✓ All images within municipal boundaries
  ✓ GPS coordinates valid
  ✓ Timestamps parseable
  ✓ No duplicates
  ✓ CSV schema correct

=============================================================================
✓ ALL TESTS PASSED - Pipeline ready for production run
=============================================================================

Estimated production performance (50 workers):
  Download rate: 12.5 images/sec
  Total download time: 5.2 days
  Shadow annotation: 4.1 days
  Total time: ~5.2 days

Recommended next steps:
  1. Ensure 11 TB disk space available
  2. Run in tmux/screen for persistence
  3. Monitor with: python scripts/monitoring/check_progress.py
  4. Start production: ./run_pipeline.sh
```

**If tests fail:**
1. Check `logs/test_municipal_pipeline.log` for detailed errors
2. Verify model files are present and not corrupted
3. Test Mapillary API token: `curl "https://graph.mapillary.com/1234567?access_token=YOUR_TOKEN"`
4. Ensure sufficient disk space (need 11 TB)
5. Check GPU availability: `nvidia-smi` (optional but recommended)

---

## Production Deployment

### Step 1: System Requirements Check

```bash
# Disk space (need 5-10 GB for outputs, NOT 11 TB)
# Images are deleted immediately after processing
df -h .

# Memory (need 16 GB minimum, 32 GB recommended)
free -h

# GPU (optional but 5-10x faster)
nvidia-smi

# Python version (need 3.8+)
python --version

# Network connectivity
ping -c 3 graph.mapillary.com
```

### Step 2: Environment Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Verify installations
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
python -c "import aiohttp; print(f'aiohttp: {aiohttp.__version__}')"
python -c "from ultralytics import YOLO; print('YOLO OK')"
```

### Step 3: Pre-Flight Tests (MANDATORY)

```bash
# Run all pre-flight tests
./test_pipeline.sh

# If tests pass, proceed to Step 4
# If tests fail, check logs and fix issues before continuing
```

### Step 4: Start Production Run

**Option A: Using tmux (recommended for SSH sessions)**

```bash
# Create tmux session
tmux new -s municipal_svi

# Start pipeline
./run_pipeline.sh

# Detach from session: Ctrl+B, then D
# Reattach later: tmux attach -t municipal_svi
```

**Option B: Using screen**

```bash
# Create screen session
screen -S municipal_svi

# Start pipeline
./run_pipeline.sh

# Detach: Ctrl+A, then D
# Reattach: screen -r municipal_svi
```

**Option C: Using nohup**

```bash
# Start in background
nohup ./run_pipeline.sh > logs/production.log 2>&1 &

# Get process ID
echo $!  # Save this number!

# Monitor log
tail -f logs/production.log
```

### Step 5: Monitor Progress

The pipeline provides multiple monitoring tools:

**Real-time progress:**
```bash
# Check current status
python scripts/monitoring/check_progress.py

# Example output:
# ============================================================
# MUNICIPAL SVI PIPELINE PROGRESS
# ============================================================
#
# New York City:
#   Total images: 3,363,405
#   Downloaded: 1,245,892 (37.0%)
#   Analyzed: 1,245,892 (37.0%)
#   ETA: 3.2 days at current rate (3.5 img/sec)
#
# Seattle:
#   Total images: 2,347,486
#   Downloaded: 892,341 (38.0%)
#   Analyzed: 892,341 (38.0%)
#   ETA: 2.1 days at current rate (3.8 img/sec)
#
# Overall Progress: 37.4% complete
# Elapsed time: 1 day, 18 hours
# Estimated remaining: 2.9 days
# ============================================================
```

**View logs:**
```bash
# Main pipeline log
tail -f logs/municipal_shadow_pipeline_*.log

# NYC city log
tail -f logs/new-york-city_progress.log

# Seattle city log
tail -f logs/seattle_progress.log

# Error log (should be empty)
tail -f logs/errors.log
```

**Resource monitoring:**
```bash
# CPU and memory
htop

# GPU utilization (if using GPU)
watch -n 1 nvidia-smi

# Disk usage
df -h .

# Network activity
iftop  # or: nethogs
```

### Step 6: Handling Interruptions

The pipeline is designed to be **fully resumable**. If interrupted (power outage, network failure, manual stop):

```bash
# Simply restart the pipeline
./run_pipeline.sh

# The pipeline will:
# 1. Detect existing checkpoint files
# 2. Skip already-processed images
# 3. Resume from where it left off

# You can manually specify resume point (optional):
./run_pipeline.sh --resume --checkpoint outputs/new-york-city/checkpoint_20260313_142530.csv
```

**Checkpoint behavior:**
- Checkpoints saved every 1,000 images
- Each checkpoint includes full metadata + analysis results so far
- Latest checkpoint is `{city}_shadow_annotated.csv` (continuously updated)
- Backup checkpoints saved as `checkpoint_YYYYMMDD_HHMMSS.csv`

---

## Pipeline Configuration

### Key Parameters

Edit `scripts/pipelines/municipal_shadow_pipeline.py` to adjust:

```python
# Performance tuning
DOWNLOAD_WORKERS = 50          # Concurrent downloads (default: 50)
DOWNLOAD_BATCH_SIZE = 500      # Images per download batch (default: 500)
ANALYSIS_BATCH_SIZE = 32       # Images per GPU batch (default: 32)
CHECKPOINT_INTERVAL = 1000     # Save checkpoint every N images (default: 1000)

# Storage management (CRITICAL)
DELETE_AFTER_PROCESSING = True # Delete images immediately after analysis (default: True)
                               # This is ESSENTIAL to keep storage < 5GB instead of 11TB
KEEP_FAILED_IMAGES = False     # Keep failed images for debugging (default: False)

# Retry behavior
MAX_DOWNLOAD_RETRIES = 5       # Retry failed downloads (default: 5)
RETRY_DELAY = 2                # Initial retry delay in seconds (default: 2)
EXPONENTIAL_BACKOFF = True     # Use exponential backoff (default: True)

# Resource limits
MAX_MEMORY_GB = 24             # Abort if memory exceeds this (default: 24)
MAX_CONCURRENT_API = 100       # Max concurrent API requests (default: 100)

# Mapillary API
MAPILLARY_TOKEN = 'MLY|...'    # API token (required)
RATE_LIMIT_DELAY = 0.1         # Delay between requests in seconds (default: 0.1)
```

**IMPORTANT - Storage Efficiency:**

The pipeline uses a **download → analyze → delete** pattern to minimize storage:

1. Download batch (500 images × ~2 MB = 1 GB)
2. Analyze batch with ViT + YOLO
3. Save results to CSV
4. **DELETE images immediately** (via `shutil.rmtree(temp_dir)`)
5. Repeat

This keeps peak storage at **~2-3 GB** instead of 11 TB. If you disable `DELETE_AFTER_PROCESSING`, you'll need 11 TB of disk space.

### Error Handling

The pipeline includes comprehensive error handling:

**Automatic retries:**
- Download failures: 5 retries with exponential backoff
- API rate limits: Automatic 60-second wait + retry
- Network timeouts: 3 retries with increasing timeout (30s, 60s, 120s)
- Model inference errors: Skip image, log error, continue

**Error logging:**
- All errors logged to `logs/errors.log`
- Failed image IDs saved to `outputs/{city}/failed_images.txt`
- Retry after main run: `./run_pipeline.sh --retry-failed`

**Graceful degradation:**
- If ViT model fails: Skip sunny/cloudy classification, continue with shadow detection
- If YOLO model fails: Skip shadow detection for that image, continue
- If metadata corrupt: Skip that row, log warning

---

## Output Format

### Shadow-Annotated CSV

Each city produces a final CSV: `outputs/{city}/{city}_shadow_annotated.csv`

**Columns:**
- `id` - Mapillary image ID
- `captured_at` - Image timestamp
- `compass_angle` - Camera direction (0-360°)
- `sequence_id` - Mapillary sequence ID
- `is_pano` - Panoramic image flag (boolean)
- `lon`, `lat` - GPS coordinates (WGS84)
- `in_municipal_boundary` - TRUE for all images (pre-filtered)
- `is_sunny` - Binary classification (boolean)
- `sunny_confidence` - ViT confidence score (0-1)
- `person_count` - Number of people detected (int)
- `shadow_count` - Number of shadows detected (int)
- `has_shadow` - At least one shadow present (boolean)
- `shadow_percentage` - % of image area in shadow (float, 0-100)
- `person_bboxes` - JSON array of person bounding boxes
- `shadow_bboxes` - JSON array of shadow bounding boxes

**Example row:**
```csv
id,captured_at,compass_angle,sequence_id,is_pano,lon,lat,in_municipal_boundary,is_sunny,sunny_confidence,person_count,shadow_count,has_shadow,shadow_percentage,person_bboxes,shadow_bboxes
123456789,2023-07-15T14:32:18Z,87.3,abc123def456,False,-73.9857,40.7484,True,True,0.98,2,3,True,24.5,"[[100,200,50,150],[300,180,45,160]]","[[50,400,200,100],[250,420,180,95],[420,390,160,110]]"
```

### Summary Statistics

Each city also produces `outputs/{city}/{city}_summary.json`:

```json
{
  "city": "new-york-city",
  "total_images": 3363405,
  "processed_successfully": 3362891,
  "failed": 514,
  "processing_time_hours": 124.3,
  "avg_processing_rate_img_per_sec": 7.5,

  "classification": {
    "sunny_count": 1848234,
    "cloudy_count": 1514657,
    "sunny_percentage": 54.9
  },

  "detection": {
    "images_with_people": 892341,
    "images_with_shadows": 1245892,
    "avg_people_per_image": 0.82,
    "avg_shadows_per_image": 1.34,
    "avg_shadow_percentage": 18.7
  },

  "boundary_validation": {
    "all_in_boundary": true,
    "boundary_area_deg2": 0.1299
  }
}
```

---

## Troubleshooting

### Common Issues

#### 1. Rate Limiting Errors

**Symptom:** Logs show "Rate limit exceeded (429)" or many failed downloads

**Solution:**
```bash
# Reduce concurrent workers
# Edit municipal_shadow_pipeline.py:
DOWNLOAD_WORKERS = 25  # Reduce from 50
RATE_LIMIT_DELAY = 0.5  # Increase delay

# Or wait 1 hour and retry
./run_pipeline.sh --resume
```

**Mapillary Limits:**
- Graph API: 60,000 requests/minute
- Tiles API: 50,000 requests/day
- Image downloads: No documented limit, but be respectful

#### 2. Out of Memory

**Symptom:** Process killed, or "CUDA out of memory" errors

**Solution:**
```bash
# Reduce batch sizes
# Edit municipal_shadow_pipeline.py:
ANALYSIS_BATCH_SIZE = 16  # Reduce from 32
DOWNLOAD_BATCH_SIZE = 250  # Reduce from 500

# Or process cities sequentially instead of parallel
./run_pipeline.sh --sequential
```

#### 3. Disk Space Exhausted

**Symptom:** "No space left on device" errors

**Solution:**
```bash
# Check current usage
df -h .

# Clean up temporary files
rm -rf outputs/*/temp_*
rm -rf outputs/*/images_batch_*

# Process cities one at a time to reduce peak storage
./run_pipeline.sh --city new-york-city
# Wait for completion, then:
./run_pipeline.sh --city seattle
```

#### 4. Model Loading Failures

**Symptom:** "RuntimeError: Error(s) in loading state_dict" or similar

**Solution:**
```bash
# Re-download models
# Check model file integrity
md5sum models/vit_binary.pth
md5sum models/yolo_best.pt

# Expected checksums (verify these match your package):
# vit_binary.pth:  a1b2c3d4e5f6...
# yolo_best.pt:    f6e5d4c3b2a1...

# If corrupted, re-extract from package or re-download
```

#### 5. Network Connectivity Issues

**Symptom:** Timeouts, "Connection reset by peer"

**Solution:**
```bash
# Test connectivity
ping -c 5 graph.mapillary.com

# If intermittent, increase timeout and retries
# Edit municipal_shadow_pipeline.py:
MAX_DOWNLOAD_RETRIES = 10  # Increase from 5
NETWORK_TIMEOUT_SEC = 60   # Increase from 30

# Resume with exponential backoff enabled
./run_pipeline.sh --resume --max-retries 10
```

#### 6. Checkpoint Corruption

**Symptom:** "CSV parse error" or "Invalid checkpoint" messages

**Solution:**
```bash
# List available checkpoints
ls -lht outputs/new-york-city/checkpoint_*.csv

# Restore from earlier checkpoint
./run_pipeline.sh --resume --checkpoint outputs/new-york-city/checkpoint_20260312_183042.csv

# Or restart from scratch (only if necessary)
./run_pipeline.sh --force-restart --city new-york-city
```

---

## Performance Optimization

### GPU Utilization

**Check GPU usage:**
```bash
nvidia-smi

# Expected during processing:
# - GPU Utilization: 70-95%
# - Memory Usage: 4-8 GB (for YOLO + ViT)
# - Temperature: <80°C
```

**If GPU underutilized:**
```python
# Increase batch size (edit pipeline config)
ANALYSIS_BATCH_SIZE = 64  # Try doubling from 32
```

**If GPU memory full:**
```python
# Reduce batch size
ANALYSIS_BATCH_SIZE = 16  # Halve from 32

# Or use mixed precision
USE_AMP = True  # Automatic Mixed Precision (saves ~40% memory)
```

### Download Optimization

**Maximize download throughput:**
```python
# Increase concurrent workers (if network can handle)
DOWNLOAD_WORKERS = 100  # Try doubling from 50

# Increase batch size
DOWNLOAD_BATCH_SIZE = 1000  # Double from 500
```

**Monitor download rate:**
```bash
python scripts/monitoring/check_progress.py | grep "img/sec"

# Target rates:
# Good: 5-10 img/sec
# Excellent: 10-20 img/sec
# Outstanding: 20+ img/sec
```

### Parallel City Processing

**Process both cities simultaneously (requires 2x resources):**
```bash
# Terminal 1: NYC
./run_pipeline.sh --city new-york-city

# Terminal 2: Seattle (in separate tmux window)
./run_pipeline.sh --city seattle
```

**Resource requirements for parallel:**
- 32 GB RAM (16 GB per city)
- 16 GB GPU VRAM (8 GB per city) OR 2 GPUs
- 2x network bandwidth

---

## Validation and QA

### Post-Processing Validation

After pipeline completes, run validation checks:

```bash
# Validate output CSVs
python scripts/pipelines/verify_municipal_boundaries.py

# Expected output:
# ============================================================
# MUNICIPAL BOUNDARY VALIDATION
# ============================================================
#
# New York City:
#   Total images: 3,362,891 (514 failed during processing)
#   All in_municipal_boundary: TRUE ✓
#   GPS bounds: (-74.047, 40.683) to (-73.907, 40.877) ✓
#   Timestamps valid: 100% ✓
#   No duplicates: TRUE ✓
#   Shadow annotations: 100% ✓
#   Average shadow %: 18.7
#
# Seattle:
#   Total images: 2,347,102 (384 failed during processing)
#   All in_municipal_boundary: TRUE ✓
#   GPS bounds: (-122.435, 47.495) to (-122.249, 47.734) ✓
#   Timestamps valid: 100% ✓
#   No duplicates: TRUE ✓
#   Shadow annotations: 100% ✓
#   Average shadow %: 22.1
#
# ============================================================
# ✓ ALL VALIDATION CHECKS PASSED
# ============================================================
```

### Quality Checks

```bash
# Check for missing values
python scripts/analysis/check_data_quality.py outputs/new-york-city/new-york-city_shadow_annotated.csv

# Visualize sample results
python scripts/visualization/plot_shadow_distribution.py --city new-york-city

# Compare with full metro dataset (if available)
python scripts/analysis/compare_municipal_vs_metro.py
```

---

## Cleanup and Archival

### After Successful Completion

```bash
# 1. Verify final outputs
ls -lh outputs/new-york-city/new-york-city_shadow_annotated.csv
ls -lh outputs/seattle/seattle_shadow_annotated.csv

# 2. Clean up temporary files
find outputs/ -type d -name "temp_*" -exec rm -rf {} +
find outputs/ -type d -name "images_batch_*" -exec rm -rf {} +

# 3. Clean up old checkpoints (keep last 3)
cd outputs/new-york-city
ls -t checkpoint_*.csv | tail -n +4 | xargs rm -f
cd ../seattle
ls -t checkpoint_*.csv | tail -n +4 | xargs rm -f
cd ../..

# 4. Compress for archival
tar -czf nyc_seattle_municipal_results_$(date +%Y%m%d).tar.gz outputs/

# 5. Verify archive
tar -tzf nyc_seattle_municipal_results_*.tar.gz | head

# 6. Remove raw intermediate data (optional, saves space)
rm -rf data/temp/
```

### What to Keep

**Essential (must keep):**
- `outputs/{city}/{city}_shadow_annotated.csv` - Final results
- `outputs/{city}/{city}_summary.json` - Summary statistics
- `logs/municipal_shadow_pipeline_*.log` - Processing log

**Optional (for debugging/reprocessing):**
- `data/metadata/{city}_svi_municipal_only.csv` - Original metadata
- `models/` - ML models (can re-download if needed)
- Latest checkpoint files (for potential re-runs)

**Can delete:**
- `outputs/*/temp_*` - Temporary batch directories
- `outputs/*/images_batch_*` - Downloaded images (already processed)
- Old checkpoint files (keep latest 3 only)
- Test output directories

---

## Expected Timeline

### Phase Breakdown (50 workers, GPU enabled)

| Phase | Duration | Details |
|-------|----------|---------|
| Pre-flight tests | 10 min | Component + integration validation |
| NYC download | 3.1 days | 3.36M images @ 12.5 img/sec |
| NYC shadow annotation | 3.1 days | 3.36M images @ 12.5 img/sec |
| Seattle download | 2.1 days | 2.35M images @ 12.5 img/sec |
| Seattle shadow annotation | 2.1 days | 2.35M images @ 12.5 img/sec |
| **Total (sequential)** | **5.2 days** | Download is rate-limiting |
| **Total (parallel cities)** | **3.1 days** | If 2x resources available |

### Milestones

**Day 1:**
- Hour 0-1: Setup, pre-flight tests, start NYC
- Hour 4: NYC ~5% complete (~168K images)
- Hour 12: NYC ~15% complete (~504K images)
- Hour 24: NYC ~30% complete (~1M images)

**Day 2:**
- NYC ~60% complete (~2M images)

**Day 3:**
- NYC ~90% complete (~3M images)

**Day 4:**
- NYC complete, start Seattle
- Seattle ~30% complete (~700K images)

**Day 5:**
- Seattle ~80% complete (~1.9M images)

**Day 6 (morning):**
- Seattle complete
- Validation and QA
- Archival

---

## Support and Contact

**For issues during deployment:**

1. Check this guide's Troubleshooting section
2. Review logs: `logs/errors.log` and `logs/municipal_shadow_pipeline_*.log`
3. Search for similar issues in project documentation
4. Contact: [Add support contact]

**Useful diagnostic commands:**
```bash
# System health
./scripts/monitoring/check_system_health.py

# Pipeline status
./scripts/monitoring/check_progress.py

# Error summary
./scripts/monitoring/summarize_errors.py
```

---

## Appendix: Manual Recovery Procedures

### If Everything Breaks

**Nuclear option - restart from scratch (loses progress):**
```bash
# 1. Stop pipeline
pkill -f municipal_shadow_pipeline

# 2. Clean all outputs
rm -rf outputs/new-york-city/* outputs/seattle/*

# 3. Verify metadata intact
wc -l data/metadata/*.csv

# 4. Run pre-flight tests
./test_pipeline.sh

# 5. Restart
./run_pipeline.sh
```

**Surgical recovery - rescue partial progress:**
```bash
# 1. Find latest valid checkpoint
python scripts/monitoring/find_latest_checkpoint.py outputs/new-york-city

# 2. Validate checkpoint
python scripts/monitoring/validate_checkpoint.py outputs/new-york-city/checkpoint_20260313_142530.csv

# 3. Resume from checkpoint
./run_pipeline.sh --resume --checkpoint outputs/new-york-city/checkpoint_20260313_142530.csv
```

---

**Package Version**: 1.0
**Last Updated**: 2026-03-13
**Tested On**: Ubuntu 22.04, Python 3.10, PyTorch 2.0, CUDA 11.8
