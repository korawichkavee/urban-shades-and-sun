# ABOUTME: Deduplicated UTCI annotation - fetches unique date+location combinations only.
# ABOUTME: Reduces API calls by ~75% by fetching unique combinations then joining back.

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
import signal


MAX_WORKERS = 8  # Conservative to avoid rate limiting
CHECKPOINT_INTERVAL = 1000  # Save every N unique fetches
INTER_CHUNK_DELAY = 5  # Seconds to wait between chunks to respect rate limits


class GracefulKiller:
    """Handle interrupt signals gracefully."""
    kill_now = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, *args):
        self.kill_now = True
        print("\n\nReceived interrupt signal. Finishing current batch and saving checkpoint...")


def setup_logging(log_file):
    """Configure logging to console and file."""
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(message)s'))

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logging.getLogger(__name__)


def fetch_utci_for_unique_location(unique_key, lat, lon, timestamp_str):
    """Fetch UTCI data for a unique date+location combination."""
    try:
        result = get_enhanced_utci_data(lat, lon, timestamp_str)
        return unique_key, result, None
    except Exception as e:
        return unique_key, None, str(e)


def process_chunk(chunk_df, chunk_num, total_chunks, logger, max_workers, killer):
    """Process a chunk of unique date+location combinations."""

    # Prepare fetch tasks
    fetch_tasks = []
    for _, row in chunk_df.iterrows():
        unique_key = row['unique_key']
        lat = row['lat_rounded']
        lon = row['lon_rounded']
        # Use the representative timestamp for this date+location
        timestamp_str = row['representative_datetime']
        fetch_tasks.append((unique_key, lat, lon, timestamp_str))

    results = {}
    errors = {}

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_key = {
            executor.submit(fetch_utci_for_unique_location, *task): task[0]
            for task in fetch_tasks
        }

        with tqdm(total=len(fetch_tasks),
                 desc=f"  Chunk {chunk_num}/{total_chunks}",
                 unit="unique",
                 position=0,
                 leave=True) as pbar:

            for future in as_completed(future_to_key):
                if killer.kill_now:
                    logger.warning("Interrupt detected, cancelling remaining tasks...")
                    executor.shutdown(wait=False, cancel_futures=True)
                    break

                unique_key, result, error = future.result()

                if error:
                    errors[unique_key] = error
                else:
                    results[unique_key] = result

                pbar.update(1)

    elapsed = time.time() - start_time
    rate = len(results) / elapsed if elapsed > 0 else 0

    return results, errors, rate


def main():
    parser = argparse.ArgumentParser(
        description='Add UTCI data with deduplication (fetch unique date+location only)'
    )
    parser.add_argument(
        '--input',
        type=str,
        default='data/transit_surveys/processed/metro_surveys_standardized.csv',
        help='Path to standardized trips CSV'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output path (default: adds _with_utci suffix)'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=MAX_WORKERS,
        help=f'Number of parallel workers (default: {MAX_WORKERS})'
    )
    parser.add_argument(
        '--checkpoint-interval',
        type=int,
        default=CHECKPOINT_INTERVAL,
        help=f'Save checkpoint every N unique fetches (default: {CHECKPOINT_INTERVAL})'
    )
    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume from last checkpoint if available'
    )

    args = parser.parse_args()

    # Setup paths
    project_root = Path(__file__).parent.parent.parent
    input_path = project_root / args.input

    if args.output:
        output_path = project_root / args.output
    else:
        output_path = input_path.parent / input_path.name.replace('.csv', '_with_utci.csv')

    unique_checkpoint = output_path.parent / (output_path.stem + '_unique_checkpoint.csv')
    final_checkpoint = output_path.parent / (output_path.stem + '_checkpoint.csv')

    # Setup logging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = project_root / "logs" / f"utci_deduped_{timestamp}.log"
    logger = setup_logging(log_file)

    # Setup graceful shutdown
    killer = GracefulKiller()

    logger.info("="*70)
    logger.info("DEDUPLICATED UTCI ANNOTATION")
    logger.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Log file: {log_file}")
    logger.info(f"Checkpoint interval: {args.checkpoint_interval:,} unique fetches")
    logger.info(f"Max workers: {args.workers}")
    logger.info(f"Inter-chunk delay: {INTER_CHUNK_DELAY}s")
    logger.info("="*70)

    # Load data
    logger.info(f"\nLoading data from {input_path}")
    trips_df = pd.read_csv(input_path, low_memory=False)
    trips_df['datetime'] = pd.to_datetime(trips_df['datetime'])
    logger.info(f"  Loaded {len(trips_df):,} trips")

    # Create unique combinations (date + hour + location for hourly accuracy)
    logger.info("\nIdentifying unique date+hour+location combinations...")
    trips_df['date'] = trips_df['datetime'].dt.date
    trips_df['hour'] = trips_df['datetime'].dt.hour
    trips_df['lat_rounded'] = trips_df['lat'].round(2)
    trips_df['lon_rounded'] = trips_df['lon'].round(2)
    trips_df['unique_key'] = (
        trips_df['date'].astype(str) + '_' +
        trips_df['hour'].astype(str) + '_' +
        trips_df['lat_rounded'].astype(str) + '_' +
        trips_df['lon_rounded'].astype(str)
    )

    # Get unique combinations with representative datetime
    unique_combos = trips_df.groupby('unique_key').agg({
        'lat_rounded': 'first',
        'lon_rounded': 'first',
        'date': 'first',
        'hour': 'first',
        'datetime': 'first'  # Use first occurrence as representative
    }).reset_index()
    unique_combos.rename(columns={'datetime': 'representative_datetime'}, inplace=True)

    logger.info(f"  Total trips: {len(trips_df):,}")
    logger.info(f"  Unique date+hour+location combos: {len(unique_combos):,}")
    logger.info(f"  Reduction: {100*(1 - len(unique_combos)/len(trips_df)):.1f}%")

    # Check for existing checkpoint
    start_idx = 0
    fetched_results = {}

    if args.resume and unique_checkpoint.exists():
        logger.info(f"\nResuming from checkpoint: {unique_checkpoint}")
        checkpoint_df = pd.read_csv(unique_checkpoint)

        # Load already fetched results
        for _, row in checkpoint_df.iterrows():
            if pd.notna(row.get('utci_C')):
                key = row['unique_key']
                fetched_results[key] = {
                    'utci_K': row['utci_K'],
                    'utci_C': row['utci_C'],
                    'utci_timestamp': row['utci_timestamp'],
                    'wind_speed_10m': row['wind_speed_10m'],
                    'temperature_2m': row['temperature_2m'],
                    'dewpoint_2m': row['dewpoint_2m'],
                    'prior_day_utci_avg_C': row['prior_day_utci_avg_C'],
                    'next_day_utci_avg_C': row['next_day_utci_avg_C'],
                    'prior_day_rain': row['prior_day_rain'],
                    'next_day_rain': row['next_day_rain'],
                }

        start_idx = len(fetched_results)
        logger.info(f"  Resuming from {start_idx:,} / {len(unique_combos):,} unique combinations")

    # Filter to unfetched combinations
    if start_idx > 0:
        already_fetched_keys = set(fetched_results.keys())
        unique_combos = unique_combos[~unique_combos['unique_key'].isin(already_fetched_keys)].reset_index(drop=True)
        logger.info(f"  {len(unique_combos):,} unique combinations remaining to fetch")

    # Process in chunks
    overall_start = time.time()
    total_unique = len(unique_combos)
    processed_count = start_idx

    logger.info(f"\nProcessing {total_unique:,} unique combinations in chunks of {args.checkpoint_interval:,}")
    logger.info("")

    chunk_start_idx = 0
    while chunk_start_idx < total_unique and not killer.kill_now:
        chunk_end_idx = min(chunk_start_idx + args.checkpoint_interval, total_unique)
        chunk = unique_combos.iloc[chunk_start_idx:chunk_end_idx]

        chunk_num = chunk_start_idx // args.checkpoint_interval + 1
        total_chunks = (total_unique + args.checkpoint_interval - 1) // args.checkpoint_interval

        logger.info(f"Processing chunk {chunk_num}/{total_chunks} (unique combinations {chunk_start_idx:,} to {chunk_end_idx:,})")

        # Process chunk
        results, errors, rate = process_chunk(chunk, chunk_num, total_chunks, logger, args.workers, killer)

        # Add results to fetched_results
        fetched_results.update(results)
        processed_count = start_idx + chunk_end_idx

        # Log progress
        valid_utci = sum(1 for r in results.values() if r and r.get('utci_C') is not None)
        logger.info(f"  Completed: {len(results):,} unique combos, {valid_utci:,} with valid UTCI ({rate:.1f}/sec)")
        if errors:
            logger.info(f"  Errors: {len(errors):,}")

        # Save checkpoint of unique combinations
        checkpoint_data = []
        for key, result in fetched_results.items():
            row_data = {'unique_key': key}
            row_data.update(result)
            checkpoint_data.append(row_data)

        checkpoint_df = pd.DataFrame(checkpoint_data)
        checkpoint_df.to_csv(unique_checkpoint, index=False)
        logger.info(f"  Saved unique combinations checkpoint: {unique_checkpoint}")

        # Calculate ETA
        elapsed = time.time() - overall_start
        combos_remaining = total_unique - chunk_end_idx
        if chunk_end_idx > 0:
            avg_rate = chunk_end_idx / elapsed
            eta_seconds = combos_remaining / avg_rate if avg_rate > 0 else 0
            eta_time = datetime.now() + timedelta(seconds=eta_seconds)
            logger.info(f"  Progress: {processed_count:,}/{len(unique_combos) + start_idx:,} ({100*chunk_end_idx/total_unique:.1f}%)")
            logger.info(f"  ETA: {eta_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("")

        if killer.kill_now:
            logger.warning("Interrupt detected, stopping after checkpoint save")
            break

        chunk_start_idx = chunk_end_idx

        # Pause between chunks to respect rate limits
        if chunk_start_idx < total_unique:
            logger.info(f"  Waiting {INTER_CHUNK_DELAY}s before next chunk...")
            time.sleep(INTER_CHUNK_DELAY)

    # Join results back to original dataframe
    if not killer.kill_now:
        logger.info("\nJoining results back to original trips...")

        # Create result columns (only what get_enhanced_utci_data returns)
        result_cols = {
            'utci_K': [],
            'utci_C': [],
            'utci_timestamp': [],
            'wind_speed_10m': [],
            'temperature_2m': [],
            'dewpoint_2m': []
        }

        for _, row in tqdm(trips_df.iterrows(), total=len(trips_df), desc="  Joining"):
            key = row['unique_key']
            result = fetched_results.get(key)

            if result:
                for col in result_cols.keys():
                    result_cols[col].append(result.get(col))
            else:
                for col in result_cols.keys():
                    result_cols[col].append(None)

        # Add columns to dataframe
        for col, values in result_cols.items():
            trips_df[col] = values

        # Drop temporary columns
        trips_df.drop(columns=['date', 'hour', 'lat_rounded', 'lon_rounded', 'unique_key'], inplace=True)

        # Save final output
        logger.info(f"\nSaving final output to {output_path}")
        trips_df.to_csv(output_path, index=False)

        # Remove checkpoints
        if unique_checkpoint.exists():
            unique_checkpoint.unlink()
            logger.info(f"Removed unique combinations checkpoint")

    # Final statistics
    total_elapsed = time.time() - overall_start

    logger.info("")
    logger.info("="*70)
    if killer.kill_now:
        logger.info("PROCESSING INTERRUPTED - CHECKPOINT SAVED")
        logger.info(f"Resume with: python {Path(__file__).name} --resume")
    else:
        logger.info("PROCESSING COMPLETE")
    logger.info(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Total time: {total_elapsed/3600:.1f} hours")
    logger.info(f"Unique combinations fetched: {len(fetched_results):,}")

    if not killer.kill_now:
        valid_utci = trips_df['utci_C'].notna().sum()
        logger.info(f"Total trips annotated: {len(trips_df):,}")
        logger.info(f"Valid UTCI: {valid_utci:,} ({100*valid_utci/len(trips_df):.1f}%)")
        logger.info(f"Output: {output_path}")
    else:
        logger.info(f"Checkpoint: {unique_checkpoint}")
    logger.info("="*70)


if __name__ == '__main__':
    main()
