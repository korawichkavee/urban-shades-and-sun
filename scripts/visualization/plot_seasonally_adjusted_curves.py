#!/usr/bin/env python3
"""
Plot shade preference curves with seasonally-adjusted weights.

Creates plots for:
1. WITH Temp-IPW version
2. WITHOUT Temp-IPW version
3. Comparison plots showing effect of seasonal adjustment

Purpose: Final publication-ready plots with seasonal standardization applied.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import statsmodels.api as sm
import statsmodels.formula.api as smf
from pathlib import Path
import sys

# Add project root
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 10
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['legend.fontsize'] = 9

# Output directory
output_dir = Path("outputs/analysis/seasonally_adjusted_plots")
output_dir.mkdir(parents=True, exist_ok=True)

def fit_quadratic_curve(df, weight_col, utci_grid):
    """Fit quadratic binomial GLM and predict on grid.

    Parameters
    ----------
    df : pd.DataFrame
        Must have 'in_shade' and 'utci_C' columns
    weight_col : str
        Name of weight column
    utci_grid : np.ndarray
        UTCI values to predict on

    Returns
    -------
    dict
        predictions, model, etc.
    """
    # Prepare data
    y = df['in_shade'].values
    X = pd.DataFrame({
        'const': 1,
        'utci': df['utci_C'].values,
        'utci_sq': df['utci_C'].values ** 2
    })

    weights = df[weight_col].values

    # Fit model
    model = sm.GLM(y, X, family=sm.families.Binomial(), freq_weights=weights).fit()

    # Predict on grid
    X_grid = pd.DataFrame({
        'const': 1,
        'utci': utci_grid,
        'utci_sq': utci_grid ** 2
    })

    predictions = model.predict(X_grid)

    return {
        'predictions': predictions,
        'model': model,
        'utci_grid': utci_grid
    }

def plot_single_city_curves(city, version_label, with_temp):
    """Plot curves for a single city with all correction stages.

    Parameters
    ----------
    city : str
        'seattle' or 'new-york-city'
    version_label : str
        'WITH Temp-IPW' or 'WITHOUT Temp-IPW'
    with_temp : bool
        Whether to include Temp-IPW in final weights
    """
    # Load data
    if with_temp:
        file_suffix = 'seasonal_and_temp'
    else:
        file_suffix = 'seasonal_no_temp'

    input_path = f"final_run_outputs/{city}/{city}_final_analysis_with_{file_suffix}.csv"
    print(f"\nLoading {city} ({version_label}): {input_path}")

    df = pd.read_csv(input_path)
    print(f"  Loaded {len(df):,} images")

    # UTCI grid for predictions
    utci_grid = np.linspace(-30, 40, 200)

    # Fit curves
    print(f"  Fitting curves...")

    # Raw (unweighted)
    raw_result = fit_quadratic_curve(df, 'w_sr_ipw', utci_grid)  # Use w_sr_ipw with all 1s as proxy
    # Actually, for raw we want no weights
    y = df['in_shade'].values
    X = pd.DataFrame({
        'const': 1,
        'utci': df['utci_C'].values,
        'utci_sq': df['utci_C'].values ** 2
    })
    model_raw = sm.GLM(y, X, family=sm.families.Binomial()).fit()
    X_grid = pd.DataFrame({
        'const': 1,
        'utci': utci_grid,
        'utci_sq': utci_grid ** 2
    })
    pred_raw = model_raw.predict(X_grid)

    # SR-IPW only
    pred_sr = fit_quadratic_curve(df, 'w_sr_ipw', utci_grid)['predictions']

    # SR-IPW + DCWP
    df['w_sr_dcwp'] = df['w_sr_ipw'] * df['w_dcwp']
    pred_sr_dcwp = fit_quadratic_curve(df, 'w_sr_dcwp', utci_grid)['predictions']

    # Final (with seasonal)
    pred_final = fit_quadratic_curve(df, 'w_final', utci_grid)['predictions']

    # Create figure
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    city_name = 'Seattle' if city == 'seattle' else 'New York City'
    fig.suptitle(f'{city_name} Shade Preference Curves\n{version_label}',
                 fontsize=14, fontweight='bold')

    # Plot 1: All correction stages
    ax = axes[0, 0]
    ax.plot(utci_grid, pred_raw * 100, 'k-', linewidth=2, label='Raw (unweighted)', alpha=0.7)
    ax.plot(utci_grid, pred_sr * 100, 'b-', linewidth=2, label='+ SR-IPW', alpha=0.7)
    ax.plot(utci_grid, pred_sr_dcwp * 100, 'g-', linewidth=2, label='+ DCWP', alpha=0.7)
    ax.plot(utci_grid, pred_final * 100, 'r-', linewidth=2.5, label='+ Seasonal Adj (Final)', alpha=0.9)
    ax.set_xlabel('UTCI (°C)')
    ax.set_ylabel('Shade Preference (%)')
    ax.set_title('Progressive Correction Stages')
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(-30, 40)
    ax.set_ylim(0, 100)

    # Plot 2: Effect decomposition
    ax = axes[0, 1]
    effect_sr = (pred_sr - pred_raw) * 100
    effect_dcwp = (pred_sr_dcwp - pred_sr) * 100
    effect_seasonal = (pred_final - pred_sr_dcwp) * 100

    ax.plot(utci_grid, effect_sr, 'b-', linewidth=2, label='SR-IPW effect', alpha=0.7)
    ax.plot(utci_grid, effect_dcwp, 'g-', linewidth=2, label='DCWP effect', alpha=0.7)
    ax.plot(utci_grid, effect_seasonal, 'orange', linewidth=2, label='Seasonal effect', alpha=0.7)
    ax.axhline(0, color='k', linestyle='--', linewidth=1, alpha=0.5)
    ax.set_xlabel('UTCI (°C)')
    ax.set_ylabel('Effect Size (pp)')
    ax.set_title('Correction Effects by UTCI')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(-30, 40)

    # Plot 3: Sample size by UTCI
    ax = axes[1, 0]
    bins = np.arange(-40, 45, 2)
    df['utci_bin'] = pd.cut(df['utci_C'], bins=bins)
    bin_counts = df.groupby('utci_bin', observed=True).size()
    bin_centers = [(b.left + b.right) / 2 for b in bin_counts.index]

    ax.bar(bin_centers, bin_counts.values, width=1.8, alpha=0.6, edgecolor='black')
    ax.set_xlabel('UTCI (°C)')
    ax.set_ylabel('Number of Images')
    ax.set_title('Sample Size Distribution')
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_xlim(-30, 40)

    # Add quality threshold lines
    ax.axhline(500, color='orange', linestyle='--', linewidth=1, alpha=0.7, label='N=500 (good)')
    ax.axhline(1000, color='green', linestyle='--', linewidth=1, alpha=0.7, label='N=1000 (excellent)')
    ax.legend(loc='upper right', fontsize=8)

    # Plot 4: Aggregate statistics
    ax = axes[1, 1]
    ax.axis('off')

    # Compute aggregate estimates
    raw_agg = df['in_shade'].mean()
    sr_agg = (df['in_shade'] * df['w_sr_ipw']).sum() / df['w_sr_ipw'].sum()
    sr_dcwp_agg = (df['in_shade'] * df['w_sr_dcwp']).sum() / df['w_sr_dcwp'].sum()
    final_agg = (df['in_shade'] * df['w_final']).sum() / df['w_final'].sum()

    # Effective sample size
    n_eff = (df['w_final'].sum() ** 2) / (df['w_final'] ** 2).sum()
    n_eff_pct = n_eff / len(df) * 100

    # Create text
    stats_text = f"""
Aggregate Estimates:
━━━━━━━━━━━━━━━━━━━━━━━
Raw (unweighted):     {raw_agg*100:>6.2f}%
+ SR-IPW:             {sr_agg*100:>6.2f}%
+ DCWP:               {sr_dcwp_agg*100:>6.2f}%
+ Seasonal (Final):   {final_agg*100:>6.2f}%

Effects:
━━━━━━━━━━━━━━━━━━━━━━━
SR-IPW:               {(sr_agg - raw_agg)*100:+6.2f} pp
DCWP:                 {(sr_dcwp_agg - sr_agg)*100:+6.2f} pp
Seasonal:             {(final_agg - sr_dcwp_agg)*100:+6.2f} pp
Total:                {(final_agg - raw_agg)*100:+6.2f} pp

Sample Quality:
━━━━━━━━━━━━━━━━━━━━━━━
Raw N:                {len(df):>8,}
Effective N:          {n_eff:>8,.0f}
N_eff %:              {n_eff_pct:>8.1f}%
    """

    ax.text(0.1, 0.9, stats_text, transform=ax.transAxes,
            fontsize=9, verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

    plt.tight_layout()

    # Save
    suffix = 'with_temp' if with_temp else 'no_temp'
    output_path = output_dir / f'{city}_curves_{suffix}'
    plt.savefig(f'{output_path}.png', dpi=300, bbox_inches='tight')
    plt.savefig(f'{output_path}.pdf', bbox_inches='tight')
    print(f"  Saved: {output_path}.png/pdf")

    plt.close()

    return {
        'city': city,
        'raw': raw_agg,
        'sr': sr_agg,
        'sr_dcwp': sr_dcwp_agg,
        'final': final_agg,
        'n_eff': n_eff,
        'n_eff_pct': n_eff_pct
    }

def plot_cross_city_comparison(version_label, with_temp):
    """Create cross-city comparison plot.

    Parameters
    ----------
    version_label : str
        'WITH Temp-IPW' or 'WITHOUT Temp-IPW'
    with_temp : bool
        Whether to include Temp-IPW
    """
    print(f"\n{'='*70}")
    print(f"Cross-City Comparison: {version_label}")
    print(f"{'='*70}")

    cities = ['seattle', 'new-york-city']
    city_names = ['Seattle', 'New York City']
    colors = ['#1f77b4', '#ff7f0e']  # Blue, Orange

    # Load data
    dfs = {}
    for city in cities:
        if with_temp:
            file_suffix = 'seasonal_and_temp'
        else:
            file_suffix = 'seasonal_no_temp'

        input_path = f"final_run_outputs/{city}/{city}_final_analysis_with_{file_suffix}.csv"
        dfs[city] = pd.read_csv(input_path)
        print(f"  Loaded {city}: {len(dfs[city]):,} images")

    # UTCI grid
    utci_grid = np.linspace(-30, 40, 200)

    # Fit curves for each city
    predictions = {}
    for city in cities:
        predictions[city] = {
            'raw': fit_quadratic_curve(dfs[city], 'w_sr_ipw', utci_grid),  # Proxy for unweighted
            'final': fit_quadratic_curve(dfs[city], 'w_final', utci_grid)
        }

        # Actually compute raw properly
        y = dfs[city]['in_shade'].values
        X = pd.DataFrame({
            'const': 1,
            'utci': dfs[city]['utci_C'].values,
            'utci_sq': dfs[city]['utci_C'].values ** 2
        })
        model_raw = sm.GLM(y, X, family=sm.families.Binomial()).fit()
        X_grid = pd.DataFrame({
            'const': 1,
            'utci': utci_grid,
            'utci_sq': utci_grid ** 2
        })
        predictions[city]['raw']['predictions'] = model_raw.predict(X_grid)

    # Create figure
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f'Cross-City Shade Preference Comparison\n{version_label}',
                 fontsize=14, fontweight='bold')

    # Plot 1: Raw curves
    ax = axes[0, 0]
    for city, city_name, color in zip(cities, city_names, colors):
        pred = predictions[city]['raw']['predictions']
        ax.plot(utci_grid, pred * 100, color=color, linewidth=2.5,
                label=city_name, alpha=0.8)

    ax.set_xlabel('UTCI (°C)')
    ax.set_ylabel('Shade Preference (%)')
    ax.set_title('Raw (Unweighted) Curves')
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(-30, 40)
    ax.set_ylim(0, 100)

    # Plot 2: Final curves
    ax = axes[0, 1]
    for city, city_name, color in zip(cities, city_names, colors):
        pred = predictions[city]['final']['predictions']
        ax.plot(utci_grid, pred * 100, color=color, linewidth=2.5,
                label=city_name, alpha=0.8)

    ax.set_xlabel('UTCI (°C)')
    ax.set_ylabel('Shade Preference (%)')
    ax.set_title('Final (Seasonally Adjusted) Curves')
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(-30, 40)
    ax.set_ylim(0, 100)

    # Plot 3: Difference (Seattle - NYC)
    ax = axes[1, 0]

    diff_raw = (predictions['seattle']['raw']['predictions'] -
                predictions['new-york-city']['raw']['predictions']) * 100
    diff_final = (predictions['seattle']['final']['predictions'] -
                  predictions['new-york-city']['final']['predictions']) * 100

    ax.plot(utci_grid, diff_raw, 'k--', linewidth=2, label='Raw difference', alpha=0.7)
    ax.plot(utci_grid, diff_final, 'r-', linewidth=2.5, label='Final difference', alpha=0.8)
    ax.axhline(0, color='gray', linestyle='-', linewidth=1, alpha=0.5)

    ax.set_xlabel('UTCI (°C)')
    ax.set_ylabel('Difference (Seattle - NYC, pp)')
    ax.set_title('Cross-City Difference')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(-30, 40)

    # Plot 4: Aggregate comparison
    ax = axes[1, 1]

    # Compute aggregates
    results = {}
    for city in cities:
        df = dfs[city]
        results[city] = {
            'raw': df['in_shade'].mean(),
            'final': (df['in_shade'] * df['w_final']).sum() / df['w_final'].sum()
        }

    # Bar chart
    x = np.arange(2)
    width = 0.35

    raw_vals = [results['seattle']['raw'] * 100, results['new-york-city']['raw'] * 100]
    final_vals = [results['seattle']['final'] * 100, results['new-york-city']['final'] * 100]

    ax.bar(x - width/2, raw_vals, width, label='Raw', alpha=0.7, color='gray')
    ax.bar(x + width/2, final_vals, width, label='Final (Seasonal Adj)', alpha=0.8, color='red')

    ax.set_ylabel('Shade Preference (%)')
    ax.set_title('Aggregate Estimates')
    ax.set_xticks(x)
    ax.set_xticklabels(city_names)
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')

    # Add value labels
    for i, (raw, final) in enumerate(zip(raw_vals, final_vals)):
        ax.text(i - width/2, raw + 2, f'{raw:.1f}%', ha='center', fontsize=9)
        ax.text(i + width/2, final + 2, f'{final:.1f}%', ha='center', fontsize=9, fontweight='bold')

    # Add difference annotation
    diff_raw_agg = results['seattle']['raw'] - results['new-york-city']['raw']
    diff_final_agg = results['seattle']['final'] - results['new-york-city']['final']

    ax.text(0.98, 0.02,
            f"Gap (S - NYC):\nRaw: {diff_raw_agg*100:+.1f} pp\nFinal: {diff_final_agg*100:+.1f} pp",
            transform=ax.transAxes, fontsize=9, verticalalignment='bottom',
            horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()

    # Save
    suffix = 'with_temp' if with_temp else 'no_temp'
    output_path = output_dir / f'cross_city_comparison_{suffix}'
    plt.savefig(f'{output_path}.png', dpi=300, bbox_inches='tight')
    plt.savefig(f'{output_path}.pdf', bbox_inches='tight')
    print(f"\nSaved: {output_path}.png/pdf")

    plt.close()

def main():
    """Main plotting pipeline."""

    print("="*70)
    print("SEASONALLY-ADJUSTED SHADE PREFERENCE CURVES")
    print("="*70)

    # Version 1: WITH Temp-IPW
    print("\n" + "="*70)
    print("VERSION 1: WITH Temp-IPW")
    print("="*70)

    results_with = []
    for city in ['seattle', 'new-york-city']:
        result = plot_single_city_curves(city, 'WITH Temp-IPW', with_temp=True)
        results_with.append(result)

    plot_cross_city_comparison('WITH Temp-IPW', with_temp=True)

    # Version 2: WITHOUT Temp-IPW
    print("\n" + "="*70)
    print("VERSION 2: WITHOUT Temp-IPW")
    print("="*70)

    results_without = []
    for city in ['seattle', 'new-york-city']:
        result = plot_single_city_curves(city, 'WITHOUT Temp-IPW', with_temp=False)
        results_without.append(result)

    plot_cross_city_comparison('WITHOUT Temp-IPW', with_temp=False)

    # Summary table
    print("\n" + "="*70)
    print("SUMMARY TABLE")
    print("="*70)

    summary_data = []
    for result, version in [(results_with, 'WITH Temp-IPW'), (results_without, 'WITHOUT Temp-IPW')]:
        for r in result:
            summary_data.append({
                'Version': version,
                'City': r['city'],
                'Raw (%)': r['raw'] * 100,
                'SR-IPW (%)': r['sr'] * 100,
                'SR+DCWP (%)': r['sr_dcwp'] * 100,
                'Final (%)': r['final'] * 100,
                'N_eff': r['n_eff'],
                'N_eff (%)': r['n_eff_pct']
            })

    summary_df = pd.DataFrame(summary_data)

    # Save
    summary_path = output_dir / 'seasonally_adjusted_summary.csv'
    summary_df.to_csv(summary_path, index=False)
    print(f"\nSummary table saved: {summary_path}")

    # Print
    print("\n" + summary_df.to_string(index=False))

    print("\n" + "="*70)
    print("DONE")
    print("="*70)
    print(f"\nAll plots saved to: {output_dir}/")

if __name__ == "__main__":
    main()
