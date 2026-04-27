#!/usr/bin/env python3
"""
Plot the effect of seasonal adjustment on estimates.

Compares:
- Before seasonal adjustment (revised IPW only)
- After seasonal adjustment (revised IPW + seasonal)

Shows how seasonal reweighting changes the estimates.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import statsmodels.api as sm
from pathlib import Path

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 10

output_dir = Path("outputs/analysis/seasonally_adjusted_plots")
output_dir.mkdir(parents=True, exist_ok=True)

def fit_curve(df, weight_col, utci_grid):
    """Fit quadratic binomial GLM."""
    y = df['in_shade'].values
    X = pd.DataFrame({
        'const': 1,
        'utci': df['utci_C'].values,
        'utci_sq': df['utci_C'].values ** 2
    })

    weights = df[weight_col].values
    model = sm.GLM(y, X, family=sm.families.Binomial(), freq_weights=weights).fit()

    X_grid = pd.DataFrame({
        'const': 1,
        'utci': utci_grid,
        'utci_sq': utci_grid ** 2
    })

    return model.predict(X_grid)

def main():
    print("="*70)
    print("SEASONAL ADJUSTMENT EFFECT")
    print("="*70)

    cities = ['seattle', 'new-york-city']
    city_names = ['Seattle', 'New York City']
    colors = ['#1f77b4', '#ff7f0e']

    utci_grid = np.linspace(-30, 40, 200)

    # Create figure
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Effect of Seasonal Standardization on Shade Preference Estimates',
                 fontsize=14, fontweight='bold')

    # Plot curves before/after for each city
    for idx, (city, city_name, color) in enumerate(zip(cities, city_names, colors)):

        print(f"\nProcessing {city_name}...")

        # Load BEFORE (revised IPW, no seasonal)
        df_before = pd.read_csv(f"final_run_outputs/{city}/{city}_final_analysis_with_ipw_revised.csv")
        print(f"  Before: {len(df_before):,} images")

        # Load AFTER (with seasonal, WITH Temp-IPW version)
        df_after = pd.read_csv(f"final_run_outputs/{city}/{city}_final_analysis_with_seasonal_and_temp.csv")
        print(f"  After:  {len(df_after):,} images")

        # Fit curves
        pred_before = fit_curve(df_before, 'w_combined', utci_grid)
        pred_after = fit_curve(df_after, 'w_final', utci_grid)

        # Compute aggregates
        agg_before = (df_before['in_shade'] * df_before['w_combined']).sum() / df_before['w_combined'].sum()
        agg_after = (df_after['in_shade'] * df_after['w_final']).sum() / df_after['w_final'].sum()

        print(f"  Before seasonal: {agg_before*100:.2f}%")
        print(f"  After seasonal:  {agg_after*100:.2f}%")
        print(f"  Effect:          {(agg_after - agg_before)*100:+.2f} pp")

        # Plot 1: Curves comparison
        ax = axes[0, idx]
        ax.plot(utci_grid, pred_before * 100, '--', color=color, linewidth=2,
                label='Before seasonal adj', alpha=0.7)
        ax.plot(utci_grid, pred_after * 100, '-', color=color, linewidth=2.5,
                label='After seasonal adj', alpha=0.9)

        ax.set_xlabel('UTCI (°C)')
        ax.set_ylabel('Shade Preference (%)')
        ax.set_title(f'{city_name}')
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)
        ax.set_xlim(-30, 40)
        ax.set_ylim(0, 100)

        # Add aggregate lines
        ax.axhline(agg_before * 100, color=color, linestyle=':', linewidth=1.5, alpha=0.5)
        ax.axhline(agg_after * 100, color=color, linestyle='-', linewidth=1.5, alpha=0.7)

        # Annotate
        ax.text(0.98, 0.02,
                f"Agg: {agg_before*100:.1f}% → {agg_after*100:.1f}%\n({(agg_after-agg_before)*100:+.1f} pp)",
                transform=ax.transAxes, fontsize=9,
                verticalalignment='bottom', horizontalalignment='right',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        # Plot 2: Effect by UTCI
        ax = axes[1, idx]
        effect = (pred_after - pred_before) * 100

        ax.plot(utci_grid, effect, color=color, linewidth=2.5, alpha=0.9)
        ax.axhline(0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        ax.axhline((agg_after - agg_before) * 100, color='red', linestyle=':',
                   linewidth=1.5, alpha=0.7, label='Avg effect')

        ax.set_xlabel('UTCI (°C)')
        ax.set_ylabel('Seasonal Adjustment Effect (pp)')
        ax.set_title(f'{city_name} - Effect Size')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)
        ax.set_xlim(-30, 40)

        # Annotate mean effect
        mean_effect = (agg_after - agg_before) * 100
        ax.text(0.02, 0.98,
                f"Mean effect: {mean_effect:+.2f} pp",
                transform=ax.transAxes, fontsize=10, fontweight='bold',
                verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.3))

    plt.tight_layout()

    # Save
    output_path = output_dir / 'seasonal_adjustment_effect'
    plt.savefig(f'{output_path}.png', dpi=300, bbox_inches='tight')
    plt.savefig(f'{output_path}.pdf', bbox_inches='tight')
    print(f"\nSaved: {output_path}.png/pdf")

    plt.close()

    # Cross-city gap comparison
    print("\n" + "="*70)
    print("CROSS-CITY GAP COMPARISON")
    print("="*70)

    # Load data
    results = {}
    for city in cities:
        df_before = pd.read_csv(f"final_run_outputs/{city}/{city}_final_analysis_with_ipw_revised.csv")
        df_after = pd.read_csv(f"final_run_outputs/{city}/{city}_final_analysis_with_seasonal_and_temp.csv")

        results[city] = {
            'before': (df_before['in_shade'] * df_before['w_combined']).sum() / df_before['w_combined'].sum(),
            'after': (df_after['in_shade'] * df_after['w_final']).sum() / df_after['w_final'].sum()
        }

    gap_before = results['seattle']['before'] - results['new-york-city']['before']
    gap_after = results['seattle']['after'] - results['new-york-city']['after']

    print(f"\nSeattle - NYC Gap:")
    print(f"  Before seasonal: {gap_before*100:+.2f} pp")
    print(f"  After seasonal:  {gap_after*100:+.2f} pp")
    print(f"  Change:          {(gap_after - gap_before)*100:+.2f} pp")

    # Simple bar chart
    fig, ax = plt.subplots(1, 1, figsize=(8, 6))

    x = np.array([0, 1])
    gaps = [gap_before * 100, gap_after * 100]

    bars = ax.bar(x, gaps, width=0.6, alpha=0.7,
                  color=['gray', 'red'], edgecolor='black', linewidth=1.5)

    ax.set_ylabel('Cross-City Gap (Seattle - NYC, pp)', fontsize=12)
    ax.set_title('Effect of Seasonal Standardization on Cross-City Gap',
                 fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(['Before Seasonal\nAdjustment', 'After Seasonal\nAdjustment'],
                       fontsize=11)
    ax.grid(True, alpha=0.3, axis='y')

    # Add value labels
    for i, (bar, gap) in enumerate(zip(bars, gaps)):
        ax.text(bar.get_x() + bar.get_width()/2, gap + 0.5,
                f'{gap:.1f} pp', ha='center', fontsize=11, fontweight='bold')

    # Add change arrow
    ax.annotate('', xy=(1, gap_after*100), xytext=(0, gap_before*100),
                arrowprops=dict(arrowstyle='->', lw=2, color='darkred'))
    ax.text(0.5, (gap_before + gap_after)/2 * 100,
            f'{(gap_after - gap_before)*100:+.1f} pp',
            ha='center', fontsize=10, fontweight='bold', color='darkred',
            bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.5))

    plt.tight_layout()

    output_path = output_dir / 'seasonal_gap_effect'
    plt.savefig(f'{output_path}.png', dpi=300, bbox_inches='tight')
    plt.savefig(f'{output_path}.pdf', bbox_inches='tight')
    print(f"\nSaved: {output_path}.png/pdf")

    print("\n" + "="*70)
    print("DONE")
    print("="*70)

if __name__ == "__main__":
    main()
