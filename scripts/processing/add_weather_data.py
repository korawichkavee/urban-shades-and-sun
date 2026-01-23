#!/usr/bin/env python3
# ABOUTME: Adds hourly weather data (wet bulb, dry bulb temps) to city CSV files
# ABOUTME: Uses meteostat to retrieve historical weather data for each image timestamp

import pandas as pd
import os
from tqdm import tqdm
from datetime import datetime, timedelta, timezone
import meteostat
from metpy.calc import wet_bulb_temperature
from metpy.units import units
from tenacity import retry, wait_exponential, stop_after_attempt
from pathlib import Path

meteostat.Hourly.max_age = 0  # disable caching since it was causing error

@retry(wait=wait_exponential(multiplier=1, min=0, max=10), stop=stop_after_attempt(5))
def get_meteostat_hourly(img_point, start_time, end_time, retrieval_timezone):
    """Retrieve hourly weather data with retry logic."""
    data = meteostat.Hourly(img_point, start_time, end_time, retrieval_timezone)
    return data

def get_meteostat_point(lat, lon, alt):
    """Create meteostat Point for location."""
    img_point = meteostat.Point(lat, lon, alt)
    return img_point

def get_hourly_weather(row):
    """Get weather data for a single image row."""
    print(f"Processing image ID: {row['id']}")

    lat = row['lat']
    lon = row['lon']
    img_point = get_meteostat_point(lat, lon, 0)  # alt of 0 to make assumption
    img_point.alt_range = 2000  # 2km alt range to be generous

    img_time = row['datetime-local']
    img_time = pd.to_datetime(img_time, format='ISO8601', utc=True)

    time_range = timedelta(hours=1)
    start_time = img_time - time_range  # 1 hr before
    end_time = img_time + time_range  # 1hr after

    retrieval_timezone = str(start_time.tz)
    start_time = start_time.replace(tzinfo=None)
    end_time = end_time.replace(tzinfo=None)

    data = get_meteostat_hourly(img_point, start_time, end_time, retrieval_timezone)
    data = data.aggregate('d')  # aggregate it all to get 1 value guaranteed
    data = data.fetch()

    if data.empty:
        print(f"  WARNING: No weather data found for image {row['id']}")
        row['wbulb'] = None
        row['dbulb'] = None
        row['tsun'] = None
        row['rhum'] = None
        return row

    # Pick first row of data only
    dry_bulb_temp = data['temp']  # C
    rel_humidity = data['rhum']  # %
    sunshine_time = data['tsun']  # min
    dew_point = data['dwpt']  # C
    air_pressure = data['pres']  # hPa

    # Calculate wet bulb temperature
    wet_bulb_temp = wet_bulb_temperature(
        air_pressure.to_numpy() * units.hPa,
        dry_bulb_temp.to_numpy() * units.degC,
        dew_point.to_numpy() * units.degC
    )

    # Extract scalar values from numpy arrays/scalars
    wbulb_val = wet_bulb_temp.magnitude
    # Handle both numpy arrays and scalars
    if hasattr(wbulb_val, '__len__'):
        row['wbulb'] = float(wbulb_val[0]) if len(wbulb_val) > 0 else None
    else:
        row['wbulb'] = float(wbulb_val)

    row['dbulb'] = float(dry_bulb_temp.to_numpy()[0])
    row['tsun'] = float(sunshine_time.to_numpy()[0]) if not pd.isna(sunshine_time.to_numpy()[0]) else None
    row['rhum'] = float(rel_humidity.to_numpy()[0]) if not pd.isna(rel_humidity.to_numpy()[0]) else None

    print(f"  Weather data added - Dry bulb: {row['dbulb']}°C, Wet bulb: {row['wbulb']}°C, RH: {row['rhum']}%")

    return row

def csv_weather_annotations(csvpath):
    """Apply weather annotations to entire CSV."""
    print(f"\nProcessing CSV: {csvpath}")
    df_city = pd.read_csv(csvpath)

    # Check if weather data already exists
    if 'wbulb' in df_city.columns and 'dbulb' in df_city.columns:
        print(f"  Weather data already exists. Skipping.")
        return df_city

    # Check if datetime-local column exists
    if 'datetime-local' not in df_city.columns:
        print(f"  ERROR: datetime-local column not found. Run time_metadata_enrichment.py first.")
        return df_city

    print(f"  Total rows: {len(df_city)}")
    df_city = df_city.apply(lambda row: get_hourly_weather(row), axis=1)

    return df_city

def main():
    """Process all CSV files in city7sample directory."""
    starting_dir = Path('/home/kieran/Documents/Python/sunny_day_SVI/city7sample')

    # Get only CSV files (not directories or other files)
    csv_files = sorted([f for f in starting_dir.iterdir() if f.suffix == '.csv'])

    print("="*60)
    print("Weather Data Annotation")
    print("="*60)
    print(f"\nFound {len(csv_files)} CSV files to process:")
    for f in csv_files:
        print(f"  - {f.name}")
    print()

    success_count = 0
    error_count = 0
    skip_count = 0

    for csvfile in csv_files:
        try:
            csvfilepath = str(csvfile)

            # Read first to check if already processed
            df_test = pd.read_csv(csvfilepath, nrows=1)
            if 'wbulb' in df_test.columns and 'dbulb' in df_test.columns:
                print(f"\n✓ {csvfile.name} - Already has weather data, skipping")
                skip_count += 1
                continue

            if 'datetime-local' not in df_test.columns:
                print(f"\n✗ {csvfile.name} - Missing datetime-local column, skipping")
                error_count += 1
                continue

            # Process the file
            city_df = csv_weather_annotations(csvfilepath)
            city_df.to_csv(csvfilepath, index=False)

            print(f"✓ {csvfile.name} - Successfully processed and saved\n")
            success_count += 1

        except Exception as e:
            print(f"\n✗ ERROR processing {csvfile.name}:")
            print(f"  {type(e).__name__}: {str(e)}\n")
            error_count += 1

    print("\n" + "="*60)
    print("Processing Complete!")
    print("="*60)
    print(f"Success: {success_count}")
    print(f"Skipped: {skip_count}")
    print(f"Errors: {error_count}")
    print()

if __name__ == '__main__':
    main()
