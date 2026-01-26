#!/usr/bin/env python3
# ABOUTME: Create seasonal UTCI vs shade preference plots for all multi-city data
# ABOUTME: Uses binomial logistic regression like Phoenix visualizations

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import statsmodels.api as sm
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

def assign_season(month, hemisphere='north'):
    """Assign season based on month and hemisphere."""
    if hemisphere == 'north':
        if month in [12, 1, 2]:
            return 'Winter'
        elif month in [3, 4, 5]:
            return 'Spring'
        elif month in [6, 7, 8]:
            return 'Summer'
        else:  # 9, 10, 11
            return 'Fall'
    else:  # southern hemisphere
        if month in [12, 1, 2]:
            return 'Summer'
        elif month in [3, 4, 5]:
            return 'Fall'
        elif month in [6, 7, 8]:
            return 'Winter'
        else:  # 9, 10, 11
            return 'Spring'

# City hemisphere mapping
CITY_HEMISPHERES = {
    'Singapore': 'north',  # Equatorial, use north
    'Osaka': 'north',
    'Madrid': 'north',
    'Istanbul': 'north',
    'Buenos-Aires': 'south',
    'Mumbai': 'north',
    'Cape-Town': 'south',
}

def fit_logistic_quadratic(x, n_success, n_total):
    """Fit binomial logistic regression with quadratic term.

    The binomial family automatically weights by n_total (number of trials).
    Each observation contributes based on how many people were in that image.

    Returns fitted model.
    """
    # Create design matrix with intercept, linear, and quadratic terms
    X = np.column_stack([np.ones(len(x)), x, x**2])

    # Binomial response: [n_successes, n_failures]
    # GLM with binomial family automatically weights by total trials
    n_failures = n_total - n_success
    y = np.column_stack([n_success, n_failures])

    # Fit GLM with binomial family (inherently weighted by n_total)
    model = sm.GLM(y, X, family=sm.families.Binomial())
    try:
        results = model.fit()
        return results
    except Exception as e:
        print(f"    Warning: Model fitting failed: {e}")
        return None


def predict_with_ci(results, x_pred, alpha=0.05):
    """Get predictions and confidence intervals from logistic model."""
    X_pred = np.column_stack([np.ones(len(x_pred)), x_pred, x_pred**2])

    predictions = results.get_prediction(X_pred)
    pred_summary = predictions.summary_frame(alpha=alpha)

    return pred_summary['mean'].values, pred_summary['mean_ci_lower'].values, pred_summary['mean_ci_upper'].values

def plot_city_seasonal(city_name, csv_path, output_dir):
    """Create seasonal plots for a single city."""
    print(f"\nProcessing {city_name}...")

    # Load data
    df = pd.read_csv(csv_path)

    # Check for required columns
    if 'utci_C' not in df.columns:
        print(f"  Skipping {city_name} - no UTCI data")
        return

    # Filter for sunny images with people (check inshade + outshade, not person_count)
    df['total_people'] = df['person_count'] + df['inshade_count'] + df['outshade_count']
    df_sunny = df[(df['is_sunny'].astype(str).str.lower() == 'true') & (df['total_people'] > 0)].copy()

    if len(df_sunny) == 0:
        print(f"  Skipping {city_name} - no sunny images with people")
        return

    total_people = df_sunny['total_people'].sum()
    print(f"  Found {len(df_sunny)} sunny images with {int(total_people)} people total")

    # Parse datetime and assign season
    if not pd.api.types.is_datetime64_any_dtype(df_sunny['datetime-local']):
        df_sunny['datetime-local'] = pd.to_datetime(df_sunny['datetime-local'], errors='coerce')
    df_sunny = df_sunny.dropna(subset=['datetime-local'])

    # Extract month safely
    try:
        df_sunny['month'] = df_sunny['datetime-local'].dt.month
    except AttributeError:
        # If still not datetime, try again with format specification
        df_sunny['datetime-local'] = pd.to_datetime(df_sunny['datetime-local'], format='mixed', errors='coerce')
        df_sunny = df_sunny.dropna(subset=['datetime-local'])
        df_sunny['month'] = df_sunny['datetime-local'].dt.month

    hemisphere = CITY_HEMISPHERES.get(city_name, 'north')
    df_sunny['season'] = df_sunny['month'].apply(lambda m: assign_season(m, hemisphere))

    # Calculate shade ratio (people in shade / total people)
    df_sunny['n_success'] = df_sunny['inshade_count']
    df_sunny['n_total'] = df_sunny['total_people']  # Use total_people instead of person_count
    df_sunny['shade_ratio'] = df_sunny['n_success'] / df_sunny['n_total']

    # Remove rows with missing or invalid UTCI (check for outliers like -200)
    df_sunny = df_sunny.dropna(subset=['utci_C'])

    # Filter out invalid UTCI values (reasonable range: -50°C to 60°C)
    before_filter = len(df_sunny)
    df_sunny = df_sunny[(df_sunny['utci_C'] >= -50) & (df_sunny['utci_C'] <= 60)]
    if len(df_sunny) < before_filter:
        print(f"  Filtered out {before_filter - len(df_sunny)} rows with invalid UTCI values")

    print(f"  Seasons: {df_sunny['season'].value_counts().to_dict()}")
    print(f"  UTCI range: {df_sunny['utci_C'].min():.1f}°C to {df_sunny['utci_C'].max():.1f}°C")

    # Season colors
    season_colors = {
        'Spring': '#2ecc71',  # Green
        'Summer': '#e74c3c',  # Red
        'Fall': '#f39c12',    # Orange
        'Winter': '#3498db'   # Blue
    }

    season_order = ['Spring', 'Summer', 'Fall', 'Winter']

    # Create individual plots for each season
    for season in season_order:
        df_season = df_sunny[df_sunny['season'] == season]

        if len(df_season) < 20:
            print(f"  Skipping {season} - too few observations ({len(df_season)})")
            continue

        # Use individual images (DO NOT aggregate by temperature)
        x = df_season['utci_C'].values
        n_success = df_season['n_success'].values
        n_total = df_season['n_total'].values
        y_ratio = df_season['shade_ratio'].values

        # Fit model on individual observations
        results = fit_logistic_quadratic(x, n_success, n_total)

        if results is None:
            continue

        # Create plot
        fig, ax = plt.subplots(figsize=(12, 8))

        # Add slight jitter to y values for visibility
        np.random.seed(42)
        y_jitter = y_ratio + np.random.normal(0, 0.01, size=len(y_ratio))
        y_jitter = np.clip(y_jitter, 0, 1)

        # Plot points sized by number of people
        point_sizes = n_total * 10  # Scale factor for visibility
        ax.scatter(x, y_jitter,
                  s=point_sizes, alpha=0.4,
                  color=season_colors[season],
                  edgecolors='black', linewidth=0.5,
                  label='Observations (size ∝ people)')

        # Plot fitted curve with proper CI
        x_range = np.linspace(x.min(), x.max(), 200)
        y_pred, ci_lower, ci_upper = predict_with_ci(results, x_range)

        ax.fill_between(x_range, ci_lower, ci_upper, alpha=0.2, color=season_colors[season],
                       label='95% CI')
        ax.plot(x_range, y_pred, color=season_colors[season], linewidth=3,
               label='Binomial Logistic (quadratic)')

        # Formatting
        ax.set_xlabel('UTCI Temperature (°C)', fontsize=13)
        ax.set_ylabel('Shade Ratio', fontsize=13)
        ax.set_title(f'{city_name} - {season}\nShade-Seeking Behavior vs UTCI Temperature\n' +
                   f'n={len(df_season)} observations, {int(n_total.sum())} people total',
                   fontsize=14, fontweight='bold')
        ax.set_ylim(-0.05, 1.05)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=11, loc='best')

        # Save
        output_file = output_dir / f"{city_name.replace(' ', '-')}_{season.lower()}_utci_logistic.png"
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"  ✓ Saved {season} plot")

    # Create overall plot
    if len(df_sunny) >= 20:
        # Use all individual images (DO NOT aggregate)
        x_all = df_sunny['utci_C'].values
        n_success_all = df_sunny['n_success'].values
        n_total_all = df_sunny['n_total'].values
        y_ratio_all = df_sunny['shade_ratio'].values

        # Fit overall model on all observations
        results = fit_logistic_quadratic(x_all, n_success_all, n_total_all)

        if results is not None:
            fig, ax = plt.subplots(figsize=(14, 10))

            # Scatter by season with size proportional to number of people
            for season in season_order:
                season_df = df_sunny[df_sunny['season'] == season]
                if len(season_df) > 0:
                    np.random.seed(42)
                    y_jitter = season_df['shade_ratio'].values + np.random.normal(0, 0.01, size=len(season_df))
                    y_jitter = np.clip(y_jitter, 0, 1)

                    # Size by number of people
                    point_sizes = season_df['n_total'].values * 5
                    ax.scatter(season_df['utci_C'].values, y_jitter, alpha=0.3, s=point_sizes,
                              color=season_colors.get(season, 'gray'), edgecolors='black', linewidth=0.3,
                              label=f'{season} (n={len(season_df)})')

            # Binomial Logistic Regression (weighted by number of people)
            x_pred = np.linspace(x_all.min(), x_all.max(), 200)
            y_pred, ci_lower, ci_upper = predict_with_ci(results, x_pred)

            ax.fill_between(x_pred, ci_lower, ci_upper, alpha=0.2, color='black',
                           label='95% CI')
            ax.plot(x_pred, y_pred, color='black', linewidth=4,
                   label='Binomial Logistic (quadratic)', linestyle='-', zorder=10)

            # Formatting
            ax.set_xlabel('UTCI Temperature (°C)', fontsize=14)
            ax.set_ylabel('Shade Ratio', fontsize=14)
            ax.set_title(f'{city_name} - All Seasons\nShade-Seeking Behavior vs UTCI Temperature\n' +
                        f'n={len(df_sunny)} observations, {int(n_total_all.sum())} people (point size ∝ people)',
                        fontsize=15, fontweight='bold')
            ax.set_ylim(-0.05, 1.05)
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=11, loc='best', ncol=2)

            # Save
            output_file = output_dir / f"{city_name.replace(' ', '-')}_overall_utci_logistic.png"
            plt.tight_layout()
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            plt.close()

            print(f"  ✓ Saved overall plot")

def main():
    results_dir = Path("data/multi_city_results")
    output_dir = Path("outputs/plots/multi_city_seasonal")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("="*80)
    print("MULTI-CITY SEASONAL UTCI VISUALIZATION")
    print("="*80)

    # Find all UTCI-enriched CSVs
    csv_files = list(results_dir.glob("*/*_analyzed_with_utci.csv"))

    print(f"\nFound {len(csv_files)} cities with UTCI data\n")

    for csv_file in sorted(csv_files):
        city_name = csv_file.parent.name
        plot_city_seasonal(city_name, csv_file, output_dir)

    print("\n" + "="*80)
    print("✓ ALL VISUALIZATIONS COMPLETE")
    print("="*80)
    print(f"\nPlots saved to: {output_dir}")
    print("")

if __name__ == "__main__":
    main()
