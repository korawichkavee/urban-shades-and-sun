# ABOUTME: Inverse probability weighting (IPW) shade preference analysis for State College
# ABOUTME: Implements Approach B from docs/ADJUSTED_SHADE_PREFERENCE.md
# ABOUTME: Produces comparison plots: raw vs IPW-weighted GLM curves for UTCI, road type, time-of-day

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import statsmodels.api as sm

INPUT_PATH = Path(__file__).parent.parent.parent.parent / 'data' / 'state-college' / 'state-college_svi_with_shadow.csv'
OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / 'outputs' / 'plots' / 'state_college' / 'ipw'

SR_MIN = 0.05          # shadow_ratio filter threshold (images below this are uninformative)
IPW_WINSOR_QUANTILE = 0.95  # winsorise IPW weights at this percentile
MIN_OBS = 15           # minimum obs per bin / group for GLM

# ── Colours ───────────────────────────────────────────────────────────────────
RAW_COLOR      = '#7f8c8d'
IPW_COLOR      = '#e74c3c'
WALKABLE_COLOR = '#2980b9'
NON_WALK_COLOR = '#c0392b'

WALKABLE_TYPES = {
    'footway', 'path', 'pedestrian', 'living_street',
    'residential', 'unclassified', 'tertiary', 'tertiary_link',
    'service', 'track',
}
NON_WALKABLE_TYPES = {
    'primary', 'primary_link', 'secondary', 'secondary_link',
    'cycleway', 'steps', 'motorway', 'motorway_link',
}

TYPE_LABELS = {
    'footway': 'Footway', 'path': 'Path', 'pedestrian': 'Pedestrian',
    'living_street': 'Living Street', 'residential': 'Residential',
    'unclassified': 'Unclassified', 'tertiary': 'Tertiary',
    'tertiary_link': 'Tertiary Link', 'service': 'Service', 'track': 'Track',
    'primary': 'Primary', 'primary_link': 'Primary Link',
    'secondary': 'Secondary', 'secondary_link': 'Secondary Link',
    'cycleway': 'Cycleway', 'steps': 'Steps',
}


# ── Data preparation ──────────────────────────────────────────────────────────

def prepare_data(df):
    """
    Filter to voted sunny rows, compute IPW weights, report filter stats.
    Returns (df_raw, df_ipw) where df_raw has all voted rows and df_ipw is
    filtered to shadow_ratio >= SR_MIN with trimmed IPW weights.
    """
    df = df.copy()
    df['total_people'] = df['inshade_count'].fillna(0) + df['outshade_count'].fillna(0)

    # Base filter: sunny, has votes, has shadow_ratio
    mask_voted = (
        (df['is_sunny'].astype(str).str.lower() == 'true') &
        df['inshade_count'].notna() &
        df['outshade_count'].notna() &
        (df['total_people'] >= 1) &
        df['shadow_ratio'].notna()
    )
    df_raw = df[mask_voted].copy()
    df_raw['shade_pref'] = df_raw['inshade_count'] / df_raw['total_people']

    # ── Filter report ─────────────────────────────────────────────────────────
    n_total  = len(df_raw)
    n_below  = (df_raw['shadow_ratio'] < SR_MIN).sum()
    n_kept   = (df_raw['shadow_ratio'] >= SR_MIN).sum()
    pct_filt = n_below / n_total * 100 if n_total else 0

    print('─' * 60)
    print(f'IPW shadow_ratio filter  (threshold = {SR_MIN})')
    print(f'  Voted rows total       : {n_total:,}')
    print(f'  Filtered out (SR<{SR_MIN}) : {n_below:,}  ({pct_filt:.1f}%)')
    print(f'  Kept for IPW analysis  : {n_kept:,}  ({100-pct_filt:.1f}%)')
    print()
    print('  shadow_ratio == 0.00   :', (df_raw['shadow_ratio'] == 0).sum())
    print('  shadow_ratio 0.00–0.05 :', ((df_raw['shadow_ratio'] > 0) & (df_raw['shadow_ratio'] < SR_MIN)).sum())
    print('─' * 60)

    # ── IPW subset ────────────────────────────────────────────────────────────
    df_ipw = df_raw[df_raw['shadow_ratio'] >= SR_MIN].copy()

    # Raw weight: 1 / shadow_ratio
    df_ipw['ipw_raw'] = 1.0 / df_ipw['shadow_ratio']

    # Winsorise at IPW_WINSOR_QUANTILE
    cap = df_ipw['ipw_raw'].quantile(IPW_WINSOR_QUANTILE)
    df_ipw['ipw'] = df_ipw['ipw_raw'].clip(upper=cap)
    print(f'IPW weight stats (after winsorising at p{IPW_WINSOR_QUANTILE*100:.0f}={cap:.2f}):')
    print(f'  min={df_ipw["ipw"].min():.2f}  median={df_ipw["ipw"].median():.2f}  '
          f'mean={df_ipw["ipw"].mean():.2f}  max={df_ipw["ipw"].max():.2f}')
    print('─' * 60)

    # Walkability label
    for ds in [df_raw, df_ipw]:
        ds['walkability'] = ds['highway'].apply(
            lambda h: 'Walkable' if h in WALKABLE_TYPES
                      else ('Non-walkable' if h in NON_WALKABLE_TYPES else 'Other')
        )

    return df_raw, df_ipw, {'n_total': n_total, 'n_below': n_below, 'n_kept': n_kept, 'pct_filt': pct_filt}


# ── GLM fitting ───────────────────────────────────────────────────────────────

def fit_glm(df_sub, x_col, weights=None, degree=2, n_points=200):
    """
    Fit binomial GLM: shade_pref ~ x + x^2.
    Optionally applies freq_weights for IPW.
    Returns (x_range, p_hat, model) or None.
    """
    x = df_sub[x_col].values
    k = df_sub['inshade_count'].values.astype(float)
    n = df_sub['total_people'].values.astype(float)
    y = np.column_stack([k, n - k])

    polys = [x ** i for i in range(1, degree + 1)]
    X = sm.add_constant(np.column_stack(polys))

    try:
        if weights is not None:
            w = df_sub[weights].values
            model = sm.GLM(y, X, family=sm.families.Binomial(),
                           freq_weights=w).fit(disp=0)
        else:
            model = sm.GLM(y, X, family=sm.families.Binomial()).fit(disp=0)
    except Exception as e:
        print(f'    GLM failed ({x_col}): {e}')
        return None

    x_range = np.linspace(x.min(), x.max(), n_points)
    polys_pred = [x_range ** i for i in range(1, degree + 1)]
    X_pred = sm.add_constant(np.column_stack(polys_pred), has_constant='add')
    p_hat = model.predict(X_pred)
    return x_range, p_hat, model


# ── Plot helpers ──────────────────────────────────────────────────────────────

def _filter_tag(n_below, pct_filt, n_kept):
    return (f'Shadow ratio filter: SR < {SR_MIN} removed {n_below:,} '
            f'({pct_filt:.1f}%) of voted images\n'
            f'{n_kept:,} images retained for IPW analysis')


def _draw_filter_note(fig, filt_stats):
    note = (f'Shadow ratio filter (SR \u2265 {SR_MIN}): '
            f'{filt_stats["n_below"]:,} / {filt_stats["n_total"]:,} '
            f'voted images removed ({filt_stats["pct_filt"]:.1f}%) — '
            f'{filt_stats["n_kept"]:,} retained')
    fig.text(0.5, -0.01, note, ha='center', va='top', fontsize=8,
             color='#555555', style='italic')


# ── Plot 1: Raw vs IPW GLM on UTCI ────────────────────────────────────────────

def plot_utci_comparison(df_raw, df_ipw, filt_stats, out_dir):
    """
    Two-panel: shade preference vs UTCI
      Left:  Raw (all voted rows, no IPW)
      Right: IPW-weighted (shadow_ratio >= SR_MIN only)
    Each panel: Overall + Walkable + Non-walkable GLM curves.
    """
    print('\n[1/4] UTCI comparison plot ...')
    x_col = 'utci_C'

    # Drop missing UTCI
    dr = df_raw.dropna(subset=[x_col]).copy()
    di = df_ipw.dropna(subset=[x_col]).copy()

    fig, axes = plt.subplots(1, 2, figsize=(15, 6), sharey=True)

    panel_configs = [
        ('Raw (unweighted)', dr, None,   RAW_COLOR),
        ('IPW-weighted (SR ≥ 0.05)', di, 'ipw', IPW_COLOR),
    ]

    for ax, (title_suffix, data, w_col, col_main) in zip(axes, panel_configs):
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
            result = fit_glm(sub, x_col, weights=w_col, degree=2)
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

    fig.suptitle('State College: Raw vs IPW-weighted shade preference (UTCI)',
                 fontsize=14, fontweight='bold')
    _draw_filter_note(fig, filt_stats)
    fig.tight_layout()
    out_path = out_dir / 'ipw_vs_raw_utci.png'
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  Saved: {out_path.name}')


# ── Plot 2: Raw vs IPW shade preference by road type ─────────────────────────

def plot_road_type_comparison(df_raw, df_ipw, filt_stats, out_dir):
    """
    Two-panel horizontal bar chart:
      Left:  Raw mean shade_pref per road type
      Right: IPW-weighted mean shade_pref per road type
    Both sorted by raw mean for direct comparison.
    """
    print('\n[2/4] Road type comparison plot ...')

    def type_color(h):
        if h in WALKABLE_TYPES:
            return WALKABLE_COLOR
        if h in NON_WALKABLE_TYPES:
            return NON_WALK_COLOR
        return '#7f8c8d'

    # Raw means
    type_counts = df_raw['highway'].value_counts()
    valid_types = type_counts[type_counts >= MIN_OBS].index.tolist()
    dr = df_raw[df_raw['highway'].isin(valid_types)].copy()

    raw_stats = (dr.groupby('highway')
                   .apply(lambda g: pd.Series({
                       'mean_pref': g['shade_pref'].mean() * 100,
                       'se':        g['shade_pref'].sem() * 100,
                       'n':         len(g),
                   }), include_groups=False)
                   .reset_index())
    raw_stats = raw_stats.sort_values('mean_pref', ascending=True)
    sorted_types = raw_stats['highway'].tolist()

    # IPW weighted means
    def ipw_weighted_mean(g):
        w = g['ipw'].values
        p = g['shade_pref'].values
        wm = np.average(p, weights=w) * 100
        # Weighted SE approximation
        n_eff = w.sum() ** 2 / (w ** 2).sum()
        wse = np.sqrt(np.average((p * 100 - wm) ** 2, weights=w) / max(n_eff - 1, 1))
        return pd.Series({'mean_pref': wm, 'se': wse, 'n': len(g)})

    di = df_ipw[df_ipw['highway'].isin(valid_types)].copy()
    if len(di) > 0:
        ipw_stats = di.groupby('highway').apply(ipw_weighted_mean, include_groups=False).reset_index()
    else:
        ipw_stats = pd.DataFrame(columns=['highway', 'mean_pref', 'se', 'n'])

    # Align to same type order
    raw_stats = raw_stats.set_index('highway')
    ipw_stats = ipw_stats.set_index('highway') if len(ipw_stats) else ipw_stats

    fig, axes = plt.subplots(1, 2, figsize=(16, max(5, len(sorted_types) * 0.55 + 1.5)),
                             sharey=True)

    y_pos = np.arange(len(sorted_types))

    for ax, (title, stats, color_base) in zip(axes, [
        ('Raw shade preference\n(all voted images)', raw_stats, RAW_COLOR),
        (f'IPW-weighted shade preference\n(SR ≥ {SR_MIN} only)', ipw_stats, IPW_COLOR),
    ]):
        means, ses, ns = [], [], []
        colors = []
        for ht in sorted_types:
            if ht in stats.index:
                means.append(stats.loc[ht, 'mean_pref'])
                ses.append(stats.loc[ht, 'se'])
                ns.append(int(stats.loc[ht, 'n']))
            else:
                means.append(np.nan)
                ses.append(0)
                ns.append(0)
            colors.append(type_color(ht))

        means = np.array(means, dtype=float)
        ses   = np.array(ses,   dtype=float)

        # Bars
        valid = ~np.isnan(means)
        ax.barh(y_pos[valid], means[valid], xerr=ses[valid] * 1.96,
                color=[colors[i] for i in np.where(valid)[0]],
                alpha=0.82, height=0.6,
                error_kw={'ecolor': '#333333', 'capsize': 3, 'lw': 1.1})
        if (~valid).any():
            for i in np.where(~valid)[0]:
                ax.text(1.0, y_pos[i], 'n/a (filtered)', va='center', fontsize=7,
                        color='#aaaaaa')

        # Annotate n
        for i, (m, s, n) in enumerate(zip(means, ses, ns)):
            if not np.isnan(m):
                ax.text(m + s * 1.96 + 0.5, y_pos[i], f'n={n:,}',
                        va='center', fontsize=7, color='#555555')

        ax.set_yticks(y_pos)
        ax.set_yticklabels(
            [TYPE_LABELS.get(ht, ht) for ht in sorted_types], fontsize=9
        )
        ax.set_xlabel('Shade preference (%)', fontsize=10)
        ax.set_title(title, fontsize=11)
        ax.set_xlim(-2, 120)
        ax.axvline(50, color='grey', lw=0.8, ls='--', alpha=0.5)
        ax.axvline(df_raw['shade_pref'].mean() * 100 if title.startswith('Raw') else
                   np.average(di['shade_pref'], weights=di['ipw']) * 100 if len(di) else np.nan,
                   color=color_base, lw=1.2, ls=':', alpha=0.7,
                   label='Overall mean')
        ax.legend(fontsize=8)
        ax.grid(True, axis='x', alpha=0.3)

        # Walkability legend
        wp = mpatches.Patch(color=WALKABLE_COLOR, alpha=0.8, label='Walkable')
        np_ = mpatches.Patch(color=NON_WALK_COLOR, alpha=0.8, label='Non-walkable')
        ax.legend(handles=[wp, np_], fontsize=8, loc='lower right')

    fig.suptitle('State College: Shade preference by road type — Raw vs IPW',
                 fontsize=14, fontweight='bold')
    _draw_filter_note(fig, filt_stats)
    fig.tight_layout()
    out_path = out_dir / 'ipw_vs_raw_road_type.png'
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  Saved: {out_path.name}')


# ── Plot 3: Raw vs IPW shade preference vs shadow_ratio ───────────────────────

def plot_shadow_ratio_comparison(df_raw, df_ipw, filt_stats, out_dir):
    """
    Two-panel: shade preference vs shadow_ratio
      Left:  Raw GLM (all voted rows including SR=0)
      Right: IPW-weighted GLM (SR >= SR_MIN)
    Shows how the relationship changes once we account for availability.
    """
    print('\n[3/4] Shadow ratio comparison plot ...')
    x_col = 'shadow_ratio'

    fig, axes = plt.subplots(1, 2, figsize=(15, 6), sharey=True)

    for ax, (title_suffix, data, w_col, col_main) in zip(axes, [
        ('Raw (unweighted, including SR=0)', df_raw, None,   RAW_COLOR),
        (f'IPW-weighted (SR ≥ {SR_MIN})',      df_ipw, 'ipw', IPW_COLOR),
    ]):
        groups = [
            ('Overall',      data,                                          col_main,      '-',  2.2),
            ('Walkable',     data[data['walkability'] == 'Walkable'],       WALKABLE_COLOR, '--', 1.6),
            ('Non-walkable', data[data['walkability'] == 'Non-walkable'],   NON_WALK_COLOR, ':',  1.6),
        ]
        handles = []
        for name, sub, color, ls, lw in groups:
            if len(sub) < MIN_OBS:
                continue
            result = fit_glm(sub, x_col, weights=w_col, degree=2)
            if result is None:
                continue
            x_r, p_h, _ = result
            line, = ax.plot(x_r, p_h * 100, color=color, ls=ls, lw=lw,
                            label=f'{name}  (n={len(sub):,})')
            handles.append(line)

        # Binned scatter (raw counts in each panel's data)
        n_bins = 8
        sub_bin = data.copy()
        try:
            sub_bin['sr_bin'] = pd.qcut(sub_bin[x_col], q=n_bins,
                                         duplicates='drop', labels=False)
            bs = sub_bin.groupby('sr_bin').agg(
                sr_mid=(x_col, 'mean'),
                pref_mean=('shade_pref', lambda x_: x_.mean() * 100),
                pref_se=('shade_pref', lambda x_: x_.sem() * 100),
                n=('shade_pref', 'count'),
            ).reset_index()
            ax.errorbar(bs['sr_mid'], bs['pref_mean'], yerr=bs['pref_se'] * 1.96,
                        fmt='o', color=col_main, ms=5, capsize=3, lw=1, alpha=0.5,
                        label='Binned mean ± 95% CI')
        except Exception:
            pass

        ax.set_xlabel('Shadow ratio', fontsize=11)
        ax.set_ylabel('Shade preference (%)' if ax is axes[0] else '', fontsize=11)
        ax.set_title(f'Shade preference vs shadow ratio\n{title_suffix}', fontsize=12)
        ax.set_ylim(0, 100)
        ax.set_xlim(-0.02, 1.02)
        ax.axhline(50, color='grey', lw=0.8, ls='--', alpha=0.5)
        ax.legend(handles=handles + [ax.get_lines()[-1]] if ax.get_lines() else handles,
                  fontsize=8)
        ax.grid(True, alpha=0.3)

    fig.suptitle('State College: Shade preference vs shadow ratio — Raw vs IPW',
                 fontsize=14, fontweight='bold')
    _draw_filter_note(fig, filt_stats)
    fig.tight_layout()
    out_path = out_dir / 'ipw_vs_raw_shadow_ratio.png'
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  Saved: {out_path.name}')


# ── Plot 4: IPW weight distribution diagnostic ────────────────────────────────

def plot_weight_diagnostics(df_ipw, filt_stats, out_dir):
    """
    Three-panel diagnostic:
      Left:   Histogram of raw IPW weights and winsorised weights
      Middle: IPW weight vs shadow_ratio (scatter)
      Right:  Effective sample size (n_eff) relative to n by shadow_ratio bin
    """
    print('\n[4/4] IPW weight diagnostics ...')

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    # ── Panel 1: weight histogram ─────────────────────────────────────────────
    ax = axes[0]
    raw_w = df_ipw['ipw_raw'].values
    trim_w = df_ipw['ipw'].values
    cap = df_ipw['ipw_raw'].quantile(IPW_WINSOR_QUANTILE)

    ax.hist(raw_w, bins=50, color=RAW_COLOR, alpha=0.6, label='Raw weights (1/SR)',
            density=True)
    ax.hist(trim_w, bins=50, color=IPW_COLOR, alpha=0.6, label=f'Winsorised (cap={cap:.2f})',
            density=True)
    ax.axvline(cap, color='black', lw=1.2, ls='--', alpha=0.7,
               label=f'Winsorise cap (p{IPW_WINSOR_QUANTILE*100:.0f})')
    ax.set_xlabel('IPW weight', fontsize=10)
    ax.set_ylabel('Density', fontsize=10)
    ax.set_title('IPW weight distribution\n(raw vs winsorised)', fontsize=11)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # ── Panel 2: weight vs shadow_ratio ───────────────────────────────────────
    ax2 = axes[1]
    sr = df_ipw['shadow_ratio'].values
    ax2.scatter(sr, trim_w, alpha=0.3, s=8, color=IPW_COLOR, rasterized=True)
    sr_curve = np.linspace(SR_MIN, 1.0, 300)
    cap_arr  = np.full_like(sr_curve, cap)
    ax2.plot(sr_curve, np.minimum(1.0 / sr_curve, cap_arr),
             color='black', lw=1.5, label=f'1/SR (capped at {cap:.2f})')
    ax2.axhline(cap, color='black', lw=1, ls='--', alpha=0.5)
    ax2.set_xlabel('Shadow ratio', fontsize=10)
    ax2.set_ylabel('IPW weight (winsorised)', fontsize=10)
    ax2.set_title('IPW weight vs shadow ratio\n(points = SVI images)', fontsize=11)
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(0, 1.05)

    # ── Panel 3: effective n per SR bin ───────────────────────────────────────
    ax3 = axes[2]
    n_bins = 8
    df_tmp = df_ipw.copy()
    try:
        df_tmp['sr_bin'] = pd.qcut(df_tmp['shadow_ratio'], q=n_bins,
                                    duplicates='drop', labels=False)
        bin_stats = df_tmp.groupby('sr_bin').apply(lambda g: pd.Series({
            'sr_mid': g['shadow_ratio'].mean(),
            'n':      len(g),
            'n_eff':  g['ipw'].sum() ** 2 / (g['ipw'] ** 2).sum(),
            'mean_w': g['ipw'].mean(),
        }), include_groups=False).reset_index()

        ax3.bar(bin_stats['sr_mid'], bin_stats['n'], width=0.07,
                color=RAW_COLOR, alpha=0.6, label='n (actual)')
        ax3.bar(bin_stats['sr_mid'], bin_stats['n_eff'], width=0.05,
                color=IPW_COLOR, alpha=0.8, label='n_eff (IPW-weighted)')
        ax3.set_xlabel('Shadow ratio (bin midpoint)', fontsize=10)
        ax3.set_ylabel('Count', fontsize=10)
        ax3.set_title('Actual n vs effective n per shadow ratio bin\n'
                      '(n_eff = weight-normalised sample size)', fontsize=11)
        ax3.legend(fontsize=8)
        ax3.grid(True, axis='y', alpha=0.3)
    except Exception as e:
        ax3.text(0.5, 0.5, f'Could not compute:\n{e}', ha='center', va='center',
                 transform=ax3.transAxes, fontsize=9)

    fig.suptitle('State College: IPW weight diagnostics', fontsize=14, fontweight='bold')
    _draw_filter_note(fig, filt_stats)
    fig.tight_layout()
    out_path = out_dir / 'ipw_weight_diagnostics.png'
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  Saved: {out_path.name}')


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f'Loading: {INPUT_PATH.name}')
    df = pd.read_csv(INPUT_PATH, low_memory=False)
    print(f'  Rows: {len(df):,}')

    df_raw, df_ipw, filt_stats = prepare_data(df)

    plot_utci_comparison(df_raw, df_ipw, filt_stats, OUTPUT_DIR)
    plot_road_type_comparison(df_raw, df_ipw, filt_stats, OUTPUT_DIR)
    plot_shadow_ratio_comparison(df_raw, df_ipw, filt_stats, OUTPUT_DIR)
    plot_weight_diagnostics(df_ipw, filt_stats, OUTPUT_DIR)

    print('\nAll done.')


if __name__ == '__main__':
    main()
