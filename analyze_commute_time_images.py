# ABOUTME: Filters street view metadata to commute hours (8-10am, 4-6pm) in local time.
# ABOUTME: Counts filtered images per city and estimates analysis time for shade detection.

import pandas as pd
from pathlib import Path
from datetime import datetime
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
    'phoenix': 'America/Phoenix',  # Arizona doesn't observe DST
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

def analyze_city_metadata(csv_file, city_name, timezone_str):
    """Analyze metadata for a single city and filter for commute hours."""

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
    commute_images = commute_mask.sum()

    # Get hour distribution for commute times
    commute_df = df[commute_mask]
    hour_dist = commute_df['local_hour'].value_counts().sort_index()

    percentage = (commute_images / total_images * 100) if total_images > 0 else 0

    print(f"  Total images: {total_images:,}")
    print(f"  Commute time images (8-10am, 4-6pm local): {commute_images:,} ({percentage:.1f}%)")
    if len(hour_dist) > 0:
        print(f"  Hour distribution:")
        for hour, count in hour_dist.items():
            hour_pct = count / commute_images * 100
            print(f"    {hour:02d}:00 - {count:,} ({hour_pct:.1f}%)")

    return {
        'city': city_name,
        'timezone': timezone_str,
        'total_images': total_images,
        'commute_images': commute_images,
        'percentage': percentage,
        'hour_distribution': dict(hour_dist)
    }

def main():
    base_dir = Path(__file__).parent
    data_dir = base_dir / "data" / "metro_cities_svi_test"

    print("="*70)
    print("COMMUTE TIME IMAGE ANALYSIS")
    print("Filtering for: 8-10am and 4-6pm local time")
    print("="*70)

    all_results = []
    total_all_images = 0
    total_commute_images = 0

    # Process each city
    for city_name, timezone_str in sorted(CITY_TIMEZONES.items()):
        csv_file = data_dir / city_name / f"{city_name}_metadata.csv"

        if not csv_file.exists():
            print(f"\nSkipping {city_name} - no metadata file found")
            continue

        try:
            result = analyze_city_metadata(csv_file, city_name, timezone_str)
            all_results.append(result)
            total_all_images += result['total_images']
            total_commute_images += result['commute_images']
        except Exception as e:
            print(f"  ERROR: {e}")

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    print(f"\nTotal images across all cities: {total_all_images:,}")
    print(f"Commute time images (8-10am, 4-6pm local): {total_commute_images:,}")
    print(f"Percentage: {total_commute_images/total_all_images*100:.1f}%")

    # Sort by commute images
    sorted_results = sorted(all_results, key=lambda x: x['commute_images'], reverse=True)

    print(f"\n{'City':<20} {'Total Images':>15} {'Commute Images':>15} {'%':>8}")
    print("-"*70)
    for r in sorted_results:
        print(f"{r['city'].title():<20} {r['total_images']:>15,} {r['commute_images']:>15,} {r['percentage']:>7.1f}%")
    print("-"*70)
    print(f"{'TOTAL':<20} {total_all_images:>15,} {total_commute_images:>15,} {total_commute_images/total_all_images*100:>7.1f}%")

    # Estimate analysis time
    print("\n" + "="*70)
    print("ANALYSIS TIME ESTIMATION")
    print("="*70)

    # Performance estimates from optimization documentation
    print("\n=== RTX 4090 24GB GPU (Optimized Pipeline) ===")
    print("Batch sizes: ViT=128, YOLO=32")
    print("Pipeline: Batch ViT + Batch YOLO + Async Download")

    # RTX 4090 estimates from METRO_SVI_OPTIMIZATIONS.md
    conservative_ips = 3.0  # Conservative estimate
    typical_ips = 4.0       # Typical expected performance
    optimistic_ips = 5.0    # Best case performance

    print(f"\nConservative ({conservative_ips} img/sec):")
    cons_hours = total_commute_images / conservative_ips / 3600
    print(f"  Total time: {cons_hours:,.1f} hours ({cons_hours/24:,.1f} days)")

    print(f"\nTypical ({typical_ips} img/sec):")
    typ_hours = total_commute_images / typical_ips / 3600
    print(f"  Total time: {typ_hours:,.1f} hours ({typ_hours/24:,.1f} days)")

    print(f"\nOptimistic ({optimistic_ips} img/sec):")
    opt_hours = total_commute_images / optimistic_ips / 3600
    print(f"  Total time: {opt_hours:,.1f} hours ({opt_hours/24:,.1f} days)")

    print("\n=== Standard GPU (8GB VRAM) ===")
    print("Batch sizes: ViT=32, YOLO=8")
    standard_ips = 1.5  # Standard performance with smaller batches

    std_hours = total_commute_images / standard_ips / 3600
    print(f"\nTypical ({standard_ips} img/sec):")
    print(f"  Total time: {std_hours:,.1f} hours ({std_hours/24:,.1f} days)")

    print("\n=== CPU Only (No GPU) ===")
    cpu_ips = 0.2  # Very slow without GPU
    cpu_hours = total_commute_images / cpu_ips / 3600
    print(f"\nTypical ({cpu_ips} img/sec):")
    print(f"  Total time: {cpu_hours:,.1f} hours ({cpu_hours/24:,.1f} days)")

    print("\n" + "="*70)
    print("RECOMMENDATION: RTX 4090 can complete analysis in ~1-2 days")
    print("="*70)

if __name__ == "__main__":
    main()
