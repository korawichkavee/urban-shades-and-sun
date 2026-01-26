# ABOUTME: Adds UTCI weather data to Phoenix_1840020568_analyzed.csv using multithreaded processing.
# ABOUTME: Uses the enhanced UTCI API with prior/next day data and rain information.

from enhanced_utci import get_enhanced_utci_data
import pandas as pd
from pathlib import Path
from tqdm import tqdm
import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

MAX_WORKERS = 10  # Number of parallel API requests


def setup_logging():
    """Set up logging to both file and console."""
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"phoenix_utci_{timestamp}.log"

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


def main():
    log_file = setup_logging()
    overall_start = time.time()

    logging.info("="*60)
    logging.info("Adding UTCI data to Phoenix_1840020568_analyzed.csv")
    logging.info(f"Max workers: {MAX_WORKERS}")
    logging.info(f"Log file: {log_file}")
    logging.info("="*60)

    input_path = Path("Phoenix_1840020568_analyzed.csv")
    output_path = Path("Phoenix_1840020568_with_utci.csv")

    if not input_path.exists():
        logging.error(f"Input file not found: {input_path}")
        return

    # Load CSV
    logging.info(f"Loading {input_path}...")
    df = pd.read_csv(input_path)
    logging.info(f"  Loaded {len(df)} rows")

    # Check if UTCI columns already exist
    if 'utci_C' in df.columns:
        logging.info("  UTCI data already present - skipping")
        return

    # Check for required columns
    if 'datetime_local' not in df.columns:
        logging.error("  Missing datetime_local column")
        return

    # Parse datetime
    df["datetime_local"] = pd.to_datetime(df["datetime_local"], format="ISO8601", errors="coerce")

    # Prepare data for multithreaded processing
    row_data_list = []
    for idx, row in df.iterrows():
        timestamp = row["datetime_local"].isoformat()
        row_data_list.append((idx, row["lat"], row["lon"], timestamp))

    # Initialize result storage
    results = {idx: None for idx in range(len(df))}
    errors = {}

    # Process with multithreading and progress tracking
    start_time = time.time()
    completed = 0

    logging.info(f"Starting multithreaded processing with {MAX_WORKERS} workers")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks
        future_to_idx = {executor.submit(fetch_utci_for_row, row_data): row_data[0]
                        for row_data in row_data_list}

        # Process completed tasks with progress bar
        with tqdm(total=len(row_data_list), desc="Processing", unit="row") as pbar:
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
    logging.info(f"Completed {completed} rows in {elapsed:.1f}s ({completed/elapsed:.1f} rows/sec)")

    if errors:
        logging.warning(f"Encountered {len(errors)} errors during processing")
        for idx, error in list(errors.items())[:5]:  # Log first 5 errors
            logging.debug(f"  Row {idx}: {error}")

    # Convert results to columns
    result_cols = {
        'utci_K': [],
        'utci_C': [],
        'utci_timestamp': [],
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
    logging.info(f"Saving to {output_path}...")
    df.to_csv(output_path, index=False)
    logging.info(f"Saved successfully!")

    total_elapsed = time.time() - overall_start
    logging.info("="*60)
    logging.info(f"Processing complete!")
    logging.info(f"  Total time: {total_elapsed/60:.2f} minutes")
    logging.info(f"  Output file: {output_path}")
    logging.info("="*60)


if __name__ == "__main__":
    main()
