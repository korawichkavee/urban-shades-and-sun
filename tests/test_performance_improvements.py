#!/usr/bin/env python3
"""
Performance testing for UTCI enrichment optimizations.
Tests sequential vs parallel processing with small dataset.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts' / 'utils'))

import pandas as pd
import time
from datetime import datetime, timedelta
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from enhanced_utci import get_enhanced_utci_data

def generate_test_data(n_rows=100):
    """Generate small test dataset for benchmarking."""
    # Buenos Aires coordinates with some variation
    base_lat, base_lon = -34.603722, -58.381592

    # Generate random dates in May 2022
    base_date = datetime(2022, 5, 15, 12, 0, 0)

    data = {
        'lat': [base_lat + np.random.uniform(-0.1, 0.1) for _ in range(n_rows)],
        'lon': [base_lon + np.random.uniform(-0.1, 0.1) for _ in range(n_rows)],
        'datetime-local': [base_date + timedelta(hours=np.random.randint(0, 168)) for _ in range(n_rows)]
    }

    return pd.DataFrame(data)

def process_row_sequential(idx, row):
    """Process single row (current method)."""
    try:
        result = get_enhanced_utci_data(
            row['lat'],
            row['lon'],
            row['datetime-local'].isoformat()
        )
        return idx, result, None
    except Exception as e:
        return idx, None, str(e)

def test_sequential_processing(df, desc="Sequential"):
    """Test current sequential processing."""
    print(f"\n{'='*60}")
    print(f"Testing {desc} Processing")
    print(f"{'='*60}")
    print(f"Processing {len(df)} rows...")

    start_time = time.time()
    results = []

    for idx, row in df.iterrows():
        _, result, error = process_row_sequential(idx, row)
        if result:
            results.append(result)
        if (idx + 1) % 10 == 0:
            print(f"  Processed {idx+1}/{len(df)} rows...")

    elapsed = time.time() - start_time
    rate = len(df) / elapsed if elapsed > 0 else 0

    print(f"\nResults:")
    print(f"  Total time: {elapsed:.2f} seconds")
    print(f"  Rate: {rate:.2f} rows/second")
    print(f"  Success: {len(results)}/{len(df)} rows")

    return elapsed, rate, len(results)

def test_parallel_processing(df, max_workers=20, desc="Parallel"):
    """Test parallel processing with ThreadPoolExecutor."""
    print(f"\n{'='*60}")
    print(f"Testing {desc} Processing (workers={max_workers})")
    print(f"{'='*60}")
    print(f"Processing {len(df)} rows...")

    start_time = time.time()
    results = []
    errors = []

    # Prepare data for parallel processing
    row_data_list = [(idx, row) for idx, row in df.iterrows()]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_row_sequential, idx, row): idx
            for idx, row in row_data_list
        }

        completed = 0
        for future in as_completed(futures):
            idx, result, error = future.result()
            if result:
                results.append(result)
            else:
                errors.append((idx, error))

            completed += 1
            if completed % 10 == 0:
                print(f"  Processed {completed}/{len(df)} rows...")

    elapsed = time.time() - start_time
    rate = len(df) / elapsed if elapsed > 0 else 0

    print(f"\nResults:")
    print(f"  Total time: {elapsed:.2f} seconds")
    print(f"  Rate: {rate:.2f} rows/second")
    print(f"  Success: {len(results)}/{len(df)} rows")
    if errors:
        print(f"  Errors: {len(errors)}")

    return elapsed, rate, len(results)

def compare_performance(df, worker_counts=[1, 10, 20, 50]):
    """Compare performance across different worker counts."""
    print(f"\n{'='*60}")
    print(f"PERFORMANCE COMPARISON")
    print(f"{'='*60}")
    print(f"Dataset size: {len(df)} rows\n")

    # Test sequential (baseline)
    seq_time, seq_rate, seq_success = test_sequential_processing(df.head(10), "Sequential (10 rows)")

    # Test parallel with different worker counts
    results = []
    for workers in worker_counts:
        if workers == 1:
            # Sequential-style (1 worker)
            time_taken, rate, success = test_parallel_processing(
                df.head(10), max_workers=1, desc=f"Parallel (1 worker, 10 rows)"
            )
        else:
            # Use more rows for parallel tests
            test_size = min(50, len(df))
            time_taken, rate, success = test_parallel_processing(
                df.head(test_size), max_workers=workers,
                desc=f"Parallel ({workers} workers, {test_size} rows)"
            )

        results.append({
            'workers': workers,
            'time': time_taken,
            'rate': rate,
            'success': success
        })

    # Print comparison table
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"{'Workers':<10} {'Time (s)':<12} {'Rate (r/s)':<15} {'Speedup':<10}")
    print(f"{'-'*60}")

    baseline_time = seq_time
    for r in results:
        speedup = baseline_time / r['time'] if r['time'] > 0 else 0
        print(f"{r['workers']:<10} {r['time']:<12.2f} {r['rate']:<15.2f} {speedup:<10.2f}x")

    return results

def main():
    print("="*60)
    print("UTCI ENRICHMENT PERFORMANCE TEST")
    print("="*60)

    # Generate test data
    print("\nGenerating test dataset...")
    df = generate_test_data(n_rows=100)
    print(f"Created dataset with {len(df)} rows")
    print(f"Date range: {df['datetime-local'].min()} to {df['datetime-local'].max()}")
    print(f"Location: Buenos Aires (lat: {df['lat'].min():.2f} to {df['lat'].max():.2f})")

    # Run performance comparison
    results = compare_performance(df, worker_counts=[1, 10, 20])

    # Recommendations
    print(f"\n{'='*60}")
    print("RECOMMENDATIONS")
    print(f"{'='*60}")

    if len(results) > 1:
        best = max(results[1:], key=lambda x: x['rate'])
        baseline = results[0]
        speedup = best['rate'] / baseline['rate']

        print(f"✓ Optimal worker count: {best['workers']}")
        print(f"✓ Speedup vs sequential: {speedup:.1f}x")
        print(f"✓ Rate improvement: {baseline['rate']:.1f} → {best['rate']:.1f} rows/sec")

        # Project to full dataset
        if 'Buenos Aires' in str(df['datetime-local'].iloc[0]):
            full_size = 44461  # Buenos Aires actual size
            print(f"\nProjection for Buenos Aires ({full_size} rows):")
            print(f"  Sequential time: {full_size / baseline['rate'] / 3600:.1f} hours")
            print(f"  Parallel time: {full_size / best['rate'] / 3600:.1f} hours")
            print(f"  Time saved: {(full_size / baseline['rate'] - full_size / best['rate']) / 3600:.1f} hours")

if __name__ == "__main__":
    main()
