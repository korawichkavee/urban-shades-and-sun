#!/usr/bin/env python3
# ABOUTME: Tests weather data addition on small sample of walkable images
# ABOUTME: Verifies the weather data pipeline works before running full dataset

import pandas as pd
from pathlib import Path
from add_weather_data import get_hourly_weather

def main():
    """Test weather data on first 10 rows of Buenos Aires walkable images."""

    print("="*60)
    print("Test Weather Data on Sample")
    print("="*60)

    base_dir = Path('/home/kieran/Documents/Python/sunny_day_SVI/city7sample')
    csv_file = base_dir / 'Buenos-Aires_walkable_1032717330.csv'

    if not csv_file.exists():
        print(f"\nERROR: {csv_file.name} not found")
        print("Run filter_walkable_streets.py first")
        return

    print(f"\nLoading first 10 rows from {csv_file.name}...")
    df = pd.read_csv(csv_file, nrows=10)
    print(f"Loaded {len(df)} rows")

    # Check if datetime-local exists
    if 'datetime-local' not in df.columns:
        print("\nERROR: datetime-local column not found")
        print("Run time_metadata_enrichment.py first")
        return

    print(f"\nTesting weather data retrieval on {len(df)} images...")
    print("This will take ~20 seconds (2 sec per image)\n")

    success = 0
    errors = 0

    for idx, row in df.iterrows():
        try:
            row_with_weather = get_hourly_weather(row)
            if pd.notna(row_with_weather.get('wbulb')):
                success += 1
            else:
                errors += 1
        except Exception as e:
            print(f"  Error on row {idx}: {e}")
            errors += 1

    print("\n" + "="*60)
    print("Test Complete!")
    print("="*60)
    print(f"Success: {success}/{len(df)}")
    print(f"Errors: {errors}/{len(df)}")

    if success > 0:
        print("\n✓ Weather data pipeline working!")
        print("Ready to run full dataset with add_weather_overnight.py")
    else:
        print("\n✗ Weather data pipeline has issues")
        print("Check error messages above")

if __name__ == '__main__':
    main()
