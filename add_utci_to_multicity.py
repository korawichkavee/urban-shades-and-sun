#!/usr/bin/env python3
# ABOUTME: Add UTCI weather data to all multi-city analyzed CSVs with time estimates

from batch_add_enhanced_utci_optimized import process_city_csv
from pathlib import Path
import logging
import pandas as pd
import time
import sys

def estimate_processing_time(csv_files):
    """Estimate total processing time based on row counts."""
    total_rows = 0
    city_info = []

    for csv_file in csv_files:
        df = pd.read_csv(csv_file, nrows=5)  # Just check if exists
        row_count = sum(1 for _ in open(csv_file)) - 1  # Subtract header
        total_rows += row_count
        city_info.append({
            'city': csv_file.parent.name,
            'rows': row_count,
            'file': csv_file
        })

    # Estimate: ~0.05 seconds per row with 20 parallel workers (optimized)
    # This is based on API response time and parallel processing
    estimated_seconds = total_rows * 0.05
    estimated_minutes = estimated_seconds / 60
    estimated_hours = estimated_minutes / 60

    return city_info, total_rows, estimated_seconds, estimated_minutes, estimated_hours

def main():
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    # Find all analyzed CSVs
    results_dir = Path("data/multi_city_results")
    csv_files = list(results_dir.glob("*/*_analyzed.csv"))

    # Filter out already processed files
    csv_files_to_process = []
    for csv_file in csv_files:
        output_file = csv_file.parent / f"{csv_file.stem}_with_utci.csv"
        if not output_file.exists():
            csv_files_to_process.append(csv_file)

    if not csv_files_to_process:
        logger.info("All cities already have UTCI data!")
        return

    logger.info(f"Found {len(csv_files_to_process)} CSVs to process (out of {len(csv_files)} total)")
    logger.info("")
    logger.info("Estimating processing time...")

    # Get estimates
    city_info, total_rows, est_seconds, est_minutes, est_hours = estimate_processing_time(csv_files_to_process)

    # Print summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("PROCESSING ESTIMATE")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Cities to process:")
    for info in city_info:
        logger.info(f"  {info['city']:20s} - {info['rows']:6,d} rows")
    logger.info("")
    logger.info(f"Total rows: {total_rows:,}")
    logger.info("")
    logger.info("Estimated time:")
    logger.info(f"  {est_seconds:.0f} seconds")
    logger.info(f"  {est_minutes:.1f} minutes")
    if est_hours >= 1:
        logger.info(f"  {est_hours:.2f} hours")
    logger.info("")
    logger.info("Note: Using 20 parallel workers for API calls")
    logger.info("=" * 80)
    logger.info("")

    # Ask for confirmation (unless --yes flag is provided)
    if '--yes' not in sys.argv and '-y' not in sys.argv:
        response = input("Continue with UTCI data collection? (y/n): ")
        if response.lower() != 'y':
            logger.info("Cancelled by user")
            return
    else:
        logger.info("Auto-confirmed with --yes flag")

    # Process each city
    overall_start = time.time()
    completed_cities = 0

    for info in city_info:
        csv_file = info['file']
        city_name = info['city']

        logger.info(f"\n{'='*80}")
        logger.info(f"Processing: {city_name} ({completed_cities+1}/{len(city_info)})")
        logger.info(f"{'='*80}")

        output_file = csv_file.parent / f"{csv_file.stem}_with_utci.csv"

        try:
            city_start = time.time()

            # Process CSV to add UTCI data
            process_city_csv(
                input_path=csv_file,
                output_path=output_file
            )

            city_elapsed = time.time() - city_start
            completed_cities += 1

            # Calculate ETA
            overall_elapsed = time.time() - overall_start
            avg_time_per_city = overall_elapsed / completed_cities
            remaining_cities = len(city_info) - completed_cities
            eta_seconds = avg_time_per_city * remaining_cities

            logger.info(f"✓ Completed {city_name} in {city_elapsed/60:.1f} minutes")
            if remaining_cities > 0:
                logger.info(f"  ETA for remaining {remaining_cities} cities: {eta_seconds/60:.1f} minutes")

        except Exception as e:
            logger.error(f"✗ Error processing {city_name}: {e}")
            import traceback
            traceback.print_exc()

    total_elapsed = time.time() - overall_start
    logger.info(f"\n{'='*80}")
    logger.info("All cities processed!")
    logger.info(f"Total time: {total_elapsed/60:.1f} minutes ({total_elapsed/3600:.2f} hours)")
    logger.info(f"{'='*80}")

if __name__ == "__main__":
    main()
