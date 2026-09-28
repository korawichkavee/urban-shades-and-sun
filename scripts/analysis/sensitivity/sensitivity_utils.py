#!/usr/bin/env python3
"""
Shared utilities for sensitivity analyses.

This module provides common functions for parameter sensitivity studies.
All functions are READ-ONLY and do not modify source data.

Author: Sensitivity analysis for reviewer response
Date: 2026-09-28
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy.interpolate import interp1d


# ── Data Loading ────────────────────────────────────────────────────────────

def get_project_root():
    """Get project root directory."""
    return Path(__file__).parent.parent.parent.parent


def load_seattle_data():
    """
    Load Seattle dataset (READ-ONLY).

    Returns:
        DataFrame: Seattle data with all columns intact
    """
    project_root = get_project_root()
    data_path = project_root / 'data/final_datasets/seattle/seattle_final_analysis_with_seasonal_and_temp.csv'

    print(f"Loading Seattle data from: {data_path}")
    df = pd.read_csv(data_path, low_memory=False)
    print(f"  Loaded {len(df):,} rows")

    return df


def load_walk_rate_data():
    """
    Load walk rate data (READ-ONLY).

    Returns:
        DataFrame: Walk rate by UTCI bin
    """
    project_root = get_project_root()
    walk_rate_path = project_root / 'outputs/analysis/seattle_walking_by_utci.csv'

    print(f"Loading walk rate data from: {walk_rate_path}")
    walk_rate_df = pd.read_csv(walk_rate_path)
    print(f"  Loaded {len(walk_rate_df)} UTCI bins")

    return walk_rate_df


# ── Effective Sample Size ──────────────────────────────────────────────────

def effective_sample_size(weights):
    """
    Compute effective sample size for weighted data.

    N_eff = (sum w)^2 / sum(w^2)

    Args:
        weights: Series or array of weights

    Returns:
        float: Effective sample size
    """
    valid_weights = weights[np.isfinite(weights) & (weights > 0)]
    if len(valid_weights) == 0:
        return 0
    return (valid_weights.sum() ** 2) / (valid_weights ** 2).sum()


# ── Temperature Adjustment ──────────────────────────────────────────────────

def get_temp_adjustment_function(walk_rate_df, baseline_utci=20.0):
    """
    Create temperature adjustment function matching the paper methodology.

    This matches the approach in plot_shade_preference_adjustment_progression.py

    Args:
        walk_rate_df: DataFrame with utci_bin_center and walk_rate columns
        baseline_utci: Baseline temperature in °C (default 20.0)

    Returns:
        function: Takes UTCI value, returns adjustment to shade preference
    """
    # Create interpolation function
    walk_rate_interp = interp1d(
        walk_rate_df['utci_bin_center'],
        walk_rate_df['walk_rate'],
        kind='linear',
        bounds_error=False,
        fill_value=(walk_rate_df['walk_rate'].iloc[0], walk_rate_df['walk_rate'].iloc[-1])
    )

    baseline_walk_rate = walk_rate_interp(baseline_utci)

    def temp_adjustment(utci):
        """
        Calculate temperature selection adjustment for a given UTCI value.

        Args:
            utci: UTCI temperature (scalar or array)

        Returns:
            Adjustment to add to shade preference (scalar or array)
        """
        walk_rate_T = walk_rate_interp(utci)

        # Only adjust when walk_rate < baseline (selection occurring)
        adjustment = np.zeros_like(utci, dtype=float)
        mask = walk_rate_T < baseline_walk_rate

        if np.any(mask):
            # Hot side (UTCI >= baseline): non-walkers prefer more shade
            hot_mask = mask & (utci >= baseline_utci)
            adjustment[hot_mask] = (baseline_walk_rate - walk_rate_T[hot_mask]) * 1.0

            # Cold side (UTCI < baseline): non-walkers prefer more sun (less shade)
            cold_mask = mask & (utci < baseline_utci)
            adjustment[cold_mask] = (walk_rate_T[cold_mask] - baseline_walk_rate) * 1.0

        return adjustment

    return temp_adjustment


# ── Ablation Table Computation ─────────────────────────────────────────────

def compute_ablation_table(df, walk_rate_df=None):
    """
    Compute ablation table with progressive corrections.

    MATCHES PAPER METHODOLOGY EXACTLY (compute_ablation_table.py):
    - Uses in_shade (camera boolean) as outcome variable
    - Filters to person_count > 0 only
    - Applies w_dcwp as a WEIGHT (not outcome adjustment)

    Args:
        df: DataFrame with in_shade, person_count, w_sr_ipw, w_dcwp columns
        walk_rate_df: Walk rate data (optional, for temp adjustment)

    Returns:
        DataFrame: Ablation results with columns [level, mean, delta]
    """
    # Filter to images with people ONLY (matches paper line 32)
    df_people = df[df['person_count'] > 0].copy()

    results = []

    # Level 1: Raw (no corrections) - uses in_shade like paper line 86
    raw_pref = df_people['in_shade'].mean()

    results.append({
        'level': 'None (raw)',
        'mean': raw_pref,
        'delta': None
    })

    # Temperature adjustment (if walk rate data provided)
    if walk_rate_df is not None:
        temp_adj_func = get_temp_adjustment_function(walk_rate_df)
        df_people['temp_adjustment'] = temp_adj_func(df_people['utci_C'].values)
        temp_adjusted_pref = raw_pref + df_people['temp_adjustment'].mean()
    else:
        temp_adjusted_pref = raw_pref
        df_people['temp_adjustment'] = 0.0

    delta_temp = (temp_adjusted_pref - raw_pref) * 100
    results.append({
        'level': 'Temperature selection',
        'mean': temp_adjusted_pref,
        'delta': delta_temp
    })

    # Level 3: Temperature + Shadow ratio (SR-IPW) - matches paper line 105
    sr_weighted_pref = (df_people['in_shade'] * df_people['w_sr_ipw']).sum() / df_people['w_sr_ipw'].sum()
    sr_temp_pref = sr_weighted_pref + df_people['temp_adjustment'].mean()

    delta_sr = (sr_temp_pref - temp_adjusted_pref) * 100
    results.append({
        'level': 'Shadow ratio (SR-IPW)',
        'mean': sr_temp_pref,
        'delta': delta_sr
    })

    # Level 4: Temperature + SR-IPW + Detour cost (DCWP) - matches paper lines 116-118
    # w_dcwp is applied as a WEIGHT, not an outcome adjustment
    sr_dcwp_weight = df_people['w_sr_ipw'] * df_people['w_dcwp']
    dcwp_weighted_pref = (df_people['in_shade'] * sr_dcwp_weight).sum() / sr_dcwp_weight.sum()
    dcwp_temp_pref = dcwp_weighted_pref + df_people['temp_adjustment'].mean()

    delta_dcwp = (dcwp_temp_pref - sr_temp_pref) * 100
    results.append({
        'level': 'Detour cost (DCWP)',
        'mean': dcwp_temp_pref,
        'delta': delta_dcwp
    })

    return pd.DataFrame(results)


# ── Output Helpers ──────────────────────────────────────────────────────────

def print_ablation_table(ablation_df, title="ABLATION RESULTS"):
    """
    Pretty-print ablation table.

    Args:
        ablation_df: DataFrame from compute_ablation_table
        title: Title to print
    """
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)

    for _, row in ablation_df.iterrows():
        level = row['level']
        mean = row['mean']
        delta = row['delta']

        if pd.isna(delta):
            print(f"{level:30s}  {mean:.3f} ({mean*100:.1f}%)")
        else:
            print(f"{level:30s}  {mean:.3f} ({mean*100:.1f}%)  Δ = {delta:+.1f} pp")

    print("=" * 70)
    print()


def save_sensitivity_results(results_df, filename, description=""):
    """
    Save sensitivity results to CSV with metadata.

    Args:
        results_df: DataFrame with sensitivity results
        filename: Output filename (relative to sensitivity output dir)
        description: Optional description to print
    """
    project_root = get_project_root()
    output_path = project_root / 'outputs/analysis/sensitivity' / filename

    results_df.to_csv(output_path, index=False)

    if description:
        print(description)
    print(f"Saved to: {output_path}")
    print(f"  {len(results_df)} rows written")
    print()
