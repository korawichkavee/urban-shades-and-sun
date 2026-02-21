# ABOUTME: Snaps State College SVI points to nearest OSM road segments
# ABOUTME: Adds highway classification column to state-college_svi_with_utci.csv

import sys
import numpy as np
import pandas as pd
import geopandas as gpd
import osmnx as ox
from pathlib import Path

INPUT_PATH  = Path(__file__).parent.parent.parent / 'data' / 'state-college' / 'state-college_svi_with_utci.csv'
OUTPUT_PATH = Path(__file__).parent.parent.parent / 'data' / 'state-college' / 'state-college_svi_with_highway.csv'

SNAP_TOLERANCE = 20  # metres — generous enough for GPS jitter on campus


def snap_points_to_roads(points_proj, roads_proj, tolerance):
    """
    Snap projected GeoDataFrame of points to nearest road within tolerance.

    Returns a GeoDataFrame with road attributes merged in.
    Follows the same spatial-index approach as process_all_cities_osm.py.
    """
    points_bbox = points_proj.bounds + [-tolerance, -tolerance, tolerance, tolerance]
    hits = points_bbox.apply(lambda row: list(roads_proj.sindex.intersection(row)), axis=1)

    tmp = pd.DataFrame({
        'pt_idx':  np.repeat(hits.index, hits.apply(len)),
        'line_i':  np.concatenate(hits.values),
    })

    if tmp.empty:
        return gpd.GeoDataFrame()

    roads_reset = roads_proj.reset_index(drop=True)
    tmp = tmp.join(roads_reset, on='line_i')

    points_reset = points_proj.rename(columns={'geometry': 'og_point'})
    tmp = tmp.join(points_reset, on='pt_idx')

    tmp = gpd.GeoDataFrame(tmp, geometry='geometry', crs=points_proj.crs)
    tmp['snap_dist'] = tmp.geometry.distance(gpd.GeoSeries(tmp['og_point'], crs=tmp.crs))
    tmp = tmp.loc[tmp['snap_dist'] <= tolerance]
    tmp = tmp.sort_values('snap_dist')
    closest = tmp.groupby('pt_idx').first()
    return closest


def normalise_highway(val):
    """Flatten list-valued highway tags to a single representative string."""
    if isinstance(val, list):
        return val[0]
    if isinstance(val, str) and val.startswith('['):
        import ast
        try:
            parsed = ast.literal_eval(val)
            return parsed[0] if parsed else 'unknown'
        except Exception:
            pass
    return val if pd.notna(val) else 'unknown'


def main():
    print('=' * 60)
    print('STATE COLLEGE — Snap SVI to OSM Roads')
    print('=' * 60)

    # ── Load SVI data ──────────────────────────────────────────
    print(f'\nLoading: {INPUT_PATH.name}')
    df = pd.read_csv(INPUT_PATH, low_memory=False)
    print(f'  Rows: {len(df):,}')

    gdf = gpd.GeoDataFrame(
        df, geometry=gpd.points_from_xy(df['lon'], df['lat']), crs='EPSG:4326'
    )

    # ── Fetch OSM road network ─────────────────────────────────
    bounds = gdf.total_bounds  # [west, south, east, north]
    margin = 0.005
    bbox = (bounds[0] - margin, bounds[1] - margin,
            bounds[2] + margin, bounds[3] + margin)  # (west, south, east, north)

    print('\nFetching OSM road network ...')
    G = ox.graph_from_bbox(bbox=bbox, network_type='all')
    G_undir = ox.convert.to_undirected(G)
    edges = ox.graph_to_gdfs(G_undir, nodes=False)
    print(f'  Road segments (edges): {len(edges):,}')

    # ── Project both to a local metric CRS ────────────────────
    crs_proj = gdf.estimate_utm_crs()
    gdf_proj   = gdf.to_crs(crs_proj)
    edges_proj = edges.to_crs(crs_proj).reset_index(drop=True)

    # Keep only highway + geometry — avoids column-name clashes with SVI data
    edges_slim = edges_proj[['highway', 'geometry']].copy()

    # ── Snap ──────────────────────────────────────────────────
    print(f'\nSnapping {len(gdf_proj):,} points to roads (tolerance={SNAP_TOLERANCE} m) ...')
    closest = snap_points_to_roads(gdf_proj, edges_slim, SNAP_TOLERANCE)
    print(f'  Snapped: {len(closest):,} / {len(gdf_proj):,} points')

    unsnapped = len(gdf_proj) - len(closest)
    if unsnapped:
        print(f'  Unsnapped (>{SNAP_TOLERANCE} m from any road): {unsnapped:,} — will be tagged "unknown"')

    # ── Merge highway tag back to original df ─────────────────
    snap_highway = closest[['highway']].copy()
    snap_highway.index.name = 'orig_idx'
    snap_highway['highway'] = snap_highway['highway'].apply(normalise_highway)

    df = df.join(snap_highway[['highway']], how='left')
    df['highway'] = df['highway'].fillna('unknown')

    # ── Summary ───────────────────────────────────────────────
    print('\nHighway type counts:')
    for ht, cnt in df['highway'].value_counts().items():
        print(f'  {ht:<25} {cnt:>6,}')

    # ── Save ──────────────────────────────────────────────────
    df.to_csv(OUTPUT_PATH, index=False)
    print(f'\nSaved {len(df):,} rows → {OUTPUT_PATH}')
    print('Done.')


if __name__ == '__main__':
    main()
