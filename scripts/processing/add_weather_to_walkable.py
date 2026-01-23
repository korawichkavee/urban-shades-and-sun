#!/usr/bin/env python3
# ABOUTME: Adds weather data to walkable street image CSVs
# ABOUTME: Processes only the filtered subset of images on walkable streets

import pandas as pd
from pathlib import Path
from add_weather_data import csv_weather_annotations

def main():
    """Add weather data to walkable CSV subsets."""

    print("="*60)
    print("Add Weather Data to Walkable Street Images")
    print("="*60)

    base_dir = Path('/home/kieran/Documents/Python/sunny_day_SVI/city7sample')

    # Find all walkable CSVs
    walkable_csvs = list(base_dir.glob('*_walkable_*.csv'))

    print(f"\nFound {len(walkable_csvs)} walkable CSV files:")
    for csv_file in walkable_csvs:
        df = pd.read_csv(csv_file)
        print(f"  {csv_file.name}: {len(df)} images")

    if not walkable_csvs:
        print("\nNo walkable CSV files found. Run filter_walkable_streets.py first.")
        return

    success_count = 0
    error_count = 0

    for csv_file in walkable_csvs:
        try:
            print(f"\nProcessing {csv_file.name}...")

            # Check if already has weather data
            df_test = pd.read_csv(csv_file, nrows=1)
            if 'wbulb' in df_test.columns:
                print(f"  Already has weather data, skipping")
                continue

            # Add weather data
            df_with_weather = csv_weather_annotations(str(csv_file))

            # Save
            df_with_weather.to_csv(csv_file, index=False)
            print(f"  ✓ Successfully added weather data")
            success_count += 1

        except Exception as e:
            print(f"  ✗ ERROR: {type(e).__name__}: {str(e)}")
            error_count += 1

    print("\n" + "="*60)
    print("Processing Complete!")
    print("="*60)
    print(f"Success: {success_count}")
    print(f"Errors: {error_count}")
    print()

if __name__ == '__main__':
    main()
