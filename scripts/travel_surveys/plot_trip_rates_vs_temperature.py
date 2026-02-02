# ABOUTME: Plots trip rates (trips per person-day) vs temperature to detect trip suppression.
# ABOUTME: Shows how people may avoid traveling altogether in extreme temperatures.

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path
import argparse

def create_trip_rate_plots(df, output_dir):
    """
    Create plots showing trip rates vs temperature.

    Args:
        df: DataFrame with person-day data
        output_dir: Directory to save plots
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Remove outliers in trip count for better visualization
    df_valid = df[df['total_trips'] <= 30].copy()  # Remove extreme outliers

    # Create temperature bins (every 3 degrees)
    df_valid['temp_bin'] = (df_valid['utci_C'] // 3) * 3 + 1.5

    # Calculate statistics by temperature bin
    trip_stats = df_valid.groupby('temp_bin').agg({
        'total_trips': ['mean', 'median', 'std', 'count'],
        'walk_only': 'sum',
        'contains_walk': 'sum'
    }).reset_index()

    trip_stats.columns = ['temp_bin', 'mean_trips', 'median_trips', 'std_trips', 'n_person_days',
                          'total_walk_only', 'total_contains_walk']

    # Calculate walking rates
    trip_stats['walk_only_rate'] = trip_stats['total_walk_only'] / (trip_stats['mean_trips'] * trip_stats['n_person_days'])
    trip_stats['contains_walk_rate'] = trip_stats['total_contains_walk'] / (trip_stats['mean_trips'] * trip_stats['n_person_days'])

    # Filter bins with at least 50 person-days
    trip_stats = trip_stats[trip_stats['n_person_days'] >= 50].copy()

    # Set style
    sns.set_style("whitegrid")

    # Plot 1: Mean trips per person-day vs temperature
    fig, ax = plt.subplots(figsize=(12, 7))

    scatter = ax.scatter(
        trip_stats['temp_bin'],
        trip_stats['mean_trips'],
        s=trip_stats['n_person_days'] / 5,  # Size proportional to sample
        alpha=0.6,
        c=trip_stats['mean_trips'],
        cmap='viridis',
        edgecolors='black',
        linewidth=0.5
    )

    # Add trend line
    z = np.polyfit(trip_stats['temp_bin'], trip_stats['mean_trips'], 2)
    p = np.poly1d(z)
    x_smooth = np.linspace(trip_stats['temp_bin'].min(), trip_stats['temp_bin'].max(), 100)
    ax.plot(x_smooth, p(x_smooth), "r--", alpha=0.8, linewidth=2, label='Trend (polynomial)')

    # Add horizontal line at overall mean
    overall_mean = df_valid['total_trips'].mean()
    ax.axhline(overall_mean, color='gray', linestyle=':', linewidth=2,
               label=f'Overall mean: {overall_mean:.2f} trips/person-day', alpha=0.7)

    ax.set_xlabel('UTCI Temperature (°C)', fontsize=13, fontweight='bold')
    ax.set_ylabel('Mean Trips per Person-Day', fontsize=13, fontweight='bold')
    ax.set_title('Trip Rate vs Temperature\n(Are people staying home in extreme temperatures?)',
                 fontsize=15, fontweight='bold')
    ax.legend(loc='best', fontsize=11)
    ax.grid(True, alpha=0.3)

    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Mean Trips/Day', fontsize=11)

    # Add text with summary
    total_person_days = len(df_valid)
    ax.text(0.02, 0.98,
            f'Total person-days: {total_person_days:,}\n'
            f'Mean trips/day: {overall_mean:.2f}\n'
            f'Median trips/day: {df_valid["total_trips"].median():.0f}',
            transform=ax.transAxes, fontsize=11, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.7))

    plt.tight_layout()
    plt.savefig(output_dir / 'trip_rate_vs_temperature.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  Created: trip_rate_vs_temperature.png")

    # Plot 2: Combined - Trip rate AND walk rate
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)

    # Top panel: Trip rate
    ax1.scatter(trip_stats['temp_bin'], trip_stats['mean_trips'],
                s=trip_stats['n_person_days'] / 5, alpha=0.6,
                c='steelblue', edgecolors='black', linewidth=0.5)
    z1 = np.polyfit(trip_stats['temp_bin'], trip_stats['mean_trips'], 2)
    p1 = np.poly1d(z1)
    ax1.plot(x_smooth, p1(x_smooth), "r--", alpha=0.8, linewidth=2)
    ax1.axhline(overall_mean, color='gray', linestyle=':', linewidth=2, alpha=0.7)
    ax1.set_ylabel('Trips per Person-Day', fontsize=12, fontweight='bold')
    ax1.set_title('Trip Suppression and Walking Mode Choice vs Temperature',
                  fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.text(0.02, 0.98, 'A. Overall trip rate (all modes)',
             transform=ax1.transAxes, fontsize=11, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))

    # Bottom panel: Walk-only rate
    ax2.scatter(trip_stats['temp_bin'], trip_stats['walk_only_rate'],
                s=trip_stats['n_person_days'] / 5, alpha=0.6,
                c='green', edgecolors='black', linewidth=0.5)
    z2 = np.polyfit(trip_stats['temp_bin'], trip_stats['walk_only_rate'], 2)
    p2 = np.poly1d(z2)
    ax2.plot(x_smooth, p2(x_smooth), "r--", alpha=0.8, linewidth=2)
    ax2.set_xlabel('UTCI Temperature (°C)', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Walk-Only Trip Rate', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.text(0.02, 0.98, 'B. Proportion of walk-only trips',
             transform=ax2.transAxes, fontsize=11, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.7))

    plt.tight_layout()
    plt.savefig(output_dir / 'trip_rate_and_walk_rate_vs_temperature.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  Created: trip_rate_and_walk_rate_vs_temperature.png")

    # Plot 3: Distribution of trips per person-day by temperature category
    fig, ax = plt.subplots(figsize=(12, 7))

    # Create temperature categories
    df_valid['temp_category'] = pd.cut(df_valid['utci_C'],
                                        bins=[-40, 0, 10, 20, 30, 55],
                                        labels=['<0°C\n(Cold)', '0-10°C\n(Cool)',
                                                '10-20°C\n(Mild)', '20-30°C\n(Warm)',
                                                '>30°C\n(Hot)'])

    # Box plot
    df_valid.boxplot(column='total_trips', by='temp_category', ax=ax, patch_artist=True)
    ax.set_xlabel('Temperature Category', fontsize=13, fontweight='bold')
    ax.set_ylabel('Trips per Person-Day', fontsize=13, fontweight='bold')
    ax.set_title('Distribution of Trip Rates by Temperature Category',
                 fontsize=14, fontweight='bold')
    plt.suptitle('')  # Remove auto-generated title
    ax.grid(True, alpha=0.3, axis='y')

    # Add sample sizes
    category_counts = df_valid.groupby('temp_category', observed=True).size()
    for i, (cat, count) in enumerate(category_counts.items()):
        ax.text(i + 1, ax.get_ylim()[1] * 0.95, f'n={count:,}',
                ha='center', va='top', fontsize=9,
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))

    plt.tight_layout()
    plt.savefig(output_dir / 'trip_rate_distribution_by_temp_category.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  Created: trip_rate_distribution_by_temp_category.png")

    # Plot 4: Absolute walking trips per person-day (not just proportion)
    fig, ax = plt.subplots(figsize=(12, 7))

    # Calculate absolute walk trips per person-day
    trip_stats['walk_trips_per_day'] = trip_stats['total_walk_only'] / trip_stats['n_person_days']

    scatter = ax.scatter(
        trip_stats['temp_bin'],
        trip_stats['walk_trips_per_day'],
        s=trip_stats['n_person_days'] / 5,
        alpha=0.6,
        c=trip_stats['walk_trips_per_day'],
        cmap='RdYlGn',
        edgecolors='black',
        linewidth=0.5
    )

    # Add trend line
    z = np.polyfit(trip_stats['temp_bin'], trip_stats['walk_trips_per_day'], 2)
    p = np.poly1d(z)
    ax.plot(x_smooth, p(x_smooth), "r--", alpha=0.8, linewidth=2, label='Trend')

    ax.set_xlabel('UTCI Temperature (°C)', fontsize=13, fontweight='bold')
    ax.set_ylabel('Walk-Only Trips per Person-Day', fontsize=13, fontweight='bold')
    ax.set_title('Absolute Walking Trip Rate vs Temperature\n(Accounts for both mode choice AND trip suppression)',
                 fontsize=14, fontweight='bold')
    ax.legend(loc='best', fontsize=11)
    ax.grid(True, alpha=0.3)

    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Walk Trips/Person-Day', fontsize=11)

    # Add text
    total_walk_trips = df_valid['walk_only'].sum()
    overall_walk_rate = total_walk_trips / len(df_valid)
    ax.text(0.02, 0.98,
            f'Total walk-only trips: {total_walk_trips:,}\n'
            f'Walk trips/person-day: {overall_walk_rate:.3f}\n'
            f'Walk trips as % of all trips: {100*overall_walk_rate/overall_mean:.1f}%',
            transform=ax.transAxes, fontsize=11, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.7))

    plt.tight_layout()
    plt.savefig(output_dir / 'absolute_walk_trips_vs_temperature.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  Created: absolute_walk_trips_vs_temperature.png")

    # Print summary statistics
    print("\n" + "="*70)
    print("SUMMARY STATISTICS")
    print("="*70)
    print(f"\nOverall trip rate: {overall_mean:.2f} trips/person-day")
    print(f"Overall walk rate: {overall_walk_rate:.3f} walk trips/person-day")
    print(f"Walk trips as % of all trips: {100*overall_walk_rate/overall_mean:.1f}%")

    print("\nTrip rates by temperature category:")
    temp_cat_stats = df_valid.groupby('temp_category', observed=True).agg({
        'total_trips': ['mean', 'median'],
        'walk_only': 'sum'
    })
    temp_cat_stats['person_days'] = df_valid.groupby('temp_category', observed=True).size()
    temp_cat_stats['walk_per_day'] = temp_cat_stats[('walk_only', 'sum')] / temp_cat_stats['person_days']
    print(temp_cat_stats)

    print("="*70)


def main():
    parser = argparse.ArgumentParser(
        description='Plot trip rates vs temperature to detect trip suppression'
    )
    parser.add_argument(
        '--input',
        type=str,
        default='data/transit_surveys/processed/person_day_trip_rates.csv',
        help='Path to person-day trip rates CSV'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='outputs/trip_rate_plots',
        help='Directory to save plots'
    )

    args = parser.parse_args()

    # Setup paths
    project_root = Path(__file__).parent.parent.parent
    input_path = project_root / args.input
    output_dir = project_root / args.output_dir

    print("="*70)
    print("TRIP RATE VS TEMPERATURE ANALYSIS")
    print("="*70)
    print(f"\nLoading data from {input_path}")

    # Load data
    df = pd.read_csv(input_path)
    print(f"  Loaded {len(df):,} person-days")
    print(f"  Temperature range: {df['utci_C'].min():.1f}°C to {df['utci_C'].max():.1f}°C")
    print(f"  Mean trips per person-day: {df['total_trips'].mean():.2f}")

    # Create plots
    print("\nCreating plots...")
    create_trip_rate_plots(df, output_dir)

    print(f"\n{'='*70}")
    print(f"COMPLETE - Plots saved to {output_dir}")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
