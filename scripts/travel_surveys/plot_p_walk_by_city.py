# ABOUTME: Plots walk trip rates vs temperature separately for each metro area.
# ABOUTME: Shows city-specific temperature sensitivity of walking behavior.

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path
import argparse


def get_metro_area(survey_name):
    """Extract metro area from survey name (remove year suffix)."""
    return survey_name.rsplit('-', 1)[0]


def calculate_city_walk_rates(person_days_df):
    """
    Calculate walk trip rates by temperature for each metro area.

    Args:
        person_days_df: DataFrame with person-day trip rates

    Returns:
        Dictionary mapping metro area to temperature statistics DataFrame
    """
    # Add metro area column
    person_days_df['metro_area'] = person_days_df['survey'].apply(get_metro_area)

    # Create temperature bins (5°C)
    person_days_df['temp_bin'] = (person_days_df['utci_C'] // 5) * 5 + 2.5

    # Calculate statistics by metro area and temperature
    city_stats = {}

    for metro_area in person_days_df['metro_area'].unique():
        metro_df = person_days_df[person_days_df['metro_area'] == metro_area].copy()

        # Aggregate by temperature bin
        temp_stats = metro_df.groupby('temp_bin').agg({
            'total_trips': ['sum', 'mean'],
            'walk_only': ['sum', 'mean']
        }).reset_index()

        temp_stats.columns = ['temp_bin', 'total_trips_sum', 'trips_per_person_day',
                              'walk_trips_sum', 'walk_trips_per_person_day']

        # Add person-day counts and walk share
        temp_stats['n_person_days'] = metro_df.groupby('temp_bin').size().values
        temp_stats['walk_share'] = temp_stats['walk_trips_sum'] / temp_stats['total_trips_sum']

        # Filter bins with at least 50 person-days
        temp_stats = temp_stats[temp_stats['n_person_days'] >= 50].copy()

        if len(temp_stats) >= 3:  # Need at least 3 temperature bins
            city_stats[metro_area] = temp_stats

    return city_stats


def create_city_grid_plot(city_stats, output_dir):
    """
    Create grid of small multiples showing each city's walk rate vs temp.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cities = sorted(city_stats.keys())
    n_cities = len(cities)

    # Create grid layout
    n_cols = 5
    n_rows = int(np.ceil(n_cities / n_cols))

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(20, 4*n_rows))
    axes = axes.flatten()

    for idx, metro_area in enumerate(cities):
        ax = axes[idx]
        stats = city_stats[metro_area]

        # Plot walk trips per person-day
        ax.scatter(stats['temp_bin'], stats['walk_trips_per_person_day'],
                   s=stats['n_person_days'] / 10,  # Size by sample
                   alpha=0.6, color='darkgreen', edgecolors='black', linewidth=0.5)

        # Add trend line if enough points
        if len(stats) >= 4:
            z = np.polyfit(stats['temp_bin'], stats['walk_trips_per_person_day'], 2)
            p = np.poly1d(z)
            x_smooth = np.linspace(stats['temp_bin'].min(), stats['temp_bin'].max(), 50)
            ax.plot(x_smooth, p(x_smooth), 'r--', alpha=0.7, linewidth=1.5)

        # Formatting
        ax.set_title(metro_area.replace('-', ' ').title(), fontsize=10, fontweight='bold')
        ax.set_xlabel('UTCI (°C)', fontsize=8)
        ax.set_ylabel('Walk trips/person-day', fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_ylim(bottom=0)

        # Add sample size annotation
        total_person_days = stats['n_person_days'].sum()
        ax.text(0.95, 0.95, f'n={total_person_days:,}',
                transform=ax.transAxes, fontsize=7,
                verticalalignment='top', horizontalalignment='right',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.7, pad=0.3))

    # Hide unused subplots
    for idx in range(n_cities, len(axes)):
        axes[idx].axis('off')

    plt.suptitle('Walk Trip Rate vs Temperature by Metro Area', fontsize=16, fontweight='bold', y=0.995)
    plt.tight_layout()
    plt.savefig(output_dir / 'walk_rate_by_city_grid.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  Created: walk_rate_by_city_grid.png")


def create_city_overlay_plot(city_stats, output_dir):
    """
    Create overlay plot showing all cities on one axis.
    """
    output_dir = Path(output_dir)

    fig, ax = plt.subplots(figsize=(14, 9))

    # Use colormap for cities
    colors = plt.cm.tab20(np.linspace(0, 1, len(city_stats)))

    for idx, (metro_area, stats) in enumerate(sorted(city_stats.items())):
        color = colors[idx]

        # Plot line
        ax.plot(stats['temp_bin'], stats['walk_trips_per_person_day'],
                marker='o', markersize=6, linewidth=2, alpha=0.7,
                color=color, label=metro_area.replace('-', ' ').title())

    ax.set_xlabel('UTCI Temperature (°C)', fontsize=13, fontweight='bold')
    ax.set_ylabel('Walk Trips per Person-Day', fontsize=13, fontweight='bold')
    ax.set_title('Walk Trip Rate vs Temperature: City-Specific Patterns',
                 fontsize=15, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_ylim(bottom=0)

    # Legend in two columns
    ax.legend(loc='upper left', fontsize=8, ncol=2, framealpha=0.9)

    plt.tight_layout()
    plt.savefig(output_dir / 'walk_rate_by_city_overlay.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  Created: walk_rate_by_city_overlay.png")


def create_individual_city_plots(city_stats, output_dir):
    """
    Create individual detailed plot for each city.
    """
    output_dir = Path(output_dir)
    city_dir = output_dir / 'by_city'
    city_dir.mkdir(parents=True, exist_ok=True)

    for metro_area, stats in sorted(city_stats.items()):
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10), sharex=True)

        # Panel 1: Walk trips per person-day
        scatter1 = ax1.scatter(stats['temp_bin'], stats['walk_trips_per_person_day'],
                               s=stats['n_person_days'] / 5,
                               c=stats['walk_trips_per_person_day'],
                               cmap='RdYlGn',
                               edgecolors='black', linewidth=1,
                               alpha=0.7)

        # Trend line
        if len(stats) >= 4:
            z = np.polyfit(stats['temp_bin'], stats['walk_trips_per_person_day'], 2)
            p = np.poly1d(z)
            x_smooth = np.linspace(stats['temp_bin'].min(), stats['temp_bin'].max(), 100)
            ax1.plot(x_smooth, p(x_smooth), 'r--', alpha=0.8, linewidth=2, label='Trend')

        # Mean line
        mean_rate = stats['walk_trips_sum'].sum() / stats['n_person_days'].sum()
        ax1.axhline(mean_rate, color='gray', linestyle=':', linewidth=2,
                    label=f'Mean: {mean_rate:.2f}', alpha=0.7)

        ax1.set_ylabel('Walk Trips per Person-Day', fontsize=11, fontweight='bold')
        ax1.set_title(f'{metro_area.replace("-", " ").title()}\nWalk Trip Rate vs Temperature',
                      fontsize=13, fontweight='bold')
        ax1.legend(loc='upper left', fontsize=9)
        ax1.grid(True, alpha=0.3)
        ax1.set_ylim(bottom=0)

        # Colorbar
        cbar1 = plt.colorbar(scatter1, ax=ax1)
        cbar1.set_label('Walk Trips/Day', fontsize=9)

        # Panel 2: Total trips per person-day
        scatter2 = ax2.scatter(stats['temp_bin'], stats['trips_per_person_day'],
                               s=stats['n_person_days'] / 5,
                               c=stats['trips_per_person_day'],
                               cmap='Blues',
                               edgecolors='black', linewidth=1,
                               alpha=0.7)

        # Trend line
        if len(stats) >= 4:
            z = np.polyfit(stats['temp_bin'], stats['trips_per_person_day'], 2)
            p = np.poly1d(z)
            x_smooth = np.linspace(stats['temp_bin'].min(), stats['temp_bin'].max(), 100)
            ax2.plot(x_smooth, p(x_smooth), 'r--', alpha=0.8, linewidth=2, label='Trend')

        mean_trip_rate = stats['total_trips_sum'].sum() / stats['n_person_days'].sum()
        ax2.axhline(mean_trip_rate, color='gray', linestyle=':', linewidth=2,
                    label=f'Mean: {mean_trip_rate:.2f}', alpha=0.7)

        ax2.set_xlabel('UTCI Temperature (°C)', fontsize=11, fontweight='bold')
        ax2.set_ylabel('Total Trips per Person-Day', fontsize=11, fontweight='bold')
        ax2.legend(loc='upper left', fontsize=9)
        ax2.grid(True, alpha=0.3)
        ax2.set_ylim(bottom=0)

        # Colorbar
        cbar2 = plt.colorbar(scatter2, ax=ax2)
        cbar2.set_label('Total Trips/Day', fontsize=9)

        # Summary stats
        total_person_days = stats['n_person_days'].sum()
        total_walk_trips = stats['walk_trips_sum'].sum()
        total_trips = stats['total_trips_sum'].sum()
        walk_share = 100 * total_walk_trips / total_trips

        fig.text(0.99, 0.01,
                 f'Person-days: {total_person_days:,} | '
                 f'Walk trips: {total_walk_trips:,} ({walk_share:.1f}%) | '
                 f'Total trips: {total_trips:,}',
                 ha='right', va='bottom', fontsize=9,
                 bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

        plt.tight_layout()

        # Save with safe filename
        safe_name = metro_area.replace(' ', '_').replace('/', '_')
        plt.savefig(city_dir / f'{safe_name}_walk_rate.png', dpi=300, bbox_inches='tight')
        plt.close()

    print(f"  Created {len(city_stats)} individual city plots in by_city/")


def create_summary_table(city_stats, output_dir):
    """
    Create summary table of walk rates by city.
    """
    output_dir = Path(output_dir)

    summary_data = []

    for metro_area, stats in sorted(city_stats.items()):
        total_person_days = stats['n_person_days'].sum()
        total_walk_trips = stats['walk_trips_sum'].sum()
        total_trips = stats['total_trips_sum'].sum()

        mean_walk_rate = total_walk_trips / total_person_days
        mean_trip_rate = total_trips / total_person_days
        walk_share = 100 * total_walk_trips / total_trips

        temp_range = f"{stats['temp_bin'].min():.0f} to {stats['temp_bin'].max():.0f}"

        summary_data.append({
            'Metro Area': metro_area.replace('-', ' ').title(),
            'Person-Days': total_person_days,
            'Walk Trips/Day': f'{mean_walk_rate:.2f}',
            'Total Trips/Day': f'{mean_trip_rate:.2f}',
            'Walk Share (%)': f'{walk_share:.1f}',
            'Temp Range (°C)': temp_range,
            'N Temp Bins': len(stats)
        })

    summary_df = pd.DataFrame(summary_data)
    summary_df = summary_df.sort_values('Person-Days', ascending=False)

    # Save to CSV
    summary_df.to_csv(output_dir / 'city_walk_rate_summary.csv', index=False)
    print(f"  Created: city_walk_rate_summary.csv")

    # Print to console
    print("\n" + "="*80)
    print("SUMMARY: Walk Trip Rates by Metro Area")
    print("="*80)
    print(summary_df.to_string(index=False))
    print("="*80)


def main():
    parser = argparse.ArgumentParser(
        description='Plot walk trip rates vs temperature by metro area'
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
        default='outputs/walk_rate_by_city',
        help='Directory to save plots'
    )

    args = parser.parse_args()

    project_root = Path(__file__).parent.parent.parent
    input_path = project_root / args.input
    output_dir = project_root / args.output_dir

    print("="*80)
    print("WALK TRIP RATE BY METRO AREA")
    print("="*80)
    print(f"\nLoading data from {input_path}")

    # Load person-day data
    df = pd.read_csv(input_path, low_memory=False)
    print(f"  Loaded {len(df):,} person-days")

    # Calculate city-specific statistics
    print("\nCalculating city-specific walk rates...")
    city_stats = calculate_city_walk_rates(df)
    print(f"  Found {len(city_stats)} metro areas with sufficient data")

    # Create plots
    print("\nCreating plots...")
    create_city_grid_plot(city_stats, output_dir)
    create_city_overlay_plot(city_stats, output_dir)
    create_individual_city_plots(city_stats, output_dir)
    create_summary_table(city_stats, output_dir)

    print(f"\n{'='*80}")
    print(f"COMPLETE - Plots saved to {output_dir}")
    print(f"{'='*80}")


if __name__ == '__main__':
    main()
