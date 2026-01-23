# ABOUTME: Batch processes all CSV files in city_estimate_outcomes/ to add UTCI values.
# ABOUTME: Skips files that already have UTCI data to avoid redundant processing.

from quickhotpoint2 import get_utci_from_coords
import pandas as pd
from pathlib import Path
from tqdm import tqdm

def process_city_csv(input_path, output_path):
    """Process a single CSV file to add UTCI values."""
    print(f"\nProcessing {input_path.name}...")

    # Load CSV
    df = pd.read_csv(input_path)

    # Check if UTCI columns already exist
    if 'utci_C' in df.columns:
        print(f"  Skipping - UTCI data already present")
        return False

    # Check for required columns
    if 'datetime-local' not in df.columns:
        print(f"  Skipping - missing datetime-local column")
        return False

    # Parse datetime
    df["datetime-local"] = pd.to_datetime(df["datetime-local"], format="ISO8601", errors="coerce")

    # Prepare result lists
    utci_K_list = []
    utci_C_list = []
    ts_list = []

    # Process each row with progress bar
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="  Fetching UTCI", unit="row"):
        lat = row["lat"]
        lon = row["lon"]
        timestamp = row["datetime-local"].isoformat()

        utci_K, utci_C, ts = get_utci_from_coords(lat, lon, timestamp)

        utci_K_list.append(utci_K)
        utci_C_list.append(utci_C)
        ts_list.append(ts)

    # Assign results to new columns
    df["utci_K"] = utci_K_list
    df["utci_C"] = utci_C_list
    df["utci_timestamp"] = ts_list

    # Save updated dataframe
    df.to_csv(output_path, index=False)
    print(f"  Saved to {output_path.name}")
    return True

def main():
    data_dir = Path("city_estimate_outcomes")

    # Find all CSV files
    csv_files = sorted(data_dir.glob("*.csv"))

    # Filter out files that already have _with_utci suffix
    csv_files = [f for f in csv_files if "_with_utci" not in f.name]

    print(f"Found {len(csv_files)} CSV files to process")

    processed_count = 0
    for csv_file in csv_files:
        # Check if output file already exists
        output_path = csv_file.parent / csv_file.name.replace(".csv", "_with_utci.csv")

        if output_path.exists():
            print(f"\nSkipping {csv_file.name} - output already exists")
            continue

        if process_city_csv(csv_file, output_path):
            processed_count += 1

    print(f"\n{'='*60}")
    print(f"Processing complete! Processed {processed_count} files.")

if __name__ == "__main__":
    main()
