# ABOUTME: Generates filtered metadata CSVs containing only commute-time images (8-10am, 4-6pm local).
# ABOUTME: Creates deployment-ready metadata files for each metro city.

import pandas as pd
from pathlib import Path
import pytz

# Metro cities with their timezones
CITY_TIMEZONES = {
    'anchorage': 'America/Anchorage',
    'atlanta': 'America/New_York',
    'boise': 'America/Boise',
    'boston': 'America/New_York',
    'cleveland': 'America/New_York',
    'columbia': 'America/New_York',
    'denver': 'America/Denver',
    'evansville': 'America/Chicago',
    'honolulu': 'Pacific/Honolulu',
    'los-angeles': 'America/Los_Angeles',
    'louisville': 'America/New_York',
    'minneapolis': 'America/Chicago',
    'phoenix': 'America/Phoenix',
    'raleigh': 'America/New_York',
    'salt-lake-city': 'America/Denver',
    'san-francisco': 'America/Los_Angeles',
    'seattle': 'America/Los_Angeles',
    'st.-louis': 'America/Chicago',
    'tucson': 'America/Phoenix',
}

def is_commute_hour(hour):
    """Check if hour is in commute time windows (8-10am or 4-6pm)."""
    return (8 <= hour < 10) or (16 <= hour < 18)

def filter_city_metadata(csv_file, city_name, timezone_str, output_dir):
    """Filter metadata for a single city to only commute hours."""

    print(f"\nProcessing {city_name}...")

    # Load metadata
    df = pd.read_csv(csv_file)
    total_images = len(df)

    # Parse timestamps and convert to local timezone
    df['captured_at'] = pd.to_datetime(df['captured_at'], format='mixed')

    # Assume captured_at is in UTC, convert to local time
    tz = pytz.timezone(timezone_str)
    df['local_time'] = df['captured_at'].dt.tz_localize('UTC').dt.tz_convert(tz)
    df['local_hour'] = df['local_time'].dt.hour

    # Filter for commute hours
    commute_mask = df['local_hour'].apply(is_commute_hour)
    filtered_df = df[commute_mask].copy()

    # Drop the temporary local_time and local_hour columns
    filtered_df = filtered_df.drop(columns=['local_time', 'local_hour'])

    # Save filtered metadata
    output_file = output_dir / city_name / f"{city_name}_metadata_commute.csv"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    filtered_df.to_csv(output_file, index=False)

    commute_images = len(filtered_df)
    percentage = (commute_images / total_images * 100) if total_images > 0 else 0

    print(f"  Original: {total_images:,} images")
    print(f"  Filtered: {commute_images:,} images ({percentage:.1f}%)")
    print(f"  Saved to: {output_file}")

    return {
        'city': city_name,
        'total': total_images,
        'filtered': commute_images,
        'percentage': percentage
    }

def main():
    base_dir = Path(__file__).parent
    input_dir = base_dir / "data" / "metro_cities_svi_test"
    output_dir = base_dir / "data" / "metro_cities_svi_commute"

    print("="*70)
    print("GENERATING COMMUTE-TIME FILTERED METADATA")
    print("Filtering for: 8-10am and 4-6pm local time")
    print("="*70)

    results = []

    # Process each city
    for city_name, timezone_str in sorted(CITY_TIMEZONES.items()):
        csv_file = input_dir / city_name / f"{city_name}_metadata.csv"

        if not csv_file.exists():
            print(f"\nSkipping {city_name} - no metadata file found")
            continue

        try:
            result = filter_city_metadata(csv_file, city_name, timezone_str, output_dir)
            results.append(result)
        except Exception as e:
            print(f"  ERROR: {e}")

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    total_original = sum(r['total'] for r in results)
    total_filtered = sum(r['filtered'] for r in results)

    print(f"\n{'City':<20} {'Original':>15} {'Filtered':>15} {'%':>8}")
    print("-"*70)
    for r in sorted(results, key=lambda x: x['filtered'], reverse=True):
        print(f"{r['city'].title():<20} {r['total']:>15,} {r['filtered']:>15,} {r['percentage']:>7.1f}%")
    print("-"*70)
    print(f"{'TOTAL':<20} {total_original:>15,} {total_filtered:>15,} {total_filtered/total_original*100:>7.1f}%")

    print(f"\nFiltered metadata saved to: {output_dir}/")
    print(f"Files created: {len(results)} cities")

if __name__ == "__main__":
    main()
