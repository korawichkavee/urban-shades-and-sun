# ABOUTME: Map plots for State College, PA SVI data overlaid on OSM road network.
# ABOUTME: Produces shade preference and UTCI temperature maps overall, by season, and by year.

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import geopandas as gpd
import osmnx as ox

INPUT_PATH = Path(__file__).parent.parent.parent.parent / 'data' / 'state-college' / 'state-college_svi_with_utci.csv'
OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / 'outputs' / 'plots' / 'state_college' / 'maps'

# OSM boundary queries — confirmed to resolve via Nominatim
BOUNDARY_QUERIES = {
    'State College': {
        'query': 'State College, Centre County, Pennsylvania, USA',
        'color': '#e67e22',   # orange
        'linewidth': 2.5,
        'linestyle': '--',
        'zorder': 4,
    },
    'Penn State University': {
        'query': 'Pennsylvania State University',
        'color': '#8e44ad',   # purple
        'linewidth': 2.5,
        'linestyle': '-',
        'zorder': 4,
    },
}

SEASON_COLORS = {
    'Winter': '#3498db',
    'Spring': '#2ecc71',
    'Summer': '#e74c3c',
    'Fall':   '#f39c12',
}

SEASON_ORDER = ['Spring', 'Summer', 'Fall', 'Winter']

SHADE_CMAP = mcolors.LinearSegmentedColormap.from_list(
    'shade_pref', ['#e74c3c', '#f39c12', '#3498db']
)

MIN_PEOPLE = 1


def get_season(month):
    """Map month number to season name (northern hemisphere)."""
    if month in [12, 1, 2]:
        return 'Winter'
    elif month in [3, 4, 5]:
        return 'Spring'
    elif month in [6, 7, 8]:
        return 'Summer'
    elif month in [9, 10, 11]:
        return 'Fall'
    return None


def load_svi_data():
    """Load CSV and return (gdf_all, gdf_shade) GeoDataFrames with season/year columns."""
    df = pd.read_csv(INPUT_PATH, low_memory=False)
    df = df[df['utci_C'].notna()].copy()
    df['captured_at'] = pd.to_datetime(df['captured_at'], format='mixed')
    df['month'] = df['captured_at'].dt.month
    df['year'] = df['captured_at'].dt.year
    df['season'] = df['month'].apply(get_season)

    gdf_all = gpd.GeoDataFrame(
        df, geometry=gpd.points_from_xy(df['lon'], df['lat']), crs='EPSG:4326'
    )

    df['total_people'] = df['inshade_count'].fillna(0) + df['outshade_count'].fillna(0)
    mask = (
        (df['is_sunny'].astype(str).str.lower() == 'true') &
        df['inshade_count'].notna() &
        df['outshade_count'].notna() &
        (df['total_people'] >= MIN_PEOPLE)
    )
    df_shade = df[mask].copy()
    df_shade['shade_ratio'] = df_shade['inshade_count'] / df_shade['total_people']

    gdf_shade = gpd.GeoDataFrame(
        df_shade, geometry=gpd.points_from_xy(df_shade['lon'], df_shade['lat']), crs='EPSG:4326'
    )
    return gdf_all, gdf_shade


def fetch_road_network(gdf_all):
    """Fetch full OSM road network covering the data extent.

    osmnx 2.x graph_from_bbox expects bbox=(west, south, east, north).
    """
    bounds = gdf_all.total_bounds  # [minx=west, miny=south, maxx=east, maxy=north]
    margin = 0.005
    bbox = (
        bounds[0] - margin,  # west
        bounds[1] - margin,  # south
        bounds[2] + margin,  # east
        bounds[3] + margin,  # north
    )
    G = ox.graph_from_bbox(bbox=bbox, network_type='all')
    nodes, edges = ox.graph_to_gdfs(G)
    return edges.to_crs('EPSG:4326')


def fetch_boundaries():
    """Fetch boundary polygons from OSM; skip any that fail."""
    boundaries = {}
    for name, cfg in BOUNDARY_QUERIES.items():
        try:
            gdf = ox.geocode_to_gdf(cfg['query'])
            boundaries[name] = {'gdf': gdf.to_crs('EPSG:4326'), **cfg}
            print(f'  Boundary loaded: {name}')
        except Exception as e:
            print(f'  WARNING: Could not load boundary for {name}: {e}')
    return boundaries


def _draw_boundaries(ax, boundaries):
    """Draw boundary polygons on ax; return legend handles."""
    handles = []
    for name, cfg in boundaries.items():
        cfg['gdf'].boundary.plot(
            ax=ax,
            color=cfg['color'],
            linewidth=cfg['linewidth'],
            linestyle=cfg['linestyle'],
            zorder=cfg['zorder'],
        )
        handles.append(mpatches.Patch(
            edgecolor=cfg['color'],
            facecolor='none',
            linewidth=cfg['linewidth'],
            linestyle=cfg['linestyle'],
            label=name,
        ))
    return handles


def _set_map_extent(ax, gdf_all, margin=0.005):
    """Set axis limits to the full data extent so all facets share the same view."""
    bounds = gdf_all.total_bounds
    ax.set_xlim(bounds[0] - margin, bounds[2] + margin)
    ax.set_ylim(bounds[1] - margin, bounds[3] + margin)


def _render_shade_map(ax, edges, gdf_subset, gdf_all, boundaries, title, shade_norm):
    """Render one shade preference map panel onto ax."""
    edges.plot(ax=ax, linewidth=0.4, color='#888888', alpha=0.5, zorder=1)
    scatter = ax.scatter(
        gdf_subset.geometry.x,
        gdf_subset.geometry.y,
        c=gdf_subset['shade_ratio'],
        cmap=SHADE_CMAP,
        norm=shade_norm,
        s=18,
        alpha=0.75,
        zorder=3,
        linewidths=0,
    )
    boundary_handles = _draw_boundaries(ax, boundaries)
    _set_map_extent(ax, gdf_all)
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.set_xlabel('Longitude', fontsize=10)
    ax.set_ylabel('Latitude', fontsize=10)
    ax.tick_params(labelsize=8)
    return scatter, boundary_handles


def _render_utci_map(ax, edges, gdf_subset, gdf_all, boundaries, title, utci_norm):
    """Render one UTCI temperature map panel onto ax."""
    # Aggregate to mean UTCI per location to reduce overplotting
    sub = gdf_subset.copy()
    sub['lat_r'] = sub['lat'].round(4)
    sub['lon_r'] = sub['lon'].round(4)
    agg = sub.groupby(['lat_r', 'lon_r']).agg(mean_utci=('utci_C', 'mean')).reset_index()
    gdf_agg = gpd.GeoDataFrame(
        agg, geometry=gpd.points_from_xy(agg['lon_r'], agg['lat_r']), crs='EPSG:4326'
    )

    edges.plot(ax=ax, linewidth=0.4, color='#888888', alpha=0.5, zorder=1)
    scatter = ax.scatter(
        gdf_agg.geometry.x,
        gdf_agg.geometry.y,
        c=gdf_agg['mean_utci'],
        cmap=cm.RdYlBu_r,
        norm=utci_norm,
        s=18,
        alpha=0.75,
        zorder=3,
        linewidths=0,
    )
    boundary_handles = _draw_boundaries(ax, boundaries)
    _set_map_extent(ax, gdf_all)
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.set_xlabel('Longitude', fontsize=10)
    ax.set_ylabel('Latitude', fontsize=10)
    ax.tick_params(labelsize=8)
    return scatter, boundary_handles


# ── Aggregate maps ─────────────────────────────────────────────────────────────

def plot_shade_map(edges, gdf_shade, gdf_all, boundaries, out_dir):
    """Single map: all data, colored by shade ratio."""
    out_dir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(14, 12))
    norm = mcolors.Normalize(vmin=0, vmax=1)
    scatter, bh = _render_shade_map(
        ax, edges, gdf_shade, gdf_all, boundaries,
        f'Shade Preference by SVI Location — State College, PA\n'
        f'(n={len(gdf_shade):,} sunny images with ≥1 person; blue=more shade, red=less shade)',
        norm,
    )
    cbar = plt.colorbar(scatter, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label('Shade Ratio  (0 = no shade, 1 = full shade)', fontsize=12)
    if bh:
        ax.legend(handles=bh, fontsize=11, loc='lower left', framealpha=0.9)
    plt.tight_layout()
    path = out_dir / 'state_college_map_shade_preference.png'
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f'  Saved: {path}')


def plot_utci_map(edges, gdf_all, boundaries, out_dir):
    """Single map: all data, colored by mean UTCI."""
    out_dir.mkdir(parents=True, exist_ok=True)
    vmin = np.percentile(gdf_all['utci_C'], 2)
    vmax = np.percentile(gdf_all['utci_C'], 98)
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)

    fig, ax = plt.subplots(figsize=(14, 12))
    scatter, bh = _render_utci_map(
        ax, edges, gdf_all, gdf_all, boundaries,
        f'Mean UTCI Temperature by SVI Location — State College, PA\n'
        f'(n={len(gdf_all):,} images)',
        norm,
    )
    cbar = plt.colorbar(scatter, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label('Mean UTCI Temperature (°C)', fontsize=12)
    if bh:
        ax.legend(handles=bh, fontsize=11, loc='lower left', framealpha=0.9)
    plt.tight_layout()
    path = out_dir / 'state_college_map_utci_temperature.png'
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f'  Saved: {path}')


# ── Seasonal maps ──────────────────────────────────────────────────────────────

def plot_shade_maps_by_season(edges, gdf_shade, gdf_all, boundaries, out_dir):
    """Grid of shade preference maps, one panel per season."""
    out_dir.mkdir(parents=True, exist_ok=True)
    valid = [(s, gdf_shade[gdf_shade['season'] == s]) for s in SEASON_ORDER]
    valid = [(s, g) for s, g in valid if len(g) >= 10]

    n = len(valid)
    if n == 0:
        print('  No seasons with enough data, skipping seasonal shade maps.')
        return

    ncols = min(2, n)
    nrows = (n + ncols - 1) // ncols
    norm = mcolors.Normalize(vmin=0, vmax=1)

    fig, axes = plt.subplots(nrows, ncols, figsize=(13 * ncols, 11 * nrows), squeeze=False)

    last_scatter = None
    last_bh = None
    for idx, (season, gsub) in enumerate(valid):
        r, c = divmod(idx, ncols)
        ax = axes[r][c]
        scatter, bh = _render_shade_map(
            ax, edges, gsub, gdf_all, boundaries,
            f'{season}  (n={len(gsub):,})', norm,
        )
        last_scatter, last_bh = scatter, bh

    # Hide unused panels
    for idx in range(n, nrows * ncols):
        r, c = divmod(idx, ncols)
        axes[r][c].set_visible(False)

    fig.suptitle('Shade Preference by Season — State College, PA\n'
                 '(blue=more shade, red=less shade)',
                 fontsize=16, fontweight='bold', y=1.01)

    if last_scatter is not None:
        cbar = fig.colorbar(last_scatter, ax=axes, fraction=0.015, pad=0.02)
        cbar.set_label('Shade Ratio', fontsize=12)
    if last_bh:
        fig.legend(handles=last_bh, fontsize=11, loc='lower center',
                   ncol=len(last_bh), bbox_to_anchor=(0.5, -0.02))

    plt.tight_layout()
    path = out_dir / 'state_college_map_shade_by_season.png'
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f'  Saved: {path}')


def plot_utci_maps_by_season(edges, gdf_all, boundaries, out_dir):
    """Grid of UTCI temperature maps, one panel per season."""
    out_dir.mkdir(parents=True, exist_ok=True)
    valid = [(s, gdf_all[gdf_all['season'] == s]) for s in SEASON_ORDER]
    valid = [(s, g) for s, g in valid if len(g) >= 10]

    n = len(valid)
    if n == 0:
        return

    # Use a shared UTCI colour scale across all seasons for comparability
    all_utci = gdf_all['utci_C']
    norm = mcolors.Normalize(
        vmin=np.percentile(all_utci, 2),
        vmax=np.percentile(all_utci, 98),
    )

    ncols = min(2, n)
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(13 * ncols, 11 * nrows), squeeze=False)

    last_scatter = None
    last_bh = None
    for idx, (season, gsub) in enumerate(valid):
        r, c = divmod(idx, ncols)
        ax = axes[r][c]
        scatter, bh = _render_utci_map(
            ax, edges, gsub, gdf_all, boundaries,
            f'{season}  (n={len(gsub):,})', norm,
        )
        last_scatter, last_bh = scatter, bh

    for idx in range(n, nrows * ncols):
        r, c = divmod(idx, ncols)
        axes[r][c].set_visible(False)

    fig.suptitle('Mean UTCI Temperature by Season — State College, PA',
                 fontsize=16, fontweight='bold', y=1.01)

    if last_scatter is not None:
        cbar = fig.colorbar(last_scatter, ax=axes, fraction=0.015, pad=0.02)
        cbar.set_label('Mean UTCI (°C)', fontsize=12)
    if last_bh:
        fig.legend(handles=last_bh, fontsize=11, loc='lower center',
                   ncol=len(last_bh), bbox_to_anchor=(0.5, -0.02))

    plt.tight_layout()
    path = out_dir / 'state_college_map_utci_by_season.png'
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f'  Saved: {path}')


# ── Yearly maps ────────────────────────────────────────────────────────────────

def plot_shade_maps_by_year(edges, gdf_shade, gdf_all, boundaries, out_dir):
    """Grid of shade preference maps, one panel per year."""
    out_dir.mkdir(parents=True, exist_ok=True)
    years = sorted(gdf_shade['year'].unique())
    valid = [(y, gdf_shade[gdf_shade['year'] == y]) for y in years]
    valid = [(y, g) for y, g in valid if len(g) >= 10]

    n = len(valid)
    if n == 0:
        return

    ncols = min(3, n)
    nrows = (n + ncols - 1) // ncols
    norm = mcolors.Normalize(vmin=0, vmax=1)

    fig, axes = plt.subplots(nrows, ncols, figsize=(12 * ncols, 10 * nrows), squeeze=False)

    last_scatter = None
    last_bh = None
    for idx, (year, gsub) in enumerate(valid):
        r, c = divmod(idx, ncols)
        ax = axes[r][c]
        scatter, bh = _render_shade_map(
            ax, edges, gsub, gdf_all, boundaries,
            f'{year}  (n={len(gsub):,})', norm,
        )
        last_scatter, last_bh = scatter, bh

    for idx in range(n, nrows * ncols):
        r, c = divmod(idx, ncols)
        axes[r][c].set_visible(False)

    fig.suptitle('Shade Preference by Year — State College, PA\n'
                 '(blue=more shade, red=less shade)',
                 fontsize=16, fontweight='bold', y=1.01)

    if last_scatter is not None:
        cbar = fig.colorbar(last_scatter, ax=axes, fraction=0.01, pad=0.02)
        cbar.set_label('Shade Ratio', fontsize=12)
    if last_bh:
        fig.legend(handles=last_bh, fontsize=11, loc='lower center',
                   ncol=len(last_bh), bbox_to_anchor=(0.5, -0.02))

    plt.tight_layout()
    path = out_dir / 'state_college_map_shade_by_year.png'
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f'  Saved: {path}')


def plot_utci_maps_by_year(edges, gdf_all, boundaries, out_dir):
    """Grid of UTCI temperature maps, one panel per year."""
    out_dir.mkdir(parents=True, exist_ok=True)
    years = sorted(gdf_all['year'].unique())
    valid = [(y, gdf_all[gdf_all['year'] == y]) for y in years]
    valid = [(y, g) for y, g in valid if len(g) >= 10]

    n = len(valid)
    if n == 0:
        return

    all_utci = gdf_all['utci_C']
    norm = mcolors.Normalize(
        vmin=np.percentile(all_utci, 2),
        vmax=np.percentile(all_utci, 98),
    )

    ncols = min(3, n)
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(12 * ncols, 10 * nrows), squeeze=False)

    last_scatter = None
    last_bh = None
    for idx, (year, gsub) in enumerate(valid):
        r, c = divmod(idx, ncols)
        ax = axes[r][c]
        scatter, bh = _render_utci_map(
            ax, edges, gsub, gdf_all, boundaries,
            f'{year}  (n={len(gsub):,})', norm,
        )
        last_scatter, last_bh = scatter, bh

    for idx in range(n, nrows * ncols):
        r, c = divmod(idx, ncols)
        axes[r][c].set_visible(False)

    fig.suptitle('Mean UTCI Temperature by Year — State College, PA',
                 fontsize=16, fontweight='bold', y=1.01)

    if last_scatter is not None:
        cbar = fig.colorbar(last_scatter, ax=axes, fraction=0.01, pad=0.02)
        cbar.set_label('Mean UTCI (°C)', fontsize=12)
    if last_bh:
        fig.legend(handles=last_bh, fontsize=11, loc='lower center',
                   ncol=len(last_bh), bbox_to_anchor=(0.5, -0.02))

    plt.tight_layout()
    path = out_dir / 'state_college_map_utci_by_year.png'
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f'  Saved: {path}')


def main():
    print('=' * 60)
    print('State College — Map Plots')
    print('=' * 60)

    if not INPUT_PATH.exists():
        print(f'ERROR: Input file not found: {INPUT_PATH}')
        print('Run scripts/processing/add_utci_to_state_college.py first.')
        return

    print('Loading SVI data...')
    gdf_all, gdf_shade = load_svi_data()
    print(f'  All rows with UTCI: {len(gdf_all):,}')
    print(f'  Shade-filtered rows: {len(gdf_shade):,}')

    print('Fetching OSM road network (fetched once, reused for all maps)...')
    edges = fetch_road_network(gdf_all)
    print(f'  Road edges: {len(edges):,}')

    print('Fetching boundary polygons...')
    boundaries = fetch_boundaries()

    out_dir = OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    print('\n-- Aggregate maps --')
    plot_shade_map(edges, gdf_shade, gdf_all, boundaries, out_dir)
    plot_utci_map(edges, gdf_all, boundaries, out_dir)

    print('\n-- Seasonal maps --')
    plot_shade_maps_by_season(edges, gdf_shade, gdf_all, boundaries, out_dir)
    plot_utci_maps_by_season(edges, gdf_all, boundaries, out_dir)

    print('\n-- Yearly maps --')
    plot_shade_maps_by_year(edges, gdf_shade, gdf_all, boundaries, out_dir)
    plot_utci_maps_by_year(edges, gdf_all, boundaries, out_dir)

    print('\nDone.')


if __name__ == '__main__':
    main()
