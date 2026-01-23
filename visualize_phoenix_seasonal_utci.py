# ABOUTME: Creates seasonal LOESS plots showing shade preference vs UTCI temperature for Phoenix.
# ABOUTME: Generates separate plots for each season plus an overall plot with confidence intervals.

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from statsmodels.nonparametric.smoothers_lowess import lowess
from pathlib import Path


def get_season(month):
    """Convert month number to season name."""
    if month in [12, 1, 2]:
        return 'Winter'
    elif month in [3, 4, 5]:
        return 'Spring'
    elif month in [6, 7, 8]:
        return 'Summer'
    elif month in [9, 10, 11]:
        return 'Fall'
    else:
        return None


def calculate_shade_percentage(df):
    """Calculate the percentage of people in shade for sunny rows with people only."""
    # Calculate total people for each row
    df['total_people'] = df['inshade_count'].fillna(0) + df['outshade_count'].fillna(0)

    # Filter for: sunny rows, valid shade counts, and at least one person
    mask = (df['is_sunny'] == True) & \
           (df['inshade_count'].notna()) & \
           (df['outshade_count'].notna()) & \
           (df['total_people'] > 0)

    filtered_df = df[mask].copy()

    # Calculate shade ratio (0-1 scale, not percentage)
    filtered_df['shade_ratio'] = filtered_df['inshade_count'] / filtered_df['total_people']

    return filtered_df


def create_loess_plot_with_ci(x, y, frac=0.3, n_bootstrap=100):
    """Create LOESS smoothing with confidence intervals using bootstrap.

    Returns:
        x_smooth: smoothed x values
        y_smooth: smoothed y values (LOESS curve)
        ci_lower: lower 95% confidence interval
        ci_upper: upper 95% confidence interval
    """
    # Calculate main LOESS smoothing
    smoothed = lowess(y, x, frac=frac)
    x_smooth = smoothed[:, 0]
    y_smooth = smoothed[:, 1]

    # Calculate confidence intervals using bootstrap
    bootstrap_curves = []

    # Add the original curve first
    bootstrap_curves.append(y_smooth)

    for _ in range(n_bootstrap - 1):
        # Resample with replacement
        indices = np.random.choice(len(x), size=len(x), replace=True)
        x_boot = x[indices]
        y_boot = y[indices]

        # Calculate LOESS for this bootstrap sample
        try:
            smoothed_boot = lowess(y_boot, x_boot, frac=frac)
            # Interpolate to match x_smooth points
            y_boot_interp = np.interp(x_smooth, smoothed_boot[:, 0], smoothed_boot[:, 1],
                                     left=np.nan, right=np.nan)
            bootstrap_curves.append(y_boot_interp)
        except:
            # Skip failed bootstrap iterations
            continue

    bootstrap_curves = np.array(bootstrap_curves)

    # Calculate 95% confidence intervals
    ci_lower = np.nanpercentile(bootstrap_curves, 2.5, axis=0)
    ci_upper = np.nanpercentile(bootstrap_curves, 97.5, axis=0)

    return x_smooth, y_smooth, ci_lower, ci_upper


def create_seasonal_plots(df, output_dir):
    """Create separate LOESS plots for each season and an overall plot."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Filter out rows with missing UTCI
    df = df[df['utci_C'].notna()].copy()

    # Get season labels
    df['month'] = pd.to_datetime(df['datetime_local'], format='ISO8601').dt.month
    df['season'] = df['month'].apply(get_season)

    # Filter for shade analysis (sunny, with people)
    df_filtered = calculate_shade_percentage(df)

    print(f"Total rows after filtering: {len(df_filtered)}")
    print(f"UTCI range: {df_filtered['utci_C'].min():.1f}°C to {df_filtered['utci_C'].max():.1f}°C")

    # Season colors
    season_colors = {
        'Spring': '#2ecc71',  # green
        'Summer': '#e74c3c',  # red
        'Fall': '#e67e22',    # orange
        'Winter': '#3498db'   # blue
    }

    # Create individual seasonal plots
    seasons = ['Spring', 'Summer', 'Fall', 'Winter']

    for season in seasons:
        season_df = df_filtered[df_filtered['season'] == season]

        if len(season_df) < 20:
            print(f"Skipping {season} - insufficient data (n={len(season_df)})")
            continue

        print(f"\n{season}: {len(season_df)} observations")

        # Create plot
        fig, ax = plt.subplots(figsize=(12, 8))

        x = season_df['utci_C'].values
        y = season_df['shade_ratio'].values

        # Scatter plot
        ax.scatter(x, y, alpha=0.3, s=30, color=season_colors[season],
                  label=f'Observations (n={len(season_df)})')

        # LOESS with confidence intervals
        x_smooth, y_smooth, ci_lower, ci_upper = create_loess_plot_with_ci(x, y, frac=0.3)

        # Plot confidence interval
        ax.fill_between(x_smooth, ci_lower, ci_upper,
                       color=season_colors[season], alpha=0.2, label='95% CI')

        # Plot LOESS line
        ax.plot(x_smooth, y_smooth, color=season_colors[season],
               linewidth=3, label='LOESS fit')

        # Labels and formatting
        ax.set_xlabel('UTCI Temperature (°C)', fontsize=14)
        ax.set_ylabel('Shade Ratio', fontsize=14)
        ax.set_title(f'Shade-Seeking Behavior vs UTCI Temperature - {season} (Phoenix, AZ)',
                    fontsize=16, fontweight='bold')
        ax.set_ylim(0, 1)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=12, loc='best')

        # Save plot
        output_file = output_dir / f'phoenix_{season.lower()}_utci_shade.png'
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Saved: {output_file}")
        plt.close()

    # Create overall plot with all seasons
    print(f"\nCreating overall plot with all seasons...")
    fig, ax = plt.subplots(figsize=(14, 10))

    for season in seasons:
        season_df = df_filtered[df_filtered['season'] == season]

        if len(season_df) < 20:
            continue

        x = season_df['utci_C'].values
        y = season_df['shade_ratio'].values

        # Scatter plot
        ax.scatter(x, y, alpha=0.25, s=20, color=season_colors[season], label=f'{season} (n={len(season_df)})')

        # LOESS with confidence intervals
        x_smooth, y_smooth, ci_lower, ci_upper = create_loess_plot_with_ci(x, y, frac=0.3)

        # Plot confidence interval
        ax.fill_between(x_smooth, ci_lower, ci_upper,
                       color=season_colors[season], alpha=0.15)

        # Plot LOESS line
        ax.plot(x_smooth, y_smooth, color=season_colors[season],
               linewidth=3, alpha=0.9)

    # Overall LOESS across all data
    x_all = df_filtered['utci_C'].values
    y_all = df_filtered['shade_ratio'].values
    x_smooth_all, y_smooth_all, ci_lower_all, ci_upper_all = create_loess_plot_with_ci(x_all, y_all, frac=0.3)

    # Plot overall confidence interval and LOESS
    ax.fill_between(x_smooth_all, ci_lower_all, ci_upper_all,
                   color='black', alpha=0.15, label='Overall 95% CI')
    ax.plot(x_smooth_all, y_smooth_all, color='black',
           linewidth=4, linestyle='--', alpha=0.8, label='Overall LOESS')

    # Labels and formatting
    ax.set_xlabel('UTCI Temperature (°C)', fontsize=14)
    ax.set_ylabel('Shade Ratio', fontsize=14)
    ax.set_title(f'Shade-Seeking Behavior vs UTCI Temperature - All Seasons (Phoenix, AZ)\nn={len(df_filtered)} observations',
                fontsize=16, fontweight='bold')
    ax.set_ylim(0, 1)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=11, loc='best', ncol=2)

    # Save overall plot
    output_file = output_dir / 'phoenix_overall_utci_shade.png'
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_file}")
    plt.close()

    # Print summary statistics
    print("\n" + "="*60)
    print("Summary Statistics by Season:")
    print("="*60)
    for season in seasons:
        season_df = df_filtered[df_filtered['season'] == season]
        if len(season_df) > 0:
            print(f"\n{season}:")
            print(f"  Observations: {len(season_df)}")
            print(f"  UTCI range: {season_df['utci_C'].min():.1f}°C to {season_df['utci_C'].max():.1f}°C")
            print(f"  Mean UTCI: {season_df['utci_C'].mean():.1f}°C")
            print(f"  Mean shade ratio: {season_df['shade_ratio'].mean():.3f}")
            print(f"  Median shade ratio: {season_df['shade_ratio'].median():.3f}")


def main():
    print("="*60)
    print("Phoenix Seasonal UTCI Shade Preference Visualization")
    print("="*60)

    # Load data
    input_file = Path("Phoenix_1840020568_with_utci.csv")
    if not input_file.exists():
        print(f"ERROR: Input file not found: {input_file}")
        return

    print(f"\nLoading data from {input_file}...")
    df = pd.read_csv(input_file)
    print(f"Loaded {len(df)} rows")

    # Create output directory
    output_dir = Path("outputs/plots/phoenix_seasonal")

    # Generate plots
    create_seasonal_plots(df, output_dir)

    print("\n" + "="*60)
    print("Visualization complete!")
    print(f"Plots saved to: {output_dir}")
    print("="*60)


if __name__ == "__main__":
    main()
