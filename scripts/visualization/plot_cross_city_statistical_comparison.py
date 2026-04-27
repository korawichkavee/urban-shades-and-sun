#!/usr/bin/env python3
"""
Cross-City Statistical Comparison

Performs rigorous statistical comparison between Seattle and NYC:
1. Bootstrap confidence intervals for all estimates
2. Hypothesis tests for differences between cities
3. Quantify uncertainty in effect sizes
4. Test if curves differ significantly

Priority 6 from ADDITIONAL_IPW_ANALYSES_PROPOSAL.md
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import statsmodels.api as sm
from pathlib import Path
from scipy import stats
from tqdm import tqdm

# Paths
DATA_DIR = Path("final_run_outputs")
OUTPUT_DIR = Path("outputs/analysis/ipw_plots")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Plotting settings
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.size'] = 10
plt.rcParams['figure.dpi'] = 150

# Bootstrap settings
N_BOOTSTRAP = 1000
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)


def compute_aggregate_metrics(df, weight_col=None):
    """Compute overall shade preference metrics."""
    if weight_col:
        weights = df[weight_col].values
        shade_pref = (df['in_shade'] * weights).sum() / weights.sum()
    else:
        shade_pref = df['in_shade'].mean()

    return shade_pref


def compute_dcwp_aggregate(df, tau=20.0):
    """Compute DCWP-adjusted shade preference (aggregate)."""
    effective_sun = df['outshade_count'] * np.exp(-df['dist_to_shade_m'] / tau)
    effective_shade = df['inshade_count']
    shade_pref_dcwp = effective_shade.sum() / (effective_shade.sum() + effective_sun.sum())
    return shade_pref_dcwp


def bootstrap_aggregate_metrics(df, weight_col=None, n_bootstrap=1000):
    """Bootstrap confidence intervals for aggregate shade preference."""
    estimates = []

    for i in tqdm(range(n_bootstrap), desc="Bootstrap aggregate"):
        # Resample with replacement
        df_boot = df.sample(n=len(df), replace=True, random_state=i)

        # Compute metric
        est = compute_aggregate_metrics(df_boot, weight_col)
        estimates.append(est)

    estimates = np.array(estimates)

    # Compute CI
    ci_lower = np.percentile(estimates, 2.5)
    ci_upper = np.percentile(estimates, 97.5)

    return {
        'mean': np.mean(estimates),
        'std': np.std(estimates),
        'ci_lower': ci_lower,
        'ci_upper': ci_upper,
        'estimates': estimates
    }


def fit_curve_and_predict(df, weight_col=None, utci_grid=None):
    """Fit quadratic binomial GLM and return predictions."""
    if utci_grid is None:
        utci_grid = np.linspace(-30, 35, 200)

    # Prepare data
    y = df['in_shade'].values
    X = pd.DataFrame({
        'const': 1,
        'utci': df['utci_C'].values,
        'utci_sq': df['utci_C'].values ** 2
    })

    # Handle weights
    if weight_col is not None:
        weights = df[weight_col].values
        valid_mask = np.isfinite(weights) & (weights > 0)
        if not valid_mask.all():
            weights = weights[valid_mask]
            y = y[valid_mask]
            X = X.iloc[valid_mask]
    else:
        weights = None

    # Fit GLM
    model = sm.GLM(y, X, family=sm.families.Binomial(), freq_weights=weights).fit()

    # Predict on grid
    X_grid = pd.DataFrame({
        'const': 1,
        'utci': utci_grid,
        'utci_sq': utci_grid ** 2
    })
    pred = model.predict(X_grid)

    return pred


def bootstrap_curves(df, weight_col=None, n_bootstrap=1000, utci_grid=None):
    """Bootstrap confidence bands for prediction curve."""
    if utci_grid is None:
        utci_grid = np.linspace(-30, 35, 200)

    predictions = np.zeros((n_bootstrap, len(utci_grid)))

    for i in tqdm(range(n_bootstrap), desc="Bootstrap curves"):
        # Resample
        df_boot = df.sample(n=len(df), replace=True, random_state=i)

        # Fit and predict
        try:
            pred = fit_curve_and_predict(df_boot, weight_col, utci_grid)
            predictions[i, :] = pred
        except:
            # If fit fails, use NaN
            predictions[i, :] = np.nan

    # Remove failed fits
    valid_mask = ~np.isnan(predictions).any(axis=1)
    predictions = predictions[valid_mask]

    # Compute percentiles
    ci_lower = np.percentile(predictions, 2.5, axis=0)
    ci_upper = np.percentile(predictions, 97.5, axis=0)
    mean_pred = np.mean(predictions, axis=0)

    return {
        'utci': utci_grid,
        'mean': mean_pred,
        'ci_lower': ci_lower,
        'ci_upper': ci_upper,
        'predictions': predictions
    }


def test_curve_difference(city1_preds, city2_preds):
    """Test if two prediction curves differ significantly at each UTCI point."""
    # For each bootstrap iteration, compute difference
    n_boot = min(len(city1_preds), len(city2_preds))
    differences = city1_preds[:n_boot] - city2_preds[:n_boot]

    # Test if difference CI excludes zero
    ci_lower = np.percentile(differences, 2.5, axis=0)
    ci_upper = np.percentile(differences, 97.5, axis=0)

    # Significant if CI doesn't include 0
    significant = (ci_lower > 0) | (ci_upper < 0)

    return {
        'difference_mean': np.mean(differences, axis=0),
        'difference_ci_lower': ci_lower,
        'difference_ci_upper': ci_upper,
        'significant': significant
    }


def plot_bootstrap_aggregate_comparison():
    """Compare aggregate metrics with bootstrap CIs."""

    print("\n" + "="*70)
    print("AGGREGATE METRICS COMPARISON")
    print("="*70)

    results = {}

    for city in ['seattle', 'new-york-city']:
        print(f"\n{city.upper()}")
        df = pd.read_csv(DATA_DIR / city / f"{city}_final_analysis_with_ipw_revised.csv")
        df = df[df['shadow_ratio'] >= 0.05].copy()

        print(f"Sample size: {len(df):,}")

        # Point estimates
        raw = compute_aggregate_metrics(df, weight_col=None)
        dcwp = compute_dcwp_aggregate(df, tau=20.0)
        ipw = compute_aggregate_metrics(df, weight_col='w_combined')

        print(f"\nPoint estimates:")
        print(f"  Raw:  {raw:.3f} ({raw*100:.1f}%)")
        print(f"  DCWP: {dcwp:.3f} ({dcwp*100:.1f}%)")
        print(f"  IPW:  {ipw:.3f} ({ipw*100:.1f}%)")

        # Bootstrap CIs
        print(f"\nBootstrapping (n={N_BOOTSTRAP})...")
        raw_boot = bootstrap_aggregate_metrics(df, weight_col=None, n_bootstrap=N_BOOTSTRAP)
        ipw_boot = bootstrap_aggregate_metrics(df, weight_col='w_combined', n_bootstrap=N_BOOTSTRAP)

        print(f"\nBootstrap results:")
        print(f"  Raw:  {raw_boot['mean']:.3f} [{raw_boot['ci_lower']:.3f}, {raw_boot['ci_upper']:.3f}]")
        print(f"  IPW:  {ipw_boot['mean']:.3f} [{ipw_boot['ci_lower']:.3f}, {ipw_boot['ci_upper']:.3f}]")

        results[city] = {
            'raw': raw,
            'dcwp': dcwp,
            'ipw': ipw,
            'raw_boot': raw_boot,
            'ipw_boot': ipw_boot
        }

    # Statistical tests
    print("\n" + "="*70)
    print("STATISTICAL TESTS")
    print("="*70)

    # Test difference in raw preference
    seattle_raw = results['seattle']['raw_boot']['estimates']
    nyc_raw = results['new-york-city']['raw_boot']['estimates']
    diff_raw = seattle_raw - nyc_raw

    print(f"\nSeattle vs NYC - Raw preference difference:")
    print(f"  Point estimate: {results['seattle']['raw'] - results['new-york-city']['raw']:.3f}")
    print(f"  Bootstrap mean: {np.mean(diff_raw):.3f}")
    print(f"  Bootstrap 95% CI: [{np.percentile(diff_raw, 2.5):.3f}, {np.percentile(diff_raw, 97.5):.3f}]")
    print(f"  P(diff > 0): {(diff_raw > 0).mean():.3f}")
    if (diff_raw > 0).mean() > 0.975 or (diff_raw > 0).mean() < 0.025:
        print(f"  *** SIGNIFICANT at p<0.05 ***")
    else:
        print(f"  Not significant at p<0.05")

    # Test difference in IPW preference
    seattle_ipw = results['seattle']['ipw_boot']['estimates']
    nyc_ipw = results['new-york-city']['ipw_boot']['estimates']
    diff_ipw = seattle_ipw - nyc_ipw

    print(f"\nSeattle vs NYC - IPW-adjusted preference difference:")
    print(f"  Point estimate: {results['seattle']['ipw'] - results['new-york-city']['ipw']:.3f}")
    print(f"  Bootstrap mean: {np.mean(diff_ipw):.3f}")
    print(f"  Bootstrap 95% CI: [{np.percentile(diff_ipw, 2.5):.3f}, {np.percentile(diff_ipw, 97.5):.3f}]")
    print(f"  P(diff > 0): {(diff_ipw > 0).mean():.3f}")
    if (diff_ipw > 0).mean() > 0.975 or (diff_ipw > 0).mean() < 0.025:
        print(f"  *** SIGNIFICANT at p<0.05 ***")
    else:
        print(f"  Not significant at p<0.05")

    # Create plot
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle('Cross-City Comparison - Aggregate Shade Preference', fontsize=14, fontweight='bold')

    # Plot 1: Point estimates with error bars
    ax = axes[0]
    x_pos = np.arange(2)
    width = 0.25

    # Raw
    raw_means = [results['seattle']['raw'], results['new-york-city']['raw']]
    raw_errs = [
        [results['seattle']['raw'] - results['seattle']['raw_boot']['ci_lower'],
         results['new-york-city']['raw'] - results['new-york-city']['raw_boot']['ci_lower']],
        [results['seattle']['raw_boot']['ci_upper'] - results['seattle']['raw'],
         results['new-york-city']['raw_boot']['ci_upper'] - results['new-york-city']['raw']]
    ]
    ax.bar(x_pos - width, [r*100 for r in raw_means], width, yerr=[[r*100 for r in raw_errs[0]], [r*100 for r in raw_errs[1]]],
           label='Raw', capsize=5, color='#1f77b4', alpha=0.8)

    # DCWP
    dcwp_means = [results['seattle']['dcwp'], results['new-york-city']['dcwp']]
    ax.bar(x_pos, [d*100 for d in dcwp_means], width, label='DCWP', color='#ff7f0e', alpha=0.8)

    # IPW
    ipw_means = [results['seattle']['ipw'], results['new-york-city']['ipw']]
    ipw_errs = [
        [results['seattle']['ipw'] - results['seattle']['ipw_boot']['ci_lower'],
         results['new-york-city']['ipw'] - results['new-york-city']['ipw_boot']['ci_lower']],
        [results['seattle']['ipw_boot']['ci_upper'] - results['seattle']['ipw'],
         results['new-york-city']['ipw_boot']['ci_upper'] - results['new-york-city']['ipw']]
    ]
    ax.bar(x_pos + width, [i*100 for i in ipw_means], width, yerr=[[i*100 for i in ipw_errs[0]], [i*100 for i in ipw_errs[1]]],
           label='IPW', capsize=5, color='#2ca02c', alpha=0.8)

    ax.set_ylabel('Shade Preference (%)')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(['Seattle', 'New York City'])
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_title('Point Estimates with 95% CIs')

    # Plot 2: Bootstrap distributions of difference
    ax = axes[1]
    ax.hist(diff_raw*100, bins=30, alpha=0.5, label='Raw (S - NYC)', color='#1f77b4', edgecolor='black')
    ax.hist(diff_ipw*100, bins=30, alpha=0.5, label='IPW (S - NYC)', color='#2ca02c', edgecolor='black')
    ax.axvline(0, color='red', linestyle='--', linewidth=2, label='No difference')
    ax.set_xlabel('Difference in Shade Preference (pp)')
    ax.set_ylabel('Frequency')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_title('Bootstrap Distribution of Differences')

    plt.tight_layout()

    # Save
    for ext in ['png', 'pdf']:
        outfile = OUTPUT_DIR / f"cross_city_aggregate_comparison.{ext}"
        plt.savefig(outfile, dpi=300 if ext == 'png' else None, bbox_inches='tight')
        print(f"\nSaved: {outfile}")

    plt.close()

    return results


def plot_bootstrap_curve_comparison():
    """Compare prediction curves with bootstrap confidence bands."""

    print("\n" + "="*70)
    print("CURVE COMPARISON WITH BOOTSTRAP CONFIDENCE BANDS")
    print("="*70)

    utci_grid = np.linspace(-30, 35, 200)

    curve_results = {}

    for city in ['seattle', 'new-york-city']:
        print(f"\n{city.upper()}")
        df = pd.read_csv(DATA_DIR / city / f"{city}_final_analysis_with_ipw_revised.csv")
        df = df[df['shadow_ratio'] >= 0.05].copy()

        # Bootstrap curves for Raw and IPW
        print("Bootstrapping Raw curve...")
        raw_curves = bootstrap_curves(df, weight_col=None, n_bootstrap=N_BOOTSTRAP, utci_grid=utci_grid)

        print("Bootstrapping IPW curve...")
        ipw_curves = bootstrap_curves(df, weight_col='w_combined', n_bootstrap=N_BOOTSTRAP, utci_grid=utci_grid)

        curve_results[city] = {
            'raw': raw_curves,
            'ipw': ipw_curves
        }

    # Test differences
    print("\n" + "="*70)
    print("TESTING CURVE DIFFERENCES")
    print("="*70)

    raw_diff = test_curve_difference(
        curve_results['seattle']['raw']['predictions'],
        curve_results['new-york-city']['raw']['predictions']
    )

    ipw_diff = test_curve_difference(
        curve_results['seattle']['ipw']['predictions'],
        curve_results['new-york-city']['ipw']['predictions']
    )

    print(f"\nRaw curves:")
    print(f"  Significant difference at {raw_diff['significant'].sum()} / {len(utci_grid)} UTCI points")
    print(f"  ({raw_diff['significant'].sum()/len(utci_grid)*100:.1f}% of range)")

    print(f"\nIPW curves:")
    print(f"  Significant difference at {ipw_diff['significant'].sum()} / {len(utci_grid)} UTCI points")
    print(f"  ({ipw_diff['significant'].sum()/len(utci_grid)*100:.1f}% of range)")

    # Create plots
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Cross-City Curve Comparison with Bootstrap 95% CIs', fontsize=14, fontweight='bold')

    colors = {'seattle': '#2ca02c', 'new-york-city': '#ff7f0e'}
    labels = {'seattle': 'Seattle', 'new-york-city': 'New York City'}

    # Plot 1: Raw curves
    ax = axes[0, 0]
    for city in ['seattle', 'new-york-city']:
        res = curve_results[city]['raw']
        ax.plot(res['utci'], res['mean']*100, '-', color=colors[city], linewidth=2, label=labels[city])
        ax.fill_between(res['utci'], res['ci_lower']*100, res['ci_upper']*100,
                        color=colors[city], alpha=0.2)
    ax.set_xlabel('UTCI (°C)')
    ax.set_ylabel('Shade Preference (%)')
    ax.set_title('Raw (Unadjusted)')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 2: IPW curves
    ax = axes[0, 1]
    for city in ['seattle', 'new-york-city']:
        res = curve_results[city]['ipw']
        ax.plot(res['utci'], res['mean']*100, '-', color=colors[city], linewidth=2, label=labels[city])
        ax.fill_between(res['utci'], res['ci_lower']*100, res['ci_upper']*100,
                        color=colors[city], alpha=0.2)
    ax.set_xlabel('UTCI (°C)')
    ax.set_ylabel('Shade Preference (%)')
    ax.set_title('IPW-Adjusted')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 3: Difference in raw curves
    ax = axes[1, 0]
    ax.plot(utci_grid, raw_diff['difference_mean']*100, 'k-', linewidth=2, label='Seattle - NYC')
    ax.fill_between(utci_grid, raw_diff['difference_ci_lower']*100, raw_diff['difference_ci_upper']*100,
                    color='gray', alpha=0.3, label='95% CI')
    # Highlight significant regions
    sig_mask = raw_diff['significant']
    if sig_mask.any():
        ax.scatter(utci_grid[sig_mask], raw_diff['difference_mean'][sig_mask]*100,
                  c='red', s=10, zorder=5, alpha=0.5, label='Significant')
    ax.axhline(0, color='black', linestyle='--', linewidth=1, alpha=0.5)
    ax.set_xlabel('UTCI (°C)')
    ax.set_ylabel('Difference in Shade Preference (pp)')
    ax.set_title('Difference: Raw Curves (S - NYC)')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 4: Difference in IPW curves
    ax = axes[1, 1]
    ax.plot(utci_grid, ipw_diff['difference_mean']*100, 'k-', linewidth=2, label='Seattle - NYC')
    ax.fill_between(utci_grid, ipw_diff['difference_ci_lower']*100, ipw_diff['difference_ci_upper']*100,
                    color='gray', alpha=0.3, label='95% CI')
    # Highlight significant regions
    sig_mask = ipw_diff['significant']
    if sig_mask.any():
        ax.scatter(utci_grid[sig_mask], ipw_diff['difference_mean'][sig_mask]*100,
                  c='red', s=10, zorder=5, alpha=0.5, label='Significant')
    ax.axhline(0, color='black', linestyle='--', linewidth=1, alpha=0.5)
    ax.set_xlabel('UTCI (°C)')
    ax.set_ylabel('Difference in Shade Preference (pp)')
    ax.set_title('Difference: IPW Curves (S - NYC)')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    # Save
    for ext in ['png', 'pdf']:
        outfile = OUTPUT_DIR / f"cross_city_curve_comparison.{ext}"
        plt.savefig(outfile, dpi=300 if ext == 'png' else None, bbox_inches='tight')
        print(f"\nSaved: {outfile}")

    plt.close()

    return curve_results, raw_diff, ipw_diff


def create_summary_table(aggregate_results, curve_results):
    """Create publication-ready summary table."""

    print("\n" + "="*70)
    print("SUMMARY TABLE")
    print("="*70)

    rows = []

    for city in ['seattle', 'new-york-city']:
        city_label = 'Seattle' if city == 'seattle' else 'New York City'

        # Raw
        raw = aggregate_results[city]['raw']
        raw_ci = aggregate_results[city]['raw_boot']
        rows.append({
            'City': city_label,
            'Estimate': 'Raw',
            'Shade Pref (%)': f"{raw*100:.1f}",
            '95% CI': f"[{raw_ci['ci_lower']*100:.1f}, {raw_ci['ci_upper']*100:.1f}]",
            'SE': f"{raw_ci['std']*100:.2f}"
        })

        # DCWP
        dcwp = aggregate_results[city]['dcwp']
        rows.append({
            'City': city_label,
            'Estimate': 'DCWP',
            'Shade Pref (%)': f"{dcwp*100:.1f}",
            '95% CI': '-',
            'SE': '-'
        })

        # IPW
        ipw = aggregate_results[city]['ipw']
        ipw_ci = aggregate_results[city]['ipw_boot']
        rows.append({
            'City': city_label,
            'Estimate': 'IPW',
            'Shade Pref (%)': f"{ipw*100:.1f}",
            '95% CI': f"[{ipw_ci['ci_lower']*100:.1f}, {ipw_ci['ci_upper']*100:.1f}]",
            'SE': f"{ipw_ci['std']*100:.2f}"
        })

    summary_df = pd.DataFrame(rows)

    print("\n" + summary_df.to_string(index=False))

    # Save
    outfile = OUTPUT_DIR / "cross_city_summary_table.csv"
    summary_df.to_csv(outfile, index=False)
    print(f"\nSaved: {outfile}")

    return summary_df


if __name__ == "__main__":
    print("="*70)
    print("CROSS-CITY STATISTICAL COMPARISON")
    print(f"Bootstrap iterations: {N_BOOTSTRAP}")
    print(f"Random seed: {RANDOM_SEED}")
    print("="*70)

    # Aggregate comparison
    aggregate_results = plot_bootstrap_aggregate_comparison()

    # Curve comparison
    curve_results, raw_diff, ipw_diff = plot_bootstrap_curve_comparison()

    # Summary table
    summary_table = create_summary_table(aggregate_results, curve_results)

    print("\n" + "="*70)
    print("Done.")
    print("="*70)
