# ABOUTME: Create scatter plots of walking trips vs temperature for metro surveys.
# ABOUTME: Generates plots by city and overall showing pedestrian mode choice patterns.

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import logging
import argparse


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


def plot_walking_vs_temperature(df, output_dir, logger):
    """
    Create scatter plots of walking mode share vs temperature.

    Creates:
    1. Overall plot (all cities combined)
    2. Individual plots by city (for cities with >500 trips)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Creating scatter plots...")

    # Overall plot
    logger.info("\nCreating overall plot (all cities)...")
    create_scatter_plot(
        df=df,
        title="Walking Mode Share vs Temperature (All Metro Surveys)",
        output_path=output_dir / "walking_vs_temperature_overall.png",
        logger=logger
    )

    # By city
    logger.info("\nCreating plots by city...")
    survey_counts = df['survey'].value_counts()

    for survey_name, count in survey_counts.items():
        if count < 500:  # Skip surveys with too few trips
            logger.info(f"  Skipping {survey_name} (only {count} trips)")
            continue

        logger.info(f"  Creating plot for {survey_name} ({count:,} trips)...")
        survey_df = df[df['survey'] == survey_name]

        create_scatter_plot(
            df=survey_df,
            title=f"Walking Mode Share vs Temperature - {survey_name}",
            output_path=output_dir / f"walking_vs_temperature_{survey_name.replace('/', '_')}.png",
            logger=logger
        )

    logger.info(f"\nPlots saved to: {output_dir}")


def create_scatter_plot(df, title, output_path, logger, bin_width=2):
    """
    Create a scatter plot of walking mode share vs temperature.

    Args:
        df: DataFrame with utci_C, walk_only, contains_walk columns
        title: Plot title
        output_path: Output file path
        logger: Logger instance
        bin_width: Temperature bin width in Celsius
    """
    # Filter to valid UTCI values
    valid_df = df[df['utci_C'].notna()].copy()

    if len(valid_df) == 0:
        logger.warning(f"  No valid UTCI data for plot: {title}")
        return

    # Bin temperatures
    min_temp = np.floor(valid_df['utci_C'].min())
    max_temp = np.ceil(valid_df['utci_C'].max())
    bins = np.arange(min_temp, max_temp + bin_width, bin_width)
    valid_df['temp_bin'] = pd.cut(valid_df['utci_C'], bins=bins)

    # Calculate mode share by bin
    bin_stats = valid_df.groupby('temp_bin', observed=True).agg({
        'walk_only': ['sum', 'count', 'mean'],
        'contains_walk': ['sum', 'mean'],
        'utci_C': 'mean'
    }).reset_index()

    # Flatten column names
    bin_stats.columns = ['temp_bin', 'walk_only_count', 'total_trips', 'walk_only_share',
                         'contains_walk_count', 'contains_walk_share', 'avg_temp']

    # Convert to percentages
    bin_stats['walk_only_pct'] = bin_stats['walk_only_share'] * 100
    bin_stats['contains_walk_pct'] = bin_stats['contains_walk_share'] * 100

    # Create plot
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

    # Plot 1: Walk only
    scatter1 = ax1.scatter(
        bin_stats['avg_temp'],
        bin_stats['walk_only_pct'],
        s=bin_stats['total_trips'] / 10,  # Size by sample size
        alpha=0.6,
        c=bin_stats['total_trips'],
        cmap='viridis',
        edgecolors='black',
        linewidths=0.5
    )
    ax1.set_xlabel('UTCI Temperature (°C)', fontsize=12)
    ax1.set_ylabel('Walk Only Mode Share (%)', fontsize=12)
    ax1.set_title(f'{title}\n(Walk Only Trips)', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)

    # Add colorbar for sample size
    cbar1 = plt.colorbar(scatter1, ax=ax1)
    cbar1.set_label('Sample Size (trips per bin)', fontsize=10)

    # Add summary stats
    total_trips = len(valid_df)
    walk_only_overall = valid_df['walk_only'].mean() * 100
    ax1.text(0.02, 0.98,
             f'Total trips: {total_trips:,}\nOverall walk-only: {walk_only_overall:.1f}%',
             transform=ax1.transAxes,
             verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
             fontsize=10)

    # Plot 2: Contains walk
    scatter2 = ax2.scatter(
        bin_stats['avg_temp'],
        bin_stats['contains_walk_pct'],
        s=bin_stats['total_trips'] / 10,
        alpha=0.6,
        c=bin_stats['total_trips'],
        cmap='viridis',
        edgecolors='black',
        linewidths=0.5
    )
    ax2.set_xlabel('UTCI Temperature (°C)', fontsize=12)
    ax2.set_ylabel('Contains Walk Mode Share (%)', fontsize=12)
    ax2.set_title(f'{title}\n(Trips with Walking Segment)', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)

    cbar2 = plt.colorbar(scatter2, ax=ax2)
    cbar2.set_label('Sample Size (trips per bin)', fontsize=10)

    # Add summary stats
    contains_walk_overall = valid_df['contains_walk'].mean() * 100
    ax2.text(0.02, 0.98,
             f'Total trips: {total_trips:,}\nOverall with walk: {contains_walk_overall:.1f}%',
             transform=ax2.transAxes,
             verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
             fontsize=10)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    logger.info(f"    Saved: {output_path.name}")


def main():
    parser = argparse.ArgumentParser(
        description='Visualize metro survey walking patterns vs temperature'
    )
    parser.add_argument(
        '--input',
        type=str,
        required=True,
        help='Path to metro surveys with UTCI CSV'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='results/metro_surveys',
        help='Output directory for plots'
    )
    args = parser.parse_args()

    logger = setup_logging()

    logger.info("="*70)
    logger.info("METRO SURVEY VISUALIZATION")
    logger.info("="*70)

    # Load data
    logger.info(f"\nLoading data from {args.input}...")
    df = pd.read_csv(args.input)
    logger.info(f"  Loaded {len(df):,} trips")

    # Ensure datetime is parsed
    if 'datetime' in df.columns:
        df['datetime'] = pd.to_datetime(df['datetime'])

    # Summary statistics
    logger.info("\nDataset summary:")
    logger.info(f"  Surveys: {df['survey'].nunique()}")
    logger.info(f"  Date range: {df['datetime'].min()} to {df['datetime'].max()}")
    logger.info(f"  Walking trips: {df['walk_only'].sum():,} ({100*df['walk_only'].mean():.1f}%)")
    logger.info(f"  Trips with walk: {df['contains_walk'].sum():,} ({100*df['contains_walk'].mean():.1f}%)")

    valid_utci = df['utci_C'].notna().sum()
    logger.info(f"  Valid UTCI: {valid_utci:,} ({100*valid_utci/len(df):.1f}%)")

    if valid_utci > 0:
        logger.info(f"  UTCI range: {df['utci_C'].min():.1f}°C to {df['utci_C'].max():.1f}°C")

    # Create plots
    plot_walking_vs_temperature(df, args.output_dir, logger)

    logger.info("\n" + "="*70)
    logger.info("VISUALIZATION COMPLETE")
    logger.info("="*70)


if __name__ == '__main__':
    main()
