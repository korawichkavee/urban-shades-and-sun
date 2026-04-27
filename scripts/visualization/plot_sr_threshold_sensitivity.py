#!/usr/bin/env python3
"""
Shadow Ratio Threshold Sensitivity Analysis

Tests how shade preference estimates change with different SR filter thresholds.

Current threshold: SR ≥ 0.05 (excludes ~65-70% of data)
Test thresholds: 0.01, 0.03, 0.05, 0.10, 0.15

Priority 8 from ADDITIONAL_IPW_ANALYSES_PROPOSAL.md
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import statsmodels.api as sm
from pathlib import Path

# Paths
DATA_DIR = Path("final_run_outputs")
OUTPUT_DIR = Path("outputs/analysis/ipw_plots")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Plotting settings
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.size'] = 10
plt.rcParams['figure.dpi'] = 150


def compute_metrics_at_threshold(df, sr_threshold):
    """Compute all metrics for a given SR threshold."""

    # Apply filter
    df_filtered = df[df['shadow_ratio'] >= sr_threshold].copy()

    if len(df_filtered) == 0:
        return None

    # Compute metrics
    metrics = {
        'sr_threshold': sr_threshold,
        'n_images': len(df_filtered),
        'retention_pct': len(df_filtered) / len(df) * 100,
    }

    # Raw shade preference
    metrics['shade_pref_raw'] = df_filtered['in_shade'].mean()

    # DCWP shade preference (aggregate)
    effective_sun = df_filtered['outshade_count'] * np.exp(-df_filtered['dist_to_shade_m'] / 20.0)
    effective_shade = df_filtered['inshade_count']
    metrics['shade_pref_dcwp'] = effective_shade.sum() / (effective_shade.sum() + effective_sun.sum())

    # IPW-weighted shade preference
    weights = df_filtered['w_combined']
    metrics['shade_pref_ipw'] = (df_filtered['in_shade'] * weights).sum() / weights.sum()

    # Effective N
    metrics['n_eff'] = weights.sum()**2 / (weights**2).sum()
    metrics['n_eff_pct'] = metrics['n_eff'] / len(df_filtered) * 100

    # Effect sizes
    metrics['dcwp_effect_pp'] = (metrics['shade_pref_dcwp'] - metrics['shade_pref_raw']) * 100
    metrics['ipw_effect_pp'] = (metrics['shade_pref_ipw'] - metrics['shade_pref_dcwp']) * 100
    metrics['combined_effect_pp'] = (metrics['shade_pref_ipw'] - metrics['shade_pref_raw']) * 100

    # Shadow ratio distribution
    metrics['mean_sr'] = df_filtered['shadow_ratio'].mean()
    metrics['median_sr'] = df_filtered['shadow_ratio'].median()

    return metrics


def plot_threshold_sensitivity(city):
    """Create threshold sensitivity plots for one city."""

    print(f"\n{'='*70}")
    print(f"{city.upper()} - SR THRESHOLD SENSITIVITY")
    print('='*70)

    # Load data
    df = pd.read_csv(DATA_DIR / city / f"{city}_final_analysis_with_ipw_revised.csv")

    print(f"Total images: {len(df):,}")

    # Test multiple thresholds
    thresholds = [0.01, 0.03, 0.05, 0.10, 0.15, 0.20]
    results = []

    for sr_thresh in thresholds:
        metrics = compute_metrics_at_threshold(df, sr_thresh)
        if metrics:
            results.append(metrics)
            print(f"\nSR ≥ {sr_thresh:.2f}:")
            print(f"  Retention: {metrics['retention_pct']:.1f}% ({metrics['n_images']:,} images)")
            print(f"  Raw:  {metrics['shade_pref_raw']:.3f} ({metrics['shade_pref_raw']*100:.1f}%)")
            print(f"  DCWP: {metrics['shade_pref_dcwp']:.3f} (effect: {metrics['dcwp_effect_pp']:+.2f} pp)")
            print(f"  IPW:  {metrics['shade_pref_ipw']:.3f} (effect: {metrics['combined_effect_pp']:+.2f} pp)")
            print(f"  N_eff: {metrics['n_eff']:.0f} ({metrics['n_eff_pct']:.1f}%)")

    results_df = pd.DataFrame(results)

    # Create plots
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    fig.suptitle(f'{city.replace("-", " ").title()} - Shadow Ratio Threshold Sensitivity',
                 fontsize=14, fontweight='bold')

    # Plot 1: Data retention
    ax = axes[0, 0]
    ax.plot(results_df['sr_threshold'], results_df['retention_pct'], 'o-', linewidth=2, markersize=8)
    ax.axvline(0.05, color='red', linestyle='--', alpha=0.5, label='Current (0.05)')
    ax.set_xlabel('Shadow Ratio Threshold')
    ax.set_ylabel('Data Retention (%)')
    ax.set_title('Data Retention vs Threshold')
    ax.grid(True, alpha=0.3)
    ax.legend()

    # Plot 2: Shade preference estimates
    ax = axes[0, 1]
    ax.plot(results_df['sr_threshold'], results_df['shade_pref_raw']*100, 'o-', label='Raw', linewidth=2)
    ax.plot(results_df['sr_threshold'], results_df['shade_pref_dcwp']*100, 's-', label='DCWP', linewidth=2)
    ax.plot(results_df['sr_threshold'], results_df['shade_pref_ipw']*100, '^-', label='IPW', linewidth=2)
    ax.axvline(0.05, color='red', linestyle='--', alpha=0.5)
    ax.set_xlabel('Shadow Ratio Threshold')
    ax.set_ylabel('Shade Preference (%)')
    ax.set_title('Shade Preference Estimates')
    ax.grid(True, alpha=0.3)
    ax.legend()

    # Plot 3: Effect sizes
    ax = axes[0, 2]
    ax.plot(results_df['sr_threshold'], results_df['dcwp_effect_pp'], 's-', label='DCWP effect', linewidth=2)
    ax.plot(results_df['sr_threshold'], results_df['ipw_effect_pp'], '^-', label='IPW effect', linewidth=2)
    ax.plot(results_df['sr_threshold'], results_df['combined_effect_pp'], 'D-', label='Combined', linewidth=2)
    ax.axvline(0.05, color='red', linestyle='--', alpha=0.5)
    ax.axhline(0, color='black', linestyle='-', linewidth=0.5, alpha=0.5)
    ax.set_xlabel('Shadow Ratio Threshold')
    ax.set_ylabel('Effect Size (pp)')
    ax.set_title('Correction Effect Sizes')
    ax.grid(True, alpha=0.3)
    ax.legend()

    # Plot 4: Effective N
    ax = axes[1, 0]
    ax.plot(results_df['sr_threshold'], results_df['n_eff_pct'], 'o-', linewidth=2, markersize=8, color='purple')
    ax.axvline(0.05, color='red', linestyle='--', alpha=0.5, label='Current (0.05)')
    ax.set_xlabel('Shadow Ratio Threshold')
    ax.set_ylabel('Effective N (% of retained)')
    ax.set_title('Effective Sample Size')
    ax.grid(True, alpha=0.3)
    ax.legend()

    # Plot 5: Mean shadow ratio of retained data
    ax = axes[1, 1]
    ax.plot(results_df['sr_threshold'], results_df['mean_sr'], 'o-', linewidth=2, markersize=8, color='green')
    ax.axvline(0.05, color='red', linestyle='--', alpha=0.5, label='Current (0.05)')
    ax.set_xlabel('Shadow Ratio Threshold')
    ax.set_ylabel('Mean Shadow Ratio')
    ax.set_title('Mean SR of Retained Data')
    ax.grid(True, alpha=0.3)
    ax.legend()

    # Plot 6: Absolute images retained
    ax = axes[1, 2]
    ax.plot(results_df['sr_threshold'], results_df['n_images']/1000, 'o-', linewidth=2, markersize=8, color='orange')
    ax.axvline(0.05, color='red', linestyle='--', alpha=0.5, label='Current (0.05)')
    ax.set_xlabel('Shadow Ratio Threshold')
    ax.set_ylabel('Images Retained (thousands)')
    ax.set_title('Absolute Sample Size')
    ax.grid(True, alpha=0.3)
    ax.legend()

    plt.tight_layout()

    # Save
    for ext in ['png', 'pdf']:
        outfile = OUTPUT_DIR / f"sr_threshold_sensitivity_{city}.{ext}"
        plt.savefig(outfile, dpi=300 if ext == 'png' else None, bbox_inches='tight')
        print(f"\nSaved: {outfile}")

    plt.close()

    # Save table
    table_file = OUTPUT_DIR / f"sr_threshold_sensitivity_{city}_table.csv"
    results_df.to_csv(table_file, index=False)
    print(f"Saved: {table_file}")

    return results_df


def plot_cross_city_threshold_comparison():
    """Compare threshold sensitivity across cities."""

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    fig.suptitle('Shadow Ratio Threshold Sensitivity - Cross-City Comparison',
                 fontsize=14, fontweight='bold')

    thresholds = [0.01, 0.03, 0.05, 0.10, 0.15, 0.20]
    city_colors = {'seattle': '#2ca02c', 'new-york-city': '#ff7f0e'}
    city_labels = {'seattle': 'Seattle', 'new-york-city': 'New York City'}

    all_results = {}

    for city in ['seattle', 'new-york-city']:
        df = pd.read_csv(DATA_DIR / city / f"{city}_final_analysis_with_ipw_revised.csv")
        results = []
        for sr_thresh in thresholds:
            metrics = compute_metrics_at_threshold(df, sr_thresh)
            if metrics:
                results.append(metrics)
        all_results[city] = pd.DataFrame(results)

    # Plot 1: Shade preference (IPW)
    ax = axes[0, 0]
    for city in ['seattle', 'new-york-city']:
        df_res = all_results[city]
        ax.plot(df_res['sr_threshold'], df_res['shade_pref_ipw']*100, 'o-',
                label=city_labels[city], color=city_colors[city], linewidth=2, markersize=8)
    ax.axvline(0.05, color='red', linestyle='--', alpha=0.5, label='Current (0.05)')
    ax.set_xlabel('Shadow Ratio Threshold')
    ax.set_ylabel('Shade Preference (%, IPW-adjusted)')
    ax.set_title('IPW-Adjusted Shade Preference')
    ax.grid(True, alpha=0.3)
    ax.legend()

    # Plot 2: Combined effect size
    ax = axes[0, 1]
    for city in ['seattle', 'new-york-city']:
        df_res = all_results[city]
        ax.plot(df_res['sr_threshold'], df_res['combined_effect_pp'], 'o-',
                label=city_labels[city], color=city_colors[city], linewidth=2, markersize=8)
    ax.axvline(0.05, color='red', linestyle='--', alpha=0.5, label='Current (0.05)')
    ax.axhline(0, color='black', linestyle='-', linewidth=0.5, alpha=0.5)
    ax.set_xlabel('Shadow Ratio Threshold')
    ax.set_ylabel('Combined Effect Size (pp)')
    ax.set_title('Total Correction Effect')
    ax.grid(True, alpha=0.3)
    ax.legend()

    # Plot 3: Data retention
    ax = axes[1, 0]
    for city in ['seattle', 'new-york-city']:
        df_res = all_results[city]
        ax.plot(df_res['sr_threshold'], df_res['retention_pct'], 'o-',
                label=city_labels[city], color=city_colors[city], linewidth=2, markersize=8)
    ax.axvline(0.05, color='red', linestyle='--', alpha=0.5, label='Current (0.05)')
    ax.set_xlabel('Shadow Ratio Threshold')
    ax.set_ylabel('Data Retention (%)')
    ax.set_title('Data Retention')
    ax.grid(True, alpha=0.3)
    ax.legend()

    # Plot 4: Effective N %
    ax = axes[1, 1]
    for city in ['seattle', 'new-york-city']:
        df_res = all_results[city]
        ax.plot(df_res['sr_threshold'], df_res['n_eff_pct'], 'o-',
                label=city_labels[city], color=city_colors[city], linewidth=2, markersize=8)
    ax.axvline(0.05, color='red', linestyle='--', alpha=0.5, label='Current (0.05)')
    ax.set_xlabel('Shadow Ratio Threshold')
    ax.set_ylabel('Effective N (% of retained)')
    ax.set_title('Weighting Efficiency')
    ax.grid(True, alpha=0.3)
    ax.legend()

    plt.tight_layout()

    # Save
    for ext in ['png', 'pdf']:
        outfile = OUTPUT_DIR / f"sr_threshold_sensitivity_cross_city.{ext}"
        plt.savefig(outfile, dpi=300 if ext == 'png' else None, bbox_inches='tight')
        print(f"\nSaved: {outfile}")

    plt.close()


if __name__ == "__main__":
    print("="*70)
    print("SR THRESHOLD SENSITIVITY ANALYSIS")
    print("="*70)

    # Individual cities
    for city in ['seattle', 'new-york-city']:
        plot_threshold_sensitivity(city)

    # Cross-city comparison
    print(f"\n{'='*70}")
    print("CROSS-CITY COMPARISON")
    print('='*70)
    plot_cross_city_threshold_comparison()

    print(f"\n{'='*70}")
    print("Done.")
    print('='*70)
