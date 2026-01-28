# ABOUTME: Test script to evaluate Open-Meteo bulk/multi-location API capabilities.
# ABOUTME: Determines if batching multiple coordinates counts as 1 or N API calls.

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'utils'))

import requests
import time
import pandas as pd
from datetime import datetime
import json


def test_single_location():
    """Test baseline: single location request."""
    print("=" * 70)
    print("TEST 1: Single Location (Baseline)")
    print("=" * 70)

    lat, lon = 33.68, -84.26
    start_date = "1991-06-22"
    end_date = "1991-06-24"

    url = (
        f"https://archive-api.open-meteo.com/v1/era5"
        f"?latitude={lat}"
        f"&longitude={lon}"
        f"&start_date={start_date}"
        f"&end_date={end_date}"
        f"&hourly=temperature_2m,dewpoint_2m,wind_speed_10m,precipitation"
        f"&timezone=UTC"
    )

    start_time = time.time()
    try:
        resp = requests.get(url, timeout=30)
        elapsed = time.time() - start_time

        print(f"  URL: {url[:80]}...")
        print(f"  Status: {resp.status_code}")
        print(f"  Time: {elapsed:.2f}s")
        print(f"  Response size: {len(resp.content):,} bytes")

        if resp.status_code == 200:
            data = resp.json()
            if 'hourly' in data:
                print(f"  Hourly records: {len(data['hourly']['time'])}")
                print(f"  SUCCESS ✓")
                return True, elapsed, len(resp.content)
        elif resp.status_code == 429:
            print(f"  ERROR: Rate limited (429)")
            print(f"  Response: {resp.text}")
            return False, elapsed, len(resp.content)
        else:
            print(f"  ERROR: {resp.status_code}")
            print(f"  Response: {resp.text[:200]}")
            return False, elapsed, len(resp.content)

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"  ERROR: {e}")
        return False, elapsed, 0
    finally:
        print()


def test_multiple_locations(num_locations):
    """Test multi-location request with N locations."""
    print("=" * 70)
    print(f"TEST 2: {num_locations} Locations in Single Request")
    print("=" * 70)

    # Generate test locations around Atlanta
    base_lat, base_lon = 33.75, -84.39
    lats = [round(base_lat + (i * 0.05), 2) for i in range(num_locations)]
    lons = [round(base_lon + (i * 0.05), 2) for i in range(num_locations)]

    lat_str = ",".join(map(str, lats))
    lon_str = ",".join(map(str, lons))

    start_date = "1991-06-22"
    end_date = "1991-06-24"

    url = (
        f"https://archive-api.open-meteo.com/v1/era5"
        f"?latitude={lat_str}"
        f"&longitude={lon_str}"
        f"&start_date={start_date}"
        f"&end_date={end_date}"
        f"&hourly=temperature_2m,dewpoint_2m,wind_speed_10m,precipitation"
        f"&timezone=UTC"
    )

    print(f"  Coordinates: {num_locations} locations")
    print(f"  First location: ({lats[0]}, {lons[0]})")
    print(f"  Last location: ({lats[-1]}, {lons[-1]})")

    start_time = time.time()
    try:
        resp = requests.get(url, timeout=60)
        elapsed = time.time() - start_time

        print(f"  Status: {resp.status_code}")
        print(f"  Time: {elapsed:.2f}s")
        print(f"  Response size: {len(resp.content):,} bytes")

        if resp.status_code == 200:
            data = resp.json()

            # Multi-location responses are arrays
            if isinstance(data, list):
                print(f"  Locations in response: {len(data)}")
                if len(data) > 0 and 'hourly' in data[0]:
                    print(f"  Hourly records per location: {len(data[0]['hourly']['time'])}")
                print(f"  Response format: Array of location objects")
                print(f"  SUCCESS ✓")
                return True, elapsed, len(resp.content), len(data)
            else:
                print(f"  WARNING: Expected array response, got object")
                print(f"  Response type: {type(data)}")
                return False, elapsed, len(resp.content), 1

        elif resp.status_code == 429:
            print(f"  ERROR: Rate limited (429)")
            print(f"  Response: {resp.text}")
            return False, elapsed, len(resp.content), 0
        else:
            print(f"  ERROR: {resp.status_code}")
            print(f"  Response: {resp.text[:200]}")
            return False, elapsed, len(resp.content), 0

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"  ERROR: {e}")
        return False, elapsed, 0, 0
    finally:
        print()


def test_real_data_sample():
    """Test with actual data sample to see deduplication potential."""
    print("=" * 70)
    print("TEST 3: Real Data Analysis")
    print("=" * 70)

    project_root = Path(__file__).parent.parent.parent
    data_path = project_root / "data/transit_surveys/processed/metro_surveys_standardized.csv"

    if not data_path.exists():
        print(f"  ERROR: Data file not found: {data_path}")
        return

    print(f"  Loading: {data_path.name}")
    df = pd.read_csv(data_path, low_memory=False)
    df['datetime'] = pd.to_datetime(df['datetime'])

    print(f"  Total trips: {len(df):,}")

    # Analyze deduplication potential
    df['date'] = df['datetime'].dt.date
    df['lat_rounded'] = df['lat'].round(2)
    df['lon_rounded'] = df['lon'].round(2)

    unique_combos = df.groupby(['date', 'lat_rounded', 'lon_rounded']).size()
    print(f"  Unique date+location combos: {len(unique_combos):,}")
    print(f"  Deduplication savings: {100*(1 - len(unique_combos)/len(df)):.1f}%")

    # Sample for batch testing
    sample_size = 25
    sample_combos = unique_combos.head(sample_size)

    print(f"\n  Sample {sample_size} combinations for batch test:")
    batch_lats = []
    batch_lons = []
    batch_dates = []

    for (date, lat, lon), count in sample_combos.items():
        batch_lats.append(lat)
        batch_lons.append(lon)
        batch_dates.append(date)

    print(f"    Date range: {min(batch_dates)} to {max(batch_dates)}")
    print(f"    Lat range: {min(batch_lats):.2f} to {max(batch_lats):.2f}")
    print(f"    Lon range: {min(batch_lons):.2f} to {max(batch_lons):.2f}")
    print()


def analyze_results(single_success, single_time, single_size,
                    multi_success, multi_time, multi_size, multi_locs):
    """Analyze and compare test results."""
    print("=" * 70)
    print("ANALYSIS")
    print("=" * 70)

    if single_success and multi_success:
        print(f"  Single location time: {single_time:.2f}s")
        print(f"  Multi location time: {multi_time:.2f}s")
        print(f"  Multi location count: {multi_locs}")
        print()

        # Calculate if batching is efficient
        expected_time = single_time * multi_locs
        actual_time = multi_time
        speedup = expected_time / actual_time

        print(f"  Expected time ({multi_locs} individual calls): {expected_time:.2f}s")
        print(f"  Actual time (1 batch call): {actual_time:.2f}s")
        print(f"  Speedup factor: {speedup:.1f}x")
        print()

        # Size analysis
        size_per_loc_single = single_size
        size_per_loc_multi = multi_size / multi_locs if multi_locs > 0 else 0

        print(f"  Single location response: {single_size:,} bytes")
        print(f"  Multi location response: {multi_size:,} bytes ({multi_locs} locations)")
        print(f"  Bytes per location (multi): {size_per_loc_multi:,.0f} bytes")
        print()

        # Recommendation
        print("  RECOMMENDATION:")
        if speedup > 5:
            print(f"    ✓ Bulk API is HIGHLY EFFICIENT ({speedup:.1f}x faster)")
            print(f"    ✓ Implement batched fetching with 25-50 locations per call")
        elif speedup > 2:
            print(f"    ✓ Bulk API is MODERATELY EFFICIENT ({speedup:.1f}x faster)")
            print(f"    ✓ Consider batched fetching with 10-25 locations per call")
        else:
            print(f"    ⚠ Bulk API shows minimal advantage ({speedup:.1f}x faster)")
            print(f"    ⚠ Stick with deduplicated single-location approach")

        print()
        print("  CRITICAL QUESTION:")
        print("    Does batching count as 1 API call or N calls toward rate limit?")
        print("    → Test by monitoring rate limit counter")
        print("    → If 1 call: Batch size = 50-100 locations")
        print("    → If N calls: Stick with deduplication only")

    elif not single_success:
        print("  ⚠ Single location test failed (rate limited)")
        print("  → Wait for rate limit to reset (~60 minutes)")
        print("  → Retry tests after limit resets")
    else:
        print("  ⚠ Multi location test failed")
        print("  → May not be supported or rate limited")

    print()


def main():
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "OPEN-METEO BULK API TEST SUITE" + " " * 23 + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Test 1: Single location
    single_success, single_time, single_size = test_single_location()

    if not single_success:
        print("⚠ Stopping tests - rate limited or error occurred")
        print()
        print("Rate limit likely resets at the top of the hour.")
        print("Try again later with:")
        print("  python scripts/travel_surveys/test_bulk_api.py")
        return

    # Small delay between tests
    time.sleep(2)

    # Test 2: Multiple locations (start with 10)
    multi_success_10, multi_time_10, multi_size_10, multi_locs_10 = test_multiple_locations(10)

    if multi_success_10:
        time.sleep(2)
        # Test 3: More locations (25)
        multi_success_25, multi_time_25, multi_size_25, multi_locs_25 = test_multiple_locations(25)

        # Use the 25-location result for analysis
        if multi_success_25:
            multi_success, multi_time, multi_size, multi_locs = (
                multi_success_25, multi_time_25, multi_size_25, multi_locs_25
            )
        else:
            multi_success, multi_time, multi_size, multi_locs = (
                multi_success_10, multi_time_10, multi_size_10, multi_locs_10
            )
    else:
        multi_success, multi_time, multi_size, multi_locs = (
            multi_success_10, multi_time_10, multi_size_10, multi_locs_10
        )

    # Analyze real data
    time.sleep(1)
    test_real_data_sample()

    # Final analysis
    analyze_results(single_success, single_time, single_size,
                   multi_success, multi_time, multi_size, multi_locs)

    print("=" * 70)
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()


if __name__ == '__main__':
    main()
