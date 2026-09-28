#!/usr/bin/env python3
"""
Visualization: Tau Ablation Sensitivity Analysis

Creates Supplementary Figure S1 showing how bias corrections vary with
the detour decay parameter tau in the ablation table format.

This figure shows that while DCWP magnitude varies with tau, the
shadow ratio correction (SR-IPW) dominates across all tested values.

Author: Reviewer response
Date: 2026-09-28
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Set up plotting style
sns.set_style("whitegrid")
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 11
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif', 'Times']


def create_tau_sensitivity_plot():
    """
    Create supplementary figure showing tau sensitivity.
    """
    print("=" * 70)
    print("CREATING SUPPLEMENTARY FIGURE S1: TAU SENSITIVITY")
    print("=" * 70)
    print()

    # Get project root
    project_root = Path(__file__).parent.parent.parent

    # Load tau sensitivity results
    data_path = project_root / 'outputs/analysis/sensitivity/tau_sensitivity_detailed.csv'

    if not data_path.exists():
        print(f"ERROR: Data file not found: {data_path}")
        print("Please run scripts/analysis/sensitivity/sensitivity_tau.py first.")
        return

    df = pd.read_csv(data_path)
    print(f"Loaded tau sensitivity data: {len(df)} rows")
    print()

    # Get unique tau values
    tau_values = sorted(df['tau'].unique())
    print(f"Tau values: {tau_values}")
    print()

    # Prepare data for plotting
    plot_data = []
    for tau in tau_values:
        subset = df[df['tau'] == tau]

        # Extract mean values for each correction level
        for _, row in subset.iterrows():
            plot_data.append({
                'tau': tau,
                'level': row['level'],
                'mean': row['mean'] * 100  # Convert to percentage
            })

    plot_df = pd.DataFrame(plot_data)

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))

    # Define colors and markers for each correction level
    colors = sns.color_palette("colorblind", 4)
    markers = ['o', 's', '^', 'D']
    linestyles = ['-', '--', '-.', ':']

    levels = [
        'None (raw)',
        'Temperature selection',
        'Shadow ratio (SR-IPW)',
        'Detour cost (DCWP)'
    ]

    # Plot each correction level
    for i, level in enumerate(levels):
        level_data = plot_df[plot_df['level'] == level].sort_values('tau')

        ax.plot(
            level_data['tau'],
            level_data['mean'],
            label=level,
            color=colors[i],
            marker=markers[i],
            markersize=8,
            linewidth=2,
            linestyle=linestyles[i],
            alpha=0.9
        )

    # Formatting
    ax.set_xlabel('Detour Decay Parameter $\\tau$ (meters)', fontsize=14)
    ax.set_ylabel('Shade Preference (%)', fontsize=14)
    ax.set_title('Sensitivity to Detour Decay Parameter', fontsize=16, pad=15)
    ax.legend(loc='upper right', fontsize=11, framealpha=0.95)

    # Set x-axis ticks at tested values
    ax.set_xticks(tau_values)

    # Grid
    ax.grid(True, which='major', alpha=0.3, linestyle='-', linewidth=0.8, color='gray')
    ax.set_axisbelow(True)

    # Y-axis limits
    y_min = plot_df['mean'].min() - 5
    y_max = plot_df['mean'].max() + 5
    ax.set_ylim(y_min, y_max)

    plt.tight_layout()

    # Save figure
    output_dir = project_root / 'outputs/plots/sensitivity'
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save as PDF (vector format for publication)
    output_path_pdf = output_dir / 'supplementary_figure_s1_tau_sensitivity.pdf'
    plt.savefig(output_path_pdf, bbox_inches='tight')
    print(f"PDF saved to: {output_path_pdf}")

    # Also save as PNG for quick viewing
    output_path_png = output_dir / 'supplementary_figure_s1_tau_sensitivity.png'
    plt.savefig(output_path_png, dpi=300, bbox_inches='tight')
    print(f"PNG saved to: {output_path_png}")

    # Create a second figure showing just the deltas
    create_delta_plot(df, tau_values, project_root)

    print()
    print("=" * 70)
    print("FIGURE CREATION COMPLETE")
    print("=" * 70)


def create_delta_plot(df, tau_values, project_root):
    """
    Create a second plot showing the magnitude of each correction as a function of tau.
    """
    print()
    print("Creating delta plot...")

    fig, ax = plt.subplots(figsize=(10, 6))

    # Calculate deltas for each tau
    delta_data = []
    for tau in tau_values:
        subset = df[df['tau'] == tau]

        raw = subset[subset['level'] == 'None (raw)']['mean'].values[0]
        temp = subset[subset['level'] == 'Temperature selection']['mean'].values[0]
        sr = subset[subset['level'] == 'Shadow ratio (SR-IPW)']['mean'].values[0]
        dcwp = subset[subset['level'] == 'Detour cost (DCWP)']['mean'].values[0]

        delta_data.append({
            'tau': tau,
            'Temp adjustment': (temp - raw) * 100,
            'SR-IPW correction': (sr - temp) * 100,
            'DCWP correction': (dcwp - sr) * 100
        })

    delta_df = pd.DataFrame(delta_data)

    # Plot
    colors = sns.color_palette("colorblind")[1:4]
    markers = ['s', '^', 'D']
    corrections = ['Temp adjustment', 'SR-IPW correction', 'DCWP correction']

    for i, corr in enumerate(corrections):
        ax.plot(
            delta_df['tau'],
            delta_df[corr],
            label=corr,
            color=colors[i],
            marker=markers[i],
            markersize=8,
            linewidth=2,
            alpha=0.9
        )

    # Add horizontal line at y=0
    ax.axhline(0, color='gray', linestyle='--', linewidth=1, alpha=0.5)

    # Formatting
    ax.set_xlabel('Detour Decay Parameter $\\tau$ (meters)', fontsize=14)
    ax.set_ylabel('Correction Magnitude (percentage points)', fontsize=14)
    ax.set_title('Magnitude of Each Bias Correction vs. $\\tau$', fontsize=16, pad=15)
    ax.legend(loc='best', fontsize=11, framealpha=0.95)

    ax.set_xticks(tau_values)
    ax.grid(True, which='major', alpha=0.3, linestyle='-', linewidth=0.8, color='gray')
    ax.set_axisbelow(True)

    plt.tight_layout()

    # Save
    output_path_pdf = project_root / 'outputs/plots/sensitivity/supplementary_figure_s1b_tau_deltas.pdf'
    plt.savefig(output_path_pdf, bbox_inches='tight')
    print(f"Delta plot (PDF) saved to: {output_path_pdf}")

    output_path_png = project_root / 'outputs/plots/sensitivity/supplementary_figure_s1b_tau_deltas.png'
    plt.savefig(output_path_png, dpi=300, bbox_inches='tight')
    print(f"Delta plot (PNG) saved to: {output_path_png}")


if __name__ == '__main__':
    create_tau_sensitivity_plot()
