# ABOUTME: Seasonal shade preference vs UTCI curves - HIERARCHICAL SPATIAL MODEL with season interactions.
# ABOUTME: Bayesian hierarchical GLM with spatial random effects and season-specific coefficients.
# ABOUTME: All estimates weighted by number of people in each image.
# ABOUTME: Uses average of left+right sidewalk shadow ratios and SR >= 0.10 threshold.

from pathlib import Path
import warnings
warnings.filterwarnings('ignore', category=FutureWarning)

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pymc as pm
import arviz as az
from scipy.interpolate import interp1d

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[3]
DATA_PATH = ROOT / 'data/state-college/state-college_svi_with_shadow.csv'
WALK_RATE_CSV = ROOT / 'data/transit_surveys/processed/p_walk_given_temp_final.csv'
OUTPUT_DIR = ROOT / 'outputs/plots/state_college/seasonal_utci_curves_hierarchical'
MODEL_PATH = OUTPUT_DIR / 'hierarchical_model.nc'

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------
SR_MIN = 0.10          # shadow-ratio filter threshold (sidewalk average)
TAU_M = 20.0           # DCWP decay constant (metres)
IPW_SR_CAP_Q = 0.95    # winsorise SR-IPW weights at this quantile
IPW_TEMP_CAP_Q = 0.95  # winsorise temp-IPW weights at this quantile
BASELINE_TEMP = 20.0   # °C reference for asymmetric temp-IPW

# MCMC parameters
N_TUNE = 1000          # Tuning/burn-in samples
N_SAMPLES = 2000       # Post-burn-in samples
N_CHAINS = 4           # Parallel chains
TARGET_ACCEPT = 0.95   # Target acceptance rate

# Grid size for spatial random effects
GRID_SIZE_M = 500

# Colour scheme for seasons
SEASON_COLORS = {
    'Overall': '#000000',
    'Winter': '#2E86AB',    # Blue
    'Spring': '#229954',    # Green
    'Summer': '#E05A2B',    # Orange-red
    'Fall': '#A23B72'       # Purple
}

# Season order
SEASONS = ['Winter', 'Spring', 'Summer', 'Fall']

# ---------------------------------------------------------------------------
# Walk-rate IPW helpers
# ---------------------------------------------------------------------------

def load_walk_rate_func(csv_path):
    """Linear interpolation of pooled walk trips per person-day vs UTCI (°C)."""
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
    """Asymmetric temperature activity IPW."""
    baseline_rate = float(walk_func(baseline))
    rates = walk_func(utci_c)
    w = np.where(utci_c < baseline, rates / baseline_rate, baseline_rate / rates)
    w = w / w.mean()
    cap = np.percentile(w, cap_q * 100)
    return np.clip(w, None, cap)


# ---------------------------------------------------------------------------
# Spatial utilities
# ---------------------------------------------------------------------------

def lat_lon_to_utm(lat, lon):
    """Simple approximate conversion to UTM-like meters (for gridding only)."""
    lat_m_per_deg = 111000
    lon_m_per_deg = 85000
    lat_min, lon_min = lat.min(), lon.min()
    x = (lon - lon_min) * lon_m_per_deg
    y = (lat - lat_min) * lat_m_per_deg
    return x, y


def assign_grid_cell(lat, lon, grid_size_m=GRID_SIZE_M):
    """Assign each point to a spatial grid cell."""
    x, y = lat_lon_to_utm(lat, lon)
    grid_x = (x // grid_size_m).astype(int)
    grid_y = (y // grid_size_m).astype(int)
    return grid_x.astype(str) + '_' + grid_y.astype(str)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def get_season(month):
    """Map month to season."""
    if month in [12, 1, 2]:
        return 'Winter'
    elif month in [3, 4, 5]:
        return 'Spring'
    elif month in [6, 7, 8]:
        return 'Summer'
    else:
        return 'Fall'


def load_and_prepare_data(walk_func):
    """Load data and prepare for hierarchical modeling."""
    df = pd.read_csv(DATA_PATH, low_memory=False)
    df['utci_C'] = df['utci_K'] - 273.15
    df['total_count'] = df['inshade_count'] + df['outshade_count']
    df = df[df['total_count'] > 0].copy()

    # Add datetime and season
    df['datetime-local'] = pd.to_datetime(df['datetime-local'])
    df['month'] = df['datetime-local'].dt.month
    df['season'] = df['month'].apply(get_season)

    # Compute average pedestrian shadow ratio
    df['shadow_ratio_ped_avg'] = (df['shadow_ratio_ped_l'] + df['shadow_ratio_ped_r']) / 2.0

    # Filter to valid data with SR >= SR_MIN
    df = df.dropna(subset=['utci_C', 'dist_to_shade_m', 'shadow_ratio_ped_avg']).copy()
    df = df[df['shadow_ratio_ped_avg'] >= SR_MIN].copy()

    if len(df) == 0:
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

    # Person-weighted combined weight
    df['weight'] = df['combined_ipw'] * df['total_count']

    # Assign spatial grid cells
    df['grid_cell'] = assign_grid_cell(df['lat'].values, df['lon'].values, GRID_SIZE_M)

    # Create numeric indices
    df['season_idx'] = df['season'].map({s: i for i, s in enumerate(SEASONS)})

    # Spatial cell index
    unique_cells = sorted(df['grid_cell'].unique())
    cell_to_idx = {cell: i for i, cell in enumerate(unique_cells)}
    df['spatial_idx'] = df['grid_cell'].map(cell_to_idx)

    # Standardize UTCI for numerical stability
    utci_mean = df['utci_C'].mean()
    utci_std = df['utci_C'].std()
    df['utci_scaled'] = (df['utci_C'] - utci_mean) / utci_std

    return df, utci_mean, utci_std, unique_cells


# ---------------------------------------------------------------------------
# Hierarchical Bayesian Model
# ---------------------------------------------------------------------------

def build_hierarchical_model(df):
    """
    Build hierarchical GLM with spatial random effects and season interactions.

    Model:
    logit(p_i) = β0 + β1*UTCI_i + β2*UTCI_i²
                 + γ_s[i] + δ_s[i]*(β1*UTCI_i + β2*UTCI_i²)  [season effects]
                 + α_j[i]  [spatial random effect]

    where:
    - β0, β1, β2: Global intercept and UTCI effects
    - γ_s: Season-specific intercepts
    - δ_s: Season-specific UTCI slope modifiers
    - α_j: Spatial random effects (grid cell)
    """
    print('\n--- Building Hierarchical Model ---')

    # Extract data
    utci = df['utci_scaled'].values
    utci_sq = utci ** 2
    season_idx = df['season_idx'].values
    spatial_idx = df['spatial_idx'].values

    # Outcome: success / total trials
    y_success = (df['eff_shade'] * df['weight']).values.astype(int)
    y_total = ((df['eff_shade'] + df['eff_sun']) * df['weight']).values.astype(int)

    n_obs = len(df)
    n_seasons = len(SEASONS)
    n_spatial = df['spatial_idx'].nunique()

    print(f'  Observations: {n_obs:,}')
    print(f'  Seasons: {n_seasons}')
    print(f'  Spatial units: {n_spatial}')
    print(f'  Total trials: {y_total.sum():,}')
    print(f'  Total successes: {y_success.sum():,}')

    with pm.Model() as model:
        # Global UTCI effects (weakly informative priors)
        beta0 = pm.Normal('beta0', mu=0, sigma=1)
        beta1 = pm.Normal('beta1', mu=0, sigma=1)
        beta2 = pm.Normal('beta2', mu=0, sigma=1)

        # Season-specific intercepts (random effects)
        sigma_season_intercept = pm.HalfNormal('sigma_season_intercept', sigma=0.5)
        gamma = pm.Normal('gamma', mu=0, sigma=sigma_season_intercept, shape=n_seasons)

        # Season-specific UTCI slope modifiers (random effects)
        sigma_season_slope = pm.HalfNormal('sigma_season_slope', sigma=0.5)
        delta = pm.Normal('delta', mu=0, sigma=sigma_season_slope, shape=n_seasons)

        # Spatial random effects
        sigma_spatial = pm.HalfNormal('sigma_spatial', sigma=0.5)
        alpha = pm.Normal('alpha', mu=0, sigma=sigma_spatial, shape=n_spatial)

        # Linear predictor
        global_effect = beta0 + beta1 * utci + beta2 * utci_sq
        season_intercept = gamma[season_idx]
        season_slope = delta[season_idx] * (beta1 * utci + beta2 * utci_sq)
        spatial_effect = alpha[spatial_idx]

        eta = global_effect + season_intercept + season_slope + spatial_effect

        # Likelihood
        p = pm.invlogit(eta)
        y_obs = pm.Binomial('y_obs', n=y_total, p=p, observed=y_success)

    return model


def fit_model(model, output_path):
    """Fit hierarchical model using NUTS sampler."""
    print(f'\n--- Fitting Model via MCMC ---')
    print(f'  Chains: {N_CHAINS}')
    print(f'  Tune: {N_TUNE}')
    print(f'  Samples per chain: {N_SAMPLES}')
    print(f'  Total samples: {N_CHAINS * N_SAMPLES}')
    print('\nThis may take 10-30 minutes...\n')

    with model:
        trace = pm.sample(
            draws=N_SAMPLES,
            tune=N_TUNE,
            chains=N_CHAINS,
            target_accept=TARGET_ACCEPT,
            return_inferencedata=True,
            random_seed=42
        )

    # Save trace
    trace.to_netcdf(output_path)
    print(f'\nSaved trace -> {output_path}')

    # Print diagnostics
    print('\n--- MCMC Diagnostics ---')
    summary = az.summary(trace, var_names=['beta0', 'beta1', 'beta2',
                                           'sigma_season_intercept', 'sigma_season_slope',
                                           'sigma_spatial'])
    print(summary)

    return trace


# ---------------------------------------------------------------------------
# Posterior predictions
# ---------------------------------------------------------------------------

def generate_predictions(trace, df, utci_mean, utci_std):
    """Generate posterior predictive curves for each season."""
    print('\n--- Generating Posterior Predictions ---')

    # Extract posterior samples
    beta0_post = trace.posterior['beta0'].values.flatten()
    beta1_post = trace.posterior['beta1'].values.flatten()
    beta2_post = trace.posterior['beta2'].values.flatten()
    gamma_post = trace.posterior['gamma'].values  # (chains, draws, seasons)
    delta_post = trace.posterior['delta'].values  # (chains, draws, seasons)

    # Flatten chain dimension
    gamma_post = gamma_post.reshape(-1, len(SEASONS))
    delta_post = delta_post.reshape(-1, len(SEASONS))

    # UTCI grid for predictions (original scale)
    utci_min, utci_max = df['utci_C'].min(), df['utci_C'].max()
    utci_grid = np.linspace(utci_min, utci_max, 300)
    utci_grid_scaled = (utci_grid - utci_mean) / utci_std
    utci_grid_sq = utci_grid_scaled ** 2

    results = {}

    # Overall (marginalizing over seasons)
    print('  Overall...')
    p_overall = []
    for i in range(len(beta0_post)):
        # Average over seasons (equal weighting)
        eta_seasons = []
        for s in range(len(SEASONS)):
            global_effect = beta0_post[i] + beta1_post[i] * utci_grid_scaled + beta2_post[i] * utci_grid_sq
            season_effect = gamma_post[i, s] + delta_post[i, s] * (beta1_post[i] * utci_grid_scaled + beta2_post[i] * utci_grid_sq)
            eta = global_effect + season_effect
            eta_seasons.append(1 / (1 + np.exp(-eta)))
        p_overall.append(np.mean(eta_seasons, axis=0))

    p_overall = np.array(p_overall)
    results['Overall'] = {
        'utci': utci_grid,
        'mean': p_overall.mean(axis=0),
        'lower': np.percentile(p_overall, 2.5, axis=0),
        'upper': np.percentile(p_overall, 97.5, axis=0)
    }

    # By season
    for s, season in enumerate(SEASONS):
        print(f'  {season}...')
        p_season = []
        for i in range(len(beta0_post)):
            global_effect = beta0_post[i] + beta1_post[i] * utci_grid_scaled + beta2_post[i] * utci_grid_sq
            season_effect = gamma_post[i, s] + delta_post[i, s] * (beta1_post[i] * utci_grid_scaled + beta2_post[i] * utci_grid_sq)
            eta = global_effect + season_effect
            # Spatial effects average to zero, so marginal prediction doesn't include them
            p = 1 / (1 + np.exp(-eta))
            p_season.append(p)

        p_season = np.array(p_season)
        results[season] = {
            'utci': utci_grid,
            'mean': p_season.mean(axis=0),
            'lower': np.percentile(p_season, 2.5, axis=0),
            'upper': np.percentile(p_season, 97.5, axis=0)
        }

    return results


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def plot_seasonal_curves(results, df, out_dir):
    """Create preference vs UTCI curves from hierarchical model."""
    out_dir.mkdir(parents=True, exist_ok=True)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))

    # --- LEFT: All seasons together ---
    for season in ['Overall'] + SEASONS:
        if season not in results:
            continue

        utci = results[season]['utci']
        mean = results[season]['mean']
        lower = results[season]['lower']
        upper = results[season]['upper']

        color = SEASON_COLORS.get(season, '#000000')

        # Sample sizes
        if season == 'Overall':
            n = len(df)
            label = f'{season} (n={n:,})'
        else:
            n = len(df[df['season'] == season])
            label = f'{season} (n={n:,})'

        ax1.plot(utci, mean, color=color, linewidth=2.5, label=label, alpha=0.9)
        ax1.fill_between(utci, lower, upper, color=color, alpha=0.15)

    ax1.set_xlabel('UTCI (°C)', fontsize=13, fontweight='bold')
    ax1.set_ylabel('Shade Preference', fontsize=13, fontweight='bold')
    ax1.set_title('Seasonal Shade Preference vs UTCI (Hierarchical Model)\n(Bayesian Spatial Random Effects + Season Interactions)',
                  fontsize=14, fontweight='bold', pad=15)
    ax1.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='best', fontsize=11, framealpha=0.95)
    ax1.set_ylim(0, 1)
    ax1.axhline(0.5, color='gray', linestyle='--', linewidth=1, alpha=0.5, zorder=0)
    ax1.axvline(20, color='gray', linestyle='--', linewidth=1, alpha=0.5, zorder=0)

    # --- RIGHT: Individual season panels ---
    ax2.axis('off')

    from matplotlib.gridspec import GridSpec
    gs = GridSpec(2, 2, left=0.52, right=0.98, top=0.92, bottom=0.08,
                 hspace=0.35, wspace=0.3)

    for idx, season in enumerate(SEASONS):
        if season not in results:
            continue

        row = idx // 2
        col = idx % 2
        ax_sub = fig.add_subplot(gs[row, col])

        utci = results[season]['utci']
        mean = results[season]['mean']
        lower = results[season]['lower']
        upper = results[season]['upper']

        color = SEASON_COLORS.get(season, '#000000')
        n = len(df[df['season'] == season])

        ax_sub.plot(utci, mean, color=color, linewidth=2.5, alpha=0.9)
        ax_sub.fill_between(utci, lower, upper, color=color, alpha=0.2)

        ax_sub.set_xlabel('UTCI (°C)', fontsize=10, fontweight='bold')
        ax_sub.set_ylabel('Shade Pref.', fontsize=10, fontweight='bold')
        ax_sub.set_title(f'{season}\n(n={n:,})',
                       fontsize=11, fontweight='bold', color=color)
        ax_sub.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
        ax_sub.grid(True, alpha=0.3)
        ax_sub.set_ylim(0, 1)
        ax_sub.axhline(0.5, color='gray', linestyle='--', linewidth=0.8, alpha=0.4, zorder=0)
        ax_sub.axvline(20, color='gray', linestyle='--', linewidth=0.8, alpha=0.4, zorder=0)

    plt.suptitle('State College Seasonal Shade Preference (Hierarchical Spatial Model)\nBayesian GLM with Spatial Random Effects + Season Interactions | Sidewalk SR ≥ 0.10',
                 fontsize=16, fontweight='bold', y=0.98)

    output_path = out_dir / 'seasonal_utci_curves_hierarchical.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f'\nSaved hierarchical seasonal curves -> {output_path}')


def plot_overall_only(results, df, out_dir):
    """Create standalone plot for overall preference curve."""
    out_dir.mkdir(parents=True, exist_ok=True)

    if 'Overall' not in results:
        print('No overall result to plot')
        return

    fig, ax = plt.subplots(1, 1, figsize=(10, 7))

    utci = results['Overall']['utci']
    mean = results['Overall']['mean']
    lower = results['Overall']['lower']
    upper = results['Overall']['upper']

    ax.plot(utci, mean, color=SEASON_COLORS['Overall'], linewidth=3, label='Overall (Hierarchical)', alpha=0.9)
    ax.fill_between(utci, lower, upper, color=SEASON_COLORS['Overall'], alpha=0.2)

    ax.set_xlabel('UTCI (°C)', fontsize=14, fontweight='bold')
    ax.set_ylabel('Shade Preference', fontsize=14, fontweight='bold')
    ax.set_title(f'Overall Shade Preference vs UTCI (State College - Hierarchical Model)\n'
                f'Bayesian Spatial Random Effects + Season Interactions\n'
                f'(n={len(df):,} observations, 95% credible interval)',
                fontsize=15, fontweight='bold', pad=20)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 1)

    ax.axhline(0.5, color='gray', linestyle='--', linewidth=1.5, alpha=0.5, zorder=0, label='50% preference')
    ax.axvline(20, color='red', linestyle='--', linewidth=1.5, alpha=0.5, zorder=0, label='20°C baseline')

    ax.legend(loc='best', fontsize=12, framealpha=0.95)

    output_path = out_dir / 'overall_utci_curve_hierarchical.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f'Saved hierarchical overall curve -> {output_path}')


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print('=' * 70)
    print('HIERARCHICAL SPATIAL MODEL - STATE COLLEGE')
    print('Bayesian GLM with Spatial Random Effects + Season Interactions')
    print('=' * 70)

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load data
    print('\nLoading and preparing data...')
    walk_func = load_walk_rate_func(WALK_RATE_CSV)
    result = load_and_prepare_data(walk_func)

    if result is None:
        print('ERROR: No valid data after filtering')
        return

    df, utci_mean, utci_std, unique_cells = result

    print(f'  Total observations: {len(df):,}')
    print(f'  Spatial cells: {len(unique_cells)}')
    print(f'  UTCI: mean={utci_mean:.1f}°C, std={utci_std:.1f}°C')

    for season in SEASONS:
        n = len(df[df['season'] == season])
        print(f'    {season}: {n:,} observations')

    # Build and fit model (or load if exists)
    if MODEL_PATH.exists():
        print(f'\nLoading existing model from {MODEL_PATH}')
        trace = az.from_netcdf(MODEL_PATH)
    else:
        model = build_hierarchical_model(df)
        trace = fit_model(model, MODEL_PATH)

    # Generate predictions
    results = generate_predictions(trace, df, utci_mean, utci_std)

    # Create plots
    print('\n--- Creating Plots ---')
    plot_seasonal_curves(results, df, OUTPUT_DIR)
    plot_overall_only(results, df, OUTPUT_DIR)

    print('\n' + '=' * 70)
    print('Done.')
    print('=' * 70)


if __name__ == '__main__':
    main()
