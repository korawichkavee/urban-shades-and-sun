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
    """Fit binomial logistic regression with quadratic term."""
    # Create design matrix
    X = np.column_stack([np.ones(len(x)), x, x**2])

    # Binomial response
    n_failures = n_total - n_success
    y = np.column_stack([n_success, n_failures])

    # Fit GLM
    model = sm.GLM(y, X, family=sm.families.Binomial())
    try:
        results = model.fit()
        return results
    except Exception as e:
        print(f"    Warning: Model fitting failed: {e}")
        return None

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

    # Remove rows with missing UTCI
    df_sunny = df_sunny.dropna(subset=['utci_C'])

    print(f"  Seasons: {df_sunny['season'].value_counts().to_dict()}")

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

        if len(df_season) < 10:
            print(f"  Skipping {season} - too few observations ({len(df_season)})")
            continue

        # Aggregate by UTCI (round to nearest degree)
        df_season['utci_rounded'] = df_season['utci_C'].round(0)
        agg = df_season.groupby('utci_rounded').agg({
            'n_success': 'sum',
            'n_total': 'sum'
        }).reset_index()

        if len(agg) < 3:
            print(f"  Skipping {season} - too few unique UTCI values ({len(agg)})")
            continue

        agg['shade_ratio'] = agg['n_success'] / agg['n_total']

        # Fit model
        results = fit_logistic_quadratic(agg['utci_rounded'].values,
                                        agg['n_success'].values,
                                        agg['n_total'].values)

        if results is None:
            continue

        # Create plot
        fig, ax = plt.subplots(figsize=(10, 6))

        # Plot points sized by number of people
        point_sizes = agg['n_total'] * 5
        ax.scatter(agg['utci_rounded'], agg['shade_ratio'],
                  s=point_sizes, alpha=0.6,
                  color=season_colors[season],
                  edgecolors='black', linewidth=0.5,
                  label='Observed (size = # people)')

        # Plot fitted curve
        x_range = np.linspace(agg['utci_rounded'].min(), agg['utci_rounded'].max(), 200)
        X_pred = np.column_stack([np.ones(len(x_range)), x_range, x_range**2])
        predictions = results.predict(X_pred)

        ax.plot(x_range, predictions, 'k-', linewidth=2, label='Fitted curve')

        # Confidence interval
        pred_se = np.sqrt(results.predict(X_pred, which='linear') * (1 - results.predict(X_pred, which='linear')) / agg['n_total'].mean())
        ci_lower = np.maximum(0, predictions - 1.96 * pred_se)
        ci_upper = np.minimum(1, predictions + 1.96 * pred_se)
        ax.fill_between(x_range, ci_lower, ci_upper, alpha=0.2, color='gray', label='95% CI')

        # Formatting
        ax.set_xlabel('UTCI Temperature (°C)', fontsize=12)
        ax.set_ylabel('Shade-Seeking Ratio', fontsize=12)
        ax.set_title(f'{city_name} - {season}\nShade Preference vs UTCI Temperature', fontsize=14, fontweight='bold')
        ax.set_ylim(0, 1)
        ax.grid(True, alpha=0.3)
        ax.legend()

        # Save
        output_file = output_dir / f"{city_name.replace(' ', '-')}_{season.lower()}_utci_logistic.png"
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"  ✓ Saved {season} plot")

    # Create overall plot
    if len(df_sunny) >= 10:
        # Aggregate overall
        df_sunny['utci_rounded'] = df_sunny['utci_C'].round(0)
        agg_overall = df_sunny.groupby('utci_rounded').agg({
            'n_success': 'sum',
            'n_total': 'sum',
            'season': lambda x: x.mode()[0] if len(x) > 0 else 'Unknown'
        }).reset_index()

        if len(agg_overall) >= 3:
            agg_overall['shade_ratio'] = agg_overall['n_success'] / agg_overall['n_total']

            # Fit overall model
            results = fit_logistic_quadratic(agg_overall['utci_rounded'].values,
                                            agg_overall['n_success'].values,
                                            agg_overall['n_total'].values)

            if results is not None:
                fig, ax = plt.subplots(figsize=(12, 7))

                # Plot points colored by season
                for season in season_order:
                    mask = agg_overall['season'] == season
                    if mask.sum() > 0:
                        point_sizes = agg_overall.loc[mask, 'n_total'] * 5
                        ax.scatter(agg_overall.loc[mask, 'utci_rounded'],
                                 agg_overall.loc[mask, 'shade_ratio'],
                                 s=point_sizes, alpha=0.6,
                                 color=season_colors.get(season, 'gray'),
                                 edgecolors='black', linewidth=0.5,
                                 label=season)

                # Plot fitted curve
                x_range = np.linspace(agg_overall['utci_rounded'].min(),
                                     agg_overall['utci_rounded'].max(), 200)
                X_pred = np.column_stack([np.ones(len(x_range)), x_range, x_range**2])
                predictions = results.predict(X_pred)

                ax.plot(x_range, predictions, 'k-', linewidth=3, label='Overall fitted curve')

                # Confidence interval
                pred_se = np.sqrt(predictions * (1 - predictions) / agg_overall['n_total'].mean())
                ci_lower = np.maximum(0, predictions - 1.96 * pred_se)
                ci_upper = np.minimum(1, predictions + 1.96 * pred_se)
                ax.fill_between(x_range, ci_lower, ci_upper, alpha=0.15, color='gray', label='95% CI')

                # Formatting
                ax.set_xlabel('UTCI Temperature (°C)', fontsize=13)
                ax.set_ylabel('Shade-Seeking Ratio', fontsize=13)
                ax.set_title(f'{city_name} - All Seasons\nShade Preference vs UTCI Temperature',
                           fontsize=15, fontweight='bold')
                ax.set_ylim(0, 1)
                ax.grid(True, alpha=0.3)
                ax.legend(loc='best')

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
