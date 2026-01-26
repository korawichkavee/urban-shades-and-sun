# Performance Analysis: Sunny Day SVI Processing Pipeline

**Analysis Date:** 2026-01-26

## Executive Summary

The current processing pipeline has **4 critical bottlenecks** preventing scalable multi-city processing. Primary issue: **sequential row-by-row processing** in UTCI enrichment causes 10-100x slowdowns. Parallelization opportunities exist at multiple levels but are underutilized.

---

## Current Architecture

### Pipeline Stages
1. **Image Download** → Mapillary API (network-bound)
2. **Sunny Classification** → ViT inference (GPU-bound, batched)
3. **Shade Detection** → YOLO inference (GPU-bound, batched)
4. **Weather/UTCI Enrichment** → ERA5 API (network-bound, **NOT batched**)
5. **Analysis/Visualization** → CPU-bound

### Processing Flow
```
Cities processed SEQUENTIALLY
  ↓
Images within city processed SEQUENTIALLY (hot_cities_full_pipeline.py)
  ↓
UTCI enrichment: ROW-BY-ROW with single-threaded ERA5 calls (add_wind_speed_to_existing.py)
```

---

## Critical Bottlenecks

### 🔴 BOTTLENECK 1: Row-by-Row UTCI Processing (CRITICAL)
**File:** `add_wind_speed_to_existing.py`

**Problem:**
```python
for idx in tqdm(range(len(df))):  # SEQUENTIAL ITERATION
    row = df.iloc[idx]
    result = get_enhanced_utci_data(row['lat'], row['lon'], row['datetime-local'])
    df.at[idx, 'wind_speed_10m'] = result.get('wind_speed_10m')
```

**Impact:**
- Buenos Aires: 44,461 rows at ~1-2 sec/row = **12-24 hours**
- NO parallelization despite independent API calls
- Cache helps but still processes 1 request at a time
- Observed: 1-110 it/s depending on cache hits

**Current Speed:** ~1-2 it/s without cache, ~100 it/s with cache
**Theoretical Speed with Threading:** ~500-1000 it/s (20-50 workers)

---

### 🔴 BOTTLENECK 2: Lack of City-Level Parallelization
**File:** `deployment/process_walkable_cities.py`

**Problem:**
```python
for csv_file, img_folder, city_name in cities:  # SEQUENTIAL
    results_df = pipeline.process_folder(walkable_images_dir)
    # Next city only starts after previous completes
```

**Impact:**
- 6+ cities processed one-at-a-time
- GPU/CPU idle while waiting for network I/O
- Single-threaded leaves cores unused
- If one city has 50K images, others wait hours

---

### 🟡 BOTTLENECK 3: Image Processing Not Fully Batched
**File:** `scripts/pipelines/hot_cities_full_pipeline.py`

**Problem:**
```python
for idx, row in tqdm(df.iterrows(), total=total_rows):  # ROW BY ROW
    download_mapillary_image(image_id, temp_image_path)
    is_sunny, sunny_prob = self.classify_sunny(temp_image_path)
    shade_counts = self.detect_shade(temp_image_path)
```

**Current State:**
- Images downloaded one-at-a-time (network-bound)
- ViT/YOLO run on single images (batch_size=1)
- Disk writes happen per image

**GPU Utilization:** Estimated 10-30% (batch_size=1 on GPU is inefficient)

---

### 🟡 BOTTLENECK 4: No Spatial/Temporal Batching for ERA5
**File:** `enhanced_utci.py`

**Problem:**
- Each row requests 3 days of data independently
- Nearby locations (same city) make separate API calls
- Temporal overlaps not exploited
- Cache is in-memory only (lost between runs)

**Example Inefficiency:**
- Row 1: Buenos Aires (-34.60, -58.38) May 15, 2022
- Row 2: Buenos Aires (-34.61, -58.39) May 15, 2022
→ Makes 2 separate API calls for nearly identical data

---

## Optimization Opportunities

### 🚀 Priority 1: Parallelize UTCI Enrichment (IMMEDIATE IMPACT)

**Current:** `add_wind_speed_to_existing.py` (sequential)
```python
for idx in range(len(df)):
    result = get_enhanced_utci_data(...)  # 1-2 sec each
```

**Optimized:** Use ThreadPoolExecutor (already implemented in `batch_add_enhanced_utci_optimized.py`)
```python
with ThreadPoolExecutor(max_workers=20) as executor:
    futures = [executor.submit(fetch_utci_for_row, row_data)
               for row_data in row_data_list]
```

**Expected Speedup:** 10-20x (from 12 hours → 0.6-1.2 hours for Buenos Aires)

**Action Required:**
- Replace `add_wind_speed_to_existing.py` with multithreaded version
- Already have working code in `batch_add_enhanced_utci_optimized.py` (MAX_WORKERS=20)

---

### 🚀 Priority 2: Batch Image Downloads

**Problem:** Sequential downloads waste time
```python
for image_id in image_ids:
    download_mapillary_image(image_id)  # Wait for each
```

**Solution:** Concurrent downloads
```python
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(download_mapillary_image, img_id)
               for img_id in batch]
```

**Expected Speedup:** 5-10x for download phase

---

### 🚀 Priority 3: GPU Batch Processing

**Current:** batch_size=1 (single image inference)

**Solution:**
```python
# Accumulate 32 images
image_batch = []
for i in range(32):
    image_batch.append(load_and_preprocess(images[i]))

# Run ViT on batch
with torch.no_grad():
    batch_tensor = torch.stack(image_batch)
    predictions = self.vit_model(batch_tensor)
```

**Expected Speedup:** 3-5x for ViT inference (GPU utilization 30% → 80%+)

---

### 🚀 Priority 4: City-Level Parallelization

**Solution:** Process multiple cities simultaneously
```python
with ProcessPoolExecutor(max_workers=2) as executor:
    futures = [executor.submit(pipeline.process_city, csv_file)
               for csv_file in csv_files[:2]]  # 2 cities in parallel
```

**Consideration:** Memory/GPU constraints
- Each city needs ~2-4GB GPU memory
- Limit to 2-3 cities max on single GPU
- Or distribute across multiple GPUs/machines

---

### 🚀 Priority 5: Persistent ERA5 Cache

**Current:** In-memory dict (lost between runs)

**Solution:** Disk-based cache
```python
import diskcache
cache = diskcache.Cache('./era5_cache')

def _fetch_era5_multi_day(lat, lon, start_date_str, end_date_str):
    cache_key = (lat, lon, start_date_str, end_date_str)
    if cache_key in cache:
        return cache[cache_key]

    # Fetch from API
    hourly = fetch_from_api(...)
    cache[cache_key] = hourly
    return hourly
```

**Expected Benefit:** 50-90% cache hit rate on re-runs

---

### 🚀 Priority 6: Spatial/Temporal Batching for ERA5

**Problem:** Redundant API calls for nearby locations/times

**Solution:** Pre-fetch ERA5 grids
```python
def prefetch_era5_for_city(df_city):
    """Fetch ERA5 data for entire city date range at once."""
    lat_min, lat_max = df_city['lat'].min(), df_city['lat'].max()
    lon_min, lon_max = df_city['lon'].min(), df_city['lon'].max()
    date_min, date_max = df_city['datetime-local'].min(), df_city['datetime-local'].max()

    # Single API call for entire bounding box + time range
    era5_data = fetch_era5_grid(lat_min, lat_max, lon_min, lon_max,
                                 date_min, date_max)

    # Interpolate for each row locally (fast)
    for idx, row in df_city.iterrows():
        utci = interpolate_era5(era5_data, row['lat'], row['lon'], row['datetime-local'])
```

**Expected Speedup:** 100-1000x API reduction (10,000 calls → 10 calls)

---

## Recommended Implementation Plan

### Phase 1: Quick Wins (1-2 days)
1. ✅ **Use existing multithreaded UTCI script** (`batch_add_enhanced_utci_optimized.py`)
2. **Add persistent disk cache** for ERA5 data (use `diskcache`)
3. **Increase MAX_WORKERS** from 20 → 50 for UTCI enrichment

### Phase 2: Medium Effort (3-5 days)
4. **Implement concurrent image downloads** (ThreadPoolExecutor)
5. **Add GPU batch processing** for ViT (batch_size=32)
6. **Add GPU batch processing** for YOLO (batch_size=16)

### Phase 3: Advanced (1-2 weeks)
7. **City-level parallelization** (ProcessPoolExecutor with 2-3 cities)
8. **Spatial/temporal ERA5 batching** (grid pre-fetching)
9. **Multi-GPU support** for scaling to 5+ cities simultaneously

---

## Performance Projections

### Current Performance (Buenos Aires 44K images)
- Image processing: ~8-12 hours
- UTCI enrichment (sequential): ~12-24 hours
- **Total: ~20-36 hours per city**

### With Phase 1 Optimizations
- Image processing: ~8-12 hours (unchanged)
- UTCI enrichment (20 workers): ~0.6-1.2 hours
- **Total: ~8.6-13.2 hours per city (2-3x speedup)**

### With Phase 1+2 Optimizations
- Image processing (concurrent downloads, batched GPU): ~2-3 hours
- UTCI enrichment: ~0.6-1.2 hours
- **Total: ~2.6-4.2 hours per city (8-14x speedup)**

### With Phase 1+2+3 Optimizations
- 2 cities in parallel: **~2.6-4.2 hours for 2 cities**
- ERA5 grid batching: **~1-2 hours total (10-20x speedup)**

---

## Hardware Recommendations

### Current Setup Assumptions
- Single GPU (likely RTX 3090/4090 or A100)
- 32-64 CPU cores
- 64-128GB RAM

### Optimal Setup for 10+ Cities
- **Multi-GPU:** 2-4 GPUs for parallel city processing
- **More RAM:** 256GB+ for ERA5 grid caching
- **Fast SSD:** NVMe for disk cache (1TB+)
- **Network:** 1Gbps+ for Mapillary/ERA5 API throughput

---

## Code Examples

### Example 1: Multithreaded UTCI (Already Exists)
**File to use:** `batch_add_enhanced_utci_optimized.py`
```python
MAX_WORKERS = 50  # Increase from 20

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = {executor.submit(fetch_utci_for_row, row_data): row_data[0]
               for row_data in row_data_list}

    for future in as_completed(futures):
        idx, result, error = future.result()
        results[idx] = result
```

### Example 2: Persistent Cache
```python
import diskcache

# Initialize once
cache = diskcache.Cache('./cache/era5_cache', size_limit=10e9)  # 10GB limit

def _fetch_era5_multi_day(lat, lon, start_date_str, end_date_str):
    cache_key = (round(lat, 2), round(lon, 2), start_date_str, end_date_str)

    if cache_key in cache:
        return cache[cache_key]

    # Fetch from API
    hourly = fetch_from_api(...)
    cache[cache_key] = hourly
    return hourly
```

### Example 3: Concurrent Image Downloads
```python
def download_images_batch(image_ids, temp_dir, max_workers=10):
    """Download multiple images concurrently."""
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(download_mapillary_image, img_id, temp_dir / f"{img_id}.jpeg"): img_id
            for img_id in image_ids
        }

        results = {}
        for future in as_completed(futures):
            img_id = futures[future]
            results[img_id] = future.result()

    return results
```

### Example 4: GPU Batch Inference
```python
def classify_sunny_batch(self, image_paths, batch_size=32):
    """Classify multiple images in batches."""
    results = []

    for i in range(0, len(image_paths), batch_size):
        batch_paths = image_paths[i:i+batch_size]

        # Load and preprocess batch
        batch_tensors = []
        for path in batch_paths:
            img = Image.open(path).convert("RGB")
            tensor = self.vit_transform(img)
            batch_tensors.append(tensor)

        batch = torch.stack(batch_tensors).to(self.device)

        # Single forward pass for entire batch
        with torch.no_grad():
            outputs = self.vit_model(batch).squeeze(1)
            probs = torch.sigmoid(outputs)
            predictions = probs > 0.5

        for pred, prob in zip(predictions, probs):
            results.append((pred.item(), prob.item()))

    return results
```

---

## Action Items

### Immediate (This Week)
- [ ] **Replace `add_wind_speed_to_existing.py` with multithreaded version**
  - Use `batch_add_enhanced_utci_optimized.py` as template
  - Increase MAX_WORKERS to 50

- [ ] **Add persistent ERA5 cache using diskcache**
  - Modify `enhanced_utci.py` to use disk cache
  - Configure 10GB cache size

- [ ] **Measure baseline performance**
  - Time each pipeline stage
  - Monitor GPU/CPU utilization

### Short-term (Next 2 Weeks)
- [ ] **Implement concurrent image downloads**
  - Modify `hot_cities_full_pipeline.py`
  - Add ThreadPoolExecutor for downloads (max_workers=10)

- [ ] **Add GPU batch processing for ViT**
  - Modify `classify_sunny()` to accept batch
  - Use batch_size=32

- [ ] **Add GPU batch processing for YOLO**
  - YOLO already supports batching
  - Pass list of images instead of single image

### Long-term (Next Month)
- [ ] **Implement city-level parallelization**
  - Use ProcessPoolExecutor
  - Limit to 2-3 cities based on GPU memory

- [ ] **Implement ERA5 grid pre-fetching**
  - Fetch entire city bounding box at once
  - Local interpolation for each row

- [ ] **Add multi-GPU support**
  - Distribute cities across GPUs
  - Scale to 5-10 cities simultaneously

---

## Conclusion

The current pipeline is **heavily bottlenecked by sequential processing** at multiple levels. The single most impactful change is **parallelizing UTCI enrichment**, which can provide a **10-20x speedup immediately** using existing code (`batch_add_enhanced_utci_optimized.py`).

Full optimization across all phases could reduce processing time from **20-36 hours per city** down to **1-2 hours per city**, enabling scalable multi-city analysis.

**Estimated Development Time:**
- Phase 1 (quick wins): 1-2 days
- Phase 2 (medium effort): 3-5 days
- Phase 3 (advanced): 1-2 weeks

**Total: 2-3 weeks for full optimization**
