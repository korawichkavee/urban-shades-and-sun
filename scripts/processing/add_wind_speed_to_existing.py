#!/usr/bin/env python3
# ABOUTME: Add wind speed data to existing UTCI-enriched CSVs using cached ERA5 data

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'utils'))
from enhanced_utci import get_enhanced_utci_data
import pandas as pd
from pathlib import Path
from tqdm import tqdm
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def add_wind_to_csv(csv_path):
    """Add wind speed and met data to existing CSV."""
    city_name = csv_path.parent.name
    logger.info(f"\nProcessing {city_name}...")

    # Load CSV
    df = pd.read_csv(csv_path, low_memory=False)

    # Check if wind data already exists
    if 'wind_speed_10m' in df.columns:
        logger.info(f"  Wind data already present, skipping")
        return

    # Check if we have UTCI data
    if 'utci_C' not in df.columns:
        logger.info(f"  No UTCI data found, skipping")
        return

    logger.info(f"  Processing {len(df)} rows...")

    # Add new columns
    df['wind_speed_10m'] = None
    df['temperature_2m'] = None
    df['dewpoint_2m'] = None

    #Process with progress bar
    for idx in tqdm(range(len(df)), desc=f"  {city_name}"):
        row = df.iloc[idx]

        # Skip if no datetime
        if pd.isna(row['datetime-local']):
            continue

        try:
            result = get_enhanced_utci_data(row['lat'], row['lon'], row['datetime-local'])
            df.at[idx, 'wind_speed_10m'] = result.get('wind_speed_10m')
            df.at[idx, 'temperature_2m'] = result.get('temperature_2m')
            df.at[idx, 'dewpoint_2m'] = result.get('dewpoint_2m')
        except Exception as e:
            if idx < 5:  # Only log first few errors
                logger.debug(f"    Row {idx} error: {e}")
            continue

    # Save updated CSV
    df.to_csv(csv_path, index=False)
    logger.info(f"  ✓ Updated {csv_path.name}")

def main():
    results_dir = Path("data/multi_city_results")

    print("="*80)
    print("ADDING WIND SPEED DATA TO EXISTING CSVs")
    print("="*80)
    print("\nThis will use the ERA5 cache to quickly add wind speed data")
    print()

    csv_files = list(results_dir.glob("*/*_analyzed_with_utci.csv"))

    logger.info(f"Found {len(csv_files)} CSVs to update\n")

    for csv_file in sorted(csv_files):
        add_wind_to_csv(csv_file)

    print("\n" + "="*80)
    print("✓ COMPLETE")
    print("="*80)
    print()

if __name__ == "__main__":
    main()
