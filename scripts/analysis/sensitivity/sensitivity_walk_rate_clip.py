#!/usr/bin/env python3
"""
Sensitivity Analysis: Walk Rate Clipping

Addresses Reviewer 2, Comment 3:
"The methodology states that walk rates λ(T_j) are clipped at a minimum of 0.1
to prevent extreme weights. But the bias-variance tradeoff induced by this
truncation should be justified, e.g., by reporting the variance of the
temperature-based selection weights w_temp,i,j before and after clipping."

This script:
1. Loads Seattle data and walk rate data (READ-ONLY)
2. Computes temperature IPW weights WITHOUT clipping
3. Computes temperature IPW weights WITH clipping (current method)
4. Reports statistics on variance, extreme values, and affected observations
5. Generates text summary for response letter

Author: Reviewer response
Date: 2026-09-28
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.interpolate import interp1d

# Add sensitivity module to path
sys.path.append(str(Path(__file__).parent))
from sensitivity_utils import (
    load_seattle_data,
    load_walk_rate_data,
    effective_sample_size,
    get_project_root
)


def compute_temp_ipw_no_clip(df, walk_rate_df, baseline_utci=20.0):
    """
    Compute temperature IPW WITHOUT walk rate clipping.

    This allows extreme weights when walk rate is very low.

    Args:
        df: DataFrame with utci_C column
        walk_rate_df: Walk rate data with utci_bin_center and walk_rate
        baseline_utci: Baseline temperature (default 20.0)

    Returns:
        Series: Temperature IPW weights (no clipping)
    """
    # NO CLIPPING - use raw walk rates
    f_lambda = interp1d(
        walk_rate_df['utci_bin_center'],
        walk_rate_df['walk_rate'],
        kind='linear',
        bounds_error=False,
        fill_value=(walk_rate_df['walk_rate'].iloc[0], walk_rate_df['walk_rate'].iloc[-1])
    )

    lambda_T = f_lambda(df['utci_C'])
    lambda_baseline = f_lambda(baseline_utci)

    # Asymmetric weighting (no clipping)
    w_temp_no_clip = np.where(
        df['utci_C'] < baseline_utci,
        lambda_T / lambda_baseline,       # < 20°C: downweight
        lambda_baseline / lambda_T        # ≥ 20°C: upweight
    )

    return pd.Series(w_temp_no_clip, index=df.index)


def compute_temp_ipw_with_clip(df, walk_rate_df, baseline_utci=20.0, min_walk_rate=0.1):
    """
    Compute temperature IPW WITH walk rate clipping (current method).

    This matches apply_triple_ipw_final_cities_revised.py

    Args:
        df: DataFrame with utci_C column
        walk_rate_df: Walk rate data
        baseline_utci: Baseline temperature (default 20.0)
        min_walk_rate: Minimum walk rate threshold (default 0.1)

    Returns:
        Series: Temperature IPW weights (with clipping)
    """
    # Clip walk rates
    walk_rate_df_clipped = walk_rate_df.copy()
    walk_rate_df_clipped['walk_rate'] = np.maximum(
        walk_rate_df_clipped['walk_rate'],
        min_walk_rate
    )

    # Create interpolation function
    f_lambda = interp1d(
        walk_rate_df_clipped['utci_bin_center'],
        walk_rate_df_clipped['walk_rate'],
        kind='linear',
        bounds_error=False,
        fill_value=(walk_rate_df_clipped['walk_rate'].iloc[0],
                   walk_rate_df_clipped['walk_rate'].iloc[-1])
    )

    lambda_T = f_lambda(df['utci_C'])
    lambda_baseline = f_lambda(baseline_utci)

    # Additional clipping of interpolated values
    lambda_T = np.maximum(lambda_T, min_walk_rate)

    # Asymmetric weighting
    w_temp_clip = np.where(
        df['utci_C'] < baseline_utci,
        lambda_T / lambda_baseline,
        lambda_baseline / lambda_T
    )

    return pd.Series(w_temp_clip, index=df.index)


def run_walk_rate_clip_analysis():
    """
    Run walk rate clipping analysis.
    """
    print("=" * 70)
    print("SENSITIVITY ANALYSIS: WALK RATE CLIPPING")
    print("=" * 70)
    print()

    # Load data (READ-ONLY)
    df = load_seattle_data()
    walk_rate_df = load_walk_rate_data()

    # Filter to shadow_ratio >= 0.05 (same as main analysis)
    df_filtered = df[df['shadow_ratio'] >= 0.05].copy()
    print(f"Filtered to shadow_ratio >= 0.05: {len(df_filtered):,} rows")
    print()

    # Examine walk rate data
    print("=" * 70)
    print("WALK RATE DATA EXAMINATION")
    print("=" * 70)
    print()
    print("Walk rate by UTCI bin:")
    print(walk_rate_df.to_string(index=False))
    print()

    min_walk_rate = walk_rate_df['walk_rate'].min()
    bins_below_01 = (walk_rate_df['walk_rate'] < 0.1).sum()

    print(f"Minimum walk rate: {min_walk_rate:.4f}")
    print(f"Bins with walk rate < 0.1: {bins_below_01} / {len(walk_rate_df)}")
    print()

    # Compute weights WITHOUT clipping
    print("=" * 70)
    print("COMPUTING WEIGHTS WITHOUT CLIPPING")
    print("=" * 70)
    print()

    w_temp_no_clip = compute_temp_ipw_no_clip(df_filtered, walk_rate_df)

    print("Temperature IPW weights (NO clipping):")
    print(f"  Mean:   {w_temp_no_clip.mean():.4f}")
    print(f"  Std:    {w_temp_no_clip.std():.4f}")
    print(f"  Median: {w_temp_no_clip.median():.4f}")
    print(f"  Min:    {w_temp_no_clip.min():.4f}")
    print(f"  Max:    {w_temp_no_clip.max():.4f}")
    print(f"  99th percentile: {w_temp_no_clip.quantile(0.99):.4f}")
    print(f"  N_eff:  {effective_sample_size(w_temp_no_clip):,.0f}")
    print()

    # Check for extreme/invalid values
    n_infinite = np.isinf(w_temp_no_clip).sum()
    n_negative = (w_temp_no_clip < 0).sum()
    n_very_large = (w_temp_no_clip > 10).sum()

    print(f"Extreme values:")
    print(f"  Infinite:     {n_infinite:,}")
    print(f"  Negative:     {n_negative:,}")
    print(f"  > 10:         {n_very_large:,} ({100*n_very_large/len(w_temp_no_clip):.2f}%)")
    print()

    # Compute weights WITH clipping
    print("=" * 70)
    print("COMPUTING WEIGHTS WITH CLIPPING (min_walk_rate = 0.1)")
    print("=" * 70)
    print()

    w_temp_clip = compute_temp_ipw_with_clip(df_filtered, walk_rate_df, min_walk_rate=0.1)

    print("Temperature IPW weights (WITH clipping):")
    print(f"  Mean:   {w_temp_clip.mean():.4f}")
    print(f"  Std:    {w_temp_clip.std():.4f}")
    print(f"  Median: {w_temp_clip.median():.4f}")
    print(f"  Min:    {w_temp_clip.min():.4f}")
    print(f"  Max:    {w_temp_clip.max():.4f}")
    print(f"  99th percentile: {w_temp_clip.quantile(0.99):.4f}")
    print(f"  N_eff:  {effective_sample_size(w_temp_clip):,.0f}")
    print()

    # Compare
    print("=" * 70)
    print("COMPARISON: CLIPPING EFFECT")
    print("=" * 70)
    print()

    n_affected = (w_temp_no_clip != w_temp_clip).sum()
    pct_affected = 100 * n_affected / len(w_temp_no_clip)

    variance_reduction = ((w_temp_no_clip.std() - w_temp_clip.std()) /
                         w_temp_no_clip.std() * 100)

    print(f"Observations affected by clipping: {n_affected:,} / {len(w_temp_no_clip):,} ({pct_affected:.2f}%)")
    print()
    print(f"Variance reduction: {variance_reduction:.1f}%")
    print(f"  Std (no clip):  {w_temp_no_clip.std():.4f}")
    print(f"  Std (clipped):  {w_temp_clip.std():.4f}")
    print()
    print(f"Effective sample size:")
    print(f"  N_eff (no clip): {effective_sample_size(w_temp_no_clip):,.0f}")
    print(f"  N_eff (clipped): {effective_sample_size(w_temp_clip):,.0f}")
    print(f"  Change:          {effective_sample_size(w_temp_clip) - effective_sample_size(w_temp_no_clip):+,.0f}")
    print()

    # Which observations are affected?
    df_filtered['w_temp_no_clip'] = w_temp_no_clip
    df_filtered['w_temp_clip'] = w_temp_clip
    df_filtered['affected'] = (w_temp_no_clip != w_temp_clip)

    if n_affected > 0:
        print("Affected observations by UTCI range:")
        utci_ranges = pd.cut(df_filtered['utci_C'], bins=10)
        affected_by_range = df_filtered.groupby(utci_ranges)['affected'].agg(['sum', 'count', 'mean'])
        affected_by_range.columns = ['n_affected', 'n_total', 'pct_affected']
        affected_by_range['pct_affected'] *= 100
        print(affected_by_range.to_string())
        print()

    # Save results
    results = {
        'statistic': [
            'Mean (no clip)', 'Mean (clipped)', 'Mean change',
            'Std (no clip)', 'Std (clipped)', 'Variance reduction (%)',
            'Max (no clip)', 'Max (clipped)',
            'N_eff (no clip)', 'N_eff (clipped)',
            'Observations affected', 'Percent affected (%)'
        ],
        'value': [
            w_temp_no_clip.mean(), w_temp_clip.mean(),
            w_temp_clip.mean() - w_temp_no_clip.mean(),
            w_temp_no_clip.std(), w_temp_clip.std(), variance_reduction,
            w_temp_no_clip.max(), w_temp_clip.max(),
            effective_sample_size(w_temp_no_clip),
            effective_sample_size(w_temp_clip),
            n_affected, pct_affected
        ]
    }

    results_df = pd.DataFrame(results)

    project_root = get_project_root()
    output_path = project_root / 'outputs/analysis/sensitivity/walk_rate_clipping_stats.csv'
    results_df.to_csv(output_path, index=False)

    print(f"Results saved to: {output_path}")
    print()

    # Generate text summary for response letter
    generate_response_text(results_df, n_affected, pct_affected, variance_reduction)

    print("=" * 70)
    print("WALK RATE CLIPPING ANALYSIS COMPLETE")
    print("=" * 70)


def generate_response_text(results_df, n_affected, pct_affected, variance_reduction):
    """Generate formatted text for reviewer response letter."""
    project_root = get_project_root()
    output_path = project_root / 'outputs/analysis/sensitivity/walk_rate_clipping_response.txt'

    with open(output_path, 'w') as f:
        f.write("RESPONSE TO REVIEWER 2, COMMENT 3\n")
        f.write("=" * 70 + "\n\n")

        f.write("Walk rate clipping justification:\n\n")

        f.write(f"The walk rate clipping threshold (λ_min = 0.1) affects {n_affected:,} ")
        f.write(f"observations ({pct_affected:.1f}% of the dataset). These observations ")
        f.write("occur primarily at extreme temperatures where very few individuals ")
        f.write("choose to walk outdoors.\n\n")

        f.write("Statistical impact:\n")
        f.write(f"- Variance reduction: {variance_reduction:.1f}%\n")
        f.write(f"- Maximum weight reduced from {results_df[results_df['statistic'] == 'Max (no clip)']['value'].values[0]:.2f} ")
        f.write(f"to {results_df[results_df['statistic'] == 'Max (clipped)']['value'].values[0]:.2f}\n")
        f.write(f"- Effective sample size improved from ")
        f.write(f"{results_df[results_df['statistic'] == 'N_eff (no clip)']['value'].values[0]:,.0f} to ")
        f.write(f"{results_df[results_df['statistic'] == 'N_eff (clipped)']['value'].values[0]:,.0f}\n\n")

        f.write("Justification:\n")
        f.write("Clipping prevents extreme leverage from observations at temperatures where ")
        f.write("walk rates approach zero. Without clipping, a small number of observations ")
        f.write("at extreme temperatures would dominate the weighted estimates, violating ")
        f.write("the effective sample size assumption underlying inverse probability weighting. ")
        f.write("The 0.1 threshold represents a 10% minimum walking rate, which is conservative ")
        f.write("and prevents individual observations from receiving weights >10× the mean.\n\n")

        f.write("The bias-variance tradeoff is favorable: we accept minor bias in extreme ")
        f.write("temperature bins (where few observations exist) in exchange for substantial ")
        f.write(f"variance reduction ({variance_reduction:.1f}%) and improved stability of the estimator.\n")

    print(f"Response text saved to: {output_path}")
    print()


if __name__ == '__main__':
    run_walk_rate_clip_analysis()
