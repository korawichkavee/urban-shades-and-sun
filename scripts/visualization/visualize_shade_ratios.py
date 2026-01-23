# ABOUTME: Visualizes the relationship between temperature and shade percentages across cities.
# ABOUTME: Creates scatter plots showing percent of people in shade vs wet bulb and dry bulb temperatures.

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import numpy as np
from statsmodels.nonparametric.smoothers_lowess import lowess
from tqdm import tqdm
from scipy import stats

def calculate_meaningful_range(data, percentile_low=2.5, percentile_high=97.5):
    """Calculate meaningful data range based on percentiles to focus on data-rich regions."""
    data_clean = data[~np.isnan(data)]
    if len(data_clean) == 0:
        return None, None

    low = np.percentile(data_clean, percentile_low)
    high = np.percentile(data_clean, percentile_high)

    # Add 5% margin for visual comfort
    margin = (high - low) * 0.05
    return low - margin, high + margin


def create_temperature_distribution_plot(city_data, output_file):
    """Create comparison plot showing temperature distributions for all three measures."""
    fig, axes = plt.subplots(3, 1, figsize=(12, 10))

    temp_measures = [
        ('wbulb', 'Wet Bulb Temperature (°C)', axes[0]),
        ('dbulb', 'Dry Bulb Temperature (°C)', axes[1]),
        ('utci_C', 'UTCI Temperature (°C)', axes[2])
    ]

    for temp_col, temp_label, ax in temp_measures:
        all_temps = []

        for city_name, df in city_data.items():
            filtered_df = calculate_shade_percentage(df, temp_column=temp_col)
            if len(filtered_df) > 0:
                temps = filtered_df[temp_col].values
                all_temps.extend(temps)

        all_temps = np.array(all_temps)

        # Create histogram
        ax.hist(all_temps, bins=50, alpha=0.7, color='steelblue', edgecolor='black')

        # Add KDE
        kde = stats.gaussian_kde(all_temps)
        x_range = np.linspace(all_temps.min(), all_temps.max(), 200)
        ax2 = ax.twinx()
        ax2.plot(x_range, kde(x_range), 'r-', linewidth=2, label='KDE')
        ax2.set_ylabel('Density', color='r')
        ax2.tick_params(axis='y', labelcolor='r')

        # Add statistics
        mean_val = all_temps.mean()
        median_val = np.median(all_temps)
        ax.axvline(mean_val, color='green', linestyle='--', linewidth=2, label=f'Mean: {mean_val:.1f}°C')
        ax.axvline(median_val, color='orange', linestyle='--', linewidth=2, label=f'Median: {median_val:.1f}°C')

        # Labels
        ax.set_xlabel(temp_label, fontsize=11)
        ax.set_ylabel('Frequency', fontsize=11)
        ax.set_title(f'{temp_label} Distribution (n={len(all_temps):,})', fontsize=12)
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    print(f"Saved plot to {output_file}")
    plt.close()


def load_city_data(data_dir):
    """Load all city CSV files with UTCI data and return a dictionary of dataframes."""
    data_dir = Path(data_dir)
    city_data = {}

    for csv_file in data_dir.glob("*_with_utci.csv"):
        city_name = csv_file.stem.replace("_with_utci", "").rsplit('_', 2)[0]  # Extract city name
        df = pd.read_csv(csv_file)
        city_data[city_name] = df

    return city_data

def filter_extreme_values(df, temp_column):
    """Filter out extreme/invalid temperature values."""
    if temp_column not in df.columns:
        return df

    # Define reasonable ranges for each temperature type
    ranges = {
        'utci_C': (-50, 60),      # Valid UTCI range
        'wbulb': (-40, 50),        # Wet bulb range
        'dbulb': (-40, 60),        # Dry bulb range
    }

    if temp_column in ranges:
        min_val, max_val = ranges[temp_column]
        # Filter out NaN and extreme values
        mask = df[temp_column].notna() & \
               (df[temp_column] >= min_val) & \
               (df[temp_column] <= max_val)
        return df[mask].copy()

    # For unknown columns, just filter NaN
    return df[df[temp_column].notna()].copy()


def calculate_shade_percentage(df, temp_column=None):
    """Calculate the percentage of people in shade for sunny rows with people only."""
    # Determine which column names to use (with or without _x suffix)
    if 'inshade_count_x' in df.columns:
        inshade_col = 'inshade_count_x'
        outshade_col = 'outshade_count_x'
        sunny_col = 'is_sunny_x'
    else:
        inshade_col = 'inshade_count'
        outshade_col = 'outshade_count'
        sunny_col = 'is_sunny'

    # Calculate total people for each row
    df['total_people'] = df[inshade_col].fillna(0) + df[outshade_col].fillna(0)

    # Filter for: sunny rows, valid shade counts, and at least one person
    mask = (df[sunny_col] == True) & \
           (df[inshade_col].notna()) & \
           (df[outshade_col].notna()) & \
           (df['total_people'] > 0)

    filtered_df = df[mask].copy()

    # Calculate percent in shade
    filtered_df['shade_percent'] = (filtered_df[inshade_col] / filtered_df['total_people']) * 100

    # Filter extreme temperature values if temp_column specified
    if temp_column:
        filtered_df = filter_extreme_values(filtered_df, temp_column)

    return filtered_df

def prepare_all_rows_data(df, temp_column=None):
    """Prepare data including all rows with valid counts, regardless of sunny status or people count."""
    # Determine which column names to use (with or without _x suffix)
    if 'inshade_count_x' in df.columns:
        inshade_col = 'inshade_count_x'
        outshade_col = 'outshade_count_x'
    else:
        inshade_col = 'inshade_count'
        outshade_col = 'outshade_count'

    # Calculate total people for each row
    df['total_people'] = df[inshade_col].fillna(0) + df[outshade_col].fillna(0)

    # Filter only for valid counts (exclude rows with NaN/errors)
    mask = (df[inshade_col].notna()) & (df[outshade_col].notna())

    filtered_df = df[mask].copy()

    # Filter extreme temperature values if temp_column specified
    if temp_column:
        filtered_df = filter_extreme_values(filtered_df, temp_column)

    return filtered_df

def prepare_sunny_rows_data(df, temp_column=None):
    """Prepare data including only sunny rows with valid counts, regardless of people count."""
    # Determine which column names to use (with or without _x suffix)
    if 'inshade_count_x' in df.columns:
        inshade_col = 'inshade_count_x'
        outshade_col = 'outshade_count_x'
        sunny_col = 'is_sunny_x'
    else:
        inshade_col = 'inshade_count'
        outshade_col = 'outshade_count'
        sunny_col = 'is_sunny'

    # Calculate total people for each row
    df['total_people'] = df[inshade_col].fillna(0) + df[outshade_col].fillna(0)

    # Filter for: sunny rows and valid counts (any people count including 0)
    mask = (df[sunny_col] == True) & \
           (df[inshade_col].notna()) & \
           (df[outshade_col].notna())

    filtered_df = df[mask].copy()

    # Filter extreme temperature values if temp_column specified
    if temp_column:
        filtered_df = filter_extreme_values(filtered_df, temp_column)

    return filtered_df

def calculate_city_weights(city_labels):
    """Calculate weights for data points so each city has equal total weight.

    Args:
        city_labels: List or array of city labels, one per data point

    Returns:
        Array of weights where each city's total weight equals 1
    """
    city_labels = np.array(city_labels)
    weights = np.zeros(len(city_labels))

    # Count occurrences of each city
    unique_cities, counts = np.unique(city_labels, return_counts=True)
    city_counts = dict(zip(unique_cities, counts))

    # Assign weight = 1/n_city to each point from that city
    for i, city in enumerate(city_labels):
        weights[i] = 1.0 / city_counts[city]

    return weights

def create_balanced_sample(all_x, all_y, city_labels, sample_size_per_city=None):
    """Create a balanced sample where each city contributes equally.

    Args:
        all_x: Array of x values
        all_y: Array of y values
        city_labels: Array of city labels
        sample_size_per_city: Number of samples per city (default: min city size)

    Returns:
        Tuple of (balanced_x, balanced_y)
    """
    all_x = np.array(all_x)
    all_y = np.array(all_y)
    city_labels = np.array(city_labels)

    # Find unique cities and their sizes
    unique_cities = np.unique(city_labels)
    city_sizes = {city: np.sum(city_labels == city) for city in unique_cities}

    # Use minimum city size if not specified
    if sample_size_per_city is None:
        sample_size_per_city = min(city_sizes.values())

    balanced_x = []
    balanced_y = []

    for city in unique_cities:
        # Get indices for this city
        city_indices = np.where(city_labels == city)[0]

        # Sample with replacement if we need more than available
        if len(city_indices) < sample_size_per_city:
            sampled_indices = np.random.choice(city_indices, size=sample_size_per_city, replace=True)
        else:
            # Sample without replacement if we have enough
            sampled_indices = np.random.choice(city_indices, size=sample_size_per_city, replace=False)

        balanced_x.extend(all_x[sampled_indices])
        balanced_y.extend(all_y[sampled_indices])

    return np.array(balanced_x), np.array(balanced_y)

def create_temperature_plot(city_data, temp_column, temp_label, output_file):
    """Create scatter plot of shade percentage vs temperature with LOESS fit lines and confidence intervals."""
    plt.figure(figsize=(12, 8))

    for city_name, df in city_data.items():
        filtered_df = calculate_shade_percentage(df, temp_column=temp_column)

        if len(filtered_df) > 10:  # Need sufficient data points for LOESS
            x = filtered_df[temp_column].values
            y = filtered_df['shade_percent'].values
            n_points = len(filtered_df)

            # Plot scatter points
            scatter = plt.scatter(x, y, alpha=0.4, s=20)
            color = scatter.get_facecolors()[0]

            # Calculate LOESS smoothing
            smoothed = lowess(y, x, frac=0.5)
            x_smooth = smoothed[:, 0]
            y_smooth = smoothed[:, 1]

            # Calculate confidence intervals using bootstrap
            n_bootstrap = 100
            bootstrap_curves = []

            for _ in range(n_bootstrap):
                # Resample with replacement
                indices = np.random.choice(len(x), size=len(x), replace=True)
                x_boot = x[indices]
                y_boot = y[indices]

                # Calculate LOESS for this bootstrap sample
                smoothed_boot = lowess(y_boot, x_boot, frac=0.5)
                # Interpolate to match x_smooth points for consistent CI calculation
                
                #print(x_smooth)
                print(city_name)
                y_boot_interp = np.interp(x_smooth, smoothed_boot[:, 0], smoothed_boot[:, 1])
                bootstrap_curves.append(y_boot_interp)

            bootstrap_curves = np.array(bootstrap_curves)

            # Calculate 95% confidence intervals
            ci_lower = np.percentile(bootstrap_curves, 2.5, axis=0)
            ci_upper = np.percentile(bootstrap_curves, 97.5, axis=0)

            # Plot confidence interval
            plt.fill_between(x_smooth, ci_lower, ci_upper, color=color, alpha=0.2)

            # Plot LOESS line with same color as scatter points
            plt.plot(x_smooth, y_smooth, color=color, linewidth=2, alpha=0.8,
                    label=f'{city_name} (LOESS): {n_points} img')

    plt.xlabel(temp_label, fontsize=12)
    plt.ylabel('Percent of People in Shade (%)', fontsize=12)
    plt.title(f'Percent in Shade vs {temp_label} Across Cities', fontsize=14)
    plt.ylim(0, 100)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    print(f"Saved plot to {output_file}")
    plt.close()

def create_overall_loess_plot(city_data, temp_column, temp_label, output_file):
    """Create plot with overall LOESS fit across all cities combined with confidence intervals and density."""
    # Create figure with gridspec for main plot + marginal density
    fig = plt.figure(figsize=(12, 10))
    gs = fig.add_gridspec(2, 1, height_ratios=[3, 1], hspace=0.05)
    ax_main = fig.add_subplot(gs[0])
    ax_density = fig.add_subplot(gs[1], sharex=ax_main)

    # Collect all data points across cities with city labels
    all_x = []
    all_y = []
    city_labels = []

    for city_name, df in city_data.items():
        filtered_df = calculate_shade_percentage(df, temp_column=temp_column)

        if len(filtered_df) > 0:
            x = filtered_df[temp_column].values
            y = filtered_df['shade_percent'].values
            n_points = len(filtered_df)

            # Plot scatter points for this city
            ax_main.scatter(x, y, alpha=0.3, s=15, label=f'{city_name}: {n_points} img')

            # Collect for overall LOESS
            all_x.extend(x)
            all_y.extend(y)
            city_labels.extend([city_name] * n_points)

    # Calculate overall LOESS smoothing across all cities
    if len(all_x) > 10:
        all_x = np.array(all_x)
        all_y = np.array(all_y)

        # Create balanced sample so each city has equal influence
        balanced_x, balanced_y = create_balanced_sample(all_x, all_y, city_labels)

        smoothed = lowess(balanced_y, balanced_x, frac=0.3)
        x_smooth = smoothed[:, 0]
        y_smooth = smoothed[:, 1]

        # Calculate confidence intervals using balanced bootstrap
        n_bootstrap = 100
        bootstrap_curves = []

        # Add the original curve first to ensure it's within CIs
        bootstrap_curves.append(y_smooth)

        for _ in range(n_bootstrap - 1):  # -1 because we already added original
            # Create balanced bootstrap sample (each city equally represented)
            boot_x, boot_y = create_balanced_sample(all_x, all_y, city_labels)

            # Calculate LOESS for this bootstrap sample
            smoothed_boot = lowess(boot_y, boot_x, frac=0.3)

            # Only interpolate within the range of bootstrap sample to avoid extrapolation
            y_boot_interp = np.interp(x_smooth, smoothed_boot[:, 0], smoothed_boot[:, 1],
                                     left=np.nan, right=np.nan)  # Use nan outside range

            bootstrap_curves.append(y_boot_interp)

        bootstrap_curves = np.array(bootstrap_curves)

        # Calculate 95% confidence intervals, ignoring nans from extrapolation
        ci_lower = np.nanpercentile(bootstrap_curves, 2.5, axis=0)
        ci_upper = np.nanpercentile(bootstrap_curves, 97.5, axis=0)

        # Plot confidence interval on main plot
        ax_main.fill_between(x_smooth, ci_lower, ci_upper, color='black', alpha=0.2,
                            label='95% CI')

        # Plot overall LOESS line
        ax_main.plot(x_smooth, y_smooth, color='black', linewidth=3, alpha=0.9,
                    label='Overall LOESS', linestyle='--')

        # Calculate and set meaningful x-axis range
        x_min, x_max = calculate_meaningful_range(all_x)
        if x_min is not None and x_max is not None:
            ax_main.set_xlim(x_min, x_max)

        # Create density plot (histogram + KDE)
        ax_density.hist(all_x, bins=50, alpha=0.6, color='steelblue', edgecolor='black')

        # Add KDE to density plot
        if len(all_x) > 10:
            kde = stats.gaussian_kde(all_x)
            x_range = np.linspace(all_x.min(), all_x.max(), 200)
            ax_density_twin = ax_density.twinx()
            ax_density_twin.plot(x_range, kde(x_range), 'r-', linewidth=2, label='Density (KDE)')
            ax_density_twin.set_ylabel('Density', color='r', fontsize=10)
            ax_density_twin.tick_params(axis='y', labelcolor='r')

        # Add vertical lines for meaningful range on density plot
        if x_min is not None and x_max is not None:
            ax_density.axvline(x_min, color='green', linestyle='--', alpha=0.5, linewidth=1)
            ax_density.axvline(x_max, color='green', linestyle='--', alpha=0.5, linewidth=1)

    # Main plot labels
    ax_main.set_ylabel('Percent of People in Shade (%)', fontsize=12)
    ax_main.set_title(f'Overall Percent in Shade vs {temp_label}\n(Focused on 2.5th-97.5th percentile range)', fontsize=14)
    ax_main.set_ylim(0, 100)
    ax_main.legend(fontsize=9, loc='best')
    ax_main.grid(True, alpha=0.3)
    ax_main.tick_params(labelbottom=False)  # Hide x labels on main plot

    # Density plot labels
    ax_density.set_xlabel(temp_label, fontsize=12)
    ax_density.set_ylabel('Frequency', fontsize=10)
    ax_density.grid(True, alpha=0.3, axis='x')

    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved plot to {output_file}")
    plt.close()

def create_overall_time_of_day_plot(city_data, x_label, output_file):
    """Create plot showing shade percentage vs time of day across all cities with LOESS fit and confidence intervals."""
    plt.figure(figsize=(12, 8))

    # Collect all data points across cities with city labels
    all_x = []
    all_y = []
    city_labels = []

    for city_name, df in city_data.items():
        filtered_df = calculate_shade_percentage(df)

        if len(filtered_df) > 0 and 'datetime-local' in filtered_df.columns:
            # Extract hour directly from datetime string (format: YYYY-MM-DD HH:MM:SS...)
            time_parts = filtered_df['datetime-local'].str.split(' ').str[1].str.split(':')
            hour_vals = time_parts.str[0].astype(int)
            minute_vals = time_parts.str[1].astype(int)
            hours = hour_vals + minute_vals / 60.0

            y = filtered_df['shade_percent'].values
            n_points = len(filtered_df)

            # Plot scatter points for this city
            plt.scatter(hours, y, alpha=0.3, s=15, label=f'{city_name}: {n_points} img')

            # Collect for overall LOESS
            all_x.extend(hours)
            all_y.extend(y)
            city_labels.extend([city_name] * n_points)

    # Calculate overall LOESS smoothing across all cities
    if len(all_x) > 10:
        all_x = np.array(all_x)
        all_y = np.array(all_y)

        # Create balanced sample so each city has equal influence
        balanced_x, balanced_y = create_balanced_sample(all_x, all_y, city_labels)

        smoothed = lowess(balanced_y, balanced_x, frac=0.3)
        x_smooth = smoothed[:, 0]
        y_smooth = smoothed[:, 1]

        # Calculate confidence intervals using balanced bootstrap
        n_bootstrap = 100
        bootstrap_curves = []

        # Add the original curve first to ensure it's within CIs
        bootstrap_curves.append(y_smooth)

        for _ in range(n_bootstrap - 1):  # -1 because we already added original
            # Create balanced bootstrap sample (each city equally represented)
            boot_x, boot_y = create_balanced_sample(all_x, all_y, city_labels)

            # Calculate LOESS for this bootstrap sample
            smoothed_boot = lowess(boot_y, boot_x, frac=0.3)

            # Only interpolate within the range of bootstrap sample to avoid extrapolation
            y_boot_interp = np.interp(x_smooth, smoothed_boot[:, 0], smoothed_boot[:, 1],
                                     left=np.nan, right=np.nan)  # Use nan outside range

            bootstrap_curves.append(y_boot_interp)

        bootstrap_curves = np.array(bootstrap_curves)

        # Calculate 95% confidence intervals, ignoring nans from extrapolation
        ci_lower = np.nanpercentile(bootstrap_curves, 2.5, axis=0)
        ci_upper = np.nanpercentile(bootstrap_curves, 97.5, axis=0)

        # Plot confidence interval
        plt.fill_between(x_smooth, ci_lower, ci_upper, color='black', alpha=0.2,
                        label='95% CI')

        # Plot overall LOESS line
        plt.plot(x_smooth, y_smooth, color='black', linewidth=3, alpha=0.9,
                label='Overall LOESS', linestyle='--')

    plt.xlabel(x_label, fontsize=12)
    plt.ylabel('Percent of People in Shade (%)', fontsize=12)
    plt.title(f'Overall Percent in Shade vs {x_label}', fontsize=14)
    plt.xlim(0, 24)
    plt.ylim(0, 100)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    print(f"Saved plot to {output_file}")
    plt.close()

def create_people_count_vs_time_plot(city_data, x_label, output_file):
    """Create plot showing total people count vs time of day across all cities with LOESS fit and confidence intervals."""
    plt.figure(figsize=(12, 8))

    # Collect all data points across cities
    all_x = []
    all_y = []
    city_labels = []

    for city_name, df in city_data.items():
        filtered_df = calculate_shade_percentage(df)

        if len(filtered_df) > 0 and 'datetime-local' in filtered_df.columns:
            # Extract hour directly from datetime string
            time_parts = filtered_df['datetime-local'].str.split(' ').str[1].str.split(':')
            hour_vals = time_parts.str[0].astype(int)
            minute_vals = time_parts.str[1].astype(int)
            hours = hour_vals + minute_vals / 60.0

            # Get total people count
            y = filtered_df['total_people'].values
            n_points = len(filtered_df)

            # Plot scatter points for this city
            plt.scatter(hours, y, alpha=0.3, s=15, label=f'{city_name}: {n_points} img')

            # Collect for overall LOESS
            all_x.extend(hours)
            all_y.extend(y)
            city_labels.extend([city_name] * n_points)

    # Calculate overall LOESS smoothing across all cities
    if len(all_x) > 10:
        all_x = np.array(all_x)
        all_y = np.array(all_y)

        # Create balanced sample so each city has equal influence
        balanced_x, balanced_y = create_balanced_sample(all_x, all_y, city_labels)

        smoothed = lowess(balanced_y, balanced_x, frac=0.3)
        x_smooth = smoothed[:, 0]
        y_smooth = smoothed[:, 1]

        # Calculate confidence intervals using balanced bootstrap
        n_bootstrap = 100
        bootstrap_curves = []

        for _ in range(n_bootstrap):
            # Resample with replacement
            # Create balanced bootstrap sample (each city equally represented)
            boot_x, boot_y = create_balanced_sample(all_x, all_y, city_labels)


            # Calculate LOESS for this bootstrap sample
            smoothed_boot = lowess(boot_y, boot_x, frac=0.3)
            # Interpolate to match x_smooth points for consistent CI calculation
            y_boot_interp = np.interp(x_smooth, smoothed_boot[:, 0], smoothed_boot[:, 1])
            bootstrap_curves.append(y_boot_interp)

        bootstrap_curves = np.array(bootstrap_curves)

        # Calculate 95% confidence intervals
        ci_lower = np.percentile(bootstrap_curves, 2.5, axis=0)
        ci_upper = np.percentile(bootstrap_curves, 97.5, axis=0)

        # Plot confidence interval
        plt.fill_between(x_smooth, ci_lower, ci_upper, color='black', alpha=0.2,
                        label='95% CI')

        # Plot overall LOESS line
        plt.plot(x_smooth, y_smooth, color='black', linewidth=3, alpha=0.9,
                label='Overall LOESS', linestyle='--')

    plt.xlabel(x_label, fontsize=12)
    plt.ylabel('Total People Count', fontsize=12)
    plt.title(f'People Count vs {x_label}', fontsize=14)
    plt.xlim(0, 24)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    print(f"Saved plot to {output_file}")
    plt.close()

def create_people_count_vs_temp_plot(city_data, temp_column, temp_label, output_file):
    """Create plot showing total people count vs temperature across all cities with LOESS fit and confidence intervals."""
    plt.figure(figsize=(12, 8))

    # Collect all data points across cities
    all_x = []
    all_y = []
    city_labels = []

    for city_name, df in city_data.items():
        filtered_df = calculate_shade_percentage(df, temp_column=temp_column)

        if len(filtered_df) > 0 and temp_column in filtered_df.columns:
            x = filtered_df[temp_column].values
            y = filtered_df['total_people'].values
            n_points = len(filtered_df)

            # Plot scatter points for this city
            plt.scatter(x, y, alpha=0.3, s=15, label=f'{city_name}: {n_points} img')

            # Collect for overall LOESS
            all_x.extend(x)
            all_y.extend(y)
            city_labels.extend([city_name] * n_points)

    # Calculate overall LOESS smoothing across all cities
    if len(all_x) > 10:
        all_x = np.array(all_x)
        all_y = np.array(all_y)

        # Create balanced sample so each city has equal influence
        balanced_x, balanced_y = create_balanced_sample(all_x, all_y, city_labels)

        smoothed = lowess(balanced_y, balanced_x, frac=0.3)
        x_smooth = smoothed[:, 0]
        y_smooth = smoothed[:, 1]

        # Calculate confidence intervals using balanced bootstrap
        n_bootstrap = 100
        bootstrap_curves = []

        for _ in range(n_bootstrap):
            # Resample with replacement
            # Create balanced bootstrap sample (each city equally represented)
            boot_x, boot_y = create_balanced_sample(all_x, all_y, city_labels)


            # Calculate LOESS for this bootstrap sample
            smoothed_boot = lowess(boot_y, boot_x, frac=0.3)
            # Interpolate to match x_smooth points for consistent CI calculation
            y_boot_interp = np.interp(x_smooth, smoothed_boot[:, 0], smoothed_boot[:, 1])
            bootstrap_curves.append(y_boot_interp)

        bootstrap_curves = np.array(bootstrap_curves)

        # Calculate 95% confidence intervals
        ci_lower = np.percentile(bootstrap_curves, 2.5, axis=0)
        ci_upper = np.percentile(bootstrap_curves, 97.5, axis=0)

        # Plot confidence interval
        plt.fill_between(x_smooth, ci_lower, ci_upper, color='black', alpha=0.2,
                        label='95% CI')

        # Plot overall LOESS line
        plt.plot(x_smooth, y_smooth, color='black', linewidth=3, alpha=0.9,
                label='Overall LOESS', linestyle='--')

    plt.xlabel(temp_label, fontsize=12)
    plt.ylabel('Total People Count', fontsize=12)
    plt.title(f'People Count vs {temp_label}', fontsize=14)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    print(f"Saved plot to {output_file}")
    plt.close()

def create_all_rows_people_vs_time_plot(city_data, x_label, output_file):
    """Create plot showing people count vs time of day for all rows (including non-sunny and zero-people rows)."""
    plt.figure(figsize=(12, 8))

    # Collect all data points across cities
    all_x = []
    all_y = []
    city_labels = []

    for city_name, df in city_data.items():
        filtered_df = prepare_all_rows_data(df)

        if len(filtered_df) > 0 and 'datetime-local' in filtered_df.columns:
            # Extract hour directly from datetime string
            time_parts = filtered_df['datetime-local'].str.split(' ').str[1].str.split(':')
            hour_vals = time_parts.str[0].astype(int)
            minute_vals = time_parts.str[1].astype(int)
            hours = hour_vals + minute_vals / 60.0

            # Get total people count
            y = filtered_df['total_people'].values
            n_points = len(filtered_df)

            # Plot scatter points for this city
            plt.scatter(hours, y, alpha=0.3, s=15, label=f'{city_name}: {n_points} img')

            # Collect for overall LOESS
            all_x.extend(hours)
            all_y.extend(y)
            city_labels.extend([city_name] * n_points)

    # Calculate overall LOESS smoothing across all cities
    if len(all_x) > 10:
        all_x = np.array(all_x)
        all_y = np.array(all_y)

        # Create balanced sample so each city has equal influence
        balanced_x, balanced_y = create_balanced_sample(all_x, all_y, city_labels)

        smoothed = lowess(balanced_y, balanced_x, frac=0.3)
        x_smooth = smoothed[:, 0]
        y_smooth = smoothed[:, 1]

        # Calculate confidence intervals using balanced bootstrap
        n_bootstrap = 100
        bootstrap_curves = []

        for _ in range(n_bootstrap):
            # Resample with replacement
            # Create balanced bootstrap sample (each city equally represented)
            boot_x, boot_y = create_balanced_sample(all_x, all_y, city_labels)


            # Calculate LOESS for this bootstrap sample
            smoothed_boot = lowess(boot_y, boot_x, frac=0.3)
            # Interpolate to match x_smooth points for consistent CI calculation
            y_boot_interp = np.interp(x_smooth, smoothed_boot[:, 0], smoothed_boot[:, 1])
            bootstrap_curves.append(y_boot_interp)

        bootstrap_curves = np.array(bootstrap_curves)

        # Calculate 95% confidence intervals
        ci_lower = np.percentile(bootstrap_curves, 2.5, axis=0)
        ci_upper = np.percentile(bootstrap_curves, 97.5, axis=0)

        # Plot confidence interval
        plt.fill_between(x_smooth, ci_lower, ci_upper, color='black', alpha=0.2,
                        label='95% CI')

        # Plot overall LOESS line
        plt.plot(x_smooth, y_smooth, color='black', linewidth=3, alpha=0.9,
                label='Overall LOESS', linestyle='--')

    plt.xlabel(x_label, fontsize=12)
    plt.ylabel('Total People Count', fontsize=12)
    plt.title(f'People Count vs {x_label} (All Rows)', fontsize=14)
    plt.xlim(0, 24)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    print(f"Saved plot to {output_file}")
    plt.close()

def create_all_rows_people_vs_temp_plot(city_data, temp_column, temp_label, output_file):
    """Create plot showing people count vs temperature for all rows (including non-sunny and zero-people rows)."""
    plt.figure(figsize=(12, 8))

    # Collect all data points across cities
    all_x = []
    all_y = []
    city_labels = []

    for city_name, df in city_data.items():
        filtered_df = prepare_all_rows_data(df, temp_column=temp_column)

        if len(filtered_df) > 0 and temp_column in filtered_df.columns:
            x = filtered_df[temp_column].values
            y = filtered_df['total_people'].values
            n_points = len(filtered_df)

            # Plot scatter points for this city
            plt.scatter(x, y, alpha=0.3, s=15, label=f'{city_name}: {n_points} img')

            # Collect for overall LOESS
            all_x.extend(x)
            all_y.extend(y)
            city_labels.extend([city_name] * n_points)

    # Calculate overall LOESS smoothing across all cities
    if len(all_x) > 10:
        all_x = np.array(all_x)
        all_y = np.array(all_y)

        # Create balanced sample so each city has equal influence
        balanced_x, balanced_y = create_balanced_sample(all_x, all_y, city_labels)

        smoothed = lowess(balanced_y, balanced_x, frac=0.3)
        x_smooth = smoothed[:, 0]
        y_smooth = smoothed[:, 1]

        # Calculate confidence intervals using balanced bootstrap
        n_bootstrap = 100
        bootstrap_curves = []

        for _ in range(n_bootstrap):
            # Resample with replacement
            # Create balanced bootstrap sample (each city equally represented)
            boot_x, boot_y = create_balanced_sample(all_x, all_y, city_labels)


            # Calculate LOESS for this bootstrap sample
            smoothed_boot = lowess(boot_y, boot_x, frac=0.3)
            # Interpolate to match x_smooth points for consistent CI calculation
            y_boot_interp = np.interp(x_smooth, smoothed_boot[:, 0], smoothed_boot[:, 1])
            bootstrap_curves.append(y_boot_interp)

        bootstrap_curves = np.array(bootstrap_curves)

        # Calculate 95% confidence intervals
        ci_lower = np.percentile(bootstrap_curves, 2.5, axis=0)
        ci_upper = np.percentile(bootstrap_curves, 97.5, axis=0)

        # Plot confidence interval
        plt.fill_between(x_smooth, ci_lower, ci_upper, color='black', alpha=0.2,
                        label='95% CI')

        # Plot overall LOESS line
        plt.plot(x_smooth, y_smooth, color='black', linewidth=3, alpha=0.9,
                label='Overall LOESS', linestyle='--')

    plt.xlabel(temp_label, fontsize=12)
    plt.ylabel('Total People Count', fontsize=12)
    plt.title(f'People Count vs {temp_label} (All Rows)', fontsize=14)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    print(f"Saved plot to {output_file}")
    plt.close()

def create_sunny_people_vs_time_plot(city_data, x_label, output_file):
    """Create plot showing people count vs time of day for sunny rows only (including zero-people rows)."""
    plt.figure(figsize=(12, 8))

    # Collect all data points across cities
    all_x = []
    all_y = []
    city_labels = []

    for city_name, df in city_data.items():
        filtered_df = prepare_sunny_rows_data(df)

        if len(filtered_df) > 0 and 'datetime-local' in filtered_df.columns:
            # Extract hour directly from datetime string
            time_parts = filtered_df['datetime-local'].str.split(' ').str[1].str.split(':')
            hour_vals = time_parts.str[0].astype(int)
            minute_vals = time_parts.str[1].astype(int)
            hours = hour_vals + minute_vals / 60.0

            # Get total people count
            y = filtered_df['total_people'].values
            n_points = len(filtered_df)

            # Plot scatter points for this city
            plt.scatter(hours, y, alpha=0.3, s=15, label=f'{city_name}: {n_points} img')

            # Collect for overall LOESS
            all_x.extend(hours)
            all_y.extend(y)
            city_labels.extend([city_name] * n_points)

    # Calculate overall LOESS smoothing across all cities
    if len(all_x) > 10:
        all_x = np.array(all_x)
        all_y = np.array(all_y)

        # Create balanced sample so each city has equal influence
        balanced_x, balanced_y = create_balanced_sample(all_x, all_y, city_labels)

        smoothed = lowess(balanced_y, balanced_x, frac=0.3)
        x_smooth = smoothed[:, 0]
        y_smooth = smoothed[:, 1]

        # Calculate confidence intervals using balanced bootstrap
        n_bootstrap = 100
        bootstrap_curves = []

        for _ in range(n_bootstrap):
            # Resample with replacement
            # Create balanced bootstrap sample (each city equally represented)
            boot_x, boot_y = create_balanced_sample(all_x, all_y, city_labels)


            # Calculate LOESS for this bootstrap sample
            smoothed_boot = lowess(boot_y, boot_x, frac=0.3)
            # Interpolate to match x_smooth points for consistent CI calculation
            y_boot_interp = np.interp(x_smooth, smoothed_boot[:, 0], smoothed_boot[:, 1])
            bootstrap_curves.append(y_boot_interp)

        bootstrap_curves = np.array(bootstrap_curves)

        # Calculate 95% confidence intervals
        ci_lower = np.percentile(bootstrap_curves, 2.5, axis=0)
        ci_upper = np.percentile(bootstrap_curves, 97.5, axis=0)

        # Plot confidence interval
        plt.fill_between(x_smooth, ci_lower, ci_upper, color='black', alpha=0.2,
                        label='95% CI')

        # Plot overall LOESS line
        plt.plot(x_smooth, y_smooth, color='black', linewidth=3, alpha=0.9,
                label='Overall LOESS', linestyle='--')

    plt.xlabel(x_label, fontsize=12)
    plt.ylabel('Total People Count', fontsize=12)
    plt.title(f'People Count vs {x_label} (Sunny Rows)', fontsize=14)
    plt.xlim(0, 24)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    print(f"Saved plot to {output_file}")
    plt.close()

def create_sunny_people_vs_temp_plot(city_data, temp_column, temp_label, output_file):
    """Create plot showing people count vs temperature for sunny rows only (including zero-people rows)."""
    plt.figure(figsize=(12, 8))

    # Collect all data points across cities
    all_x = []
    all_y = []
    city_labels = []

    for city_name, df in city_data.items():
        filtered_df = prepare_sunny_rows_data(df, temp_column=temp_column)

        if len(filtered_df) > 0 and temp_column in filtered_df.columns:
            x = filtered_df[temp_column].values
            y = filtered_df['total_people'].values
            n_points = len(filtered_df)

            # Plot scatter points for this city
            plt.scatter(x, y, alpha=0.3, s=15, label=f'{city_name}: {n_points} img')

            # Collect for overall LOESS
            all_x.extend(x)
            all_y.extend(y)
            city_labels.extend([city_name] * n_points)

    # Calculate overall LOESS smoothing across all cities
    if len(all_x) > 10:
        all_x = np.array(all_x)
        all_y = np.array(all_y)

        # Create balanced sample so each city has equal influence
        balanced_x, balanced_y = create_balanced_sample(all_x, all_y, city_labels)

        smoothed = lowess(balanced_y, balanced_x, frac=0.3)
        x_smooth = smoothed[:, 0]
        y_smooth = smoothed[:, 1]

        # Calculate confidence intervals using balanced bootstrap
        n_bootstrap = 100
        bootstrap_curves = []

        for _ in range(n_bootstrap):
            # Resample with replacement
            # Create balanced bootstrap sample (each city equally represented)
            boot_x, boot_y = create_balanced_sample(all_x, all_y, city_labels)


            # Calculate LOESS for this bootstrap sample
            smoothed_boot = lowess(boot_y, boot_x, frac=0.3)
            # Interpolate to match x_smooth points for consistent CI calculation
            y_boot_interp = np.interp(x_smooth, smoothed_boot[:, 0], smoothed_boot[:, 1])
            bootstrap_curves.append(y_boot_interp)

        bootstrap_curves = np.array(bootstrap_curves)

        # Calculate 95% confidence intervals
        ci_lower = np.percentile(bootstrap_curves, 2.5, axis=0)
        ci_upper = np.percentile(bootstrap_curves, 97.5, axis=0)

        # Plot confidence interval
        plt.fill_between(x_smooth, ci_lower, ci_upper, color='black', alpha=0.2,
                        label='95% CI')

        # Plot overall LOESS line
        plt.plot(x_smooth, y_smooth, color='black', linewidth=3, alpha=0.9,
                label='Overall LOESS', linestyle='--')

    plt.xlabel(temp_label, fontsize=12)
    plt.ylabel('Total People Count', fontsize=12)
    plt.title(f'People Count vs {temp_label} (Sunny Rows)', fontsize=14)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    print(f"Saved plot to {output_file}")
    plt.close()

def main():
    data_dir = "data/processed/city_estimate_outcomes"
    output_dir = Path("outputs/plots")
    shade_behavior_dir = output_dir / "shade_behavior"
    people_count_dir = output_dir / "people_count"

    # Create output directories
    shade_behavior_dir.mkdir(parents=True, exist_ok=True)
    people_count_dir.mkdir(parents=True, exist_ok=True)

    print("Loading city data...")
    city_data = load_city_data(data_dir)
    print(f"Loaded {len(city_data)} cities: {', '.join(city_data.keys())}")

    # Print statistics for each city
    for city_name, df in city_data.items():
        filtered_df = calculate_shade_percentage(df)
        print(f"{city_name}: {len(filtered_df)} data points with valid shade percentages")

    # Define all plots to generate with organized output paths
    plots = [
        # Temperature distribution comparison
        (create_temperature_distribution_plot, (city_data, str(shade_behavior_dir / 'temperature_distributions.png'))),

        # Shade behavior plots
        (create_temperature_plot, (city_data, 'wbulb', 'Wet Bulb Temperature (°C)', str(shade_behavior_dir / 'shade_ratio_vs_wetbulb.png'))),
        (create_temperature_plot, (city_data, 'dbulb', 'Dry Bulb Temperature (°C)', str(shade_behavior_dir / 'shade_ratio_vs_drybulb.png'))),
        (create_temperature_plot, (city_data, 'utci_C', 'UTCI Temperature (°C)', str(shade_behavior_dir / 'shade_ratio_vs_utci.png'))),
        (create_overall_loess_plot, (city_data, 'wbulb', 'Wet Bulb Temperature (°C)', str(shade_behavior_dir / 'overall_loess_vs_wetbulb.png'))),
        (create_overall_loess_plot, (city_data, 'dbulb', 'Dry Bulb Temperature (°C)', str(shade_behavior_dir / 'overall_loess_vs_drybulb.png'))),
        (create_overall_loess_plot, (city_data, 'utci_C', 'UTCI Temperature (°C)', str(shade_behavior_dir / 'overall_loess_vs_utci.png'))),
        (create_overall_time_of_day_plot, (city_data, 'Time of Day (Hour)', str(shade_behavior_dir / 'overall_loess_vs_timeofday.png'))),

        # People count plots (sunny + with people)
        (create_people_count_vs_time_plot, (city_data, 'Time of Day (Hour)', str(people_count_dir / 'people_count_vs_timeofday.png'))),
        (create_people_count_vs_temp_plot, (city_data, 'wbulb', 'Wet Bulb Temperature (°C)', str(people_count_dir / 'people_count_vs_wetbulb.png'))),
        (create_people_count_vs_temp_plot, (city_data, 'dbulb', 'Dry Bulb Temperature (°C)', str(people_count_dir / 'people_count_vs_drybulb.png'))),
        (create_people_count_vs_temp_plot, (city_data, 'utci_C', 'UTCI Temperature (°C)', str(people_count_dir / 'people_count_vs_utci.png'))),

        # People count plots using all rows
        (create_all_rows_people_vs_time_plot, (city_data, 'Time of Day (Hour)', str(people_count_dir / 'people_count_allrows_vs_timeofday.png'))),
        (create_all_rows_people_vs_temp_plot, (city_data, 'wbulb', 'Wet Bulb Temperature (°C)', str(people_count_dir / 'people_count_allrows_vs_wetbulb.png'))),
        (create_all_rows_people_vs_temp_plot, (city_data, 'dbulb', 'Dry Bulb Temperature (°C)', str(people_count_dir / 'people_count_allrows_vs_drybulb.png'))),
        (create_all_rows_people_vs_temp_plot, (city_data, 'utci_C', 'UTCI Temperature (°C)', str(people_count_dir / 'people_count_allrows_vs_utci.png'))),

        # People count plots using sunny rows only
        (create_sunny_people_vs_time_plot, (city_data, 'Time of Day (Hour)', str(people_count_dir / 'people_count_sunny_vs_timeofday.png'))),
        (create_sunny_people_vs_temp_plot, (city_data, 'wbulb', 'Wet Bulb Temperature (°C)', str(people_count_dir / 'people_count_sunny_vs_wetbulb.png'))),
        (create_sunny_people_vs_temp_plot, (city_data, 'dbulb', 'Dry Bulb Temperature (°C)', str(people_count_dir / 'people_count_sunny_vs_drybulb.png'))),
        (create_sunny_people_vs_temp_plot, (city_data, 'utci_C', 'UTCI Temperature (°C)', str(people_count_dir / 'people_count_sunny_vs_utci.png'))),
    ]

    # Generate all plots with progress bar
    print(f"\nGenerating {len(plots)} plots...")
    print(f"  Shade behavior plots → {shade_behavior_dir}")
    print(f"  People count plots → {people_count_dir}")
    for plot_func, args in tqdm(plots, desc="Creating plots", unit="plot"):
        plot_func(*args)

if __name__ == "__main__":
    main()
