# ABOUTME: Validates Temp-IPW rationale by overlaying walk rate and shade preference curves
# ABOUTME: Shows that IPW-adjusted curves correct for self-selection at temperature extremes

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

    print(f"Loading {city} SVI data...")
    df = pd.read_csv(data_path, low_memory=False)

    # Filter to images with people
    df = df[df['person_count'] > 0].copy()

    print(f"  {city}: {len(df):,} images with people")

    return df


def load_walk_rate(city):
    """Load walk rate function for a city."""
    # Map city name to walk rate file
    city_map = {
        'seattle': 'seattle_walking_by_utci.csv',
        'new-york-city': 'nyc_walking_by_utci.csv'
    }

    walk_rate_path = project_root / 'outputs' / 'analysis' / city_map[city]

    print(f"Loading {city} walk rate function...")
    df = pd.read_csv(walk_rate_path)

    print(f"  UTCI range: {df['utci_bin_center'].min():.1f}°C to {df['utci_bin_center'].max():.1f}°C")

    return df


def fit_smooth_curve(df, weight_col=None):
    """
    Fit quadratic binomial GLM for smooth shade preference curve.

    Args:
        df: DataFrame with utci_C, shade counts
        weight_col: Weight column name (None for unweighted)

    Returns:
        (utci_grid, p_shade_smooth)
    """
    # Filter out missing UTCI
    df = df[df['utci_C'].notna()].copy()

    # Design matrix
    X = sm.add_constant(pd.DataFrame({
        'utci': df['utci_C'],
        'utci_sq': df['utci_C'] ** 2
    }))

    # DCWP-adjusted effective counts (always use DCWP for this analysis)
    effective_sun = df['outshade_count'] * np.exp(-df['dist_to_shade_m'] / 20.0)
    effective_shade = df['inshade_count']
    y = np.column_stack([effective_shade, effective_sun])

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


def plot_walk_rate_validation(city_name, svi_data, walk_rate_data, output_path, color):
    """
    Create dual-axis plot with walk rate and shade preference.

    Args:
        city_name: City display name
        svi_data: SVI DataFrame with IPW weights
        walk_rate_data: Walk rate DataFrame
        output_path: Output file path
        color: Primary color for plots
    """
    fig, ax1 = plt.subplots(figsize=(10, 6))

    # Left y-axis: Walk rate
    ax1.plot(walk_rate_data['utci_bin_center'], walk_rate_data['walk_rate'],
            'o-', color=color, linewidth=2, markersize=6, alpha=0.7,
            label='Walk rate (trips/person-day)')

    # Add confidence band for walk rate
    ax1.fill_between(walk_rate_data['utci_bin_center'],
                     walk_rate_data['walk_rate_ci_lower'],
                     walk_rate_data['walk_rate_ci_upper'],
                     color=color, alpha=0.15)

    ax1.set_xlabel('UTCI (°C)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Walk Rate (fraction of trips)', fontsize=12, fontweight='bold', color=color)
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
    ax1.set_xlim(-30, 30)

    # Add baseline reference at 20°C
    baseline_walk_rate = walk_rate_data[
        (walk_rate_data['utci_bin_center'] >= 18) &
        (walk_rate_data['utci_bin_center'] <= 22)
    ]['walk_rate'].mean()

    ax1.axhline(baseline_walk_rate, color=color, linestyle=':', alpha=0.5, linewidth=1.5)
    ax1.text(-28, baseline_walk_rate * 1.05, 'Baseline (20°C)',
            fontsize=9, color=color, style='italic')

    # Right y-axis: Shade preference
    ax2 = ax1.twinx()

    # Fit curves for raw and IPW-adjusted
    utci_raw, shade_raw = fit_smooth_curve(svi_data, weight_col=None)
    utci_ipw, shade_ipw = fit_smooth_curve(svi_data, weight_col='w_combined')

    ax2.plot(utci_raw, shade_raw, '--', color='gray', linewidth=2, alpha=0.7,
            label='Shade pref (raw)')
    ax2.plot(utci_ipw, shade_ipw, '-', color='darkgreen', linewidth=2.5,
            label='Shade pref (IPW-adjusted)')

    ax2.set_ylabel('Shade Preference (fraction in shade)', fontsize=12, fontweight='bold', color='darkgreen')
    ax2.tick_params(axis='y', labelcolor='darkgreen')
    ax2.set_ylim(0, 1)

    # Add reference line at 0.5
    ax2.axhline(0.5, color='gray', linestyle=':', alpha=0.3, linewidth=1)

    # Title and legends
    plt.title(f'{city_name}: Walk Rate vs Shade Preference\n' +
             'Validates Asymmetric Temp-IPW Correction',
             fontsize=13, fontweight='bold', pad=15)

    # Combine legends
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', framealpha=0.9, fontsize=10)

    # Add annotation explaining the mechanism
    textstr = ('Temp-IPW Rationale:\n'
              '• Cold (<20°C): Walk rate ↓ → hardy walkers → downweight\n'
              '• Hot (>20°C): Walk rate ↓ → heat-adapted → upweight')

    props = dict(boxstyle='round', facecolor='wheat', alpha=0.8, edgecolor='gray')
    ax1.text(0.98, 0.02, textstr, transform=ax1.transAxes, fontsize=9,
            verticalalignment='bottom', horizontalalignment='right',
            bbox=props, family='monospace')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_path}")

    # PDF version
    pdf_path = output_path.with_suffix('.pdf')
    plt.savefig(pdf_path, bbox_inches='tight')
    print(f"Saved: {pdf_path}")

    plt.close()


def main():
    print("=" * 60)
    print("PRIORITY 3: Walk Rate Validation Plot")
    print("=" * 60)

    # Process Seattle
    seattle_svi = load_city_data('seattle')
    seattle_walk = load_walk_rate('seattle')

    output_seattle = output_dir / 'walk_rate_validation_seattle.png'
    plot_walk_rate_validation('Seattle', seattle_svi, seattle_walk, output_seattle, '#2ca02c')

    print()

    # Process NYC
    nyc_svi = load_city_data('new-york-city')
    nyc_walk = load_walk_rate('new-york-city')

    output_nyc = output_dir / 'walk_rate_validation_nyc.png'
    plot_walk_rate_validation('NYC', nyc_svi, nyc_walk, output_nyc, '#1f77b4')

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == '__main__':
    main()
