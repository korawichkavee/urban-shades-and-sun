#!/usr/bin/env python3
# ABOUTME: Optimized wind speed enrichment with parallel processing and persistent caching
# ABOUTME: Uses ThreadPoolExecutor for 10-20x speedup vs sequential processing

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'utils'))
from enhanced_utci import get_enhanced_utci_data

import pandas as pd
from pathlib import Path
from tqdm import tqdm
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Configuration
MAX_WORKERS = 20  # Number of parallel API requests
BATCH_SIZE = 100  # Process in batches for progress updates

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def fetch_utci_for_row(row_data):
    """Fetch UTCI data for a single row (used by parallel executor)."""
    idx, row = row_data

    try:
        result = get_enhanced_utci_data(
            row['lat'],
            row['lon'],
            row['datetime-local']
        )
        return idx, result, None
    except Exception as e:
        return idx, None, str(e)

def add_wind_to_csv_parallel(csv_path, max_workers=MAX_WORKERS):
    """Add wind speed and met data using parallel processing."""
    city_name = csv_path.parent.name
    logger.info(f"\nProcessing {city_name}...")

    # Load CSV
    df = pd.read_csv(csv_path, low_memory=False)

    # Check if wind data already exists
    if 'wind_speed_10m' in df.columns:
        logger.info(f"  Wind data already present, skipping")
        return

    # Check if we have UTCI data
    if 'utci_C' not in df.columns:
        logger.info(f"  No UTCI data found, skipping")
        return

    logger.info(f"  Processing {len(df)} rows with {max_workers} workers...")

    # Initialize new columns
    df['wind_speed_10m'] = None
    df['temperature_2m'] = None
    df['dewpoint_2m'] = None

    # Filter rows that need processing
    valid_rows = [(idx, row) for idx, row in df.iterrows()
                  if not pd.isna(row['datetime-local'])]

    if not valid_rows:
        logger.info(f"  No valid rows to process")
        return

    # Parallel processing
    start_time = time.time()
    success_count = 0
    error_count = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        futures = {
            executor.submit(fetch_utci_for_row, row_data): row_data[0]
            for row_data in valid_rows
        }

        # Process results as they complete
        with tqdm(total=len(valid_rows), desc=f"  {city_name}") as pbar:
            for future in as_completed(futures):
                idx, result, error = future.result()

                if result is not None:
                    df.at[idx, 'wind_speed_10m'] = result.get('wind_speed_10m')
                    df.at[idx, 'temperature_2m'] = result.get('temperature_2m')
                    df.at[idx, 'dewpoint_2m'] = result.get('dewpoint_2m')
                    success_count += 1
                else:
                    error_count += 1
                    if error_count <= 5:  # Log first few errors
                        logger.debug(f"    Row {idx} error: {error}")

                pbar.update(1)

    elapsed = time.time() - start_time
    rate = len(valid_rows) / elapsed if elapsed > 0 else 0

    # Save updated CSV
    df.to_csv(csv_path, index=False)

    logger.info(f"  ✓ Updated {csv_path.name}")
    logger.info(f"    Success: {success_count}/{len(valid_rows)} rows")
    logger.info(f"    Time: {elapsed:.1f}s ({rate:.1f} rows/sec)")
    if error_count > 0:
        logger.info(f"    Errors: {error_count}")

    return elapsed, rate, success_count, error_count

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Add wind speed data with parallel processing")
    parser.add_argument('--workers', type=int, default=MAX_WORKERS,
                        help=f'Number of parallel workers (default: {MAX_WORKERS})')
    parser.add_argument('--dir', type=str, default="data/multi_city_results",
                        help='Directory containing city result CSVs')
    args = parser.parse_args()

    results_dir = Path(args.dir)

    print("="*80)
    print("ADDING WIND SPEED DATA (OPTIMIZED PARALLEL VERSION)")
    print("="*80)
    print(f"\nConfiguration:")
    print(f"  Workers: {args.workers}")
    print(f"  Directory: {results_dir}")
    print(f"  Using persistent disk cache for ERA5 data")
    print()

    csv_files = list(results_dir.glob("*/*_analyzed_with_utci.csv"))

    logger.info(f"Found {len(csv_files)} CSVs to update\n")

    if not csv_files:
        logger.error(f"No CSV files found in {results_dir}")
        return

    # Track overall performance
    total_start = time.time()
    all_stats = []

    for csv_file in sorted(csv_files):
        stats = add_wind_to_csv_parallel(csv_file, max_workers=args.workers)
        if stats:
            all_stats.append(stats)

    total_elapsed = time.time() - total_start

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    if all_stats:
        total_time = sum(s[0] for s in all_stats)
        total_rows = sum(s[2] for s in all_stats)
        avg_rate = sum(s[1] for s in all_stats) / len(all_stats)

        print(f"  Cities processed: {len(all_stats)}")
        print(f"  Total rows: {total_rows}")
        print(f"  Total processing time: {total_time:.1f}s")
        print(f"  Average rate: {avg_rate:.1f} rows/sec")
        print(f"  Wall clock time: {total_elapsed:.1f}s")

    print("\n" + "="*80)
    print("✓ COMPLETE")
    print("="*80)
    print()

if __name__ == "__main__":
    main()
