# ABOUTME: Visualizes how pedestrian mode choice varies with temperature/UTCI.
# ABOUTME: Creates plots showing walking and pedestrian trip rates across temperature bins.

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path
import argparse
import logging


def setup_logging():
    """Configure logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)


def bin_temperature(df, temp_col='utci_C', bin_width=5):
    """
    Bin temperature into categories for analysis.

    Args:
        df: DataFrame with temperature data
        temp_col: Column name for temperature
        bin_width: Width of temperature bins in degrees C

    Returns:
        DataFrame with added temp_bin column
    """
    # Create bins
    temp_min = np.floor(df[temp_col].min() / bin_width) * bin_width
    temp_max = np.ceil(df[temp_col].max() / bin_width) * bin_width
    bins = np.arange(temp_min, temp_max + bin_width, bin_width)

    # Bin the data
    df['temp_bin'] = pd.cut(df[temp_col], bins=bins, right=False)
    df['temp_bin_center'] = df['temp_bin'].apply(lambda x: x.mid if pd.notna(x) else np.nan)

    return df


def calculate_mode_shares(df, logger):
    """
    Calculate pedestrian/walking mode shares by temperature bin.

    Returns dict with DataFrames for each mode type.
    """
    logger.info("Calculating mode shares by temperature...")

    # Remove trips with missing UTCI
    df_valid = df[df['utci_C'].notna()].copy()
    logger.info(f"  {len(df_valid):,} trips with valid UTCI data")

    # Group by temperature bin
    grouped = df_valid.groupby('temp_bin_center')

    # Calculate shares
    results = {
        'full_walk': grouped['is_full_walk'].agg(['sum', 'count', 'mean']).reset_index(),
        'contains_walk': grouped['contains_walk'].agg(['sum', 'count', 'mean']).reset_index(),
        'full_pedestrian': grouped['is_full_pedestrian'].agg(['sum', 'count', 'mean']).reset_index(),
        'contains_pedestrian': grouped['contains_pedestrian'].agg(['sum', 'count', 'mean']).reset_index(),
    }

    # Rename columns for clarity
    for key, df_result in results.items():
        df_result.columns = ['temp_C', 'n_mode', 'n_total', 'mode_share']
        logger.info(f"  {key}: {len(df_result)} temperature bins")

    return results


def plot_mode_share_vs_temperature(mode_shares, output_dir, logger):
    """Create plots showing mode share vs temperature."""
    logger.info("Creating plots...")

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Pedestrian Mode Choice vs Temperature (UTCI)', fontsize=16, y=0.995)

    plot_configs = [
        ('full_walk', 'Full Walk Trips', axes[0, 0]),
        ('contains_walk', 'Trips Containing Walk', axes[0, 1]),
        ('full_pedestrian', 'Full Pedestrian Trips (Walk/Bike/E-scooter)', axes[1, 0]),
        ('contains_pedestrian', 'Trips Containing Pedestrian Modes', axes[1, 1]),
    ]

    for mode_key, title, ax in plot_configs:
        data = mode_shares[mode_key]

        # Filter bins with at least 10 trips for reliability
        data_filtered = data[data['n_total'] >= 10].copy()

        if len(data_filtered) == 0:
            ax.text(0.5, 0.5, 'Insufficient data', ha='center', va='center')
            ax.set_title(title)
            continue

        # Main plot - mode share
        ax.plot(data_filtered['temp_C'], data_filtered['mode_share'] * 100,
                marker='o', linewidth=2, markersize=6, label='Mode share')

        # Add shaded region for sample size (darker = more trips)
        sizes = data_filtered['n_total']
        size_normalized = (sizes - sizes.min()) / (sizes.max() - sizes.min() + 1)

        for i in range(len(data_filtered) - 1):
            x1, x2 = data_filtered.iloc[i]['temp_C'], data_filtered.iloc[i+1]['temp_C']
            y1, y2 = data_filtered.iloc[i]['mode_share'] * 100, data_filtered.iloc[i+1]['mode_share'] * 100
            alpha = 0.1 + 0.2 * size_normalized.iloc[i]
            ax.fill_between([x1, x2], 0, max(y1, y2), alpha=alpha, color='blue')

        ax.set_xlabel('UTCI Temperature (°C)', fontsize=11)
        ax.set_ylabel('Mode Share (%)', fontsize=11)
        ax.set_title(title, fontsize=12, pad=10)
        ax.grid(True, alpha=0.3)
        ax.set_ylim(bottom=0)

        # Add sample size text
        total_trips = data_filtered['n_total'].sum()
        mode_trips = data_filtered['n_mode'].sum()
        overall_share = mode_trips / total_trips * 100 if total_trips > 0 else 0
        ax.text(0.02, 0.98, f'n={total_trips:,} trips\nOverall: {overall_share:.1f}%',
                transform=ax.transAxes, va='top', ha='left',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8),
                fontsize=9)

    plt.tight_layout()

    # Save plot
    output_path = output_dir / 'pedestrian_mode_vs_temperature.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    logger.info(f"  Saved plot to {output_path}")
    plt.close()


def plot_detailed_temperature_distribution(df, output_dir, logger):
    """Create detailed temperature distribution plots."""
    logger.info("Creating temperature distribution plots...")

    df_valid = df[df['utci_C'].notna()].copy()

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Temperature Distribution by Mode Type', fontsize=16, y=0.995)

    plot_configs = [
        ('is_full_walk', 'Full Walk vs Other', axes[0, 0]),
        ('contains_walk', 'Contains Walk vs Other', axes[0, 1]),
        ('is_full_pedestrian', 'Full Pedestrian vs Other', axes[1, 0]),
        ('contains_pedestrian', 'Contains Pedestrian vs Other', axes[1, 1]),
    ]

    for mode_col, title, ax in plot_configs:
        # Split data by mode
        mode_trips = df_valid[df_valid[mode_col] == True]['utci_C']
        other_trips = df_valid[df_valid[mode_col] == False]['utci_C']

        # Plot distributions
        if len(mode_trips) > 0:
            ax.hist(mode_trips, bins=30, alpha=0.6, label=f'Mode trips (n={len(mode_trips):,})',
                   color='green', density=True)
        if len(other_trips) > 0:
            ax.hist(other_trips, bins=30, alpha=0.6, label=f'Other trips (n={len(other_trips):,})',
                   color='gray', density=True)

        ax.set_xlabel('UTCI Temperature (°C)', fontsize=11)
        ax.set_ylabel('Density', fontsize=11)
        ax.set_title(title, fontsize=12, pad=10)
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)

        # Add mean lines
        if len(mode_trips) > 0:
            ax.axvline(mode_trips.mean(), color='green', linestyle='--', linewidth=2,
                      label=f'Mode mean: {mode_trips.mean():.1f}°C')
        if len(other_trips) > 0:
            ax.axvline(other_trips.mean(), color='gray', linestyle='--', linewidth=2,
                      label=f'Other mean: {other_trips.mean():.1f}°C')

    plt.tight_layout()

    output_path = output_dir / 'temperature_distribution_by_mode.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    logger.info(f"  Saved plot to {output_path}")
    plt.close()


def print_summary_statistics(df, logger):
    """Print summary statistics about mode choice and temperature."""
    logger.info("\n" + "="*60)
    logger.info("SUMMARY STATISTICS")
    logger.info("="*60)

    df_valid = df[df['utci_C'].notna()].copy()

    logger.info(f"\nTotal trips: {len(df):,}")
    logger.info(f"Trips with UTCI: {len(df_valid):,} ({100*len(df_valid)/len(df):.1f}%)")

    logger.info(f"\nTemperature (UTCI) range: {df_valid['utci_C'].min():.1f}°C to {df_valid['utci_C'].max():.1f}°C")
    logger.info(f"Mean temperature: {df_valid['utci_C'].mean():.1f}°C")
    logger.info(f"Median temperature: {df_valid['utci_C'].median():.1f}°C")

    mode_types = [
        ('is_full_walk', 'Full walk'),
        ('contains_walk', 'Contains walk'),
        ('is_full_pedestrian', 'Full pedestrian'),
        ('contains_pedestrian', 'Contains pedestrian'),
    ]

    for mode_col, mode_name in mode_types:
        mode_trips = df_valid[df_valid[mode_col] == True]
        other_trips = df_valid[df_valid[mode_col] == False]

        logger.info(f"\n{mode_name}:")
        logger.info(f"  Count: {len(mode_trips):,} ({100*len(mode_trips)/len(df_valid):.1f}%)")

        if len(mode_trips) > 0:
            logger.info(f"  Mean temp: {mode_trips['utci_C'].mean():.1f}°C")
            logger.info(f"  Median temp: {mode_trips['utci_C'].median():.1f}°C")

            if len(other_trips) > 0:
                diff = mode_trips['utci_C'].mean() - other_trips['utci_C'].mean()
                logger.info(f"  Temp difference vs other modes: {diff:+.1f}°C")

    logger.info("="*60)


def main():
    parser = argparse.ArgumentParser(
        description='Visualize pedestrian mode choice vs temperature'
    )
    parser.add_argument(
        '--input',
        type=str,
        default='data/transit_surveys/processed/nhts_2017_standardized_with_utci.csv',
        help='Path to trips CSV with UTCI data'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='outputs/travel_surveys',
        help='Output directory for plots'
    )
    parser.add_argument(
        '--bin-width',
        type=float,
        default=5.0,
        help='Temperature bin width in degrees C (default: 5)'
    )

    args = parser.parse_args()
    logger = setup_logging()

    # Setup paths
    project_root = Path(__file__).parent.parent.parent
    input_path = project_root / args.input
    output_dir = project_root / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    logger.info(f"Loading data from {input_path}...")
    df = pd.read_csv(input_path)
    logger.info(f"  Loaded {len(df):,} trips")

    # Check for UTCI column
    if 'utci_C' not in df.columns:
        logger.error("Error: Input file does not contain UTCI data (utci_C column missing)")
        logger.error("Please run add_utci.py first to add thermal comfort data")
        return

    # Bin temperature
    logger.info("Binning temperature data...")
    df = bin_temperature(df, temp_col='utci_C', bin_width=args.bin_width)

    # Calculate mode shares
    mode_shares = calculate_mode_shares(df, logger)

    # Create plots
    plot_mode_share_vs_temperature(mode_shares, output_dir, logger)
    plot_detailed_temperature_distribution(df, output_dir, logger)

    # Print statistics
    print_summary_statistics(df, logger)

    logger.info(f"\nAll outputs saved to {output_dir}")


if __name__ == '__main__':
    main()
