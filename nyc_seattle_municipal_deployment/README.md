# NYC & Seattle Municipal Shadow Analysis

Analyze street view imagery within municipal boundaries for New York City and Seattle.

## Quick Start

```bash
# 1. Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Test (MANDATORY - takes 5 minutes)
./test_pipeline.sh

# 3. Run production (takes ~5 days with 50 workers)
./run_pipeline.sh
```

## What's Included

- **5.71M images** (municipal boundaries only, 73.9% reduction from full metro)
- **Pre-trained models** (ViT classifier + YOLO detector)
- **Automated pipeline** (download → analyze → delete pattern)
- **Error tolerance** (automatic retries, checkpoints, resume)

## System Requirements

**Minimum:**
- Python 3.8+
- 16 GB RAM
- **5-10 GB disk space** (images deleted after processing)
- GPU with 8+ GB VRAM (optional but recommended)

**Recommended:**
- Python 3.10+
- 32 GB RAM
- GPU with 16+ GB VRAM (RTX 4090 or similar)

## Performance

With 50 parallel workers + GPU:
- NYC: 3.36M images in ~3 days
- Seattle: 2.35M images in ~2 days
- **Total: ~5 days**

## Storage Efficiency

The pipeline uses **download → analyze → delete**:
1. Download 500 images (~1 GB)
2. Run ViT + YOLO analysis
3. Save results to CSV
4. **Delete images immediately**
5. Repeat

This keeps storage at ~2-3 GB peak instead of 11 TB.

## Data

### New York City
- Total images: 3,363,405
- Coverage: Municipal boundaries only
- GPS bounds: (-74.047, 40.683) to (-73.907, 40.877)

### Seattle
- Total images: 2,347,486
- Coverage: Municipal boundaries only
- GPS bounds: (-122.435, 47.495) to (-122.249, 47.734)

## Output Format

Results saved to `outputs/{city}/{city}_shadow_annotated.csv`:

- `id` - Mapillary image ID
- `captured_at` - Image timestamp
- `lon`, `lat` - GPS coordinates
- `is_sunny` - Binary classification
- `sunny_confidence` - ViT confidence (0-1)
- `person_count` - Number of people detected
- `shadow_count` - Number of shadows detected
- `has_shadow` - Boolean
- `shadow_percentage` - % of image in shadow (0-100)
- `person_bboxes` - JSON array of person bounding boxes
- `shadow_bboxes` - JSON array of shadow bounding boxes

## Monitoring Progress

```bash
# Check current status
python scripts/monitoring/check_progress.py

# View logs
tail -f logs/municipal_shadow_*.log
```

## Troubleshooting

**Rate limited:**
Reduce `DOWNLOAD_WORKERS` in `scripts/pipelines/municipal_shadow_pipeline.py`

**Out of memory:**
Reduce `ANALYSIS_BATCH_SIZE` in pipeline config

**Disk full:**
Ensure `DELETE_AFTER_PROCESSING = True` (default)

See `docs/MUNICIPAL_DEPLOYMENT_PACKAGE_GUIDE.md` for full documentation.

## License

[Add license information]

## Citation

If you use this dataset, please cite:
[Add citation]
