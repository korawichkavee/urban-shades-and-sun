# ABOUTME: UTCI vs shade ratio plots stratified by OSM highway classification
# ABOUTME: Shows individual highway types and walkable vs non-walkable aggregates
# ABOUTME: Uses binomial GLM with quadratic UTCI term, consistent with other shade plots

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import statsmodels.api as sm

INPUT_PATH = Path(__file__).parent.parent.parent.parent / 'data' / 'state-college' / 'state-college_svi_with_highway.csv'
OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / 'outputs' / 'plots' / 'state_college' / 'street_type'

MIN_OBS = 30  # minimum shade-filtered rows to attempt a GLM fit

# ── Walkability classification ────────────────────────────────────────────────
# Based on OSM highway values found in the State College dataset.
# Walkable  = pedestrian-accessible streets / paths at normal walking speeds.
# Non-walkable = high-speed motor roads, cycle-only infrastructure, or ambiguous.

WALKABLE_TYPES = {
    'footway',        # Dedicated foot paths
    'path',           # Mixed-use paths (usually walkable)
    'pedestrian',     # Pedestrianised streets / plazas
    'living_street',  # Shared spaces, very low speed, pedestrians have priority
    'residential',    # Local residential roads — primary use is access on foot
    'unclassified',   # Minor local roads (no speed category assigned)
    'tertiary',       # Smaller through-roads, generally walkable on sidewalks
    'tertiary_link',  # Ramps/links between tertiary roads
    'service',        # Driveways, parking lots, campus service roads
    'track',          # Farm/forest tracks — included as walkable
}

NON_WALKABLE_TYPES = {
    'primary',        # Major arterial roads — high traffic, limited pedestrian access
    'primary_link',   # On/off ramps for primary roads
    'secondary',      # Collector roads — moderate traffic
    'secondary_link', # Ramps between secondary roads
    'cycleway',       # Bicycle-only infrastructure
    'steps',          # Stairs — not general walking route
}

# Display labels and colours per type
TYPE_CONFIG = {
    # walkable
    'footway':        {'label': 'Footway',        'color': '#2ecc71',  'walkable': True},
    'path':           {'label': 'Path',            'color': '#27ae60',  'walkable': True},
    'pedestrian':     {'label': 'Pedestrian',      'color': '#1abc9c',  'walkable': True},
    'living_street':  {'label': 'Living Street',   'color': '#16a085',  'walkable': True},
    'residential':    {'label': 'Residential',     'color': '#3498db',  'walkable': True},
    'unclassified':   {'label': 'Unclassified',    'color': '#5dade2',  'walkable': True},
    'tertiary':       {'label': 'Tertiary',        'color': '#85c1e9',  'walkable': True},
    'tertiary_link':  {'label': 'Tertiary Link',   'color': '#aed6f1',  'walkable': True},
    'service':        {'label': 'Service',         'color': '#9b59b6',  'walkable': True},
    'track':          {'label': 'Track',           'color': '#7f8c8d',  'walkable': True},
    # non-walkable
    'primary':        {'label': 'Primary',         'color': '#e74c3c',  'walkable': False},
    'primary_link':   {'label': 'Primary Link',    'color': '#c0392b',  'walkable': False},
    'secondary':      {'label': 'Secondary',       'color': '#e67e22',  'walkable': False},
    'secondary_link': {'label': 'Secondary Link',  'color': '#d35400',  'walkable': False},
    'cycleway':       {'label': 'Cycleway',        'color': '#f39c12',  'walkable': False},
    'steps':          {'label': 'Steps',           'color': '#bdc3c7',  'walkable': False},
}

WALKABLE_AGG_COLOR     = '#2980b9'
NON_WALKABLE_AGG_COLOR = '#c0392b'
OVERALL_AGG_COLOR      = '#2c3e50'


# ── Data helpers ──────────────────────────────────────────────────────────────

def filter_for_shade(df):
    """Keep sunny rows with ≥1 person and valid UTCI in [-50, 60]."""
    df = df.copy()
    df['total_people'] = df['inshade_count'].fillna(0) + df['outshade_count'].fillna(0)
    mask = (
        (df['is_sunny'].astype(str).str.lower() == 'true') &
        df['inshade_count'].notna() &
        df['outshade_count'].notna() &
        (df['total_people'] > 0) &
        df['utci_C'].notna() &
        (df['utci_C'] >= -50) &
        (df['utci_C'] <= 60)
    )
    out = df[mask].copy()
    out['n_success'] = out['inshade_count'].astype(int)
    out['n_total']   = out['total_people'].astype(int)
    out['shade_ratio'] = out['n_success'] / out['n_total']
    return out


def assign_walkability(df):
    """Add walkable boolean column; rows with unknown/unlisted type → NaN."""
    def _walk(h):
        if h in WALKABLE_TYPES:
            return True
        if h in NON_WALKABLE_TYPES:
            return False
        return None  # unknown / steps with no category
    df = df.copy()
    df['walkable'] = df['highway'].apply(_walk)
    return df


# ── GLM helpers (same as other shade scripts) ─────────────────────────────────

def fit_glm(x, n_success, n_total):
    X = np.column_stack([np.ones(len(x)), x, x ** 2])
    y = np.column_stack([n_success.astype(int), (n_total - n_success).astype(int)])
    try:
        return sm.GLM(y, X, family=sm.families.Binomial()).fit()
    except Exception as e:
        print(f'    Warning: GLM failed: {e}')
        return None


def predict_with_ci(results, x_pred, alpha=0.05):
    X_pred = np.column_stack([np.ones(len(x_pred)), x_pred, x_pred ** 2])
    pred = results.get_prediction(X_pred)
    s = pred.summary_frame(alpha=alpha)
    return s['mean'].values, s['mean_ci_lower'].values, s['mean_ci_upper'].values


def _apply_common_style(ax):
    ax.set_xlabel('UTCI Temperature (°C)', fontsize=13)
    ax.set_ylabel('Shade Ratio (fraction in shade)', fontsize=13)
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, alpha=0.3)


def _plot_glm_on_ax(ax, sdf, color, label):
    """Scatter + GLM fit + 95 % CI on ax. Returns True if GLM succeeded."""
    x        = sdf['utci_C'].values
    n_succ   = sdf['n_success'].values
    n_total  = sdf['n_total'].values
    shade    = sdf['shade_ratio'].values

    np.random.seed(42)
    y_jitter = np.clip(shade + np.random.normal(0, 0.01, len(shade)), 0, 1)
    ax.scatter(x, y_jitter, alpha=0.2, s=12, color=color)

    results = fit_glm(x, n_succ, n_total)
    if results is None:
        return False

    x_lo, x_hi = np.percentile(x, 5), np.percentile(x, 95)
    x_range = np.linspace(x_lo, x_hi, 300)
    y_pred, ci_lo, ci_hi = predict_with_ci(results, x_range)

    ax.fill_between(x_range, ci_lo, ci_hi, color=color, alpha=0.2)
    ax.plot(x_range, y_pred, color=color, linewidth=2.5, label=label)
    return True


# ── Plot: one panel per highway type ─────────────────────────────────────────

def plot_by_type_individual(df, out_dir):
    """Individual GLM plot for each highway type with sufficient data."""
    out_dir.mkdir(parents=True, exist_ok=True)
    types_present = [t for t in TYPE_CONFIG if t in df['highway'].values]

    for ht in types_present:
        sdf = df[df['highway'] == ht]
        if len(sdf) < MIN_OBS:
            print(f'  Skipping {ht} — n={len(sdf)} < {MIN_OBS}')
            continue

        cfg   = TYPE_CONFIG[ht]
        color = cfg['color']
        walk_label = 'Walkable' if cfg['walkable'] else 'Non-walkable'

        fig, ax = plt.subplots(figsize=(11, 7))
        ok = _plot_glm_on_ax(ax, sdf, color, f'GLM fit (95% CI)  n={len(sdf):,}')
        _apply_common_style(ax)
        ax.set_title(
            f"Shade-Seeking vs UTCI — {cfg['label']} ({walk_label})\nState College, PA  (n={len(sdf):,})",
            fontsize=15, fontweight='bold',
        )
        if ok:
            ax.legend(fontsize=11)
        plt.tight_layout()
        path = out_dir / f'state_college_street_{ht}_utci_shade.png'
        plt.savefig(path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f'  Saved: {path.name}')


# ── Plot: all highway types combined ─────────────────────────────────────────

def plot_by_type_combined(df, out_dir):
    """All highway types on one plot, coloured by type."""
    out_dir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(15, 10))

    plotted_walk, plotted_nonwalk = [], []

    for ht, cfg in TYPE_CONFIG.items():
        sdf = df[df['highway'] == ht]
        if len(sdf) < MIN_OBS:
            continue
        ok = _plot_glm_on_ax(ax, sdf, cfg['color'], f"{cfg['label']} (n={len(sdf):,})")
        if ok:
            if cfg['walkable']:
                plotted_walk.append(ht)
            else:
                plotted_nonwalk.append(ht)

    _apply_common_style(ax)
    ax.set_title(
        f'Shade-Seeking vs UTCI — By Street Type\nState College, PA  (n={len(df):,})',
        fontsize=15, fontweight='bold',
    )
    ax.legend(fontsize=10, ncol=2)
    plt.tight_layout()
    path = out_dir / 'state_college_all_street_types_utci_shade.png'
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f'  Saved: {path.name}')


# ── Plot: walkable vs non-walkable aggregate ──────────────────────────────────

def plot_walkable_aggregate(df, out_dir):
    """
    Two-panel figure:
      Left  — GLM for walkable streets vs non-walkable streets + overall
      Right — legend table listing which types are in each category
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    walk_df     = df[df['walkable'] == True]
    nonwalk_df  = df[df['walkable'] == False]

    fig = plt.figure(figsize=(17, 9))
    # Main plot occupies left 70%, legend panel right 30%
    ax_main = fig.add_axes([0.05, 0.12, 0.60, 0.75])
    ax_leg  = fig.add_axes([0.68, 0.05, 0.30, 0.88])
    ax_leg.axis('off')

    def _plot_group(ax, sdf, color, label):
        if len(sdf) >= MIN_OBS:
            _plot_glm_on_ax(ax, sdf, color, label)

    _plot_group(ax_main, walk_df,    WALKABLE_AGG_COLOR,
                f'Walkable (n={len(walk_df):,})')
    _plot_group(ax_main, nonwalk_df, NON_WALKABLE_AGG_COLOR,
                f'Non-walkable (n={len(nonwalk_df):,})')

    # Overall GLM in dark
    results_all = fit_glm(df['utci_C'].values, df['n_success'].values, df['n_total'].values)
    if results_all is not None:
        x_lo, x_hi = np.percentile(df['utci_C'].values, 5), np.percentile(df['utci_C'].values, 95)
        x_range = np.linspace(x_lo, x_hi, 300)
        y_pred, ci_lo, ci_hi = predict_with_ci(results_all, x_range)
        ax_main.fill_between(x_range, ci_lo, ci_hi, color=OVERALL_AGG_COLOR, alpha=0.12)
        ax_main.plot(x_range, y_pred, color=OVERALL_AGG_COLOR, linewidth=3,
                     linestyle='--', alpha=0.8, label=f'Overall (n={len(df):,})')

    _apply_common_style(ax_main)
    ax_main.set_title(
        'Shade-Seeking vs UTCI — Walkable vs Non-Walkable\nState College, PA',
        fontsize=15, fontweight='bold',
    )
    ax_main.legend(fontsize=12)

    # ── Legend table ──────────────────────────────────────────
    walk_types    = sorted([t for t, c in TYPE_CONFIG.items() if c['walkable']     and t in df['highway'].values])
    nonwalk_types = sorted([t for t, c in TYPE_CONFIG.items() if not c['walkable'] and t in df['highway'].values])

    def _type_rows(types, color_hex):
        rows = []
        for t in types:
            n = len(df[df['highway'] == t])
            rows.append((TYPE_CONFIG[t]['label'], f'{n:,}'))
        return rows

    y = 0.97
    def _write_section(title, color_hex, types, walkable_flag):
        nonlocal y
        ax_leg.text(0.0, y, title, transform=ax_leg.transAxes,
                    fontsize=11, fontweight='bold', color=color_hex, va='top')
        y -= 0.045
        for t in types:
            cfg = TYPE_CONFIG.get(t)
            if cfg is None:
                continue
            n_all  = len(df[df['highway'] == t])
            n_filt = len(df[(df['highway'] == t) & (df['walkable'] == walkable_flag)])
            patch = mpatches.Patch(color=cfg['color'])
            ax_leg.text(0.06, y, f"{cfg['label']}", transform=ax_leg.transAxes,
                        fontsize=9, va='top')
            ax_leg.text(0.60, y, f"n={n_filt:,}", transform=ax_leg.transAxes,
                        fontsize=9, va='top', color='#555555')
            ax_leg.add_patch(mpatches.FancyBboxPatch(
                (0.0, y - 0.025), 0.04, 0.025,
                boxstyle='round,pad=0.002',
                facecolor=cfg['color'], edgecolor='none',
                transform=ax_leg.transAxes, clip_on=False,
            ))
            y -= 0.042
        y -= 0.02

    _write_section('Walkable street types', WALKABLE_AGG_COLOR,
                   walk_types, True)
    _write_section('Non-walkable street types', NON_WALKABLE_AGG_COLOR,
                   nonwalk_types, False)

    ax_leg.text(0.0, y,
                'n = shade-filtered rows\n(sunny, ≥1 person, valid UTCI)',
                transform=ax_leg.transAxes, fontsize=8, color='#888888', va='top',
                style='italic')

    path = out_dir / 'state_college_walkable_vs_nonwalkable_utci_shade.png'
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f'  Saved: {path.name}')


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print('=' * 60)
    print('State College — UTCI vs Shade by Street Type')
    print('=' * 60)

    if not INPUT_PATH.exists():
        print(f'ERROR: Input file not found: {INPUT_PATH}')
        print('Run scripts/processing/snap_state_college_to_osm.py first.')
        return

    df = pd.read_csv(INPUT_PATH, low_memory=False)
    print(f'Loaded {len(df):,} rows')

    df = filter_for_shade(df)
    print(f'After shade filter: {len(df):,} rows')

    if len(df) == 0:
        print('ERROR: No usable rows after filtering.')
        return

    df = assign_walkability(df)

    print(f'\nHighway type counts (shade-filtered):')
    for ht, cnt in df['highway'].value_counts().items():
        walk = df.loc[df['highway'] == ht, 'walkable'].iloc[0]
        tag = 'walkable' if walk is True else ('non-walkable' if walk is False else 'unclassified')
        print(f'  {ht:<25} {cnt:>5,}   [{tag}]')

    print(f'\nWalkable rows:     {(df["walkable"] == True).sum():,}')
    print(f'Non-walkable rows: {(df["walkable"] == False).sum():,}')
    print(f'Unclassified rows: {df["walkable"].isna().sum():,}')

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    indiv_dir = OUTPUT_DIR / 'by_type'

    print('\n-- Individual type plots --')
    plot_by_type_individual(df, indiv_dir)

    print('\n-- Combined type plot --')
    plot_by_type_combined(df, OUTPUT_DIR)

    print('\n-- Walkable vs non-walkable aggregate --')
    plot_walkable_aggregate(df, OUTPUT_DIR)

    print('\nDone.')


if __name__ == '__main__':
    main()
