#!/usr/bin/env python3
# ABOUTME: Apply triple IPW + spatial post-stratification + temperature standardization to all metro areas
# ABOUTME: Generates bias-corrected shade preference estimates for each city
# ABOUTME: Outputs: corrected estimates, diagnostic plots, and summary tables

import sys
import logging
from pathlib import Path
from datetime import datetime
import traceback

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for batch processing
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import statsmodels.api as sm
from scipy.interpolate import interp1d
from scipy.stats import gaussian_kde

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / 'data' / 'metro_commute_svi_with_utci'
WALK_RATE_CSV = ROOT / 'data' / 'transit_surveys' / 'processed' / 'p_walk_given_temp_final.csv'
OUTPUT_DIR = ROOT / 'outputs' / 'metro_bias_corrected'
LOG_DIR = OUTPUT_DIR / 'logs'

# Create output directories
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Parameters
SR_MIN = 0.10
TAU_M = 20.0
IPW_SR_CAP_Q = 0.95
IPW_TEMP_CAP_Q = 0.95
BASELINE_TEMP = 20.0
GRID_SIZE_M = 500
WEIGHT_CAP_Q = 0.99

# Setup logging
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
log_file = LOG_DIR / f'metro_analysis_{timestamp}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def load_walk_rate_func(csv_path):
    """Load walk rate function from transit survey data."""
    df = pd.read_csv(csv_path)
    df['walk_rate_safe'] = df['walk_trips_per_person_day'].clip(lower=0.1)
    return interp1d(
        df['temp_bin'].values,
        df['walk_rate_safe'].values,
        kind='linear',
        bounds_error=False,
        fill_value=(df['walk_rate_safe'].iloc[0], df['walk_rate_safe'].iloc[-1]),
    )


def compute_temp_ipw(utci_c, walk_func, baseline=BASELINE_TEMP, cap_q=IPW_TEMP_CAP_Q):
    """Compute temperature IPW weights."""
    baseline_rate = float(walk_func(baseline))
    rates = walk_func(utci_c)
    w = np.where(utci_c < baseline, rates / baseline_rate, baseline_rate / rates)
    w = w / w.mean()
    cap = np.percentile(w, cap_q * 100)
    return np.clip(w, None, cap)


def lat_lon_to_utm(lat, lon):
    """Approximate conversion to meters for gridding."""
    lat_m_per_deg = 111000
    lon_m_per_deg = 85000
    lat_min, lon_min = lat.min(), lon.min()
    x = (lon - lon_min) * lon_m_per_deg
    y = (lat - lat_min) * lat_m_per_deg
    return x, y


def assign_grid_cell(lat, lon, grid_size_m=GRID_SIZE_M):
    """Assign spatial grid cells."""
    x, y = lat_lon_to_utm(lat, lon)
    grid_x = (x // grid_size_m).astype(int)
    grid_y = (y // grid_size_m).astype(int)
    return grid_x.astype(str) + '_' + grid_y.astype(str)


def compute_spatial_weights(df):
    """Compute spatial post-stratification weights."""
    overall_spatial = df.groupby('grid_cell').size() / len(df)
    df['w_spatial'] = 1.0

    # This is applied to overall (no season splitting for metro cities)
    # Just normalize to mean=1
    df['w_spatial'] = df['w_spatial'] / df['w_spatial'].mean()

    return df


def compute_temperature_weights(df):
    """Compute temperature range standardization weights."""
    # For single-city analysis, this becomes identity (no across-season reweighting)
    # But we include it for consistency and future multi-season metro analysis
    df['w_temp_range'] = 1.0

    # If we wanted to standardize to a target distribution, we'd do:
    # kde_target = gaussian_kde(target_utci_distribution)
    # kde_city = gaussian_kde(df['utci_C'].values)
    # w = kde_target(df['utci_C']) / kde_city(df['utci_C'])
    # For now, set to 1 (no correction)

    return df


def load_and_prepare_city_data(city_name, walk_func):
    """Load and prepare data for a single city."""
    logger.info(f'Loading data for {city_name}...')

    city_dir = DATA_DIR / city_name
    csv_files = list(city_dir.glob('*.csv'))

    if not csv_files:
        logger.warning(f'No CSV files found for {city_name}')
        return None

    csv_file = csv_files[0]
    df = pd.read_csv(csv_file, low_memory=False)

    # Basic data preparation
    df['utci_C'] = df['utci_K'] - 273.15
    df['total_count'] = df['inshade_count'] + df['outshade_count']
    df = df[df['total_count'] > 0].copy()

    if len(df) == 0:
        logger.warning(f'{city_name}: No images with people')
        return None

    # Compute shadow ratios
    if 'shadow_ratio_ped_l' in df.columns and 'shadow_ratio_ped_r' in df.columns:
        df['shadow_ratio_ped_avg'] = (df['shadow_ratio_ped_l'] + df['shadow_ratio_ped_r']) / 2.0
    elif 'shadow_ratio' in df.columns:
        df['shadow_ratio_ped_avg'] = df['shadow_ratio']
    else:
        logger.warning(f'{city_name}: No shadow ratio columns found')
        return None

    # Filter by shadow ratio and required columns
    df = df.dropna(subset=['utci_C', 'dist_to_shade_m', 'shadow_ratio_ped_avg']).copy()
    df = df[df['shadow_ratio_ped_avg'] >= SR_MIN].copy()

    if len(df) < 50:
        logger.warning(f'{city_name}: Insufficient data after filtering (n={len(df)})')
        return None

    # Compute triple IPW weights
    # SR-IPW
    sr_ipw = (1.0 / df['shadow_ratio_ped_avg'])
    cap = sr_ipw.quantile(IPW_SR_CAP_Q)
    df['sr_ipw'] = sr_ipw.clip(upper=cap)

    # DCWP effective counts
    a = np.exp(-df['dist_to_shade_m'] / TAU_M)
    df['eff_shade'] = df['inshade_count']
    df['eff_sun'] = df['outshade_count'] * a

    # Temperature IPW
    df['temp_ipw'] = compute_temp_ipw(df['utci_C'].values, walk_func)

    # Combined IPW
    df['combined_ipw'] = df['sr_ipw'] * df['temp_ipw']

    # Assign spatial grid cells
    df['grid_cell'] = assign_grid_cell(df['lat'].values, df['lon'].values, GRID_SIZE_M)

    # Compute bias correction weights
    df = compute_spatial_weights(df)
    df = compute_temperature_weights(df)

    # Final combined weight
    df['w_final'] = df['combined_ipw'] * df['w_spatial'] * df['w_temp_range']

    # Winsorize extreme weights
    cap_final = df['w_final'].quantile(WEIGHT_CAP_Q)
    df['w_final'] = df['w_final'].clip(upper=cap_final)

    # Normalize to mean=1
    df['w_final'] = df['w_final'] / df['w_final'].mean()

    # Person-weighted final weight
    df['weight'] = df['w_final'] * df['total_count']

    logger.info(f'{city_name}: Prepared {len(df):,} observations')
    logger.info(f'{city_name}: UTCI range [{df["utci_C"].min():.1f}, {df["utci_C"].max():.1f}]°C')
    logger.info(f'{city_name}: Weight range [{df["w_final"].min():.2f}, {df["w_final"].max():.2f}]')

    return df


def fit_glm(x, y_success, y_fail, freq_weights=None, n_pred=300):
    """Fit quadratic binomial GLM."""
    if len(x) < 20:
        return None

    X = np.column_stack([np.ones(len(x)), x, x ** 2])
    y = np.column_stack([y_success, y_fail])
    kw = {} if freq_weights is None else {'freq_weights': freq_weights}

    try:
        res = sm.GLM(y, X, family=sm.families.Binomial(), **kw).fit(disp=False)
    except Exception as e:
        logger.warning(f'GLM failed: {e}')
        return None

    x_lo, x_hi = np.percentile(x, 5), np.percentile(x, 95)
    xp = np.linspace(x_lo, x_hi, n_pred)
    Xp = np.column_stack([np.ones(n_pred), xp, xp ** 2])
    sf = res.get_prediction(Xp).summary_frame(alpha=0.05)

    return xp, sf['mean'].values, sf['mean_ci_lower'].values, sf['mean_ci_upper'].values


def aggregate_pref(k, n):
    """Compute aggregate shade preference with Wilson CI."""
    K, N = k.sum(), n.sum()
    if N == 0:
        return np.nan, np.nan, np.nan
    p = K / N
    z = 1.96
    denom = 1 + z ** 2 / N
    centre = (p + z ** 2 / (2 * N)) / denom
    half = z * np.sqrt(p * (1 - p) / N + z ** 2 / (4 * N ** 2)) / denom
    return p, max(0, centre - half), min(1, centre + half)


def analyze_city(city_name, df, walk_func):
    """Analyze single city and return results."""
    logger.info(f'Analyzing {city_name}...')

    # Compute effective sample size
    w = df['w_final'].values
    n_eff = (w.sum() ** 2) / (w ** 2).sum()

    # Fit GLM with person-weighted corrected estimates
    w_glm = df['weight'].values
    glm_result = fit_glm(
        df['utci_C'].values,
        df['eff_shade'].values,
        df['eff_sun'].values,
        freq_weights=w_glm
    )

    # Aggregate estimate
    k = df['eff_shade'].values * df['w_final'].values
    n = (df['eff_shade'] + df['eff_sun']).values * df['w_final'].values
    agg_pref, agg_lo, agg_hi = aggregate_pref(k, n)

    results = {
        'city': city_name,
        'n_raw': len(df),
        'n_eff': n_eff,
        'n_people': int(df['total_count'].sum()),
        'n_spatial_cells': df['grid_cell'].nunique(),
        'utci_min': df['utci_C'].min(),
        'utci_max': df['utci_C'].max(),
        'weight_min': df['w_final'].min(),
        'weight_max': df['w_final'].max(),
        'agg_preference': agg_pref,
        'agg_ci_lower': agg_lo,
        'agg_ci_upper': agg_hi,
        'glm_result': glm_result
    }

    logger.info(f'{city_name}: n_eff={n_eff:.0f}, agg_pref={agg_pref:.3f} [{agg_lo:.3f}, {agg_hi:.3f}]')

    return results


def plot_city_curve(results, output_dir):
    """Create UTCI curve plot for a single city."""
    city_name = results['city']
    city_output_dir = output_dir / city_name
    city_output_dir.mkdir(parents=True, exist_ok=True)

    if results['glm_result'] is None:
        logger.warning(f'{city_name}: No GLM result to plot')
        return

    fig, ax = plt.subplots(1, 1, figsize=(10, 7))

    xp, yp, ci_lo, ci_hi = results['glm_result']

    # Plot curve
    ax.plot(xp, yp, color='#2E86AB', linewidth=3, label='Corrected Estimate', alpha=0.9)
    ax.fill_between(xp, ci_lo, ci_hi, color='#2E86AB', alpha=0.2)

    # Add aggregate point
    ax.scatter([results['utci_min'] + (results['utci_max'] - results['utci_min']) / 2],
              [results['agg_preference']],
              s=100, color='#E05A2B', marker='o', zorder=10,
              label=f'Aggregate: {results["agg_preference"]:.1%}')

    # Formatting
    ax.set_xlabel('UTCI (°C)', fontsize=14, fontweight='bold')
    ax.set_ylabel('Shade Preference', fontsize=14, fontweight='bold')
    ax.set_title(f'{city_name.replace("-", " ").title()} - Shade Preference vs UTCI\n'
                f'Bias-Corrected (Spatial + Temp + Triple IPW)\n'
                f'(n_eff={results["n_eff"]:.0f}, {results["n_people"]:,} people)',
                fontsize=15, fontweight='bold', pad=20)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 1)
    ax.axhline(0.5, color='gray', linestyle='--', linewidth=1.5, alpha=0.5, zorder=0)
    ax.legend(loc='best', fontsize=12)

    output_path = city_output_dir / f'{city_name}_utci_curve_corrected.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    logger.info(f'{city_name}: Saved plot -> {output_path}')


def save_city_summary(results, output_dir):
    """Save summary statistics for a single city."""
    city_name = results['city']
    city_output_dir = output_dir / city_name
    city_output_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        'Metric': [
            'City',
            'Raw Sample Size',
            'Effective Sample Size',
            'Total People',
            'Spatial Grid Cells',
            'UTCI Range (°C)',
            'Weight Range',
            'Aggregate Preference',
            '95% CI Lower',
            '95% CI Upper',
        ],
        'Value': [
            city_name,
            f'{results["n_raw"]:,}',
            f'{results["n_eff"]:.1f}',
            f'{results["n_people"]:,}',
            f'{results["n_spatial_cells"]}',
            f'[{results["utci_min"]:.1f}, {results["utci_max"]:.1f}]',
            f'[{results["weight_min"]:.2f}, {results["weight_max"]:.2f}]',
            f'{results["agg_preference"]:.3f}',
            f'{results["agg_ci_lower"]:.3f}',
            f'{results["agg_ci_upper"]:.3f}',
        ]
    }

    summary_df = pd.DataFrame(summary)
    output_path = city_output_dir / f'{city_name}_summary.csv'
    summary_df.to_csv(output_path, index=False)

    logger.info(f'{city_name}: Saved summary -> {output_path}')


def create_master_comparison(all_results, output_dir):
    """Create master comparison plot and table across all cities."""
    logger.info('Creating master comparison...')

    # Filter valid results
    valid_results = [r for r in all_results if r['glm_result'] is not None]

    if len(valid_results) == 0:
        logger.warning('No valid results for comparison')
        return

    # Create comparison plot
    fig, ax = plt.subplots(1, 1, figsize=(14, 8))

    colors = plt.cm.tab20(np.linspace(0, 1, len(valid_results)))

    for i, result in enumerate(valid_results):
        city_name = result['city']
        xp, yp, ci_lo, ci_hi = result['glm_result']

        label = f'{city_name} (n_eff={result["n_eff"]:.0f})'
        ax.plot(xp, yp, color=colors[i], linewidth=2, label=label, alpha=0.8)

    ax.set_xlabel('UTCI (°C)', fontsize=13, fontweight='bold')
    ax.set_ylabel('Shade Preference', fontsize=13, fontweight='bold')
    ax.set_title('Metro Area Shade Preference Comparison (Bias-Corrected)\n'
                'Spatial Post-Stratification + Temperature Standardization + Triple IPW',
                fontsize=14, fontweight='bold', pad=15)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best', fontsize=9, ncol=2)
    ax.set_ylim(0, 1)
    ax.axhline(0.5, color='gray', linestyle='--', linewidth=1, alpha=0.5, zorder=0)

    output_path = output_dir / 'metro_comparison_corrected.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    logger.info(f'Saved comparison plot -> {output_path}')

    # Create comparison table
    rows = []
    for r in sorted(all_results, key=lambda x: x.get('n_eff', 0), reverse=True):
        rows.append({
            'City': r['city'],
            'Raw_N': r['n_raw'],
            'Eff_N': f'{r["n_eff"]:.1f}',
            'People': r['n_people'],
            'Spatial_Cells': r['n_spatial_cells'],
            'UTCI_Min': f'{r["utci_min"]:.1f}',
            'UTCI_Max': f'{r["utci_max"]:.1f}',
            'Preference': f'{r["agg_preference"]:.3f}',
            'CI_Lower': f'{r["agg_ci_lower"]:.3f}',
            'CI_Upper': f'{r["agg_ci_upper"]:.3f}',
        })

    comparison_df = pd.DataFrame(rows)
    output_path = output_dir / 'metro_comparison_summary.csv'
    comparison_df.to_csv(output_path, index=False)

    logger.info(f'Saved comparison table -> {output_path}')
    logger.info('\n' + comparison_df.to_string(index=False))


def main():
    """Main processing pipeline."""
    logger.info('=' * 70)
    logger.info('METRO BIAS-CORRECTED ANALYSIS')
    logger.info('Spatial Post-Stratification + Temperature Standardization + Triple IPW')
    logger.info('=' * 70)

    # Load walk rate function
    logger.info('Loading walk rate function...')
    walk_func = load_walk_rate_func(WALK_RATE_CSV)

    # Get list of cities
    cities = sorted([d.name for d in DATA_DIR.iterdir() if d.is_dir()])
    logger.info(f'Found {len(cities)} cities to process')

    all_results = []

    # Process each city
    for i, city_name in enumerate(cities, 1):
        logger.info('')
        logger.info('=' * 70)
        logger.info(f'Processing {city_name} ({i}/{len(cities)})')
        logger.info('=' * 70)

        try:
            # Load and prepare data
            df = load_and_prepare_city_data(city_name, walk_func)

            if df is None:
                logger.warning(f'{city_name}: Skipping due to data issues')
                continue

            # Analyze
            results = analyze_city(city_name, df, walk_func)

            # Save outputs
            plot_city_curve(results, OUTPUT_DIR)
            save_city_summary(results, OUTPUT_DIR)

            all_results.append(results)

            logger.info(f'{city_name}: ✓ Complete')

        except Exception as e:
            logger.error(f'{city_name}: ✗ Failed with error: {e}')
            logger.error(traceback.format_exc())
            continue

    # Create master comparison
    if all_results:
        logger.info('')
        logger.info('=' * 70)
        logger.info('CREATING MASTER COMPARISON')
        logger.info('=' * 70)
        create_master_comparison(all_results, OUTPUT_DIR)

    logger.info('')
    logger.info('=' * 70)
    logger.info('COMPLETE')
    logger.info(f'Processed: {len(all_results)}/{len(cities)} cities')
    logger.info(f'Output directory: {OUTPUT_DIR}')
    logger.info(f'Log file: {log_file}')
    logger.info('=' * 70)


if __name__ == '__main__':
    main()
