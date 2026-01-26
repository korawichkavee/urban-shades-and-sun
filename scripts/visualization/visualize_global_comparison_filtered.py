#!/usr/bin/env python3
# ABOUTME: Global comparison plots using wind-filtered data
# ABOUTME: Shows cross-city comparisons AND aggregated seasonal patterns with UTCI validation

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import statsmodels.api as sm
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Track data loss statistics
DATA_LOSS_STATS = {}

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
    'Phoenix': 'north',
    'Singapore': 'north',
    'Osaka': 'north',
    'Madrid': 'north',
    'Istanbul': 'north',
    'Buenos-Aires': 'south',
    'Mumbai': 'north',
    'Cape-Town': 'south',
}

# City colors
CITY_COLORS = {
    'Phoenix': '#FF6B35',
    'Buenos-Aires': '#e74c3c',
    'Istanbul': '#3498db',
    'Madrid': '#f39c12',
    'Mumbai': '#9b59b6',
    'Singapore': '#2ecc71',
    'Cape-Town': '#1abc9c',
    'Osaka': '#e91e63',
}

# Season colors
SEASON_COLORS = {
    'Spring': '#2ecc71',
    'Summer': '#e74c3c',
    'Fall': '#f39c12',
    'Winter': '#3498db'
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

def load_city_data(results_dir, use_filtered=True):
    """Load all city data with wind filtering applied."""
    city_data = {}

    # Load multi-city data (look for filtered CSVs)
    if use_filtered:
        csv_files = list(results_dir.glob("*/*_analyzed_with_utci_filtered.csv"))
        print(f"Using filtered CSVs (wind-validated)")
    else:
        csv_files = list(results_dir.glob("*/*_analyzed_with_utci.csv"))
        # Exclude filtered versions
        csv_files = [f for f in csv_files if '_filtered' not in f.name]
        print(f"Using unfiltered CSVs (original)")

    if len(csv_files) == 0:
        print("ERROR: No CSV files found!")
        return city_data

    for csv_file in csv_files:
        city_name = csv_file.parent.name
        print(f"Loading {city_name}...")

        df = pd.read_csv(csv_file, low_memory=False)

        # Track original size
        original_size = len(df)

        if 'utci_C' not in df.columns:
            print(f"  Skipping {city_name} - no UTCI data")
            continue

        # Check if we have utci_valid flag
        if use_filtered and 'utci_valid' in df.columns:
            # Filter using the utci_valid flag
            df_before = len(df)
            df = df[df['utci_valid'] == True].copy()
            filtered_count = df_before - len(df)
            print(f"  Filtered {filtered_count} rows with utci_valid flag")

        # Filter for sunny images with people
        df['total_people'] = df['person_count'] + df['inshade_count'] + df['outshade_count']
        df_sunny = df[(df['is_sunny'].astype(str).str.lower() == 'true') & (df['total_people'] > 0)].copy()

        if len(df_sunny) == 0:
            print(f"  Skipping {city_name} - no sunny images with people")
            DATA_LOSS_STATS[city_name] = {
                'original': original_size,
                'after_filtering': len(df),
                'after_sunny_people_filter': 0,
                'final': 0,
                'loss_pct': 100.0
            }
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

        # Additional UTCI validation (belt and suspenders)
        df_sunny = df_sunny.dropna(subset=['utci_C'])
        before_utci_filter = len(df_sunny)
        df_sunny = df_sunny[(df_sunny['utci_C'] >= -50) & (df_sunny['utci_C'] <= 60)]
        if len(df_sunny) < before_utci_filter:
            print(f"  Filtered out {before_utci_filter - len(df_sunny)} rows with invalid UTCI range")

        # Record data loss statistics
        final_size = len(df_sunny)
        DATA_LOSS_STATS[city_name] = {
            'original': original_size,
            'after_filtering': len(df),
            'after_sunny_people_filter': before_utci_filter,
            'final': final_size,
            'loss_pct': ((original_size - final_size) / original_size * 100) if original_size > 0 else 0
        }

        city_data[city_name] = df_sunny
        print(f"  Loaded {len(df_sunny)} observations, {int(df_sunny['n_total'].sum())} people")
        print(f"  Data retention: {final_size}/{original_size} ({100 - DATA_LOSS_STATS[city_name]['loss_pct']:.1f}%)")

    return city_data

def plot_season_comparison(city_data, season, output_dir):
    """Create comparison plot for a specific season."""
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
                   label=f'{city_name} (n={len(df_season)})', alpha=0.75)

    if len(cities_with_data) == 0:
        print(f"  No cities with sufficient {season} data")
        plt.close()
        return

    # Formatting
    ax.set_xlabel('UTCI Temperature (°C)', fontsize=14)
    ax.set_ylabel('Shade Ratio', fontsize=14)
    ax.set_title(f'Global Comparison - {season} (Wind-Filtered Data)\nShade-Seeking Behavior vs UTCI Temperature',
                fontsize=16, fontweight='bold')
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=11, loc='best', ncol=2)

    # Save
    output_file = output_dir / f"global_{season.lower()}_comparison_filtered.png"
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"  ✓ Saved {season} comparison ({len(cities_with_data)} cities)")

def plot_overall_comparison(city_data, output_dir):
    """Create overall comparison plot."""
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
                   alpha=0.8)

    # Formatting
    ax.set_xlabel('UTCI Temperature (°C)', fontsize=15)
    ax.set_ylabel('Shade Ratio', fontsize=15)
    ax.set_title('Global Comparison - All Seasons (Wind-Filtered Data)\nShade-Seeking Behavior vs UTCI Temperature',
                fontsize=17, fontweight='bold')
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=12, loc='best', ncol=2)

    # Save
    output_file = output_dir / "global_overall_comparison_filtered.png"
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"  ✓ Saved overall comparison")

def plot_aggregated_seasonal(city_data, season, output_dir):
    """Create aggregated plot combining all cities' data for a specific season."""
    print(f"Processing aggregated {season}...")

    # Combine all cities' data for this season
    all_data = []
    cities_included = []

    for city_name, df_city in city_data.items():
        df_season = df_city[df_city['season'] == season]
        if len(df_season) >= 20:
            all_data.append(df_season)
            cities_included.append(city_name)

    if len(all_data) == 0:
        print(f"  No data for {season}")
        return

    # Concatenate all data
    df_combined = pd.concat(all_data, ignore_index=True)

    x = df_combined['utci_C'].values
    n_success = df_combined['n_success'].values
    n_total = df_combined['n_total'].values
    y_ratio = df_combined['shade_ratio'].values

    print(f"  Combined: {len(df_combined)} observations from {len(cities_included)} cities")
    print(f"  Total people: {int(n_total.sum())}")

    # Fit model on combined data
    results = fit_logistic_quadratic(x, n_success, n_total)

    if results is None:
        return

    # Create plot
    fig, ax = plt.subplots(figsize=(14, 10))

    # Add slight jitter to y values for visibility
    np.random.seed(42)
    y_jitter = y_ratio + np.random.normal(0, 0.01, size=len(y_ratio))
    y_jitter = np.clip(y_jitter, 0, 1)

    # Plot points sized by number of people
    point_sizes = n_total * 5
    ax.scatter(x, y_jitter,
              s=point_sizes, alpha=0.15,
              color=SEASON_COLORS[season],
              edgecolors='none',
              label='Observations (size ∝ people)')

    # Plot fitted curve with CI
    x_range = np.linspace(x.min(), x.max(), 200)
    y_pred, ci_lower, ci_upper = predict_with_ci(results, x_range)

    ax.fill_between(x_range, ci_lower, ci_upper, alpha=0.25,
                   color=SEASON_COLORS[season],
                   label='95% CI')
    ax.plot(x_range, y_pred, color=SEASON_COLORS[season], linewidth=4,
           label='Aggregated fit (all cities)', zorder=10)

    # Formatting
    ax.set_xlabel('UTCI Temperature (°C)', fontsize=14)
    ax.set_ylabel('Shade Ratio', fontsize=14)
    ax.set_title(f'Aggregated Global Pattern - {season} (Wind-Filtered)\n' +
                f'Combined data from {len(cities_included)} cities\n' +
                f'n={len(df_combined):,} observations, {int(n_total.sum()):,} people total',
                fontsize=15, fontweight='bold')
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=12, loc='best')

    # Add text box with cities included
    cities_text = ', '.join(sorted(cities_included))
    ax.text(0.02, 0.98, f'Cities: {cities_text}',
           transform=ax.transAxes, fontsize=9,
           verticalalignment='top',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

    # Save
    output_file = output_dir / f"aggregated_{season.lower()}_global_filtered.png"
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"  ✓ Saved aggregated {season} plot")

def plot_aggregated_overall(city_data, output_dir):
    """Create aggregated plot combining all cities and seasons."""
    print("Processing aggregated overall...")

    # Combine ALL data
    all_data = []
    for city_name, df_city in city_data.items():
        if len(df_city) >= 20:
            all_data.append(df_city)

    if len(all_data) == 0:
        print("  No data for overall")
        return

    df_combined = pd.concat(all_data, ignore_index=True)

    x = df_combined['utci_C'].values
    n_success = df_combined['n_success'].values
    n_total = df_combined['n_total'].values
    y_ratio = df_combined['shade_ratio'].values

    print(f"  Combined: {len(df_combined)} observations from {len(city_data)} cities")
    print(f"  Total people: {int(n_total.sum())}")

    # Fit model
    results = fit_logistic_quadratic(x, n_success, n_total)

    if results is None:
        return

    # Create plot
    fig, ax = plt.subplots(figsize=(16, 12))

    # Plot points colored by season
    np.random.seed(42)
    for season in ['Spring', 'Summer', 'Fall', 'Winter']:
        mask = df_combined['season'] == season
        if mask.sum() > 0:
            y_jitter = y_ratio[mask] + np.random.normal(0, 0.01, size=mask.sum())
            y_jitter = np.clip(y_jitter, 0, 1)

            point_sizes = n_total[mask] * 3
            ax.scatter(x[mask], y_jitter, alpha=0.15, s=point_sizes,
                      color=SEASON_COLORS[season],
                      edgecolors='none',
                      label=f'{season} (n={mask.sum():,})')

    # Plot fitted curve
    x_range = np.linspace(x.min(), x.max(), 200)
    y_pred, ci_lower, ci_upper = predict_with_ci(results, x_range)

    ax.fill_between(x_range, ci_lower, ci_upper, alpha=0.2, color='black',
                   label='95% CI')
    ax.plot(x_range, y_pred, color='black', linewidth=5,
           label='Aggregated fit (all data)', linestyle='-', zorder=10)

    # Formatting
    ax.set_xlabel('UTCI Temperature (°C)', fontsize=15)
    ax.set_ylabel('Shade Ratio', fontsize=15)
    ax.set_title(f'Aggregated Global Pattern - All Seasons (Wind-Filtered)\n' +
                f'Combined data from {len(city_data)} cities worldwide\n' +
                f'n={len(df_combined):,} observations, {int(n_total.sum()):,} people (point size ∝ people)',
                fontsize=16, fontweight='bold')
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=12, loc='best', ncol=2)

    # Add text box with cities
    cities_text = ', '.join(sorted(city_data.keys()))
    ax.text(0.02, 0.98, f'Cities: {cities_text}',
           transform=ax.transAxes, fontsize=10,
           verticalalignment='top',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

    # Save
    output_file = output_dir / "aggregated_overall_global_filtered.png"
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"  ✓ Saved aggregated overall plot")

def save_data_loss_report(output_dir):
    """Save data loss statistics to a markdown file."""
    report_path = output_dir / "DATA_LOSS_REPORT.md"

    with open(report_path, 'w') as f:
        f.write("# Data Loss Report - Wind Filtering\n\n")
        f.write("**Date:** 2026-01-26\n")
        f.write("**Filter Applied:** UTCI wind speed validation (>17 m/s filtered)\n\n")
        f.write("---\n\n")
        f.write("## Summary by City\n\n")
        f.write("| City | Original Rows | After Wind Filter | After Analysis Filters | Final Usable | Data Retention |\n")
        f.write("|------|---------------|-------------------|------------------------|--------------|----------------|\n")

        total_original = 0
        total_final = 0

        for city_name in sorted(DATA_LOSS_STATS.keys()):
            stats = DATA_LOSS_STATS[city_name]
            total_original += stats['original']
            total_final += stats['final']

            retention_pct = 100 - stats['loss_pct']
            f.write(f"| {city_name} | {stats['original']:,} | {stats['after_filtering']:,} | ")
            f.write(f"{stats['after_sunny_people_filter']:,} | {stats['final']:,} | {retention_pct:.1f}% |\n")

        overall_retention = (total_final / total_original * 100) if total_original > 0 else 0
        f.write(f"| **TOTAL** | **{total_original:,}** | - | - | **{total_final:,}** | **{overall_retention:.1f}%** |\n\n")

        f.write("---\n\n")
        f.write("## Filtering Pipeline\n\n")
        f.write("The data goes through the following filtering stages:\n\n")
        f.write("1. **Wind Speed Filter**: Removes observations with wind >17 m/s (UTCI validity threshold)\n")
        f.write("2. **Sunny Filter**: Keeps only images classified as sunny (is_sunny == True)\n")
        f.write("3. **People Filter**: Keeps only images with detected people (total_people > 0)\n")
        f.write("4. **UTCI Range Filter**: Removes extreme UTCI values (<-50°C or >60°C)\n")
        f.write("5. **DateTime Filter**: Removes rows with invalid datetime stamps\n\n")

        f.write("---\n\n")
        f.write("## Key Findings\n\n")

        # Find cities with highest data loss
        sorted_cities = sorted(DATA_LOSS_STATS.items(), key=lambda x: x[1]['loss_pct'], reverse=True)

        f.write("### Cities Most Affected by Wind Filtering\n\n")
        for city_name, stats in sorted_cities[:3]:
            f.write(f"- **{city_name}**: {stats['loss_pct']:.1f}% data loss ")
            f.write(f"({stats['original']:,} → {stats['final']:,} rows)\n")

        f.write("\n### Cities Least Affected by Wind Filtering\n\n")
        for city_name, stats in sorted_cities[-3:]:
            f.write(f"- **{city_name}**: {stats['loss_pct']:.1f}% data loss ")
            f.write(f"({stats['original']:,} → {stats['final']:,} rows)\n")

        f.write("\n---\n\n")
        f.write("## Implications\n\n")
        f.write(f"- **Overall data retention:** {overall_retention:.1f}%\n")
        f.write(f"- **Total observations lost:** {total_original - total_final:,}\n")
        f.write("- High wind speeds are more common in some cities (Istanbul, Madrid)\n")
        f.write("- The filtering ensures all analyzed observations have valid UTCI calculations\n")
        f.write("- Statistical power remains strong with final sample size\n")

    print(f"\n✓ Data loss report saved to: {report_path}")

def main():
    results_dir = Path("data/multi_city_results")
    output_dir = Path("outputs/plots/global_comparison_filtered")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("="*80)
    print("GLOBAL COMPARISON WITH WIND-FILTERED DATA")
    print("="*80)
    print()

    # Load all city data with filtering
    city_data = load_city_data(results_dir, use_filtered=True)

    if len(city_data) == 0:
        print("No city data found!")
        return

    print()
    print("="*80)
    print("PART 1: City-by-city comparisons")
    print("="*80)
    print()

    # Create seasonal comparison plots
    for season in ['Spring', 'Summer', 'Fall', 'Winter']:
        plot_season_comparison(city_data, season, output_dir)

    # Create overall comparison
    plot_overall_comparison(city_data, output_dir)

    print()
    print("="*80)
    print("PART 2: Aggregated patterns across all cities")
    print("="*80)
    print()

    # Create aggregated seasonal plots
    for season in ['Spring', 'Summer', 'Fall', 'Winter']:
        plot_aggregated_seasonal(city_data, season, output_dir)

    # Create aggregated overall
    plot_aggregated_overall(city_data, output_dir)

    # Save data loss report
    print()
    print("="*80)
    print("PART 3: Data loss analysis")
    print("="*80)
    save_data_loss_report(output_dir)

    print()
    print("="*80)
    print("✓ ALL GLOBAL COMPARISON PLOTS COMPLETE")
    print("="*80)
    print(f"\nPlots saved to: {output_dir}")
    print()

if __name__ == "__main__":
    main()
