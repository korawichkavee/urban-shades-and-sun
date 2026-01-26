#!/usr/bin/env python3
# ABOUTME: Cross-city comparison plots for shade preference by season
# ABOUTME: Shows how different cities compare in their shade-seeking behavior

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
    'Singapore': 'north',
    'Osaka': 'north',
    'Madrid': 'north',
    'Istanbul': 'north',
    'Buenos-Aires': 'south',
    'Mumbai': 'north',
    'Cape-Town': 'south',
}

# City colors for consistency
CITY_COLORS = {
    'Buenos-Aires': '#e74c3c',    # Red
    'Istanbul': '#3498db',        # Blue
    'Madrid': '#f39c12',          # Orange
    'Mumbai': '#9b59b6',          # Purple
    'Singapore': '#2ecc71',       # Green
    'Cape-Town': '#1abc9c',       # Teal
    'Osaka': '#e91e63',           # Pink
}

def fit_logistic_quadratic(x, n_success, n_total):
    """Fit binomial logistic regression with quadratic term."""
    X = np.column_stack([np.ones(len(x)), x, x**2])
    n_failures = n_total - n_success
    y = np.column_stack([n_success, n_failures])

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

def load_city_data(results_dir):
    """Load all city data with UTCI."""
    city_data = {}

    csv_files = list(results_dir.glob("*/*_analyzed_with_utci.csv"))

    for csv_file in csv_files:
        city_name = csv_file.parent.name
        print(f"Loading {city_name}...")

        df = pd.read_csv(csv_file)

        # Check for required columns
        if 'utci_C' not in df.columns:
            print(f"  Skipping {city_name} - no UTCI data")
            continue

        # Filter for sunny images with people
        df['total_people'] = df['person_count'] + df['inshade_count'] + df['outshade_count']
        df_sunny = df[(df['is_sunny'].astype(str).str.lower() == 'true') & (df['total_people'] > 0)].copy()

        if len(df_sunny) == 0:
            print(f"  Skipping {city_name} - no sunny images with people")
            continue

        # Parse datetime and assign season
        if not pd.api.types.is_datetime64_any_dtype(df_sunny['datetime-local']):
            df_sunny['datetime-local'] = pd.to_datetime(df_sunny['datetime-local'], errors='coerce')
        df_sunny = df_sunny.dropna(subset=['datetime-local'])

        try:
            df_sunny['month'] = df_sunny['datetime-local'].dt.month
        except AttributeError:
            df_sunny['datetime-local'] = pd.to_datetime(df_sunny['datetime-local'], format='mixed', errors='coerce')
            df_sunny = df_sunny.dropna(subset=['datetime-local'])
            df_sunny['month'] = df_sunny['datetime-local'].dt.month

        hemisphere = CITY_HEMISPHERES.get(city_name, 'north')
        df_sunny['season'] = df_sunny['month'].apply(lambda m: assign_season(m, hemisphere))

        # Calculate shade ratio
        df_sunny['n_success'] = df_sunny['inshade_count']
        df_sunny['n_total'] = df_sunny['total_people']
        df_sunny['shade_ratio'] = df_sunny['n_success'] / df_sunny['n_total']

        # Filter invalid UTCI
        df_sunny = df_sunny.dropna(subset=['utci_C'])
        before_filter = len(df_sunny)
        df_sunny = df_sunny[(df_sunny['utci_C'] >= -50) & (df_sunny['utci_C'] <= 60)]
        if len(df_sunny) < before_filter:
            print(f"  Filtered out {before_filter - len(df_sunny)} rows with invalid UTCI")

        city_data[city_name] = df_sunny
        print(f"  Loaded {len(df_sunny)} observations, {int(df_sunny['n_total'].sum())} people")

    return city_data

def plot_season_comparison(city_data, season, output_dir):
    """Create comparison plot for a specific season across all cities."""
    fig, ax = plt.subplots(figsize=(14, 10))

    cities_with_data = []

    for city_name, df_city in sorted(city_data.items()):
        df_season = df_city[df_city['season'] == season]

        if len(df_season) < 20:
            continue

        cities_with_data.append(city_name)

        x = df_season['utci_C'].values
        n_success = df_season['n_success'].values
        n_total = df_season['n_total'].values

        # Fit model
        results = fit_logistic_quadratic(x, n_success, n_total)

        if results is not None:
            # Plot fitted curve
            x_range = np.linspace(x.min(), x.max(), 200)
            y_pred, ci_lower, ci_upper = predict_with_ci(results, x_range)

            color = CITY_COLORS.get(city_name, 'gray')

            # Plot with CI
            ax.fill_between(x_range, ci_lower, ci_upper, alpha=0.15, color=color)
            ax.plot(x_range, y_pred, color=color, linewidth=3,
                   label=f'{city_name} (n={len(df_season)})', alpha=0.8)

    if len(cities_with_data) == 0:
        print(f"  No cities with sufficient {season} data")
        plt.close()
        return

    # Formatting
    ax.set_xlabel('UTCI Temperature (°C)', fontsize=14)
    ax.set_ylabel('Shade Ratio', fontsize=14)
    ax.set_title(f'Cross-City Comparison - {season}\nShade-Seeking Behavior vs UTCI Temperature',
                fontsize=16, fontweight='bold')
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=11, loc='best')

    # Save
    output_file = output_dir / f"cross_city_{season.lower()}_comparison.png"
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"  ✓ Saved {season} comparison ({len(cities_with_data)} cities)")

def plot_overall_comparison(city_data, output_dir):
    """Create overall comparison plot across all cities and seasons."""
    fig, ax = plt.subplots(figsize=(16, 12))

    for city_name, df_city in sorted(city_data.items()):
        if len(df_city) < 20:
            continue

        x = df_city['utci_C'].values
        n_success = df_city['n_success'].values
        n_total = df_city['n_total'].values

        # Fit model
        results = fit_logistic_quadratic(x, n_success, n_total)

        if results is not None:
            # Plot fitted curve
            x_range = np.linspace(x.min(), x.max(), 200)
            y_pred, ci_lower, ci_upper = predict_with_ci(results, x_range)

            color = CITY_COLORS.get(city_name, 'gray')

            # Plot with CI
            ax.fill_between(x_range, ci_lower, ci_upper, alpha=0.12, color=color)
            ax.plot(x_range, y_pred, color=color, linewidth=3.5,
                   label=f'{city_name} (n={len(df_city)}, {int(n_total.sum())} people)',
                   alpha=0.85)

    # Formatting
    ax.set_xlabel('UTCI Temperature (°C)', fontsize=15)
    ax.set_ylabel('Shade Ratio', fontsize=15)
    ax.set_title('Cross-City Comparison - All Seasons\nShade-Seeking Behavior vs UTCI Temperature',
                fontsize=17, fontweight='bold')
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=12, loc='best', ncol=2)

    # Save
    output_file = output_dir / "cross_city_overall_comparison.png"
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"  ✓ Saved overall comparison")

def main():
    results_dir = Path("data/multi_city_results")
    output_dir = Path("outputs/plots/multi_city_comparison")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("="*80)
    print("MULTI-CITY COMPARISON PLOTS")
    print("="*80)
    print()

    # Load all city data
    city_data = load_city_data(results_dir)

    if len(city_data) == 0:
        print("No city data found!")
        return

    print()
    print("Creating comparison plots...")
    print()

    # Create seasonal comparison plots
    for season in ['Spring', 'Summer', 'Fall', 'Winter']:
        print(f"Processing {season}...")
        plot_season_comparison(city_data, season, output_dir)

    # Create overall comparison
    print("Processing overall comparison...")
    plot_overall_comparison(city_data, output_dir)

    print()
    print("="*80)
    print("✓ ALL COMPARISON PLOTS COMPLETE")
    print("="*80)
    print(f"\nPlots saved to: {output_dir}")
    print()

if __name__ == "__main__":
    main()
