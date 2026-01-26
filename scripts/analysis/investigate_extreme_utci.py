#!/usr/bin/env python3
# ABOUTME: Investigate extreme negative UTCI values across all cities
# ABOUTME: Analyzes cases below -10°C to understand causes

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

def investigate_city_extremes(csv_path):
    """Investigate extreme UTCI values for a single city."""
    city_name = csv_path.parent.name

    df = pd.read_csv(csv_path, low_memory=False)

    if 'utci_C' not in df.columns:
        return None

    # Filter for extreme negative values
    df_extreme = df[df['utci_C'] < -10].copy()

    if len(df_extreme) == 0:
        return None

    # Parse datetime for analysis
    if 'datetime-local' in df.columns:
        df_extreme['datetime-local'] = pd.to_datetime(df_extreme['datetime-local'], errors='coerce')
        df_extreme = df_extreme.dropna(subset=['datetime-local'])

        # Only extract datetime parts if we have datetime type
        if pd.api.types.is_datetime64_any_dtype(df_extreme['datetime-local']):
            df_extreme['month'] = df_extreme['datetime-local'].dt.month
            df_extreme['year'] = df_extreme['datetime-local'].dt.year
            df_extreme['hour'] = df_extreme['datetime-local'].dt.hour

    results = {
        'city': city_name,
        'total_rows': len(df),
        'extreme_count': len(df_extreme),
        'extreme_pct': len(df_extreme) / len(df) * 100,
        'min_utci': df_extreme['utci_C'].min(),
        'max_utci': df_extreme['utci_C'].max(),
        'mean_utci': df_extreme['utci_C'].mean(),
        'median_utci': df_extreme['utci_C'].median(),
        'examples': []
    }

    # Get some examples with metadata
    sample_size = min(10, len(df_extreme))
    samples = df_extreme.nsmallest(sample_size, 'utci_C')

    for _, row in samples.iterrows():
        example = {
            'utci_C': row['utci_C'],
            'lat': row.get('lat'),
            'lon': row.get('lon'),
            'datetime': str(row.get('datetime-local')),
            'month': row.get('month'),
            'year': row.get('year'),
            'hour': row.get('hour'),
            'is_sunny': row.get('is_sunny'),
        }

        # Add weather context if available
        if 'prior_day_rain' in df.columns:
            example['prior_day_rain'] = row.get('prior_day_rain')
        if 'next_day_rain' in df.columns:
            example['next_day_rain'] = row.get('next_day_rain')
        if 'prior_day_utci_avg_C' in df.columns:
            example['prior_day_utci_avg_C'] = row.get('prior_day_utci_avg_C')

        results['examples'].append(example)

    # Month distribution
    if 'month' in df_extreme.columns:
        month_dist = df_extreme['month'].value_counts().to_dict()
        results['month_distribution'] = month_dist

    return results

def main():
    results_dir = Path("data/multi_city_results")

    print("="*80)
    print("EXTREME NEGATIVE UTCI INVESTIGATION")
    print("="*80)
    print("\nAnalyzing UTCI values below -10°C across all cities...")
    print()

    csv_files = list(results_dir.glob("*/*_analyzed_with_utci.csv"))

    all_results = []

    for csv_file in sorted(csv_files):
        result = investigate_city_extremes(csv_file)
        if result:
            all_results.append(result)

    # Sort by severity (lowest minimum UTCI)
    all_results.sort(key=lambda x: x['min_utci'])

    # Print summary table
    print("\n" + "="*80)
    print("SUMMARY: Cities with UTCI < -10°C")
    print("="*80)
    print(f"{'City':<20} {'Count':>8} {'%':>7} {'Min':>8} {'Max':>8} {'Mean':>8} {'Median':>8}")
    print("-"*80)

    for r in all_results:
        print(f"{r['city']:<20} {r['extreme_count']:>8} {r['extreme_pct']:>6.1f}% "
              f"{r['min_utci']:>8.1f} {r['max_utci']:>8.1f} {r['mean_utci']:>8.1f} {r['median_utci']:>8.1f}")

    print()

    # Detailed analysis for each city
    print("\n" + "="*80)
    print("DETAILED ANALYSIS")
    print("="*80)

    for r in all_results:
        print(f"\n{'='*80}")
        print(f"{r['city'].upper()}")
        print(f"{'='*80}")
        print(f"Total observations: {r['total_rows']:,}")
        print(f"Extreme UTCI (<-10°C): {r['extreme_count']:,} ({r['extreme_pct']:.1f}%)")
        print(f"UTCI range: {r['min_utci']:.1f}°C to {r['max_utci']:.1f}°C")
        print(f"Mean: {r['mean_utci']:.1f}°C, Median: {r['median_utci']:.1f}°C")

        if 'month_distribution' in r:
            print(f"\nMonth distribution:")
            month_names = {1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
                          7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}
            for month, count in sorted(r['month_distribution'].items()):
                pct = count / r['extreme_count'] * 100
                print(f"  {month_names.get(month, month):>3}: {count:>4} ({pct:>5.1f}%)")

        print(f"\n10 Most Extreme Examples:")
        print(f"{'-'*80}")
        print(f"{'UTCI':>8} {'Date':<20} {'Month':<5} {'Hour':<5} {'Lat':>8} {'Lon':>9} {'Sunny':<6}")
        print(f"{'-'*80}")

        for ex in r['examples']:
            date_str = ex['datetime'][:16] if ex['datetime'] else 'N/A'
            sunny = str(ex['is_sunny']) if ex['is_sunny'] is not None else 'N/A'
            month = ex.get('month') if ex.get('month') is not None else 'N/A'
            hour = ex.get('hour') if ex.get('hour') is not None else 'N/A'
            print(f"{ex['utci_C']:>8.1f} {date_str:<20} "
                  f"{str(month):<5} {str(hour):<5} "
                  f"{ex.get('lat', 0):>8.2f} {ex.get('lon', 0):>9.2f} {sunny:<6}")

    # Overall statistics
    print("\n" + "="*80)
    print("OVERALL STATISTICS")
    print("="*80)

    total_obs = sum(r['total_rows'] for r in all_results)
    total_extreme = sum(r['extreme_count'] for r in all_results)
    overall_pct = total_extreme / total_obs * 100

    print(f"Total observations across all cities: {total_obs:,}")
    print(f"Total extreme UTCI (<-10°C): {total_extreme:,} ({overall_pct:.2f}%)")
    print(f"Most extreme UTCI: {min(r['min_utci'] for r in all_results):.1f}°C")

    # Geographic/seasonal patterns
    print("\n" + "="*80)
    print("INSIGHTS")
    print("="*80)

    print("\nUTCI Calculation Method:")
    print("  - Based on ERA5 reanalysis data from Open-Meteo")
    print("  - Uses: Temperature (2m), Dewpoint (2m), Wind Speed (10m)")
    print("  - Formula: thermofeel.calculate_utci() from ECMWF library")
    print("  - MRT approximation: Uses air temperature (no solar radiation component)")

    print("\nPotential causes of extreme negative UTCI:")
    print("  1. High winds + cold temperatures (wind chill effect)")
    print("  2. Winter months in continental/northern cities")
    print("  3. Night-time/early morning observations (low solar angle)")
    print("  4. High humidity + cold temps (increased heat loss)")
    print("  5. Data quality issues (rare)")

    print("\nCities most affected:")
    for i, r in enumerate(all_results[:3], 1):
        print(f"  {i}. {r['city']}: {r['extreme_count']} cases, min {r['min_utci']:.1f}°C")

    print()

if __name__ == "__main__":
    main()
