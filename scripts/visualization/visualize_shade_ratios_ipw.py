"""
Visualize shade ratios with Inverse Probability Weighting (IPW).

This script creates shade ratio visualizations that account for differential
probability of capturing people in street view images based on temperature
and time of day. Focuses on UTCI temperature only.

Outputs are saved with 'ipw_' prefix to distinguish from unweighted analyses.
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import numpy as np
from statsmodels.nonparametric.smoothers_lowess import lowess
from tqdm import tqdm
from scipy import stats
import sys

# Add parent directory to path to import helper module
sys.path.insert(0, str(Path(__file__).parent))
from calculate_person_probability_weights import prepare_data_with_weights, get_weight_statistics


def filter_extreme_values(df, temp_column='utci_C'):
    """Filter out extreme/invalid UTCI temperature values."""
    if temp_column not in df.columns:
        return df

    # UTCI valid range
    min_val, max_val = -50, 60

    mask = df[temp_column].notna() & \
           (df[temp_column] >= min_val) & \
           (df[temp_column] <= max_val)

    return df[mask].copy()


def calculate_shade_percentage_with_weights(df, weight_column=None):
    """
    Calculate shade percentage for sunny rows with people, optionally with weights.

    Args:
        df: DataFrame with person counts and shade info (expects standardized column names)
        weight_column: Column name for weights (None for unweighted)

    Returns:
        Filtered DataFrame with shade_percent column
    """
    # Use standardized column names (no _x suffix)
    # The prepare_data_with_weights function already standardizes these
    inshade_col = 'inshade_count'
    outshade_col = 'outshade_count'
    sunny_col = 'is_sunny'

    # Calculate total people
    df['total_people'] = df[inshade_col].fillna(0) + df[outshade_col].fillna(0)

    # Filter for: sunny rows, valid shade counts, and at least one person
    mask = (df[sunny_col] == True) & \
           (df[inshade_col].notna()) & \
           (df[outshade_col].notna()) & \
           (df['total_people'] > 0)

    filtered_df = df[mask].copy()

    # Calculate percent in shade
    filtered_df['shade_percent'] = (filtered_df[inshade_col] / filtered_df['total_people']) * 100

    # Add weight column if specified (default to 1.0 if not present)
    if weight_column:
        if weight_column in filtered_df.columns:
            filtered_df['weight'] = filtered_df[weight_column]
        else:
            print(f"Warning: {weight_column} not found, using uniform weights")
            filtered_df['weight'] = 1.0
    else:
        filtered_df['weight'] = 1.0

    return filtered_df


def calculate_city_weights(city_labels):
    """Calculate weights so each city has equal total weight."""
    city_labels = np.array(city_labels)
    weights = np.zeros(len(city_labels))

    unique_cities, counts = np.unique(city_labels, return_counts=True)
    city_counts = dict(zip(unique_cities, counts))

    for i, city in enumerate(city_labels):
        weights[i] = 1.0 / city_counts[city]

    return weights


def create_balanced_sample_with_weights(all_x, all_y, city_labels, ipw_weights, sample_size_per_city=None):
    """
    Create a balanced sample where each city contributes equally, preserving IPW weights.

    Args:
        all_x: Array of x values
        all_y: Array of y values
        city_labels: Array of city labels
        ipw_weights: Array of IPW weights
        sample_size_per_city: Number of samples per city

    Returns:
        Tuple of (balanced_x, balanced_y, balanced_weights)
    """
    all_x = np.array(all_x)
    all_y = np.array(all_y)
    city_labels = np.array(city_labels)
    ipw_weights = np.array(ipw_weights)

    unique_cities = np.unique(city_labels)
    city_sizes = {city: np.sum(city_labels == city) for city in unique_cities}

    if sample_size_per_city is None:
        sample_size_per_city = min(city_sizes.values())

    balanced_x = []
    balanced_y = []
    balanced_weights = []

    for city in unique_cities:
        city_indices = np.where(city_labels == city)[0]

        if len(city_indices) < sample_size_per_city:
            sampled_indices = np.random.choice(city_indices, size=sample_size_per_city, replace=True)
        else:
            sampled_indices = np.random.choice(city_indices, size=sample_size_per_city, replace=False)

        balanced_x.extend(all_x[sampled_indices])
        balanced_y.extend(all_y[sampled_indices])
        balanced_weights.extend(ipw_weights[sampled_indices])

    return np.array(balanced_x), np.array(balanced_y), np.array(balanced_weights)


def create_comparison_loess_plot(city_data, weight_column, output_file):
    """
    Create side-by-side comparison of unweighted vs IPW-weighted LOESS curves.

    Args:
        city_data: Dictionary of city dataframes
        weight_column: Which IPW weight to use ('ipw_temp', 'ipw_hour', 'ipw_combined')
        output_file: Path to save plot
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))

    temp_column = 'utci_C'
    temp_label = 'UTCI Temperature (°C)'

    # Collect all data
    all_x = []
    all_y = []
    all_weights = []
    city_labels = []

    city_count = 0
    cities_plotted = []

    for city_name, df in city_data.items():
        filtered_df = calculate_shade_percentage_with_weights(df, weight_column=weight_column)
        filtered_df = filter_extreme_values(filtered_df, temp_column)

        if len(filtered_df) > 0:
            cities_plotted.append(f'{city_name}({len(filtered_df)})')
            x = filtered_df[temp_column].values
            y = filtered_df['shade_percent'].values
            weights = filtered_df['weight'].values
            n_points = len(filtered_df)

            # Plot scatter for both panels - only show first 5 cities in legend
            show_in_legend = city_count < 5
            label = f'{city_name}: {n_points} img' if show_in_legend else None

            for ax in [ax1, ax2]:
                ax.scatter(x, y, alpha=0.3, s=15, label=label)

            all_x.extend(x)
            all_y.extend(y)
            all_weights.extend(weights)
            city_labels.extend([city_name] * n_points)
            city_count += 1

    # Convert to arrays
    all_x = np.array(all_x)
    all_y = np.array(all_y)
    all_weights = np.array(all_weights)

    # LEFT PANEL: Unweighted LOESS
    if len(all_x) > 10:
        # Create balanced sample (equal city representation)
        balanced_x, balanced_y, _ = create_balanced_sample_with_weights(
            all_x, all_y, city_labels, all_weights
        )

        # Unweighted LOESS
        smoothed = lowess(balanced_y, balanced_x, frac=0.3)
        x_smooth = smoothed[:, 0]
        y_smooth = smoothed[:, 1]

        # Bootstrap CI
        n_bootstrap = 100
        bootstrap_curves = [y_smooth]

        for _ in range(n_bootstrap - 1):
            boot_x, boot_y, _ = create_balanced_sample_with_weights(
                all_x, all_y, city_labels, all_weights
            )
            smoothed_boot = lowess(boot_y, boot_x, frac=0.3)
            y_boot_interp = np.interp(x_smooth, smoothed_boot[:, 0], smoothed_boot[:, 1],
                                     left=np.nan, right=np.nan)
            bootstrap_curves.append(y_boot_interp)

        bootstrap_curves = np.array(bootstrap_curves)
        ci_lower = np.nanpercentile(bootstrap_curves, 2.5, axis=0)
        ci_upper = np.nanpercentile(bootstrap_curves, 97.5, axis=0)

        ax1.fill_between(x_smooth, ci_lower, ci_upper, color='black', alpha=0.2, label='95% CI')
        ax1.plot(x_smooth, y_smooth, color='black', linewidth=3, alpha=0.9,
                label='Unweighted LOESS', linestyle='--')

    # RIGHT PANEL: IPW-weighted LOESS
    if len(all_x) > 10:
        # Create balanced sample with weights
        balanced_x, balanced_y, balanced_weights = create_balanced_sample_with_weights(
            all_x, all_y, city_labels, all_weights
        )

        # IPW-weighted LOESS - use weighted sampling approach
        # Repeat samples proportional to their weights
        weighted_indices = np.random.choice(
            len(balanced_x),
            size=len(balanced_x),
            replace=True,
            p=balanced_weights / balanced_weights.sum()
        )
        weighted_x = balanced_x[weighted_indices]
        weighted_y = balanced_y[weighted_indices]

        smoothed_weighted = lowess(weighted_y, weighted_x, frac=0.3)
        x_smooth_w = smoothed_weighted[:, 0]
        y_smooth_w = smoothed_weighted[:, 1]

        # Bootstrap CI for weighted
        bootstrap_curves_w = [y_smooth_w]

        for _ in range(n_bootstrap - 1):
            boot_x, boot_y, boot_weights = create_balanced_sample_with_weights(
                all_x, all_y, city_labels, all_weights
            )
            # Apply weights through resampling
            weighted_indices = np.random.choice(
                len(boot_x),
                size=len(boot_x),
                replace=True,
                p=boot_weights / boot_weights.sum()
            )
            smoothed_boot = lowess(boot_y[weighted_indices], boot_x[weighted_indices], frac=0.3)
            y_boot_interp = np.interp(x_smooth_w, smoothed_boot[:, 0], smoothed_boot[:, 1],
                                     left=np.nan, right=np.nan)
            bootstrap_curves_w.append(y_boot_interp)

        bootstrap_curves_w = np.array(bootstrap_curves_w)
        ci_lower_w = np.nanpercentile(bootstrap_curves_w, 2.5, axis=0)
        ci_upper_w = np.nanpercentile(bootstrap_curves_w, 97.5, axis=0)

        ax2.fill_between(x_smooth_w, ci_lower_w, ci_upper_w, color='darkred', alpha=0.2, label='95% CI')
        ax2.plot(x_smooth_w, y_smooth_w, color='darkred', linewidth=3, alpha=0.9,
                label='IPW-Weighted LOESS', linestyle='--')

    # Format both panels
    for ax, title in zip([ax1, ax2], ['Unweighted (Original)', f'IPW-Weighted ({weight_column})']):
        ax.set_xlabel(temp_label, fontsize=12)
        ax.set_ylabel('Percent of People in Shade (%)', fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_ylim(0, 100)
        ax.legend(fontsize=9, loc='best')
        ax.grid(True, alpha=0.3)

    # Add note about total cities
    fig.text(0.5, 0.01, f'Total cities: {city_count} | Total observations: {len(all_x):,}',
             ha='center', fontsize=10, style='italic')

    plt.suptitle(f'Shade Ratio vs {temp_label}: IPW Comparison', fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved comparison plot to {output_file}")
    print(f"  Cities plotted: {', '.join(cities_plotted)}")
    plt.close()


def create_weight_distribution_plot(city_data, output_file):
    """Create plot showing distribution of IPW weights."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Collect all weights
    all_weights = {
        'ipw_temp': [],
        'ipw_hour': [],
        'ipw_combined': []
    }

    for city_name, df in city_data.items():
        filtered_df = calculate_shade_percentage_with_weights(df, weight_column='ipw_combined')
        if len(filtered_df) > 0:
            for weight_col in all_weights.keys():
                if weight_col in filtered_df.columns:
                    all_weights[weight_col].extend(filtered_df[weight_col].values)

    # Plot distributions
    weight_labels = {
        'ipw_temp': 'Temperature-based IPW',
        'ipw_hour': 'Time-based IPW',
        'ipw_combined': 'Combined IPW'
    }

    for idx, (weight_col, label) in enumerate(weight_labels.items()):
        ax = axes.flat[idx]
        weights = np.array(all_weights[weight_col])

        if len(weights) > 0:
            # Histogram
            ax.hist(weights, bins=50, alpha=0.6, color='steelblue', edgecolor='black')

            # Add statistics
            mean_w = weights.mean()
            median_w = np.median(weights)
            ax.axvline(mean_w, color='red', linestyle='--', linewidth=2, label=f'Mean: {mean_w:.2f}')
            ax.axvline(median_w, color='orange', linestyle='--', linewidth=2, label=f'Median: {median_w:.2f}')

            ax.set_xlabel('Weight Value', fontsize=11)
            ax.set_ylabel('Frequency', fontsize=11)
            ax.set_title(label, fontsize=12, fontweight='bold')
            ax.legend()
            ax.grid(True, alpha=0.3)

    # Remove empty subplot
    axes.flat[3].axis('off')

    plt.suptitle('Distribution of Inverse Probability Weights', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved weight distribution plot to {output_file}")
    plt.close()


def create_time_of_day_comparison(city_data, weight_column, output_file):
    """Create side-by-side comparison of shade ratio vs time of day."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))

    # Collect all data
    all_x = []
    all_y = []
    all_weights = []
    city_labels = []

    city_count = 0

    for city_name, df in city_data.items():
        filtered_df = calculate_shade_percentage_with_weights(df, weight_column=weight_column)

        if len(filtered_df) > 0 and 'datetime-local' in filtered_df.columns:
            # Extract hour
            time_parts = filtered_df['datetime-local'].str.split(' ').str[1].str.split(':')
            hour_vals = time_parts.str[0].astype(int)
            minute_vals = time_parts.str[1].astype(int)
            hours = hour_vals + minute_vals / 60.0

            y = filtered_df['shade_percent'].values
            weights = filtered_df['weight'].values
            n_points = len(filtered_df)

            # Plot scatter for both panels - only show first 5 cities in legend
            show_in_legend = city_count < 5
            label = f'{city_name}: {n_points} img' if show_in_legend else None

            for ax in [ax1, ax2]:
                ax.scatter(hours, y, alpha=0.3, s=15, label=label)

            all_x.extend(hours)
            all_y.extend(y)
            all_weights.extend(weights)
            city_labels.extend([city_name] * n_points)
            city_count += 1

    all_x = np.array(all_x)
    all_y = np.array(all_y)
    all_weights = np.array(all_weights)

    # LEFT: Unweighted
    if len(all_x) > 10:
        balanced_x, balanced_y, _ = create_balanced_sample_with_weights(
            all_x, all_y, city_labels, all_weights
        )

        smoothed = lowess(balanced_y, balanced_x, frac=0.3)
        x_smooth = smoothed[:, 0]
        y_smooth = smoothed[:, 1]

        # Bootstrap
        n_bootstrap = 100
        bootstrap_curves = [y_smooth]

        for _ in range(n_bootstrap - 1):
            boot_x, boot_y, _ = create_balanced_sample_with_weights(
                all_x, all_y, city_labels, all_weights
            )
            smoothed_boot = lowess(boot_y, boot_x, frac=0.3)
            y_boot_interp = np.interp(x_smooth, smoothed_boot[:, 0], smoothed_boot[:, 1],
                                     left=np.nan, right=np.nan)
            bootstrap_curves.append(y_boot_interp)

        bootstrap_curves = np.array(bootstrap_curves)
        ci_lower = np.nanpercentile(bootstrap_curves, 2.5, axis=0)
        ci_upper = np.nanpercentile(bootstrap_curves, 97.5, axis=0)

        ax1.fill_between(x_smooth, ci_lower, ci_upper, color='black', alpha=0.2, label='95% CI')
        ax1.plot(x_smooth, y_smooth, color='black', linewidth=3, alpha=0.9,
                label='Unweighted LOESS', linestyle='--')

    # RIGHT: Weighted
    if len(all_x) > 10:
        balanced_x, balanced_y, balanced_weights = create_balanced_sample_with_weights(
            all_x, all_y, city_labels, all_weights
        )

        # Apply weights through resampling
        weighted_indices = np.random.choice(
            len(balanced_x),
            size=len(balanced_x),
            replace=True,
            p=balanced_weights / balanced_weights.sum()
        )
        weighted_x = balanced_x[weighted_indices]
        weighted_y = balanced_y[weighted_indices]

        smoothed_weighted = lowess(weighted_y, weighted_x, frac=0.3)
        x_smooth_w = smoothed_weighted[:, 0]
        y_smooth_w = smoothed_weighted[:, 1]

        # Bootstrap
        bootstrap_curves_w = [y_smooth_w]

        for _ in range(n_bootstrap - 1):
            boot_x, boot_y, boot_weights = create_balanced_sample_with_weights(
                all_x, all_y, city_labels, all_weights
            )
            # Apply weights through resampling
            weighted_indices = np.random.choice(
                len(boot_x),
                size=len(boot_x),
                replace=True,
                p=boot_weights / boot_weights.sum()
            )
            smoothed_boot = lowess(boot_y[weighted_indices], boot_x[weighted_indices], frac=0.3)
            y_boot_interp = np.interp(x_smooth_w, smoothed_boot[:, 0], smoothed_boot[:, 1],
                                     left=np.nan, right=np.nan)
            bootstrap_curves_w.append(y_boot_interp)

        bootstrap_curves_w = np.array(bootstrap_curves_w)
        ci_lower_w = np.nanpercentile(bootstrap_curves_w, 2.5, axis=0)
        ci_upper_w = np.nanpercentile(bootstrap_curves_w, 97.5, axis=0)

        ax2.fill_between(x_smooth_w, ci_lower_w, ci_upper_w, color='darkred', alpha=0.2, label='95% CI')
        ax2.plot(x_smooth_w, y_smooth_w, color='darkred', linewidth=3, alpha=0.9,
                label='IPW-Weighted LOESS', linestyle='--')

    # Format
    for ax, title in zip([ax1, ax2], ['Unweighted (Original)', f'IPW-Weighted ({weight_column})']):
        ax.set_xlabel('Time of Day (Hour)', fontsize=12)
        ax.set_ylabel('Percent of People in Shade (%)', fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlim(0, 24)
        ax.set_ylim(0, 100)
        ax.legend(fontsize=9, loc='best')
        ax.grid(True, alpha=0.3)

    # Add note about total cities
    fig.text(0.5, 0.01, f'Total cities: {city_count} | Total observations: {len(all_x):,}',
             ha='center', fontsize=10, style='italic')

    plt.suptitle('Shade Ratio vs Time of Day: IPW Comparison', fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved time comparison plot to {output_file}")
    plt.close()


def load_city_data(data_dir):
    """Load all city CSV files with UTCI data - same pattern as visualize_shade_ratios.py"""
    data_dir = Path(data_dir)

    # Load files with *_with_utci.csv pattern, searching recursively
    city_files = list(data_dir.glob("**/*_with_utci.csv"))

    if len(city_files) == 0:
        print(f"Warning: No *_with_utci.csv files found in {data_dir}")

    print(f"Found {len(city_files)} city files with UTCI data")

    all_csvs = []
    city_names = []

    for csv_file in city_files:
        try:
            df = pd.read_csv(csv_file, low_memory=False)
            # Extract city name from filename (same as original script)
            city_name = csv_file.stem.replace("_with_utci", "").rsplit('_', 2)[0]
            df['city_name'] = city_name
            all_csvs.append(df)
            city_names.append(city_name)
        except Exception as e:
            print(f"Error loading {csv_file}: {e}")

    print(f"Loaded cities: {', '.join(city_names)}")

    # Prepare combined data with IPW weights
    combined_df = prepare_data_with_weights(all_csvs)

    # Print weight statistics
    get_weight_statistics(combined_df)

    # Split back into cities for plotting
    city_data = {}
    for city_name in city_names:
        city_df = combined_df[combined_df['city_name'] == city_name].copy()
        if len(city_df) > 0:
            city_data[city_name] = city_df

    return city_data


def main():
    import argparse
    parser = argparse.ArgumentParser(description='IPW shade ratio analysis for metro SVI data')
    parser.add_argument('--data-dir', type=str,
                        default='data/processed/city_estimate_outcomes',
                        help='Directory containing *_with_utci.csv files (searched recursively)')
    parser.add_argument('--output-dir', type=str,
                        default='outputs/plots/ipw_weighted',
                        help='Directory to save plots')
    args = parser.parse_args()

    data_dir = args.data_dir
    output_dir = Path(args.output_dir)

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    print("="*70)
    print("INVERSE PROBABILITY WEIGHTED SHADE RATIO ANALYSIS")
    print("="*70)
    print("\nLoading data and calculating IPW weights...")

    city_data = load_city_data(data_dir)
    print(f"\nProcessed {len(city_data)} city datasets")

    # Create plots for different weighting schemes
    weight_schemes = [
        ('ipw_temp', 'Temperature-based IPW'),
        ('ipw_hour', 'Time-based IPW'),
        ('ipw_combined', 'Combined IPW')
    ]

    print("\nGenerating IPW comparison plots...")

    # Weight distribution plot
    create_weight_distribution_plot(
        city_data,
        output_dir / 'ipw_weight_distributions.png'
    )

    # Temperature comparison plots
    for weight_col, weight_name in tqdm(weight_schemes, desc="UTCI comparisons"):
        create_comparison_loess_plot(
            city_data,
            weight_col,
            output_dir / f'ipw_utci_comparison_{weight_col}.png'
        )

    # Time of day comparison plots
    for weight_col, weight_name in tqdm(weight_schemes, desc="Time comparisons"):
        create_time_of_day_comparison(
            city_data,
            weight_col,
            output_dir / f'ipw_timeofday_comparison_{weight_col}.png'
        )

    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)
    print(f"\nAll plots saved to: {output_dir}")
    print("\nGenerated files:")
    for f in sorted(output_dir.glob("*.png")):
        print(f"  - {f.name}")


if __name__ == "__main__":
    main()
