#!/usr/bin/env python3
# ABOUTME: Visualize sunny image classification vs temperature for each city
# ABOUTME: Shows relationship between temperature and sunny classification probability

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import statsmodels.api as sm
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# City colors
CITY_COLORS = {
    'Buenos-Aires': '#e74c3c',
    'Istanbul': '#3498db',
    'Madrid': '#f39c12',
    'Mumbai': '#9b59b6',
    'Singapore': '#2ecc71',
    'Cape-Town': '#1abc9c',
    'Osaka': '#e91e63',
}

def fit_logistic_quadratic_binary(x, y_binary):
    """Fit binomial logistic regression for binary classification."""
    X = np.column_stack([np.ones(len(x)), x, x**2])

    model = sm.GLM(y_binary, X, family=sm.families.Binomial())
    try:
        results = model.fit()
        return results
    except Exception as e:
        print(f"    Warning: Model fitting failed: {e}")
        return None

def predict_with_ci(results, x_pred, alpha=0.05):
    """Get predictions and confidence intervals."""
    X_pred = np.column_stack([np.ones(len(x_pred)), x_pred, x_pred**2])
    predictions = results.get_prediction(X_pred)
    pred_summary = predictions.summary_frame(alpha=alpha)
    return pred_summary['mean'].values, pred_summary['mean_ci_lower'].values, pred_summary['mean_ci_upper'].values

def plot_city_sunny_vs_temp(city_name, csv_path, output_dir):
    """Create sunny vs temperature plot for a single city."""
    print(f"\nProcessing {city_name}...")

    # Load data
    df = pd.read_csv(csv_path)

    # Check for required columns
    if 'utci_C' not in df.columns:
        print(f"  Skipping {city_name} - no UTCI data")
        return

    # Filter for valid UTCI
    df = df.dropna(subset=['utci_C'])
    before_filter = len(df)
    df = df[(df['utci_C'] >= -50) & (df['utci_C'] <= 60)]
    if len(df) < before_filter:
        print(f"  Filtered out {before_filter - len(df)} rows with invalid UTCI")

    if len(df) < 50:
        print(f"  Skipping {city_name} - too few observations ({len(df)})")
        return

    # Create binary sunny variable
    df['is_sunny_binary'] = (df['is_sunny'].astype(str).str.lower() == 'true').astype(int)

    x = df['utci_C'].values
    y = df['is_sunny_binary'].values

    print(f"  Total images: {len(df)}")
    print(f"  Sunny images: {y.sum()} ({y.mean()*100:.1f}%)")
    print(f"  UTCI range: {x.min():.1f}°C to {x.max():.1f}°C")

    # Fit model
    results = fit_logistic_quadratic_binary(x, y)

    if results is None:
        return

    # Create plot
    fig, ax = plt.subplots(figsize=(12, 8))

    # Bin data for visualization
    bins = np.linspace(x.min(), x.max(), 30)
    bin_centers = (bins[:-1] + bins[1:]) / 2
    bin_indices = np.digitize(x, bins)

    bin_means = []
    bin_counts = []
    for i in range(1, len(bins)):
        mask = bin_indices == i
        if mask.sum() > 0:
            bin_means.append(y[mask].mean())
            bin_counts.append(mask.sum())
        else:
            bin_means.append(np.nan)
            bin_counts.append(0)

    # Plot binned observations
    valid_mask = ~np.isnan(bin_means)
    bin_sizes = np.array(bin_counts)[valid_mask] * 3
    ax.scatter(bin_centers[valid_mask], np.array(bin_means)[valid_mask],
              s=bin_sizes, alpha=0.5,
              color=CITY_COLORS.get(city_name, 'gray'),
              edgecolors='black', linewidth=0.5,
              label='Binned observations (size ∝ count)')

    # Plot fitted curve
    x_range = np.linspace(x.min(), x.max(), 200)
    y_pred, ci_lower, ci_upper = predict_with_ci(results, x_range)

    ax.fill_between(x_range, ci_lower, ci_upper, alpha=0.2,
                   color=CITY_COLORS.get(city_name, 'gray'),
                   label='95% CI')
    ax.plot(x_range, y_pred, color=CITY_COLORS.get(city_name, 'gray'),
           linewidth=3, label='Binomial Logistic (quadratic)')

    # Formatting
    ax.set_xlabel('UTCI Temperature (°C)', fontsize=13)
    ax.set_ylabel('Probability of Sunny Classification', fontsize=13)
    ax.set_title(f'{city_name}\nSunny Classification vs UTCI Temperature\n' +
                f'n={len(df)} images, {y.sum()} sunny ({y.mean()*100:.1f}%)',
                fontsize=14, fontweight='bold')
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=11, loc='best')

    # Save
    output_file = output_dir / f"{city_name.replace(' ', '-')}_sunny_vs_temperature.png"
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"  ✓ Saved plot")

def plot_overall_sunny_vs_temp(results_dir, output_dir):
    """Create overall sunny vs temperature comparison across all cities."""
    print("\nProcessing overall comparison...")

    fig, ax = plt.subplots(figsize=(16, 12))

    csv_files = list(results_dir.glob("*/*_analyzed_with_utci.csv"))

    cities_plotted = 0

    for csv_file in sorted(csv_files):
        city_name = csv_file.parent.name

        # Load data
        df = pd.read_csv(csv_file)

        if 'utci_C' not in df.columns:
            continue

        # Filter for valid UTCI
        df = df.dropna(subset=['utci_C'])
        df = df[(df['utci_C'] >= -50) & (df['utci_C'] <= 60)]

        if len(df) < 50:
            continue

        # Create binary sunny variable
        df['is_sunny_binary'] = (df['is_sunny'].astype(str).str.lower() == 'true').astype(int)

        x = df['utci_C'].values
        y = df['is_sunny_binary'].values

        # Fit model
        results = fit_logistic_quadratic_binary(x, y)

        if results is None:
            continue

        # Plot fitted curve
        x_range = np.linspace(x.min(), x.max(), 200)
        y_pred, ci_lower, ci_upper = predict_with_ci(results, x_range)

        color = CITY_COLORS.get(city_name, 'gray')

        ax.fill_between(x_range, ci_lower, ci_upper, alpha=0.1, color=color)
        ax.plot(x_range, y_pred, color=color, linewidth=3,
               label=f'{city_name} (n={len(df)}, {y.mean()*100:.1f}% sunny)',
               alpha=0.85)

        cities_plotted += 1

    if cities_plotted == 0:
        print("  No cities with sufficient data")
        plt.close()
        return

    # Formatting
    ax.set_xlabel('UTCI Temperature (°C)', fontsize=15)
    ax.set_ylabel('Probability of Sunny Classification', fontsize=15)
    ax.set_title('Cross-City Comparison\nSunny Classification vs UTCI Temperature',
                fontsize=17, fontweight='bold')
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=12, loc='best', ncol=2)

    # Save
    output_file = output_dir / "all_cities_sunny_vs_temperature.png"
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"  ✓ Saved overall comparison ({cities_plotted} cities)")

def main():
    results_dir = Path("data/multi_city_results")
    output_dir = Path("outputs/plots/sunny_vs_temperature")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("="*80)
    print("SUNNY CLASSIFICATION VS TEMPERATURE VISUALIZATION")
    print("="*80)

    # Find all UTCI-enriched CSVs
    csv_files = list(results_dir.glob("*/*_analyzed_with_utci.csv"))

    print(f"\nFound {len(csv_files)} cities with UTCI data\n")

    # Create individual city plots
    for csv_file in sorted(csv_files):
        city_name = csv_file.parent.name
        plot_city_sunny_vs_temp(city_name, csv_file, output_dir)

    # Create overall comparison
    plot_overall_sunny_vs_temp(results_dir, output_dir)

    print("\n" + "="*80)
    print("✓ ALL SUNNY VS TEMPERATURE VISUALIZATIONS COMPLETE")
    print("="*80)
    print(f"\nPlots saved to: {output_dir}")
    print()

if __name__ == "__main__":
    main()
