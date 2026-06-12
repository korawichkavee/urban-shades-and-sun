#!/usr/bin/env python3
"""
Compute ablation study table for bias correction methods.

This script reproduces the ablation analysis shown in the paper, matching
the methodology used in plot_shade_preference_adjustment_progression.py.

Output: LaTeX table showing marginal effect of each bias correction.

Author: Generated for reproducibility
Date: 2024
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy.interpolate import interp1d


def main():
    # Paths
    project_root = Path(__file__).parent.parent.parent
    data_path = project_root / 'data/final_datasets/seattle/seattle_final_analysis_with_seasonal_and_temp.csv'
    walk_rate_path = project_root / 'outputs/analysis/seattle_walking_by_utci.csv'

    # Load data
    print("Loading Seattle data...")
    df = pd.read_csv(data_path, low_memory=False)

    # Filter to images with people ONLY (no shadow ratio filter)
    # This matches the methodology in shade_preference_adjustment_progression.py
    df = df[df['person_count'] > 0].copy()

    print(f"Total images with people: {len(df):,}")
    print(f"UTCI range: {df['utci_C'].min():.1f} to {df['utci_C'].max():.1f}°C")
    print()

    # Load walk rate data for temperature adjustment
    walk_rate_df = pd.read_csv(walk_rate_path)
    walk_rate_interp = interp1d(
        walk_rate_df['utci_bin_center'],
        walk_rate_df['walk_rate'],
        kind='linear',
        bounds_error=False,
        fill_value=(walk_rate_df['walk_rate'].iloc[0], walk_rate_df['walk_rate'].iloc[-1])
    )

    baseline_utci = 20.0
    baseline_walk_rate = walk_rate_interp(baseline_utci)

    print(f"Baseline walk rate at {baseline_utci}°C: {baseline_walk_rate:.3f}")
    print()

    # ── Temperature Adjustment Function ────────────────────────────────────

    def get_temp_adjustment(utci):
        """
        Calculate temperature selection adjustment for a given UTCI value.

        Assumption: Non-walkers at extreme temperatures have different shade
        preferences than walkers. Adjustment is proportional to selection rate.
        """
        walk_rate_T = walk_rate_interp(utci)
        if walk_rate_T < baseline_walk_rate:
            if utci >= baseline_utci:
                # Hot weather: non-walkers avoiding heat prefer more shade
                return (baseline_walk_rate - walk_rate_T) * 1.0
            else:
                # Cold weather: non-walkers avoiding cold prefer more sun (less shade)
                return (walk_rate_T - baseline_walk_rate) * 1.0
        return 0.0

    # Calculate temperature adjustment for each row
    df['temp_adjustment'] = df['utci_C'].apply(get_temp_adjustment)

    # ── Ablation Study: Progressive Bias Corrections ──────────────────────

    print("=" * 70)
    print("ABLATION STUDY")
    print("=" * 70)
    print()

    results = []

    # Level 1: Raw (no corrections)
    raw_pref = df['in_shade'].mean()
    results.append({
        'level': 'None (raw)',
        'mean': raw_pref,
        'delta': None
    })
    print(f"1. None (raw):                  {raw_pref:.3f} ({raw_pref*100:.1f}%)")

    # Level 2: Temperature selection adjustment only
    temp_adjusted_pref = df['in_shade'].mean() + df['temp_adjustment'].mean()
    delta_temp = (temp_adjusted_pref - raw_pref) * 100
    results.append({
        'level': 'Temperature selection',
        'mean': temp_adjusted_pref,
        'delta': delta_temp
    })
    print(f"2. Temperature selection:        {temp_adjusted_pref:.3f} ({temp_adjusted_pref*100:.1f}%)  Δ = {delta_temp:+.1f} pp")

    # Level 3: Temperature + Shadow ratio (SR-IPW)
    sr_weighted_pref = (df['in_shade'] * df['w_sr_ipw']).sum() / df['w_sr_ipw'].sum()
    sr_temp_pref = sr_weighted_pref + df['temp_adjustment'].mean()
    delta_sr = (sr_temp_pref - temp_adjusted_pref) * 100
    results.append({
        'level': 'Shadow ratio (SR-IPW)',
        'mean': sr_temp_pref,
        'delta': delta_sr
    })
    print(f"3. Shadow ratio (SR-IPW):        {sr_temp_pref:.3f} ({sr_temp_pref*100:.1f}%)  Δ = {delta_sr:+.1f} pp")

    # Level 4: Temperature + SR-IPW + Detour cost (DCWP)
    sr_dcwp_weight = df['w_sr_ipw'] * df['w_dcwp']
    dcwp_weighted_pref = (df['in_shade'] * sr_dcwp_weight).sum() / sr_dcwp_weight.sum()
    dcwp_temp_pref = dcwp_weighted_pref + df['temp_adjustment'].mean()
    delta_dcwp = (dcwp_temp_pref - sr_temp_pref) * 100
    results.append({
        'level': 'Detour cost (DCWP)',
        'mean': dcwp_temp_pref,
        'delta': delta_dcwp
    })
    print(f"4. Detour cost (DCWP):           {dcwp_temp_pref:.3f} ({dcwp_temp_pref*100:.1f}%)  Δ = {delta_dcwp:+.1f} pp")

    # ── Summary Statistics ─────────────────────────────────────────────────

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    total_correction = (dcwp_temp_pref - raw_pref) * 100
    print(f"Total correction: {total_correction:+.1f} pp")
    print(f"  - Temperature:   {delta_temp:+.1f} pp ({abs(delta_temp)/abs(total_correction)*100:.1f}% of total)")
    print(f"  - SR-IPW:        {delta_sr:+.1f} pp ({abs(delta_sr)/abs(total_correction)*100:.1f}% of total)")
    print(f"  - DCWP:          {delta_dcwp:+.1f} pp ({abs(delta_dcwp)/abs(total_correction)*100:.1f}% of total)")
    print()

    # ── LaTeX Table Output ─────────────────────────────────────────────────

    print("=" * 70)
    print("LATEX TABLE")
    print("=" * 70)
    print()
    print("\\begin{table}[t!]")
    print("\\centering")
    print("\\caption{Ablation analysis of bias corrections on shade preference estimates.}")
    print("\\label{tab:ablation}")
    print("\\small")
    print("\\begin{tabular}{@{}lcc@{}}")
    print("\\toprule")
    print("\\textbf{Corrections Applied} & \\textbf{Mean $\\hat{p}_{\\text{shade}}$} & \\textbf{$\\Delta$ (pp)} \\\\")
    print("\\midrule")

    for i, row in enumerate(results):
        level = row['level']
        mean = row['mean']
        delta = row['delta']

        if delta is None:
            print(f"{level:30s} & {mean:.3f} & ---   \\\\")
        else:
            print(f"{level:30s} & {mean:.3f} & {delta:+.1f}  \\\\")

    print("\\bottomrule")
    print("\\end{tabular}")
    print()
    print("\\vspace{2pt}")
    print("\\parbox{0.9\\linewidth}{\\footnotesize")
    print(f"\\textit{{Note:}} $\\Delta$ values are reported in percentage points (pp) relative to the preceding row. ")
    print(f"Based on {len(df):,} images with pedestrians, UTCI range of ${df['utci_C'].min():.0f}$ to ${df['utci_C'].max():.0f}^{{\\circ}}\\text{{C}}$.")
    print("}")
    print("\\end{table}")
    print()

    # ── Save Results ───────────────────────────────────────────────────────

    output_path = project_root / 'outputs/analysis/ablation_study_results.csv'
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df_results = pd.DataFrame(results)
    df_results.to_csv(output_path, index=False)
    print(f"Results saved to: {output_path}")


if __name__ == '__main__':
    main()
