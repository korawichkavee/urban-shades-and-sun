# ABOUTME: Map of State College OSM road network coloured by highway classification
# ABOUTME: Overlays SVI point locations; includes legend showing walkable vs non-walkable groupings

from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
import osmnx as ox

INPUT_PATH = Path(__file__).parent.parent.parent.parent / 'data' / 'state-college' / 'state-college_svi_with_highway.csv'
OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / 'outputs' / 'plots' / 'state_college' / 'street_type'

# ── Colour scheme ─────────────────────────────────────────────────────────────
# Walkable types → greens/blues; non-walkable → reds/oranges; special → greys

HIGHWAY_STYLE = {
    # ---- Walkable ----------------------------------------------------------
    'footway':        {'color': '#27ae60', 'lw': 0.8,  'alpha': 0.9,  'zorder': 4,
                       'label': 'Footway',        'walkable': True},
    'path':           {'color': '#2ecc71', 'lw': 0.7,  'alpha': 0.85, 'zorder': 4,
                       'label': 'Path',            'walkable': True},
    'pedestrian':     {'color': '#1abc9c', 'lw': 1.2,  'alpha': 0.95, 'zorder': 5,
                       'label': 'Pedestrian',      'walkable': True},
    'living_street':  {'color': '#16a085', 'lw': 1.0,  'alpha': 0.9,  'zorder': 4,
                       'label': 'Living Street',   'walkable': True},
    'residential':    {'color': '#3498db', 'lw': 1.0,  'alpha': 0.85, 'zorder': 3,
                       'label': 'Residential',     'walkable': True},
    'unclassified':   {'color': '#85c1e9', 'lw': 0.8,  'alpha': 0.8,  'zorder': 3,
                       'label': 'Unclassified',    'walkable': True},
    'tertiary':       {'color': '#5dade2', 'lw': 1.0,  'alpha': 0.85, 'zorder': 3,
                       'label': 'Tertiary',        'walkable': True},
    'tertiary_link':  {'color': '#aed6f1', 'lw': 0.7,  'alpha': 0.8,  'zorder': 3,
                       'label': 'Tertiary Link',   'walkable': True},
    'service':        {'color': '#9b59b6', 'lw': 0.7,  'alpha': 0.75, 'zorder': 3,
                       'label': 'Service',         'walkable': True},
    'track':          {'color': '#7f8c8d', 'lw': 0.6,  'alpha': 0.7,  'zorder': 2,
                       'label': 'Track',           'walkable': True},
    # ---- Non-walkable -------------------------------------------------------
    'primary':        {'color': '#e74c3c', 'lw': 2.0,  'alpha': 0.95, 'zorder': 5,
                       'label': 'Primary',         'walkable': False},
    'primary_link':   {'color': '#c0392b', 'lw': 1.2,  'alpha': 0.9,  'zorder': 4,
                       'label': 'Primary Link',    'walkable': False},
    'secondary':      {'color': '#e67e22', 'lw': 1.6,  'alpha': 0.9,  'zorder': 4,
                       'label': 'Secondary',       'walkable': False},
    'secondary_link': {'color': '#d35400', 'lw': 0.9,  'alpha': 0.85, 'zorder': 3,
                       'label': 'Secondary Link',  'walkable': False},
    'cycleway':       {'color': '#f39c12', 'lw': 0.9,  'alpha': 0.85, 'zorder': 4,
                       'label': 'Cycleway',        'walkable': False},
    'steps':          {'color': '#bdc3c7', 'lw': 0.7,  'alpha': 0.8,  'zorder': 3,
                       'label': 'Steps',           'walkable': False},
    'motorway':       {'color': '#922b21', 'lw': 2.2,  'alpha': 0.95, 'zorder': 6,
                       'label': 'Motorway',        'walkable': False},
    'motorway_link':  {'color': '#a93226', 'lw': 1.4,  'alpha': 0.9,  'zorder': 5,
                       'label': 'Motorway Link',   'walkable': False},
}

# Fallback for any type not listed above
DEFAULT_STYLE = {'color': '#cccccc', 'lw': 0.5, 'alpha': 0.5, 'zorder': 1, 'label': 'Other', 'walkable': None}

BOUNDARY_QUERIES = {
    'State College':         {'query': 'State College, Centre County, Pennsylvania, USA',
                              'color': '#e67e22', 'linestyle': '--', 'lw': 1.5},
    'Penn State University': {'query': 'Pennsylvania State University',
                              'color': '#8e44ad', 'linestyle': '-',  'lw': 1.5},
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def normalise_highway(val):
    """Flatten list-valued OSM highway tags."""
    if isinstance(val, list):
        return val[0]
    if isinstance(val, str) and val.startswith('['):
        import ast
        try:
            parsed = ast.literal_eval(val)
            return parsed[0] if parsed else 'other'
        except Exception:
            pass
    return val if (pd.notna(val) and val != '') else 'other'


def fetch_road_network_with_types(gdf_all):
    """Fetch OSM network; return edges GeoDataFrame with normalised highway column."""
    bounds = gdf_all.total_bounds
    margin = 0.005
    bbox = (bounds[0] - margin, bounds[1] - margin,
            bounds[2] + margin, bounds[3] + margin)

    print('  Fetching OSM road network ...')
    G = ox.graph_from_bbox(bbox=bbox, network_type='all')
    edges = ox.graph_to_gdfs(G, nodes=False).to_crs('EPSG:4326').reset_index(drop=True)
    edges['highway_norm'] = edges['highway'].apply(normalise_highway)
    print(f'  Edges: {len(edges):,}')
    return edges


def fetch_boundaries():
    """Fetch boundary polygons; skip failures."""
    boundaries = {}
    for name, cfg in BOUNDARY_QUERIES.items():
        try:
            gdf = ox.geocode_to_gdf(cfg['query'])
            boundaries[name] = gdf
            print(f'  Loaded boundary: {name}')
        except Exception as e:
            print(f'  WARNING: Could not fetch boundary for {name}: {e}')
    return boundaries


def _set_extent(ax, gdf_all, margin=0.003):
    b = gdf_all.total_bounds
    ax.set_xlim(b[0] - margin, b[2] + margin)
    ax.set_ylim(b[1] - margin, b[3] + margin)


def _draw_boundaries(ax, boundaries):
    for name, cfg in BOUNDARY_QUERIES.items():
        gdf = boundaries.get(name)
        if gdf is not None:
            gdf.boundary.plot(ax=ax, color=cfg['color'],
                              linestyle=cfg['linestyle'], linewidth=cfg['lw'],
                              zorder=10, label=name)


def _build_legend_handles(types_present, boundaries):
    """Build a list of legend handles with walkable/non-walkable section headers."""
    walk_handles     = []
    nonwalk_handles  = []

    # Section header patches (invisible, just for spacing/title)
    walk_header = mpatches.Patch(color='none', label='── Walkable ──')
    nwalk_header = mpatches.Patch(color='none', label='── Non-walkable ──')

    for ht in types_present:
        sty = HIGHWAY_STYLE.get(ht, DEFAULT_STYLE)
        handle = mlines.Line2D([], [], color=sty['color'],
                               linewidth=max(sty['lw'] * 1.5, 1.5),
                               label=f"{sty['label']}  ({ht})")
        if sty['walkable'] is True:
            walk_handles.append(handle)
        elif sty['walkable'] is False:
            nonwalk_handles.append(handle)

    boundary_handles = [
        mlines.Line2D([], [], color=cfg['color'], linestyle=cfg['linestyle'],
                      linewidth=1.8, label=name)
        for name, cfg in BOUNDARY_QUERIES.items()
    ]

    all_handles = (
        [walk_header] + walk_handles +
        [nwalk_header] + nonwalk_handles +
        boundary_handles
    )
    return all_handles


# ── Main plot ─────────────────────────────────────────────────────────────────

def plot_street_type_map(edges, gdf_all, boundaries, out_dir):
    """Full-area map coloured by highway type with SVI points overlaid."""
    out_dir.mkdir(parents=True, exist_ok=True)

    types_present = sorted(edges['highway_norm'].unique())
    print(f'  Highway types in network: {types_present}')

    fig, ax = plt.subplots(figsize=(16, 14))
    ax.set_facecolor('#f0f0f0')

    # Draw roads grouped by type so zorder is respected
    type_order = sorted(types_present,
                        key=lambda t: HIGHWAY_STYLE.get(t, DEFAULT_STYLE)['zorder'])
    for ht in type_order:
        sty = HIGHWAY_STYLE.get(ht, DEFAULT_STYLE)
        subset = edges[edges['highway_norm'] == ht]
        subset.plot(ax=ax, color=sty['color'], linewidth=sty['lw'],
                    alpha=sty['alpha'], zorder=sty['zorder'])

    # SVI point locations (all, tiny grey dots for context)
    ax.scatter(gdf_all.geometry.x, gdf_all.geometry.y,
               s=2, color='#222222', alpha=0.25, zorder=8, label='_nolegend_')

    _draw_boundaries(ax, boundaries)
    _set_extent(ax, gdf_all)

    ax.set_xlabel('Longitude', fontsize=12)
    ax.set_ylabel('Latitude', fontsize=12)
    ax.set_title('OSM Street Classification — State College, PA\n'
                 'SVI locations shown as grey dots',
                 fontsize=16, fontweight='bold')

    handles = _build_legend_handles(types_present, boundaries)
    ax.legend(handles=handles, fontsize=9, loc='lower left',
              framealpha=0.85, title='Street type', title_fontsize=10)

    plt.tight_layout()
    path = out_dir / 'state_college_street_type_map.png'
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f'  Saved: {path.name}')


def plot_walkable_map(edges, gdf_all, boundaries, out_dir):
    """
    Simplified two-colour map: walkable (blue) vs non-walkable (red),
    with walkable types listed in the legend.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(14, 12))
    ax.set_facecolor('#f0f0f0')

    walk_color    = '#2980b9'
    nonwalk_color = '#e74c3c'
    other_color   = '#bbbbbb'

    for ht in sorted(edges['highway_norm'].unique()):
        sty = HIGHWAY_STYLE.get(ht, DEFAULT_STYLE)
        subset = edges[edges['highway_norm'] == ht]
        if sty['walkable'] is True:
            color, zo = walk_color, 3
        elif sty['walkable'] is False:
            color, zo = nonwalk_color, 4
        else:
            color, zo = other_color, 2
        subset.plot(ax=ax, color=color, linewidth=max(sty['lw'], 0.6),
                    alpha=0.8, zorder=zo)

    ax.scatter(gdf_all.geometry.x, gdf_all.geometry.y,
               s=3, color='#111111', alpha=0.3, zorder=8)

    _draw_boundaries(ax, boundaries)
    _set_extent(ax, gdf_all)

    ax.set_xlabel('Longitude', fontsize=12)
    ax.set_ylabel('Latitude', fontsize=12)
    ax.set_title('Walkable vs Non-Walkable Streets — State College, PA',
                 fontsize=16, fontweight='bold')

    # Build legend entries listing which types fall in each group
    walk_types    = [ht for ht in sorted(HIGHWAY_STYLE)
                     if HIGHWAY_STYLE[ht]['walkable'] is True
                     and ht in edges['highway_norm'].values]
    nonwalk_types = [ht for ht in sorted(HIGHWAY_STYLE)
                     if HIGHWAY_STYLE[ht]['walkable'] is False
                     and ht in edges['highway_norm'].values]

    def _type_list_str(types):
        return '\n  '.join(HIGHWAY_STYLE[t]['label'] for t in types)

    walk_handle = mpatches.Patch(
        color=walk_color,
        label=f"Walkable:\n  {_type_list_str(walk_types)}"
    )
    nonwalk_handle = mpatches.Patch(
        color=nonwalk_color,
        label=f"Non-walkable:\n  {_type_list_str(nonwalk_types)}"
    )
    boundary_handles = [
        mlines.Line2D([], [], color=cfg['color'], linestyle=cfg['linestyle'],
                      linewidth=1.8, label=name)
        for name, cfg in BOUNDARY_QUERIES.items()
    ]

    ax.legend(handles=[walk_handle, nonwalk_handle] + boundary_handles,
              fontsize=9, loc='lower left', framealpha=0.88,
              title='Street category', title_fontsize=10)

    plt.tight_layout()
    path = out_dir / 'state_college_walkable_map.png'
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f'  Saved: {path.name}')


def plot_unclassified_highlight_map(edges, gdf_all, boundaries, out_dir):
    """
    Highlight highway=unclassified segments; all other roads drawn in light grey.
    SVI points on unclassified roads shown in orange; all others in grey.
    Includes an inset count annotation.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    UNCLASSIFIED_COLOR = '#e67e22'   # orange
    OTHER_ROAD_COLOR   = '#cccccc'
    SVI_ON_COLOR       = '#e67e22'
    SVI_OFF_COLOR      = '#aaaaaa'

    unclass_edges  = edges[edges['highway_norm'] == 'unclassified']
    other_edges    = edges[edges['highway_norm'] != 'unclassified']

    svi_on  = gdf_all[gdf_all['highway'] == 'unclassified']
    svi_off = gdf_all[gdf_all['highway'] != 'unclassified']

    fig, ax = plt.subplots(figsize=(14, 12))
    ax.set_facecolor('#f5f5f5')

    other_edges.plot(ax=ax, color=OTHER_ROAD_COLOR, linewidth=0.5, alpha=0.5, zorder=2)
    unclass_edges.plot(ax=ax, color=UNCLASSIFIED_COLOR, linewidth=1.8, alpha=0.95, zorder=4)

    if len(svi_off):
        ax.scatter(svi_off.geometry.x, svi_off.geometry.y,
                   s=3, color=SVI_OFF_COLOR, alpha=0.25, zorder=5)
    if len(svi_on):
        ax.scatter(svi_on.geometry.x, svi_on.geometry.y,
                   s=18, color=SVI_ON_COLOR, alpha=0.85, zorder=6,
                   edgecolors='white', linewidths=0.3)

    _draw_boundaries(ax, boundaries)
    _set_extent(ax, gdf_all)

    ax.set_xlabel('Longitude', fontsize=12)
    ax.set_ylabel('Latitude', fontsize=12)
    ax.set_title(
        'OSM highway=unclassified Segments — State College, PA\n'
        'Orange = unclassified roads & SVI locations  |  Grey = all other roads',
        fontsize=14, fontweight='bold',
    )

    # Legend
    unclass_line = mlines.Line2D([], [], color=UNCLASSIFIED_COLOR, linewidth=2.5,
                                 label=f'Unclassified road segments  ({len(unclass_edges):,} edges)')
    other_line   = mlines.Line2D([], [], color=OTHER_ROAD_COLOR, linewidth=1.5,
                                 label='All other road types')
    svi_on_pt    = mlines.Line2D([], [], marker='o', color='none',
                                 markerfacecolor=SVI_ON_COLOR, markeredgecolor='white',
                                 markersize=7,
                                 label=f'SVI on unclassified  (n={len(svi_on):,})')
    svi_off_pt   = mlines.Line2D([], [], marker='o', color='none',
                                 markerfacecolor=SVI_OFF_COLOR, markersize=5, alpha=0.5,
                                 label=f'SVI on other types  (n={len(svi_off):,})')
    boundary_handles = [
        mlines.Line2D([], [], color=cfg['color'], linestyle=cfg['linestyle'],
                      linewidth=1.8, label=name)
        for name, cfg in BOUNDARY_QUERIES.items()
    ]

    ax.legend(handles=[unclass_line, other_line, svi_on_pt, svi_off_pt] + boundary_handles,
              fontsize=10, loc='lower left', framealpha=0.88)

    plt.tight_layout()
    path = out_dir / 'state_college_unclassified_highlight_map.png'
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f'  Saved: {path.name}')


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print('=' * 60)
    print('State College — Street Type Maps')
    print('=' * 60)

    if not INPUT_PATH.exists():
        print(f'ERROR: {INPUT_PATH} not found.')
        print('Run scripts/processing/snap_state_college_to_osm.py first.')
        return

    df = pd.read_csv(INPUT_PATH, low_memory=False)
    print(f'Loaded {len(df):,} rows')

    gdf_all = gpd.GeoDataFrame(
        df, geometry=gpd.points_from_xy(df['lon'], df['lat']), crs='EPSG:4326'
    )

    edges      = fetch_road_network_with_types(gdf_all)
    boundaries = fetch_boundaries()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print('\n-- Detailed street type map --')
    plot_street_type_map(edges, gdf_all, boundaries, OUTPUT_DIR)

    print('\n-- Walkable vs non-walkable map --')
    plot_walkable_map(edges, gdf_all, boundaries, OUTPUT_DIR)

    print('\n-- Unclassified highlight map --')
    plot_unclassified_highlight_map(edges, gdf_all, boundaries, OUTPUT_DIR)

    print('\nDone.')


if __name__ == '__main__':
    main()
