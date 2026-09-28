#!/usr/bin/env python3
"""
Sensitivity Analysis: Detour Decay Parameter (tau)

Addresses Reviewer 2, Comment 2:
"Incorporate a parametric sweep over a reasonable domain of τ (e.g., τ ∈ [5, 50])
to quantify the sensitivity of the outcome adjustment p_shade,i,j and the final
estimate f̂(T_j) to this assumed decay rate."

This script:
1. Loads Seattle data (READ-ONLY)
2. Recomputes DCWP adjustment with different tau values
3. Generates ablation tables for each tau
4. Saves results for supplementary figure and table

Author: Reviewer response
Date: 2026-09-28
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path

# Add sensitivity module to path
sys.path.append(str(Path(__file__).parent))
from sensitivity_utils import (
    load_seattle_data,
    load_walk_rate_data,
    compute_ablation_table,
    print_ablation_table,
    save_sensitivity_results,
    get_project_root
)


def compute_dcwp_with_tau(df, tau):
    """
    Compute distance-conditioned walk preference with variable tau.

    This matches apply_triple_ipw_final_cities_revised.py but allows
    varying the decay constant.

    Args:
        df: DataFrame with dist_to_shade_m, inshade_count, outshade_count
        tau: Detour decay constant in meters

    Returns:
        Series: DCWP-adjusted shade preference
    """
    # DCWP adjustment: downweight sun-standing by distance to shade
    effective_sun = df['outshade_count'] * np.exp(-df['dist_to_shade_m'] / tau)
    effective_shade = df['inshade_count']  # No adjustment

    # Shade preference ratio
    shade_pref_dcwp = effective_shade / (effective_shade + effective_sun + 1e-10)

    return shade_pref_dcwp


def compute_dcwp_weight_with_tau(df, tau):
    """
    Compute DCWP as a weight (alternative formulation).

    This computes w_dcwp = 1 / (1 + (outshade/inshade) * exp(-d/tau))

    Args:
        df: DataFrame with dist_to_shade_m, inshade_count, outshade_count
        tau: Detour decay constant in meters

    Returns:
        Series: DCWP weights
    """
    # From apply_seasonal_reweighting.py formulation
    # This is an alternative to the outcome adjustment
    ratio = df['outshade_count'] / (df['inshade_count'] + 1e-10)
    w_dcwp = 1.0 / (1.0 + ratio * np.exp(-df['dist_to_shade_m'] / tau))

    return w_dcwp


def run_tau_sensitivity():
    """
    Run tau sensitivity analysis.

    Tests tau ∈ {5, 10, 15, 20, 30, 40, 50} meters
    """
    print("=" * 70)
    print("SENSITIVITY ANALYSIS: DETOUR DECAY PARAMETER (TAU)")
    print("=" * 70)
    print()

    # Load data (READ-ONLY)
    df = load_seattle_data()
    walk_rate_df = load_walk_rate_data()

    # NO filtering by shadow_ratio - match paper methodology (person_count > 0 only)
    print(f"Total rows loaded: {len(df):,}")
    print()

    # Test different tau values
    tau_values = [5, 10, 15, 20, 30, 40, 50]
    all_results = []

    for tau in tau_values:
        print(f"Testing tau = {tau} meters")
        print("-" * 70)

        # Recompute w_dcwp with this tau (matches paper methodology)
        w_dcwp_tau = compute_dcwp_weight_with_tau(df, tau)

        # Statistics on DCWP weight
        print(f"  DCWP statistics (tau={tau}):")
        print(f"    Mean w_dcwp weight:     {w_dcwp_tau.mean():.3f}")
        print()

        # Create temp dataframe with new w_dcwp
        df_test = df.copy()
        df_test['w_dcwp'] = w_dcwp_tau

        # Compute ablation table (uses person_count > 0 filtering internally)
        ablation = compute_ablation_table(
            df_test,
            walk_rate_df=walk_rate_df
        )

        # Print results
        print_ablation_table(ablation, f"Ablation (tau = {tau}m)")

        # Add tau column for combined results
        ablation['tau'] = tau
        all_results.append(ablation)

    # Combine all results
    combined_results = pd.concat(all_results, ignore_index=True)

    # Save detailed results
    save_sensitivity_results(
        combined_results,
        'tau_sensitivity_detailed.csv',
        'Detailed tau sensitivity results saved.'
    )

    # Create summary table for supplementary materials
    summary = []
    for tau in tau_values:
        subset = combined_results[combined_results['tau'] == tau]

        # Get values at each level
        raw = subset[subset['level'] == 'None (raw)'].iloc[0]['mean']
        temp = subset[subset['level'] == 'Temperature selection'].iloc[0]['mean']
        sr = subset[subset['level'] == 'Shadow ratio (SR-IPW)'].iloc[0]['mean']
        dcwp = subset[subset['level'] == 'Detour cost (DCWP)'].iloc[0]['mean']

        # Deltas
        delta_sr = (sr - temp) * 100
        delta_dcwp = (dcwp - sr) * 100
        total_delta = (dcwp - raw) * 100

        summary.append({
            'tau': tau,
            'raw': raw,
            'temp': temp,
            'sr': sr,
            'dcwp': dcwp,
            'delta_sr_pp': delta_sr,
            'delta_dcwp_pp': delta_dcwp,
            'total_delta_pp': total_delta
        })

    summary_df = pd.DataFrame(summary)

    print("=" * 70)
    print("SUPPLEMENTARY TABLE S2: TAU SENSITIVITY")
    print("=" * 70)
    print(summary_df.to_string(index=False))
    print()

    save_sensitivity_results(
        summary_df,
        'supplementary_table_s2_tau.csv',
        'Supplementary Table S2 saved.'
    )

    # Generate LaTeX table
    generate_latex_table(summary_df)

    # Generate data for plotting
    generate_plot_data(combined_results, tau_values)

    print("=" * 70)
    print("TAU SENSITIVITY ANALYSIS COMPLETE")
    print("=" * 70)
    print()
    print("Key findings:")
    print(f"  - DCWP correction varies from {summary_df['delta_dcwp_pp'].min():.1f} to "
          f"{summary_df['delta_dcwp_pp'].max():.1f} pp across tau ∈ [5, 50]")
    print(f"  - Total correction varies from {summary_df['total_delta_pp'].min():.1f} to "
          f"{summary_df['total_delta_pp'].max():.1f} pp")
    print(f"  - SR-IPW dominates: accounts for ~{abs(summary_df['delta_sr_pp'].mean() / summary_df['total_delta_pp'].mean() * 100):.0f}% "
          f"of total correction on average")
    print()


def generate_latex_table(summary_df):
    """Generate LaTeX table for supplementary materials."""
    project_root = get_project_root()
    output_path = project_root / 'outputs/analysis/sensitivity/supplementary_table_s2_tau.tex'

    with open(output_path, 'w') as f:
        f.write("\\begin{table}[t!]\n")
        f.write("\\centering\n")
        f.write("\\caption{Sensitivity to detour decay parameter $\\tau$ in DCWP adjustment.}\n")
        f.write("\\label{tab:sensitivity-tau}\n")
        f.write("\\small\n")
        f.write("\\begin{tabular}{@{}lcccccc@{}}\n")
        f.write("\\toprule\n")
        f.write("$\\tau$ (m) & Raw & +Temp & +SR-IPW & +DCWP & $\\Delta_{\\text{SR}}$ (pp) & $\\Delta_{\\text{DCWP}}$ (pp) \\\\\n")
        f.write("\\midrule\n")

        for _, row in summary_df.iterrows():
            f.write(f"{row['tau']:2.0f} & {row['raw']:.3f} & {row['temp']:.3f} & "
                   f"{row['sr']:.3f} & {row['dcwp']:.3f} & "
                   f"{row['delta_sr_pp']:+.1f} & {row['delta_dcwp_pp']:+.1f} \\\\\n")

        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")
        f.write("\\vspace{2pt}\n")
        f.write("\\parbox{0.9\\linewidth}{\\footnotesize\n")
        f.write("\\textit{Note:} DCWP correction magnitude varies with $\\tau$, but the ")
        f.write("shadow ratio correction (SR-IPW) dominates in all cases. Total correction ")
        f.write(f"ranges from {summary_df['total_delta_pp'].min():.1f} to ")
        f.write(f"{summary_df['total_delta_pp'].max():.1f} percentage points across ")
        f.write("tested values of $\\tau \\in [5, 50]$ meters.\n")
        f.write("}\n")
        f.write("\\end{table}\n")

    print(f"LaTeX table saved to: {output_path}")
    print()


def generate_plot_data(combined_results, tau_values):
    """
    Generate data file for plotting (to be used by visualization script).

    Saves a wide-format CSV for easy plotting.
    """
    plot_data = []

    for tau in tau_values:
        subset = combined_results[combined_results['tau'] == tau]

        row = {'tau': tau}
        for _, ablation_row in subset.iterrows():
            level_short = ablation_row['level'].split('(')[0].strip()  # e.g., "None" from "None (raw)"
            row[level_short] = ablation_row['mean']

        plot_data.append(row)

    plot_df = pd.DataFrame(plot_data)

    save_sensitivity_results(
        plot_df,
        'tau_sensitivity_for_plotting.csv',
        'Plot data for tau sensitivity saved.'
    )


if __name__ == '__main__':
    run_tau_sensitivity()
