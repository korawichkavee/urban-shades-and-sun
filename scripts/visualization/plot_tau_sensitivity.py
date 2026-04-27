# ABOUTME: Tests sensitivity of DCWP-adjusted estimates to tau parameter choice
# ABOUTME: Shows shade preference curves for tau in [5, 10, 20, 40, 80] meters

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


def fit_smooth_curve_with_tau(df, tau, use_ipw=False):
    """
    Fit quadratic binomial GLM with specific tau for DCWP adjustment.

    Args:
        df: DataFrame with shade counts and distances
        tau: Decay constant for DCWP (meters)
        use_ipw: If True, apply full IPW weights

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

    # DCWP-adjusted effective counts with specified tau
    effective_sun = df['outshade_count'] * np.exp(-df['dist_to_shade_m'] / tau)
    effective_shade = df['inshade_count']
    y = np.column_stack([effective_shade, effective_sun])

    # Apply IPW weights if requested
    if use_ipw:
        weights = df['w_combined'].values
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


def plot_tau_sensitivity(city_name, city_data, output_path, color):
    """
    Create tau sensitivity plot for a city.

    Shows curves for tau = [5, 10, 20, 40, 80] meters.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), sharey=True)

    # Tau values to test
    tau_values = [5, 10, 20, 40, 80]
    alphas = [0.4, 0.5, 1.0, 0.5, 0.4]  # Highlight default tau=20
    linewidths = [1.5, 2.0, 3.0, 2.0, 1.5]

    # Panel 1: DCWP only (no IPW)
    for tau, alpha, lw in zip(tau_values, alphas, linewidths):
        utci, shade_pref = fit_smooth_curve_with_tau(city_data, tau, use_ipw=False)

        linestyle = '-' if tau == 20 else '--'
        label = f'τ = {tau}m' + (' (default)' if tau == 20 else '')

        ax1.plot(utci, shade_pref, linestyle=linestyle, color=color,
                linewidth=lw, alpha=alpha, label=label)

    ax1.set_xlabel('UTCI (°C)', fontsize=11)
    ax1.set_ylabel('Shade Preference (fraction in shade)', fontsize=11)
    ax1.set_title('DCWP Only (no IPW)', fontsize=12, fontweight='bold')
    ax1.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
    ax1.set_xlim(-30, 30)
    ax1.set_ylim(0, 1)
    ax1.legend(loc='upper left', framealpha=0.9, fontsize=9)

    # Panel 2: DCWP + Full IPW
    for tau, alpha, lw in zip(tau_values, alphas, linewidths):
        utci, shade_pref = fit_smooth_curve_with_tau(city_data, tau, use_ipw=True)

        linestyle = '-' if tau == 20 else '--'
        label = f'τ = {tau}m' + (' (default)' if tau == 20 else '')

        ax2.plot(utci, shade_pref, linestyle=linestyle, color=color,
                linewidth=lw, alpha=alpha, label=label)

    ax2.set_xlabel('UTCI (°C)', fontsize=11)
    ax2.set_title('DCWP + Full IPW', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
    ax2.set_xlim(-30, 30)
    ax2.set_ylim(0, 1)
    ax2.legend(loc='upper left', framealpha=0.9, fontsize=9)

    # Add tau interpretation annotation
    textstr = ('τ interpretation:\n'
              '  5m: Shade must be very close\n'
              ' 20m: Moderate detour tolerance\n'
              ' 80m: Willing to walk far for shade\n\n'
              'Decay weight at d=20m:\n'
              '  τ=5m  → 0.02 (heavily discounted)\n'
              '  τ=20m → 0.37 (moderate)\n'
              '  τ=80m → 0.78 (lightly discounted)')

    props = dict(boxstyle='round', facecolor='wheat', alpha=0.8, edgecolor='gray')
    ax2.text(0.98, 0.02, textstr, transform=ax2.transAxes, fontsize=8,
            verticalalignment='bottom', horizontalalignment='right',
            bbox=props, family='monospace')

    plt.suptitle(f'{city_name}: DCWP Sensitivity to τ Parameter',
                fontsize=14, fontweight='bold')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_path}")

    # PDF version
    pdf_path = output_path.with_suffix('.pdf')
    plt.savefig(pdf_path, bbox_inches='tight')
    print(f"Saved: {pdf_path}")

    plt.close()


def compute_tau_effect_table(city_data):
    """
    Compute aggregate shade preference for different tau values.

    Returns:
        DataFrame with tau, shade_pref_dcwp, shade_pref_ipw
    """
    # Compute aggregate raw shade preference (correct baseline)
    raw_shade_pref = (city_data['inshade_count'].sum() /
                     (city_data['inshade_count'].sum() + city_data['outshade_count'].sum()))

    tau_values = [5, 10, 20, 40, 80]
    results = []

    for tau in tau_values:
        # DCWP only
        effective_sun_dcwp = city_data['outshade_count'] * np.exp(-city_data['dist_to_shade_m'] / tau)
        effective_shade_dcwp = city_data['inshade_count']
        total_dcwp = effective_shade_dcwp.sum() + effective_sun_dcwp.sum()
        pref_dcwp = effective_shade_dcwp.sum() / total_dcwp if total_dcwp > 0 else np.nan

        # DCWP + IPW
        weights = city_data['w_combined']
        valid_mask = np.isfinite(weights) & (weights > 0)

        effective_sun_ipw = (city_data.loc[valid_mask, 'outshade_count'] *
                            np.exp(-city_data.loc[valid_mask, 'dist_to_shade_m'] / tau) *
                            weights[valid_mask])
        effective_shade_ipw = city_data.loc[valid_mask, 'inshade_count'] * weights[valid_mask]
        total_ipw = effective_shade_ipw.sum() + effective_sun_ipw.sum()
        pref_ipw = effective_shade_ipw.sum() / total_ipw if total_ipw > 0 else np.nan

        results.append({
            'tau': tau,
            'shade_pref_dcwp': pref_dcwp,
            'shade_pref_ipw': pref_ipw,
            'dcwp_vs_raw_pp': (pref_dcwp - raw_shade_pref) * 100,
            'ipw_vs_raw_pp': (pref_ipw - raw_shade_pref) * 100
        })

    return pd.DataFrame(results)


def main():
    print("=" * 60)
    print("PRIORITY 4: DCWP Tau Sensitivity Analysis")
    print("=" * 60)

    # Process Seattle
    seattle = load_city_data('seattle')

    output_seattle = output_dir / 'tau_sensitivity_seattle.png'
    plot_tau_sensitivity('Seattle', seattle, output_seattle, '#2ca02c')

    print("\nSeattle tau effect table:")
    seattle_table = compute_tau_effect_table(seattle)
    print(seattle_table.to_string(index=False))

    print()

    # Process NYC
    nyc = load_city_data('new-york-city')

    output_nyc = output_dir / 'tau_sensitivity_nyc.png'
    plot_tau_sensitivity('NYC', nyc, output_nyc, '#1f77b4')

    print("\nNYC tau effect table:")
    nyc_table = compute_tau_effect_table(nyc)
    print(nyc_table.to_string(index=False))

    # Save tables
    seattle_table.to_csv(output_dir / 'tau_sensitivity_seattle_table.csv', index=False)
    nyc_table.to_csv(output_dir / 'tau_sensitivity_nyc_table.csv', index=False)

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == '__main__':
    main()
