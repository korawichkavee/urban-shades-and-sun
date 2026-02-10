# ABOUTME: Adds UTCI weather data to metro commute SVI analyzed CSVs.
# ABOUTME: Merges analyzed CSVs with metadata for local datetime, then fetches UTCI via ERA5 API.

import sys
import argparse
import logging
import time
import signal
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import pytz
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent / 'utils'))
from enhanced_utci import get_enhanced_utci_data


# Cities present in both analyzed and metadata directories
CITY_TIMEZONES = {
    'anchorage': 'America/Anchorage',
    'atlanta': 'America/New_York',
    'boise': 'America/Boise',
    'cleveland': 'America/New_York',
    'columbia': 'America/New_York',
    'denver': 'America/Denver',
    'evansville': 'America/Chicago',
    'honolulu': 'Pacific/Honolulu',
    'louisville': 'America/New_York',
    'minneapolis': 'America/Chicago',
    'salt-lake-city': 'America/Denver',
    'st.-louis': 'America/Chicago',
    'tucson': 'America/Phoenix',
}

MAX_WORKERS = 20
CHECKPOINT_INTERVAL = 1000
INTER_CHUNK_DELAY = 5


class GracefulKiller:
    """Handle interrupt signals gracefully."""
    kill_now = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, *args):
        self.kill_now = True
        print("\nReceived interrupt. Finishing current batch and saving checkpoint...")


def setup_logging(log_file):
    """Configure logging to console and file."""
    log_file.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(message)s'))

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logging.getLogger(__name__)


def add_local_datetime(df, timezone_str):
    """
    Convert UTC captured_at to local datetime string.

    captured_at in the analyzed CSVs is a UTC timestamp string.
    Converts to local time using the city's timezone.
    """
    tz = pytz.timezone(timezone_str)
    captured = pd.to_datetime(df['captured_at'], format='mixed')
    # Localize to UTC then convert to local time
    local_time = captured.dt.tz_localize('UTC').dt.tz_convert(tz)
    df['datetime-local'] = local_time.dt.strftime('%Y-%m-%d %H:%M:%S')
    return df


def fetch_utci_for_unique(unique_key, lat, lon, timestamp_str):
    """Fetch UTCI for a unique date+location combination."""
    try:
        result = get_enhanced_utci_data(lat, lon, timestamp_str)
        return unique_key, result, None
    except Exception as e:
        return unique_key, None, str(e)


def process_chunk(chunk_df, chunk_num, total_chunks, logger, max_workers, killer):
    """Fetch UTCI for a chunk of unique date+location combinations."""
    fetch_tasks = [
        (row['unique_key'], row['lat_rounded'], row['lon_rounded'], row['representative_datetime'])
        for _, row in chunk_df.iterrows()
    ]

    results = {}
    errors = {}
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_key = {
            executor.submit(fetch_utci_for_unique, *task): task[0]
            for task in fetch_tasks
        }

        with tqdm(total=len(fetch_tasks),
                  desc=f"  Chunk {chunk_num}/{total_chunks}",
                  unit="unique") as pbar:
            for future in as_completed(future_to_key):
                if killer.kill_now:
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


def process_city(city_name, analyzed_path, output_path, checkpoint_interval,
                 max_workers, resume, logger, killer):
    """Add local datetime and UTCI to a single city's analyzed SVI CSV."""

    logger.info(f"\n{'='*60}")
    logger.info(f"Processing {city_name}")
    logger.info(f"{'='*60}")

    if output_path.exists() and not resume:
        logger.info(f"  Output already exists, skipping: {output_path}")
        return True

    # Load analyzed CSV (lat/lon come from analyzed CSV as instructed)
    df = pd.read_csv(analyzed_path)
    logger.info(f"  Loaded {len(df):,} rows from analyzed CSV")

    # Add local datetime using city timezone
    timezone_str = CITY_TIMEZONES[city_name]
    df = add_local_datetime(df, timezone_str)
    logger.info(f"  Added datetime-local (timezone: {timezone_str})")

    # Build unique date+hour+location keys for deduplication
    df['_captured_utc'] = pd.to_datetime(df['captured_at'], format='mixed')
    df['_date'] = df['_captured_utc'].dt.date
    df['_hour'] = df['_captured_utc'].dt.hour
    df['lat_rounded'] = df['lat'].round(2)
    df['lon_rounded'] = df['lon'].round(2)
    df['unique_key'] = (
        df['_date'].astype(str) + '_' +
        df['_hour'].astype(str) + '_' +
        df['lat_rounded'].astype(str) + '_' +
        df['lon_rounded'].astype(str)
    )

    unique_combos = df.groupby('unique_key').agg(
        lat_rounded=('lat_rounded', 'first'),
        lon_rounded=('lon_rounded', 'first'),
        representative_datetime=('_captured_utc', 'first'),
    ).reset_index()
    unique_combos['representative_datetime'] = unique_combos['representative_datetime'].astype(str)

    logger.info(f"  Total rows: {len(df):,}")
    logger.info(f"  Unique date+hour+location combos: {len(unique_combos):,} "
                f"({100*(1 - len(unique_combos)/len(df)):.1f}% reduction)")

    # Check for existing checkpoint
    unique_checkpoint = output_path.parent / (output_path.stem + '_unique_checkpoint.csv')
    fetched_results = {}

    if resume and unique_checkpoint.exists():
        checkpoint_df = pd.read_csv(unique_checkpoint)
        for _, row in checkpoint_df.iterrows():
            if pd.notna(row.get('utci_C')):
                fetched_results[row['unique_key']] = {
                    'utci_K': row['utci_K'],
                    'utci_C': row['utci_C'],
                    'utci_timestamp': row['utci_timestamp'],
                    'wind_speed_10m': row['wind_speed_10m'],
                    'temperature_2m': row['temperature_2m'],
                    'dewpoint_2m': row['dewpoint_2m'],
                }
        logger.info(f"  Resuming from checkpoint: {len(fetched_results):,} already fetched")
        already_fetched = set(fetched_results.keys())
        unique_combos = unique_combos[~unique_combos['unique_key'].isin(already_fetched)].reset_index(drop=True)
        logger.info(f"  {len(unique_combos):,} unique combos remaining")

    # Fetch UTCI in chunks
    total_unique = len(unique_combos)
    overall_start = time.time()
    chunk_start = 0

    while chunk_start < total_unique and not killer.kill_now:
        chunk_end = min(chunk_start + checkpoint_interval, total_unique)
        chunk = unique_combos.iloc[chunk_start:chunk_end]
        chunk_num = chunk_start // checkpoint_interval + 1
        total_chunks = (total_unique + checkpoint_interval - 1) // checkpoint_interval

        logger.info(f"  Chunk {chunk_num}/{total_chunks} "
                    f"({chunk_start:,}–{chunk_end:,} of {total_unique:,})")

        results, errors, rate = process_chunk(chunk, chunk_num, total_chunks,
                                              logger, max_workers, killer)
        fetched_results.update(results)

        valid = sum(1 for r in results.values() if r and r.get('utci_C') is not None)
        logger.info(f"  Fetched {len(results):,} ({valid:,} valid UTCI) at {rate:.1f}/sec")
        if errors:
            logger.info(f"  Errors: {len(errors):,}")

        # Save unique checkpoint
        checkpoint_rows = [{'unique_key': k, **v} for k, v in fetched_results.items()]
        pd.DataFrame(checkpoint_rows).to_csv(unique_checkpoint, index=False)

        # ETA
        elapsed = time.time() - overall_start
        remaining = total_unique - chunk_end
        avg_rate = chunk_end / elapsed if elapsed > 0 else 0
        if avg_rate > 0:
            eta = datetime.now() + timedelta(seconds=remaining / avg_rate)
            logger.info(f"  ETA: {eta.strftime('%Y-%m-%d %H:%M:%S')}")

        if killer.kill_now:
            break

        chunk_start = chunk_end
        if chunk_start < total_unique:
            logger.info(f"  Waiting {INTER_CHUNK_DELAY}s before next chunk...")
            time.sleep(INTER_CHUNK_DELAY)

    if killer.kill_now:
        logger.warning(f"  Interrupted — checkpoint saved to {unique_checkpoint}")
        return False

    # Join results back
    logger.info("  Joining UTCI results back to rows...")
    result_cols = ['utci_K', 'utci_C', 'utci_timestamp', 'wind_speed_10m',
                   'temperature_2m', 'dewpoint_2m']

    joined = {col: [] for col in result_cols}
    for _, row in tqdm(df.iterrows(), total=len(df), desc="  Joining"):
        result = fetched_results.get(row['unique_key'])
        for col in result_cols:
            joined[col].append(result.get(col) if result else None)

    for col in result_cols:
        df[col] = joined[col]

    # Drop temporary working columns
    df.drop(columns=['_captured_utc', '_date', '_hour', 'lat_rounded',
                     'lon_rounded', 'unique_key'], inplace=True)

    df.to_csv(output_path, index=False)
    logger.info(f"  Saved {len(df):,} rows to {output_path}")

    valid_utci = df['utci_C'].notna().sum()
    logger.info(f"  Valid UTCI: {valid_utci:,} ({100*valid_utci/len(df):.1f}%)")

    if unique_checkpoint.exists():
        unique_checkpoint.unlink()

    return True


def main():
    parser = argparse.ArgumentParser(
        description='Add UTCI to metro commute SVI analyzed CSVs'
    )
    parser.add_argument('--analyzed-dir', type=str,
                        default='data/metro_commute_svi',
                        help='Root dir containing per-city analyzed CSVs')
    parser.add_argument('--output-dir', type=str,
                        default='data/metro_commute_svi_with_utci',
                        help='Root dir for output CSVs with UTCI')
    parser.add_argument('--cities', nargs='+', default=None,
                        help='Specific cities to process (default: all)')
    parser.add_argument('--workers', type=int, default=MAX_WORKERS)
    parser.add_argument('--checkpoint-interval', type=int, default=CHECKPOINT_INTERVAL)
    parser.add_argument('--resume', action='store_true',
                        help='Resume from checkpoint if available')
    args = parser.parse_args()

    project_root = Path(__file__).parent.parent.parent
    analyzed_dir = project_root / args.analyzed_dir
    output_dir = project_root / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = project_root / 'logs' / f'utci_metro_svi_{timestamp}.log'
    logger = setup_logging(log_file)
    killer = GracefulKiller()

    cities = args.cities if args.cities else list(CITY_TIMEZONES.keys())

    logger.info("="*60)
    logger.info("METRO SVI UTCI ANNOTATION")
    logger.info(f"Cities: {', '.join(cities)}")
    logger.info(f"Workers: {args.workers}")
    logger.info(f"Log: {log_file}")
    logger.info("="*60)

    overall_start = time.time()
    success_count = 0

    for city in cities:
        if killer.kill_now:
            break

        analyzed_path = analyzed_dir / city / f'{city}_svi_analyzed.csv'
        if not analyzed_path.exists():
            logger.warning(f"Skipping {city}: analyzed CSV not found at {analyzed_path}")
            continue

        city_output_dir = output_dir / city
        city_output_dir.mkdir(parents=True, exist_ok=True)
        output_path = city_output_dir / f'{city}_svi_with_utci.csv'

        ok = process_city(
            city_name=city,
            analyzed_path=analyzed_path,
            output_path=output_path,
            checkpoint_interval=args.checkpoint_interval,
            max_workers=args.workers,
            resume=args.resume,
            logger=logger,
            killer=killer,
        )
        if ok:
            success_count += 1

    elapsed = time.time() - overall_start
    logger.info("\n" + "="*60)
    logger.info(f"Done. {success_count}/{len(cities)} cities processed in {elapsed/3600:.1f}h")
    logger.info(f"Output: {output_dir}")
    logger.info("="*60)


if __name__ == '__main__':
    main()
