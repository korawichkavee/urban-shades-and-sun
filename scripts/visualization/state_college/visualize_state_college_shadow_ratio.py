# ABOUTME: Shadow ratio visualizations for State College SVI
# ABOUTME: 1) shadow_ratio vs shade preference (binomial GLM)
# ABOUTME: 2) Map of shadow_ratio across OSM road network (walkable vs non-walkable)
# ABOUTME: 3) shadow_ratio distribution by road type (boxplot + mean bars)

from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import matplotlib.lines as mlines
import statsmodels.api as sm
import osmnx as ox

INPUT_PATH = Path(__file__).parent.parent.parent.parent / 'data' / 'state-college' / 'state-college_svi_with_shadow.csv'
OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / 'outputs' / 'plots' / 'state_college' / 'shadow_ratio'

MIN_OBS = 20  # minimum obs per bin for GLM

# ── Walkability classification ────────────────────────────────────────────────

WALKABLE_TYPES = {
    'footway', 'path', 'pedestrian', 'living_street',
    'residential', 'unclassified', 'tertiary', 'tertiary_link',
    'service', 'track',
}
NON_WALKABLE_TYPES = {
    'primary', 'primary_link', 'secondary', 'secondary_link',
    'cycleway', 'steps', 'motorway', 'motorway_link',
}

WALKABLE_COLOR     = '#2980b9'
NON_WALKABLE_COLOR = '#c0392b'
OVERALL_COLOR      = '#2c3e50'

TYPE_CONFIG = {
    'footway':        {'label': 'Footway',        'color': '#27ae60', 'walkable': True},
    'path':           {'label': 'Path',            'color': '#2ecc71', 'walkable': True},
    'pedestrian':     {'label': 'Pedestrian',      'color': '#1abc9c', 'walkable': True},
    'living_street':  {'label': 'Living Street',   'color': '#16a085', 'walkable': True},
    'residential':    {'label': 'Residential',     'color': '#3498db', 'walkable': True},
    'unclassified':   {'label': 'Unclassified',    'color': '#85c1e9', 'walkable': True},
    'tertiary':       {'label': 'Tertiary',        'color': '#5dade2', 'walkable': True},
    'tertiary_link':  {'label': 'Tertiary Link',   'color': '#aed6f1', 'walkable': True},
    'service':        {'label': 'Service',         'color': '#9b59b6', 'walkable': True},
    'track':          {'label': 'Track',           'color': '#7f8c8d', 'walkable': True},
    'primary':        {'label': 'Primary',         'color': '#e74c3c', 'walkable': False},
    'primary_link':   {'label': 'Primary Link',    'color': '#c0392b', 'walkable': False},
    'secondary':      {'label': 'Secondary',       'color': '#e67e22', 'walkable': False},
    'secondary_link': {'label': 'Secondary Link',  'color': '#d35400', 'walkable': False},
    'cycleway':       {'label': 'Cycleway',        'color': '#f39c12', 'walkable': False},
    'steps':          {'label': 'Steps',           'color': '#bdc3c7', 'walkable': False},
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def filter_for_shade(df):
    """Keep sunny rows with >= 1 vote."""
    df = df.copy()
    df['total_people'] = df['inshade_count'].fillna(0) + df['outshade_count'].fillna(0)
    mask = (
        (df['is_sunny'].astype(str).str.lower() == 'true') &
        df['inshade_count'].notna() &
        df['outshade_count'].notna() &
        (df['total_people'] >= 1)
    )
    return df[mask].copy()


def fit_glm_shadow(df_sub, x_col='shadow_ratio', n_points=200):
    """
    Fit binomial GLM: shade_preference ~ shadow_ratio + shadow_ratio^2
    Returns (x_range, p_hat, model) or None on failure.
    """
    x = df_sub[x_col].values
    n = df_sub['total_people'].values.astype(float)
    k = df_sub['inshade_count'].values.astype(float)
    y = np.column_stack([k, n - k])

    X = sm.add_constant(np.column_stack([x, x ** 2]))
    try:
        model = sm.GLM(y, X, family=sm.families.Binomial()).fit(disp=0)
    except Exception as e:
        print(f'    GLM failed: {e}')
        return None

    x_range = np.linspace(x.min(), x.max(), n_points)
    X_pred = sm.add_constant(np.column_stack([x_range, x_range ** 2]),
                              has_constant='add')
    p_hat = model.predict(X_pred)
    return x_range, p_hat, model


# ── Plot 1: shadow_ratio vs shade preference (GLM) ────────────────────────────

def plot_shadow_ratio_vs_preference(df, out_dir):
    """
    Two-panel figure:
      Left:  GLM curves for walkable / non-walkable / overall groups
      Right: Binned scatter (mean shade-pref per shadow_ratio decile) with error bars
    """
    df_filt = filter_for_shade(df)
    df_filt = df_filt[df_filt['shadow_ratio'].notna()].copy()

    # Classify
    df_filt['walkability'] = df_filt['highway'].apply(
        lambda h: 'walkable' if h in WALKABLE_TYPES
                  else ('non-walkable' if h in NON_WALKABLE_TYPES else None)
    )

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # ── Left panel: GLM curves ────────────────────────────────────────────────
    ax = axes[0]

    groups = [
        ('Overall',       df_filt,                                     OVERALL_COLOR,      '-',  2.0),
        ('Walkable',      df_filt[df_filt['walkability'] == 'walkable'],     WALKABLE_COLOR,     '--', 1.8),
        ('Non-walkable',  df_filt[df_filt['walkability'] == 'non-walkable'], NON_WALKABLE_COLOR, ':', 1.8),
    ]

    handles = []
    for name, sub, color, ls, lw in groups:
        if len(sub) < MIN_OBS:
            print(f'  Skipping {name}: n={len(sub)} < {MIN_OBS}')
            continue
        result = fit_glm_shadow(sub)
        if result is None:
            continue
        x_range, p_hat, _ = result
        line, = ax.plot(x_range, p_hat * 100, color=color, ls=ls, lw=lw,
                        label=f'{name}  (n={len(sub):,})')
        handles.append(line)

    ax.set_xlabel('Shadow ratio (fraction of nearest road in shadow)', fontsize=11)
    ax.set_ylabel('Shade preference (%)', fontsize=11)
    ax.set_title('Shade preference vs shadow ratio\n(binomial GLM, quadratic term)', fontsize=12)
    ax.set_ylim(0, 100)
    ax.set_xlim(0, 1)
    ax.axhline(50, color='grey', lw=0.8, ls='--', alpha=0.5)
    ax.legend(handles=handles, fontsize=9)
    ax.grid(True, alpha=0.3)

    # ── Right panel: binned means ─────────────────────────────────────────────
    ax2 = axes[1]

    # Decile bins on shadow_ratio (using quantiles so bins are populated)
    n_bins = 10
    df_filt['sr_decile'] = pd.qcut(df_filt['shadow_ratio'], q=n_bins,
                                    duplicates='drop', labels=False)
    df_filt['shade_pref_pct'] = df_filt['inshade_count'] / df_filt['total_people'] * 100

    bin_stats = df_filt.groupby('sr_decile').agg(
        sr_mid=('shadow_ratio', 'mean'),
        pref_mean=('shade_pref_pct', 'mean'),
        pref_se=('shade_pref_pct', lambda x: x.sem()),
        n=('shade_pref_pct', 'count'),
    ).reset_index()

    for _, row in bin_stats.iterrows():
        ax2.errorbar(row['sr_mid'], row['pref_mean'],
                     yerr=row['pref_se'] * 1.96,
                     fmt='o', color=OVERALL_COLOR, ms=6, capsize=4, lw=1.2)

    # Light walkable / non-walkable binned curves
    for name, sub, color, marker in [
        ('Walkable',     df_filt[df_filt['walkability'] == 'walkable'],     WALKABLE_COLOR,     '^'),
        ('Non-walkable', df_filt[df_filt['walkability'] == 'non-walkable'], NON_WALKABLE_COLOR, 's'),
    ]:
        if len(sub) < 10:
            continue
        sub = sub.copy()
        sub['sr_decile'] = pd.qcut(sub['shadow_ratio'], q=min(n_bins, len(sub)//5),
                                    duplicates='drop', labels=False)
        bs = sub.groupby('sr_decile').agg(
            sr_mid=('shadow_ratio', 'mean'),
            pref_mean=('shade_pref_pct', 'mean'),
            n=('shade_pref_pct', 'count'),
        ).reset_index()
        ax2.plot(bs['sr_mid'], bs['pref_mean'], marker=marker,
                 color=color, lw=1.2, ms=5, alpha=0.7, ls='--', label=name)

    # Overall line
    ax2.errorbar(bin_stats['sr_mid'], bin_stats['pref_mean'],
                 fmt='o-', color=OVERALL_COLOR, ms=6, capsize=3, lw=1.5,
                 label='Overall (mean ± 95% CI)')

    ax2.set_xlabel('Shadow ratio (mean per decile)', fontsize=11)
    ax2.set_ylabel('Shade preference (%)', fontsize=11)
    ax2.set_title('Binned mean shade preference\nby shadow ratio decile', fontsize=12)
    ax2.set_ylim(0, 100)
    ax2.set_xlim(-0.02, 1.02)
    ax2.axhline(50, color='grey', lw=0.8, ls='--', alpha=0.5)
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3)

    fig.suptitle('State College: Shadow ratio vs shade preference', fontsize=14, fontweight='bold')
    fig.tight_layout()
    out_path = out_dir / 'shadow_ratio_vs_preference.png'
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  Saved: {out_path.name}')


# ── Plot 2: Map of shadow_ratio across road network ───────────────────────────

def plot_shadow_ratio_map(df, out_dir):
    """
    Fetch OSM road network; colour each edge by mean shadow_ratio of SVI points
    snapped to that road type.  Walkable vs non-walkable roads are shown with
    different line widths; non-walkable roads have a distinct background stroke.
    """
    print('  Fetching OSM road network for shadow ratio map ...')
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df['lon'], df['lat']), crs='EPSG:4326')
    bounds = gdf.total_bounds
    margin = 0.005
    bbox = (bounds[0] - margin, bounds[1] - margin,
            bounds[2] + margin, bounds[3] + margin)

    try:
        G = ox.graph_from_bbox(bbox=bbox, network_type='all')
        edges = ox.graph_to_gdfs(G, nodes=False).reset_index()
    except Exception as e:
        print(f'  Road fetch failed: {e}')
        return

    # Normalise highway tag
    def norm_hw(v):
        if isinstance(v, list):
            return v[0]
        if isinstance(v, str) and v.startswith('['):
            import ast
            try:
                p = ast.literal_eval(v)
                return p[0] if p else 'unknown'
            except Exception:
                pass
        return v if pd.notna(v) else 'unknown'

    edges['highway_norm'] = edges['highway'].apply(norm_hw)

    # Mean shadow_ratio per highway type from SVI data
    sr_by_type = df.groupby('highway')['shadow_ratio'].mean()
    print('  Mean shadow_ratio by highway type (SVI-weighted):')
    for ht, sr in sr_by_type.sort_values(ascending=False).items():
        print(f'    {ht:<20} {sr:.3f}')

    # Walkability flag on edges
    edges['walkable'] = edges['highway_norm'].apply(
        lambda h: 'walkable' if h in WALKABLE_TYPES
                  else ('non-walkable' if h in NON_WALKABLE_TYPES else 'other')
    )
    # Map edge highway type to mean shadow_ratio
    edges['mean_sr'] = edges['highway_norm'].map(sr_by_type)

    utm_crs = gdf.estimate_utm_crs()
    edges_utm = edges.to_crs(utm_crs)
    gdf_utm   = gdf.to_crs(utm_crs)

    # ── Figure ────────────────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(18, 8))

    cmap = cm.YlOrRd
    norm = mcolors.Normalize(vmin=0, vmax=1)

    for ax_idx, (ax, show_svi) in enumerate(zip(axes, [False, True])):
        # Background: draw all edges grey first
        edges_utm.plot(ax=ax, color='#cccccc', lw=0.4, alpha=0.5)

        # Draw walkable roads (thinner) then non-walkable (thicker) for visual hierarchy
        for walk_group, lw_base, zorder in [('walkable', 1.2, 3), ('non-walkable', 2.2, 4), ('other', 0.7, 2)]:
            sub = edges_utm[edges_utm['walkable'] == walk_group]
            if len(sub) == 0:
                continue
            # Roads with known shadow_ratio → colour-coded
            known = sub[sub['mean_sr'].notna()]
            unknown = sub[sub['mean_sr'].isna()]

            if len(known):
                known.plot(ax=ax, column='mean_sr', cmap=cmap, norm=norm,
                           lw=lw_base, alpha=0.9, zorder=zorder)
            if len(unknown):
                unknown.plot(ax=ax, color='#aaaaaa', lw=lw_base * 0.6,
                             alpha=0.5, zorder=zorder - 1)

        # Walkable / non-walkable boundary visual: dashed outline on non-walkable
        nw = edges_utm[edges_utm['walkable'] == 'non-walkable']
        if len(nw):
            nw.plot(ax=ax, color='black', lw=0.4, alpha=0.25, zorder=5,
                    linestyle='dashed')

        if show_svi:
            # Overlay SVI points coloured by shadow_ratio
            svi_known = gdf_utm[gdf_utm['shadow_ratio'].notna()]
            sc = ax.scatter(svi_known.geometry.x, svi_known.geometry.y,
                            c=svi_known['shadow_ratio'], cmap=cmap, norm=norm,
                            s=2, alpha=0.6, zorder=6)

        ax.set_axis_off()

        title = ('Road network coloured by mean shadow ratio\n'
                 '(solid = walkable, dashed outline = non-walkable)')
        if show_svi:
            title = 'Road network + SVI point shadow ratio'
        ax.set_title(title, fontsize=11, pad=6)

    # Shared colorbar
    sm_obj = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm_obj.set_array([])
    cbar = fig.colorbar(sm_obj, ax=axes, orientation='vertical',
                        fraction=0.015, pad=0.02, shrink=0.7)
    cbar.set_label('Shadow ratio (0 = no shadow, 1 = full shadow)', fontsize=10)

    # Legend patches
    walk_patch  = mlines.Line2D([], [], color='#2980b9', lw=2, label='Walkable roads')
    nwalk_patch = mlines.Line2D([], [], color='#c0392b', lw=2, ls='--', label='Non-walkable roads (dashed outline)')
    axes[0].legend(handles=[walk_patch, nwalk_patch], fontsize=8, loc='lower left')

    fig.suptitle('State College: Shadow ratio across OSM road network', fontsize=14, fontweight='bold')
    out_path = out_dir / 'shadow_ratio_map.png'
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  Saved: {out_path.name}')


# ── Plot 3: shadow_ratio by road type ─────────────────────────────────────────

def plot_shadow_ratio_by_road_type(df, out_dir):
    """
    Three-panel figure:
      Left:   Box plot of shadow_ratio per highway type (all SVI rows)
      Middle: Mean shadow_ratio per highway type with 95% CI bars,
              coloured by walkability and sorted by mean
      Right:  Walkable vs non-walkable aggregate distribution (violin)
    """
    # Restrict to types with meaningful data
    type_counts = df['highway'].value_counts()
    valid_types = type_counts[type_counts >= 10].index.tolist()
    df_plot = df[df['highway'].isin(valid_types)].copy()

    # Assign walkability colour to each row
    df_plot['color'] = df_plot['highway'].apply(
        lambda h: WALKABLE_COLOR if h in WALKABLE_TYPES
                  else (NON_WALKABLE_COLOR if h in NON_WALKABLE_TYPES else '#7f8c8d')
    )
    df_plot['walkability'] = df_plot['highway'].apply(
        lambda h: 'Walkable' if h in WALKABLE_TYPES
                  else ('Non-walkable' if h in NON_WALKABLE_TYPES else 'Other')
    )

    # Sort types by mean shadow_ratio
    mean_sr = df_plot.groupby('highway')['shadow_ratio'].mean().sort_values(ascending=False)
    sorted_types = mean_sr.index.tolist()

    fig, axes = plt.subplots(1, 3, figsize=(18, 7))

    # ── Panel 1: Box plot ─────────────────────────────────────────────────────
    ax = axes[0]
    data_by_type = [df_plot[df_plot['highway'] == ht]['shadow_ratio'].values
                    for ht in sorted_types]
    colors_by_type = [
        WALKABLE_COLOR if ht in WALKABLE_TYPES
        else (NON_WALKABLE_COLOR if ht in NON_WALKABLE_TYPES else '#7f8c8d')
        for ht in sorted_types
    ]
    labels = [TYPE_CONFIG.get(ht, {}).get('label', ht) for ht in sorted_types]
    n_types = len(sorted_types)

    bp = ax.boxplot(data_by_type, vert=False, patch_artist=True,
                    widths=0.6, showfliers=False,
                    medianprops={'color': 'white', 'lw': 2})
    for patch, color in zip(bp['boxes'], colors_by_type):
        patch.set_facecolor(color)
        patch.set_alpha(0.8)
    for whisker in bp['whiskers']:
        whisker.set_color('#555555')
        whisker.set_lw(1)
    for cap in bp['caps']:
        cap.set_color('#555555')

    ax.set_yticks(range(1, n_types + 1))
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel('Shadow ratio', fontsize=10)
    ax.set_title('Shadow ratio distribution\nby road type (box = IQR, no outliers)', fontsize=10)
    ax.set_xlim(-0.05, 1.05)
    ax.axvline(0.5, color='grey', lw=0.8, ls='--', alpha=0.5)
    ax.grid(True, axis='x', alpha=0.3)

    walk_p  = mpatches.Patch(color=WALKABLE_COLOR,     alpha=0.8, label='Walkable')
    nwalk_p = mpatches.Patch(color=NON_WALKABLE_COLOR, alpha=0.8, label='Non-walkable')
    ax.legend(handles=[walk_p, nwalk_p], fontsize=8, loc='lower right')

    # ── Panel 2: Mean + 95% CI bar chart ─────────────────────────────────────
    ax2 = axes[1]
    stats = df_plot.groupby('highway')['shadow_ratio'].agg(['mean', 'sem', 'count']).reset_index()
    stats['ci95'] = stats['sem'] * 1.96
    stats['color'] = stats['highway'].apply(
        lambda h: WALKABLE_COLOR if h in WALKABLE_TYPES
                  else (NON_WALKABLE_COLOR if h in NON_WALKABLE_TYPES else '#7f8c8d')
    )
    stats['label'] = stats['highway'].apply(
        lambda h: TYPE_CONFIG.get(h, {}).get('label', h)
    )
    stats = stats.set_index('highway').loc[sorted_types].reset_index()

    y_pos = np.arange(len(stats))
    bars = ax2.barh(y_pos, stats['mean'], xerr=stats['ci95'],
                    color=stats['color'], alpha=0.85,
                    error_kw={'ecolor': '#333333', 'capsize': 3, 'lw': 1.2},
                    height=0.6)

    # Annotate n
    for i, (_, row) in enumerate(stats.iterrows()):
        ax2.text(row['mean'] + row['ci95'] + 0.01, i,
                 f"n={int(row['count']):,}", va='center', fontsize=7, color='#555555')

    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(stats['label'], fontsize=9)
    ax2.set_xlabel('Mean shadow ratio (± 95% CI)', fontsize=10)
    ax2.set_title('Mean shadow ratio by road type\n(sorted by mean, coloured by walkability)', fontsize=10)
    ax2.set_xlim(-0.02, 1.15)
    ax2.axvline(0.5, color='grey', lw=0.8, ls='--', alpha=0.5)
    ax2.axvline(df_plot['shadow_ratio'].mean(), color='#2c3e50',
                lw=1.2, ls=':', alpha=0.7, label=f'Overall mean ({df_plot["shadow_ratio"].mean():.3f})')
    ax2.legend(fontsize=8)
    ax2.grid(True, axis='x', alpha=0.3)

    # ── Panel 3: Walkable vs non-walkable violin ───────────────────────────────
    ax3 = axes[2]

    walk_data  = df_plot[df_plot['walkability'] == 'Walkable']['shadow_ratio'].values
    nwalk_data = df_plot[df_plot['walkability'] == 'Non-walkable']['shadow_ratio'].values

    vparts = ax3.violinplot([walk_data, nwalk_data], positions=[0, 1],
                             showmedians=True, showextrema=True)

    colors = [WALKABLE_COLOR, NON_WALKABLE_COLOR]
    for i, pc in enumerate(vparts['bodies']):
        pc.set_facecolor(colors[i])
        pc.set_alpha(0.7)
    vparts['cmedians'].set_color('white')
    vparts['cmedians'].set_lw(2)
    for part in ['cmins', 'cmaxes', 'cbars']:
        vparts[part].set_color('#333333')

    # Overlay mean points
    for i, (data, color) in enumerate([(walk_data, WALKABLE_COLOR),
                                        (nwalk_data, NON_WALKABLE_COLOR)]):
        ax3.scatter(i, np.mean(data), color='white', s=60, zorder=5,
                    edgecolors=color, lw=2)
        ax3.text(i, np.mean(data) + 0.04, f'mean={np.mean(data):.3f}',
                 ha='center', fontsize=8, color=color, fontweight='bold')

    ax3.set_xticks([0, 1])
    ax3.set_xticklabels(['Walkable', 'Non-walkable'], fontsize=11)
    ax3.set_ylabel('Shadow ratio', fontsize=10)
    ax3.set_ylim(-0.05, 1.1)
    ax3.set_title('Shadow ratio distribution:\nwalkable vs non-walkable roads', fontsize=10)
    ax3.axhline(0.5, color='grey', lw=0.8, ls='--', alpha=0.5)
    ax3.grid(True, axis='y', alpha=0.3)

    # Counts
    ax3.text(0, -0.04, f'n={len(walk_data):,}', ha='center', fontsize=9, color='#555555')
    ax3.text(1, -0.04, f'n={len(nwalk_data):,}', ha='center', fontsize=9, color='#555555')

    fig.suptitle('State College: Shadow ratio by OSM road type', fontsize=14, fontweight='bold')
    fig.tight_layout()
    out_path = out_dir / 'shadow_ratio_by_road_type.png'
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  Saved: {out_path.name}')


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f'Loading: {INPUT_PATH.name}')
    df = pd.read_csv(INPUT_PATH, low_memory=False)
    print(f'  Rows: {len(df):,}')

    print('\n[1/3] Shadow ratio vs shade preference ...')
    plot_shadow_ratio_vs_preference(df, OUTPUT_DIR)

    print('\n[2/3] Shadow ratio map ...')
    plot_shadow_ratio_map(df, OUTPUT_DIR)

    print('\n[3/3] Shadow ratio by road type ...')
    plot_shadow_ratio_by_road_type(df, OUTPUT_DIR)

    print('\nDone.')


if __name__ == '__main__':
    main()
