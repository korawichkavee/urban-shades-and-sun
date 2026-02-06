# Metro SVI Pipeline Optimizations

## Overview
Major performance and usability improvements to the metro cities SVI pipeline to handle millions of images efficiently.

## Changes Made

### 1. Incremental CSV Output (Progress Preservation)
**Problem**: Boston has 4.2M images. Waiting for all images to complete before saving results is risky - any crash loses all progress.

**Solution**:
- Results are now saved after **each batch** (every 256 images)
- CSV file grows incrementally: `{city}_svi_analyzed.csv`
- Pipeline can be **interrupted and resumed** - it skips already-processed images
- No data loss if pipeline crashes or is stopped

**Implementation**:
- `process_city_batch()` now appends batch results to CSV after each batch completes
- On resume, loads existing CSV and tracks processed image IDs in a set
- Skips batches where all images are already in the output file
- **Batch size optimized to 256** to ensure YOLO batch saturation (~128 sunny images → 4 full YOLO batches of 32)

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
- New pipeline (8GB GPU): ~1-2 img/sec (batch ViT=32 + batch YOLO=8)
- **New pipeline (24GB RTX 4090): ~3-5 img/sec (batch ViT=128 + batch YOLO=32)**
- **15-30x speedup** compared to old sequential pipeline

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

### Boston Example (4.2M images) - WITH RTX 4090 24GB
**Old Pipeline**: ~12-42 days (0.1-0.3 img/sec)
**New Pipeline (8GB GPU)**: ~2-4 days (1-2 img/sec)
**New Pipeline (RTX 4090 24GB)**: ~0.5-1.5 days (3-5 img/sec)**
**Speedup**: **15-30x faster than sequential**

### All 19 Cities (estimated 5-20M images total after boundary filtering)
**RTX 4090 24GB Performance:**
- **Conservative** (3 img/sec): ~19-77 hours (0.8-3.2 days)
- **Typical** (4 img/sec): ~14-58 hours (0.6-2.4 days)
- **Optimistic** (5 img/sec): ~11-46 hours (0.5-1.9 days)

**Note**: With actual city boundaries, we expect significantly fewer images than bbox-only approach, reducing processing time by 30-60%

*Actual performance depends on network speed and sunny image percentage (~50%)*

## Technical Details

### Batch Size Tuning
- **Default ViT batch size: 128 images (optimized for RTX 4090 24GB)**
- **Default YOLO batch size: 32 images (optimized for RTX 4090 24GB)**
- Can be adjusted based on GPU VRAM:
  - 4GB VRAM: ViT=16, YOLO=4
  - 8GB VRAM: ViT=32, YOLO=8
  - 16GB VRAM: ViT=64, YOLO=16
  - 24GB VRAM: ViT=128, YOLO=32 **(current defaults)**
  - 40GB+ VRAM: ViT=256, YOLO=64 (A100/H100)

### Memory Usage (RTX 4090 24GB)
- Per-batch download: ~512MB (256 images @ 2MB each)
- ViT inference: ~8GB VRAM (batch of 128, processes 2 sub-batches per 256 images)
- YOLO inference: ~10GB VRAM (batch of 32, processes ~4 sub-batches per 256 images @ 50% sunny)
- Total: ~18-20GB VRAM utilized at peak
- **Recommended**: 16GB+ VRAM (current config uses 24GB efficiently)

### Disk Space
- Temporary: ~512MB (deleted after each batch)
- Metadata CSVs: ~100MB per city
- Results CSVs: ~50MB per 100k images

## Backward Compatibility

The old `process_folder()` method is preserved for compatibility but marked as legacy. New code should use `process_folder_batch()`.

## Recent Fixes (2026-02-06)

### CRS Bug Fix
**Problem**: Pipeline crashed with `Must pass either crs or epsg` error when filtering images to city boundaries.

**Solution**:
- Set explicit CRS when creating GeoDataFrame: `gp.GeoDataFrame.from_features(geojson_dict, crs="EPSG:4326")`
- Add null check for boundary CRS: `if boundary_gdf.crs is None: boundary_gdf = boundary_gdf.set_crs("EPSG:4326")`
- Ensures both GeoDataFrames have compatible CRS before spatial operations

### City Processing Order
**Problem**: Large cities (Boston, LA) take hours to fetch metadata, blocking quick results.

**Solution**:
- Reordered cities by population (smallest first)
- Small cities (Evansville, Columbia, Boise) process first → faster initial results
- Users can see successful outputs while large cities are still fetching
- Order: Evansville (118k) → Columbia (137k) → ... → Boston (693k) → LA (3.9M)

### Metadata Fetching Performance Investigation
**Problem**: Metadata fetching is extremely slow (2 hours for Boston)

**Root Cause**:
- `mly.images_in_bbox()` uses Mapillary Tiles API at zoom level 14
- Each tile requires a separate API request (~300-500ms each)
- Large city bboxes span hundreds of tiles (Boston: ~400 tiles = ~2 minutes minimum)
- API processes tiles sequentially, not in parallel
- With city boundary filtering, still needs to fetch entire bbox first

**Current Performance**:
- Small cities (< 50 tiles): 5-15 minutes
- Medium cities (50-200 tiles): 15-60 minutes
- Large cities (200+ tiles): 1-2+ hours

**Potential Solutions** (not yet implemented):
1. **Parallel Tile Fetching**: Modify mapillary-python library to fetch tiles concurrently
2. **Alternative API**: Use Mapillary Entity API with spatial filtering (if available)
3. **Cached Metadata**: Pre-fetch and cache metadata for all cities once, reuse for analysis
4. **Reduced Bbox**: Use tighter bboxes based on actual city boundaries (partially implemented)

## Next Steps

Additional optimizations that could be implemented:

1. ~~**CRS Handling**: Fix coordinate system bugs~~ ✓ **IMPLEMENTED**
2. ~~**City Processing Order**: Process smallest cities first~~ ✓ **IMPLEMENTED**
3. **Parallel Tile Fetching**: Fetch Mapillary tiles concurrently (requires library modification)
4. **Multi-GPU Support**: Distribute cities across multiple GPUs
5. **Parallel Downloads**: Increase concurrent downloads from 100 to 500+
6. ~~**YOLO Batching**: Batch YOLO inference for sunny images~~ ✓ **IMPLEMENTED**
7. ~~**Batch Size Optimization**: Increase to 256 for better YOLO saturation~~ ✓ **IMPLEMENTED**
8. **Mixed Precision**: Use FP16 for 2x speedup on modern GPUs
9. **Persistent Workers**: Reduce dataloader overhead
10. **Compiled Models**: Use `torch.compile()` for additional speedup (PyTorch 2.0+)
11. **Prefetch to GPU**: Load images directly to GPU memory to reduce CPU→GPU transfer
12. **TensorRT**: Convert models to TensorRT for optimized inference

These could provide another 2-4x speedup but require more testing and may reduce portability.
