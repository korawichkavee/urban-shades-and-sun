#!/usr/bin/env python3
# ABOUTME: Prepare multi-city CSVs for UTCI processing by adding datetime-local column

import pandas as pd
from pathlib import Path
import pytz
from datetime import datetime
import logging

# City timezone mappings
CITY_TIMEZONES = {
    'Singapore': 'Asia/Singapore',
    'Osaka': 'Asia/Tokyo',
    'Madrid': 'Europe/Madrid',
    'Istanbul': 'Europe/Istanbul',
    'Buenos-Aires': 'America/Argentina/Buenos_Aires',
    'Mumbai': 'Asia/Kolkata',
    'Cape-Town': 'Africa/Johannesburg',
}

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    results_dir = Path("data/multi_city_results")
    csv_files = list(results_dir.glob("*/*_analyzed.csv"))

    logger.info(f"Found {len(csv_files)} CSVs to prepare")

    for csv_file in csv_files:
        city_name = csv_file.parent.name
        logger.info(f"\nProcessing {city_name}...")

        # Load CSV
        df = pd.read_csv(csv_file)

        # Check if datetime-local already exists
        if 'datetime-local' in df.columns:
            logger.info(f"  {city_name} already has datetime-local column")
            continue

        # Get timezone for this city
        if city_name not in CITY_TIMEZONES:
            logger.error(f"  No timezone mapping for {city_name}")
            continue

        tz = pytz.timezone(CITY_TIMEZONES[city_name])

        # Convert captured_at (milliseconds since epoch) to datetime
        df['datetime_utc'] = pd.to_datetime(df['captured_at'], unit='ms', utc=True)

        # Convert to local timezone
        df['datetime-local'] = df['datetime_utc'].dt.tz_convert(tz)

        # Format as ISO string (required by UTCI script)
        df['datetime-local'] = df['datetime-local'].dt.strftime('%Y-%m-%dT%H:%M:%S%z')

        # Save back to same file
        df.to_csv(csv_file, index=False)
        logger.info(f"  ✓ Added datetime-local column ({len(df)} rows)")

    logger.info("\n" + "="*80)
    logger.info("All CSVs prepared!")
    logger.info("="*80)

if __name__ == "__main__":
    main()
