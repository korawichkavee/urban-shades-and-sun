# ABOUTME: Test version of enhanced UTCI batch processor with limited rows.
# ABOUTME: Validates enhanced data collection before full overnight batch processing.

from enhanced_utci import get_enhanced_utci_data
import pandas as pd
from pathlib import Path
from tqdm import tqdm
import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

TEST_ROWS = 10  # Number of rows to test per city
TEST_CITIES = 3  # Number of cities to test
MAX_WORKERS = 5  # Number of parallel API requests for testing

def setup_logging():
    """Set up logging to both file and console."""
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"utci_test_{timestamp}.log"

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


def process_city_csv(input_path, output_path, max_rows=None):
    """Process a single CSV file to add enhanced UTCI values with multithreading."""
    logging.info(f"Processing {input_path.name}...")

    # Load CSV
    try:
        df = pd.read_csv(input_path)
        logging.debug(f"  Loaded {len(df)} rows")

        if max_rows:
            df = df.head(max_rows)
            logging.info(f"  Testing with first {len(df)} rows")
    except Exception as e:
        logging.error(f"  Failed to load CSV: {e}")
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
    results_dict = {idx: None for idx in range(len(df))}
    errors = {}

    # Process with multithreading
    start_time = time.time()

    logging.info(f"  Starting multithreaded processing with {MAX_WORKERS} workers")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_idx = {executor.submit(fetch_utci_for_row, row_data): row_data[0]
                        for row_data in row_data_list}

        with tqdm(total=len(row_data_list), desc=f"  {input_path.stem}", unit="row") as pbar:
            for future in as_completed(future_to_idx):
                idx, result, error = future.result()

                if error:
                    errors[idx] = error
                else:
                    results_dict[idx] = result

                    # Log first result as example
                    if idx == 0 and result:
                        logging.debug(f"  First row result: UTCI={result['utci_C']:.2f}°C, "
                                    f"Prior day avg={result['prior_day_utci_avg_C']:.2f}°C, "
                                    f"Next day avg={result['next_day_utci_avg_C']:.2f}°C, "
                                    f"Prior rain={result['prior_day_rain']}, "
                                    f"Next rain={result['next_day_rain']}")

                pbar.update(1)

    elapsed = time.time() - start_time
    rate = len(row_data_list) / elapsed if elapsed > 0 else 0
    logging.info(f"  Processed {len(row_data_list)} rows in {elapsed:.1f}s ({rate:.1f} rows/sec)")

    if errors:
        logging.warning(f"  Encountered {len(errors)} errors during processing")

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
        result = results_dict.get(idx)
        if result:
            for key in result_cols.keys():
                result_cols[key].append(result[key])
        else:
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
    logging.info("="*60)
    logging.info("Starting enhanced UTCI TEST processing")
    logging.info(f"Log file: {log_file}")
    logging.info(f"Testing {TEST_ROWS} rows from {TEST_CITIES} cities")
    logging.info("="*60)

    data_dir = Path("city_estimate_outcomes")

    # Find all CSV files
    csv_files = sorted(data_dir.glob("*.csv"))
    csv_files = [f for f in csv_files if "_with_utci" not in f.name]

    logging.info(f"Found {len(csv_files)} CSV files")

    processed_count = 0

    for csv_file in csv_files[:TEST_CITIES]:
        output_path = csv_file.parent / f"test_{csv_file.name.replace('.csv', '_with_utci.csv')}"

        if process_city_csv(csv_file, output_path, max_rows=TEST_ROWS):
            processed_count += 1

    logging.info("="*60)
    logging.info(f"Test complete! Processed {processed_count} files.")
    logging.info(f"Check test_*_with_utci.csv files in {data_dir}")
    logging.info("="*60)


if __name__ == "__main__":
    main()
