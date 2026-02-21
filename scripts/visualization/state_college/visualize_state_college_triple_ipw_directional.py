# ABOUTME: Triple-adjusted shade preference plot for State College SVI using DIRECTIONAL sidewalk shadow ratios.
# ABOUTME: Combines SR-IPW, DCWP, and temperature activity IPW. Overall only.
# ABOUTME: Uses camera-facing sidewalk: left SR if camera faces left, right SR if camera faces right.

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
OUTPUT_DIR = ROOT / 'outputs/plots/state_college/triple_ipw_directional'

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

def load_data():
    df = pd.read_csv(DATA_PATH, low_memory=False)
    df['utci_C'] = df['utci_K'] - 273.15
    df['total_count'] = df['inshade_count'] + df['outshade_count']
    df = df[df['total_count'] > 0].copy()

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

def plot_triple(df, walk_func, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)

    # --- build estimator datasets ---
    d_raw  = make_raw(df)
    d_sr   = make_sr_ipw(df)
    d_dcwp = make_dcwp(df)
    d_comb = make_combined(df)
    d_trip = make_triple(df, walk_func)

    print(f'  Sample sizes: raw={len(d_raw)}, SR-IPW={len(d_sr)}, '
          f'DCWP={len(d_dcwp)}, Combined={len(d_comb)}, Triple={len(d_trip)}')

    # --- GLM fits ---
    def _glm_raw(d):
        return fit_glm(d['utci_C'].values, d['inshade_count'].values,
                       d['outshade_count'].values)

    def _glm_sr(d):
        return fit_glm(d['utci_C'].values, d['inshade_count'].values,
                       d['outshade_count'].values,
                       freq_weights=d['sr_ipw'].values * d['total_count'].values)

    def _glm_dcwp(d):
        return fit_glm(d['utci_C'].values, d['eff_shade'].values,
                       d['eff_sun'].values)

    def _glm_comb(d):
        return fit_glm(d['utci_C'].values, d['eff_shade'].values,
                       d['eff_sun'].values,
                       freq_weights=d['sr_ipw'].values * d['total_count'].values)

    def _glm_trip(d):
        return fit_glm(d['utci_C'].values, d['eff_shade'].values,
                       d['eff_sun'].values,
                       freq_weights=d['combined_ipw'].values * d['total_count'].values)

    r_raw  = _glm_raw(d_raw)
    r_sr   = _glm_sr(d_sr)
    r_dcwp = _glm_dcwp(d_dcwp)
    r_comb = _glm_comb(d_comb)
    r_trip = _glm_trip(d_trip)

    # --- aggregate estimates ---
    # raw
    p_raw, lo_raw, hi_raw = aggregate_pref(d_raw['inshade_count'], d_raw['total_count'])
    # sr-ipw
    w_sr = d_sr['sr_ipw'].values * d_sr['total_count'].values
    k_sr = d_sr['inshade_count'].values * d_sr['sr_ipw'].values
    n_sr = d_sr['total_count'].values * d_sr['sr_ipw'].values
    p_sr, lo_sr, hi_sr = aggregate_pref(k_sr, n_sr)
    # dcwp
    p_dc, lo_dc, hi_dc = aggregate_pref(d_dcwp['eff_shade'], d_dcwp['eff_shade'] + d_dcwp['eff_sun'])
    # combined
    w_co = d_comb['sr_ipw'].values
    k_co = d_comb['eff_shade'].values * w_co
    n_co = (d_comb['eff_shade'] + d_comb['eff_sun']).values * w_co
    p_co, lo_co, hi_co = aggregate_pref(k_co, n_co)
    # triple
    w_tr = d_trip['combined_ipw'].values
    k_tr = d_trip['eff_shade'].values * w_tr
    n_tr = (d_trip['eff_shade'] + d_trip['eff_sun']).values * w_tr
    p_tr, lo_tr, hi_tr = aggregate_pref(k_tr, n_tr)

    agg = {
        'Raw':                (p_raw, lo_raw, hi_raw, COL_RAW),
        'SR-IPW\n(directional)':             (p_sr,  lo_sr,  hi_sr,  COL_SR),
        'DCWP':               (p_dc,  lo_dc,  hi_dc,  COL_DCWP),
        'SR-IPW\n+ DCWP':    (p_co,  lo_co,  hi_co,  COL_COMBINED),
        'SR-IPW\n+ DCWP\n+ Temp-IPW': (p_tr, lo_tr, hi_tr, COL_TRIPLE),
    }

    print('  Aggregate shade preferences (USING DIRECTIONAL SIDEWALK SHADOW RATIOS):')
    for label, (p, lo, hi, _) in agg.items():
        print(f'    {label.replace(chr(10)," ")}: {p:.3f} [{lo:.3f}, {hi:.3f}]')

    # -----------------------------------------------------------------------
    # Figure layout: 2 panels
    #   Left  : GLM curves vs UTCI
    #   Right : aggregate bar chart
    # -----------------------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5),
                             gridspec_kw={'width_ratios': [2, 1]})
    ax_glm, ax_agg = axes

    # -- GLM panel --
    estimators = [
        ('Raw',              r_raw,  d_raw,  COL_RAW,      '-',  1.5, 0.12),
        ('SR-IPW (directional)',           r_sr,   d_sr,   COL_SR,       '-',  1.8, 0.12),
        ('DCWP',             r_dcwp, d_dcwp, COL_DCWP,     '-',  1.8, 0.12),
        ('SR-IPW + DCWP',    r_comb, d_comb, COL_COMBINED, '-',  2.0, 0.14),
        ('SR-IPW + DCWP\n+ Temp-IPW', r_trip, d_trip, COL_TRIPLE, '--', 2.2, 0.14),
    ]

    for label, result, dset, col, ls, lw, alpha in estimators:
        if result is None:
            continue
        xp, yp, ylo, yhi = result
        ax_glm.plot(xp, yp, color=col, ls=ls, lw=lw,
                    label=label.replace('\n', ' '))
        ax_glm.fill_between(xp, ylo, yhi, color=col, alpha=alpha)

    ax_glm.set_xlabel('UTCI (°C)', fontsize=11)
    ax_glm.set_ylabel('Shade preference', fontsize=11)
    ax_glm.set_title('Shade preference vs UTCI — all estimators (DIRECTIONAL sidewalk)\n'
                     f'(SR_directional ≥ {SR_MIN}, τ = {TAU_M:.0f} m, overall)', fontsize=11)
    ax_glm.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=0))
    ax_glm.set_ylim(0, None)
    ax_glm.legend(fontsize=8.5, loc='upper left')
    ax_glm.grid(True, alpha=0.3)

    # Rug
    utci_rug = d_raw['utci_C'].values
    ax_glm.plot(utci_rug, np.full_like(utci_rug, -0.015), '|',
                color='#999999', markersize=3, alpha=0.3, markeredgewidth=0.5)

    # -- Aggregate bar panel --
    labels = list(agg.keys())
    x_pos = np.arange(len(labels))
    for i, (lab, (p, lo, hi, col)) in enumerate(agg.items()):
        ax_agg.bar(i, p, color=col, alpha=0.85, width=0.6)
        ax_agg.errorbar(i, p, yerr=[[p - lo], [hi - p]],
                        fmt='none', color='#333333', capsize=4, linewidth=1.5)
        ax_agg.text(i, hi + 0.005, f'{p:.1%}', ha='center', va='bottom',
                    fontsize=8, color='#333333')

    ax_agg.set_xticks(x_pos)
    ax_agg.set_xticklabels(labels, fontsize=8.5)
    ax_agg.set_ylabel('Aggregate shade preference', fontsize=11)
    ax_agg.set_title('Aggregate estimates\n(95% Wilson CI)', fontsize=11)
    ax_agg.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=0))
    ax_agg.set_ylim(0, max(p for p, *_ in agg.values()) * 1.25)
    ax_agg.grid(axis='y', alpha=0.3)

    fig.tight_layout()
    out = out_dir / 'triple_ipw_shade_preference_directional.png'
    fig.savefig(out, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  Saved: {out}')


# ---------------------------------------------------------------------------
# Walk rate + weight diagnostic
# ---------------------------------------------------------------------------

def plot_walk_rate_diagnostic(df, walk_func, out_dir):
    """Two-panel: (1) walk rate λ(T) curve; (2) resulting IPW weights on SC data."""
    out_dir.mkdir(parents=True, exist_ok=True)

    t_grid = np.linspace(-15, 40, 300)
    lambda_grid = walk_func(t_grid)

    baseline_rate = float(walk_func(BASELINE_TEMP))
    w_grid = np.where(
        t_grid < BASELINE_TEMP,
        lambda_grid / baseline_rate,
        baseline_rate / lambda_grid,
    )
    w_grid = w_grid / w_grid.mean()

    d = df.dropna(subset=['utci_C']).copy()

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    ax_lr, ax_wt = axes

    # -- Walk rate --
    ax_lr.plot(t_grid, lambda_grid, color='#2B7BB9', lw=2)
    ax_lr.axvline(BASELINE_TEMP, color='#888888', ls='--', lw=1,
                  label=f'Baseline {BASELINE_TEMP}°C')
    ax_lr.set_xlabel('UTCI (°C)', fontsize=11)
    ax_lr.set_ylabel('Walk trips per person-day', fontsize=11)
    ax_lr.set_title('Pooled walk rate function λ(T)\n(25 US travel surveys)', fontsize=11)
    ax_lr.legend(fontsize=9)
    ax_lr.grid(True, alpha=0.3)

    # Rug of SC data
    ax_lr.plot(d['utci_C'].values, np.full(len(d), lambda_grid.min() - 0.05),
               '|', color='#999999', markersize=3, alpha=0.3)

    # -- IPW weights on SC distribution --
    sc_utci = d['utci_C'].values
    w_sc_raw = np.where(
        sc_utci < BASELINE_TEMP,
        walk_func(sc_utci) / baseline_rate,
        baseline_rate / walk_func(sc_utci),
    )
    w_sc = w_sc_raw / w_sc_raw.mean()
    cap = np.percentile(w_sc, IPW_TEMP_CAP_Q * 100)
    w_sc = np.clip(w_sc, None, cap)

    ax_wt.plot(t_grid, w_grid / w_grid.mean(), color='#E05A2B', lw=2,
               label='Theoretical weight w(T)')
    ax_wt.scatter(sc_utci, w_sc, s=6, color='#555555', alpha=0.25,
                  label='SC observations')
    ax_wt.axhline(1.0, color='#888888', ls='--', lw=1, label='w = 1 (no adjustment)')
    ax_wt.axvline(BASELINE_TEMP, color='#888888', ls=':', lw=1)
    ax_wt.set_xlabel('UTCI (°C)', fontsize=11)
    ax_wt.set_ylabel('Temperature activity IPW weight', fontsize=11)
    ax_wt.set_title('Asymmetric temp-IPW weights\n(State College observations)', fontsize=11)
    ax_wt.legend(fontsize=9, loc='upper right')
    ax_wt.grid(True, alpha=0.3)

    # Annotate the range
    ax_wt.text(0.02, 0.97,
               f'Weight range: {w_sc.min():.2f}–{w_sc.max():.2f}\n'
               f'(p5={np.percentile(w_sc, 5):.2f}, p95={np.percentile(w_sc, 95):.2f})',
               transform=ax_wt.transAxes, va='top', fontsize=8.5,
               bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))

    fig.tight_layout()
    out = out_dir / 'triple_ipw_walk_rate_diagnostic_directional.png'
    fig.savefig(out, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  Saved: {out}')


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print('Loading data...')
    df = load_data()
    print(f'  Voted images: {len(df)}')

    # Check that we have directional shadow ratios
    has_directional = df['shadow_ratio_directional'].notna().sum()
    print(f'  Images with directional shadow ratios: {has_directional} ({has_directional/len(df)*100:.1f}%)')

    if has_directional == 0:
        print('ERROR: No directional shadow ratios found! Re-run add_road_bearing_to_state_college.py first.')
        return

    # Check distribution
    left_count = (df['camera_facing_side'] == 'left').sum()
    right_count = (df['camera_facing_side'] == 'right').sum()
    print(f'  Camera facing left:  {left_count} ({left_count/len(df)*100:.1f}%)')
    print(f'  Camera facing right: {right_count} ({right_count/len(df)*100:.1f}%)')

    print('Loading walk rate function...')
    walk_func = load_walk_rate_func(WALK_RATE_CSV)

    print('Plotting triple-adjusted shade preference (DIRECTIONAL sidewalk shadow ratios)...')
    plot_triple(df, walk_func, OUTPUT_DIR)

    print('Plotting walk rate diagnostic...')
    plot_walk_rate_diagnostic(df, walk_func, OUTPUT_DIR)

    print('Done.')


if __name__ == '__main__':
    main()
