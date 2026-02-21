# ABOUTME: Seasonal triple-adjusted shade preference plot for State College SVI using DIRECTIONAL sidewalk shadow ratios.
# ABOUTME: Combines SR-IPW, DCWP, and temperature activity IPW. Overall + per-season analysis.
# ABOUTME: Uses camera-facing sidewalk: left SR if camera faces left, right SR if camera faces right.
# ABOUTME: All estimates weighted by number of people in each image.

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import statsmodels.api as sm
from scipy.interpolate import interp1d

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[3]
DATA_PATH = ROOT / 'data/state-college/state-college_svi_with_road_bearing.csv'
WALK_RATE_CSV = ROOT / 'data/transit_surveys/processed/p_walk_given_temp_final.csv'
OUTPUT_DIR = ROOT / 'outputs/plots/state_college/seasonal_triple_ipw'

# ---------------------------------------------------------------------------
# Parameters (use SR >= 0.05 based on threshold analysis)
# ---------------------------------------------------------------------------
SR_MIN = 0.05          # shadow-ratio filter threshold (directional sidewalk)
TAU_M = 20.0           # DCWP decay constant (metres)
IPW_SR_CAP_Q = 0.95    # winsorise SR-IPW weights at this quantile
IPW_TEMP_CAP_Q = 0.95  # winsorise temp-IPW weights at this quantile
BASELINE_TEMP = 20.0   # °C reference for asymmetric temp-IPW

# Colour scheme
COL_RAW      = '#555555'
COL_SR       = '#E05A2B'   # orange-red
COL_DCWP     = '#2B7BB9'   # blue
COL_COMBINED = '#6A3D9A'   # purple
COL_TRIPLE   = '#229954'   # green

# Season order
SEASONS = ['Winter', 'Spring', 'Summer', 'Fall']

# ---------------------------------------------------------------------------
# Walk-rate IPW helpers (adapted from visualize_metro_svi_shade_ipw.py)
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
    """
    Asymmetric temperature activity IPW (from compute_ipw_weights in metro script).

    T < baseline  : weight = λ(T)/λ(baseline)
    T >= baseline : weight = λ(baseline)/λ(T)

    Normalised to mean=1, capped at cap_q percentile.
    """
    baseline_rate = float(walk_func(baseline))
    rates = walk_func(utci_c)
    w = np.where(utci_c < baseline, rates / baseline_rate, baseline_rate / rates)
    w = w / w.mean()
    cap = np.percentile(w, cap_q * 100)
    return np.clip(w, None, cap)


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


def load_data():
    df = pd.read_csv(DATA_PATH, low_memory=False)
    df['utci_C'] = df['utci_K'] - 273.15
    df['total_count'] = df['inshade_count'] + df['outshade_count']
    df = df[df['total_count'] > 0].copy()

    # Add datetime and season
    df['datetime-local'] = pd.to_datetime(df['datetime-local'])
    df['month'] = df['datetime-local'].dt.month
    df['season'] = df['month'].apply(get_season)

    # Compute DIRECTIONAL pedestrian shadow ratio (camera-facing sidewalk)
    # If camera faces left: use left sidewalk SR
    # If camera faces right: use right sidewalk SR
    df['shadow_ratio_directional'] = df.apply(
        lambda row: row['shadow_ratio_ped_l'] if row['camera_facing_side'] == 'left'
                    else row['shadow_ratio_ped_r'] if row['camera_facing_side'] == 'right'
                    else np.nan,
        axis=1
    )

    return df


# ---------------------------------------------------------------------------
# Estimator builders
# ---------------------------------------------------------------------------

def make_raw(df):
    """All voted images with valid UTCI."""
    return df.dropna(subset=['utci_C']).copy()


def make_sr_ipw(df):
    """SR ≥ SR_MIN (using DIRECTIONAL sidewalk), winsorised SR-IPW weights."""
    d = df.dropna(subset=['utci_C', 'shadow_ratio_directional']).copy()
    d = d[d['shadow_ratio_directional'] >= SR_MIN].copy()
    if len(d) == 0:
        return d
    sr_ipw = (1.0 / d['shadow_ratio_directional'])
    cap = sr_ipw.quantile(IPW_SR_CAP_Q)
    d['sr_ipw'] = sr_ipw.clip(upper=cap)
    return d


def make_dcwp(df):
    """Valid dist_to_shade_m, DCWP effective counts, no SR filter."""
    d = df.dropna(subset=['utci_C', 'dist_to_shade_m']).copy()
    a = np.exp(-d['dist_to_shade_m'] / TAU_M)
    d['eff_shade'] = d['inshade_count']
    d['eff_sun'] = d['outshade_count'] * a
    return d


def make_combined(df):
    """SR ≥ SR_MIN (DIRECTIONAL) AND valid dist_to_shade_m, SR-IPW + DCWP."""
    d = df.dropna(subset=['utci_C', 'dist_to_shade_m', 'shadow_ratio_directional']).copy()
    d = d[d['shadow_ratio_directional'] >= SR_MIN].copy()
    if len(d) == 0:
        return d
    sr_ipw = (1.0 / d['shadow_ratio_directional'])
    cap = sr_ipw.quantile(IPW_SR_CAP_Q)
    d['sr_ipw'] = sr_ipw.clip(upper=cap)
    a = np.exp(-d['dist_to_shade_m'] / TAU_M)
    d['eff_shade'] = d['inshade_count']
    d['eff_sun'] = d['outshade_count'] * a
    return d


def make_triple(df, walk_func):
    """SR ≥ SR_MIN (DIRECTIONAL) AND valid dist_to_shade_m, SR-IPW + DCWP + Temp-IPW."""
    d = make_combined(df)
    if len(d) == 0:
        return d
    d['temp_ipw'] = compute_temp_ipw(d['utci_C'].values, walk_func)
    d['combined_ipw'] = d['sr_ipw'] * d['temp_ipw']
    # Re-normalise combined weight to mean=1 for interpretability
    d['combined_ipw'] = d['combined_ipw'] / d['combined_ipw'].mean()
    return d


# ---------------------------------------------------------------------------
# GLM fitting
# ---------------------------------------------------------------------------

def fit_glm(x, y_success, y_fail, freq_weights=None, n_pred=300):
    """Fit quadratic binomial GLM; return (x_pred, y_pred, ci_lo, ci_hi)."""
    if len(x) < 10:  # Need minimum samples
        return None
    X = np.column_stack([np.ones(len(x)), x, x ** 2])
    y = np.column_stack([y_success, y_fail])
    kw = {} if freq_weights is None else {'freq_weights': freq_weights}
    try:
        res = sm.GLM(y, X, family=sm.families.Binomial(), **kw).fit(disp=False)
    except Exception as e:
        print(f'    GLM failed: {e}')
        return None
    x_lo, x_hi = np.percentile(x, 5), np.percentile(x, 95)
    xp = np.linspace(x_lo, x_hi, n_pred)
    Xp = np.column_stack([np.ones(n_pred), xp, xp ** 2])
    sf = res.get_prediction(Xp).summary_frame(alpha=0.05)
    return xp, sf['mean'].values, sf['mean_ci_lower'].values, sf['mean_ci_upper'].values


def aggregate_pref(k, n):
    """Weighted aggregate shade preference with Wilson CI."""
    K, N = k.sum(), n.sum()
    if N == 0:
        return np.nan, np.nan, np.nan
    p = K / N
    z = 1.96
    denom = 1 + z ** 2 / N
    centre = (p + z ** 2 / (2 * N)) / denom
    half = z * np.sqrt(p * (1 - p) / N + z ** 2 / (4 * N ** 2)) / denom
    return p, max(0, centre - half), min(1, centre + half)


# ---------------------------------------------------------------------------
# Main plot
# ---------------------------------------------------------------------------

def analyze_season(df, walk_func, season_name):
    """Analyze single season and return statistics + estimates."""
    print(f'\n{season_name}:')
    print('=' * 70)

    # --- build estimator datasets ---
    d_raw  = make_raw(df)
    d_sr   = make_sr_ipw(df)
    d_dcwp = make_dcwp(df)
    d_comb = make_combined(df)
    d_trip = make_triple(df, walk_func)

    n_svi = len(df)
    n_people = df['total_count'].sum()

    print(f'  SVI images: {n_svi:,}')
    print(f'  Total people: {n_people:,.0f}')
    print(f'  Sample sizes: raw={len(d_raw)}, SR-IPW={len(d_sr)}, '
          f'DCWP={len(d_dcwp)}, Combined={len(d_comb)}, Triple={len(d_trip)}')

    # --- aggregate estimates (person-weighted) ---
    results = {}

    # raw
    if len(d_raw) > 0:
        p_raw, lo_raw, hi_raw = aggregate_pref(d_raw['inshade_count'], d_raw['total_count'])
        results['raw'] = (p_raw, lo_raw, hi_raw)
    else:
        results['raw'] = (np.nan, np.nan, np.nan)

    # sr-ipw (person-weighted)
    if len(d_sr) > 0:
        k_sr = d_sr['inshade_count'].values * d_sr['sr_ipw'].values
        n_sr = d_sr['total_count'].values * d_sr['sr_ipw'].values
        p_sr, lo_sr, hi_sr = aggregate_pref(k_sr, n_sr)
        results['sr_ipw'] = (p_sr, lo_sr, hi_sr)
    else:
        results['sr_ipw'] = (np.nan, np.nan, np.nan)

    # dcwp (person-weighted through effective counts)
    if len(d_dcwp) > 0:
        p_dc, lo_dc, hi_dc = aggregate_pref(d_dcwp['eff_shade'], d_dcwp['eff_shade'] + d_dcwp['eff_sun'])
        results['dcwp'] = (p_dc, lo_dc, hi_dc)
    else:
        results['dcwp'] = (np.nan, np.nan, np.nan)

    # combined (person-weighted)
    if len(d_comb) > 0:
        w_co = d_comb['sr_ipw'].values
        k_co = d_comb['eff_shade'].values * w_co
        n_co = (d_comb['eff_shade'] + d_comb['eff_sun']).values * w_co
        p_co, lo_co, hi_co = aggregate_pref(k_co, n_co)
        results['combined'] = (p_co, lo_co, hi_co)
    else:
        results['combined'] = (np.nan, np.nan, np.nan)

    # triple (person-weighted)
    if len(d_trip) > 0:
        w_tr = d_trip['combined_ipw'].values
        k_tr = d_trip['eff_shade'].values * w_tr
        n_tr = (d_trip['eff_shade'] + d_trip['eff_sun']).values * w_tr
        p_tr, lo_tr, hi_tr = aggregate_pref(k_tr, n_tr)
        results['triple'] = (p_tr, lo_tr, hi_tr)
    else:
        results['triple'] = (np.nan, np.nan, np.nan)

    # Print results
    print(f'\n  Aggregate shade preferences (person-weighted):')
    for key, (p, lo, hi) in results.items():
        if not np.isnan(p):
            print(f'    {key:12s}: {p:.3f} [{lo:.3f}, {hi:.3f}]')
        else:
            print(f'    {key:12s}: N/A')

    return {
        'season': season_name,
        'n_svi': n_svi,
        'n_people': int(n_people),
        **results
    }


def plot_seasonal_comparison(all_results, out_dir):
    """Create bar plot comparing all seasons."""
    out_dir.mkdir(parents=True, exist_ok=True)

    # Extract data for plotting
    seasons = [r['season'] for r in all_results]
    estimators = ['raw', 'sr_ipw', 'dcwp', 'combined', 'triple']
    labels = ['Raw', 'SR-IPW', 'DCWP', 'SR+DCWP', 'Triple']
    colors = [COL_RAW, COL_SR, COL_DCWP, COL_COMBINED, COL_TRIPLE]

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    axes = axes.flatten()

    # Plot each season
    for idx, (season, ax) in enumerate(zip(SEASONS, axes)):
        season_data = next((r for r in all_results if r['season'] == season), None)

        if season_data is None:
            ax.set_visible(False)
            continue

        x_pos = np.arange(len(estimators))
        means = []
        errors_lo = []
        errors_hi = []

        for est in estimators:
            if est in season_data and not np.isnan(season_data[est][0]):
                p, lo, hi = season_data[est]
                means.append(p)
                errors_lo.append(p - lo)
                errors_hi.append(hi - p)
            else:
                means.append(0)
                errors_lo.append(0)
                errors_hi.append(0)

        # Create bars
        bars = ax.bar(x_pos, means, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)

        # Add error bars
        ax.errorbar(x_pos, means, yerr=[errors_lo, errors_hi], fmt='none',
                   ecolor='black', capsize=5, capthick=2, linewidth=2)

        # Formatting
        ax.set_xticks(x_pos)
        ax.set_xticklabels(labels, fontsize=11, fontweight='bold')
        ax.set_ylabel('Shade Preference', fontsize=12, fontweight='bold')
        ax.set_ylim(0, 0.5)
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
        ax.grid(axis='y', alpha=0.3)

        # Title with statistics
        n_svi = season_data['n_svi']
        n_people = season_data['n_people']
        ax.set_title(f'{season}\n(SVI: {n_svi:,} | People: {n_people:,})',
                    fontsize=13, fontweight='bold', pad=10)

        # Add value labels on bars
        for i, (bar, mean) in enumerate(zip(bars, means)):
            if mean > 0:
                ax.text(bar.get_x() + bar.get_width()/2, mean + 0.01,
                       f'{mean:.1%}', ha='center', va='bottom',
                       fontsize=9, fontweight='bold')

    plt.suptitle('Seasonal Shade Preference Comparison (State College)\nPerson-Weighted Estimates with Directional Sidewalk Shadow Ratios',
                 fontsize=15, fontweight='bold', y=0.995)
    plt.tight_layout()

    # Save
    output_path = out_dir / 'seasonal_shade_preference_comparison.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f'\nSaved comparison plot -> {output_path}')


def create_summary_table(all_results, out_dir):
    """Create summary table of results."""
    rows = []
    for r in all_results:
        row = {
            'Season': r['season'],
            'SVI Images': r['n_svi'],
            'People': r['n_people'],
        }
        for est in ['raw', 'sr_ipw', 'dcwp', 'combined', 'triple']:
            if est in r and not np.isnan(r[est][0]):
                p, lo, hi = r[est]
                row[est] = f'{p:.3f} [{lo:.3f}, {hi:.3f}]'
            else:
                row[est] = 'N/A'
        rows.append(row)

    summary_df = pd.DataFrame(rows)
    summary_path = out_dir / 'seasonal_summary.csv'
    summary_df.to_csv(summary_path, index=False)
    print(f'\nSaved summary table -> {summary_path}')
    print('\n' + summary_df.to_string(index=False))


def main():
    print('=' * 70)
    print('SEASONAL TRIPLE IPW ANALYSIS - STATE COLLEGE')
    print('=' * 70)

    # Load data and walk rate function
    print('\nLoading data...')
    df = load_data()
    walk_func = load_walk_rate_func(WALK_RATE_CSV)
    print(f'  Total images with people: {len(df):,}')
    print(f'  Total people: {df["total_count"].sum():,.0f}')
    print(f'  Date range: {df["datetime-local"].min()} to {df["datetime-local"].max()}')

    # Overall analysis
    print('\n' + '=' * 70)
    print('OVERALL (ALL SEASONS)')
    print('=' * 70)
    overall_result = analyze_season(df, walk_func, 'Overall')

    # Seasonal analysis
    seasonal_results = []
    for season in SEASONS:
        season_df = df[df['season'] == season].copy()
        if len(season_df) > 0:
            result = analyze_season(season_df, walk_func, season)
            seasonal_results.append(result)

    # Create comparison plot
    print('\n' + '=' * 70)
    print('CREATING COMPARISON PLOTS')
    print('=' * 70)
    plot_seasonal_comparison(seasonal_results, OUTPUT_DIR)

    # Create summary table
    all_results = [overall_result] + seasonal_results
    create_summary_table(all_results, OUTPUT_DIR)

    print('\n' + '=' * 70)
    print('Done.')
    print('=' * 70)


if __name__ == '__main__':
    main()
