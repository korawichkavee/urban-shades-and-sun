# ABOUTME: Batch processes CSV files to add enhanced UTCI data with multi-day context.
# ABOUTME: Includes current UTCI, prior/next day averages, rain data, and logging to logs folder.

from enhanced_utci import get_enhanced_utci_data
import pandas as pd
from pathlib import Path
from tqdm import tqdm
import logging
from datetime import datetime

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


def process_city_csv(input_path, output_path):
    """Process a single CSV file to add enhanced UTCI values."""
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

    # Prepare result lists
    results = {
        'utci_K': [],
        'utci_C': [],
        'utci_timestamp': [],
        'prior_day_utci_avg_C': [],
        'next_day_utci_avg_C': [],
        'prior_day_rain': [],
        'next_day_rain': []
    }

    # Process each row with progress bar
    errors = 0
    for idx, row in tqdm(df.iterrows(), total=len(df), desc=f"  {input_path.stem}", unit="row"):
        try:
            lat = row["lat"]
            lon = row["lon"]
            timestamp = row["datetime-local"].isoformat()

            result = get_enhanced_utci_data(lat, lon, timestamp)

            for key in results.keys():
                results[key].append(result[key])

        except Exception as e:
            errors += 1
            logging.error(f"  Row {idx}: {e}")
            # Append NaN/None for failed rows
            for key in results.keys():
                results[key].append(None)

    if errors > 0:
        logging.warning(f"  Encountered {errors} errors during processing")

    # Assign results to new columns
    for key, values in results.items():
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
    logging.info("Starting enhanced UTCI batch processing")
    logging.info(f"Log file: {log_file}")
    logging.info("="*60)

    data_dir = Path("city_estimate_outcomes")

    # Find all CSV files
    csv_files = sorted(data_dir.glob("*.csv"))

    # Filter out files that already have _with_utci suffix
    csv_files = [f for f in csv_files if "_with_utci" not in f.name]

    logging.info(f"Found {len(csv_files)} CSV files to process")

    processed_count = 0
    skipped_count = 0

    for csv_file in csv_files:
        # Check if output file already exists
        output_path = csv_file.parent / csv_file.name.replace(".csv", "_with_utci.csv")

        if output_path.exists():
            logging.info(f"Skipping {csv_file.name} - output already exists")
            skipped_count += 1
            continue

        if process_city_csv(csv_file, output_path):
            processed_count += 1

    logging.info("="*60)
    logging.info(f"Processing complete!")
    logging.info(f"  Processed: {processed_count} files")
    logging.info(f"  Skipped: {skipped_count} files")
    logging.info("="*60)


if __name__ == "__main__":
    main()
