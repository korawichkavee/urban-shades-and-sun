# ABOUTME: Investigates shade preference in filtered vs kept shadow_ratio bands
# ABOUTME: Shows that SR=0 images still contain signal (people in shade exist)
# ABOUTME: but the signal is uninformative for IPW because choice was constrained

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
from scipy import stats

INPUT_PATH = Path(__file__).parent.parent.parent.parent / 'data' / 'state-college' / 'state-college_svi_with_shadow.csv'
OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / 'outputs' / 'plots' / 'state_college' / 'ipw'

SR_MIN = 0.05

# Shadow ratio bands: (lo, hi, label, filtered?)
BANDS = [
    (-0.001, 0.000, 'SR = 0\n(no shadow)', True),
    (0.000,  0.050, '0 < SR < 0.05\n(near-zero)', True),
    (0.050,  0.100, '0.05–0.10', False),
    (0.100,  0.250, '0.10–0.25', False),
    (0.250,  0.500, '0.25–0.50', False),
    (0.500,  0.750, '0.50–0.75', False),
    (0.750,  1.001, '0.75–1.0', False),
]

FILT_COLOR = '#c0392b'   # red — filtered
KEEP_COLOR = '#2980b9'   # blue — kept
FILT_ALPHA = 0.75
KEEP_ALPHA = 0.82


def prepare_data():
    df = pd.read_csv(INPUT_PATH, low_memory=False)
    df['total_people'] = df['inshade_count'].fillna(0) + df['outshade_count'].fillna(0)
    mask = (
        (df['is_sunny'].astype(str).str.lower() == 'true') &
        df['inshade_count'].notna() &
        df['outshade_count'].notna() &
        (df['total_people'] >= 1) &
        df['shadow_ratio'].notna()
    )
    df = df[mask].copy()
    df['shade_pref'] = df['inshade_count'] / df['total_people']
    df['filtered'] = df['shadow_ratio'] < SR_MIN

    # Assign band
    def assign_band(sr):
        for lo, hi, label, filt in BANDS:
            if lo < sr <= hi:
                return label
        return None
    df['band'] = df['shadow_ratio'].apply(assign_band)

    return df


def band_stats(df):
    rows = []
    for lo, hi, label, filtered in BANDS:
        sub = df[(df['shadow_ratio'] > lo) & (df['shadow_ratio'] <= hi)].copy()
        n = len(sub)
        if n == 0:
            continue
        sp = sub['shade_pref']
        any_shade  = (sp > 0).mean() * 100
        all_shade  = (sp == 1).mean() * 100
        none_shade = (sp == 0).mean() * 100
        mean_pref  = sp.mean() * 100
        se         = sp.sem() * 100
        ci95       = se * 1.96

        # 95% CI on 'any_shade' proportion (Wilson interval approx via normal)
        p_any = any_shade / 100
        se_any = np.sqrt(p_any * (1 - p_any) / n) * 100

        rows.append({
            'label':      label,
            'filtered':   filtered,
            'n':          n,
            'mean_pref':  mean_pref,
            'se':         se,
            'ci95':       ci95,
            'any_shade':  any_shade,
            'se_any':     se_any,
            'all_shade':  all_shade,
            'none_shade': none_shade,
            'sr_mid':     (lo + min(hi, 1.0)) / 2 if lo >= 0 else 0.0,
            'data':       sp.values,
        })
    return rows


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = prepare_data()
    stats_rows = band_stats(df)

    n_bands  = len(stats_rows)
    labels   = [r['label'] for r in stats_rows]
    filtered = [r['filtered'] for r in stats_rows]
    colors   = [FILT_COLOR if f else KEEP_COLOR for f in filtered]
    alphas   = [FILT_ALPHA if f else KEEP_ALPHA for f in filtered]
    x        = np.arange(n_bands)

    # ── Filter boundary x position (between band 1 and 2)
    filt_boundary = 1.5  # between index 1 (last filtered) and 2 (first kept)

    fig, axes = plt.subplots(2, 2, figsize=(15, 11))
    fig.subplots_adjust(hspace=0.38, wspace=0.32)

    # ── Panel A: Mean shade preference ± 95% CI ───────────────────────────────
    ax = axes[0, 0]
    means = [r['mean_pref'] for r in stats_rows]
    ci95s = [r['ci95']      for r in stats_rows]
    ns    = [r['n']         for r in stats_rows]

    for i, (m, ci, c, a) in enumerate(zip(means, ci95s, colors, alphas)):
        ax.bar(x[i], m, color=c, alpha=a, width=0.65, zorder=3)
        ax.errorbar(x[i], m, yerr=ci, fmt='none',
                    ecolor='#333333', capsize=4, lw=1.3, zorder=4)
        ax.text(x[i], m + ci + 0.5, f'n={ns[i]:,}',
                ha='center', va='bottom', fontsize=7, color='#555555')

    ax.axvline(filt_boundary, color='black', lw=1.5, ls='--', alpha=0.6, zorder=5)
    ax.text(filt_boundary - 0.05, ax.get_ylim()[1] if ax.get_ylim()[1] > 0 else 42,
            'IPW filter\nthreshold', ha='right', va='top', fontsize=8,
            color='black', alpha=0.7)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel('Mean shade preference (%)', fontsize=10)
    ax.set_title('A  Mean shade preference by shadow ratio band\n(± 95% CI)', fontsize=11)
    ax.set_ylim(0, 55)
    ax.axhline(df['shade_pref'].mean() * 100, color='#7f8c8d',
               lw=1, ls=':', alpha=0.6, label=f'Overall mean ({df["shade_pref"].mean()*100:.1f}%)')
    ax.legend(fontsize=8)
    ax.grid(True, axis='y', alpha=0.3)

    filt_patch = mpatches.Patch(color=FILT_COLOR, alpha=FILT_ALPHA, label='Filtered (SR < 0.05)')
    keep_patch = mpatches.Patch(color=KEEP_COLOR, alpha=KEEP_ALPHA, label='Kept (SR ≥ 0.05)')
    ax.legend(handles=[filt_patch, keep_patch], fontsize=8, loc='upper left')

    # ── Panel B: Proportion breakdown (none / partial / all in shade) ─────────
    ax2 = axes[0, 1]
    none_vals    = [r['none_shade'] for r in stats_rows]
    partial_vals = [r['any_shade'] - r['all_shade'] for r in stats_rows]   # any but not all
    all_vals     = [r['all_shade'] for r in stats_rows]

    bar_none    = ax2.bar(x, none_vals,    color='#ecf0f1', edgecolor='#bdc3c7', width=0.65,
                          label='All in sun (shade_pref = 0)', zorder=3)
    bar_partial = ax2.bar(x, partial_vals, bottom=none_vals,
                          color=[c for c in colors], alpha=0.5, width=0.65,
                          label='Mixed (0 < shade_pref < 1)', zorder=3)
    bar_all     = ax2.bar(x, all_vals,
                          bottom=[n + p for n, p in zip(none_vals, partial_vals)],
                          color=[c for c in colors], alpha=0.95, width=0.65,
                          label='All in shade (shade_pref = 1)', zorder=3)

    ax2.axvline(filt_boundary, color='black', lw=1.5, ls='--', alpha=0.6, zorder=5)
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, fontsize=8)
    ax2.set_ylabel('% of images', fontsize=10)
    ax2.set_title('B  Shade outcome composition by shadow ratio band', fontsize=11)
    ax2.set_ylim(0, 105)
    ax2.axhline(100, color='#aaaaaa', lw=0.8)
    ax2.grid(True, axis='y', alpha=0.3)

    none_p    = mpatches.Patch(color='#ecf0f1', edgecolor='#bdc3c7', label='All in sun (pref = 0)')
    partial_p = mpatches.Patch(color='#95a5a6', alpha=0.7, label='Mixed (0 < pref < 1)')
    all_p     = mpatches.Patch(color='#2c3e50', alpha=0.9, label='All in shade (pref = 1)')
    ax2.legend(handles=[none_p, partial_p, all_p], fontsize=8, loc='upper right')

    # ── Panel C: Shade preference distributions (violin / strip) ─────────────
    ax3 = axes[1, 0]

    vdata = [r['data'] for r in stats_rows]
    parts = ax3.violinplot(vdata, positions=x, showmedians=True,
                           showextrema=False, widths=0.6)

    for i, (pc, c) in enumerate(zip(parts['bodies'], colors)):
        pc.set_facecolor(c)
        pc.set_alpha(0.55)
    parts['cmedians'].set_color('#2c3e50')
    parts['cmedians'].set_lw(2)

    # Overlay mean dots
    for i, (r, c) in enumerate(zip(stats_rows, colors)):
        ax3.scatter(x[i], r['mean_pref'] / 100, color=c, s=55,
                    zorder=5, edgecolors='white', lw=1.2)

    ax3.axvline(filt_boundary, color='black', lw=1.5, ls='--', alpha=0.6, zorder=5)
    ax3.set_xticks(x)
    ax3.set_xticklabels(labels, fontsize=8)
    ax3.set_ylabel('Shade preference (fraction)', fontsize=10)
    ax3.set_title('C  Shade preference distribution by band\n(violin; dot = mean, line = median)', fontsize=11)
    ax3.set_ylim(-0.05, 1.1)
    ax3.axhline(0.5, color='grey', lw=0.8, ls='--', alpha=0.4)
    ax3.grid(True, axis='y', alpha=0.3)
    ax3.legend(handles=[filt_patch, keep_patch], fontsize=8)

    # ── Panel D: Continuous scatter — shade_pref vs shadow_ratio ─────────────
    ax4 = axes[1, 1]

    # Separate filtered vs kept
    df_filt = df[df['filtered']].copy()
    df_kept = df[~df['filtered']].copy()

    # Jitter shadow_ratio for visibility
    rng = np.random.default_rng(42)
    jitter_scale = 0.008

    ax4.scatter(df_filt['shadow_ratio'] + rng.uniform(-jitter_scale, jitter_scale, len(df_filt)),
                df_filt['shade_pref']   + rng.uniform(-0.015, 0.015, len(df_filt)),
                color=FILT_COLOR, alpha=0.12, s=5, rasterized=True, label='Filtered (SR < 0.05)')
    ax4.scatter(df_kept['shadow_ratio'] + rng.uniform(-jitter_scale, jitter_scale, len(df_kept)),
                df_kept['shade_pref']   + rng.uniform(-0.015, 0.015, len(df_kept)),
                color=KEEP_COLOR, alpha=0.25, s=5, rasterized=True, label='Kept (SR ≥ 0.05)')

    # Rolling mean line (10-percentile window)
    df_sorted = df.sort_values('shadow_ratio')
    window = max(50, len(df_sorted) // 20)
    roll_mean = df_sorted['shade_pref'].rolling(window, center=True, min_periods=20).mean()
    ax4.plot(df_sorted['shadow_ratio'], roll_mean,
             color='#2c3e50', lw=2, zorder=5, label=f'Rolling mean (w={window})')

    # Band mean overlay
    for r, c in zip(stats_rows, colors):
        sr_mid = r['sr_mid']
        ax4.errorbar(sr_mid, r['mean_pref'] / 100, yerr=r['ci95'] / 100,
                     fmt='D', color=c, ms=7, capsize=4, lw=1.5,
                     zorder=6, markeredgecolor='white', markeredgewidth=0.8)

    ax4.axvline(SR_MIN, color='black', lw=1.5, ls='--', alpha=0.6,
                label=f'Filter threshold (SR = {SR_MIN})')
    ax4.set_xlabel('Shadow ratio', fontsize=10)
    ax4.set_ylabel('Shade preference (fraction)', fontsize=10)
    ax4.set_title('D  Shade preference vs shadow ratio (all voted images)\n'
                  '(points jittered; diamonds = band means ± 95% CI)', fontsize=11)
    ax4.set_xlim(-0.02, 1.02)
    ax4.set_ylim(-0.05, 1.1)
    ax4.axhline(0.5, color='grey', lw=0.8, ls='--', alpha=0.4)
    ax4.legend(fontsize=8, loc='upper left')
    ax4.grid(True, alpha=0.25)

    # ── Suptitle and filter annotation ───────────────────────────────────────
    n_filt = df['filtered'].sum()
    n_kept = (~df['filtered']).sum()
    n_tot  = len(df)
    fig.suptitle(
        f'State College: Shade preference in filtered vs retained images\n'
        f'(IPW filter SR < {SR_MIN} removes {n_filt:,}/{n_tot:,} voted images '
        f'[{n_filt/n_tot*100:.1f}%] — {n_kept:,} retained)',
        fontsize=13, fontweight='bold', y=1.01
    )

    out_path = OUTPUT_DIR / 'ipw_filter_shade_preference.png'
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved: {out_path}')

    # ── Print summary table ───────────────────────────────────────────────────
    print()
    print(f'{"Band":<26} {"n":>6}  {"mean%":>6}  {"any_shade%":>10}  {"all_shade%":>10}  {"none%":>6}')
    print('─' * 70)
    for r in stats_rows:
        tag = '[filtered]' if r['filtered'] else '[kept]    '
        print(f'  {r["label"].replace(chr(10), " "):<24} {r["n"]:>6,}  '
              f'{r["mean_pref"]:>6.1f}  {r["any_shade"]:>10.1f}  '
              f'{r["all_shade"]:>10.1f}  {r["none_shade"]:>6.1f}  {tag}')


if __name__ == '__main__':
    main()
