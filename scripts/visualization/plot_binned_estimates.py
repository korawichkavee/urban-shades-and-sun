#!/usr/bin/env python3
"""
Plot binned shade preference estimates with error bars.

Shows:
1. Binned estimates (2°C bins) with 95% confidence intervals
2. Sample size by bin
3. Comparison across correction stages
4. Cross-city comparison

Purpose: Show actual data points underlying smooth curves and assess data quality.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 10

output_dir = Path("outputs/analysis/seasonally_adjusted_plots")
output_dir.mkdir(parents=True, exist_ok=True)

def compute_binned_estimates(df, weight_col, bin_width=2.0):
    """Compute binned shade preference estimates with confidence intervals.

    Parameters
    ----------
    df : pd.DataFrame
        Must have 'in_shade', 'utci_C', and weight column
    weight_col : str
        Name of weight column (or None for unweighted)
    bin_width : float
        Width of UTCI bins in °C (default 2.0)

    Returns
    -------
    pd.DataFrame
        Binned estimates with columns: bin_center, estimate, se, ci_lower, ci_upper, n
    """
    # Create bins
    bins = np.arange(-40, 45, bin_width)
    df['utci_bin'] = pd.cut(df['utci_C'], bins=bins)

    results = []

    for bin_interval in df['utci_bin'].cat.categories:
        df_bin = df[df['utci_bin'] == bin_interval]

        if len(df_bin) == 0:
            continue

        bin_center = (bin_interval.left + bin_interval.right) / 2

        # Compute weighted estimate
        if weight_col and weight_col in df_bin.columns:
            weights = df_bin[weight_col].values
            estimate = (df_bin['in_shade'] * weights).sum() / weights.sum()

            # Effective sample size
            n_eff = (weights.sum() ** 2) / (weights ** 2).sum()

            # Variance (weighted)
            # For binomial: var = p(1-p) / n_eff
            variance = estimate * (1 - estimate) / n_eff
        else:
            estimate = df_bin['in_shade'].mean()
            n_eff = len(df_bin)

            # Variance (unweighted)
            variance = estimate * (1 - estimate) / n_eff

        se = np.sqrt(variance)

        # 95% CI (normal approximation)
        ci_lower = estimate - 1.96 * se
        ci_upper = estimate + 1.96 * se

        results.append({
            'bin_center': bin_center,
            'bin_left': bin_interval.left,
            'bin_right': bin_interval.right,
            'estimate': estimate,
            'se': se,
            'ci_lower': ci_lower,
            'ci_upper': ci_upper,
            'n_raw': len(df_bin),
            'n_eff': n_eff
        })

    return pd.DataFrame(results)

def plot_binned_single_city(city, version_label, with_temp):
    """Plot binned estimates for a single city showing correction progression.

    Parameters
    ----------
    city : str
        'seattle' or 'new-york-city'
    version_label : str
        'WITH Temp-IPW' or 'WITHOUT Temp-IPW'
    with_temp : bool
        Whether to include Temp-IPW
    """
    # Load data
    if with_temp:
        file_suffix = 'seasonal_and_temp'
    else:
        file_suffix = 'seasonal_no_temp'

    input_path = f"final_run_outputs/{city}/{city}_final_analysis_with_{file_suffix}.csv"
    print(f"\nProcessing {city} ({version_label}): {input_path}")

    df = pd.read_csv(input_path)
    print(f"  Loaded {len(df):,} images")

    # Compute binned estimates for each stage
    print(f"  Computing binned estimates...")

    # Raw (unweighted)
    bins_raw = compute_binned_estimates(df, None)

    # SR-IPW only
    bins_sr = compute_binned_estimates(df, 'w_sr_ipw')

    # SR-IPW + DCWP
    df['w_sr_dcwp'] = df['w_sr_ipw'] * df['w_dcwp']
    bins_sr_dcwp = compute_binned_estimates(df, 'w_sr_dcwp')

    # Final (with seasonal)
    bins_final = compute_binned_estimates(df, 'w_final')

    # Create figure
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    city_name = 'Seattle' if city == 'seattle' else 'New York City'
    fig.suptitle(f'{city_name} - Binned Shade Preference Estimates\n{version_label}',
                 fontsize=14, fontweight='bold')

    # Plot 1: All correction stages with error bars
    ax = axes[0, 0]

    # Plot each stage
    offset = 0
    for bins_df, label, color, marker in [
        (bins_raw, 'Raw', 'gray', 'o'),
        (bins_sr, 'SR-IPW', 'blue', 's'),
        (bins_sr_dcwp, 'SR+DCWP', 'green', '^'),
        (bins_final, 'Final (Seasonal)', 'red', 'D')
    ]:
        x = bins_df['bin_center'] + offset
        y = bins_df['estimate'] * 100
        yerr = bins_df['se'] * 1.96 * 100  # 95% CI

        ax.errorbar(x, y, yerr=yerr, fmt=marker, markersize=5,
                   capsize=3, capthick=1, alpha=0.7, label=label, color=color)
        offset += 0.3

    ax.set_xlabel('UTCI (°C)')
    ax.set_ylabel('Shade Preference (%)')
    ax.set_title('Binned Estimates - All Correction Stages')
    ax.legend(loc='upper left', fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(-30, 40)
    ax.set_ylim(0, 100)

    # Plot 2: Final estimates with sample size overlay
    ax = axes[0, 1]

    x = bins_final['bin_center']
    y = bins_final['estimate'] * 100
    yerr = bins_final['se'] * 1.96 * 100

    ax.errorbar(x, y, yerr=yerr, fmt='D', markersize=6,
               capsize=4, capthick=1.5, alpha=0.8, label='Final estimate', color='red',
               elinewidth=1.5)

    ax.set_xlabel('UTCI (°C)')
    ax.set_ylabel('Shade Preference (%)', color='red')
    ax.set_title('Final Binned Estimates with Sample Size')
    ax.tick_params(axis='y', labelcolor='red')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(-30, 40)
    ax.set_ylim(0, 100)

    # Add sample size on secondary axis
    ax2 = ax.twinx()
    ax2.bar(bins_final['bin_center'], bins_final['n_raw'], width=1.8,
            alpha=0.3, color='blue', edgecolor='black', linewidth=0.5)
    ax2.set_ylabel('Sample Size (N)', color='blue')
    ax2.tick_params(axis='y', labelcolor='blue')

    # Add quality threshold lines
    ax2.axhline(500, color='orange', linestyle='--', linewidth=1, alpha=0.5, label='N=500')
    ax2.axhline(1000, color='green', linestyle='--', linewidth=1, alpha=0.5, label='N=1000')
    ax2.legend(loc='upper right', fontsize=8)

    # Plot 3: Standard errors by bin
    ax = axes[1, 0]

    ax.plot(bins_raw['bin_center'], bins_raw['se'] * 100, 'o-',
            label='Raw', color='gray', alpha=0.7)
    ax.plot(bins_final['bin_center'], bins_final['se'] * 100, 'D-',
            label='Final', color='red', alpha=0.8, linewidth=2)

    ax.set_xlabel('UTCI (°C)')
    ax.set_ylabel('Standard Error (pp)')
    ax.set_title('Precision by UTCI Bin')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(-30, 40)

    # Add threshold lines
    ax.axhline(2.2, color='orange', linestyle='--', linewidth=1, alpha=0.5,
               label='SE=2.2 pp (N≥500)')
    ax.axhline(1.6, color='green', linestyle='--', linewidth=1, alpha=0.5,
               label='SE=1.6 pp (N≥1000)')

    # Plot 4: Summary statistics table
    ax = axes[1, 1]
    ax.axis('off')

    # Compute summary stats
    n_bins = len(bins_final)
    n_bins_good = (bins_final['n_raw'] >= 500).sum()
    n_bins_excellent = (bins_final['n_raw'] >= 1000).sum()

    median_n = bins_final['n_raw'].median()
    median_se = bins_final['se'].median() * 100

    max_se_bin = bins_final.loc[bins_final['se'].idxmax()]
    min_n_bin = bins_final.loc[bins_final['n_raw'].idxmin()]

    # Create text
    stats_text = f"""
Data Quality Summary:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total UTCI bins:          {n_bins}
Bins with N ≥ 1000:       {n_bins_excellent} ({n_bins_excellent/n_bins*100:.0f}%)
Bins with N ≥ 500:        {n_bins_good} ({n_bins_good/n_bins*100:.0f}%)

Sample Size:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Median N per bin:         {median_n:.0f}
Min N per bin:            {min_n_bin['n_raw']:.0f}
  (at {min_n_bin['bin_center']:.0f}°C)

Precision:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Median SE:                {median_se:.2f} pp
Max SE:                   {max_se_bin['se']*100:.2f} pp
  (at {max_se_bin['bin_center']:.0f}°C)

Effective Sample:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total N (raw):            {df['in_shade'].count():,}
Total N (effective):      {bins_final['n_eff'].sum():.0f}
Effective %:              {bins_final['n_eff'].sum() / df['in_shade'].count() * 100:.1f}%
    """

    ax.text(0.1, 0.9, stats_text, transform=ax.transAxes,
            fontsize=9, verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

    plt.tight_layout()

    # Save
    suffix = 'with_temp' if with_temp else 'no_temp'
    output_path = output_dir / f'{city}_binned_estimates_{suffix}'
    plt.savefig(f'{output_path}.png', dpi=300, bbox_inches='tight')
    plt.savefig(f'{output_path}.pdf', bbox_inches='tight')
    print(f"  Saved: {output_path}.png/pdf")

    plt.close()

    # Save binned data to CSV
    csv_path = output_dir / f'{city}_binned_data_{suffix}.csv'
    bins_final.to_csv(csv_path, index=False)
    print(f"  Saved binned data: {csv_path}")

    return bins_final

def plot_cross_city_binned(version_label, with_temp):
    """Create cross-city binned comparison.

    Parameters
    ----------
    version_label : str
        'WITH Temp-IPW' or 'WITHOUT Temp-IPW'
    with_temp : bool
        Whether to include Temp-IPW
    """
    print(f"\n{'='*70}")
    print(f"Cross-City Binned Comparison: {version_label}")
    print(f"{'='*70}")

    cities = ['seattle', 'new-york-city']
    city_names = ['Seattle', 'New York City']
    colors = ['#1f77b4', '#ff7f0e']

    # Load data and compute bins
    bins_data = {}
    for city in cities:
        if with_temp:
            file_suffix = 'seasonal_and_temp'
        else:
            file_suffix = 'seasonal_no_temp'

        input_path = f"final_run_outputs/{city}/{city}_final_analysis_with_{file_suffix}.csv"
        df = pd.read_csv(input_path)

        bins_data[city] = compute_binned_estimates(df, 'w_final')
        print(f"  {city}: {len(bins_data[city])} bins")

    # Create figure
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f'Cross-City Binned Estimates Comparison\n{version_label}',
                 fontsize=14, fontweight='bold')

    # Plot 1: Both cities with error bars
    ax = axes[0, 0]

    for city, city_name, color in zip(cities, city_names, colors):
        bins_df = bins_data[city]
        x = bins_df['bin_center']
        y = bins_df['estimate'] * 100
        yerr = bins_df['se'] * 1.96 * 100

        ax.errorbar(x, y, yerr=yerr, fmt='o', markersize=6,
                   capsize=4, capthick=1.5, alpha=0.8, label=city_name,
                   color=color, elinewidth=2)

    ax.set_xlabel('UTCI (°C)')
    ax.set_ylabel('Shade Preference (%)')
    ax.set_title('Binned Estimates with 95% CI')
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(-30, 40)
    ax.set_ylim(0, 100)

    # Plot 2: Difference (Seattle - NYC)
    ax = axes[0, 1]

    # Merge bins on bin_center
    bins_seattle = bins_data['seattle'].set_index('bin_center')
    bins_nyc = bins_data['new-york-city'].set_index('bin_center')

    # Find common bins
    common_bins = bins_seattle.index.intersection(bins_nyc.index)

    diff_estimate = (bins_seattle.loc[common_bins, 'estimate'] -
                    bins_nyc.loc[common_bins, 'estimate']) * 100

    # Propagate errors (assuming independence)
    diff_se = np.sqrt(bins_seattle.loc[common_bins, 'se']**2 +
                     bins_nyc.loc[common_bins, 'se']**2) * 100

    ax.errorbar(common_bins, diff_estimate, yerr=diff_se*1.96,
               fmt='D', markersize=6, capsize=4, capthick=1.5,
               color='purple', alpha=0.8, elinewidth=2)

    ax.axhline(0, color='gray', linestyle='-', linewidth=1, alpha=0.5)

    ax.set_xlabel('UTCI (°C)')
    ax.set_ylabel('Difference (Seattle - NYC, pp)')
    ax.set_title('Cross-City Difference by Bin')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(-30, 40)

    # Add significance markers
    significant = np.abs(diff_estimate) > (1.96 * diff_se)
    ax.scatter(common_bins[significant], diff_estimate[significant],
              marker='*', s=200, color='red', alpha=0.5, zorder=10,
              label='Significant (p<0.05)')
    ax.legend(loc='best')

    # Plot 3: Sample size comparison
    ax = axes[1, 0]

    for city, city_name, color in zip(cities, city_names, colors):
        bins_df = bins_data[city]
        ax.plot(bins_df['bin_center'], bins_df['n_raw'], 'o-',
               markersize=6, label=city_name, color=color, alpha=0.8)

    ax.set_xlabel('UTCI (°C)')
    ax.set_ylabel('Sample Size (N)')
    ax.set_title('Sample Size by Bin')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(-30, 40)
    ax.set_yscale('log')

    # Add quality thresholds
    ax.axhline(500, color='orange', linestyle='--', linewidth=1, alpha=0.5)
    ax.axhline(1000, color='green', linestyle='--', linewidth=1, alpha=0.5)

    # Plot 4: Precision comparison
    ax = axes[1, 1]

    for city, city_name, color in zip(cities, city_names, colors):
        bins_df = bins_data[city]
        ax.plot(bins_df['bin_center'], bins_df['se'] * 100, 'o-',
               markersize=6, label=city_name, color=color, alpha=0.8)

    ax.set_xlabel('UTCI (°C)')
    ax.set_ylabel('Standard Error (pp)')
    ax.set_title('Precision by Bin')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(-30, 40)

    # Add quality thresholds
    ax.axhline(2.2, color='orange', linestyle='--', linewidth=1, alpha=0.5,
               label='SE=2.2 pp (N≥500)')
    ax.axhline(1.6, color='green', linestyle='--', linewidth=1, alpha=0.5,
               label='SE=1.6 pp (N≥1000)')

    plt.tight_layout()

    # Save
    suffix = 'with_temp' if with_temp else 'no_temp'
    output_path = output_dir / f'cross_city_binned_{suffix}'
    plt.savefig(f'{output_path}.png', dpi=300, bbox_inches='tight')
    plt.savefig(f'{output_path}.pdf', bbox_inches='tight')
    print(f"\nSaved: {output_path}.png/pdf")

    plt.close()

def main():
    """Main plotting pipeline."""

    print("="*70)
    print("BINNED SHADE PREFERENCE ESTIMATES")
    print("="*70)

    # Version 1: WITH Temp-IPW
    print("\n" + "="*70)
    print("VERSION 1: WITH Temp-IPW")
    print("="*70)

    for city in ['seattle', 'new-york-city']:
        plot_binned_single_city(city, 'WITH Temp-IPW', with_temp=True)

    plot_cross_city_binned('WITH Temp-IPW', with_temp=True)

    # Version 2: WITHOUT Temp-IPW
    print("\n" + "="*70)
    print("VERSION 2: WITHOUT Temp-IPW")
    print("="*70)

    for city in ['seattle', 'new-york-city']:
        plot_binned_single_city(city, 'WITHOUT Temp-IPW', with_temp=False)

    plot_cross_city_binned('WITHOUT Temp-IPW', with_temp=False)

    print("\n" + "="*70)
    print("DONE")
    print("="*70)
    print(f"\nAll plots saved to: {output_dir}/")

if __name__ == "__main__":
    main()
