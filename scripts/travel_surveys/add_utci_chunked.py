# ABOUTME: Chunked UTCI annotation with checkpoint saving for long-running jobs.
# ABOUTME: Processes data in batches and saves progress to allow resumption on failure.

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


MAX_WORKERS = 12  # Reduced to avoid rate limiting
CHECKPOINT_INTERVAL = 5000  # Save every N trips
INTER_CHUNK_DELAY = 3  # Seconds to wait between chunks


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


def fetch_utci_for_trip(trip_data):
    """Fetch UTCI data for a single trip."""
    idx, lat, lon, timestamp = trip_data
    try:
        result = get_enhanced_utci_data(lat, lon, timestamp)
        return idx, result, None
    except Exception as e:
        return idx, None, str(e)


def process_chunk(chunk_df, chunk_start_idx, logger, max_workers, killer):
    """Process a chunk of trips with UTCI data."""
    trip_data_list = []
    for idx, row in chunk_df.iterrows():
        timestamp = row['datetime']
        trip_data_list.append((idx, row['lat'], row['lon'], timestamp))

    results = {}
    errors = {}

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {
            executor.submit(fetch_utci_for_trip, trip_data): trip_data[0]
            for trip_data in trip_data_list
        }

        with tqdm(total=len(trip_data_list),
                 desc=f"  Chunk {chunk_start_idx//CHECKPOINT_INTERVAL + 1}",
                 unit="trip",
                 position=0,
                 leave=True) as pbar:

            for future in as_completed(future_to_idx):
                if killer.kill_now:
                    logger.warning("Interrupt detected, cancelling remaining tasks...")
                    executor.shutdown(wait=False, cancel_futures=True)
                    break

                idx, result, error = future.result()

                if error:
                    errors[idx] = error
                else:
                    results[idx] = result

                pbar.update(1)

    elapsed = time.time() - start_time
    rate = len(results) / elapsed if elapsed > 0 else 0

    return results, errors, rate


def add_results_to_dataframe(df, results, errors):
    """Add UTCI results to dataframe."""
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

    for idx in df.index:
        result = results.get(idx)
        if result:
            for key in result_cols.keys():
                result_cols[key].append(result[key])
        else:
            for key in result_cols.keys():
                result_cols[key].append(None)

    for key, values in result_cols.items():
        df[key] = values

    return df


def main():
    parser = argparse.ArgumentParser(
        description='Add UTCI data with chunked processing and checkpoints'
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
        help=f'Save checkpoint every N trips (default: {CHECKPOINT_INTERVAL})'
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

    checkpoint_path = output_path.parent / (output_path.stem + '_checkpoint.csv')

    # Setup logging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = project_root / "logs" / f"utci_chunked_{timestamp}.log"
    logger = setup_logging(log_file)

    # Setup graceful shutdown
    killer = GracefulKiller()

    logger.info("="*70)
    logger.info("CHUNKED UTCI ANNOTATION WITH CHECKPOINTS")
    logger.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Log file: {log_file}")
    logger.info(f"Checkpoint interval: {args.checkpoint_interval:,} trips")
    logger.info(f"Max workers: {args.workers}")
    logger.info("="*70)

    # Load or resume data
    start_idx = 0

    if args.resume and checkpoint_path.exists():
        logger.info(f"\nResuming from checkpoint: {checkpoint_path}")
        trips_df = pd.read_csv(checkpoint_path)
        trips_df['datetime'] = pd.to_datetime(trips_df['datetime'])

        # Find where to resume (first row without UTCI)
        if 'utci_C' in trips_df.columns:
            incomplete = trips_df['utci_C'].isna()
            if incomplete.any():
                start_idx = incomplete.idxmax()
                logger.info(f"  Resuming from trip {start_idx:,} / {len(trips_df):,}")
            else:
                logger.info("  Checkpoint is complete! Nothing to process.")
                return
        else:
            logger.info("  Checkpoint has no UTCI data, starting from beginning")
    else:
        logger.info(f"\nLoading fresh data from {input_path}")
        trips_df = pd.read_csv(input_path)
        trips_df['datetime'] = pd.to_datetime(trips_df['datetime'])
        logger.info(f"  Loaded {len(trips_df):,} trips")

        # Initialize UTCI columns
        for col in ['utci_K', 'utci_C', 'utci_timestamp', 'wind_speed_10m',
                    'temperature_2m', 'dewpoint_2m', 'prior_day_utci_avg_C',
                    'next_day_utci_avg_C', 'prior_day_rain', 'next_day_rain']:
            trips_df[col] = None

    # Process in chunks
    overall_start = time.time()
    total_trips = len(trips_df)
    processed_count = start_idx

    logger.info(f"\nProcessing {total_trips - start_idx:,} remaining trips in chunks of {args.checkpoint_interval:,}")
    logger.info("")

    while start_idx < total_trips and not killer.kill_now:
        end_idx = min(start_idx + args.checkpoint_interval, total_trips)
        chunk = trips_df.iloc[start_idx:end_idx]

        chunk_num = start_idx // args.checkpoint_interval + 1
        total_chunks = (total_trips + args.checkpoint_interval - 1) // args.checkpoint_interval

        logger.info(f"Processing chunk {chunk_num}/{total_chunks} (trips {start_idx:,} to {end_idx:,})")

        # Process chunk
        results, errors, rate = process_chunk(chunk, start_idx, logger, args.workers, killer)

        # Update dataframe with results
        for idx in range(start_idx, end_idx):
            result = results.get(idx)
            if result:
                for key, value in result.items():
                    trips_df.at[idx, key] = value

        processed_count = end_idx

        # Log progress
        valid_utci = sum(1 for r in results.values() if r and r.get('utci_C') is not None)
        logger.info(f"  Completed: {len(results):,} trips, {valid_utci:,} with valid UTCI ({rate:.1f} trips/sec)")
        if errors:
            logger.info(f"  Errors: {len(errors):,}")

        # Save checkpoint
        trips_df.to_csv(checkpoint_path, index=False)
        logger.info(f"  Saved checkpoint: {checkpoint_path}")

        # Calculate ETA
        elapsed = time.time() - overall_start
        trips_remaining = total_trips - processed_count
        if processed_count > start_idx:
            avg_rate = (processed_count - start_idx) / elapsed
            eta_seconds = trips_remaining / avg_rate if avg_rate > 0 else 0
            eta_time = datetime.now() + timedelta(seconds=eta_seconds)
            logger.info(f"  Progress: {processed_count:,}/{total_trips:,} ({100*processed_count/total_trips:.1f}%)")
            logger.info(f"  ETA: {eta_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("")

        if killer.kill_now:
            logger.warning("Interrupt detected, stopping after checkpoint save")
            break

        start_idx = end_idx

        # Brief pause between chunks to avoid rate limiting
        if start_idx < total_trips:
            time.sleep(INTER_CHUNK_DELAY)

    # Save final output
    if not killer.kill_now:
        logger.info(f"Saving final output to {output_path}")
        trips_df.to_csv(output_path, index=False)

        # Remove checkpoint
        if checkpoint_path.exists():
            checkpoint_path.unlink()
            logger.info(f"Removed checkpoint file")

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
    logger.info(f"Processed: {processed_count:,} trips")

    valid_utci = trips_df['utci_C'].notna().sum()
    logger.info(f"Valid UTCI: {valid_utci:,} ({100*valid_utci/len(trips_df):.1f}%)")

    if not killer.kill_now:
        logger.info(f"Output: {output_path}")
    else:
        logger.info(f"Checkpoint: {checkpoint_path}")
    logger.info("="*70)


if __name__ == '__main__':
    main()
