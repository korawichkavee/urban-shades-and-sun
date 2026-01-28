# ABOUTME: Plots pedestrian mode choice vs UTCI during commute hours (8-10am, 4-6pm).
# ABOUTME: Compares all-day patterns with commute-only patterns to understand choice differences.

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import argparse
from pathlib import Path
import numpy as np

def create_comparison_plots(df, output_dir):
    """
    Create comparison plots of pedestrian choice vs UTCI for all-day vs commute hours.

    Args:
        df: DataFrame with trip data including datetime and utci_C
        output_dir: Directory to save plots
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Extract hour from datetime
    df['hour'] = pd.to_datetime(df['datetime']).dt.hour

    # Prepare data - keep only rows with valid UTCI
    df_valid = df[df['utci_C'].notna()].copy()

    # Filter for commute hours
    df_commute = df_valid[
        ((df_valid['hour'] >= 8) & (df_valid['hour'] < 10)) |  # 8-10am
        ((df_valid['hour'] >= 16) & (df_valid['hour'] < 18))   # 4-6pm
    ].copy()

    print(f"All-day trips: {len(df_valid):,}")
    print(f"Commute hours trips: {len(df_commute):,} ({100*len(df_commute)/len(df_valid):.1f}%)")
    print(f"All-day walk rate: {100*df_valid['walk_only'].mean():.1f}%")
    print(f"Commute walk rate: {100*df_commute['walk_only'].mean():.1f}%")

    # Create bins for aggregation (every 2 degrees)
    df_valid['utci_bin'] = (df_valid['utci_C'] // 2) * 2 + 1
    df_commute['utci_bin'] = (df_commute['utci_C'] // 2) * 2 + 1

    # Calculate choice rates by UTCI bin for both datasets
    def get_rates(data):
        walk_only = data.groupby('utci_bin').agg({
            'walk_only': ['sum', 'count', 'mean']
        }).reset_index()
        walk_only.columns = ['utci_bin', 'walk_only_count', 'total_count', 'walk_only_rate']

        contains_walk = data.groupby('utci_bin').agg({
            'contains_walk': ['sum', 'count', 'mean']
        }).reset_index()
        contains_walk.columns = ['utci_bin', 'contains_walk_count', 'total_count', 'contains_walk_rate']

        return walk_only, contains_walk

    walk_only_all, contains_walk_all = get_rates(df_valid)
    walk_only_commute, contains_walk_commute = get_rates(df_commute)

    # Set style
    sns.set_style("whitegrid")

    # Plot 1: Walk-only trips comparison
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    # All-day data
    scatter1 = ax1.scatter(
        walk_only_all['utci_bin'],
        walk_only_all['walk_only_rate'],
        s=walk_only_all['total_count'] / 10,
        alpha=0.6,
        c=walk_only_all['walk_only_rate'],
        cmap='RdYlBu_r',
        edgecolors='black',
        linewidth=0.5
    )

    # Trend line for all-day
    z_all = np.polyfit(walk_only_all['utci_bin'], walk_only_all['walk_only_rate'], 2)
    p_all = np.poly1d(z_all)
    x_smooth = np.linspace(walk_only_all['utci_bin'].min(),
                          walk_only_all['utci_bin'].max(), 100)
    ax1.plot(x_smooth, p_all(x_smooth), "r--", alpha=0.8, linewidth=2,
            label=f'Trend (all-day, n={len(df_valid):,})')

    ax1.set_xlabel('UTCI Temperature (°C)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Proportion of Walk-Only Trips', fontsize=12, fontweight='bold')
    ax1.set_title('Walk-Only Trip Choice vs UTCI\nAll Day (All Hours)',
                 fontsize=14, fontweight='bold')
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(0, 1)

    # Commute hours data
    scatter2 = ax2.scatter(
        walk_only_commute['utci_bin'],
        walk_only_commute['walk_only_rate'],
        s=walk_only_commute['total_count'] / 10,
        alpha=0.6,
        c=walk_only_commute['walk_only_rate'],
        cmap='RdYlBu_r',
        edgecolors='black',
        linewidth=0.5
    )

    # Trend line for commute
    if len(walk_only_commute) > 2:
        z_commute = np.polyfit(walk_only_commute['utci_bin'],
                               walk_only_commute['walk_only_rate'], 2)
        p_commute = np.poly1d(z_commute)
        x_smooth_commute = np.linspace(walk_only_commute['utci_bin'].min(),
                                      walk_only_commute['utci_bin'].max(), 100)
        ax2.plot(x_smooth_commute, p_commute(x_smooth_commute), "b--",
                alpha=0.8, linewidth=2,
                label=f'Trend (commute, n={len(df_commute):,})')

    ax2.set_xlabel('UTCI Temperature (°C)', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Proportion of Walk-Only Trips', fontsize=12, fontweight='bold')
    ax2.set_title('Walk-Only Trip Choice vs UTCI\nCommute Hours (8-10am, 4-6pm)',
                 fontsize=14, fontweight='bold')
    ax2.legend(loc='best')
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim(0, 1)

    plt.tight_layout()
    plt.savefig(output_dir / 'walk_only_comparison_allday_vs_commute.png',
               dpi=300, bbox_inches='tight')
    print(f"Saved: {output_dir / 'walk_only_comparison_allday_vs_commute.png'}")
    plt.close()

    # Plot 2: Overlay comparison
    fig, ax = plt.subplots(figsize=(12, 8))

    # All-day scatter
    ax.scatter(
        walk_only_all['utci_bin'],
        walk_only_all['walk_only_rate'],
        s=walk_only_all['total_count'] / 10,
        alpha=0.4,
        c='blue',
        edgecolors='black',
        linewidth=0.5,
        label=f'All Day (n={len(df_valid):,})'
    )

    # Commute scatter
    ax.scatter(
        walk_only_commute['utci_bin'],
        walk_only_commute['walk_only_rate'],
        s=walk_only_commute['total_count'] / 10,
        alpha=0.6,
        c='red',
        edgecolors='black',
        linewidth=0.5,
        label=f'Commute Hours (n={len(df_commute):,})'
    )

    # Trend lines
    ax.plot(x_smooth, p_all(x_smooth), "b--", alpha=0.8, linewidth=3,
           label='Trend (all-day)')

    if len(walk_only_commute) > 2:
        ax.plot(x_smooth_commute, p_commute(x_smooth_commute), "r--",
               alpha=0.8, linewidth=3, label='Trend (commute)')

    ax.set_xlabel('UTCI Temperature (°C)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Proportion of Walk-Only Trips', fontsize=12, fontweight='bold')
    ax.set_title('Walk-Only Trip Choice vs UTCI\nComparison: All Day vs Commute Hours',
                fontsize=14, fontweight='bold')
    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 1)

    plt.tight_layout()
    plt.savefig(output_dir / 'walk_only_overlay_allday_vs_commute.png',
               dpi=300, bbox_inches='tight')
    print(f"Saved: {output_dir / 'walk_only_overlay_allday_vs_commute.png'}")
    plt.close()

    # Plot 3: Contains walk comparison
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    # All-day
    ax1.scatter(
        contains_walk_all['utci_bin'],
        contains_walk_all['contains_walk_rate'],
        s=contains_walk_all['total_count'] / 10,
        alpha=0.6,
        c=contains_walk_all['contains_walk_rate'],
        cmap='YlGn',
        edgecolors='black',
        linewidth=0.5
    )

    z_cw_all = np.polyfit(contains_walk_all['utci_bin'],
                         contains_walk_all['contains_walk_rate'], 2)
    p_cw_all = np.poly1d(z_cw_all)
    ax1.plot(x_smooth, p_cw_all(x_smooth), "g--", alpha=0.8, linewidth=2,
            label=f'Trend (all-day, n={len(df_valid):,})')

    ax1.set_xlabel('UTCI Temperature (°C)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Proportion of Trips with Walking', fontsize=12, fontweight='bold')
    ax1.set_title('Trips Containing Walk vs UTCI\nAll Day',
                 fontsize=14, fontweight='bold')
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(0, 1)

    # Commute hours
    ax2.scatter(
        contains_walk_commute['utci_bin'],
        contains_walk_commute['contains_walk_rate'],
        s=contains_walk_commute['total_count'] / 10,
        alpha=0.6,
        c=contains_walk_commute['contains_walk_rate'],
        cmap='YlGn',
        edgecolors='black',
        linewidth=0.5
    )

    if len(contains_walk_commute) > 2:
        z_cw_commute = np.polyfit(contains_walk_commute['utci_bin'],
                                  contains_walk_commute['contains_walk_rate'], 2)
        p_cw_commute = np.poly1d(z_cw_commute)
        ax2.plot(x_smooth_commute, p_cw_commute(x_smooth_commute), "darkgreen",
                linestyle='--', alpha=0.8, linewidth=2,
                label=f'Trend (commute, n={len(df_commute):,})')

    ax2.set_xlabel('UTCI Temperature (°C)', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Proportion of Trips with Walking', fontsize=12, fontweight='bold')
    ax2.set_title('Trips Containing Walk vs UTCI\nCommute Hours (8-10am, 4-6pm)',
                 fontsize=14, fontweight='bold')
    ax2.legend(loc='best')
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim(0, 1)

    plt.tight_layout()
    plt.savefig(output_dir / 'contains_walk_comparison_allday_vs_commute.png',
               dpi=300, bbox_inches='tight')
    print(f"Saved: {output_dir / 'contains_walk_comparison_allday_vs_commute.png'}")
    plt.close()


def main():
    parser = argparse.ArgumentParser(
        description='Plot pedestrian choice vs UTCI for commute hours comparison'
    )
    parser.add_argument(
        '--input',
        type=str,
        default='data/transit_surveys/processed/metro_surveys_standardized_with_utci.csv',
        help='Input CSV file with UTCI data'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='outputs/plots/commute_hours',
        help='Output directory for plots'
    )
    parser.add_argument(
        '--by-city',
        action='store_true',
        help='Generate per-city comparison plots'
    )
    parser.add_argument(
        '--min-trips',
        type=int,
        default=1000,
        help='Minimum commute trips required for per-city plots'
    )

    args = parser.parse_args()

    project_root = Path(__file__).parent.parent.parent
    input_path = project_root / args.input
    output_dir = project_root / args.output_dir

    print("="*70)
    print("PEDESTRIAN CHOICE VS UTCI - COMMUTE HOURS COMPARISON")
    print("="*70)
    print(f"\nLoading data from: {input_path}")

    df = pd.read_csv(input_path, low_memory=False)
    print(f"Loaded {len(df):,} trips")

    print("\nCreating overall comparison plots...")
    create_comparison_plots(df, output_dir)

    if args.by_city:
        print("\n" + "="*70)
        print("GENERATING PER-CITY COMPARISON PLOTS")
        print("="*70)

        # Extract hour
        df['hour'] = pd.to_datetime(df['datetime']).dt.hour

        # Filter for commute hours
        df_commute = df[
            ((df['hour'] >= 8) & (df['hour'] < 10)) |
            ((df['hour'] >= 16) & (df['hour'] < 18))
        ]

        # Get surveys with sufficient commute trips
        commute_counts = df_commute.groupby('survey').size()
        eligible_surveys = commute_counts[commute_counts >= args.min_trips].index

        print(f"\nFound {len(eligible_surveys)} surveys with >={args.min_trips} commute trips:")
        for survey in eligible_surveys:
            count = commute_counts[survey]
            print(f"  {survey}: {count:,} commute trips")

        # Generate per-city plots
        for survey in eligible_surveys:
            print(f"\nProcessing {survey}...")
            df_survey = df[df['survey'] == survey].copy()

            city_output_dir = output_dir / survey
            create_comparison_plots(df_survey, city_output_dir)

    print("\n" + "="*70)
    print("DONE")
    print("="*70)


if __name__ == '__main__':
    main()
