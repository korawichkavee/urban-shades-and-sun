# ABOUTME: Shows how each IPW correction layer contributes to final shade preference estimate
# ABOUTME: Creates 4-panel cumulative effect plot showing Raw → +DCWP → +SR-IPW → +Temp-IPW

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm

# Setup paths
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / 'scripts'))

# Output directory
output_dir = project_root / 'outputs' / 'analysis' / 'figures'
output_dir.mkdir(parents=True, exist_ok=True)


def load_city_data(city):
    """Load IPW-adjusted data for a city."""
    data_path = project_root / 'final_run_outputs' / city / f'{city}_final_analysis_with_ipw.csv'

    print(f"Loading {city}...")
    df = pd.read_csv(data_path, low_memory=False)

    # Filter to images with people
    df = df[df['person_count'] > 0].copy()

    print(f"  {city}: {len(df):,} images with people")

    return df


def fit_smooth_curve(df, weight_col=None, use_dcwp=False):
    """
    Fit quadratic binomial GLM for smooth shade preference curve.

    Args:
        df: DataFrame with utci_C, shade counts
        weight_col: Weight column name (None for unweighted)
        use_dcwp: If True, use DCWP-adjusted outcomes

    Returns:
        (utci_grid, p_shade_smooth)
    """
    # Filter out missing UTCI
    df = df[df['utci_C'].notna()].copy()

    # Design matrix: intercept, utci, utci^2
    X = sm.add_constant(pd.DataFrame({
        'utci': df['utci_C'],
        'utci_sq': df['utci_C'] ** 2
    }))

    if use_dcwp:
        # DCWP-adjusted effective counts
        effective_sun = df['outshade_count'] * np.exp(-df['dist_to_shade_m'] / 20.0)
        effective_shade = df['inshade_count']
        y = np.column_stack([effective_shade, effective_sun])
    else:
        # Raw counts
        y = np.column_stack([df['inshade_count'], df['outshade_count']])

    # Fit model with weights
    if weight_col is not None:
        weights = df[weight_col].values
        # Filter out invalid weights
        valid_mask = np.isfinite(weights) & (weights > 0)
        if not valid_mask.all():
            weights = weights[valid_mask]
            y = y[valid_mask]
            X = X.iloc[valid_mask]
    else:
        weights = None

    model = sm.GLM(y, X,
                   family=sm.families.Binomial(),
                   freq_weights=weights).fit()

    # Predict over fine grid
    utci_grid = np.linspace(-30, 30, 200)

    X_pred = sm.add_constant(pd.DataFrame({
        'utci': utci_grid,
        'utci_sq': utci_grid ** 2
    }))

    p_shade_smooth = model.predict(X_pred)

    return utci_grid, p_shade_smooth


def compute_aggregate_at_utci(df, utci_value, weight_col=None, use_dcwp=False):
    """
    Compute aggregate shade preference at a specific UTCI value.

    Args:
        df: DataFrame with shade counts
        utci_value: UTCI temperature to evaluate at
        weight_col: Weight column (None for unweighted)
        use_dcwp: If True, use DCWP adjustment

    Returns:
        Shade preference estimate
    """
    # Filter to images within ±2°C of target UTCI
    mask = (df['utci_C'] >= utci_value - 2) & (df['utci_C'] <= utci_value + 2)
    subset = df[mask]

    if len(subset) == 0:
        return np.nan

    if use_dcwp:
        # DCWP-adjusted
        if weight_col is not None:
            weights = subset[weight_col] * subset['person_count']
            return np.average(subset['shade_pref_dcwp'], weights=weights)
        else:
            weights = subset['person_count']
            return np.average(subset['shade_pref_dcwp'], weights=weights)
    else:
        # Raw counts
        if weight_col is not None:
            total_shade = (subset['inshade_count'] * subset[weight_col]).sum()
            total_sun = (subset['outshade_count'] * subset[weight_col]).sum()
        else:
            total_shade = subset['inshade_count'].sum()
            total_sun = subset['outshade_count'].sum()

        total = total_shade + total_sun
        return total_shade / total if total > 0 else np.nan


def plot_cumulative_effects(seattle_data, nyc_data, output_path):
    """
    Create 4-panel cumulative effect plot.

    Shows: Raw → +DCWP → +SR-IPW → +Full IPW
    """
    fig, axes = plt.subplots(1, 4, figsize=(18, 5), sharey=True)

    # Colors
    seattle_color = '#2ca02c'
    nyc_color = '#1f77b4'

    # Panel configurations (cumulative)
    panels = [
        {'title': 'Raw', 'weight_col': None, 'use_dcwp': False},
        {'title': 'Raw + DCWP', 'weight_col': None, 'use_dcwp': True},
        {'title': 'Raw + DCWP + SR-IPW', 'weight_col': 'w_sr_ipw', 'use_dcwp': True},
        {'title': 'Raw + DCWP + SR-IPW + Temp-IPW', 'weight_col': 'w_combined', 'use_dcwp': True}
    ]

    for ax, panel in zip(axes, panels):
        # Fit smooth curves
        seattle_utci, seattle_smooth = fit_smooth_curve(
            seattle_data,
            weight_col=panel['weight_col'],
            use_dcwp=panel['use_dcwp']
        )

        nyc_utci, nyc_smooth = fit_smooth_curve(
            nyc_data,
            weight_col=panel['weight_col'],
            use_dcwp=panel['use_dcwp']
        )

        # Plot smooth curves
        ax.plot(seattle_utci, seattle_smooth, color=seattle_color, linewidth=2.5, label='Seattle')
        ax.plot(nyc_utci, nyc_smooth, color=nyc_color, linewidth=2.5, label='NYC')

        # Formatting
        ax.set_xlabel('UTCI (°C)', fontsize=11)
        ax.set_title(panel['title'], fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
        ax.set_xlim(-30, 30)
        ax.set_ylim(0, 1)

        # Add horizontal reference line at 0.5
        ax.axhline(0.5, color='gray', linestyle=':', alpha=0.5, linewidth=1)

        if ax == axes[0]:
            ax.set_ylabel('Shade Preference\n(fraction in shade)', fontsize=11)
            ax.legend(loc='upper left', framealpha=0.9, fontsize=10)

    plt.suptitle('Cumulative Effect of IPW Corrections on Shade Preference Curve',
                fontsize=14, fontweight='bold', y=0.98)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\nSaved: {output_path}")

    # PDF version
    pdf_path = output_path.with_suffix('.pdf')
    plt.savefig(pdf_path, bbox_inches='tight')
    print(f"Saved: {pdf_path}")

    plt.close()


def plot_waterfall_chart(seattle_data, nyc_data, output_path):
    """
    Create waterfall chart showing effect sizes at specific UTCI values.
    """
    utci_values = [0, 10, 20, 30]
    cities_data = [('Seattle', seattle_data, '#2ca02c'), ('NYC', nyc_data, '#1f77b4')]

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()

    for ax, utci_val in zip(axes, utci_values):
        x_pos = np.arange(len(cities_data))
        width = 0.35

        for i, (city_name, city_data, color) in enumerate(cities_data):
            # Compute estimates at each correction level
            raw = compute_aggregate_at_utci(city_data, utci_val, weight_col=None, use_dcwp=False)
            dcwp = compute_aggregate_at_utci(city_data, utci_val, weight_col=None, use_dcwp=True)
            sr_ipw = compute_aggregate_at_utci(city_data, utci_val, weight_col='w_sr_ipw', use_dcwp=True)
            full_ipw = compute_aggregate_at_utci(city_data, utci_val, weight_col='w_combined', use_dcwp=True)

            # Effect sizes (percentage points)
            dcwp_effect = (dcwp - raw) * 100
            sr_effect = (sr_ipw - dcwp) * 100
            temp_effect = (full_ipw - sr_ipw) * 100

            # Waterfall bar positions
            y_base = [raw * 100, dcwp * 100, sr_ipw * 100]
            y_height = [dcwp_effect, sr_effect, temp_effect]
            labels = ['DCWP', 'SR-IPW', 'Temp-IPW']
            colors_bars = [color, color, color]
            alphas = [0.5, 0.7, 0.9]

            pos = i * width

            # Draw baseline (raw)
            ax.barh(pos, raw * 100, width * 0.8, left=0, color=color, alpha=0.3, label=f'{city_name} Raw')

            # Draw incremental effects
            cumulative = raw * 100
            for j, (height, label, alpha) in enumerate(zip(y_height, labels, alphas)):
                ax.barh(pos, height, width * 0.8, left=cumulative, color=color, alpha=alpha,
                       edgecolor='black', linewidth=0.5)
                cumulative += height

            # Final value annotation
            ax.text(cumulative + 1, pos, f'{cumulative:.1f}%', va='center', fontsize=9, fontweight='bold')

        ax.set_ylim(-0.5, len(cities_data) * width)
        ax.set_yticks([i * width for i in range(len(cities_data))])
        ax.set_yticklabels([name for name, _, _ in cities_data])
        ax.set_xlabel('Shade Preference (%)', fontsize=10)
        ax.set_title(f'UTCI = {utci_val}°C', fontsize=11, fontweight='bold')
        ax.grid(axis='x', alpha=0.3, linestyle='--', linewidth=0.5)
        ax.set_xlim(0, 100)

    plt.suptitle('Effect Decomposition at Different UTCI Values',
                fontsize=14, fontweight='bold')

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\nSaved: {output_path}")

    # PDF version
    pdf_path = output_path.with_suffix('.pdf')
    plt.savefig(pdf_path, bbox_inches='tight')
    print(f"Saved: {pdf_path}")

    plt.close()


def main():
    print("=" * 60)
    print("PRIORITY 2: Effect Decomposition Plot")
    print("=" * 60)

    # Load data
    seattle = load_city_data('seattle')
    nyc = load_city_data('new-york-city')

    # Create cumulative effects plot
    output_path_cumulative = output_dir / 'effect_decomposition_cumulative.png'
    plot_cumulative_effects(seattle, nyc, output_path_cumulative)

    # Create waterfall chart
    output_path_waterfall = output_dir / 'effect_decomposition_waterfall.png'
    plot_waterfall_chart(seattle, nyc, output_path_waterfall)

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == '__main__':
    main()
