# ABOUTME: Plots pedestrian mode choice vs UTCI temperature for transit surveys.
# ABOUTME: Creates scatter plots for walk-only and partial-walk trips, overall and by municipality.

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import argparse
from pathlib import Path
import numpy as np

def create_choice_plots(df, output_dir, groupby_col=None, group_name=None):
    """
    Create scatter plots of pedestrian choice vs UTCI.

    Args:
        df: DataFrame with trip data
        output_dir: Directory to save plots
        groupby_col: Optional column to group by (e.g., 'survey', 'county')
        group_name: Name of the specific group being plotted
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Prepare data - keep only rows with valid UTCI
    df_valid = df[df['utci_C'].notna()].copy()

    # Create bins for aggregation (every 2 degrees)
    df_valid['utci_bin'] = (df_valid['utci_C'] // 2) * 2 + 1  # Center of 2-degree bins

    # Calculate choice rates by UTCI bin
    walk_only_by_utci = df_valid.groupby('utci_bin').agg({
        'walk_only': ['sum', 'count', 'mean']
    }).reset_index()
    walk_only_by_utci.columns = ['utci_bin', 'walk_only_count', 'total_count', 'walk_only_rate']

    contains_walk_by_utci = df_valid.groupby('utci_bin').agg({
        'contains_walk': ['sum', 'count', 'mean']
    }).reset_index()
    contains_walk_by_utci.columns = ['utci_bin', 'contains_walk_count', 'total_count', 'contains_walk_rate']

    # Set style
    sns.set_style("whitegrid")

    # Create filename prefix
    prefix = f"{group_name}_" if group_name else "overall_"

    # Plot 1: Walk-only trips
    fig, ax = plt.subplots(figsize=(10, 6))

    # Scatter plot with size proportional to count
    scatter = ax.scatter(
        walk_only_by_utci['utci_bin'],
        walk_only_by_utci['walk_only_rate'],
        s=walk_only_by_utci['total_count'],
        alpha=0.6,
        c=walk_only_by_utci['walk_only_rate'],
        cmap='RdYlBu_r',
        edgecolors='black',
        linewidth=0.5
    )

    # Add trend line
    z = np.polyfit(walk_only_by_utci['utci_bin'], walk_only_by_utci['walk_only_rate'], 2)
    p = np.poly1d(z)
    x_smooth = np.linspace(walk_only_by_utci['utci_bin'].min(),
                           walk_only_by_utci['utci_bin'].max(), 100)
    ax.plot(x_smooth, p(x_smooth), "r--", alpha=0.8, linewidth=2, label='Trend (polynomial)')

    ax.set_xlabel('UTCI Temperature (°C)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Proportion of Walk-Only Trips', fontsize=12, fontweight='bold')

    title = 'Walk-Only Trip Choice vs UTCI Temperature'
    if group_name:
        title += f'\n{group_name}'
    ax.set_title(title, fontsize=14, fontweight='bold')

    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)

    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Walk-Only Rate', fontsize=10)

    # Add text with total counts
    total_trips = len(df_valid)
    walk_only_trips = df_valid['walk_only'].sum()
    ax.text(0.02, 0.98, f'Total trips: {total_trips:,}\nWalk-only: {walk_only_trips:,} ({100*walk_only_trips/total_trips:.1f}%)',
            transform=ax.transAxes, fontsize=10, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    plt.savefig(output_dir / f'{prefix}walk_only_vs_utci.png', dpi=300, bbox_inches='tight')
    plt.close()

    # Plot 2: Partial-walk trips (contains walk)
    fig, ax = plt.subplots(figsize=(10, 6))

    scatter = ax.scatter(
        contains_walk_by_utci['utci_bin'],
        contains_walk_by_utci['contains_walk_rate'],
        s=contains_walk_by_utci['total_count'],
        alpha=0.6,
        c=contains_walk_by_utci['contains_walk_rate'],
        cmap='RdYlBu_r',
        edgecolors='black',
        linewidth=0.5
    )

    # Add trend line
    z = np.polyfit(contains_walk_by_utci['utci_bin'], contains_walk_by_utci['contains_walk_rate'], 2)
    p = np.poly1d(z)
    x_smooth = np.linspace(contains_walk_by_utci['utci_bin'].min(),
                           contains_walk_by_utci['utci_bin'].max(), 100)
    ax.plot(x_smooth, p(x_smooth), "r--", alpha=0.8, linewidth=2, label='Trend (polynomial)')

    ax.set_xlabel('UTCI Temperature (°C)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Proportion of Trips Containing Walk', fontsize=12, fontweight='bold')

    title = 'Partial-Walk Trip Choice vs UTCI Temperature'
    if group_name:
        title += f'\n{group_name}'
    ax.set_title(title, fontsize=14, fontweight='bold')

    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)

    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Contains Walk Rate', fontsize=10)

    # Add text with total counts
    contains_walk_trips = df_valid['contains_walk'].sum()
    ax.text(0.02, 0.98, f'Total trips: {total_trips:,}\nContains walk: {contains_walk_trips:,} ({100*contains_walk_trips/total_trips:.1f}%)',
            transform=ax.transAxes, fontsize=10, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    plt.savefig(output_dir / f'{prefix}contains_walk_vs_utci.png', dpi=300, bbox_inches='tight')
    plt.close()

    print(f"  Created plots for {group_name or 'overall'}")


def main():
    parser = argparse.ArgumentParser(
        description='Plot pedestrian choice vs UTCI temperature'
    )
    parser.add_argument(
        '--input',
        type=str,
        default='data/transit_surveys/processed/metro_surveys_standardized_with_utci.csv',
        help='Path to annotated trips CSV'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='outputs/pedestrian_choice_plots',
        help='Directory to save plots'
    )
    parser.add_argument(
        '--groupby',
        type=str,
        choices=['survey', 'county', 'survey_year', None],
        default=None,
        help='Group plots by this column (optional)'
    )

    args = parser.parse_args()

    # Setup paths
    project_root = Path(__file__).parent.parent.parent
    input_path = project_root / args.input
    output_dir = project_root / args.output_dir

    print("="*70)
    print("PEDESTRIAN CHOICE VS UTCI PLOTS")
    print("="*70)
    print(f"\nLoading data from {input_path}")

    # Load data
    df = pd.read_csv(input_path, low_memory=False)
    print(f"  Loaded {len(df):,} trips")
    print(f"  Valid UTCI: {df['utci_C'].notna().sum():,} ({100*df['utci_C'].notna().sum()/len(df):.1f}%)")

    # Create overall plots
    print("\nCreating overall plots...")
    create_choice_plots(df, output_dir, group_name=None)

    # Create grouped plots if requested
    if args.groupby:
        print(f"\nCreating plots by {args.groupby}...")
        groups = df[args.groupby].unique()
        print(f"  Found {len(groups)} unique {args.groupby} values")

        for group in sorted(groups):
            if pd.isna(group):
                continue
            group_df = df[df[args.groupby] == group]
            if len(group_df) < 10:  # Skip groups with too few samples
                print(f"  Skipping {group} (only {len(group_df)} trips)")
                continue

            group_dir = output_dir / args.groupby
            create_choice_plots(group_df, group_dir, groupby_col=args.groupby, group_name=str(group))

    print(f"\n{'='*70}")
    print(f"COMPLETE - Plots saved to {output_dir}")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
