#!/usr/bin/env python3
# ABOUTME: Plot UTCI vs shade preference at three adjustment levels
# ABOUTME: Raw, DCWP-adjusted, and DCWP+IPW-adjusted preferences

"""
CRITICAL ANALYSIS OF THIS APPROACH:

WHAT'S REASONABLE:
1. Weighting by total_people for raw estimates - each person made a choice
2. Using UTCI bins to capture non-linear temperature-preference relationships
3. Showing uncertainty with standard error bands
4. Comparing two cities to identify generalizable patterns

WHAT'S QUESTIONABLE/PROBLEMATIC:
1. AGGREGATION LEVEL MISMATCH:
   - We observe IMAGE-level data (counts of people in/out of shade)
   - But we're treating each image as independent
   - People in the same image share the same conditions → correlated choices
   - Should use cluster-robust SEs or hierarchical models

2. BINNING ARTIFACTS:
   - Equal-width UTCI bins ignore data density
   - Bins with few images → unreliable estimates
   - Arbitrary choice of 20 bins (why not 15 or 30?)
   - Edge bins especially problematic

3. WEIGHTING INTERPRETATION:
   - IPW weights (w_combined) are meant to adjust for SAMPLING bias
   - Assumes images are randomly sampled from population
   - But Mapillary coverage is highly non-random (popular areas oversampled)
   - Unclear if IPW weights correctly address this

4. CONFOUNDING:
   - UTCI correlates with time of day, season, location
   - People's shade seeking may vary by activity type (commuting vs leisure)
   - We don't control for trip purpose or demographics
   - "Shade preference" may really be "trip type" effect

5. DCWP VS IPW:
   - shade_pref_dcwp = "double-centered weighted preference"
   - But what does "double-centered" mean here?
   - Need to understand the DCWP transformation
   - Is it removing fixed effects? Detrending?

6. MISSING MOBILITY ADJUSTMENT:
   - User asked for "mobility + IPW" but we don't have separate mobility weights
   - The w_combined already includes everything
   - Can't separate out mobility effect

WHAT COULD BE WRONG:
1. shade_pref_raw might not equal inshade_count/total_people
   - Could have additional filtering or adjustments
   - Should verify they match

2. Images without people are excluded
   - This creates SELECTION BIAS if people avoid certain conditions
   - E.g., if everyone stays inside when UTCI > 40°C, we underestimate discomfort

3. Seasonal confounding:
   - Summer images → high UTCI, more people outside
   - Winter images → low UTCI, fewer people outside
   - "Preference" confounded with "availability"

RECOMMENDATION:
Plot what we have, but interpret cautiously:
- Level 1: Raw (shade_pref_raw, weighted by total_people)
- Level 2: DCWP (shade_pref_dcwp, weighted by total_people)
- Level 3: DCWP + IPW (shade_pref_dcwp, weighted by w_combined)
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

project_root = Path(__file__).parent.parent.parent

def load_city_data(city_key):
    """Load and prepare city data."""
    input_file = project_root / 'final_run_outputs' / city_key / f'{city_key}_final_analysis_with_ipw.csv'

    print(f"Loading {city_key}...")
    df = pd.read_csv(input_file, low_memory=False)

    # Only keep images with people
    df['total_people'] = df['inshade_count'] + df['outshade_count']
    df = df[df['total_people'] > 0].copy()

    print(f"  Images with people: {len(df):,}")
    print(f"  Total people: {df['total_people'].sum():,.0f}")

    return df

def compute_binned_curve(df, utci_col, shade_col, weight_col, n_bins=15):
    """Compute weighted mean shade preference in UTCI bins."""
    # Remove NaN
    valid = df[[utci_col, shade_col, weight_col]].notna().all(axis=1)
    df_valid = df[valid].copy()

    if len(df_valid) == 0:
        return None

    # Create bins
    utci_range = (df_valid[utci_col].quantile(0.01), df_valid[utci_col].quantile(0.99))
    bins = np.linspace(utci_range[0], utci_range[1], n_bins + 1)
    df_valid['bin'] = pd.cut(df_valid[utci_col], bins=bins, include_lowest=True)

    results = []
    for bin_val, group in df_valid.groupby('bin', observed=True):
        if len(group) < 5:  # Skip bins with < 5 images
            continue

        bin_center = (bin_val.left + bin_val.right) / 2
        weights = group[weight_col].values
        values = group[shade_col].values

        # Weighted mean
        weighted_mean = np.average(values, weights=weights)

        # Weighted SE (Kish's effective sample size)
        n_eff = weights.sum()**2 / (weights**2).sum()
        if n_eff > 1:
            weighted_var = np.average((values - weighted_mean)**2, weights=weights)
            se = np.sqrt(max(0, weighted_var / n_eff))  # Ensure non-negative
        else:
            se = np.nan

        results.append({
            'bin_center': bin_center,
            'mean': weighted_mean,
            'se': se,
            'n_images': len(group),
            'sum_weights': weights.sum()
        })

    return pd.DataFrame(results)

def plot_comparison(seattle, nyc, output_dir):
    """Plot UTCI vs shade preference at three adjustment levels."""

    fig, axes = plt.subplots(1, 3, figsize=(18, 5.5))

    # Three adjustment levels
    configs = [
        ('Raw (unweighted)', 'shade_pref_raw', 'total_people'),
        ('DCWP adjusted', 'shade_pref_dcwp', 'total_people'),
        ('DCWP + IPW', 'shade_pref_dcwp', 'w_combined'),
    ]

    city_configs = {
        'seattle': {'data': seattle, 'name': 'Seattle', 'color': '#2E7D32'},
        'new-york-city': {'data': nyc, 'name': 'NYC', 'color': '#1565C0'},
    }

    for idx, (title, shade_col, weight_col) in enumerate(configs):
        ax = axes[idx]

        for city_key, config in city_configs.items():
            df = config['data']

            # Compute curve
            curve = compute_binned_curve(df, 'utci_C', shade_col, weight_col, n_bins=15)

            if curve is None or len(curve) == 0:
                continue

            # Plot
            ax.plot(curve['bin_center'], curve['mean'],
                   color=config['color'], linewidth=2.5,
                   label=config['name'], alpha=0.9, marker='o', markersize=4)

            # Error bands
            ax.fill_between(
                curve['bin_center'],
                curve['mean'] - curve['se'],
                curve['mean'] + curve['se'],
                color=config['color'], alpha=0.15
            )

        # Formatting
        ax.set_xlabel('UTCI (°C)', fontsize=12, fontweight='bold')
        if idx == 0:
            ax.set_ylabel('Shade Preference\n(fraction in shade)', fontsize=12, fontweight='bold')
        ax.set_title(title, fontsize=13, fontweight='bold', pad=10)
        ax.grid(True, alpha=0.25, linestyle='--')
        ax.legend(loc='upper left', framealpha=0.95, fontsize=11)
        ax.set_ylim(-0.05, 1.05)
        ax.axhline(0.5, color='gray', linestyle='--', linewidth=1, alpha=0.4, zorder=0)

        # Add text box with sample info
        ax.text(0.98, 0.02, f'15 UTCI bins\n≥5 images/bin',
               transform=ax.transAxes, fontsize=9,
               ha='right', va='bottom', alpha=0.6,
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.7, edgecolor='none'))

    plt.suptitle('Effect of Adjustments on UTCI-Shade Preference Relationship',
                 fontsize=14, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.96])

    # Save
    output_file = output_dir / 'utci_shade_preference_curves.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✓ Saved plot to {output_file}")

    # Also save as PDF for publication
    pdf_file = output_dir / 'utci_shade_preference_curves.pdf'
    plt.savefig(pdf_file, bbox_inches='tight')
    print(f"✓ Saved PDF to {pdf_file}")

def main():
    print("=" * 70)
    print("UTCI vs SHADE PREFERENCE CURVES")
    print("=" * 70)
    print()

    # Load data
    seattle = load_city_data('seattle')
    nyc = load_city_data('new-york-city')

    # Create output directory
    output_dir = project_root / 'outputs' / 'analysis'
    output_dir.mkdir(parents=True, exist_ok=True)

    # Plot
    print("\nGenerating plots...")
    plot_comparison(seattle, nyc, output_dir)

    print("\n" + "=" * 70)
    print("Done.")
    print("=" * 70)

if __name__ == '__main__':
    main()
