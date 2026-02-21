# ABOUTME: Combined IPW + DCWP shade preference analysis for State College SVI
# ABOUTME: Produces shade preference vs UTCI plots varying SR threshold and tau

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import statsmodels.api as sm

INPUT_PATH = Path(__file__).parent.parent.parent.parent / 'data' / 'state-college' / 'state-college_svi_with_shadow.csv'
OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / 'outputs' / 'plots' / 'state_college' / 'dtc'

# Parameter grids
SR_THRESHOLDS = [0.05, 0.10, 0.20, 0.30]
TAU_VALUES    = [5, 10, 20, 40, 80]

IPW_WINSOR_QUANTILE = 0.95
MIN_OBS = 15

RAW_COLOR      = '#7f8c8d'
COMBINED_COLOR = '#8e44ad'   # purple to distinguish from IPW-only (red) and DCWP-only (blue)
IPW_COLOR      = '#e74c3c'
DCWP_COLOR     = '#2c7bb6'

WALKABLE_TYPES = {
    'footway', 'path', 'pedestrian', 'living_street',
    'residential', 'unclassified', 'tertiary', 'tertiary_link',
    'service', 'track',
}
NON_WALKABLE_TYPES = {
    'primary', 'primary_link', 'secondary', 'secondary_link',
    'cycleway', 'steps', 'motorway', 'motorway_link',
}


# ── Data loading ────────────────────────────────────────────────────────────────

def load_base(df):
    """
    Filter to voted sunny rows with valid shadow_ratio and dist_to_shade_m.
    Returns a clean base dataframe with walkability label.
    """
    df = df.copy()
    df['total_people'] = df['inshade_count'].fillna(0) + df['outshade_count'].fillna(0)
    mask = (
        (df['is_sunny'].astype(str).str.lower() == 'true') &
        df['inshade_count'].notna() &
        df['outshade_count'].notna() &
        (df['total_people'] >= 1) &
        df['shadow_ratio'].notna() &
        df['dist_to_shade_m'].notna()   # exclude sun-below-horizon rows
    )
    base = df[mask].copy()
    base['shade_pref'] = base['inshade_count'] / base['total_people']
    base['walkability'] = base['highway'].apply(
        lambda h: 'Walkable'     if h in WALKABLE_TYPES     else
                  'Non-walkable' if h in NON_WALKABLE_TYPES else 'Other'
    )
    return base


def apply_params(base, sr_min, tau):
    """
    Apply SR filter, compute DCWP effective counts, and compute IPW weights.
    Returns a ready-to-fit dataframe with columns:
      eff_shade, eff_sun, eff_total, ipw, shade_pref
    """
    df = base[base['shadow_ratio'] >= sr_min].copy()

    # DCWP effective counts
    a = np.exp(-df['dist_to_shade_m'] / tau)
    df['eff_shade'] = df['inshade_count'].astype(float)
    df['eff_sun']   = df['outshade_count'] * a
    df['eff_total'] = df['eff_shade'] + df['eff_sun']

    # IPW weights (winsorised on this SR-filtered subset)
    raw_w = 1.0 / df['shadow_ratio']
    cap   = raw_w.quantile(IPW_WINSOR_QUANTILE)
    df['ipw'] = raw_w.clip(upper=cap)

    return df


# ── GLM helpers ────────────────────────────────────────────────────────────────

def _fit(y, x_vals, weights=None, degree=2, n_points=200):
    """
    Core GLM fitter. y must be (n, 2) array of [successes, failures].
    Returns (x_range, p_hat) or None on failure.
    """
    polys = [x_vals ** i for i in range(1, degree + 1)]
    X = sm.add_constant(np.column_stack(polys))
    try:
        kw = {'freq_weights': weights} if weights is not None else {}
        model = sm.GLM(y, X, family=sm.families.Binomial()).fit(disp=0, **kw)
    except Exception:
        return None
    x_range = np.linspace(x_vals.min(), x_vals.max(), n_points)
    polys_p = [x_range ** i for i in range(1, degree + 1)]
    X_p = sm.add_constant(np.column_stack(polys_p), has_constant='add')
    return x_range, model.predict(X_p)


def fit_raw(df, x_col):
    """Raw GLM: unweighted inshade/outshade counts."""
    sub = df.dropna(subset=[x_col])
    if len(sub) < MIN_OBS:
        return None
    x = sub[x_col].values
    y = np.column_stack([sub['inshade_count'].values.astype(float),
                         sub['outshade_count'].values.astype(float)])
    return _fit(y, x)


def fit_ipw(df, x_col):
    """IPW-only GLM: raw counts weighted by IPW."""
    sub = df.dropna(subset=[x_col])
    if len(sub) < MIN_OBS:
        return None
    x = sub[x_col].values
    y = np.column_stack([sub['inshade_count'].values.astype(float),
                         sub['outshade_count'].values.astype(float)])
    return _fit(y, x, weights=sub['ipw'].values)


def fit_dcwp(df, x_col):
    """DCWP-only GLM: effective counts, unweighted."""
    sub = df.dropna(subset=[x_col])
    sub = sub[sub['eff_total'] > 0]
    if len(sub) < MIN_OBS:
        return None
    x = sub[x_col].values
    y = np.column_stack([sub['eff_shade'].values, sub['eff_sun'].values])
    return _fit(y, x)


def fit_combined(df, x_col):
    """Combined IPW+DCWP GLM: effective counts weighted by IPW."""
    sub = df.dropna(subset=[x_col])
    sub = sub[sub['eff_total'] > 0]
    if len(sub) < MIN_OBS:
        return None
    x = sub[x_col].values
    y = np.column_stack([sub['eff_shade'].values, sub['eff_sun'].values])
    return _fit(y, x, weights=sub['ipw'].values)


# ── Aggregate summary ──────────────────────────────────────────────────────────

def aggregate_prefs(df):
    """
    Return dict of aggregate shade preference for each estimator.
    """
    k  = df['inshade_count'].sum()
    n  = df['total_people'].sum()
    ek = df['eff_shade'].sum()
    en = df['eff_total'].sum()
    w  = df['ipw'].values

    raw      = k / n if n > 0 else np.nan
    ipw_p    = np.average(df['inshade_count'] / df['total_people'], weights=w)
    dcwp_p   = ek / en if en > 0 else np.nan
    comb_p   = (w * df['eff_shade'].values).sum() / (w * df['eff_total'].values).sum()
    return {'raw': raw, 'ipw': ipw_p, 'dcwp': dcwp_p, 'combined': comb_p, 'n': len(df)}


# ── Plot 1: Grid — SR threshold (rows) × tau (columns) ─────────────────────────

def plot_grid(base, out_dir):
    """
    Grid of shade preference vs UTCI plots.
    Rows = SR threshold values; columns = tau values.
    Each panel shows four curves: Raw, IPW-only, DCWP-only, Combined.
    """
    print('\n[1/2] SR × tau grid plot ...')
    n_rows = len(SR_THRESHOLDS)
    n_cols = len(TAU_VALUES)
    fig, axes = plt.subplots(n_rows, n_cols,
                             figsize=(4.2 * n_cols, 3.8 * n_rows),
                             sharey=True, sharex=True)

    x_col = 'utci_C'

    for ri, sr_min in enumerate(SR_THRESHOLDS):
        for ci, tau in enumerate(TAU_VALUES):
            ax = axes[ri, ci]
            df = apply_params(base, sr_min, tau)

            agg = aggregate_prefs(df)

            curves = [
                ('Raw',      fit_raw(df, x_col),      RAW_COLOR,      '-',  1.6),
                ('IPW',      fit_ipw(df, x_col),       IPW_COLOR,      '--', 1.6),
                ('DCWP',     fit_dcwp(df, x_col),      DCWP_COLOR,     ':',  1.6),
                ('Combined', fit_combined(df, x_col),  COMBINED_COLOR, '-',  2.0),
            ]

            handles = []
            for name, result, color, ls, lw in curves:
                if result is None:
                    continue
                x_r, p_h = result
                line, = ax.plot(x_r, p_h * 100, color=color, ls=ls, lw=lw,
                                label=name, alpha=0.9)
                handles.append(line)

            # Aggregate preference annotations
            ax.text(0.03, 0.97,
                    f"Raw   {agg['raw']*100:.1f}%\n"
                    f"IPW   {agg['ipw']*100:.1f}%\n"
                    f"DCWP  {agg['dcwp']*100:.1f}%\n"
                    f"Comb  {agg['combined']*100:.1f}%\n"
                    f"n={agg['n']:,}",
                    transform=ax.transAxes, fontsize=6.5, va='top', ha='left',
                    family='monospace',
                    bbox=dict(boxstyle='round,pad=0.25', facecolor='white',
                              alpha=0.85, edgecolor='#cccccc'))

            ax.axhline(50, color='grey', lw=0.6, ls='--', alpha=0.4)
            ax.set_ylim(0, 100)
            ax.grid(True, alpha=0.25)

            # Row / column labels on edges only
            if ri == 0:
                ax.set_title(f'τ = {tau} m', fontsize=10, fontweight='bold')
            if ci == 0:
                ax.set_ylabel(f'SR ≥ {sr_min}\nShade pref (%)', fontsize=8.5)
            if ri == n_rows - 1:
                ax.set_xlabel('UTCI (°C)', fontsize=9)

            # Legend only on top-left panel
            if ri == 0 and ci == 0:
                ax.legend(handles=handles, fontsize=7.5, loc='upper left')

    fig.suptitle(
        'State College: Shade preference vs UTCI\n'
        'rows = SR filter threshold · columns = DCWP tau · curves = estimator',
        fontsize=13, fontweight='bold'
    )
    fig.tight_layout()
    out_path = out_dir / 'combined_ipw_dcwp_grid.png'
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  Saved: {out_path.name}')


# ── Plot 2: Aggregate preference table — heatmaps ──────────────────────────────

def plot_aggregate_heatmaps(base, out_dir):
    """
    Four heatmaps (one per estimator) showing aggregate shade preference
    as a function of SR threshold (rows) and tau (columns).
    Makes the superadditivity and its magnitude immediately visible.
    """
    print('\n[2/2] Aggregate preference heatmaps ...')

    estimators = ['raw', 'ipw', 'dcwp', 'combined']
    labels     = ['Raw', 'IPW only', 'DCWP only', 'Combined IPW+DCWP']
    colors_map = ['Greys', 'Reds', 'Blues', 'Purples']

    # Build results table: rows=SR, cols=tau
    table = {e: np.full((len(SR_THRESHOLDS), len(TAU_VALUES)), np.nan)
             for e in estimators}
    n_table = np.full((len(SR_THRESHOLDS), len(TAU_VALUES)), 0)

    for ri, sr_min in enumerate(SR_THRESHOLDS):
        for ci, tau in enumerate(TAU_VALUES):
            df  = apply_params(base, sr_min, tau)
            agg = aggregate_prefs(df)
            for e in estimators:
                table[e][ri, ci] = agg[e] * 100
            n_table[ri, ci] = agg['n']

    # Note: raw and IPW are independent of tau (tau only enters DCWP/combined)
    # but we compute them for every tau cell so the grid is complete.

    fig, axes = plt.subplots(1, 4, figsize=(18, 3.8))

    for ax, est, lbl, cmap_name in zip(axes, estimators, labels, colors_map):
        data = table[est]
        vmin = np.nanmin(data)
        vmax = np.nanmax(data)
        im = ax.imshow(data, aspect='auto', cmap=cmap_name,
                       vmin=max(vmin - 2, 0), vmax=min(vmax + 2, 100))
        plt.colorbar(im, ax=ax, label='Shade pref (%)')

        # Annotate cells
        for ri in range(len(SR_THRESHOLDS)):
            for ci in range(len(TAU_VALUES)):
                v = data[ri, ci]
                n = n_table[ri, ci]
                txt_color = 'white' if v > (vmin + vmax) / 2 + 5 else '#222222'
                ax.text(ci, ri, f'{v:.1f}%\nn={n:,}',
                        ha='center', va='center', fontsize=7,
                        color=txt_color, family='monospace')

        ax.set_xticks(range(len(TAU_VALUES)))
        ax.set_xticklabels([f'τ={t}' for t in TAU_VALUES], fontsize=8)
        ax.set_yticks(range(len(SR_THRESHOLDS)))
        ax.set_yticklabels([f'SR≥{s}' for s in SR_THRESHOLDS], fontsize=8)
        ax.set_xlabel('tau (m)', fontsize=9)
        ax.set_ylabel('SR filter', fontsize=9)
        ax.set_title(lbl, fontsize=11, fontweight='bold')

    # Add a fifth "combined minus raw" delta heatmap
    fig2, ax_delta = plt.subplots(1, 1, figsize=(5.5, 3.8))
    delta = table['combined'] - table['raw']
    vabs  = np.nanmax(np.abs(delta))
    im2 = ax_delta.imshow(delta, aspect='auto', cmap='RdBu_r',
                          vmin=-vabs, vmax=vabs)
    plt.colorbar(im2, ax=ax_delta, label='Combined − Raw (pp)')

    for ri in range(len(SR_THRESHOLDS)):
        for ci in range(len(TAU_VALUES)):
            v = delta[ri, ci]
            ax_delta.text(ci, ri, f'{v:+.1f}pp',
                          ha='center', va='center', fontsize=8,
                          color='white' if abs(v) > vabs * 0.5 else '#222222',
                          family='monospace')
    ax_delta.set_xticks(range(len(TAU_VALUES)))
    ax_delta.set_xticklabels([f'τ={t}' for t in TAU_VALUES], fontsize=8)
    ax_delta.set_yticks(range(len(SR_THRESHOLDS)))
    ax_delta.set_yticklabels([f'SR≥{s}' for s in SR_THRESHOLDS], fontsize=8)
    ax_delta.set_xlabel('tau (m)', fontsize=9)
    ax_delta.set_ylabel('SR filter', fontsize=9)
    ax_delta.set_title('Combined − Raw\n(percentage-point shift)', fontsize=11, fontweight='bold')
    fig2.tight_layout()
    out_path2 = out_dir / 'combined_ipw_dcwp_delta.png'
    fig2.savefig(out_path2, dpi=150, bbox_inches='tight')
    plt.close(fig2)
    print(f'  Saved: {out_path2.name}')

    fig.suptitle(
        'State College: Aggregate shade preference by estimator, SR threshold, and tau',
        fontsize=12, fontweight='bold'
    )
    fig.tight_layout()
    out_path = out_dir / 'combined_ipw_dcwp_heatmaps.png'
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  Saved: {out_path.name}')


# ── Plot 3: Tau sensitivity at fixed SR — Overall / Walkable / Non-walkable ─────

TAU_SENSITIVITY_VALUES = [5, 10, 20, 40, 80]
SR_FIXED = 0.10


def plot_tau_sensitivity_combined(base, out_dir, sr_fixed=SR_FIXED):
    """
    Three-panel plot (Overall / Walkable / Non-walkable) at a fixed SR threshold.
    Each panel shows:
      - Raw curve (grey, thick)                     — reference, no adjustment
      - IPW-only curve (red, dashed)                — reference, supply-only adjustment
      - Combined IPW+DCWP for each tau (colourmap)  — supply + access-cost adjustment
    Matches the layout of dtc_tau_sensitivity.png.
    """
    print(f'\n[3/3] Tau sensitivity (combined IPW+DCWP, SR ≥ {sr_fixed}) ...')

    x_col = 'utci_C'
    groups = [
        ('Overall',      lambda d: d),
        ('Walkable',     lambda d: d[d['walkability'] == 'Walkable']),
        ('Non-walkable', lambda d: d[d['walkability'] == 'Non-walkable']),
    ]

    cmap = plt.cm.RdYlBu_r
    tau_colors = {tau: cmap(i / (len(TAU_SENSITIVITY_VALUES) - 1))
                  for i, tau in enumerate(TAU_SENSITIVITY_VALUES)}

    fig, axes = plt.subplots(1, 3, figsize=(18, 6), sharey=True)

    for ax, (group_name, group_fn) in zip(axes, groups):
        # Use tau=20 dataset for raw/IPW curves (tau doesn't affect those)
        df_ref = apply_params(base, sr_fixed, tau=20)
        sub_ref = group_fn(df_ref).dropna(subset=[x_col])

        # Raw reference
        result_raw = fit_raw(sub_ref, x_col)
        if result_raw is not None:
            x_r, p_h = result_raw
            ax.plot(x_r, p_h * 100, color=RAW_COLOR, lw=2.5, ls='-',
                    label=f'Raw  (n={len(sub_ref):,})', zorder=10)

        # IPW-only reference
        result_ipw = fit_ipw(sub_ref, x_col)
        if result_ipw is not None:
            x_r, p_h = result_ipw
            ax.plot(x_r, p_h * 100, color=IPW_COLOR, lw=2.0, ls='--',
                    label='IPW only', zorder=9)

        # Combined IPW+DCWP for each tau
        for tau in TAU_SENSITIVITY_VALUES:
            df_tau = apply_params(base, sr_fixed, tau)
            sub    = group_fn(df_tau).dropna(subset=[x_col])
            if len(sub) < MIN_OBS:
                continue
            result = fit_combined(sub, x_col)
            if result is None:
                continue
            x_r, p_h = result
            agg_comb = (sub['ipw'] * sub['eff_shade']).sum() / (sub['ipw'] * sub['eff_total']).sum()
            ax.plot(x_r, p_h * 100,
                    color=tau_colors[tau], lw=1.8, ls='-', alpha=0.85,
                    label=f'τ = {tau} m  (agg = {agg_comb*100:.1f}%)')

        ax.set_xlabel('UTCI (°C)', fontsize=11)
        ax.set_ylabel('Shade preference (%)' if ax is axes[0] else '', fontsize=11)
        ax.set_title(group_name, fontsize=12, fontweight='bold')
        ax.set_ylim(0, 100)
        ax.axhline(50, color='grey', lw=0.8, ls='--', alpha=0.4)
        ax.legend(fontsize=8, loc='upper left')
        ax.grid(True, alpha=0.3)

    # Colourbar for tau scale
    sm_obj = plt.cm.ScalarMappable(cmap=cmap,
                                   norm=plt.Normalize(vmin=0, vmax=len(TAU_SENSITIVITY_VALUES) - 1))
    sm_obj.set_array([])
    cbar = fig.colorbar(sm_obj, ax=axes, orientation='vertical',
                        fraction=0.012, pad=0.01)
    cbar.set_ticks(range(len(TAU_SENSITIVITY_VALUES)))
    cbar.set_ticklabels([f'{t} m' for t in TAU_SENSITIVITY_VALUES], fontsize=9)
    cbar.set_label('τ (DCWP decay constant)\nsmall = aggressive discount', fontsize=9)

    fig.suptitle(
        f'State College: Combined IPW+DCWP shade preference vs UTCI — tau sensitivity\n'
        f'SR ≥ {sr_fixed}  ·  a(d) = exp(−d / τ)  ·  larger τ → milder discounting → approaches IPW',
        fontsize=13, fontweight='bold'
    )
    fig.tight_layout()
    out_path = out_dir / f'combined_tau_sensitivity_sr{int(sr_fixed*100):02d}.png'
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  Saved: {out_path.name}')


# ── Main ────────────────────────────────────────────────────────────────────────

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f'Loading: {INPUT_PATH.name}')
    df = pd.read_csv(INPUT_PATH, low_memory=False)
    print(f'  Rows: {len(df):,}')

    base = load_base(df)
    print(f'  Voted rows with valid SR and dist: {len(base):,}')

    # Print summary table to stdout
    print('\n── Aggregate preference table ──────────────────────────────────────')
    print(f'{"SR":>6}  {"tau":>5}  {"n":>6}  {"Raw":>7}  {"IPW":>7}  {"DCWP":>7}  {"Comb":>7}  {"Δ(Comb-Raw)":>12}')
    print('─' * 72)
    for sr_min in SR_THRESHOLDS:
        for tau in TAU_VALUES:
            d   = apply_params(base, sr_min, tau)
            agg = aggregate_prefs(d)
            delta = (agg['combined'] - agg['raw']) * 100
            print(f'{sr_min:>6.2f}  {tau:>5}  {agg["n"]:>6,}  '
                  f'{agg["raw"]*100:>6.2f}%  {agg["ipw"]*100:>6.2f}%  '
                  f'{agg["dcwp"]*100:>6.2f}%  {agg["combined"]*100:>6.2f}%  '
                  f'{delta:>+10.2f}pp')
        print()

    plot_grid(base, OUTPUT_DIR)
    plot_aggregate_heatmaps(base, OUTPUT_DIR)
    plot_tau_sensitivity_combined(base, OUTPUT_DIR)

    print('\nAll done.')


if __name__ == '__main__':
    main()
