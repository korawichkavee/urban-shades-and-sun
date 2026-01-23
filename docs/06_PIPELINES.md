# Pipeline Guide

## Overview

End-to-end pipelines that combine multiple processing steps into complete workflows.

Located in: `scripts/pipelines/`

## Available Pipelines

### `hot_cities_full_pipeline.py` ⭐ PRIMARY PIPELINE

Complete pipeline for hot cities analysis: download → classify → detect → analyze.

**Purpose**: Process hot cities from raw data to final analysis in one run.

**Usage**:
```bash
python scripts/pipelines/hot_cities_full_pipeline.py \
  --city Bangkok \
  --start_date 2023-06-01 \
  --end_date 2023-08-31
```

**Pipeline Steps**:
1. Load city metadata CSV
2. Binary classification (sunny vs cloudy)
3. YOLO detection (people and shadows)
4. Weather data enrichment (UTCI)
5. Geometric analysis (shade ratios)
6. Save annotated results

**Required Models**:
- Binary classifier: `outputs/models/vit_binary.pth`
- YOLO detector: `outputs/models/YOLO/best.pt`

**Output**:
- `data/processed/city_estimate_outcomes/{CityName}_annotated_with_utci.csv`

**Processing Time**:
- ~5-10 images/second (GPU)
- ~1-2 images/second (CPU)

**Log File**: `logs/hot_cities_{city}_{timestamp}.log`

---

### `sunny_shade_pipeline.py`

Focused pipeline for sunny/shade classification and analysis.

**Purpose**: Classify images and compute shade statistics without full detection.

**Usage**:
```bash
python scripts/pipelines/sunny_shade_pipeline.py \
  --input data/raw/city.csv \
  --output data/processed/city_classified.csv
```

**Pipeline Steps**:
1. Load images
2. Binary classification (sunny/shade)
3. Compute shade statistics per city
4. Generate summary report

**Output**:
- Classified CSV with `is_sunny` column
- Summary statistics JSON

---

### `sunny_shade_pipeline_ondemand.py`

On-demand version that downloads images as needed.

**Purpose**: Process without pre-downloading all images (saves storage).

**Usage**:
```bash
python scripts/pipelines/sunny_shade_pipeline_ondemand.py \
  --metadata metadata.csv \
  --mapillary_token YOUR_TOKEN
```

**Features**:
- Streams images from Mapillary API
- Processes in batches
- No local image storage required
- Slower but storage-efficient

**Best For**:
- Quick exploratory analysis
- Limited storage situations
- Testing on new cities

---

### `prelim_filtering_tmux.py`

Preliminary filtering pipeline for large-scale batch processing.

**Purpose**: Filter raw downloads to remove low-quality images before expensive processing.

**Usage**:
```bash
# Via tmux (recommended for overnight)
tmux new -s filtering
python scripts/pipelines/prelim_filtering_tmux.py
# Ctrl+B, D to detach
```

**Filters Applied**:
1. Date range (hot days only)
2. Time of day (10am-4pm when sun is strong)
3. Image quality thresholds
4. Geographic bounds
5. Duplicate removal

**Output**:
- Filtered CSVs in `data/processed/`
- Log of removed images and reasons

**Processing Time**: ~1 hour per million images

---

### `uci_csv.py`

Pipeline for UCI (presumably a dataset/format name) CSV processing.

**Purpose**: Convert and process UCI-format data.

**Usage**:
```bash
python scripts/pipelines/uci_csv.py --input uci_data.csv
```

---

## Pipeline Configuration

### Configuration Files

Pipelines can use config files to avoid long command-line arguments:

```yaml
# pipeline_config.yaml
city: Bangkok
date_range:
  start: 2023-06-01
  end: 2023-08-31

models:
  binary: outputs/models/vit_binary.pth
  yolo: outputs/models/YOLO/best.pt

processing:
  batch_size: 32
  workers: 4

output:
  dir: data/processed/city_estimate_outcomes/
  format: csv
```

Usage:
```bash
python scripts/pipelines/hot_cities_full_pipeline.py --config pipeline_config.yaml
```

---

## Creating Custom Pipelines

### Template

```python
#!/usr/bin/env python3
# ABOUTME: Custom pipeline for [your purpose]
# ABOUTME: Combines [step1], [step2], [step3]

import pandas as pd
from pathlib import Path
import logging

def setup_logging(log_file):
    """Configure logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

def step1_load_data(input_path):
    """Load and validate input data."""
    logging.info(f"Loading data from {input_path}")
    df = pd.read_csv(input_path)
    logging.info(f"Loaded {len(df)} rows")
    return df

def step2_process(df):
    """Your processing logic."""
    logging.info("Processing data...")
    # ... your code ...
    return df

def step3_save(df, output_path):
    """Save results."""
    logging.info(f"Saving to {output_path}")
    df.to_csv(output_path, index=False)
    logging.info("Pipeline complete!")

def main():
    """Run pipeline."""
    setup_logging('logs/custom_pipeline.log')

    df = step1_load_data('input.csv')
    df = step2_process(df)
    step3_save(df, 'output.csv')

if __name__ == '__main__':
    main()
```

---

## Pipeline Monitoring

### Using Tmux

Start long-running pipelines in tmux:

```bash
# Create new session
tmux new -s pipeline

# Run pipeline
python scripts/pipelines/hot_cities_full_pipeline.py

# Detach: Ctrl+B, then D

# Reattach later
tmux attach -t pipeline

# List sessions
tmux ls

# Kill session
tmux kill-session -t pipeline
```

### Viewing Logs

```bash
# Real-time log viewing
tail -f logs/hot_cities_*.log

# Search for errors
grep -i error logs/hot_cities_*.log

# Count processed images
grep "Processed image" logs/hot_cities_*.log | wc -l
```

### Progress Tracking

Pipeline scripts typically log progress like:

```
[2025-01-21 10:30:15] INFO - Processing image 1000/5000 (20%)
[2025-01-21 10:30:16] INFO - ETA: 2 hours 15 minutes
```

---

## Error Handling

### Checkpointing

Most pipelines support checkpointing:

```python
# Save progress every N rows
CHECKPOINT_INTERVAL = 100

for idx, row in df.iterrows():
    process_row(row)

    if idx % CHECKPOINT_INTERVAL == 0:
        df.to_csv('checkpoint.csv', index=False)
        logging.info(f"Checkpoint saved at row {idx}")
```

### Resume from Checkpoint

```bash
python scripts/pipelines/hot_cities_full_pipeline.py \
  --resume checkpoint.csv \
  --start_row 1500
```

### Error Recovery

```python
import traceback

failed_images = []

for image_id in image_ids:
    try:
        result = process_image(image_id)
    except Exception as e:
        logging.error(f"Failed on {image_id}: {e}")
        logging.error(traceback.format_exc())
        failed_images.append(image_id)
        continue

# Save failed IDs for retry
with open('failed_images.txt', 'w') as f:
    f.write('\n'.join(failed_images))
```

---

## Performance Optimization

### Batch Processing

Process images in batches for efficiency:

```python
BATCH_SIZE = 32

for i in range(0, len(images), BATCH_SIZE):
    batch = images[i:i+BATCH_SIZE]
    results = model.predict(batch)  # Vectorized
```

### Parallel Processing

Use multiprocessing for CPU-bound tasks:

```python
from multiprocessing import Pool

def process_city(city_file):
    # ... processing logic ...
    return results

with Pool(processes=4) as pool:
    results = pool.map(process_city, city_files)
```

### GPU Utilization

Maximize GPU usage:

```python
import torch

# Increase batch size until GPU memory full
BATCH_SIZE = 64  # Adjust based on GPU

# Use mixed precision
from torch.cuda.amp import autocast
with autocast():
    outputs = model(inputs)
```

---

## Common Workflows

### Full Processing from Scratch

```bash
# 1. Download data
python scripts/data_collection/download_hot_cities.py

# 2. Filter to hot days and walkable streets
python scripts/pipelines/prelim_filtering_tmux.py

# 3. Add UTCI data
python batch_add_enhanced_utci_optimized.py

# 4. Run full ML pipeline
python scripts/pipelines/hot_cities_full_pipeline.py

# 5. Generate visualizations
python scripts/visualization/visualize_shade_ratios.py
```

### Quick Analysis (New City)

```bash
# Using on-demand pipeline (no storage needed)
python scripts/pipelines/sunny_shade_pipeline_ondemand.py \
  --city "New York" \
  --date 2023-07-15
```

### Reprocessing with Updated Models

```bash
# Update just the ML annotations
python scripts/pipelines/hot_cities_full_pipeline.py \
  --input data/processed/city_with_utci.csv \
  --skip-weather \
  --new-models
```

---

## Deployment

### Production Checklist

- [ ] Test on small sample first
- [ ] Configure proper logging
- [ ] Set up checkpointing
- [ ] Verify output paths exist
- [ ] Check disk space available
- [ ] Validate input data format
- [ ] Set resource limits (memory, CPU)

### Tmux Scripts

Located in: `deployment/`

```bash
# UTCI processing
./deployment/run_utci_tmux.sh

# Weather processing
./deployment/run_weather_tmux.sh

# Full pipeline (all cities)
./deployment/run_pipeline_tmux.sh
```

### Cron Jobs

Schedule regular pipeline runs:

```bash
# Edit crontab
crontab -e

# Run daily at 2am
0 2 * * * cd /path/to/sunny_day_SVI && python scripts/pipelines/hot_cities_full_pipeline.py >> logs/cron.log 2>&1
```

---

## Troubleshooting

### Pipeline Hangs

Common causes:
- Waiting for API response (network timeout)
- Deadlock in multiprocessing
- Out of memory (swapping)

Solutions:
```bash
# Monitor resource usage
htop

# Check network
ping archive-api.open-meteo.com

# Kill and restart
tmux kill-session -t pipeline
```

### Incomplete Output

Check logs for:
- Exceptions during processing
- Early termination signals
- Disk space exhausted

```bash
# Check disk space
df -h

# Find where pipeline stopped
tail -50 logs/pipeline.log
```

### Inconsistent Results

Ensure reproducibility:
```python
# Set random seeds
import random
import numpy as np
import torch

random.seed(42)
np.random.seed(42)
torch.manual_seed(42)
```

---

## Pipeline Comparison

| Pipeline | Speed | Storage | Use Case |
|----------|-------|---------|----------|
| `hot_cities_full_pipeline.py` | Medium | High | Complete analysis |
| `sunny_shade_pipeline.py` | Fast | Medium | Quick classification |
| `sunny_shade_pipeline_ondemand.py` | Slow | Low | Exploratory work |
| `prelim_filtering_tmux.py` | Fast | Low | Data cleaning |

Choose based on your needs:
- **Research**: Full pipeline
- **Exploration**: On-demand pipeline
- **Production**: Filtered + optimized pipeline
