# ABOUTME: Detour-conditioned shade preference analysis for State College SVI
# ABOUTME: Produces detour-tolerance curve, DCWP vs raw comparison, and distance diagnostics

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import statsmodels.api as sm
from scipy import stats as scipy_stats

INPUT_PATH = Path(__file__).parent.parent.parent.parent / 'data' / 'state-college' / 'state-college_svi_with_shadow.csv'
OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / 'outputs' / 'plots' / 'state_college' / 'dtc'

# Detour-tolerance curve thresholds (metres)
DTC_THRESHOLDS = [0, 3, 5, 8, 10, 15, 20, 30, 40, 50, 75, 100, 150, np.inf]

# DCWP exponential decay constant (metres)
DCWP_TAU_M = 20.0

MIN_OBS = 15

# ── Colours (match existing IPW script palette) ────────────────────────────────
RAW_COLOR  = '#7f8c8d'
DCWP_COLOR = '#2c7bb6'
DTC_COLOR  = '#1a9641'

WALKABLE_TYPES = {
    'footway', 'path', 'pedestrian', 'living_street',
    'residential', 'unclassified', 'tertiary', 'tertiary_link',
    'service', 'track',
}
NON_WALKABLE_TYPES = {
    'primary', 'primary_link', 'secondary', 'secondary_link',
    'cycleway', 'steps', 'motorway', 'motorway_link',
}
WALKABLE_COLOR  = '#2980b9'
NON_WALK_COLOR  = '#c0392b'

TYPE_LABELS = {
    'footway': 'Footway', 'path': 'Path', 'pedestrian': 'Pedestrian',
    'living_street': 'Living Street', 'residential': 'Residential',
    'unclassified': 'Unclassified', 'tertiary': 'Tertiary',
    'tertiary_link': 'Tertiary Link', 'service': 'Service', 'track': 'Track',
    'primary': 'Primary', 'primary_link': 'Primary Link',
    'secondary': 'Secondary', 'secondary_link': 'Secondary Link',
    'cycleway': 'Cycleway', 'steps': 'Steps',
}


# ── Data preparation ────────────────────────────────────────────────────────────

def prepare_data(df):
    """
    Filter to voted sunny rows with valid dist_to_shade_m.
    Returns df_voted (all voted rows) and df_dtc (has valid dist_to_shade_m).
    """
    df = df.copy()
    df['total_people'] = df['inshade_count'].fillna(0) + df['outshade_count'].fillna(0)

    mask_voted = (
        (df['is_sunny'].astype(str).str.lower() == 'true') &
        df['inshade_count'].notna() &
        df['outshade_count'].notna() &
        (df['total_people'] >= 1) &
        df['shadow_ratio'].notna()
    )
    df_voted = df[mask_voted].copy()
    df_voted['shade_pref'] = df_voted['inshade_count'] / df_voted['total_people']

    # DCWP subset: requires valid dist_to_shade_m (NaN = sun below horizon)
    df_dtc = df_voted.dropna(subset=['dist_to_shade_m']).copy()

    # DCWP effective counts (exponential accessibility decay)
    d = df_dtc['dist_to_shade_m']
    a = np.exp(-d / DCWP_TAU_M)
    df_dtc['access_weight'] = a
    df_dtc['eff_sun']   = df_dtc['outshade_count'] * a
    df_dtc['eff_shade'] = df_dtc['inshade_count'].astype(float)
    df_dtc['eff_total'] = df_dtc['eff_shade'] + df_dtc['eff_sun']
    df_dtc['dcwp'] = np.where(
        df_dtc['eff_total'] > 0,
        df_dtc['eff_shade'] / df_dtc['eff_total'],
        np.nan
    )

    # Walkability label
    for ds in [df_voted, df_dtc]:
        ds['walkability'] = ds['highway'].apply(
            lambda h: 'Walkable' if h in WALKABLE_TYPES
                      else ('Non-walkable' if h in NON_WALKABLE_TYPES else 'Other')
        )

    n_nan = mask_voted.sum() - len(df_dtc) if mask_voted.sum() > len(df_voted) else (len(df_voted) - len(df_dtc))
    print('─' * 60)
    print(f'Voted sunny rows total      : {len(df_voted):,}')
    print(f'  With valid dist_to_shade_m: {len(df_dtc):,}')
    print(f'  NaN (sun below horizon)   : {n_nan:,}')
    print(f'  In shadow (dist = 0)      : {(df_dtc["dist_to_shade_m"] == 0).sum():,}')
    print(f'  dist <= 5m                : {(df_dtc["dist_to_shade_m"] <= 5).sum():,}')
    print(f'  dist <= 20m               : {(df_dtc["dist_to_shade_m"] <= 20).sum():,}')
    print(f'  dist <= 50m               : {(df_dtc["dist_to_shade_m"] <= 50).sum():,}')
    print(f'DCWP tau = {DCWP_TAU_M} m')
    print(f'  Mean raw shade_pref       : {df_dtc["shade_pref"].mean():.3f}')
    print(f'  Mean DCWP score           : {df_dtc["dcwp"].mean():.3f}')
    print('─' * 60)

    return df_voted, df_dtc


# ── GLM fitting ─────────────────────────────────────────────────────────────────

def fit_glm_raw(df_sub, x_col, degree=2, n_points=200):
    """Fit binomial GLM using raw inshade/outshade counts."""
    x = df_sub[x_col].dropna()
    df_sub = df_sub.loc[x.index]
    k = df_sub['inshade_count'].values.astype(float)
    n = df_sub['total_people'].values.astype(float)
    y = np.column_stack([k, n - k])
    polys = [x.values ** i for i in range(1, degree + 1)]
    X = sm.add_constant(np.column_stack(polys))
    try:
        model = sm.GLM(y, X, family=sm.families.Binomial()).fit(disp=0)
    except Exception as e:
        print(f'    GLM failed ({x_col}): {e}')
        return None
    x_range = np.linspace(x.min(), x.max(), n_points)
    polys_pred = [x_range ** i for i in range(1, degree + 1)]
    X_pred = sm.add_constant(np.column_stack(polys_pred), has_constant='add')
    return x_range, model.predict(X_pred), model


def fit_glm_dcwp(df_sub, x_col, degree=2, n_points=200):
    """Fit binomial GLM using DCWP effective counts (eff_shade, eff_sun)."""
    x = df_sub[x_col].dropna()
    df_sub = df_sub.loc[x.index]
    df_sub = df_sub[df_sub['eff_total'] > 0]
    x = df_sub[x_col].values
    k = df_sub['eff_shade'].values
    n_fail = df_sub['eff_sun'].values
    y = np.column_stack([k, n_fail])
    polys = [x ** i for i in range(1, degree + 1)]
    X = sm.add_constant(np.column_stack(polys))
    try:
        model = sm.GLM(y, X, family=sm.families.Binomial()).fit(disp=0)
    except Exception as e:
        print(f'    DCWP GLM failed ({x_col}): {e}')
        return None
    x_range = np.linspace(x.min(), x.max(), n_points)
    polys_pred = [x_range ** i for i in range(1, degree + 1)]
    X_pred = sm.add_constant(np.column_stack(polys_pred), has_constant='add')
    return x_range, model.predict(X_pred), model


# ── Detour-tolerance curve computation ─────────────────────────────────────────

def compute_dtc(df_dtc):
    """
    Compute p̂(shade | dist ≤ D) and 95% CI for each threshold in DTC_THRESHOLDS.
    Returns a DataFrame with columns: D, n, shade_pref, ci_lo, ci_hi.
    """
    rows = []
    for D in DTC_THRESHOLDS:
        sub = df_dtc[df_dtc['dist_to_shade_m'] <= D]
        n = len(sub)
        if n == 0:
            continue
        total_in  = sub['inshade_count'].sum()
        total_all = sub['total_people'].sum()
        p = float(total_in / total_all) if total_all > 0 else np.nan
        # Wilson score interval on aggregate proportion
        ci_lo, ci_hi = _wilson_ci(total_in, total_all)
        label = f'{D:.0f}' if D != np.inf else '∞'
        rows.append({'D': D, 'D_label': label, 'n': n,
                     'shade_pref': p * 100, 'ci_lo': ci_lo * 100, 'ci_hi': ci_hi * 100})
    return pd.DataFrame(rows)


def _wilson_ci(k, n, z=1.96):
    """Wilson score confidence interval for a proportion."""
    if n == 0:
        return np.nan, np.nan
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


# ── Plot 1: Distance-to-shade diagnostics ──────────────────────────────────────

def plot_dist_diagnostics(df_voted, df_dtc, out_dir):
    """
    Four-panel diagnostic showing how distance to shade relates to shade behaviour.
      Panel 1: Histogram of dist_to_shade_m
      Panel 2: Binned mean shade preference by dist_to_shade_m band
      Panel 3: Sun vs shade standing by in/out-of-shadow status
      Panel 4: DCWP access weight function for several tau values
    """
    print('\n[1/4] Distance diagnostics ...')
    fig, axes = plt.subplots(1, 4, figsize=(20, 5))

    # ── Panel 1: dist histogram ─────────────────────────────────────────────
    ax = axes[0]
    d_vals = df_dtc['dist_to_shade_m'].values
    d_clip = np.clip(d_vals, 0, 100)  # clip tail for readability
    ax.hist(d_clip, bins=50, color=DTC_COLOR, alpha=0.75, edgecolor='white', lw=0.4)
    for xv, lbl in [(5, '5m'), (20, '20m'), (50, '50m')]:
        ax.axvline(xv, color='#c0392b', lw=1, ls='--', alpha=0.7)
        ax.text(xv + 0.5, ax.get_ylim()[1] * 0.92, lbl, fontsize=7.5,
                color='#c0392b', va='top')
    in_shad_n = (d_vals == 0).sum()
    ax.text(0.65, 0.88, f'dist = 0: {in_shad_n:,} ({in_shad_n/len(d_vals)*100:.0f}%)',
            transform=ax.transAxes, fontsize=8, color='#333333')
    ax.set_xlabel('Distance to nearest shade (m)', fontsize=10)
    ax.set_ylabel('Count', fontsize=10)
    ax.set_title('Distribution of\ndistance to nearest shade', fontsize=11)
    ax.grid(True, alpha=0.3)
    total_n = len(d_vals)
    nan_n   = df_voted['dist_to_shade_m'].isna().sum()
    ax.text(0.65, 0.78, f'NaN (no sun): {nan_n:,}', transform=ax.transAxes,
            fontsize=8, color='#888888')
    ax.text(0.65, 0.68, f'Displayed: ≤ 100m\n(max = {d_vals.max():.0f}m)',
            transform=ax.transAxes, fontsize=8, color='#888888')

    # ── Panel 2: binned shade preference by distance band ─────────────────
    ax2 = axes[1]
    # Narrow distance bins for the first 50m, then a final ">50" bucket
    bin_edges = [0, 1, 3, 5, 8, 10, 15, 20, 30, 50, np.inf]
    bin_labels = ['0', '1–3', '3–5', '5–8', '8–10', '10–15', '15–20', '20–30', '30–50', '>50']
    prefs, ci_los, ci_his, ns_bin = [], [], [], []
    for lo, hi, lbl in zip(bin_edges[:-1], bin_edges[1:], bin_labels):
        sub = df_dtc[(df_dtc['dist_to_shade_m'] >= lo) & (df_dtc['dist_to_shade_m'] < hi)]
        n_b = len(sub)
        ns_bin.append(n_b)
        if n_b < 5:
            prefs.append(np.nan); ci_los.append(np.nan); ci_his.append(np.nan)
            continue
        tot_in  = sub['inshade_count'].sum()
        tot_all = sub['total_people'].sum()
        p = tot_in / tot_all if tot_all > 0 else np.nan
        lo_ci, hi_ci = _wilson_ci(tot_in, tot_all)
        prefs.append(p * 100)
        ci_los.append(lo_ci * 100)
        ci_his.append(hi_ci * 100)

    prefs   = np.array(prefs, dtype=float)
    ci_los  = np.array(ci_los, dtype=float)
    ci_his  = np.array(ci_his, dtype=float)
    y_pos   = np.arange(len(bin_labels))
    colors  = [DTC_COLOR if not np.isnan(p) else '#dddddd' for p in prefs]

    valid = ~np.isnan(prefs)
    ax2.barh(y_pos[valid], prefs[valid],
             xerr=[prefs[valid] - ci_los[valid], ci_his[valid] - prefs[valid]],
             color=[colors[i] for i in np.where(valid)[0]],
             alpha=0.8, height=0.65,
             error_kw={'ecolor': '#333333', 'capsize': 3, 'lw': 1})
    for i, (p, n_b) in enumerate(zip(prefs, ns_bin)):
        if not np.isnan(p):
            ax2.text(p + 1.5, y_pos[i], f'n={n_b:,}', va='center', fontsize=7.5,
                     color='#555555')
        elif n_b > 0:
            ax2.text(1.0, y_pos[i], f'n={n_b} (too few)', va='center', fontsize=7,
                     color='#aaaaaa')
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(bin_labels, fontsize=9)
    ax2.set_xlabel('Shade preference (%)', fontsize=10)
    ax2.set_ylabel('Distance to shade (m)', fontsize=10)
    ax2.set_title('Shade preference by\ndistance-to-shade band', fontsize=11)
    ax2.axvline(50, color='grey', lw=0.8, ls='--', alpha=0.4)
    overall_pref = df_dtc['inshade_count'].sum() / df_dtc['total_people'].sum() * 100
    ax2.axvline(overall_pref, color=RAW_COLOR, lw=1.2, ls=':', alpha=0.7,
                label=f'Overall mean ({overall_pref:.1f}%)')
    ax2.legend(fontsize=8, loc='lower right')
    ax2.set_xlim(0, 80)
    ax2.grid(True, axis='x', alpha=0.3)

    # ── Panel 3: in-shade vs out-of-shade SVI points ───────────────────────
    ax3 = axes[2]
    in_shad  = df_dtc[df_dtc['in_shade_shadow'] == True]
    out_shad = df_dtc[df_dtc['in_shade_shadow'] == False]

    def _pref_counts(sub):
        tot_in  = sub['inshade_count'].sum()
        tot_all = sub['total_people'].sum()
        p = tot_in / tot_all if tot_all > 0 else 0.0
        lo, hi = _wilson_ci(tot_in, tot_all)
        return p * 100, (p - lo) * 100, (hi - p) * 100, len(sub)

    p_in,  lo_in,  hi_in,  n_in  = _pref_counts(in_shad)
    p_out, lo_out, hi_out, n_out = _pref_counts(out_shad)

    # Also split out-of-shadow by distance quartile
    q1 = out_shad['dist_to_shade_m'].quantile(0.33)
    q2 = out_shad['dist_to_shade_m'].quantile(0.67)
    out_near = out_shad[out_shad['dist_to_shade_m'] <= q1]
    out_mid  = out_shad[(out_shad['dist_to_shade_m'] > q1) & (out_shad['dist_to_shade_m'] <= q2)]
    out_far  = out_shad[out_shad['dist_to_shade_m'] > q2]

    p_near, lo_near, hi_near, n_near = _pref_counts(out_near)
    p_mid,  lo_mid,  hi_mid,  n_mid  = _pref_counts(out_mid)
    p_far,  lo_far,  hi_far,  n_far  = _pref_counts(out_far)

    groups = [
        (f'SVI in shadow\n(dist = 0, n={n_in:,})',               p_in,   lo_in,   hi_in,   '#1a9641'),
        (f'Outside shadow\nnear (≤{q1:.0f}m, n={n_near:,})',    p_near, lo_near, hi_near, '#74c476'),
        (f'Outside shadow\nmid ({q1:.0f}–{q2:.0f}m, n={n_mid:,})', p_mid, lo_mid, hi_mid, '#fdae61'),
        (f'Outside shadow\nfar (>{q2:.0f}m, n={n_far:,})',      p_far,  lo_far,  hi_far,  '#d7191c'),
    ]
    ys     = np.arange(len(groups))
    vals   = [g[1] for g in groups]
    lo_err = [g[2] for g in groups]
    hi_err = [g[3] for g in groups]
    cols   = [g[4] for g in groups]

    ax3.barh(ys, vals,
             xerr=[lo_err, hi_err],
             color=cols, alpha=0.82, height=0.55,
             error_kw={'ecolor': '#333333', 'capsize': 3, 'lw': 1})
    ax3.set_yticks(ys)
    ax3.set_yticklabels([g[0] for g in groups], fontsize=8.5)
    ax3.set_xlabel('Shade preference (%)', fontsize=10)
    ax3.set_title('Shade preference by\nSVI shadow status', fontsize=11)
    ax3.axvline(50, color='grey', lw=0.8, ls='--', alpha=0.4)
    ax3.axvline(overall_pref, color=RAW_COLOR, lw=1.2, ls=':', alpha=0.7,
                label=f'Overall mean ({overall_pref:.1f}%)')
    ax3.legend(fontsize=8, loc='lower right')
    ax3.set_xlim(0, 80)
    ax3.grid(True, axis='x', alpha=0.3)

    # ── Panel 4: DCWP access weight function ──────────────────────────────
    ax4 = axes[3]
    d_plot = np.linspace(0, 80, 300)
    tau_vals = [5, 10, 20, 40]
    colors_tau = ['#1a9641', '#2c7bb6', '#fd8d3c', '#d7191c']
    for tau, col in zip(tau_vals, colors_tau):
        a_vals = np.exp(-d_plot / tau)
        ax4.plot(d_plot, a_vals, color=col, lw=1.8,
                 label=f'τ = {tau} m')
    ax4.axhline(1/np.e, color='grey', lw=0.8, ls='--', alpha=0.5,
                label='1/e ≈ 0.37 (weight at τ)')
    ax4.set_xlabel('Distance to nearest shade (m)', fontsize=10)
    ax4.set_ylabel('Accessibility weight a(d)', fontsize=10)
    ax4.set_title(f'DCWP weight function\na(d) = exp(−d / τ)', fontsize=11)
    ax4.set_ylim(-0.02, 1.05)
    ax4.axvline(DCWP_TAU_M, color='#2c7bb6', lw=1, ls=':', alpha=0.7)
    ax4.text(DCWP_TAU_M + 0.5, 0.10, f'τ = {DCWP_TAU_M:.0f}m\n(selected)', fontsize=8,
             color='#2c7bb6')
    ax4.legend(fontsize=9)
    ax4.grid(True, alpha=0.3)

    fig.suptitle('State College: Distance to shade — diagnostics', fontsize=14, fontweight='bold')
    fig.tight_layout()
    out_path = out_dir / 'dtc_dist_diagnostics.png'
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  Saved: {out_path.name}')


# ── Plot 2: Detour-tolerance curve ─────────────────────────────────────────────

def plot_detour_tolerance_curve(df_dtc, out_dir):
    """
    Two-panel plot:
      Left:  Cumulative detour-tolerance curve — p̂(shade | dist ≤ D) vs D
      Right: Within-band shade preference (non-cumulative) vs distance band
    """
    print('\n[2/4] Detour-tolerance curve ...')
    dtc = compute_dtc(df_dtc)

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # ── Panel 1: cumulative DTC ────────────────────────────────────────────
    ax = axes[0]

    # Plot finite thresholds only on x-axis (put inf at the right margin)
    finite = dtc[dtc['D'] < np.inf].copy()
    inf_row = dtc[dtc['D'] == np.inf]

    x_vals = finite['D'].values
    y_vals = finite['shade_pref'].values
    y_lo   = finite['ci_lo'].values
    y_hi   = finite['ci_hi'].values
    n_vals = finite['n'].values

    ax.fill_between(x_vals, y_lo, y_hi, color=DTC_COLOR, alpha=0.18)
    ax.plot(x_vals, y_vals, color=DTC_COLOR, lw=2.2, marker='o', ms=5,
            label='p̂(shade | dist ≤ D)')

    # Mark the raw (D=∞) level
    if len(inf_row):
        raw_level = float(inf_row['shade_pref'].iloc[0])
        ax.axhline(raw_level, color=RAW_COLOR, lw=1.4, ls='--', alpha=0.8,
                   label=f'Raw (all distances): {raw_level:.1f}%')

    # Annotate n at key thresholds
    for _, row in finite.iterrows():
        if row['D'] in [0, 10, 20, 50]:
            ax.annotate(f"n={row['n']:,}", xy=(row['D'], row['shade_pref']),
                        xytext=(row['D'] + 1.5, row['shade_pref'] + 1.5),
                        fontsize=7.5, color='#333333',
                        arrowprops=dict(arrowstyle='-', color='#aaaaaa', lw=0.7))

    ax.set_xlabel('Detour threshold D (metres)', fontsize=11)
    ax.set_ylabel('Shade preference (%)', fontsize=11)
    ax.set_title('Detour-tolerance curve\np̂(shade | dist ≤ D) vs detour distance', fontsize=12)
    ax.set_ylim(0, 60)
    ax.set_xlim(-2, 155)
    ax.axhline(50, color='grey', lw=0.8, ls='--', alpha=0.4)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    # Secondary x-axis annotation: sample size
    ax_n = ax.twinx()
    ax_n.plot(x_vals, n_vals, color='#aaaaaa', lw=1, ls=':', alpha=0.7)
    ax_n.set_ylabel('n (images at dist ≤ D)', fontsize=9, color='#888888')
    ax_n.tick_params(axis='y', labelcolor='#888888', labelsize=8)
    ax_n.set_ylim(0, n_vals.max() * 3)

    # ── Panel 2: within-band (non-cumulative) shade preference ────────────
    ax2 = axes[1]
    band_edges  = [0, 1, 3, 5, 8, 10, 15, 20, 30, 50, np.inf]
    band_labels = ['0–1\n(incl. in shadow)', '1–3', '3–5', '5–8',
                   '8–10', '10–15', '15–20', '20–30', '30–50', '>50']
    band_prefs, band_lo, band_hi, band_ns = [], [], [], []
    for lo, hi in zip(band_edges[:-1], band_edges[1:]):
        sub = df_dtc[(df_dtc['dist_to_shade_m'] >= lo) & (df_dtc['dist_to_shade_m'] < hi)]
        n_b = len(sub)
        band_ns.append(n_b)
        if n_b < MIN_OBS:
            band_prefs.append(np.nan); band_lo.append(np.nan); band_hi.append(np.nan)
            continue
        tot_in  = sub['inshade_count'].sum()
        tot_all = sub['total_people'].sum()
        p = tot_in / tot_all if tot_all > 0 else np.nan
        lo_ci, hi_ci = _wilson_ci(tot_in, tot_all)
        band_prefs.append(p * 100)
        band_lo.append(lo_ci * 100)
        band_hi.append(hi_ci * 100)

    band_prefs = np.array(band_prefs, dtype=float)
    band_lo    = np.array(band_lo, dtype=float)
    band_hi    = np.array(band_hi, dtype=float)
    x_pos      = np.arange(len(band_labels))

    valid = ~np.isnan(band_prefs)
    bar_colors = [DTC_COLOR if i == 0 else '#74c476' if i <= 4 else '#fdae61'
                  if i <= 7 else '#d7191c' for i in range(len(band_labels))]
    ax2.bar(x_pos[valid], band_prefs[valid],
            yerr=[band_prefs[valid] - band_lo[valid],
                  band_hi[valid] - band_prefs[valid]],
            color=[bar_colors[i] for i in np.where(valid)[0]],
            alpha=0.82, width=0.65,
            error_kw={'ecolor': '#333333', 'capsize': 4, 'lw': 1.1})
    for i, (p, n_b) in enumerate(zip(band_prefs, band_ns)):
        yoff = 2.5
        if not np.isnan(p):
            ax2.text(x_pos[i], p + yoff + (band_hi[i] - p), f'n={n_b:,}',
                     ha='center', va='bottom', fontsize=7, color='#555555')

    ax2.axhline(50, color='grey', lw=0.8, ls='--', alpha=0.4, label='50%')
    overall_pref = df_dtc['inshade_count'].sum() / df_dtc['total_people'].sum() * 100
    ax2.axhline(overall_pref, color=RAW_COLOR, lw=1.4, ls=':', alpha=0.8,
                label=f'Overall mean ({overall_pref:.1f}%)')
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(band_labels, fontsize=8)
    ax2.set_xlabel('Distance to nearest shade (m)', fontsize=11)
    ax2.set_ylabel('Shade preference (%)', fontsize=11)
    ax2.set_title('Within-band shade preference\n(non-cumulative, 95% CI)', fontsize=12)
    ax2.set_ylim(0, 70)
    ax2.legend(fontsize=9)
    ax2.grid(True, axis='y', alpha=0.3)

    fig.suptitle('State College: Detour-tolerance curve', fontsize=14, fontweight='bold')
    fig.tight_layout()
    out_path = out_dir / 'dtc_detour_tolerance_curve.png'
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  Saved: {out_path.name}')


# ── Plot 3: Raw vs DCWP shade preference vs UTCI ──────────────────────────────

def plot_utci_comparison(df_dtc, out_dir):
    """
    Two-panel: shade preference vs UTCI
      Left:  Raw GLM (unweighted counts)
      Right: DCWP GLM (effective counts using exponential accessibility decay)
    Matches format of ipw_vs_raw_utci.png.
    """
    print('\n[3/4] UTCI comparison (Raw vs DCWP) ...')
    x_col = 'utci_C'

    dr = df_dtc.dropna(subset=[x_col]).copy()
    di = dr.copy()

    fig, axes = plt.subplots(1, 2, figsize=(15, 6), sharey=True)

    panel_configs = [
        ('Raw (unweighted)', dr, fit_glm_raw,  RAW_COLOR),
        (f'DCWP-adjusted (τ = {DCWP_TAU_M:.0f} m)', di, fit_glm_dcwp, DCWP_COLOR),
    ]

    for ax, (title_suffix, data, fit_fn, col_main) in zip(axes, panel_configs):
        groups = [
            ('Overall',      data,                                          col_main,      '-',  2.2),
            ('Walkable',     data[data['walkability'] == 'Walkable'],       WALKABLE_COLOR, '--', 1.6),
            ('Non-walkable', data[data['walkability'] == 'Non-walkable'],   NON_WALK_COLOR, ':',  1.6),
        ]
        handles = []
        for name, sub, color, ls, lw in groups:
            if len(sub) < MIN_OBS:
                print(f'    Skipping {name}: n={len(sub)} < {MIN_OBS}')
                continue
            result = fit_fn(sub, x_col, degree=2)
            if result is None:
                continue
            x_r, p_h, _ = result
            line, = ax.plot(x_r, p_h * 100, color=color, ls=ls, lw=lw,
                            label=f'{name}  (n={len(sub):,})')
            handles.append(line)

        ax.set_xlabel('UTCI (°C)', fontsize=11)
        ax.set_ylabel('Shade preference (%)' if ax is axes[0] else '', fontsize=11)
        ax.set_title(f'Shade preference vs UTCI\n{title_suffix}', fontsize=12)
        ax.set_ylim(0, 100)
        ax.axhline(50, color='grey', lw=0.8, ls='--', alpha=0.5)
        ax.legend(handles=handles, fontsize=9)
        ax.grid(True, alpha=0.3)

    fig.suptitle(f'State College: Raw vs DCWP-adjusted shade preference (UTCI, τ = {DCWP_TAU_M:.0f} m)',
                 fontsize=14, fontweight='bold')
    note = (f'DCWP: sun-standing votes discounted by a(d) = exp(−d / {DCWP_TAU_M:.0f}m), '
            f'where d = distance to nearest shade.  '
            f'NaN rows excluded (sun below horizon): {len(df_dtc):,} images used.')
    fig.text(0.5, -0.01, note, ha='center', va='top', fontsize=8,
             color='#555555', style='italic')
    fig.tight_layout()
    out_path = out_dir / 'dtc_dcwp_vs_raw_utci.png'
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  Saved: {out_path.name}')


# ── Plot 4: DCWP score diagnostics ─────────────────────────────────────────────

def plot_dcwp_diagnostics(df_dtc, out_dir):
    """
    Three-panel DCWP diagnostic:
      Left:   DCWP score vs raw shade_pref scatter (coloured by dist_to_shade_m)
      Middle: Histogram of DCWP score vs raw shade_pref distribution
      Right:  DCWP score vs dist_to_shade_m (mean per bin ± CI)
    """
    print('\n[4/4] DCWP diagnostics ...')
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    df_v = df_dtc.dropna(subset=['dcwp', 'shade_pref']).copy()

    # ── Panel 1: DCWP vs raw scatter ──────────────────────────────────────
    ax = axes[0]
    d_clipped = np.clip(df_v['dist_to_shade_m'].values, 0, 80)
    sc = ax.scatter(df_v['shade_pref'] * 100, df_v['dcwp'] * 100,
                    c=d_clipped, cmap='RdYlGn_r', alpha=0.25, s=8,
                    rasterized=True, vmin=0, vmax=50)
    ax.plot([0, 100], [0, 100], color='grey', lw=1, ls='--', alpha=0.5,
            label='No adjustment (y = x)')
    plt.colorbar(sc, ax=ax, label='dist to shade (m, capped at 80)')

    # Highlight the direction of adjustment
    raw_mean  = df_v['shade_pref'].mean() * 100
    dcwp_mean = df_v['dcwp'].mean() * 100
    ax.axvline(raw_mean,  color=RAW_COLOR,  lw=1.3, ls=':', alpha=0.8,
               label=f'Raw mean ({raw_mean:.1f}%)')
    ax.axhline(dcwp_mean, color=DCWP_COLOR, lw=1.3, ls=':', alpha=0.8,
               label=f'DCWP mean ({dcwp_mean:.1f}%)')
    ax.set_xlabel('Raw shade preference (per image, %)', fontsize=10)
    ax.set_ylabel(f'DCWP score (τ = {DCWP_TAU_M:.0f} m, %)', fontsize=10)
    ax.set_title('DCWP vs raw shade preference\n(colour = dist to shade)', fontsize=11)
    ax.set_xlim(-3, 103)
    ax.set_ylim(-3, 103)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # ── Panel 2: distribution comparison ──────────────────────────────────
    ax2 = axes[1]
    bins = np.linspace(0, 1, 26)
    ax2.hist(df_v['shade_pref'].values, bins=bins, color=RAW_COLOR,
             alpha=0.6, label=f'Raw shade_pref\n(mean = {raw_mean:.1f}%)', density=True)
    ax2.hist(df_v['dcwp'].dropna().values, bins=bins, color=DCWP_COLOR,
             alpha=0.6, label=f'DCWP score\n(mean = {dcwp_mean:.1f}%)', density=True)
    ax2.axvline(raw_mean / 100,  color=RAW_COLOR,  lw=2, ls='--', alpha=0.8)
    ax2.axvline(dcwp_mean / 100, color=DCWP_COLOR, lw=2, ls='--', alpha=0.8)
    ax2.set_xlabel('Score (0 = all sun, 1 = all shade)', fontsize=10)
    ax2.set_ylabel('Density', fontsize=10)
    ax2.set_title('Distribution: raw shade_pref\nvs DCWP score', fontsize=11)
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3)

    # ── Panel 3: mean DCWP by dist band ───────────────────────────────────
    ax3 = axes[2]
    band_edges_fine = [0, 1, 3, 5, 8, 10, 15, 20, 30, 50, np.inf]
    band_lbls_fine  = ['0–1\n(in shadow)', '1–3', '3–5', '5–8', '8–10',
                       '10–15', '15–20', '20–30', '30–50', '>50']
    raw_means_b, dcwp_means_b, band_ns3 = [], [], []
    for lo, hi in zip(band_edges_fine[:-1], band_edges_fine[1:]):
        sub = df_v[(df_v['dist_to_shade_m'] >= lo) & (df_v['dist_to_shade_m'] < hi)]
        n_b = len(sub)
        band_ns3.append(n_b)
        if n_b < MIN_OBS:
            raw_means_b.append(np.nan); dcwp_means_b.append(np.nan)
            continue
        raw_means_b.append(sub['shade_pref'].mean() * 100)
        dcwp_means_b.append(sub['dcwp'].mean() * 100)

    x_pos3 = np.arange(len(band_lbls_fine))
    ax3.plot(x_pos3, raw_means_b,  color=RAW_COLOR,  marker='o', lw=1.8, ms=6,
             label=f'Raw shade_pref (mean per band)')
    ax3.plot(x_pos3, dcwp_means_b, color=DCWP_COLOR, marker='s', lw=1.8, ms=6,
             label=f'DCWP score (mean per band)')
    ax3.set_xticks(x_pos3)
    ax3.set_xticklabels(band_lbls_fine, fontsize=8, rotation=30, ha='right')
    ax3.set_xlabel('Distance to nearest shade (m)', fontsize=10)
    ax3.set_ylabel('Mean score (%)', fontsize=10)
    ax3.set_title(f'Raw vs DCWP mean per\ndistance band (τ = {DCWP_TAU_M:.0f} m)', fontsize=11)
    ax3.set_ylim(0, 80)
    ax3.axhline(50, color='grey', lw=0.8, ls='--', alpha=0.4)
    ax3.legend(fontsize=9)
    ax3.grid(True, alpha=0.3)

    # Annotate the divergence direction
    ax3.text(0.55, 0.92,
             'DCWP > raw when sun-standing is near shade\n(sun preference discounted more)',
             transform=ax3.transAxes, fontsize=7.5, color='#333333',
             ha='center', bbox=dict(boxstyle='round,pad=0.3', facecolor='#f0f0f0', alpha=0.7))

    fig.suptitle(f'State College: DCWP diagnostics (τ = {DCWP_TAU_M:.0f} m)', fontsize=14, fontweight='bold')
    fig.tight_layout()
    out_path = out_dir / 'dtc_dcwp_diagnostics.png'
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  Saved: {out_path.name}')


# ── Tau sensitivity helpers ────────────────────────────────────────────────────

TAU_SENSITIVITY_VALUES = [3, 5, 10, 20, 40, 80, 200]


def _apply_tau(df_dtc, tau):
    """Return a copy of df_dtc with eff_shade/eff_sun recomputed for a given tau."""
    df = df_dtc.copy()
    a = np.exp(-df['dist_to_shade_m'] / tau)
    df['eff_sun']   = df['outshade_count'] * a
    df['eff_shade'] = df['inshade_count'].astype(float)
    df['eff_total'] = df['eff_shade'] + df['eff_sun']
    df['dcwp'] = np.where(
        df['eff_total'] > 0,
        df['eff_shade'] / df['eff_total'],
        np.nan
    )
    return df


# ── Plot 5: Tau sensitivity — all tau values on one figure ─────────────────────

def plot_tau_sensitivity(df_dtc, out_dir):
    """
    Single figure showing DCWP GLM curves for every tau in TAU_SENSITIVITY_VALUES,
    plus the raw (unweighted) curve, all vs UTCI.

    Layout: one panel per road-type group (Overall / Walkable / Non-walkable),
    arranged in a 1×3 row so the effect of tau can be read across each group.
    """
    print(f'\n[5/5] Tau sensitivity plot ({TAU_SENSITIVITY_VALUES}) ...')

    x_col = 'utci_C'
    groups = [
        ('Overall',      lambda d: d,                                        '-'),
        ('Walkable',     lambda d: d[d['walkability'] == 'Walkable'],        '--'),
        ('Non-walkable', lambda d: d[d['walkability'] == 'Non-walkable'],    ':'),
    ]

    # Colormap: small tau = cool blue (aggressive), large tau = warm red (mild)
    cmap = plt.cm.RdYlBu_r
    tau_colors = {tau: cmap(i / (len(TAU_SENSITIVITY_VALUES) - 1))
                  for i, tau in enumerate(TAU_SENSITIVITY_VALUES)}

    fig, axes = plt.subplots(1, 3, figsize=(18, 6), sharey=True)

    for ax, (group_name, group_fn, ls) in zip(axes, groups):
        # Raw curve (same on every panel)
        sub_raw = group_fn(df_dtc).dropna(subset=[x_col])
        if len(sub_raw) >= MIN_OBS:
            result = fit_glm_raw(sub_raw, x_col, degree=2)
            if result is not None:
                x_r, p_h, _ = result
                ax.plot(x_r, p_h * 100, color=RAW_COLOR, lw=2.5, ls=ls,
                        label=f'Raw (unweighted)  n={len(sub_raw):,}', zorder=10)

        # DCWP curves for each tau
        for tau in TAU_SENSITIVITY_VALUES:
            df_tau = _apply_tau(df_dtc, tau)
            sub    = group_fn(df_tau).dropna(subset=[x_col])
            if len(sub) < MIN_OBS:
                continue
            result = fit_glm_dcwp(sub, x_col, degree=2)
            if result is None:
                continue
            x_r, p_h, _ = result
            dcwp_mean = sub['dcwp'].mean() * 100
            ax.plot(x_r, p_h * 100,
                    color=tau_colors[tau], lw=1.8, ls=ls, alpha=0.85,
                    label=f'τ = {tau} m  (mean DCWP = {dcwp_mean:.1f}%)')

        ax.set_xlabel('UTCI (°C)', fontsize=11)
        ax.set_ylabel('Shade preference (%)' if ax is axes[0] else '', fontsize=11)
        ax.set_title(f'{group_name}', fontsize=12)
        ax.set_ylim(0, 100)
        ax.axhline(50, color='grey', lw=0.8, ls='--', alpha=0.4)
        ax.legend(fontsize=7.5, loc='upper left')
        ax.grid(True, alpha=0.3)

    # Colourbar showing tau scale
    sm = plt.cm.ScalarMappable(cmap=cmap,
                               norm=plt.Normalize(vmin=0, vmax=len(TAU_SENSITIVITY_VALUES) - 1))
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=axes, orientation='vertical', fraction=0.012, pad=0.01)
    cbar.set_ticks(range(len(TAU_SENSITIVITY_VALUES)))
    cbar.set_ticklabels([f'{t} m' for t in TAU_SENSITIVITY_VALUES], fontsize=8)
    cbar.set_label('τ (decay constant)\nsmall = aggressive discount', fontsize=9)

    fig.suptitle('State College: DCWP shade preference vs UTCI — tau sensitivity\n'
                 'a(d) = exp(−d / τ)  ·  larger τ → milder discounting → approaches raw',
                 fontsize=13, fontweight='bold')
    fig.tight_layout()
    out_path = out_dir / 'dtc_tau_sensitivity.png'
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  Saved: {out_path.name}')


# ── Main ────────────────────────────────────────────────────────────────────────

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f'Loading: {INPUT_PATH.name}')
    df = pd.read_csv(INPUT_PATH, low_memory=False)
    print(f'  Rows: {len(df):,}')

    df_voted, df_dtc = prepare_data(df)

    plot_dist_diagnostics(df_voted, df_dtc, OUTPUT_DIR)
    plot_detour_tolerance_curve(df_dtc, OUTPUT_DIR)
    plot_utci_comparison(df_dtc, OUTPUT_DIR)
    plot_dcwp_diagnostics(df_dtc, OUTPUT_DIR)
    plot_tau_sensitivity(df_dtc, OUTPUT_DIR)

    print('\nAll done.')


if __name__ == '__main__':
    main()
