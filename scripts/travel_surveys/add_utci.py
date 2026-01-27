# ABOUTME: Adds UTCI thermal comfort data to standardized travel survey trips.
# ABOUTME: Uses existing enhanced_utci infrastructure to fetch weather and thermal comfort data.

import sys
from pathlib import Path

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'utils'))
from enhanced_utci import get_enhanced_utci_data

import pandas as pd
import argparse
import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import time


MAX_WORKERS = 20  # Number of parallel API requests


def setup_logging(log_file=None):
    """Configure logging to console and optionally to file."""
    handlers = [logging.StreamHandler()]

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=handlers,
        force=True
    )
    return logging.getLogger(__name__)


def fetch_utci_for_trip(trip_data):
    """Fetch UTCI data for a single trip (used in multithreading)."""
    idx, lat, lon, timestamp = trip_data
    try:
        result = get_enhanced_utci_data(lat, lon, timestamp)
        return idx, result, None
    except Exception as e:
        return idx, None, str(e)


def add_utci_to_trips(trips_df, logger, max_workers=MAX_WORKERS):
    """
    Add UTCI thermal comfort data to trips dataframe.

    Uses multithreading to parallelize API calls to ERA5 weather data.
    """
    logger.info(f"Adding UTCI data to {len(trips_df)} trips...")
    logger.info(f"  Using {max_workers} parallel workers")

    # Prepare data for multithreaded processing
    trip_data_list = []
    for idx, row in trips_df.iterrows():
        timestamp = row['datetime']
        trip_data_list.append((idx, row['lat'], row['lon'], timestamp))

    # Initialize result storage
    results = {idx: None for idx in trips_df.index}
    errors = {}

    # Process with multithreading and progress tracking
    start_time = time.time()
    completed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_idx = {
            executor.submit(fetch_utci_for_trip, trip_data): trip_data[0]
            for trip_data in trip_data_list
        }

        # Process completed tasks with progress bar
        with tqdm(total=len(trip_data_list), desc="  Fetching UTCI", unit="trip") as pbar:
            for future in as_completed(future_to_idx):
                idx, result, error = future.result()

                if error:
                    errors[idx] = error
                else:
                    results[idx] = result

                completed += 1
                pbar.update(1)

                # Log progress every 1000 trips
                if completed % 1000 == 0:
                    elapsed = time.time() - start_time
                    rate = completed / elapsed
                    remaining = len(trip_data_list) - completed
                    eta_seconds = remaining / rate if rate > 0 else 0
                    eta_time = datetime.now() + timedelta(seconds=eta_seconds)

                    logger.info(
                        f"  Progress: {completed:,}/{len(trip_data_list):,} "
                        f"({rate:.1f} trips/sec, ETA: {eta_time.strftime('%H:%M:%S')})"
                    )

    # Log final timing
    elapsed = time.time() - start_time
    logger.info(f"  Completed {completed:,} trips in {elapsed:.1f}s ({completed/elapsed:.1f} trips/sec)")

    if errors:
        logger.warning(f"  Encountered {len(errors):,} errors during processing")
        # Log first 5 errors
        for idx, error in list(errors.items())[:5]:
            logger.debug(f"    Trip {idx}: {error}")

    # Convert results to columns
    result_cols = {
        'utci_K': [],
        'utci_C': [],
        'utci_timestamp': [],
        'wind_speed_10m': [],
        'temperature_2m': [],
        'dewpoint_2m': [],
        'prior_day_utci_avg_C': [],
        'next_day_utci_avg_C': [],
        'prior_day_rain': [],
        'next_day_rain': []
    }

    for idx in trips_df.index:
        result = results.get(idx)
        if result:
            for key in result_cols.keys():
                result_cols[key].append(result[key])
        else:
            # Append None for failed trips
            for key in result_cols.keys():
                result_cols[key].append(None)

    # Assign results to dataframe
    for key, values in result_cols.items():
        trips_df[key] = values

    return trips_df


def main():
    parser = argparse.ArgumentParser(
        description='Add UTCI thermal comfort data to travel survey trips'
    )
    parser.add_argument(
        '--input',
        type=str,
        default='data/transit_surveys/processed/nhts_2017_standardized.csv',
        help='Path to standardized trips CSV'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output path (default: adds _with_utci suffix to input)'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=MAX_WORKERS,
        help=f'Number of parallel workers (default: {MAX_WORKERS})'
    )
    parser.add_argument(
        '--sample',
        type=int,
        default=None,
        help='Process only first N trips (for testing)'
    )

    args = parser.parse_args()

    # Setup paths
    project_root = Path(__file__).parent.parent.parent
    input_path = project_root / args.input

    if args.output:
        output_path = project_root / args.output
    else:
        # Add _with_utci before extension
        output_path = input_path.parent / input_path.name.replace('.csv', '_with_utci.csv')

    # Setup logging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = project_root / "logs" / f"utci_annotation_{timestamp}.log"
    logger = setup_logging(log_file)

    logger.info("="*60)
    logger.info("Starting UTCI annotation for travel survey data")
    logger.info(f"Log file: {log_file}")
    logger.info("="*60)

    # Load data
    logger.info(f"Loading trips from {input_path}...")
    if args.sample:
        trips_df = pd.read_csv(input_path, nrows=args.sample)
        logger.info(f"  Loaded {len(trips_df):,} trips (sample)")
    else:
        trips_df = pd.read_csv(input_path)
        logger.info(f"  Loaded {len(trips_df):,} trips")

    # Parse datetime
    trips_df['datetime'] = pd.to_datetime(trips_df['datetime'])

    # Check if UTCI already exists
    if 'utci_C' in trips_df.columns:
        logger.warning("UTCI data already present in input file!")
        response = input("Continue and overwrite? (y/n): ")
        if response.lower() != 'y':
            logger.info("Aborted")
            return

    # Add UTCI data
    overall_start = time.time()
    trips_with_utci = add_utci_to_trips(trips_df, logger, max_workers=args.workers)

    # Save result
    logger.info(f"Saving results to {output_path}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    trips_with_utci.to_csv(output_path, index=False)

    # Summary statistics
    total_elapsed = time.time() - overall_start
    logger.info("="*60)
    logger.info("Processing complete!")
    logger.info(f"  Total time: {total_elapsed/60:.1f} minutes")
    logger.info(f"  Processed: {len(trips_with_utci):,} trips")
    logger.info(f"  Output: {output_path}")

    # UTCI statistics
    valid_utci = trips_with_utci['utci_C'].notna()
    logger.info(f"\nUTCI data quality:")
    logger.info(f"  Valid UTCI values: {valid_utci.sum():,} ({100*valid_utci.mean():.1f}%)")

    if valid_utci.sum() > 0:
        logger.info(f"  UTCI range: {trips_with_utci['utci_C'].min():.1f}°C to {trips_with_utci['utci_C'].max():.1f}°C")
        logger.info(f"  UTCI mean: {trips_with_utci['utci_C'].mean():.1f}°C")
        logger.info(f"  UTCI median: {trips_with_utci['utci_C'].median():.1f}°C")

    logger.info("="*60)


if __name__ == '__main__':
    main()
