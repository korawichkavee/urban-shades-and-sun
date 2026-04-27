# ABOUTME: Creates publication-quality shade preference vs UTCI plots with smooth curves
# ABOUTME: Shows binned estimates as points with smooth quadratic logistic overlay

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
from scipy import stats

# Setup paths
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / 'scripts'))

# Output directory
output_dir = project_root / 'outputs' / 'analysis' / 'figures'
output_dir.mkdir(parents=True, exist_ok=True)


def load_city_data(city):
    """
    Load IPW-adjusted data for a city.

    Args:
        city: 'seattle' or 'new-york-city'

    Returns:
        DataFrame with IPW weights and shade metrics
    """
    data_path = project_root / 'final_run_outputs' / city / f'{city}_final_analysis_with_ipw.csv'

    print(f"Loading {city}...")
    df = pd.read_csv(data_path, low_memory=False)

    # Filter to images with people
    df = df[df['person_count'] > 0].copy()

    print(f"  {city}: {len(df):,} images with people")
    print(f"  UTCI range: {df['utci_C'].min():.1f}°C to {df['utci_C'].max():.1f}°C")

    return df


def compute_binned_estimates(df, utci_bins, min_images=5, weight_col=None, use_dcwp=False):
    """
    Compute binned shade preference estimates with confidence intervals.

    Args:
        df: DataFrame with shade counts and UTCI
        utci_bins: Bin edges for UTCI
        min_images: Minimum images per bin
        weight_col: Weight column name (None for unweighted)
        use_dcwp: If True, use DCWP-adjusted shade preference

    Returns:
        DataFrame with bin_center, shade_pref, ci_lower, ci_upper, n_images
    """
    df = df.copy()
    df['utci_bin'] = pd.cut(df['utci_C'], bins=utci_bins, include_lowest=True)

    results = []

    for bin_label, group in df.groupby('utci_bin', observed=True):
        if len(group) < min_images:
            continue

        bin_center = (bin_label.left + bin_label.right) / 2

        if use_dcwp:
            # Use DCWP-adjusted preference
            if weight_col is not None:
                # Weighted average of DCWP-adjusted preferences
                weights = group[weight_col] * group['person_count']
                shade_pref = np.average(group['shade_pref_dcwp'], weights=weights)

                # Weighted variance for CI
                n_eff = (weights.sum() ** 2) / (weights ** 2).sum()
                se = group['shade_pref_dcwp'].std() / np.sqrt(n_eff)
            else:
                # Unweighted average
                weights = group['person_count']
                shade_pref = np.average(group['shade_pref_dcwp'], weights=weights)
                se = group['shade_pref_dcwp'].std() / np.sqrt(len(group))
        else:
            # Use raw counts
            if weight_col is not None:
                # Weighted counts
                total_shade = (group['inshade_count'] * group[weight_col]).sum()
                total_sun = (group['outshade_count'] * group[weight_col]).sum()
            else:
                # Unweighted counts
                total_shade = group['inshade_count'].sum()
                total_sun = group['outshade_count'].sum()

            total = total_shade + total_sun
            shade_pref = total_shade / total if total > 0 else np.nan

            # Binomial CI (Wilson score interval)
            if total > 0:
                se = np.sqrt(shade_pref * (1 - shade_pref) / total)
            else:
                se = np.nan

        # 95% CI
        ci_lower = shade_pref - 1.96 * se
        ci_upper = shade_pref + 1.96 * se

        results.append({
            'bin_center': bin_center,
            'shade_pref': shade_pref,
            'ci_lower': np.clip(ci_lower, 0, 1),
            'ci_upper': np.clip(ci_upper, 0, 1),
            'n_images': len(group),
            'se': se
        })

    return pd.DataFrame(results)


def fit_smooth_curve(df, weight_col=None, use_dcwp=False):
    """
    Fit quadratic binomial GLM for smooth shade preference curve.

    Args:
        df: DataFrame with utci_C, inshade_count, outshade_count
        weight_col: Weight column name (None for unweighted)
        use_dcwp: If True, use DCWP-adjusted outcomes

    Returns:
        (utci_grid, p_shade_smooth, ci_lower, ci_upper)
    """
    # Filter out missing UTCI
    df = df[df['utci_C'].notna()].copy()

    # Design matrix: intercept, utci, utci^2
    X = sm.add_constant(pd.DataFrame({
        'utci': df['utci_C'],
        'utci_sq': df['utci_C'] ** 2
    }))

    if use_dcwp:
        # Convert DCWP-adjusted preferences to effective counts
        # Use effective sun counts from DCWP
        effective_sun = df['outshade_count'] * np.exp(-df['dist_to_shade_m'] / 20.0)
        effective_shade = df['inshade_count']

        y = np.column_stack([effective_shade, effective_sun])
    else:
        # Raw counts
        y = np.column_stack([df['inshade_count'], df['outshade_count']])

    # Fit model
    if weight_col is not None:
        weights = df[weight_col].values
        # Filter out NaN/inf weights
        valid_mask = np.isfinite(weights) & (weights > 0)
        if not valid_mask.all():
            print(f"  Warning: Filtering {(~valid_mask).sum()} invalid weights")
            weights = weights[valid_mask]
            y = y[valid_mask]
            X = X.iloc[valid_mask]
    else:
        weights = None

    model = sm.GLM(y, X,
                   family=sm.families.Binomial(),
                   freq_weights=weights).fit()

    # Predict over fine grid
    utci_range = df['utci_C'].min(), df['utci_C'].max()
    utci_grid = np.linspace(utci_range[0], utci_range[1], 200)

    X_pred = sm.add_constant(pd.DataFrame({
        'utci': utci_grid,
        'utci_sq': utci_grid ** 2
    }))

    predictions = model.get_prediction(X_pred)
    p_shade_smooth = predictions.predicted_mean
    ci = predictions.conf_int(alpha=0.05)

    return utci_grid, p_shade_smooth, ci[:, 0], ci[:, 1]


def plot_comparison(seattle_data, nyc_data, output_path):
    """
    Create 3-panel comparison plot: Raw / DCWP / DCWP+IPW.

    Args:
        seattle_data: Seattle DataFrame
        nyc_data: NYC DataFrame
        output_path: Output file path
    """
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=True)

    # UTCI bins for binned estimates
    utci_bins = np.linspace(-30, 30, 16)  # 15 bins

    # Colors
    seattle_color = '#2ca02c'
    nyc_color = '#1f77b4'

    # Panel configurations
    panels = [
        {'title': 'Raw (unweighted)', 'weight_col': None, 'use_dcwp': False},
        {'title': 'DCWP adjusted', 'weight_col': None, 'use_dcwp': True},
        {'title': 'DCWP + IPW', 'weight_col': 'w_combined', 'use_dcwp': True}
    ]

    for ax, panel in zip(axes, panels):
        # Compute binned estimates for both cities
        seattle_bins = compute_binned_estimates(
            seattle_data, utci_bins,
            weight_col=panel['weight_col'],
            use_dcwp=panel['use_dcwp']
        )

        nyc_bins = compute_binned_estimates(
            nyc_data, utci_bins,
            weight_col=panel['weight_col'],
            use_dcwp=panel['use_dcwp']
        )

        # Fit smooth curves
        seattle_utci, seattle_smooth, seattle_ci_l, seattle_ci_u = fit_smooth_curve(
            seattle_data,
            weight_col=panel['weight_col'],
            use_dcwp=panel['use_dcwp']
        )

        nyc_utci, nyc_smooth, nyc_ci_l, nyc_ci_u = fit_smooth_curve(
            nyc_data,
            weight_col=panel['weight_col'],
            use_dcwp=panel['use_dcwp']
        )

        # Plot smooth curves with confidence bands
        ax.plot(seattle_utci, seattle_smooth, color=seattle_color, linewidth=2, label='Seattle', zorder=3)
        ax.fill_between(seattle_utci, seattle_ci_l, seattle_ci_u,
                        color=seattle_color, alpha=0.15, zorder=1)

        ax.plot(nyc_utci, nyc_smooth, color=nyc_color, linewidth=2, label='NYC', zorder=3)
        ax.fill_between(nyc_utci, nyc_ci_l, nyc_ci_u,
                        color=nyc_color, alpha=0.15, zorder=1)

        # Plot binned estimates as points with error bars
        ax.errorbar(seattle_bins['bin_center'], seattle_bins['shade_pref'],
                   yerr=[seattle_bins['shade_pref'] - seattle_bins['ci_lower'],
                         seattle_bins['ci_upper'] - seattle_bins['shade_pref']],
                   fmt='o', color=seattle_color, markersize=5, alpha=0.6,
                   elinewidth=1, capsize=3, zorder=2)

        ax.errorbar(nyc_bins['bin_center'], nyc_bins['shade_pref'],
                   yerr=[nyc_bins['shade_pref'] - nyc_bins['ci_lower'],
                         nyc_bins['ci_upper'] - nyc_bins['shade_pref']],
                   fmt='o', color=nyc_color, markersize=5, alpha=0.6,
                   elinewidth=1, capsize=3, zorder=2)

        # Formatting
        ax.set_xlabel('UTCI (°C)', fontsize=11)
        ax.set_title(panel['title'], fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
        ax.set_xlim(-30, 30)
        ax.set_ylim(0, 1)

        # Add metadata annotation
        ax.text(0.02, 0.98, '15 UTCI bins\n≥5 images/bin',
               transform=ax.transAxes, fontsize=8, verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.7, edgecolor='gray'))

        if ax == axes[0]:
            ax.set_ylabel('Shade Preference\n(fraction in shade)', fontsize=11)

        # Legend only on first panel
        if ax == axes[0]:
            ax.legend(loc='upper left', framealpha=0.9, fontsize=10)

    plt.suptitle('Effect of Adjustments on UTCI-Shade Preference Relationship',
                fontsize=14, fontweight='bold', y=0.98)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\nSaved: {output_path}")

    # Also save as PDF for publication
    pdf_path = output_path.with_suffix('.pdf')
    plt.savefig(pdf_path, bbox_inches='tight')
    print(f"Saved: {pdf_path}")

    plt.close()


def main():
    print("=" * 60)
    print("PRIORITY 1: Smoothed Parametric Curves with Binned Overlays")
    print("=" * 60)

    # Load data
    seattle = load_city_data('seattle')
    nyc = load_city_data('new-york-city')

    # Create plot
    output_path = output_dir / 'utci_shade_preference_smooth_curves.png'
    plot_comparison(seattle, nyc, output_path)

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == '__main__':
    main()
