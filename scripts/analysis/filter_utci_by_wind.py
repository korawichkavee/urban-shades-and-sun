#!/usr/bin/env python3
# ABOUTME: Filter UTCI data by wind speed threshold (17 m/s) and add validation flags
# ABOUTME: Creates visualizations showing filtering impact and updates CSVs

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

WIND_THRESHOLD = 17.0  # m/s - UTCI valid range upper limit

def analyze_and_filter_city(csv_path, output_dir):
    """Analyze wind speed distribution and filter invalid UTCI values."""
    city_name = csv_path.parent.name

    print(f"\nProcessing {city_name}...")

    df = pd.read_csv(csv_path, low_memory=False)

    if 'utci_C' not in df.columns:
        print(f"  No UTCI data found")
        return None

    # Get original counts
    total_rows = len(df)
    has_utci = df['utci_C'].notna().sum()

    # Check if we need to fetch wind speed data
    if 'wind_speed_10m' not in df.columns:
        print(f"  Warning: No wind speed data available")
        # We can't filter without wind data, but mark this
        return {
            'city': city_name,
            'total_rows': total_rows,
            'has_utci': has_utci,
            'wind_data_available': False
        }

    # Analyze wind speeds
    df_with_wind = df[df['wind_speed_10m'].notna() & df['utci_C'].notna()].copy()

    if len(df_with_wind) == 0:
        print(f"  No data with both UTCI and wind speed")
        return None

    wind_speeds = df_with_wind['wind_speed_10m']
    utci_values = df_with_wind['utci_C']

    # Count invalid by wind threshold
    high_wind_mask = wind_speeds > WIND_THRESHOLD
    high_wind_count = high_wind_mask.sum()
    high_wind_pct = high_wind_count / len(df_with_wind) * 100

    # Also check for extreme UTCI values
    extreme_utci_mask = (utci_values < -50) | (utci_values > 60)
    extreme_utci_count = extreme_utci_mask.sum()

    # Overlap between high wind and extreme UTCI
    overlap_count = (high_wind_mask & extreme_utci_mask).sum()

    print(f"  Total rows: {total_rows:,}")
    print(f"  Has UTCI: {has_utci:,}")
    print(f"  With wind data: {len(df_with_wind):,}")
    print(f"  High wind (>{WIND_THRESHOLD} m/s): {high_wind_count:,} ({high_wind_pct:.1f}%)")
    print(f"  Extreme UTCI (<-50 or >60): {extreme_utci_count:,}")
    print(f"  Overlap (high wind + extreme UTCI): {overlap_count:,}")

    # Add validation flag to DataFrame
    df['utci_valid'] = True
    df.loc[df['wind_speed_10m'] > WIND_THRESHOLD, 'utci_valid'] = False
    df.loc[(df['utci_C'] < -50) | (df['utci_C'] > 60), 'utci_valid'] = False

    valid_utci_count = (df['utci_valid'] == True).sum()

    # Save updated CSV
    output_csv = csv_path.parent / f"{csv_path.stem}_filtered.csv"
    df.to_csv(output_csv, index=False)
    print(f"  Saved filtered CSV: {output_csv.name}")

    # Create visualization for this city
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 1. Wind speed distribution
    ax = axes[0, 0]
    ax.hist(wind_speeds, bins=50, alpha=0.7, edgecolor='black')
    ax.axvline(WIND_THRESHOLD, color='red', linestyle='--', linewidth=2, label=f'Threshold ({WIND_THRESHOLD} m/s)')
    ax.set_xlabel('Wind Speed (m/s)', fontsize=11)
    ax.set_ylabel('Frequency', fontsize=11)
    ax.set_title(f'{city_name} - Wind Speed Distribution', fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 2. UTCI vs Wind Speed scatter
    ax = axes[0, 1]
    # Sample for visibility if too many points
    sample_size = min(5000, len(df_with_wind))
    sample_idx = np.random.choice(len(df_with_wind), sample_size, replace=False)
    df_sample = df_with_wind.iloc[sample_idx]

    valid_mask = df_sample['wind_speed_10m'] <= WIND_THRESHOLD
    ax.scatter(df_sample.loc[valid_mask, 'wind_speed_10m'],
              df_sample.loc[valid_mask, 'utci_C'],
              alpha=0.3, s=10, color='blue', label='Valid')
    ax.scatter(df_sample.loc[~valid_mask, 'wind_speed_10m'],
              df_sample.loc[~valid_mask, 'utci_C'],
              alpha=0.3, s=10, color='red', label='Invalid (high wind)')

    ax.axvline(WIND_THRESHOLD, color='red', linestyle='--', linewidth=2)
    ax.axhline(-50, color='orange', linestyle=':', linewidth=1.5, label='UTCI bounds')
    ax.axhline(60, color='orange', linestyle=':', linewidth=1.5)
    ax.set_xlabel('Wind Speed (m/s)', fontsize=11)
    ax.set_ylabel('UTCI (°C)', fontsize=11)
    ax.set_title(f'{city_name} - UTCI vs Wind Speed', fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 3. UTCI distribution (before/after filtering)
    ax = axes[1, 0]
    ax.hist(utci_values, bins=50, alpha=0.5, label='All data', edgecolor='black')
    valid_utci = df_with_wind.loc[~high_wind_mask, 'utci_C']
    ax.hist(valid_utci, bins=50, alpha=0.7, label='After wind filter', edgecolor='black')
    ax.axvline(-50, color='orange', linestyle=':', linewidth=1.5, label='Filter bounds')
    ax.axvline(60, color='orange', linestyle=':', linewidth=1.5)
    ax.set_xlabel('UTCI (°C)', fontsize=11)
    ax.set_ylabel('Frequency', fontsize=11)
    ax.set_title(f'{city_name} - UTCI Distribution', fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 4. Summary statistics
    ax = axes[1, 1]
    ax.axis('off')

    summary_text = f"""
{city_name} - Filtering Summary

Total observations: {total_rows:,}
With UTCI data: {has_utci:,}
With wind data: {len(df_with_wind):,}

Wind Speed Statistics:
  Mean: {wind_speeds.mean():.1f} m/s
  Median: {wind_speeds.median():.1f} m/s
  Max: {wind_speeds.max():.1f} m/s
  > {WIND_THRESHOLD} m/s: {high_wind_count:,} ({high_wind_pct:.1f}%)

UTCI Statistics (original):
  Mean: {utci_values.mean():.1f}°C
  Median: {utci_values.median():.1f}°C
  Range: [{utci_values.min():.1f}, {utci_values.max():.1f}]°C

Filtering Results:
  Invalid (high wind): {high_wind_count:,}
  Invalid (extreme UTCI): {extreme_utci_count:,}
  Overlap: {overlap_count:,}

  Valid UTCI remaining: {len(valid_utci):,}
  Percentage retained: {len(valid_utci)/len(df_with_wind)*100:.1f}%
    """

    ax.text(0.1, 0.9, summary_text, transform=ax.transAxes,
           fontsize=10, verticalalignment='top', family='monospace',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

    plt.tight_layout()
    output_file = output_dir / f"{city_name}_wind_filtering_analysis.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"  ✓ Saved analysis plot")

    return {
        'city': city_name,
        'total_rows': total_rows,
        'has_utci': has_utci,
        'with_wind': len(df_with_wind),
        'high_wind_count': high_wind_count,
        'high_wind_pct': high_wind_pct,
        'extreme_utci_count': extreme_utci_count,
        'overlap_count': overlap_count,
        'valid_remaining': len(valid_utci),
        'retention_pct': len(valid_utci)/len(df_with_wind)*100,
        'wind_data_available': True
    }

def create_summary_plot(results, output_dir):
    """Create overall summary visualization."""
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    cities = [r['city'] for r in results if r.get('wind_data_available')]
    high_wind_pcts = [r['high_wind_pct'] for r in results if r.get('wind_data_available')]
    retention_pcts = [r['retention_pct'] for r in results if r.get('wind_data_available')]

    # 1. Percentage with high wind by city
    ax = axes[0, 0]
    bars = ax.bar(cities, high_wind_pcts, edgecolor='black', alpha=0.7)
    ax.set_ylabel('% Observations with Wind > 17 m/s', fontsize=12)
    ax.set_title('High Wind Observations by City', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    # Color code by severity
    for i, (bar, pct) in enumerate(zip(bars, high_wind_pcts)):
        if pct > 10:
            bar.set_color('#e74c3c')  # Red
        elif pct > 5:
            bar.set_color('#f39c12')  # Orange
        else:
            bar.set_color('#2ecc71')  # Green

    # 2. Data retention after filtering
    ax = axes[0, 1]
    bars = ax.bar(cities, retention_pcts, edgecolor='black', alpha=0.7, color='#3498db')
    ax.axhline(95, color='green', linestyle='--', linewidth=2, label='95% threshold')
    ax.set_ylabel('% Data Retained', fontsize=12)
    ax.set_title('Data Retention After Wind Filtering', fontsize=13, fontweight='bold')
    ax.set_ylim([85, 100])
    ax.grid(True, alpha=0.3, axis='y')
    ax.legend()
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    # 3. Absolute numbers filtered
    ax = axes[1, 0]
    total_obs = [r['with_wind'] for r in results if r.get('wind_data_available')]
    filtered_obs = [r['high_wind_count'] for r in results if r.get('wind_data_available')]

    x = np.arange(len(cities))
    width = 0.35

    ax.bar(x - width/2, total_obs, width, label='Total with wind data', alpha=0.7, edgecolor='black')
    ax.bar(x + width/2, filtered_obs, width, label='Filtered (>17 m/s)', alpha=0.7, edgecolor='black', color='red')

    ax.set_ylabel('Number of Observations', fontsize=12)
    ax.set_title('Absolute Filtering Counts by City', fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(cities)
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    # 4. Summary table
    ax = axes[1, 1]
    ax.axis('off')

    total_with_wind = sum(r['with_wind'] for r in results if r.get('wind_data_available'))
    total_filtered = sum(r['high_wind_count'] for r in results if r.get('wind_data_available'))
    overall_retention = (total_with_wind - total_filtered) / total_with_wind * 100

    summary_text = f"""
GLOBAL WIND FILTERING SUMMARY

Wind Speed Threshold: {WIND_THRESHOLD} m/s
(Upper limit of UTCI valid range)

Total observations with wind data: {total_with_wind:,}
Filtered (wind > {WIND_THRESHOLD} m/s): {total_filtered:,}
Overall retention: {overall_retention:.1f}%

Most affected cities:
"""

    # Sort by high wind percentage
    sorted_results = sorted([r for r in results if r.get('wind_data_available')],
                           key=lambda x: x['high_wind_pct'], reverse=True)

    for r in sorted_results[:5]:
        summary_text += f"  {r['city']}: {r['high_wind_pct']:.1f}% filtered\n"

    summary_text += f"""

Rationale:
The UTCI polynomial approximation is only
validated for wind speeds 0.5-17 m/s.
Beyond this range, the calculation produces
unreliable results (e.g., -2500°C UTCI).

This filter removes these invalid values
while retaining {overall_retention:.1f}% of data.
    """

    ax.text(0.1, 0.9, summary_text, transform=ax.transAxes,
           fontsize=11, verticalalignment='top', family='monospace',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

    plt.tight_layout()
    output_file = output_dir / "global_wind_filtering_summary.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"\n✓ Saved global summary plot")

def main():
    results_dir = Path("data/multi_city_results")
    output_dir = Path("outputs/plots/wind_filtering_analysis")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("="*80)
    print("WIND-BASED UTCI FILTERING AND VALIDATION")
    print("="*80)
    print(f"\nWind speed threshold: {WIND_THRESHOLD} m/s (UTCI valid range limit)")
    print()

    csv_files = list(results_dir.glob("*/*_analyzed_with_utci.csv"))

    all_results = []

    for csv_file in sorted(csv_files):
        result = analyze_and_filter_city(csv_file, output_dir)
        if result:
            all_results.append(result)

    # Create overall summary
    if all_results:
        create_summary_plot(all_results, output_dir)

    print("\n" + "="*80)
    print("✓ FILTERING COMPLETE")
    print("="*80)
    print(f"\nAnalysis plots saved to: {output_dir}")
    print(f"Filtered CSVs saved with '_filtered' suffix")
    print()

if __name__ == "__main__":
    main()
