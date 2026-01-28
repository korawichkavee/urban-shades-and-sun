# ABOUTME: Bulk-batched UTCI annotation using multi-location API calls.
# ABOUTME: Fetches up to 50 locations per API call, reducing total calls by ~50x.

import sys
from pathlib import Path

# Add utils and config to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'utils'))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'config'))

import pandas as pd
import argparse
import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import time
import signal
import requests
import math
import numpy as np
import thermofeel
from api_config import load_api_config


MAX_WORKERS = 1  # Single worker to control rate limiting precisely
BATCH_SIZE = 100  # Locations per API call (tested up to 100 successfully)
CHECKPOINT_INTERVAL = 50  # Save every N batches
INTER_BATCH_DELAY = 10  # Seconds between batches (600 calls/min = 10 calls/sec max, so 100 locs = 10sec delay)


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


def _round_coord_for_cache(lat, lon, decimals=2):
    """Round coordinates to reduce API calls."""
    return round(lat, decimals), round(lon, decimals)


def _calculate_utci_from_met(Ta_C, Td_C, Va):
    """Calculate UTCI from meteorological variables."""
    if Ta_C is None or Td_C is None or Va is None:
        return math.nan, math.nan
    if math.isnan(Ta_C) or math.isnan(Td_C) or math.isnan(Va):
        return math.nan, math.nan

    Ta_K = np.array([Ta_C + 273.15])
    Td_K = np.array([Td_C + 273.15])
    Va_a = np.array([Va])
    Tr_K = Ta_K.copy()

    rh_pc = thermofeel.calculate_relative_humidity_percent(Ta_K, Td_K)
    es_hPa = thermofeel.calculate_saturation_vapour_pressure(Ta_K)
    ehPa = es_hPa * rh_pc / 100.0

    utci_K = thermofeel.calculate_utci(Ta_K, Va_a, Tr_K, ehPa=ehPa)
    utci_C = utci_K - 273.15

    return utci_K.item(), utci_C.item()


def _calculate_daily_average_utci(hourly_data, date_str):
    """Calculate average UTCI for a specific day from hourly data."""
    time_strings = hourly_data.get("time", [])
    temps = hourly_data.get("temperature_2m", [])
    dews = hourly_data.get("dewpoint_2m", [])
    winds = hourly_data.get("wind_speed_10m") or hourly_data.get("windspeed_10m")

    if not time_strings or not temps or not dews or winds is None:
        return math.nan

    utci_values = []
    for i, time_str in enumerate(time_strings):
        if time_str.startswith(date_str):
            Ta_C = temps[i]
            Td_C = dews[i]
            Va = winds[i]
            _, utci_C = _calculate_utci_from_met(Ta_C, Td_C, Va)
            if not math.isnan(utci_C):
                utci_values.append(utci_C)

    if utci_values:
        return np.mean(utci_values)
    return math.nan


def _check_daily_rain(hourly_data, date_str, threshold_mm=1.0):
    """Check if a specific day had rain."""
    time_strings = hourly_data.get("time", [])
    precip = hourly_data.get("precipitation", [])

    if not time_strings or not precip:
        return None

    daily_precip = 0.0
    for i, time_str in enumerate(time_strings):
        if time_str.startswith(date_str):
            if precip[i] is not None and not math.isnan(precip[i]):
                daily_precip += precip[i]

    return daily_precip > threshold_mm


def fetch_bulk_era5(batch_locations, start_date_str, end_date_str, max_retries=3):
    """
    Fetch ERA5 data for multiple locations in a single API call.

    batch_locations: list of (lat, lon) tuples
    Returns: list of hourly dicts (one per location) or None on error
    """
    if not batch_locations:
        return None

    lats = [lat for lat, lon in batch_locations]
    lons = [lon for lat, lon in batch_locations]

    lat_str = ",".join(str(lat) for lat in lats)
    lon_str = ",".join(str(lon) for lon in lons)

    # Get API config
    config = load_api_config()
    api_key = config['api_key']

    # Use customer archive API endpoint
    url = (
        "https://customer-archive-api.open-meteo.com/v1/era5"
        f"?latitude={lat_str}"
        f"&longitude={lon_str}"
        f"&start_date={start_date_str}"
        f"&end_date={end_date_str}"
        "&hourly=temperature_2m,dewpoint_2m,wind_speed_10m,precipitation"
        "&timezone=UTC"
        f"&apikey={api_key}"
    )

    for attempt in range(max_retries):
        try:
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            data = resp.json()

            if "error" in data:
                print(f"[ERROR] Open-Meteo API error: {data.get('reason')}")
                return None

            # Multi-location returns array of location objects
            if isinstance(data, list):
                return [loc.get("hourly") for loc in data]
            else:
                # Single location (shouldn't happen with multiple coords)
                return [data.get("hourly")]

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:  # Rate limit
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + (attempt * 0.5)
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"[ERROR] ERA5 rate limit exceeded after {max_retries} retries")
                    return None
            else:
                print(f"[ERROR] ERA5 HTTP error: {e}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] ERA5 request failed: {e}")
            return None

    return None


def process_date_batch(date_batch_df, logger, batch_size, inter_batch_delay):
    """
    Process a batch of unique locations for a single date.
    Groups locations into batches of batch_size and fetches in bulk.
    Respects rate limits with delays between batches.
    """
    date = date_batch_df['date'].iloc[0]
    prior_date = date - timedelta(days=1)
    next_date = date + timedelta(days=1)

    # Convert to date-only strings (YYYY-MM-DD)
    start_date_str = prior_date.strftime('%Y-%m-%d')
    end_date_str = next_date.strftime('%Y-%m-%d')

    # Split into batches of batch_size
    results = {}
    total_locs = len(date_batch_df)
    num_batches = (total_locs + batch_size - 1) // batch_size

    for batch_num, batch_start in enumerate(range(0, total_locs, batch_size)):
        batch_end = min(batch_start + batch_size, total_locs)
        batch_df = date_batch_df.iloc[batch_start:batch_end]

        # Prepare batch locations
        batch_locations = [(row['lat_rounded'], row['lon_rounded'])
                          for _, row in batch_df.iterrows()]

        # Fetch bulk data
        logger.debug(f"  Fetching batch {batch_num+1}/{num_batches} ({len(batch_locations)} locations)")
        hourly_list = fetch_bulk_era5(batch_locations, start_date_str, end_date_str)

        if hourly_list is None:
            logger.error(f"Failed to fetch batch for date {date}")
            continue

        if len(hourly_list) != len(batch_df):
            logger.error(f"Mismatch: expected {len(batch_df)} locations, got {len(hourly_list)}")
            continue

        # Process each location in the batch
        for idx, (_, row) in enumerate(batch_df.iterrows()):
            unique_key = row['unique_key']
            target_datetime = row['representative_datetime']
            hourly = hourly_list[idx]

            result = {
                'utci_K': math.nan,
                'utci_C': math.nan,
                'utci_timestamp': None,
                'wind_speed_10m': math.nan,
                'temperature_2m': math.nan,
                'dewpoint_2m': math.nan,
                'prior_day_utci_avg_C': math.nan,
                'next_day_utci_avg_C': math.nan,
                'prior_day_rain': None,
                'next_day_rain': None,
            }

            if hourly is None or 'time' not in hourly:
                results[unique_key] = result
                continue

            # Find nearest hour for current UTCI
            time_strings = hourly.get("time", [])
            if not time_strings:
                results[unique_key] = result
                continue

            times = [datetime.fromisoformat(t) for t in time_strings]
            target_utc = pd.to_datetime(target_datetime).tz_localize(None)
            idx_nearest = min(range(len(times)), key=lambda i: abs(times[i] - target_utc))
            matched_time = times[idx_nearest].isoformat()
            result['utci_timestamp'] = matched_time

            # Calculate current UTCI
            temps = hourly.get("temperature_2m", [])
            dews = hourly.get("dewpoint_2m", [])
            winds = hourly.get("wind_speed_10m") or hourly.get("windspeed_10m")

            if temps and dews and winds:
                Ta_C = temps[idx_nearest]
                Td_C = dews[idx_nearest]
                Va = winds[idx_nearest]

                utci_K, utci_C = _calculate_utci_from_met(Ta_C, Td_C, Va)
                result['utci_K'] = utci_K
                result['utci_C'] = utci_C
                result['wind_speed_10m'] = Va
                result['temperature_2m'] = Ta_C
                result['dewpoint_2m'] = Td_C

            # Daily averages and rain
            result['prior_day_utci_avg_C'] = _calculate_daily_average_utci(hourly, prior_date.strftime('%Y-%m-%d'))
            result['next_day_utci_avg_C'] = _calculate_daily_average_utci(hourly, next_date.strftime('%Y-%m-%d'))
            result['prior_day_rain'] = _check_daily_rain(hourly, prior_date.strftime('%Y-%m-%d'))
            result['next_day_rain'] = _check_daily_rain(hourly, next_date.strftime('%Y-%m-%d'))

            results[unique_key] = result

        # Rate limiting: wait between batches (except after last batch)
        if batch_num < num_batches - 1:
            logger.debug(f"  Waiting {inter_batch_delay}s before next batch (rate limiting)...")
            time.sleep(inter_batch_delay)

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Add UTCI data with bulk batching (50 locations per API call)'
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
        '--batch-size',
        type=int,
        default=BATCH_SIZE,
        help=f'Locations per API call (default: {BATCH_SIZE})'
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

    unique_checkpoint = output_path.parent / (output_path.stem + '_bulk_checkpoint.csv')

    # Setup logging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = project_root / "logs" / f"utci_bulk_{timestamp}.log"
    logger = setup_logging(log_file)

    # Setup graceful shutdown
    killer = GracefulKiller()

    logger.info("="*70)
    logger.info("BULK-BATCHED UTCI ANNOTATION (WITH RATE LIMITING)")
    logger.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Log file: {log_file}")
    logger.info(f"Batch size: {args.batch_size} locations per API call")
    logger.info(f"Inter-batch delay: {INTER_BATCH_DELAY}s (respects 600 calls/min limit)")
    logger.info(f"Note: Each location in batch counts as 1 API call")
    logger.info("="*70)

    # Load data
    logger.info(f"\nLoading data from {input_path}")
    trips_df = pd.read_csv(input_path, low_memory=False)
    trips_df['datetime'] = pd.to_datetime(trips_df['datetime'])
    logger.info(f"  Loaded {len(trips_df):,} trips")

    # Create unique combinations
    logger.info("\nIdentifying unique date+location combinations...")
    trips_df['date'] = pd.to_datetime(trips_df['datetime'].dt.date)
    trips_df['lat_rounded'] = trips_df['lat'].round(2)
    trips_df['lon_rounded'] = trips_df['lon'].round(2)
    trips_df['unique_key'] = (
        trips_df['date'].astype(str) + '_' +
        trips_df['lat_rounded'].astype(str) + '_' +
        trips_df['lon_rounded'].astype(str)
    )

    # Get unique combinations
    unique_combos = trips_df.groupby('unique_key').agg({
        'lat_rounded': 'first',
        'lon_rounded': 'first',
        'date': 'first',
        'datetime': 'first'
    }).reset_index()
    unique_combos.rename(columns={'datetime': 'representative_datetime'}, inplace=True)

    total_api_calls = len(unique_combos) / args.batch_size

    logger.info(f"  Total trips: {len(trips_df):,}")
    logger.info(f"  Unique date+location combos: {len(unique_combos):,}")
    logger.info(f"  Estimated API calls: ~{total_api_calls:.0f} (at {args.batch_size} locations/call)")
    logger.info(f"  Reduction from naive: {100*(1 - total_api_calls/len(trips_df)):.1f}%")

    # Check for checkpoint
    fetched_results = {}
    if args.resume and unique_checkpoint.exists():
        logger.info(f"\nResuming from checkpoint: {unique_checkpoint}")
        checkpoint_df = pd.read_csv(unique_checkpoint)

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

        logger.info(f"  Loaded {len(fetched_results):,} already-fetched combinations")
        unique_combos = unique_combos[~unique_combos['unique_key'].isin(fetched_results.keys())].reset_index(drop=True)

    # Group by date for efficient batching
    logger.info(f"\nGrouping {len(unique_combos):,} combinations by date...")
    date_groups = unique_combos.groupby('date')
    logger.info(f"  Found {len(date_groups)} unique dates")

    # Process by date
    overall_start = time.time()
    processed_dates = 0

    logger.info("\nProcessing dates...")
    with tqdm(total=len(date_groups), desc="Dates", unit="date") as pbar:
        for date, date_df in date_groups:
            if killer.kill_now:
                logger.warning("Interrupt detected, stopping...")
                break

            # Process this date's locations in batches
            date_results = process_date_batch(date_df, logger, args.batch_size, INTER_BATCH_DELAY)
            fetched_results.update(date_results)

            processed_dates += 1
            pbar.update(1)

            # Periodic checkpoint save
            if processed_dates % 50 == 0:
                checkpoint_data = []
                for key, result in fetched_results.items():
                    row_data = {'unique_key': key}
                    row_data.update(result)
                    checkpoint_data.append(row_data)

                checkpoint_df = pd.DataFrame(checkpoint_data)
                checkpoint_df.to_csv(unique_checkpoint, index=False)
                logger.info(f"  Checkpoint saved: {len(fetched_results):,} combinations")

    # Final checkpoint save
    if not killer.kill_now:
        checkpoint_data = []
        for key, result in fetched_results.items():
            row_data = {'unique_key': key}
            row_data.update(result)
            checkpoint_data.append(row_data)

        checkpoint_df = pd.DataFrame(checkpoint_data)
        checkpoint_df.to_csv(unique_checkpoint, index=False)

    # Join results back
    if not killer.kill_now:
        logger.info("\nJoining results back to original trips...")

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

        for _, row in tqdm(trips_df.iterrows(), total=len(trips_df), desc="  Joining"):
            key = row['unique_key']
            result = fetched_results.get(key)

            if result:
                for col in result_cols.keys():
                    result_cols[col].append(result.get(col))
            else:
                for col in result_cols.keys():
                    result_cols[col].append(None)

        for col, values in result_cols.items():
            trips_df[col] = values

        trips_df.drop(columns=['date', 'lat_rounded', 'lon_rounded', 'unique_key'], inplace=True)

        logger.info(f"\nSaving final output to {output_path}")
        trips_df.to_csv(output_path, index=False)

        if unique_checkpoint.exists():
            unique_checkpoint.unlink()
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
    logger.info(f"Total time: {total_elapsed/60:.1f} minutes")
    logger.info(f"Unique combinations fetched: {len(fetched_results):,}")

    if not killer.kill_now:
        valid_utci = trips_df['utci_C'].notna().sum()
        logger.info(f"Total trips annotated: {len(trips_df):,}")
        logger.info(f"Valid UTCI: {valid_utci:,} ({100*valid_utci/len(trips_df):.1f}%)")
        logger.info(f"Output: {output_path}")
    logger.info("="*70)


if __name__ == '__main__':
    main()
