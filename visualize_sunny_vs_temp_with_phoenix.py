#!/usr/bin/env python3
# ABOUTME: Sunny classification vs temperature including Phoenix
# ABOUTME: Shows relationship between temperature and sunny classification

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import statsmodels.api as sm
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

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

def plot_overall_sunny_vs_temp_with_phoenix(results_dir, phoenix_csv, output_dir):
    """Create overall sunny vs temperature comparison including Phoenix."""
    print("\nProcessing global comparison...")

    fig, ax = plt.subplots(figsize=(16, 12))

    cities_plotted = 0
    phoenix_included = False

    # Process Phoenix first
    print("  Loading Phoenix...")
    df_phoenix = pd.read_csv(phoenix_csv)

    if 'utci_C' in df_phoenix.columns:
        df = df_phoenix.dropna(subset=['utci_C'])
        df = df[(df['utci_C'] >= -50) & (df['utci_C'] <= 60)]

        if len(df) >= 50:
            # Handle is_sunny as boolean
            df = df.dropna(subset=['is_sunny'])
            df['is_sunny_binary'] = df['is_sunny'].astype(bool).astype(int)
            x = df['utci_C'].values
            y = df['is_sunny_binary'].values

            results = fit_logistic_quadratic_binary(x, y)

            if results is not None:
                x_range = np.linspace(x.min(), x.max(), 200)
                y_pred, ci_lower, ci_upper = predict_with_ci(results, x_range)

                color = CITY_COLORS['Phoenix']
                ax.fill_between(x_range, ci_lower, ci_upper, alpha=0.12, color=color)
                ax.plot(x_range, y_pred, color=color, linewidth=4.5,
                       label=f'Phoenix (n={len(df):,}, {y.mean()*100:.1f}% sunny)',
                       alpha=0.95)
                cities_plotted += 1
                phoenix_included = True
                print(f"    ✓ Phoenix: {len(df)} images, {y.mean()*100:.1f}% sunny")

    # Process other cities
    csv_files = list(results_dir.glob("*/*_analyzed_with_utci.csv"))

    for csv_file in sorted(csv_files):
        city_name = csv_file.parent.name
        print(f"  Loading {city_name}...")

        df = pd.read_csv(csv_file)

        if 'utci_C' not in df.columns:
            continue

        df = df.dropna(subset=['utci_C'])
        df = df[(df['utci_C'] >= -50) & (df['utci_C'] <= 60)]

        if len(df) < 50:
            continue

        df['is_sunny_binary'] = (df['is_sunny'].astype(str).str.lower() == 'true').astype(int)
        x = df['utci_C'].values
        y = df['is_sunny_binary'].values

        results = fit_logistic_quadratic_binary(x, y)

        if results is None:
            continue

        x_range = np.linspace(x.min(), x.max(), 200)
        y_pred, ci_lower, ci_upper = predict_with_ci(results, x_range)

        color = CITY_COLORS.get(city_name, 'gray')

        ax.fill_between(x_range, ci_lower, ci_upper, alpha=0.1, color=color)
        ax.plot(x_range, y_pred, color=color, linewidth=3.5,
               label=f'{city_name} (n={len(df):,}, {y.mean()*100:.1f}% sunny)',
               alpha=0.8)

        cities_plotted += 1
        print(f"    ✓ {city_name}: {len(df)} images, {y.mean()*100:.1f}% sunny")

    if cities_plotted == 0:
        print("  No cities with sufficient data")
        plt.close()
        return

    # Formatting
    ax.set_xlabel('UTCI Temperature (°C)', fontsize=15)
    ax.set_ylabel('Probability of Sunny Classification', fontsize=15)
    title = 'Global Comparison\nSunny Classification vs UTCI Temperature'
    if phoenix_included:
        title += '\n(Phoenix/Arizona highlighted)'
    ax.set_title(title, fontsize=17, fontweight='bold')
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=11, loc='best', ncol=2)

    # Save
    output_file = output_dir / "global_sunny_vs_temperature.png"
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"  ✓ Saved global comparison ({cities_plotted} cities)")

def main():
    results_dir = Path("data/multi_city_results")
    phoenix_csv = Path("archive/phoenix_results/Phoenix_1840020568_with_utci.csv")
    output_dir = Path("outputs/plots/global_comparison")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("="*80)
    print("GLOBAL SUNNY VS TEMPERATURE (INCLUDING PHOENIX)")
    print("="*80)

    plot_overall_sunny_vs_temp_with_phoenix(results_dir, phoenix_csv, output_dir)

    print()
    print("="*80)
    print("✓ COMPLETE")
    print("="*80)
    print(f"\nPlots saved to: {output_dir}")
    print()

if __name__ == "__main__":
    main()
