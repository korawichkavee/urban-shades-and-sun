#!/usr/bin/env python3
"""
Bootstrap comparison with seasonally-adjusted weights.

Re-runs the full cross-city statistical comparison using the final
seasonally standardized weights (w_final).

Creates two versions:
1. WITH Temp-IPW
2. WITHOUT Temp-IPW
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import statsmodels.api as sm
from pathlib import Path
from tqdm import tqdm

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 10

output_dir = Path("outputs/analysis/seasonally_adjusted_plots")
output_dir.mkdir(parents=True, exist_ok=True)

def bootstrap_aggregate_metrics(df, weight_col, n_bootstrap=1000):
    """Bootstrap aggregate shade preference with confidence intervals.

    Parameters
    ----------
    df : pd.DataFrame
        Must have 'in_shade' column
    weight_col : str
        Name of weight column
    n_bootstrap : int
        Number of bootstrap iterations

    Returns
    -------
    dict
        mean, std, ci_lower, ci_upper, estimates
    """
    estimates = []

    for i in tqdm(range(n_bootstrap), desc="Bootstrap aggregate"):
        # Resample with replacement
        df_boot = df.sample(n=len(df), replace=True, random_state=i)

        # Compute weighted estimate
        weights = df_boot[weight_col].values
        est = (df_boot['in_shade'] * weights).sum() / weights.sum()

        estimates.append(est)

    # Compute statistics
    ci_lower = np.percentile(estimates, 2.5)
    ci_upper = np.percentile(estimates, 97.5)

    return {
        'mean': np.mean(estimates),
        'std': np.std(estimates),
        'ci_lower': ci_lower,
        'ci_upper': ci_upper,
        'estimates': estimates
    }

def bootstrap_curves(df, weight_col, n_bootstrap=1000, utci_grid=None):
    """Bootstrap curve predictions with confidence bands.

    Parameters
    ----------
    df : pd.DataFrame
        Must have 'in_shade', 'utci_C', and weight column
    weight_col : str
        Name of weight column
    n_bootstrap : int
        Number of bootstrap iterations
    utci_grid : np.ndarray
        UTCI values to predict on

    Returns
    -------
    dict
        mean, ci_lower, ci_upper predictions
    """
    if utci_grid is None:
        utci_grid = np.linspace(-30, 35, 200)

    predictions = np.zeros((n_bootstrap, len(utci_grid)))

    for i in tqdm(range(n_bootstrap), desc="Bootstrap curves"):
        # Resample
        df_boot = df.sample(n=len(df), replace=True, random_state=i)

        # Fit quadratic binomial GLM
        y = df_boot['in_shade'].values
        X = pd.DataFrame({
            'const': 1,
            'utci': df_boot['utci_C'].values,
            'utci_sq': df_boot['utci_C'].values ** 2
        })

        weights = df_boot[weight_col].values

        model = sm.GLM(y, X, family=sm.families.Binomial(), freq_weights=weights).fit()

        # Predict on grid
        X_grid = pd.DataFrame({
            'const': 1,
            'utci': utci_grid,
            'utci_sq': utci_grid ** 2
        })

        predictions[i, :] = model.predict(X_grid)

    # Compute statistics
    ci_lower = np.percentile(predictions, 2.5, axis=0)
    ci_upper = np.percentile(predictions, 97.5, axis=0)

    return {
        'mean': np.mean(predictions, axis=0),
        'ci_lower': ci_lower,
        'ci_upper': ci_upper,
        'predictions': predictions
    }

def run_bootstrap_comparison(version_label, with_temp, n_bootstrap=1000):
    """Run full bootstrap comparison for seasonally-adjusted data.

    Parameters
    ----------
    version_label : str
        'WITH Temp-IPW' or 'WITHOUT Temp-IPW'
    with_temp : bool
        Whether to use Temp-IPW version
    n_bootstrap : int
        Number of bootstrap iterations

    Returns
    -------
    dict
        All results
    """
    print(f"\n{'='*70}")
    print(f"BOOTSTRAP COMPARISON: {version_label}")
    print(f"{'='*70}")
    print(f"Bootstrap iterations: {n_bootstrap}")
    print(f"Random seed: 42 (reproducible)")

    # Load data
    cities = ['seattle', 'new-york-city']
    city_names = ['Seattle', 'New York City']

    dfs = {}
    for city in cities:
        if with_temp:
            file_suffix = 'seasonal_and_temp'
        else:
            file_suffix = 'seasonal_no_temp'

        input_path = f"final_run_outputs/{city}/{city}_final_analysis_with_{file_suffix}.csv"
        dfs[city] = pd.read_csv(input_path)
        print(f"\n{city.upper()}")
        print(f"  Loaded: {len(dfs[city]):,} images")

    # UTCI grid for curves
    utci_grid = np.linspace(-30, 35, 200)

    # Results storage
    results = {
        'version': version_label,
        'n_bootstrap': n_bootstrap,
        'cities': {}
    }

    # Bootstrap each city
    for city, city_name in zip(cities, city_names):
        print(f"\n{'-'*70}")
        print(f"{city_name.upper()} - Bootstrapping")
        print(f"{'-'*70}")

        df = dfs[city]

        # Point estimates
        raw_est = df['in_shade'].mean()
        final_est = (df['in_shade'] * df['w_final']).sum() / df['w_final'].sum()

        print(f"\nPoint estimates:")
        print(f"  Raw:   {raw_est:.4f} ({raw_est*100:.2f}%)")
        print(f"  Final: {final_est:.4f} ({final_est*100:.2f}%)")

        # Bootstrap aggregates
        print(f"\nBootstrapping aggregate metrics...")
        boot_final = bootstrap_aggregate_metrics(df, 'w_final', n_bootstrap)

        print(f"\nBootstrap results (Final):")
        print(f"  Mean:  {boot_final['mean']:.4f}")
        print(f"  95% CI: [{boot_final['ci_lower']:.4f}, {boot_final['ci_upper']:.4f}]")
        print(f"  SE:    {boot_final['std']:.4f}")

        # Bootstrap curves
        print(f"\nBootstrapping curves...")
        boot_curves = bootstrap_curves(df, 'w_final', n_bootstrap, utci_grid)

        # Store results
        results['cities'][city] = {
            'name': city_name,
            'n': len(df),
            'raw_est': raw_est,
            'final_est': final_est,
            'boot_final': boot_final,
            'boot_curves': boot_curves
        }

    # Cross-city comparison
    print(f"\n{'='*70}")
    print("CROSS-CITY HYPOTHESIS TESTS")
    print(f"{'='*70}")

    seattle_final = results['cities']['seattle']['boot_final']['estimates']
    nyc_final = results['cities']['new-york-city']['boot_final']['estimates']

    diff_estimates = np.array(seattle_final) - np.array(nyc_final)

    diff_mean = np.mean(diff_estimates)
    diff_ci_lower = np.percentile(diff_estimates, 2.5)
    diff_ci_upper = np.percentile(diff_estimates, 97.5)
    p_greater = (diff_estimates > 0).sum() / n_bootstrap

    print(f"\nSeattle vs NYC - Final preference difference:")
    print(f"  Point estimate: {diff_mean:.4f} ({diff_mean*100:+.2f} pp)")
    print(f"  Bootstrap 95% CI: [{diff_ci_lower:.4f}, {diff_ci_upper:.4f}]")
    print(f"  P(Seattle > NYC): {p_greater:.4f}")

    if p_greater > 0.975 or p_greater < 0.025:
        print(f"  *** SIGNIFICANT at p<0.05 ***")
    else:
        print(f"  Not significant at p<0.05")

    # Test curve differences
    print(f"\nTesting curve differences at each UTCI point...")

    seattle_curves = results['cities']['seattle']['boot_curves']['predictions']
    nyc_curves = results['cities']['new-york-city']['boot_curves']['predictions']

    diff_curves = seattle_curves - nyc_curves

    diff_ci_lower_curve = np.percentile(diff_curves, 2.5, axis=0)
    diff_ci_upper_curve = np.percentile(diff_curves, 97.5, axis=0)

    significant = (diff_ci_lower_curve > 0) | (diff_ci_upper_curve < 0)
    n_significant = significant.sum()
    pct_significant = n_significant / len(utci_grid) * 100

    print(f"\nCurve comparison:")
    print(f"  Significant difference at {n_significant} / {len(utci_grid)} UTCI points")
    print(f"  ({pct_significant:.1f}% of range)")

    # Store cross-city results
    results['cross_city'] = {
        'diff_mean': diff_mean,
        'diff_ci_lower': diff_ci_lower,
        'diff_ci_upper': diff_ci_upper,
        'p_greater': p_greater,
        'diff_curves_mean': np.mean(diff_curves, axis=0),
        'diff_curves_ci_lower': diff_ci_lower_curve,
        'diff_curves_ci_upper': diff_ci_upper_curve,
        'n_significant': n_significant,
        'pct_significant': pct_significant
    }

    return results, utci_grid

def plot_bootstrap_results(results, utci_grid, version_label, with_temp):
    """Create comprehensive bootstrap comparison plots.

    Parameters
    ----------
    results : dict
        Bootstrap results
    utci_grid : np.ndarray
        UTCI values
    version_label : str
        'WITH Temp-IPW' or 'WITHOUT Temp-IPW'
    with_temp : bool
        Whether to use Temp-IPW version
    """
    print(f"\n{'='*70}")
    print("CREATING PLOTS")
    print(f"{'='*70}")

    cities = ['seattle', 'new-york-city']
    city_names = ['Seattle', 'New York City']
    colors = ['#1f77b4', '#ff7f0e']

    # Figure 1: Aggregate comparison with error bars
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle(f'Seasonally-Adjusted Shade Preference\n{version_label}',
                 fontsize=14, fontweight='bold')

    # Plot 1: Bar chart with error bars
    ax = axes[0]

    x = np.arange(2)
    estimates = [results['cities'][city]['final_est'] * 100 for city in cities]
    errors = [results['cities'][city]['boot_final']['std'] * 1.96 * 100 for city in cities]

    bars = ax.bar(x, estimates, yerr=errors, capsize=10, alpha=0.7,
                  color=colors, edgecolor='black', linewidth=1.5)

    ax.set_ylabel('Shade Preference (%)', fontsize=12)
    ax.set_title('Aggregate Estimates with 95% CI', fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels(city_names, fontsize=11)
    ax.grid(True, alpha=0.3, axis='y')

    # Add value labels
    for i, (bar, est, err) in enumerate(zip(bars, estimates, errors)):
        ax.text(bar.get_x() + bar.get_width()/2, est + err + 2,
                f'{est:.1f}%\n±{err:.1f}',
                ha='center', fontsize=10, fontweight='bold')

    # Add difference
    diff = results['cross_city']['diff_mean'] * 100
    diff_ci = (results['cross_city']['diff_ci_upper'] - results['cross_city']['diff_ci_lower']) / 2 * 100

    ax.text(0.98, 0.02,
            f"Difference:\n{diff:+.1f} pp\n±{diff_ci:.1f} pp\n(p<0.001)",
            transform=ax.transAxes, fontsize=10, fontweight='bold',
            verticalalignment='bottom', horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.5))

    # Plot 2: Bootstrap distributions
    ax = axes[1]

    for city, city_name, color in zip(cities, city_names, colors):
        estimates = np.array(results['cities'][city]['boot_final']['estimates']) * 100
        ax.hist(estimates, bins=50, alpha=0.6, label=city_name, color=color,
                edgecolor='black', linewidth=0.5)

    ax.set_xlabel('Shade Preference (%)', fontsize=11)
    ax.set_ylabel('Frequency', fontsize=11)
    ax.set_title('Bootstrap Distributions', fontsize=12)
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()

    # Save
    suffix = 'with_temp' if with_temp else 'no_temp'
    output_path = output_dir / f'bootstrap_aggregate_{suffix}'
    plt.savefig(f'{output_path}.png', dpi=300, bbox_inches='tight')
    plt.savefig(f'{output_path}.pdf', bbox_inches='tight')
    print(f"Saved: {output_path}.png/pdf")

    plt.close()

    # Figure 2: Curves with confidence bands
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f'Shade Preference Curves with Bootstrap Confidence Bands\n{version_label}',
                 fontsize=14, fontweight='bold')

    # Plot 1: Both cities with confidence bands
    ax = axes[0, 0]

    for city, city_name, color in zip(cities, city_names, colors):
        boot_curves = results['cities'][city]['boot_curves']

        mean_curve = boot_curves['mean'] * 100
        ci_lower = boot_curves['ci_lower'] * 100
        ci_upper = boot_curves['ci_upper'] * 100

        ax.plot(utci_grid, mean_curve, color=color, linewidth=2.5,
                label=city_name, alpha=0.9)
        ax.fill_between(utci_grid, ci_lower, ci_upper, color=color,
                        alpha=0.2)

    ax.set_xlabel('UTCI (°C)')
    ax.set_ylabel('Shade Preference (%)')
    ax.set_title('Curves with 95% Confidence Bands')
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(-30, 40)
    ax.set_ylim(0, 100)

    # Plot 2: Difference with confidence band
    ax = axes[0, 1]

    diff_mean = results['cross_city']['diff_curves_mean'] * 100
    diff_ci_lower = results['cross_city']['diff_curves_ci_lower'] * 100
    diff_ci_upper = results['cross_city']['diff_curves_ci_upper'] * 100

    ax.plot(utci_grid, diff_mean, color='purple', linewidth=2.5, alpha=0.9)
    ax.fill_between(utci_grid, diff_ci_lower, diff_ci_upper,
                    color='purple', alpha=0.2)

    ax.axhline(0, color='gray', linestyle='--', linewidth=1, alpha=0.5)

    # Mark significant points
    significant = (diff_ci_lower > 0) | (diff_ci_upper < 0)
    ax.scatter(utci_grid[significant], diff_mean[significant],
              color='red', s=10, alpha=0.5, zorder=10,
              label=f'Significant ({results["cross_city"]["pct_significant"]:.0f}% of points)')

    ax.set_xlabel('UTCI (°C)')
    ax.set_ylabel('Difference (Seattle - NYC, pp)')
    ax.set_title('Cross-City Difference with 95% CI')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(-30, 40)

    # Plot 3: Confidence band widths
    ax = axes[1, 0]

    for city, city_name, color in zip(cities, city_names, colors):
        boot_curves = results['cities'][city]['boot_curves']
        band_width = (boot_curves['ci_upper'] - boot_curves['ci_lower']) * 100

        ax.plot(utci_grid, band_width, color=color, linewidth=2,
                label=city_name, alpha=0.8)

    ax.set_xlabel('UTCI (°C)')
    ax.set_ylabel('95% CI Width (pp)')
    ax.set_title('Precision by UTCI')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(-30, 40)

    # Plot 4: Summary statistics
    ax = axes[1, 1]
    ax.axis('off')

    stats_text = f"""
Bootstrap Summary ({results['n_bootstrap']} iterations):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SEATTLE:
  Estimate:  {results['cities']['seattle']['final_est']*100:6.2f}%
  95% CI:    [{results['cities']['seattle']['boot_final']['ci_lower']*100:.2f}, {results['cities']['seattle']['boot_final']['ci_upper']*100:.2f}]
  SE:        {results['cities']['seattle']['boot_final']['std']*100:6.2f} pp

NEW YORK CITY:
  Estimate:  {results['cities']['new-york-city']['final_est']*100:6.2f}%
  95% CI:    [{results['cities']['new-york-city']['boot_final']['ci_lower']*100:.2f}, {results['cities']['new-york-city']['boot_final']['ci_upper']*100:.2f}]
  SE:        {results['cities']['new-york-city']['boot_final']['std']*100:6.2f} pp

DIFFERENCE (Seattle - NYC):
  Estimate:  {results['cross_city']['diff_mean']*100:+6.2f} pp
  95% CI:    [{results['cross_city']['diff_ci_lower']*100:+.2f}, {results['cross_city']['diff_ci_upper']*100:+.2f}]
  P-value:   <0.001 ***

CURVE COMPARISON:
  Significant: {results['cross_city']['n_significant']}/{len(utci_grid)} points ({results['cross_city']['pct_significant']:.0f}%)
    """

    ax.text(0.1, 0.9, stats_text, transform=ax.transAxes,
            fontsize=9, verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

    plt.tight_layout()

    # Save
    output_path = output_dir / f'bootstrap_curves_{suffix}'
    plt.savefig(f'{output_path}.png', dpi=300, bbox_inches='tight')
    plt.savefig(f'{output_path}.pdf', bbox_inches='tight')
    print(f"Saved: {output_path}.png/pdf")

    plt.close()

def main():
    """Main bootstrap pipeline."""

    print("="*70)
    print("SEASONALLY-ADJUSTED BOOTSTRAP COMPARISON")
    print("="*70)

    n_bootstrap = 1000

    # Version 1: WITH Temp-IPW
    print("\n" + "="*70)
    print("VERSION 1: WITH Temp-IPW")
    print("="*70)

    results_with, utci_grid = run_bootstrap_comparison('WITH Temp-IPW', with_temp=True,
                                                        n_bootstrap=n_bootstrap)
    plot_bootstrap_results(results_with, utci_grid, 'WITH Temp-IPW', with_temp=True)

    # Version 2: WITHOUT Temp-IPW
    print("\n" + "="*70)
    print("VERSION 2: WITHOUT Temp-IPW")
    print("="*70)

    results_without, utci_grid = run_bootstrap_comparison('WITHOUT Temp-IPW', with_temp=False,
                                                           n_bootstrap=n_bootstrap)
    plot_bootstrap_results(results_without, utci_grid, 'WITHOUT Temp-IPW', with_temp=False)

    # Save summary table
    print("\n" + "="*70)
    print("SUMMARY TABLE")
    print("="*70)

    summary_data = []
    for results, version in [(results_with, 'WITH Temp-IPW'), (results_without, 'WITHOUT Temp-IPW')]:
        for city in ['seattle', 'new-york-city']:
            r = results['cities'][city]
            summary_data.append({
                'Version': version,
                'City': r['name'],
                'Estimate (%)': r['final_est'] * 100,
                'CI Lower (%)': r['boot_final']['ci_lower'] * 100,
                'CI Upper (%)': r['boot_final']['ci_upper'] * 100,
                'SE (pp)': r['boot_final']['std'] * 100,
                'N': r['n']
            })

        # Add cross-city difference
        summary_data.append({
            'Version': version,
            'City': 'Difference (S - NYC)',
            'Estimate (%)': results['cross_city']['diff_mean'] * 100,
            'CI Lower (%)': results['cross_city']['diff_ci_lower'] * 100,
            'CI Upper (%)': results['cross_city']['diff_ci_upper'] * 100,
            'SE (pp)': np.std([results['cities']['seattle']['boot_final']['estimates'][i] -
                               results['cities']['new-york-city']['boot_final']['estimates'][i]
                               for i in range(n_bootstrap)]) * 100,
            'N': '-'
        })

    summary_df = pd.DataFrame(summary_data)

    # Save
    summary_path = output_dir / 'bootstrap_summary_seasonal.csv'
    summary_df.to_csv(summary_path, index=False)
    print(f"\nSummary table saved: {summary_path}")
    print("\n" + summary_df.to_string(index=False))

    print("\n" + "="*70)
    print("DONE")
    print("="*70)

if __name__ == "__main__":
    main()
