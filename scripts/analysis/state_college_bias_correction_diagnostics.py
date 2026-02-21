#!/usr/bin/env python3
# ABOUTME: Comprehensive diagnostics for bias correction methodology
# ABOUTME: Addresses reviewer critiques: sensitivity analysis, overlap diagnostics, variance-bias tradeoff
# ABOUTME: Target population: State College residents
# ABOUTME: Estimand: Shade preference at each UTCI value (overall and seasonal)

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.gridspec import GridSpec
import statsmodels.api as sm
from scipy.interpolate import interp1d
from scipy.stats import gaussian_kde
from sklearn.utils import resample

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / 'data/state-college/state-college_svi_with_shadow.csv'
WALK_RATE_CSV = ROOT / 'data/transit_surveys/processed/p_walk_given_temp_final.csv'
OUTPUT_DIR = ROOT / 'outputs/diagnostics/bias_correction'

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Parameters (baseline)
# ---------------------------------------------------------------------------
SR_MIN = 0.10
TAU_M = 20.0
IPW_SR_CAP_Q = 0.95
IPW_TEMP_CAP_Q = 0.95
BASELINE_TEMP = 20.0
GRID_SIZE_M = 500
WEIGHT_CAP_Q = 0.99

# Seasons
SEASONS = ['Winter', 'Spring', 'Summer', 'Fall']

# ---------------------------------------------------------------------------
# Helper Functions
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
        fill_value=(df['walk_rate_safe'].iloc[0], df['walk_rate_safe'].iloc[-1])
    )

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

def assign_grid_cell(lats, lons, grid_size_m):
    """Assign each lat/lon to a spatial grid cell."""
    from pyproj import Transformer

    # Convert to UTM for meter-based grid
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:32618", always_xy=True)
    x, y = transformer.transform(lons, lats)

    # Grid cell assignment
    x_cell = (x // grid_size_m).astype(int)
    y_cell = (y // grid_size_m).astype(int)

    return [f"{xc}_{yc}" for xc, yc in zip(x_cell, y_cell)]

def load_data():
    """Load and prepare data."""
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

    # Assign spatial grid cells
    df['grid_cell'] = assign_grid_cell(df['lat'].values, df['lon'].values, GRID_SIZE_M)

    return df

def compute_triple_ipw(df, walk_func, sr_min, tau_m, ipw_sr_cap_q, ipw_temp_cap_q, baseline_temp):
    """Compute triple IPW weights with specified parameters."""

    # Filter: sidewalk shadow ratio >= threshold
    df = df[df['shadow_ratio_ped_avg'] >= sr_min].copy()

    # SR-IPW
    sr = df['shadow_ratio_ped_avg'].values
    p_sr = 1.0 / (1.0 + np.exp(-10 * (sr - 0.5)))
    p_sr = np.clip(p_sr, 0.05, 0.95)
    w_sr = 1.0 / p_sr
    cap_sr = np.quantile(w_sr, ipw_sr_cap_q)
    w_sr = np.clip(w_sr, None, cap_sr)
    df['w_sr'] = w_sr

    # DCWP
    dist = df['dist_to_shade_m'].values
    w_dcwp = np.exp(-dist / tau_m)
    df['w_dcwp'] = w_dcwp

    # Temp-IPW
    utci_vals = df['utci_C'].values
    walk_rate = walk_func(utci_vals)
    w_temp = 1.0 / walk_rate

    # Asymmetric weighting
    cold_mask = utci_vals < baseline_temp
    cold_factor = 1.0 + 0.5 * ((baseline_temp - utci_vals[cold_mask]) / 20.0)
    w_temp[cold_mask] *= cold_factor

    cap_temp = np.quantile(w_temp, ipw_temp_cap_q)
    w_temp = np.clip(w_temp, None, cap_temp)
    df['w_temp'] = w_temp

    # Combined triple IPW
    df['w_triple_ipw'] = df['w_sr'] * df['w_dcwp'] * df['w_temp']

    return df

def compute_spatial_weights(df, grid_size_m, weight_cap_q):
    """Compute spatial post-stratification weights."""

    # Reassign grid with specified size
    df['grid_cell'] = assign_grid_cell(df['lat'].values, df['lon'].values, grid_size_m)

    # Overall spatial distribution
    overall_spatial = df.groupby('grid_cell').size() / len(df)

    df['w_spatial'] = 1.0

    for season in SEASONS:
        season_mask = df['season'] == season
        n_season = season_mask.sum()

        if n_season == 0:
            continue

        season_spatial = df[season_mask].groupby('grid_cell').size() / n_season
        season_cells = set(season_spatial.index)
        overall_cells = set(overall_spatial.index)

        for cell in season_cells:
            if cell in overall_cells:
                w = overall_spatial[cell] / season_spatial[cell]
                df.loc[season_mask & (df['grid_cell'] == cell), 'w_spatial'] = w

    # Normalize within season
    for season in SEASONS:
        season_mask = df['season'] == season
        if season_mask.sum() > 0:
            mean_w = df.loc[season_mask, 'w_spatial'].mean()
            df.loc[season_mask, 'w_spatial'] /= mean_w

    # Cap weights
    cap = np.quantile(df['w_spatial'], weight_cap_q)
    df['w_spatial'] = np.clip(df['w_spatial'], None, cap)

    return df

def compute_temperature_weights(df):
    """Compute temperature range standardization weights."""

    kde_target = gaussian_kde(df['utci_C'].values, bw_method='scott')
    df['w_temp_range'] = 1.0

    for season in SEASONS:
        season_mask = df['season'] == season
        season_df = df[season_mask]

        if len(season_df) == 0:
            continue

        kde_season = gaussian_kde(season_df['utci_C'].values, bw_method='scott')

        utci_vals = season_df['utci_C'].values
        density_target = kde_target(utci_vals)
        density_season = kde_season(utci_vals)

        w_temp = np.where(density_season > 1e-10,
                         density_target / density_season,
                         1.0)

        df.loc[season_mask, 'w_temp_range'] = w_temp

    # Normalize within season
    for season in SEASONS:
        season_mask = df['season'] == season
        if season_mask.sum() > 0:
            mean_w = df.loc[season_mask, 'w_temp_range'].mean()
            df.loc[season_mask, 'w_temp_range'] /= mean_w

    return df

def compute_full_weights(df, walk_func, sr_min=SR_MIN, tau_m=TAU_M, grid_size_m=GRID_SIZE_M,
                        ipw_sr_cap_q=IPW_SR_CAP_Q, ipw_temp_cap_q=IPW_TEMP_CAP_Q,
                        baseline_temp=BASELINE_TEMP, weight_cap_q=WEIGHT_CAP_Q):
    """Compute all weights with specified parameters."""

    # Triple IPW
    df = compute_triple_ipw(df, walk_func, sr_min, tau_m, ipw_sr_cap_q, ipw_temp_cap_q, baseline_temp)

    # Spatial + temp corrections
    df = compute_spatial_weights(df, grid_size_m, weight_cap_q)
    df = compute_temperature_weights(df)

    # Final weight
    df['w_final'] = df['w_triple_ipw'] * df['w_spatial'] * df['w_temp_range']

    # Person-weight
    df['w_final_person'] = df['w_final'] * df['total_count']

    return df

def compute_n_eff(weights):
    """Compute effective sample size."""
    return (weights.sum() ** 2) / (weights ** 2).sum()

# ---------------------------------------------------------------------------
# Diagnostic 1: UTCI Overlap Diagnostics
# ---------------------------------------------------------------------------

def overlap_diagnostics(df):
    """Generate UTCI overlap diagnostics for all seasons."""

    print('\n' + '='*70)
    print('DIAGNOSTIC 1: UTCI OVERLAP ANALYSIS')
    print('='*70)

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    axes = axes.flatten()

    # Overall UTCI range
    utci_overall = df['utci_C'].values
    utci_min_overall = utci_overall.min()
    utci_max_overall = utci_overall.max()

    print(f'\nOverall UTCI range: [{utci_min_overall:.1f}, {utci_max_overall:.1f}]°C')

    overlap_stats = []

    for idx, season in enumerate(SEASONS):
        ax = axes[idx]
        season_df = df[df['season'] == season]

        if len(season_df) == 0:
            continue

        utci_season = season_df['utci_C'].values
        utci_min_season = utci_season.min()
        utci_max_season = utci_season.max()

        # Compute overlap percentage
        overlap_min = max(utci_min_overall, utci_min_season)
        overlap_max = min(utci_max_overall, utci_max_season)
        overlap_range = overlap_max - overlap_min
        overall_range = utci_max_overall - utci_min_overall
        overlap_pct = (overlap_range / overall_range) * 100

        # KDE plots
        utci_grid = np.linspace(utci_min_overall - 5, utci_max_overall + 5, 500)

        kde_overall = gaussian_kde(utci_overall, bw_method='scott')
        kde_season = gaussian_kde(utci_season, bw_method='scott')

        density_overall = kde_overall(utci_grid)
        density_season = kde_season(utci_grid)

        ax.fill_between(utci_grid, density_overall, alpha=0.3, color='black', label='Overall')
        ax.fill_between(utci_grid, density_season, alpha=0.5, label=f'{season}')

        # Mark non-overlapping regions
        non_overlap_left = utci_grid < utci_min_season
        non_overlap_right = utci_grid > utci_max_season

        ax.axvspan(utci_min_overall, utci_min_season, alpha=0.2, color='red', label='Extrapolation zone')
        ax.axvspan(utci_max_season, utci_max_overall, alpha=0.2, color='red')

        ax.set_xlabel('UTCI (°C)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Density', fontsize=12, fontweight='bold')
        ax.set_title(f'{season}\nOverlap: {overlap_pct:.1f}% | n={len(season_df):,}',
                    fontsize=13, fontweight='bold')
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)

        # Print stats
        print(f'\n{season}:')
        print(f'  UTCI range: [{utci_min_season:.1f}, {utci_max_season:.1f}]°C')
        print(f'  Overlap with overall: {overlap_pct:.1f}%')
        print(f'  Extrapolation needed: {100-overlap_pct:.1f}%')
        print(f'  Sample size: {len(season_df):,}')

        overlap_stats.append({
            'Season': season,
            'UTCI_Min': utci_min_season,
            'UTCI_Max': utci_max_season,
            'Overlap_Pct': overlap_pct,
            'Extrapolation_Pct': 100 - overlap_pct,
            'Sample_Size': len(season_df)
        })

    plt.suptitle('UTCI Density Overlap by Season\n(Red zones indicate extrapolation regions)',
                fontsize=15, fontweight='bold', y=0.995)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'overlap_diagnostics_seasonal.png', dpi=300, bbox_inches='tight')
    print(f'\nSaved overlap plot -> {OUTPUT_DIR / "overlap_diagnostics_seasonal.png"}')

    # Save overlap stats
    overlap_df = pd.DataFrame(overlap_stats)
    overlap_df.to_csv(OUTPUT_DIR / 'overlap_statistics.csv', index=False)
    print(f'Saved overlap statistics -> {OUTPUT_DIR / "overlap_statistics.csv"}')

    return overlap_df

# ---------------------------------------------------------------------------
# Diagnostic 2: Sensitivity Analysis
# ---------------------------------------------------------------------------

def sensitivity_analysis(df, walk_func):
    """Test sensitivity to key parameter choices."""

    print('\n' + '='*70)
    print('DIAGNOSTIC 2: SENSITIVITY ANALYSIS')
    print('='*70)

    sensitivity_results = []

    # Baseline
    print('\n--- BASELINE CONFIGURATION ---')
    df_baseline = compute_full_weights(df.copy(), walk_func)
    n_eff_baseline = compute_n_eff(df_baseline['w_final_person'])
    print(f'Baseline n_eff: {n_eff_baseline:.1f}')

    # Parameter variations
    variations = {
        'SR_threshold': [0.05, 0.10, 0.15],
        'DCWP_tau': [10.0, 20.0, 30.0],
        'Grid_size': [250, 500, 1000],
        'SR_IPW_cap': [0.90, 0.95, 0.99],
        'Weight_cap': [0.95, 0.99, 1.00],
        'Baseline_temp': [15.0, 20.0, 25.0]
    }

    for param_name, param_values in variations.items():
        print(f'\n--- {param_name} ---')

        for val in param_values:
            # Set parameter
            kwargs = {
                'sr_min': SR_MIN,
                'tau_m': TAU_M,
                'grid_size_m': GRID_SIZE_M,
                'ipw_sr_cap_q': IPW_SR_CAP_Q,
                'ipw_temp_cap_q': IPW_TEMP_CAP_Q,
                'baseline_temp': BASELINE_TEMP,
                'weight_cap_q': WEIGHT_CAP_Q
            }

            if param_name == 'SR_threshold':
                kwargs['sr_min'] = val
            elif param_name == 'DCWP_tau':
                kwargs['tau_m'] = val
            elif param_name == 'Grid_size':
                kwargs['grid_size_m'] = val
            elif param_name == 'SR_IPW_cap':
                kwargs['ipw_sr_cap_q'] = val
            elif param_name == 'Weight_cap':
                kwargs['weight_cap_q'] = val if val < 1.0 else 1.0
            elif param_name == 'Baseline_temp':
                kwargs['baseline_temp'] = val

            # Compute weights
            df_variant = compute_full_weights(df.copy(), walk_func, **kwargs)
            n_eff = compute_n_eff(df_variant['w_final_person'])
            n_samples = len(df_variant)

            pct_change = ((n_eff - n_eff_baseline) / n_eff_baseline) * 100

            print(f'  {param_name}={val}: n_eff={n_eff:.1f}, n={n_samples:,} ({pct_change:+.1f}%)')

            sensitivity_results.append({
                'Parameter': param_name,
                'Value': val,
                'n_eff': n_eff,
                'n_samples': n_samples,
                'pct_change_from_baseline': pct_change,
                'is_baseline': (
                    (param_name == 'SR_threshold' and val == SR_MIN) or
                    (param_name == 'DCWP_tau' and val == TAU_M) or
                    (param_name == 'Grid_size' and val == GRID_SIZE_M) or
                    (param_name == 'SR_IPW_cap' and val == IPW_SR_CAP_Q) or
                    (param_name == 'Weight_cap' and val == WEIGHT_CAP_Q) or
                    (param_name == 'Baseline_temp' and val == BASELINE_TEMP)
                )
            })

    # Save results
    sens_df = pd.DataFrame(sensitivity_results)
    sens_df.to_csv(OUTPUT_DIR / 'sensitivity_analysis.csv', index=False)
    print(f'\nSaved sensitivity analysis -> {OUTPUT_DIR / "sensitivity_analysis.csv"}')

    # Plot sensitivity
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    axes = axes.flatten()

    for idx, (param_name, param_data) in enumerate(sens_df.groupby('Parameter')):
        ax = axes[idx]

        baseline_val = param_data[param_data['is_baseline']]['Value'].values[0]

        ax.plot(param_data['Value'], param_data['n_eff'], 'o-', linewidth=2, markersize=8)
        ax.axvline(baseline_val, color='red', linestyle='--', linewidth=2, label='Baseline', alpha=0.7)

        ax.set_xlabel(param_name, fontsize=11, fontweight='bold')
        ax.set_ylabel('Effective Sample Size', fontsize=11, fontweight='bold')
        ax.set_title(f'{param_name} Sensitivity', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend()

    plt.suptitle('Sensitivity of n_eff to Parameter Choices', fontsize=15, fontweight='bold')
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'sensitivity_analysis.png', dpi=300, bbox_inches='tight')
    print(f'Saved sensitivity plot -> {OUTPUT_DIR / "sensitivity_analysis.png"}')

    return sens_df

# ---------------------------------------------------------------------------
# Diagnostic 3: Variance-Bias Tradeoff (Sequential Weight Application)
# ---------------------------------------------------------------------------

def variance_bias_tradeoff(df, walk_func):
    """Analyze variance-bias tradeoff for sequential weight application."""

    print('\n' + '='*70)
    print('DIAGNOSTIC 3: VARIANCE-BIAS TRADEOFF ANALYSIS')
    print('='*70)

    # Apply corrections sequentially
    corrections = []

    # 0. No correction
    df0 = df[df['shadow_ratio_ped_avg'] >= SR_MIN].copy()
    df0['w'] = df0['total_count']  # Just person-weighting
    n_eff_0 = compute_n_eff(df0['w'])
    corrections.append({
        'Stage': 'No correction',
        'n_eff': n_eff_0,
        'n_samples': len(df0),
        'weight_mean': df0['w'].mean(),
        'weight_std': df0['w'].std(),
        'weight_max': df0['w'].max()
    })
    print(f'0. No correction: n_eff={n_eff_0:.1f}, n={len(df0):,}')

    # 1. SR-IPW only
    df1 = compute_triple_ipw(df.copy(), walk_func, SR_MIN, TAU_M, IPW_SR_CAP_Q, IPW_TEMP_CAP_Q, BASELINE_TEMP)
    df1['w'] = df1['w_sr'] * df1['total_count']
    n_eff_1 = compute_n_eff(df1['w'])
    corrections.append({
        'Stage': '+ SR-IPW',
        'n_eff': n_eff_1,
        'n_samples': len(df1),
        'weight_mean': df1['w'].mean(),
        'weight_std': df1['w'].std(),
        'weight_max': df1['w'].max()
    })
    print(f'1. + SR-IPW: n_eff={n_eff_1:.1f}, n={len(df1):,}')

    # 2. SR-IPW + DCWP
    df2 = df1.copy()
    df2['w'] = df2['w_sr'] * df2['w_dcwp'] * df2['total_count']
    n_eff_2 = compute_n_eff(df2['w'])
    corrections.append({
        'Stage': '+ DCWP',
        'n_eff': n_eff_2,
        'n_samples': len(df2),
        'weight_mean': df2['w'].mean(),
        'weight_std': df2['w'].std(),
        'weight_max': df2['w'].max()
    })
    print(f'2. + DCWP: n_eff={n_eff_2:.1f}, n={len(df2):,}')

    # 3. Triple IPW (SR + DCWP + Temp)
    df3 = df2.copy()
    df3['w'] = df3['w_sr'] * df3['w_dcwp'] * df3['w_temp'] * df3['total_count']
    n_eff_3 = compute_n_eff(df3['w'])
    corrections.append({
        'Stage': '+ Temp-IPW',
        'n_eff': n_eff_3,
        'n_samples': len(df3),
        'weight_mean': df3['w'].mean(),
        'weight_std': df3['w'].std(),
        'weight_max': df3['w'].max()
    })
    print(f'3. + Temp-IPW: n_eff={n_eff_3:.1f}, n={len(df3):,}')

    # 4. + Spatial
    df4 = compute_spatial_weights(df3.copy(), GRID_SIZE_M, WEIGHT_CAP_Q)
    df4['w'] = df4['w_sr'] * df4['w_dcwp'] * df4['w_temp'] * df4['w_spatial'] * df4['total_count']
    n_eff_4 = compute_n_eff(df4['w'])
    corrections.append({
        'Stage': '+ Spatial',
        'n_eff': n_eff_4,
        'n_samples': len(df4),
        'weight_mean': df4['w'].mean(),
        'weight_std': df4['w'].std(),
        'weight_max': df4['w'].max()
    })
    print(f'4. + Spatial: n_eff={n_eff_4:.1f}, n={len(df4):,}')

    # 5. + Temperature range
    df5 = compute_temperature_weights(df4.copy())
    df5['w'] = df5['w_sr'] * df5['w_dcwp'] * df5['w_temp'] * df5['w_spatial'] * df5['w_temp_range'] * df5['total_count']
    n_eff_5 = compute_n_eff(df5['w'])
    corrections.append({
        'Stage': '+ Temp Range',
        'n_eff': n_eff_5,
        'n_samples': len(df5),
        'weight_mean': df5['w'].mean(),
        'weight_std': df5['w'].std(),
        'weight_max': df5['w'].max()
    })
    print(f'5. + Temp Range: n_eff={n_eff_5:.1f}, n={len(df5):,}')

    # Save results
    tradeoff_df = pd.DataFrame(corrections)
    tradeoff_df.to_csv(OUTPUT_DIR / 'variance_bias_tradeoff.csv', index=False)
    print(f'\nSaved variance-bias tradeoff -> {OUTPUT_DIR / "variance_bias_tradeoff.csv"}')

    # Plot
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    # Plot 1: n_eff cascade
    stages = tradeoff_df['Stage']
    n_effs = tradeoff_df['n_eff']

    ax1.plot(range(len(stages)), n_effs, 'o-', linewidth=3, markersize=10, color='#2E86AB')
    ax1.set_xticks(range(len(stages)))
    ax1.set_xticklabels(stages, rotation=45, ha='right')
    ax1.set_ylabel('Effective Sample Size', fontsize=13, fontweight='bold')
    ax1.set_title('Information Loss Through Sequential Corrections', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.axhline(100, color='red', linestyle='--', label='n_eff=100 threshold', linewidth=2)
    ax1.legend()

    # Annotate percent loss
    for i in range(1, len(n_effs)):
        pct_loss = ((n_effs[i-1] - n_effs[i]) / n_effs[i-1]) * 100
        ax1.annotate(f'-{pct_loss:.1f}%',
                    xy=(i-0.5, (n_effs[i-1] + n_effs[i])/2),
                    fontsize=9, ha='center', color='red', fontweight='bold')

    # Plot 2: Weight distribution
    ax2.bar(range(len(stages)), tradeoff_df['weight_max'], alpha=0.7, color='#E05A2B')
    ax2.set_xticks(range(len(stages)))
    ax2.set_xticklabels(stages, rotation=45, ha='right')
    ax2.set_ylabel('Maximum Weight', fontsize=13, fontweight='bold')
    ax2.set_title('Weight Extremity by Correction Stage', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'variance_bias_tradeoff.png', dpi=300, bbox_inches='tight')
    print(f'Saved variance-bias plot -> {OUTPUT_DIR / "variance_bias_tradeoff.png"}')

    return tradeoff_df

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print('='*70)
    print('BIAS CORRECTION DIAGNOSTICS - STATE COLLEGE')
    print('Target Population: State College residents')
    print('Estimand: Shade preference P(shade | UTCI) for population')
    print('='*70)

    # Load data
    print('\nLoading data...')
    df = load_data()
    walk_func = load_walk_rate_func(WALK_RATE_CSV)
    print(f'  Total images: {len(df):,}')
    print(f'  Total people: {df["total_count"].sum():,}')

    # Run diagnostics
    overlap_df = overlap_diagnostics(df)
    sens_df = sensitivity_analysis(df, walk_func)
    tradeoff_df = variance_bias_tradeoff(df, walk_func)

    print('\n' + '='*70)
    print('DIAGNOSTICS COMPLETE')
    print(f'Output directory: {OUTPUT_DIR}')
    print('='*70)

if __name__ == '__main__':
    main()
