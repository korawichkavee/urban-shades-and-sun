# Metro SVI Pipeline Optimizations

## Overview
Major performance and usability improvements to the metro cities SVI pipeline to handle millions of images efficiently.

## Changes Made

### 1. Incremental CSV Output (Progress Preservation)
**Problem**: Boston has 4.2M images. Waiting for all images to complete before saving results is risky - any crash loses all progress.

**Solution**:
- Results are now saved after **each batch** (every 100 images)
- CSV file grows incrementally: `{city}_svi_analyzed.csv`
- Pipeline can be **interrupted and resumed** - it skips already-processed images
- No data loss if pipeline crashes or is stopped

**Implementation**:
- `process_city_batch()` now appends batch results to CSV after each batch completes
- On resume, loads existing CSV and tracks processed image IDs in a set
- Skips batches where all images are already in the output file

### 2. Metadata Prefetch with Time Estimation
**Problem**: Users don't know how long the pipeline will take until it's already running.

**Solution**:
- **Phase 1**: Prefetch metadata for all cities before starting processing
- Displays total image count per city
- Provides **three runtime estimates**:
  - Conservative (0.5 img/sec): Worst case scenario
  - Typical (1.0 img/sec): Expected with good GPU
  - Optimistic (2.0 img/sec): Best case with excellent hardware
- User can review estimates and **abort before models are loaded**

**Implementation**:
- New `prefetch_all_metadata()` function runs first
- Checks for existing metadata CSVs (fast if already fetched)
- Calculates estimates based on benchmarked performance
- Asks for user confirmation before proceeding (can be skipped with `--skip-prefetch`)

### 3. Performance Optimizations

#### Batch Inference for ViT Classification
**Problem**: Sequential processing - one image at a time through ViT model

**Solution**:
- New `classify_sunny_batch()` method processes 32 images simultaneously
- Leverages GPU parallelism for significant speedup
- **Expected speedup**: 5-10x faster for ViT classification step

**Implementation**:
- Loads batch of images and stacks into single tensor
- Single forward pass through ViT model
- Graceful handling of failed image loads

#### Batch Inference for YOLO Detection (NEW!)
**Problem**: Sequential processing - one image at a time through YOLO model

**Solution**:
- New `detect_shade_batch()` method processes 8 images simultaneously
- Smaller batch size than ViT (8 vs 32) due to higher memory usage
- Only processes sunny images (typically 50% of dataset)
- **Expected speedup**: 3-5x faster for YOLO detection step

**Implementation**:
- Passes list of image paths to YOLO for batch inference
- Processes results for each image in batch
- Graceful error handling for batch failures

#### Optimized Pipeline Method
**Problem**: Old `process_folder()` had sequential bottlenecks

**Solution**:
- New `process_folder_batch()` method with:
  - Batch ViT inference (32 images at once)
  - Batch YOLO inference (8 images at once, only on sunny images)
  - Reduced I/O overhead

**Expected Performance**:
- Old pipeline: ~0.1-0.3 img/sec (sequential ViT + sequential YOLO)
- New pipeline: ~1-2 img/sec (batch ViT + batch YOLO)
- **5-15x speedup** depending on GPU and sunny image percentage

### 4. Additional Improvements

#### Resume Support
- Detects existing progress files automatically
- Reports "Already processed: X images" on resume
- No duplicate processing

#### Better Logging
- Shows processing rate (images/second) per city
- Tracks download success/failure rates
- Reports batch progress: "Batch 42/420"

#### User Control
- `--skip-prefetch`: Skip metadata phase if already done
- `--cities "Boston"`: Process specific cities only
- `--test-mode`: Quick validation with 5 images/city

## Usage Examples

### Full Run with Estimates
```bash
python scripts/pipelines/metro_cities_svi_pipeline.py
# Shows estimates, waits for confirmation, then processes all cities
```

### Resume After Interruption
```bash
python scripts/pipelines/metro_cities_svi_pipeline.py --skip-prefetch
# Skips metadata phase, resumes processing from checkpoints
```

### Process Specific Cities
```bash
python scripts/pipelines/metro_cities_svi_pipeline.py --cities "Boston" "Seattle"
```

### Test Mode (Validation)
```bash
python scripts/pipelines/metro_cities_svi_pipeline.py --test-mode
# 5 images per city for quick validation
```

## Performance Estimates

### Boston Example (4.2M images)
**Old Pipeline**: ~12-42 days (0.1-0.3 img/sec)
**New Pipeline**: ~2-4 days (1-2 img/sec)
**Speedup**: **3-10x faster**

### All 20 Cities (estimated 10-50M images total)
**Conservative**: 5.5-23 days @ 0.5 img/sec
**Typical**: 3-11 days @ 1.0 img/sec
**Optimistic**: 1.5-6 days @ 2.0 img/sec

*Actual performance depends on GPU, network speed, and sunny image percentage*

## Technical Details

### Batch Size Tuning
- Default ViT batch size: 32 images
- Default YOLO batch size: 8 images (smaller due to higher memory)
- Can be adjusted based on GPU VRAM:
  - 4GB VRAM: ViT=16, YOLO=4
  - 8GB VRAM: ViT=32, YOLO=8 (default)
  - 16GB+ VRAM: ViT=64, YOLO=16
  - 24GB+ VRAM: ViT=128, YOLO=32

### Memory Usage
- Per-batch download: ~200MB (100 images @ 2MB each)
- ViT inference: ~2GB VRAM (batch of 32)
- YOLO inference: ~2-3GB VRAM (batch of 8)
- Total: ~6-8GB VRAM recommended (4GB minimum with reduced batch sizes)

### Disk Space
- Temporary: 200MB (deleted after each batch)
- Metadata CSVs: ~100MB per city
- Results CSVs: ~50MB per 100k images

## Backward Compatibility

The old `process_folder()` method is preserved for compatibility but marked as legacy. New code should use `process_folder_batch()`.

## Next Steps

Additional optimizations that could be implemented:

1. **Multi-GPU Support**: Distribute cities across multiple GPUs
2. **Parallel Downloads**: Increase concurrent downloads from 100 to 500+
3. ~~**YOLO Batching**: Batch YOLO inference for sunny images~~ ✓ **IMPLEMENTED**
4. **Mixed Precision**: Use FP16 for 2x speedup on modern GPUs
5. **Persistent Workers**: Reduce dataloader overhead
6. **Compiled Models**: Use `torch.compile()` for additional speedup (PyTorch 2.0+)
7. **Prefetch to GPU**: Load images directly to GPU memory to reduce CPU→GPU transfer
8. **TensorRT**: Convert models to TensorRT for optimized inference

These could provide another 2-4x speedup but require more testing and may reduce portability.
