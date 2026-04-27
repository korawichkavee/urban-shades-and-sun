# NYC & Seattle Municipal-Only Deployment Package Creation Checklist

**Package Name**: `nyc_seattle_municipal_shadow_analysis_v1.0`
**Target Cities**: New York City (3.36M images), Seattle (2.35M images)
**Total Images**: 5.71M (municipal boundaries only)
**Created**: 2026-03-13

---

## Pre-Creation Checklist

### ☐ 1. Verify Municipal-Only Metadata Files

```bash
# Check files exist
ls -lh data/metro_commute_svi/new-york-city/new-york-city_svi_municipal_only.csv
ls -lh data/metro_commute_svi/seattle/seattle_svi_municipal_only.csv

# Verify row counts
wc -l data/metro_commute_svi/new-york-city/new-york-city_svi_municipal_only.csv
# Expected: 3363406 (3,363,405 + 1 header)

wc -l data/metro_commute_svi/seattle/seattle_svi_municipal_only.csv
# Expected: 2347487 (2,347,486 + 1 header)

# Verify columns
head -1 data/metro_commute_svi/new-york-city/new-york-city_svi_municipal_only.csv
# Expected: id,captured_at,compass_angle,sequence_id,is_pano,lon,lat

# Verify no in_municipal_boundary column (already filtered)
head -1 data/metro_commute_svi/new-york-city/new-york-city_svi_municipal_only.csv | grep -q in_municipal_boundary
# Should NOT find it (exit code 1)
```

### ☐ 2. Verify ML Models Available

```bash
# Check ViT model
ls -lh outputs/models/vit_binary.pth
# Expected: ~330 MB

# Check YOLO model
ls -lh outputs/models/sunny_batch_train4/weights/best.pt
# Expected: ~6 MB

# Test model loading
python -c "
import torch
from ultralytics import YOLO

# Test ViT
vit = torch.load('outputs/models/vit_binary.pth', map_location='cpu')
print('✓ ViT model loads')

# Test YOLO
yolo = YOLO('outputs/models/sunny_batch_train4/weights/best.pt')
print('✓ YOLO model loads')
"
```

### ☐ 3. Create Package Directory Structure

```bash
# Create package root
mkdir -p nyc_seattle_municipal_deployment
cd nyc_seattle_municipal_deployment

# Create directory structure
mkdir -p data/metadata
mkdir -p data/boundaries
mkdir -p models
mkdir -p scripts/pipelines
mkdir -p scripts/data_collection
mkdir -p scripts/monitoring
mkdir -p logs
mkdir -p outputs/new-york-city
mkdir -p outputs/seattle

# Verify structure
tree -L 2
```

---

## Package File Creation

### ☐ 4. Copy Municipal-Only Metadata

```bash
# Copy NYC metadata
cp ../data/metro_commute_svi/new-york-city/new-york-city_svi_municipal_only.csv \
   data/metadata/new-york-city_svi_municipal_only.csv

# Copy Seattle metadata
cp ../data/metro_commute_svi/seattle/seattle_svi_municipal_only.csv \
   data/metadata/seattle_svi_municipal_only.csv

# Verify file sizes
ls -lh data/metadata/
# NYC: ~357 MB
# Seattle: ~251 MB
```

### ☐ 5. Copy ML Models

```bash
# Copy ViT model
cp ../outputs/models/vit_binary.pth models/vit_binary.pth

# Copy YOLO model (rename to standard name)
cp ../outputs/models/sunny_batch_train4/weights/best.pt models/yolo_best.pt

# Verify
ls -lh models/
# vit_binary.pth: ~330 MB
# yolo_best.pt: ~6 MB
```

### ☐ 6. Create Pipeline Scripts

The main pipeline script must implement the **download → analyze → delete** pattern.

**Key components:**

1. `scripts/pipelines/municipal_shadow_pipeline.py` - Main pipeline
2. `scripts/pipelines/test_municipal_pipeline.py` - Pre-flight tests
3. `scripts/pipelines/verify_municipal_boundaries.py` - Validation
4. `scripts/data_collection/download_mly_municipal.py` - Download helper
5. `scripts/monitoring/check_progress.py` - Progress tracker
6. `scripts/monitoring/estimate_remaining_time.py` - ETA calculator

**Critical implementation pattern (from metro_commute_svi_package):**

```python
def process_city_batch(city_name, metadata_df, batch_start, batch_size,
                      output_dir, pipeline, token, logger):
    """Process a batch of images for a city."""
    batch_end = min(batch_start + batch_size, len(metadata_df))
    batch_df = metadata_df.iloc[batch_start:batch_end]

    # Create temp directory for THIS BATCH ONLY
    temp_dir = output_dir / city_name / f"temp_batch_{batch_start}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 1. Download batch
        logger.info(f"Downloading batch {batch_start//batch_size + 1}: {len(batch_df)} images...")
        successful, failed = asyncio.run(
            download_batch_async(batch_df['id'].tolist(), temp_dir, token)
        )

        if successful == 0:
            logger.warning(f"No images downloaded for batch {batch_start//batch_size + 1}")
            return []

        # 2. Process with pipeline (ViT + YOLO)
        logger.info(f"Processing {successful} images...")
        results_df = pipeline.process_folder_batch(temp_dir)

        # 3. Merge with metadata
        results_list = []
        for _, row_result in results_df.iterrows():
            img_id = str(row_result['image_id'])
            row = batch_df[batch_df['id'] == int(img_id)]
            if not row.empty:
                result_dict = row_result.to_dict()
                result_dict['lat'] = row.iloc[0]['lat']
                result_dict['lon'] = row.iloc[0]['lon']
                result_dict['captured_at'] = row.iloc[0]['captured_at']
                results_list.append(result_dict)

        return results_list

    finally:
        # 4. CRITICAL: Clean up temp directory IMMEDIATELY
        # This deletes ~1GB of images after each batch
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            logger.debug(f"Cleaned up {temp_dir}")
```

**Create the scripts:**

```bash
# Copy and adapt from metro_commute_svi_package
cp ../metro_commute_svi_package/scripts/pipelines/metro_commute_svi_pipeline.py \
   scripts/pipelines/municipal_shadow_pipeline.py

# Edit to:
# 1. Use municipal-only metadata (no filtering needed)
# 2. Add shadow detection annotations
# 3. Update CITIES config to NYC and Seattle only
# 4. Ensure temp cleanup in finally block

# Copy test script as template
cp ../metro_commute_svi_package/scripts/pipelines/test_municipal_pipeline.py \
   scripts/pipelines/test_municipal_pipeline.py

# Copy sunny_shade_pipeline (analysis component)
cp ../metro_commute_svi_package/scripts/pipelines/sunny_shade_pipeline.py \
   scripts/pipelines/sunny_shade_pipeline.py
```

### ☐ 7. Create Shell Scripts

**`run_pipeline.sh`:**

```bash
cat > run_pipeline.sh << 'EOF'
#!/bin/bash
# Main pipeline execution script

set -e  # Exit on error

echo "=========================================="
echo "NYC & Seattle Municipal Shadow Analysis"
echo "=========================================="
echo ""

# Activate virtual environment if exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Check Python
python --version || { echo "Python not found!"; exit 1; }

# Check GPU
if command -v nvidia-smi &> /dev/null; then
    echo "GPU detected:"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
else
    echo "WARNING: No GPU detected, will use CPU (very slow)"
fi

# Run pipeline
python scripts/pipelines/municipal_shadow_pipeline.py "$@"
EOF

chmod +x run_pipeline.sh
```

**`test_pipeline.sh`:**

```bash
cat > test_pipeline.sh << 'EOF'
#!/bin/bash
# Pre-flight test script

set -e

echo "=========================================="
echo "Running Pre-Flight Tests"
echo "=========================================="
echo ""

# Activate venv
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run component tests
echo "Component tests..."
python scripts/pipelines/test_municipal_pipeline.py --mode component

# Run integration tests
echo ""
echo "Integration tests..."
python scripts/pipelines/test_municipal_pipeline.py --mode integration

echo ""
echo "=========================================="
echo "✓ All tests passed - ready for deployment"
echo "=========================================="
EOF

chmod +x test_pipeline.sh
```

### ☐ 8. Create requirements.txt

```bash
cat > requirements.txt << 'EOF'
# Core dependencies
torch>=2.0.0
torchvision>=0.15.0
ultralytics>=8.0.0
Pillow>=9.0.0

# Data processing
pandas>=1.5.0
numpy>=1.23.0
geopandas>=0.12.0
shapely>=2.0.0

# Geospatial
osmnx>=1.3.0

# Async downloads
aiohttp>=3.8.0
asyncio

# Utilities
tqdm>=4.65.0
python-dotenv>=1.0.0

# Optional but recommended
jupyter  # For analysis
matplotlib  # For visualization
seaborn  # For plots
EOF
```

### ☐ 9. Create README.md

```bash
cat > README.md << 'EOF'
# NYC & Seattle Municipal Shadow Analysis

Analyze street view imagery within municipal boundaries for New York City and Seattle.

## Quick Start

```bash
# 1. Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Test (MANDATORY - takes 10 minutes)
./test_pipeline.sh

# 3. Run production (takes ~5 days with 50 workers)
./run_pipeline.sh
```

## What's Included

- **5.71M images** (municipal boundaries only, 73.9% reduction)
- **Pre-trained models** (ViT classifier + YOLO detector)
- **Automated pipeline** (download → analyze → delete pattern)
- **Error tolerance** (automatic retries, checkpoints, resume)

## System Requirements

- Python 3.8+
- 16 GB RAM (32 GB recommended)
- **5-10 GB disk space** (images deleted after processing)
- GPU with 8+ GB VRAM (optional but 5-10x faster)

## Performance

With 50 parallel workers + GPU:
- NYC: 3.36M images in ~3 days
- Seattle: 2.35M images in ~2 days
- **Total: ~5 days**

See MUNICIPAL_DEPLOYMENT_PACKAGE_GUIDE.md for full documentation.

## Storage Efficiency

The pipeline uses **download → analyze → delete**:
1. Download 500 images (~1 GB)
2. Run ViT + YOLO analysis
3. Save results to CSV
4. **Delete images immediately**
5. Repeat

This keeps storage at ~2-3 GB peak instead of 11 TB.

## Support

For issues:
1. Check logs: `logs/municipal_shadow_pipeline_*.log`
2. Run diagnostics: `python scripts/monitoring/check_progress.py`
3. See troubleshooting guide in docs/

EOF
```

### ☐ 10. Create Documentation

```bash
# Copy the comprehensive guide
cp ../docs/MUNICIPAL_DEPLOYMENT_PACKAGE_GUIDE.md docs/

# Create quick reference
cat > docs/QUICK_REFERENCE.md << 'EOF'
# Quick Reference

## Common Commands

```bash
# Test pipeline
./test_pipeline.sh

# Run pipeline
./run_pipeline.sh

# Monitor progress
python scripts/monitoring/check_progress.py

# Resume from interruption
./run_pipeline.sh --resume

# Check errors
tail -f logs/errors.log

# Estimate remaining time
python scripts/monitoring/estimate_remaining_time.py
```

## Troubleshooting

**Rate limited:**
```bash
# Reduce workers in scripts/pipelines/municipal_shadow_pipeline.py:
DOWNLOAD_WORKERS = 25  # Default: 50
```

**Out of memory:**
```bash
# Reduce batch sizes in pipeline:
ANALYSIS_BATCH_SIZE = 16  # Default: 32
```

**Disk full:**
```bash
# Verify auto-cleanup is enabled:
DELETE_AFTER_PROCESSING = True  # Must be True!
```

See full guide: docs/MUNICIPAL_DEPLOYMENT_PACKAGE_GUIDE.md
EOF
```

---

## Testing & Validation

### ☐ 11. Run Component Tests

```bash
# Test metadata loading
python -c "
import pandas as pd
df_nyc = pd.read_csv('data/metadata/new-york-city_svi_municipal_only.csv')
df_seattle = pd.read_csv('data/metadata/seattle_svi_municipal_only.csv')
print(f'✓ NYC: {len(df_nyc):,} images')
print(f'✓ Seattle: {len(df_seattle):,} images')
assert len(df_nyc) == 3363405, 'NYC count mismatch'
assert len(df_seattle) == 2347486, 'Seattle count mismatch'
print('✓ All metadata checks passed')
"

# Test model loading
python -c "
import sys
sys.path.insert(0, 'scripts/pipelines')
from sunny_shade_pipeline import SunnyShadePipeline

pipeline = SunnyShadePipeline(
    vit_model_path='models/vit_binary.pth',
    yolo_model_path='models/yolo_best.pt'
)
print('✓ Models loaded successfully')
"

# Run full test suite
./test_pipeline.sh
```

### ☐ 12. Verify Storage Cleanup Pattern

```bash
# Grep for cleanup code
grep -n "shutil.rmtree" scripts/pipelines/municipal_shadow_pipeline.py
# Should show cleanup in finally block

# Verify DELETE_AFTER_PROCESSING flag exists
grep -n "DELETE_AFTER_PROCESSING" scripts/pipelines/municipal_shadow_pipeline.py
# Should be True by default

# Check temp directory naming
grep -n "temp_batch_" scripts/pipelines/municipal_shadow_pipeline.py
# Should use unique names per batch
```

---

## Package Creation

### ☐ 13. Create Package Archive

```bash
# Go to parent directory
cd ..

# Create tarball (will be ~600 MB)
tar -czf nyc_seattle_municipal_shadow_analysis_v1.0.tar.gz nyc_seattle_municipal_deployment/

# Verify archive
tar -tzf nyc_seattle_municipal_shadow_analysis_v1.0.tar.gz | head -20

# Check size
ls -lh nyc_seattle_municipal_shadow_analysis_v1.0.tar.gz
# Expected: ~600 MB
```

### ☐ 14. Create Checksums

```bash
# MD5
md5sum nyc_seattle_municipal_shadow_analysis_v1.0.tar.gz > nyc_seattle_municipal_shadow_analysis_v1.0.tar.gz.md5

# SHA256
sha256sum nyc_seattle_municipal_shadow_analysis_v1.0.tar.gz > nyc_seattle_municipal_shadow_analysis_v1.0.tar.gz.sha256

# Display
cat *.md5
cat *.sha256
```

### ☐ 15. Test Package Extraction

```bash
# Extract to test location
mkdir -p package_test
cd package_test
tar -xzf ../nyc_seattle_municipal_shadow_analysis_v1.0.tar.gz

# Verify structure
ls -la nyc_seattle_municipal_deployment/

# Quick test
cd nyc_seattle_municipal_deployment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run component tests only (fast)
python scripts/pipelines/test_municipal_pipeline.py --mode component
```

---

## Distribution Checklist

### ☐ 16. Package Contents Verification

Final package should contain:

**Metadata (608 MB):**
- [ ] `data/metadata/new-york-city_svi_municipal_only.csv` (357 MB)
- [ ] `data/metadata/seattle_svi_municipal_only.csv` (251 MB)

**Models (336 MB):**
- [ ] `models/vit_binary.pth` (330 MB)
- [ ] `models/yolo_best.pt` (6 MB)

**Scripts:**
- [ ] `scripts/pipelines/municipal_shadow_pipeline.py`
- [ ] `scripts/pipelines/test_municipal_pipeline.py`
- [ ] `scripts/pipelines/sunny_shade_pipeline.py`
- [ ] `scripts/pipelines/verify_municipal_boundaries.py`
- [ ] `scripts/monitoring/check_progress.py`
- [ ] `scripts/monitoring/estimate_remaining_time.py`

**Documentation:**
- [ ] `README.md`
- [ ] `docs/MUNICIPAL_DEPLOYMENT_PACKAGE_GUIDE.md`
- [ ] `docs/QUICK_REFERENCE.md`

**Setup Files:**
- [ ] `requirements.txt`
- [ ] `run_pipeline.sh` (executable)
- [ ] `test_pipeline.sh` (executable)

**Directories (empty, created on run):**
- [ ] `logs/`
- [ ] `outputs/new-york-city/`
- [ ] `outputs/seattle/`

### ☐ 17. Documentation Verification

- [ ] README has correct quick start instructions
- [ ] Guide explains download → analyze → delete pattern
- [ ] Storage requirements show 5-10 GB (NOT 11 TB)
- [ ] Performance estimates are accurate (5 days with 50 workers)
- [ ] Troubleshooting section is complete
- [ ] All code examples are tested and correct

### ☐ 18. Final Quality Checks

```bash
# Check for hardcoded paths
grep -r "/home/kieran" nyc_seattle_municipal_deployment/scripts/ || echo "✓ No hardcoded paths"

# Check for API tokens (shouldn't be in files)
grep -r "MLY|" nyc_seattle_municipal_deployment/scripts/ && echo "⚠ API token found!" || echo "✓ No hardcoded tokens"

# Check file permissions
ls -la nyc_seattle_municipal_deployment/*.sh
# Should be executable (rwxr-xr-x)

# Count total files
find nyc_seattle_municipal_deployment -type f | wc -l

# Total package size
du -sh nyc_seattle_municipal_deployment/
# Expected: ~950 MB uncompressed
```

---

## Post-Creation Tasks

### ☐ 19. Create Release Notes

```bash
cat > RELEASE_NOTES_v1.0.md << 'EOF'
# Release Notes - v1.0

## NYC & Seattle Municipal Shadow Analysis Package

**Release Date**: 2026-03-13
**Package**: nyc_seattle_municipal_shadow_analysis_v1.0.tar.gz
**Size**: ~600 MB compressed, ~950 MB uncompressed

### What's Included

- **5.71M street view images** (municipal boundaries only)
- New York City: 3,363,405 images
- Seattle: 2,347,486 images
- Pre-trained ML models (ViT + YOLO)
- Automated shadow analysis pipeline

### Key Features

- **Storage efficient**: 5-10 GB peak (download → analyze → delete pattern)
- **Error tolerant**: Automatic retries, checkpoints, resume capability
- **Fast**: ~5 days with 50 workers + GPU
- **Validated**: All images within municipal boundaries

### System Requirements

- Python 3.8+
- 16 GB RAM (32 GB recommended)
- 5-10 GB disk space
- GPU with 8+ GB VRAM (optional but recommended)

### Known Limitations

- Mapillary rate limits: May need to reduce workers if hitting limits
- GPU required for reasonable performance (CPU is 10-50x slower)
- Network connectivity required throughout run

### Checksums

MD5: [from .md5 file]
SHA256: [from .sha256 file]

### Support

See docs/MUNICIPAL_DEPLOYMENT_PACKAGE_GUIDE.md for full documentation.
EOF
```

### ☐ 20. Upload & Share

- [ ] Upload package to distribution location
- [ ] Share checksums separately for verification
- [ ] Provide download link
- [ ] Include instructions for checksum verification:

```bash
# Verify MD5
md5sum -c nyc_seattle_municipal_shadow_analysis_v1.0.tar.gz.md5

# Verify SHA256
sha256sum -c nyc_seattle_municipal_shadow_analysis_v1.0.tar.gz.sha256
```

---

## Success Criteria

Package is ready for distribution when:

- ✓ All checklist items completed
- ✓ Test suite passes completely
- ✓ Package extracts cleanly
- ✓ Component tests run successfully
- ✓ Storage cleanup pattern verified
- ✓ Documentation is complete and accurate
- ✓ No hardcoded paths or tokens
- ✓ Checksums generated and verified
- ✓ File permissions correct

**Estimated time to create package**: 2-3 hours
**Estimated time to test package**: 30 minutes
**Total**: ~3-4 hours

---

**Created by**: [Your name]
**Date**: 2026-03-13
**Version**: 1.0
