# ABOUTME: Plots true p(walk | temperature) accounting for trip suppression.
# ABOUTME: Shows walk trip rate per person-day, not just mode share among trips taken.

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path
import argparse


def create_p_walk_plots(df, output_dir):
    """
    Create plots showing true p(walk | temp).

    Args:
        df: DataFrame with temperature statistics
        output_dir: Directory to save plots
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Filter to reasonable temperatures and sample sizes
    df_plot = df[(df['temp_bin'] >= -15) & (df['temp_bin'] <= 40) &
                  (df['n_person_days'] >= 100)].copy()

    sns.set_style("whitegrid")

    # Plot 1: Three measures on same plot
    fig, ax = plt.subplots(figsize=(14, 8))

    # Plot all three measures
    ax.plot(df_plot['temp_bin'], df_plot['walk_trips_per_person_day'],
            marker='o', markersize=10, linewidth=3, label='Walk trips per person-day\n(True p(walk|temp))',
            color='darkgreen', alpha=0.8)

    ax.plot(df_plot['temp_bin'], df_plot['trips_per_person_day'],
            marker='s', markersize=8, linewidth=2, label='Total trips per person-day\n(p(any trip|temp))',
            color='steelblue', alpha=0.7, linestyle='--')

    # Add walk share on secondary y-axis
    ax2 = ax.twinx()
    ax2.plot(df_plot['temp_bin'], df_plot['walk_share_given_trip'] * 100,
             marker='^', markersize=8, linewidth=2, label='Walk share among trips\n(p(walk|trip,temp))',
             color='orange', alpha=0.7, linestyle=':')

    ax.set_xlabel('UTCI Temperature (°C)', fontsize=14, fontweight='bold')
    ax.set_ylabel('Trips per Person-Day', fontsize=13, fontweight='bold')
    ax2.set_ylabel('Walk Share Among Trips (%)', fontsize=13, fontweight='bold', color='orange')
    ax2.tick_params(axis='y', labelcolor='orange')

    ax.set_title('True p(walk | temperature)\nAccounting for Trip Suppression and Mode Choice',
                 fontsize=16, fontweight='bold', pad=20)

    # Combine legends
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=11,
              framealpha=0.9)

    ax.grid(True, alpha=0.3)
    ax.set_ylim(bottom=0)
    ax2.set_ylim(bottom=0, top=100)

    # Add annotation box
    total_person_days = df_plot['n_person_days'].sum()
    total_walk_trips = df_plot['walk_trips_sum'].sum()
    total_trips = df_plot['total_trips_sum'].sum()

    ax.text(0.98, 0.05,
            f'Total person-days: {total_person_days:,}\n'
            f'Total trips: {total_trips:,}\n'
            f'Walk trips: {total_walk_trips:,}\n'
            f'Overall walk rate: {total_walk_trips/total_person_days:.2f} trips/person-day',
            transform=ax.transAxes, fontsize=10, verticalalignment='bottom',
            horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    plt.tight_layout()
    plt.savefig(output_dir / 'p_walk_given_temp_combined.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("  Created: p_walk_given_temp_combined.png")

    # Plot 2: Focus on walk trips per person-day (the key metric)
    fig, ax = plt.subplots(figsize=(12, 7))

    scatter = ax.scatter(df_plot['temp_bin'], df_plot['walk_trips_per_person_day'],
                         s=df_plot['n_person_days'] / 50,
                         c=df_plot['walk_trips_per_person_day'],
                         cmap='RdYlGn',
                         edgecolors='black',
                         linewidth=1.5,
                         alpha=0.7)

    # Add trend line
    z = np.polyfit(df_plot['temp_bin'], df_plot['walk_trips_per_person_day'], 2)
    p = np.poly1d(z)
    x_smooth = np.linspace(df_plot['temp_bin'].min(), df_plot['temp_bin'].max(), 100)
    ax.plot(x_smooth, p(x_smooth), "r--", alpha=0.8, linewidth=3, label='Trend (quadratic)')

    # Add horizontal line at mean
    mean_rate = (df_plot['walk_trips_sum'].sum() / df_plot['n_person_days'].sum())
    ax.axhline(mean_rate, color='gray', linestyle=':', linewidth=2,
               label=f'Overall mean: {mean_rate:.2f}', alpha=0.7)

    ax.set_xlabel('UTCI Temperature (°C)', fontsize=14, fontweight='bold')
    ax.set_ylabel('Walk Trips per Person-Day', fontsize=14, fontweight='bold')
    ax.set_title('True p(walk | temperature)\n' +
                 'Expected walk trips per person-day at each temperature',
                 fontsize=15, fontweight='bold', pad=15)

    ax.legend(loc='upper left', fontsize=12, framealpha=0.9)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(bottom=0)

    # Colorbar
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Walk Trips/Person-Day', fontsize=11)

    # Add text
    ax.text(0.02, 0.98,
            f'Total person-days: {total_person_days:,}\n'
            f'Total walk trips: {total_walk_trips:,}\n'
            f'Overall rate: {mean_rate:.2f} walk trips/person-day\n\n'
            f'Point size ∝ sample size',
            transform=ax.transAxes, fontsize=10, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))

    plt.tight_layout()
    plt.savefig(output_dir / 'p_walk_given_temp_focus.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("  Created: p_walk_given_temp_focus.png")

    # Plot 3: Decomposition - showing the two effects
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 12), sharex=True)

    # Panel 1: Trip rate (suppression effect)
    ax1.plot(df_plot['temp_bin'], df_plot['trips_per_person_day'],
             marker='s', markersize=8, linewidth=2.5, color='steelblue')
    ax1.fill_between(df_plot['temp_bin'], 0, df_plot['trips_per_person_day'],
                      alpha=0.3, color='steelblue')
    ax1.axhline(df_plot['trips_per_person_day'].mean(), color='gray',
                linestyle=':', linewidth=2, alpha=0.7)
    ax1.set_ylabel('Total Trips/Person-Day', fontsize=12, fontweight='bold')
    ax1.set_title('A. Trip Suppression Effect\n(Do people travel less at extreme temperatures?)',
                  fontsize=12, fontweight='bold', pad=10)
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(bottom=0)

    # Panel 2: Walk share among trips (mode choice effect)
    ax2.plot(df_plot['temp_bin'], df_plot['walk_share_given_trip'] * 100,
             marker='^', markersize=8, linewidth=2.5, color='orange')
    ax2.fill_between(df_plot['temp_bin'], 0, df_plot['walk_share_given_trip'] * 100,
                      alpha=0.3, color='orange')
    ax2.axhline((df_plot['walk_share_given_trip'] * 100).mean(), color='gray',
                linestyle=':', linewidth=2, alpha=0.7)
    ax2.set_ylabel('Walk Share (%)', fontsize=12, fontweight='bold')
    ax2.set_title('B. Mode Choice Effect\n(When people travel, do they choose to walk?)',
                  fontsize=12, fontweight='bold', pad=10)
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim(bottom=0, top=100)

    # Panel 3: Combined effect (walk trips per person-day)
    ax3.plot(df_plot['temp_bin'], df_plot['walk_trips_per_person_day'],
             marker='o', markersize=10, linewidth=3, color='darkgreen')
    ax3.fill_between(df_plot['temp_bin'], 0, df_plot['walk_trips_per_person_day'],
                      alpha=0.3, color='darkgreen')
    ax3.axhline(mean_rate, color='gray', linestyle=':', linewidth=2, alpha=0.7)
    ax3.set_xlabel('UTCI Temperature (°C)', fontsize=13, fontweight='bold')
    ax3.set_ylabel('Walk Trips/Person-Day', fontsize=12, fontweight='bold')
    ax3.set_title('C. Combined Effect = A × B\n(True p(walk | temperature))',
                  fontsize=12, fontweight='bold', pad=10)
    ax3.grid(True, alpha=0.3)
    ax3.set_ylim(bottom=0)

    plt.suptitle('Decomposing Temperature Effects on Walking',
                 fontsize=15, fontweight='bold', y=0.995)
    plt.tight_layout()
    plt.savefig(output_dir / 'p_walk_given_temp_decomposition.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("  Created: p_walk_given_temp_decomposition.png")

    # Print summary stats
    print("\n" + "="*70)
    print("SUMMARY STATISTICS")
    print("="*70)
    print(f"\nOverall walk trip rate: {mean_rate:.3f} walk trips per person-day")
    print(f"Overall total trip rate: {df_plot['trips_per_person_day'].mean():.2f} trips per person-day")
    print(f"Overall walk share: {100*mean_rate/df_plot['trips_per_person_day'].mean():.1f}%")

    print("\nBy temperature range:")
    temp_ranges = [
        (-15, 0, "Cold (<0°C)"),
        (0, 15, "Cool (0-15°C)"),
        (15, 25, "Mild (15-25°C)"),
        (25, 40, "Warm (>25°C)")
    ]

    for tmin, tmax, label in temp_ranges:
        mask = (df_plot['temp_bin'] >= tmin) & (df_plot['temp_bin'] < tmax)
        if mask.sum() > 0:
            subset = df_plot[mask]
            walk_rate = subset['walk_trips_sum'].sum() / subset['n_person_days'].sum()
            trip_rate = subset['trips_per_person_day'].mean()
            walk_share = 100 * walk_rate / trip_rate if trip_rate > 0 else 0
            print(f"\n{label}:")
            print(f"  Walk trips/person-day: {walk_rate:.3f}")
            print(f"  Total trips/person-day: {trip_rate:.2f}")
            print(f"  Walk share: {walk_share:.1f}%")

    print("="*70)


def main():
    parser = argparse.ArgumentParser(
        description='Plot true p(walk | temperature) accounting for trip suppression'
    )
    parser.add_argument(
        '--input',
        type=str,
        default='data/transit_surveys/processed/p_walk_given_temp_final.csv',
        help='Path to p(walk|temp) statistics CSV'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='outputs/p_walk_temp_plots',
        help='Directory to save plots'
    )

    args = parser.parse_args()

    project_root = Path(__file__).parent.parent.parent
    input_path = project_root / args.input
    output_dir = project_root / args.output_dir

    print("="*70)
    print("TRUE p(walk | temperature) PLOTS")
    print("="*70)
    print(f"\nLoading data from {input_path}")

    df = pd.read_csv(input_path)
    print(f"  Loaded {len(df)} temperature bins")

    print("\nCreating plots...")
    create_p_walk_plots(df, output_dir)

    print(f"\n{'='*70}")
    print(f"COMPLETE - Plots saved to {output_dir}")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
