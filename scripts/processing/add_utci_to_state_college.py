# ABOUTME: Adds UTCI weather data to the state-college SVI analyzed CSV.
# ABOUTME: Fetches ERA5 UTCI via Open-Meteo API using unique date+hour+location deduplication.

import sys
import logging
import signal
import time
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import pytz
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent / 'utils'))
from enhanced_utci import get_enhanced_utci_data


TIMEZONE = 'America/New_York'
MAX_WORKERS = 20
CHECKPOINT_INTERVAL = 1000
INTER_CHUNK_DELAY = 5

INPUT_PATH = Path(__file__).parent.parent.parent / 'data' / 'state-college' / 'state-college_svi_analyzed.csv'
OUTPUT_PATH = Path(__file__).parent.parent.parent / 'data' / 'state-college' / 'state-college_svi_with_utci.csv'


class GracefulKiller:
    """Handle interrupt signals gracefully."""
    kill_now = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, *args):
        self.kill_now = True
        print('\nReceived interrupt. Finishing current batch and saving checkpoint...')


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
    """Convert UTC captured_at to local datetime string."""
    tz = pytz.timezone(timezone_str)
    captured = pd.to_datetime(df['captured_at'], format='mixed')
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
                  desc=f'  Chunk {chunk_num}/{total_chunks}',
                  unit='unique') as pbar:
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


def main():
    project_root = Path(__file__).parent.parent.parent
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = project_root / 'logs' / f'utci_state_college_{timestamp}.log'
    logger = setup_logging(log_file)
    killer = GracefulKiller()

    logger.info('=' * 60)
    logger.info('STATE COLLEGE UTCI ANNOTATION')
    logger.info(f'Input:  {INPUT_PATH}')
    logger.info(f'Output: {OUTPUT_PATH}')
    logger.info(f'Log:    {log_file}')
    logger.info('=' * 60)

    if OUTPUT_PATH.exists():
        logger.info('Output already exists. Delete it to re-run.')
        return

    df = pd.read_csv(INPUT_PATH, low_memory=False)
    logger.info(f'Loaded {len(df):,} rows')

    df = add_local_datetime(df, TIMEZONE)
    logger.info(f'Added datetime-local (timezone: {TIMEZONE})')

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

    total_unique = len(unique_combos)
    logger.info(f'Total rows: {len(df):,}')
    logger.info(f'Unique date+hour+location combos: {total_unique:,} '
                f'({100*(1 - total_unique/len(df)):.1f}% reduction)')

    checkpoint_path = OUTPUT_PATH.parent / (OUTPUT_PATH.stem + '_unique_checkpoint.csv')
    fetched_results = {}

    if checkpoint_path.exists():
        checkpoint_df = pd.read_csv(checkpoint_path)
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
        logger.info(f'Resuming from checkpoint: {len(fetched_results):,} already fetched')
        already_fetched = set(fetched_results.keys())
        unique_combos = unique_combos[~unique_combos['unique_key'].isin(already_fetched)].reset_index(drop=True)
        logger.info(f'{len(unique_combos):,} unique combos remaining')

    chunk_start = 0
    overall_start = time.time()

    while chunk_start < len(unique_combos) and not killer.kill_now:
        chunk_end = min(chunk_start + CHECKPOINT_INTERVAL, len(unique_combos))
        chunk = unique_combos.iloc[chunk_start:chunk_end]
        chunk_num = chunk_start // CHECKPOINT_INTERVAL + 1
        total_chunks = (len(unique_combos) + CHECKPOINT_INTERVAL - 1) // CHECKPOINT_INTERVAL

        logger.info(f'Chunk {chunk_num}/{total_chunks} '
                    f'({chunk_start:,}–{chunk_end:,} of {len(unique_combos):,})')

        results, errors, rate = process_chunk(chunk, chunk_num, total_chunks,
                                              logger, MAX_WORKERS, killer)
        fetched_results.update(results)

        valid = sum(1 for r in results.values() if r and r.get('utci_C') is not None)
        logger.info(f'Fetched {len(results):,} ({valid:,} valid UTCI) at {rate:.1f}/sec')
        if errors:
            logger.info(f'Errors: {len(errors):,}')

        checkpoint_rows = [{'unique_key': k, **v} for k, v in fetched_results.items()]
        pd.DataFrame(checkpoint_rows).to_csv(checkpoint_path, index=False)

        elapsed = time.time() - overall_start
        remaining = len(unique_combos) - chunk_end
        avg_rate = chunk_end / elapsed if elapsed > 0 else 0
        if avg_rate > 0:
            eta = datetime.now() + timedelta(seconds=remaining / avg_rate)
            logger.info(f'ETA: {eta.strftime("%Y-%m-%d %H:%M:%S")}')

        if killer.kill_now:
            break

        chunk_start = chunk_end
        if chunk_start < len(unique_combos):
            logger.info(f'Waiting {INTER_CHUNK_DELAY}s before next chunk...')
            time.sleep(INTER_CHUNK_DELAY)

    if killer.kill_now:
        logger.warning(f'Interrupted — checkpoint saved to {checkpoint_path}')
        return

    logger.info('Joining UTCI results back to rows...')
    result_cols = ['utci_K', 'utci_C', 'utci_timestamp', 'wind_speed_10m',
                   'temperature_2m', 'dewpoint_2m']

    joined = {col: [] for col in result_cols}
    for _, row in tqdm(df.iterrows(), total=len(df), desc='Joining'):
        result = fetched_results.get(row['unique_key'])
        for col in result_cols:
            joined[col].append(result.get(col) if result else None)

    for col in result_cols:
        df[col] = joined[col]

    df.drop(columns=['_captured_utc', '_date', '_hour', 'lat_rounded',
                     'lon_rounded', 'unique_key'], inplace=True)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    logger.info(f'Saved {len(df):,} rows to {OUTPUT_PATH}')

    valid_utci = df['utci_C'].notna().sum()
    logger.info(f'Valid UTCI: {valid_utci:,} ({100*valid_utci/len(df):.1f}%)')

    if checkpoint_path.exists():
        checkpoint_path.unlink()

    logger.info('=' * 60)
    logger.info('Done.')
    logger.info('=' * 60)


if __name__ == '__main__':
    main()
