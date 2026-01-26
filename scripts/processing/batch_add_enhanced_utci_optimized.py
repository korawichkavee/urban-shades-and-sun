# ABOUTME: Optimized batch processor with multithreading and ETA calculation.
# ABOUTME: Uses concurrent API calls and progress tracking for faster UTCI data collection.

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'utils'))
from enhanced_utci import get_enhanced_utci_data
import pandas as pd
from pathlib import Path
from tqdm import tqdm
import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

MAX_WORKERS = 20  # Number of parallel API requests


def setup_logging():
    """Set up logging to both file and console."""
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"utci_batch_{timestamp}.log"

    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')

    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return log_file


def fetch_utci_for_row(row_data):
    """Fetch UTCI data for a single row (used in multithreading)."""
    idx, lat, lon, timestamp = row_data
    try:
        result = get_enhanced_utci_data(lat, lon, timestamp)
        return idx, result, None
    except Exception as e:
        return idx, None, str(e)


def process_city_csv(input_path, output_path):
    """Process a single CSV file to add enhanced UTCI values with multithreading."""
    logging.info(f"Processing {input_path.name}...")

    # Load CSV
    try:
        df = pd.read_csv(input_path)
        logging.debug(f"  Loaded {len(df)} rows")
    except Exception as e:
        logging.error(f"  Failed to load CSV: {e}")
        return False

    # Check if UTCI columns already exist
    if 'utci_C' in df.columns:
        logging.info(f"  Skipping - UTCI data already present")
        return False

    # Check for required columns
    if 'datetime-local' not in df.columns:
        logging.warning(f"  Skipping - missing datetime-local column")
        return False

    # Parse datetime
    df["datetime-local"] = pd.to_datetime(df["datetime-local"], format="ISO8601", errors="coerce")

    # Prepare data for multithreaded processing
    row_data_list = []
    for idx, row in df.iterrows():
        timestamp = row["datetime-local"].isoformat()
        row_data_list.append((idx, row["lat"], row["lon"], timestamp))

    # Initialize result storage
    results = {idx: None for idx in range(len(df))}
    errors = {}

    # Process with multithreading and progress tracking
    start_time = time.time()
    completed = 0

    logging.info(f"  Starting multithreaded processing with {MAX_WORKERS} workers")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks
        future_to_idx = {executor.submit(fetch_utci_for_row, row_data): row_data[0]
                        for row_data in row_data_list}

        # Process completed tasks with progress bar
        with tqdm(total=len(row_data_list), desc=f"  {input_path.stem}", unit="row") as pbar:
            for future in as_completed(future_to_idx):
                idx, result, error = future.result()

                if error:
                    errors[idx] = error
                else:
                    results[idx] = result

                completed += 1
                pbar.update(1)

                # Calculate and log ETA every 100 rows
                if completed % 100 == 0:
                    elapsed = time.time() - start_time
                    rate = completed / elapsed
                    remaining = len(row_data_list) - completed
                    eta_seconds = remaining / rate if rate > 0 else 0
                    eta_time = datetime.now() + timedelta(seconds=eta_seconds)

                    logging.debug(f"  Progress: {completed}/{len(row_data_list)} "
                                f"({rate:.1f} rows/sec, ETA: {eta_time.strftime('%H:%M:%S')})")

    # Log final timing
    elapsed = time.time() - start_time
    logging.info(f"  Completed {completed} rows in {elapsed:.1f}s ({completed/elapsed:.1f} rows/sec)")

    if errors:
        logging.warning(f"  Encountered {len(errors)} errors during processing")
        for idx, error in list(errors.items())[:5]:  # Log first 5 errors
            logging.debug(f"    Row {idx}: {error}")

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

    for idx in range(len(df)):
        result = results.get(idx)
        if result:
            for key in result_cols.keys():
                result_cols[key].append(result[key])
        else:
            # Append None for failed rows
            for key in result_cols.keys():
                result_cols[key].append(None)

    # Assign results to dataframe
    for key, values in result_cols.items():
        df[key] = values

    # Save updated dataframe
    try:
        df.to_csv(output_path, index=False)
        logging.info(f"  Saved to {output_path.name}")
        return True
    except Exception as e:
        logging.error(f"  Failed to save output: {e}")
        return False


def main():
    log_file = setup_logging()
    overall_start = time.time()

    logging.info("="*60)
    logging.info("Starting OPTIMIZED enhanced UTCI batch processing")
    logging.info(f"Max workers: {MAX_WORKERS}")
    logging.info(f"Log file: {log_file}")
    logging.info("="*60)

    data_dir = Path("city_estimate_outcomes")

    # Find all CSV files
    csv_files = sorted(data_dir.glob("*.csv"))
    csv_files = [f for f in csv_files if "_with_utci" not in f.name]

    # Calculate total rows for ETA
    total_rows = 0
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            if csv_file.with_name(csv_file.name.replace(".csv", "_with_utci.csv")).exists():
                continue
            if 'utci_C' not in df.columns:
                total_rows += len(df)
        except:
            pass

    logging.info(f"Found {len(csv_files)} CSV files")
    logging.info(f"Estimated total rows to process: {total_rows:,}")

    processed_count = 0
    skipped_count = 0
    processed_rows = 0

    for file_idx, csv_file in enumerate(csv_files, 1):
        output_path = csv_file.parent / csv_file.name.replace(".csv", "_with_utci.csv")

        if output_path.exists():
            logging.info(f"[{file_idx}/{len(csv_files)}] Skipping {csv_file.name} - output exists")
            skipped_count += 1
            continue

        logging.info(f"[{file_idx}/{len(csv_files)}] Processing {csv_file.name}")

        if process_city_csv(csv_file, output_path):
            processed_count += 1
            # Update ETA for remaining files
            elapsed = time.time() - overall_start
            avg_time_per_file = elapsed / processed_count if processed_count > 0 else 0
            remaining_files = len(csv_files) - file_idx
            eta_seconds = avg_time_per_file * remaining_files
            eta_time = datetime.now() + timedelta(seconds=eta_seconds)

            logging.info(f"  Overall ETA for all files: {eta_time.strftime('%Y-%m-%d %H:%M:%S')}")

    total_elapsed = time.time() - overall_start
    logging.info("="*60)
    logging.info(f"Processing complete!")
    logging.info(f"  Total time: {total_elapsed/3600:.2f} hours")
    logging.info(f"  Processed: {processed_count} files")
    logging.info(f"  Skipped: {skipped_count} files")
    logging.info("="*60)


if __name__ == "__main__":
    main()
