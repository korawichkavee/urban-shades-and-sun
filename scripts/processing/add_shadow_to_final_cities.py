# ABOUTME: Annotates Seattle/NYC final_run_outputs SVI with shadow availability using salusshadow.py
# ABOUTME: Downloads OSM buildings/trees once, then computes shadow union per unique date+hour

import sys
import math
import logging
import argparse
from datetime import timezone as dt_timezone
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from shapely.ops import unary_union
import osmnx as ox

# Add salusshadow to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'data_collection'))
from salusshadow import (
    get_sun,
    estimate_building_height,
    building_shadow,
    tree_shadow_geom,
    shaded_fraction,
    SUN_ELEV_MIN_DEG,
    DEFAULT_BUILDING_HEIGHT_M,
    DEFAULT_TREE_HEIGHT_M,
    DEFAULT_CROWN_RADIUS_M,
)

# City-specific timezones
TIMEZONES = {
    'seattle': 'America/Los_Angeles',
    'new-york-city': 'America/New_York',
}

MARGIN_DEG = 0.01   # extra bbox margin when fetching OSM data
INCLUDE_TREES = True

# New metric parameters
LOCAL_SHADE_RADIUS_25M  = 25.0   # metres  — immediate vicinity shade fraction
LOCAL_SHADE_RADIUS_50M  = 50.0   # metres  — short-detour shade fraction
ROAD_WINDOW_M           = 50.0   # metres along road from snap point for shadow_ratio_50m

# ── Pedestrian shadow ratio parameters ────────────────────────────────────────
LANE_WIDTH_M     = 3.5   # standard US lane width (AASHTO)
SIDEWALK_WIDTH_M = 2.0   # pedestrian buffer strip width on each side of carriageway

# Roads where pedestrians walk on the surface itself — use centerline shadow ratio
PEDESTRIAN_ROADS = {
    'footway', 'path', 'pedestrian', 'steps', 'track', 'living_street', 'cycleway',
}

# Default lane count by highway type when OSM `lanes` tag is absent
DEFAULT_LANES_BY_HW = {
    'motorway': 4,       'motorway_link': 2,
    'primary': 3,        'primary_link': 1,
    'secondary': 2,      'secondary_link': 1,
    'tertiary': 2,       'tertiary_link': 1,
    'residential': 2,    'unclassified': 2,
    'service': 1,
}


# ── Logging ────────────────────────────────────────────────────────────────────

def setup_logging(log_path):
    log_path.mkdir(parents=True, exist_ok=True)
    from datetime import datetime
    log_file = log_path / f'shadow_final_cities_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ]
    )
    return log_file


# ── OSM data fetching (done once) ──────────────────────────────────────────────

def fetch_osm_features(bbox_wgs, tags):
    """
    Fetch OSM features with given tags over a (west, south, east, north) bbox.
    Returns GeoDataFrame in EPSG:4326, or empty GDF on failure.
    """
    west, south, east, north = bbox_wgs
    try:
        gdf = ox.features_from_bbox(bbox=(west, south, east, north), tags=tags)
        if gdf.crs is None:
            gdf = gdf.set_crs('EPSG:4326', allow_override=True)
        return gdf.to_crs('EPSG:4326')
    except Exception as e:
        logging.warning(f'  features_from_bbox failed ({tags}): {e}')
        return gpd.GeoDataFrame(columns=['geometry'], geometry='geometry', crs='EPSG:4326')


def load_osm_data(gdf_points):
    """
    Download buildings and trees once for the full study area.
    Returns dict with 'buildings', 'trees_pt', 'trees_row' GeoDataFrames in UTM.
    """
    bounds = gdf_points.total_bounds  # [west, south, east, north]
    bbox_wgs = (
        bounds[0] - MARGIN_DEG,  # west
        bounds[1] - MARGIN_DEG,  # south
        bounds[2] + MARGIN_DEG,  # east
        bounds[3] + MARGIN_DEG,  # north
    )

    utm_crs = gdf_points.estimate_utm_crs()

    logging.info('Fetching OSM buildings ...')
    bldgs_wgs = fetch_osm_features(bbox_wgs, {'building': True})
    bldgs = bldgs_wgs[bldgs_wgs.geometry.geom_type.isin(['Polygon', 'MultiPolygon'])].copy()
    bldgs = bldgs.to_crs(utm_crs)
    bldgs['H'] = [
        estimate_building_height(row)
        for row in bldgs.drop(columns='geometry').to_dict(orient='records')
    ]
    logging.info(f'  Buildings: {len(bldgs):,}')

    trees_pt = trees_row = None
    if INCLUDE_TREES:
        logging.info('Fetching OSM trees (points) ...')
        t_wgs = fetch_osm_features(bbox_wgs, {'natural': 'tree'})
        if len(t_wgs):
            trees_pt = t_wgs.to_crs(utm_crs)
            logging.info(f'  Tree points: {len(trees_pt):,}')
        else:
            logging.info('  No tree points found.')

        logging.info('Fetching OSM tree rows ...')
        tr_wgs = fetch_osm_features(bbox_wgs, {'natural': 'tree_row'})
        if len(tr_wgs):
            trees_row = tr_wgs.to_crs(utm_crs)
            logging.info(f'  Tree rows: {len(trees_row):,}')
        else:
            logging.info('  No tree rows found.')

    return {
        'buildings': bldgs,
        'trees_pt':  trees_pt,
        'trees_row': trees_row,
        'utm_crs':   utm_crs,
    }


# ── Shadow union per date+hour ─────────────────────────────────────────────────

def compute_shadow_union(dt_utc, lat_c, lon_c, osm_data):
    """
    Compute the merged shadow polygon for a given UTC datetime.
    Also returns separate building and tree shadow unions.
    Returns (shadow_union, bldg_union, tree_union, sun_azimuth, sun_elevation).
    """
    sun_result = get_sun(dt_utc, lat_c, lon_c)
    az = sun_result['azimuth']
    elev = sun_result['elevation']

    if elev <= SUN_ELEV_MIN_DEG:
        return None, None, None, az, elev  # Sun below horizon — no shadows

    bldgs    = osm_data['buildings']
    trees_pt = osm_data['trees_pt']
    trees_row = osm_data['trees_row']

    bldg_geoms = []
    tree_geoms = []

    # Building shadows
    for row in bldgs.itertuples():
        geom = row.geometry
        try:
            geom = geom.buffer(0)
        except Exception:
            pass
        sp = building_shadow(geom, getattr(row, 'H', DEFAULT_BUILDING_HEIGHT_M), az, elev)
        if sp is not None and not sp.is_empty:
            bldg_geoms.append(sp)

    # Tree shadows
    if trees_pt is not None and len(trees_pt):
        for geom in trees_pt.geometry:
            sp = tree_shadow_geom(geom, DEFAULT_TREE_HEIGHT_M, DEFAULT_CROWN_RADIUS_M, az, elev)
            if sp is not None and not sp.is_empty:
                tree_geoms.append(sp)

    if trees_row is not None and len(trees_row):
        for geom in trees_row.geometry:
            sp = tree_shadow_geom(geom, DEFAULT_TREE_HEIGHT_M, DEFAULT_CROWN_RADIUS_M, az, elev)
            if sp is not None and not sp.is_empty:
                tree_geoms.append(sp)

    bldg_union = unary_union(bldg_geoms) if bldg_geoms else None
    tree_union = unary_union(tree_geoms) if tree_geoms else None

    all_geoms = bldg_geoms + tree_geoms
    shadow_union = unary_union(all_geoms) if all_geoms else None

    return shadow_union, bldg_union, tree_union, az, elev


# ── Solar angle relative to street bearing ────────────────────────────────────

def solar_street_angle(az_deg, road_seg):
    """
    Angle (0–90°) between the sun azimuth and the street bearing.
    90° = sun perpendicular to street (maximum cross-street shadow coverage).
    0°  = sun parallel to street (minimum coverage).
    Returns NaN if road segment is empty or too short.
    """
    try:
        coords = list(road_seg.coords)
        if len(coords) < 2:
            return math.nan
        x1, y1 = coords[0]
        x2, y2 = coords[-1]
        bearing = math.degrees(math.atan2(x2 - x1, y2 - y1)) % 360
        angle = abs(az_deg - bearing) % 180
        return min(angle, 180 - angle)   # fold to 0–90°
    except Exception:
        return math.nan


# ── Pedestrian shadow ratio helper ────────────────────────────────────────────

def _parse_first(val, cast=None):
    """Return the first element of a list/array, or the value itself."""
    if isinstance(val, (list, np.ndarray)):
        val = val[0] if len(val) > 0 else None
    if val is None:
        return None
    if cast is not None:
        try:
            return cast(val)
        except Exception:
            return None
    return val


def _strip_shade_frac(strip, shadow_union):
    """Area fraction of a polygon strip that is in shadow. Returns 0.0 if strip is empty."""
    if strip is None or strip.is_empty or strip.area == 0.0:
        return 0.0
    if shadow_union is None:
        return 0.0
    try:
        return float(np.clip(shadow_union.intersection(strip).area / strip.area, 0.0, 1.0))
    except Exception:
        return 0.0


def pedestrian_shadow_ratio_sides(seg, highway_val, lanes_val, shadow_union):
    """
    Compute per-side pedestrian shadow ratios for the zone where pedestrians walk.

    Returns (left_frac, right_frac) where left/right are the two sides of the road
    in the direction of the OSM segment geometry (start → end node).

    Pedestrian-only road types (footway, path, cycleway, etc.):
        Both sides return the same value: shaded_fraction on the centreline.
        The left/right distinction is meaningless for a footpath.

    Motorised road types (residential, primary, secondary, etc.):
        1. Estimate carriageway half-width = (n_lanes * LANE_WIDTH_M) / 2
        2. Build a sidewalk strip on each side using Shapely's single_sided buffer:
               left_strip  = buffer(+outer).difference(buffer(+half_road))
               right_strip = buffer(-outer).difference(buffer(-half_road))
           Positive offset = left of line direction; negative = right.
        3. Return area fractions of each strip that are in shadow.

    Falls back to symmetric centreline fraction on any geometry error.
    """
    hw = _parse_first(highway_val)
    if hw is None:
        hw = 'residential'

    # For pedestrian-only surfaces both sides equal the centreline fraction
    if hw in PEDESTRIAN_ROADS:
        f = shaded_fraction(seg, shadow_union)
        return f, f

    # Parse OSM lanes; fall back to type-level default
    n_lanes = _parse_first(lanes_val, cast=lambda v: int(float(str(v).strip())))
    if n_lanes is None or n_lanes < 1:
        n_lanes = DEFAULT_LANES_BY_HW.get(hw, 2)

    half_road = (n_lanes * LANE_WIDTH_M) / 2.0
    outer_buf = half_road + SIDEWALK_WIDTH_M

    try:
        left_outer  = seg.buffer( outer_buf, single_sided=True)
        left_inner  = seg.buffer( half_road, single_sided=True)
        right_outer = seg.buffer(-outer_buf, single_sided=True)
        right_inner = seg.buffer(-half_road, single_sided=True)

        left_strip  = left_outer.difference(left_inner)
        right_strip = right_outer.difference(right_inner)

        left_frac  = _strip_shade_frac(left_strip,  shadow_union)
        right_frac = _strip_shade_frac(right_strip, shadow_union)
        return left_frac, right_frac

    except Exception:
        f = shaded_fraction(seg, shadow_union)
        return f, f


# ── Per-point lookup ───────────────────────────────────────────────────────────

def lookup_points(gdf_subset, shadow_union, bldg_union, tree_union, az, elev, roads_utm):
    """
    For a GeoDataFrame of SVI points (already in UTM), return arrays of:
      in_shade           — bool: point is within shadow_union
      shadow_ratio       — float: fraction of nearest road segment in shadow
      dist_to_shade_m    — float: metres from point to nearest shadow boundary (0 if in shade)
      local_shade_25m    — float: fraction of 25m-radius circle around point in shadow
      local_shade_50m    — float: fraction of 50m-radius circle around point in shadow
      shadow_ratio_50m   — float: fraction of road within 50m of snap point in shadow
      shadow_ratio_bldg  — float: building-only shadow fraction on nearest road segment
      shadow_ratio_tree  — float: tree-only shadow fraction on nearest road segment
      solar_street_angle — float: 0–90° angle between sun and street bearing
      shadow_ratio_ped_l — float: pedestrian shadow ratio, left side of road direction
      shadow_ratio_ped_r — float: pedestrian shadow ratio, right side of road direction
                           For pedestrian-only roads both sides equal the centreline fraction.
                           Left/right follow the OSM segment direction (start→end node).
    """
    n = len(gdf_subset)
    in_shade_arr          = np.zeros(n, dtype=bool)
    shadow_ratio_arr      = np.zeros(n, dtype=float)
    dist_to_shade_arr     = np.full(n, math.nan)
    local_25m_arr         = np.zeros(n, dtype=float)
    local_50m_arr         = np.zeros(n, dtype=float)
    shadow_ratio_50m_arr  = np.zeros(n, dtype=float)
    shadow_bldg_arr       = np.zeros(n, dtype=float)
    shadow_tree_arr       = np.zeros(n, dtype=float)
    solar_angle_arr       = np.full(n, math.nan)
    shadow_ped_l_arr      = np.zeros(n, dtype=float)
    shadow_ped_r_arr      = np.zeros(n, dtype=float)

    if shadow_union is None:
        # Sun below horizon: dist_to_shade = NaN (undefined), all fractions = 0
        return (in_shade_arr, shadow_ratio_arr, dist_to_shade_arr,
                local_25m_arr, local_50m_arr, shadow_ratio_50m_arr,
                shadow_bldg_arr, shadow_tree_arr, solar_angle_arr,
                shadow_ped_l_arr, shadow_ped_r_arr)

    shadow_boundary = shadow_union.boundary

    for i, (_, row) in enumerate(gdf_subset.iterrows()):
        pt = row.geometry

        # ── in_shade ────────────────────────────────────────────────────────
        try:
            in_shade_arr[i] = bool(pt.within(shadow_union))
        except Exception:
            pass

        # ── dist_to_shade_m ─────────────────────────────────────────────────
        try:
            if in_shade_arr[i]:
                dist_to_shade_arr[i] = 0.0
            else:
                dist_to_shade_arr[i] = pt.distance(shadow_boundary)
        except Exception:
            pass

        # ── local_shade_25m and local_shade_50m ─────────────────────────────
        try:
            circ_25 = pt.buffer(LOCAL_SHADE_RADIUS_25M)
            shade_area_25 = shadow_union.intersection(circ_25).area
            local_25m_arr[i] = shade_area_25 / circ_25.area
        except Exception:
            pass

        try:
            circ_50 = pt.buffer(LOCAL_SHADE_RADIUS_50M)
            shade_area_50 = shadow_union.intersection(circ_50).area
            local_50m_arr[i] = shade_area_50 / circ_50.area
        except Exception:
            pass

        # ── road-based metrics (shadow_ratio, shadow_ratio_50m, bldg/tree, solar_angle)
        if roads_utm is not None and len(roads_utm):
            try:
                result = roads_utm.sindex.nearest(pt, return_all=False)
                tree_idx = result[1][0] if hasattr(result[1], '__len__') else result[1]
                nearest_row = roads_utm.iloc[int(tree_idx)]
                seg = nearest_row.geometry

                # shadow_ratio on full nearest segment
                shadow_ratio_arr[i]  = shaded_fraction(seg, shadow_union)
                shadow_bldg_arr[i]   = shaded_fraction(seg, bldg_union) if bldg_union is not None else 0.0
                shadow_tree_arr[i]   = shaded_fraction(seg, tree_union) if tree_union is not None else 0.0

                # shadow_ratio_ped_l / _r: per-side pedestrian sidewalk strips
                hw_val    = nearest_row.get('highway', None)
                lanes_val = nearest_row.get('lanes', None)
                shadow_ped_l_arr[i], shadow_ped_r_arr[i] = pedestrian_shadow_ratio_sides(
                    seg, hw_val, lanes_val, shadow_union
                )

                # shadow_ratio_50m: restrict segment to ±50m window around snap point
                try:
                    snap_pt = seg.interpolate(seg.project(pt))
                    window = snap_pt.buffer(ROAD_WINDOW_M)
                    seg_local = seg.intersection(window)
                    if not seg_local.is_empty and seg_local.length > 0:
                        shadow_ratio_50m_arr[i] = shaded_fraction(seg_local, shadow_union)
                    else:
                        shadow_ratio_50m_arr[i] = shadow_ratio_arr[i]
                except Exception:
                    shadow_ratio_50m_arr[i] = shadow_ratio_arr[i]

                # solar_street_angle
                solar_angle_arr[i] = solar_street_angle(az, seg)

            except Exception:
                pass

    return (in_shade_arr, shadow_ratio_arr, dist_to_shade_arr,
            local_25m_arr, local_50m_arr, shadow_ratio_50m_arr,
            shadow_bldg_arr, shadow_tree_arr, solar_angle_arr,
            shadow_ped_l_arr, shadow_ped_r_arr)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Add shadow metrics to final_run_outputs SVI data')
    parser.add_argument('--city', required=True, choices=['seattle', 'new-york-city'],
                        help='City to process')
    args = parser.parse_args()

    city = args.city
    timezone = TIMEZONES[city]

    project_root = Path(__file__).parent.parent.parent
    input_path = project_root / 'final_run_outputs' / city / f'{city}_shadow_annotated.csv'
    output_path = project_root / 'final_run_outputs' / city / f'{city}_with_shadow_metrics.csv'
    log_path = project_root / 'logs'

    log_file = setup_logging(log_path)
    logging.info('=' * 60)
    logging.info(f'{city.upper()} SHADOW ANNOTATION')
    logging.info(f'Input:  {input_path}')
    logging.info(f'Output: {output_path}')
    logging.info(f'Timezone: {timezone}')
    logging.info('=' * 60)

    # ── Load data ──────────────────────────────────────────────
    df = pd.read_csv(input_path, low_memory=False)
    logging.info(f'Loaded {len(df):,} rows')

    # Convert captured_at from milliseconds to UTC datetime
    df['captured_at_utc'] = pd.to_datetime(df['captured_at'], unit='ms', utc=True)

    # Bucket to nearest hour (UTC) for shadow deduplication
    df['_date_hour_utc'] = df['captured_at_utc'].dt.floor('h')

    gdf = gpd.GeoDataFrame(
        df, geometry=gpd.points_from_xy(df['lon'], df['lat']), crs='EPSG:4326'
    )

    # ── Fetch OSM data once ────────────────────────────────────
    osm_data = load_osm_data(gdf)
    utm_crs = osm_data['utm_crs']

    # Project SVI points to UTM
    gdf_utm = gdf.to_crs(utm_crs)
    df['_geom_utm'] = gdf_utm.geometry  # store for lookup

    # Centroid of study area (for pvlib sun position)
    bounds = gdf.total_bounds
    lat_c = (bounds[1] + bounds[3]) / 2
    lon_c = (bounds[0] + bounds[2]) / 2
    logging.info(f'Study area centroid: lat={lat_c:.4f}, lon={lon_c:.4f}')

    # Fetch road network once for road-based metrics
    logging.info('Fetching road network ...')
    try:
        margin = MARGIN_DEG
        # bounds = [west, south, east, north]
        # ox.graph_from_bbox expects (west, south, east, north) = (left, bottom, right, top)
        bbox = (bounds[0] - margin, bounds[1] - margin,
                bounds[2] + margin, bounds[3] + margin)
        G = ox.graph_from_bbox(bbox=bbox, network_type='all')
        roads_utm = ox.graph_to_gdfs(G, nodes=False).to_crs(utm_crs).reset_index(drop=True)
        logging.info(f'  Road segments: {len(roads_utm):,}')
    except Exception as e:
        logging.warning(f'  Road fetch failed: {e} — road-based metrics will be 0.0')
        roads_utm = None

    # ── Process each unique date+hour bucket ───────────────────
    unique_buckets = sorted(df['_date_hour_utc'].unique())
    logging.info(f'Unique date+hour buckets: {len(unique_buckets)}')

    # Initialise output columns
    in_shade_out         = np.full(len(df), False, dtype=bool)
    shadow_ratio_out     = np.zeros(len(df), dtype=float)
    dist_to_shade_out    = np.full(len(df), math.nan)
    local_25m_out        = np.zeros(len(df), dtype=float)
    local_50m_out        = np.zeros(len(df), dtype=float)
    shadow_ratio_50m_out = np.zeros(len(df), dtype=float)
    shadow_bldg_out      = np.zeros(len(df), dtype=float)
    shadow_tree_out      = np.zeros(len(df), dtype=float)
    solar_angle_out      = np.full(len(df), math.nan)
    shadow_ped_l_out     = np.zeros(len(df), dtype=float)
    shadow_ped_r_out     = np.zeros(len(df), dtype=float)
    sun_az_out           = np.full(len(df), math.nan)
    sun_elev_out         = np.full(len(df), math.nan)

    for i, bucket in enumerate(unique_buckets):
        mask = df['_date_hour_utc'] == bucket
        n_bucket = mask.sum()

        # Convert numpy Timestamp → Python datetime for pvlib
        dt_utc = pd.Timestamp(bucket).to_pydatetime().replace(tzinfo=dt_timezone.utc)

        shadow_union, bldg_union, tree_union, az, elev = compute_shadow_union(
            dt_utc, lat_c, lon_c, osm_data
        )

        sun_az_out[mask]   = az
        sun_elev_out[mask] = elev

        if elev > SUN_ELEV_MIN_DEG and shadow_union is not None:
            gdf_sub = gdf_utm[mask].copy()
            (in_s, sh_r, dist_s, loc25, loc50,
             sh_r50, sh_b, sh_t, sol_ang, sh_ped_l, sh_ped_r) = lookup_points(
                gdf_sub, shadow_union, bldg_union, tree_union, az, elev, roads_utm
            )
            in_shade_out[mask]         = in_s
            shadow_ratio_out[mask]     = sh_r
            dist_to_shade_out[mask]    = dist_s
            local_25m_out[mask]        = loc25
            local_50m_out[mask]        = loc50
            shadow_ratio_50m_out[mask] = sh_r50
            shadow_bldg_out[mask]      = sh_b
            shadow_tree_out[mask]      = sh_t
            solar_angle_out[mask]      = sol_ang
            shadow_ped_l_out[mask]     = sh_ped_l
            shadow_ped_r_out[mask]     = sh_ped_r
        else:
            # Below horizon: solar angle still computable (no shadow, but geometry still valid)
            if roads_utm is not None:
                gdf_sub = gdf_utm[mask].copy()
                for j, (_, row) in enumerate(gdf_sub.iterrows()):
                    pt = row.geometry
                    try:
                        result = roads_utm.sindex.nearest(pt, return_all=False)
                        tree_idx = result[1][0] if hasattr(result[1], '__len__') else result[1]
                        seg = roads_utm.iloc[int(tree_idx)].geometry
                        idx = np.where(mask)[0][j]
                        solar_angle_out[idx] = solar_street_angle(az, seg)
                    except Exception:
                        pass

        status = 'no shadow (sun below horizon)' if elev <= SUN_ELEV_MIN_DEG else \
                 f'az={az:.1f}° elev={elev:.1f}° → {in_shade_out[mask].sum()} in shade'
        logging.info(f'  [{i+1:3d}/{len(unique_buckets)}] {bucket}  n={n_bucket:>4}  {status}')

    # ── Attach results ──────────────────────────────────────────
    df['in_shade']             = in_shade_out
    df['shadow_ratio']         = np.round(shadow_ratio_out, 4)
    df['dist_to_shade_m']      = np.round(dist_to_shade_out, 2)
    df['local_shade_25m']      = np.round(local_25m_out, 4)
    df['local_shade_50m']      = np.round(local_50m_out, 4)
    df['shadow_ratio_50m']     = np.round(shadow_ratio_50m_out, 4)
    df['shadow_ratio_bldg']    = np.round(shadow_bldg_out, 4)
    df['shadow_ratio_tree']    = np.round(shadow_tree_out, 4)
    df['solar_street_angle']   = np.round(solar_angle_out, 2)
    df['shadow_ratio_ped_l']   = np.round(shadow_ped_l_out, 4)
    df['shadow_ratio_ped_r']   = np.round(shadow_ped_r_out, 4)
    df['sun_azimuth']          = np.round(sun_az_out, 2)
    df['sun_elevation']        = np.round(sun_elev_out, 2)

    # Drop temporary columns
    df = df.drop(columns=['captured_at_utc', '_date_hour_utc', '_geom_utm'])

    # ── Save ───────────────────────────────────────────────────
    df.to_csv(output_path, index=False)
    logging.info(f'Saved {len(df):,} rows → {output_path}')

    # Summary
    valid = sun_elev_out > SUN_ELEV_MIN_DEG
    logging.info('=' * 60)
    logging.info(f'Rows with sun above horizon:   {valid.sum():,} / {len(df):,}')
    logging.info(f'in_shade=True:                 {in_shade_out.sum():,}  ({in_shade_out.mean()*100:.1f}%)')
    logging.info(f'Mean shadow_ratio (all):        {shadow_ratio_out.mean():.3f}')
    logging.info(f'Mean shadow_ratio (daytime):    {shadow_ratio_out[valid].mean():.3f}')
    logging.info(f'Mean dist_to_shade (daytime):   {np.nanmean(dist_to_shade_out[valid]):.1f} m')
    logging.info(f'Mean local_shade_25m (daytime): {local_25m_out[valid].mean():.3f}')
    logging.info(f'Mean local_shade_50m (daytime): {local_50m_out[valid].mean():.3f}')
    logging.info(f'Mean shadow_ratio_bldg:         {shadow_bldg_out[valid].mean():.3f}')
    logging.info(f'Mean shadow_ratio_tree:         {shadow_tree_out[valid].mean():.3f}')
    logging.info('=' * 60)
    logging.info('Done.')


if __name__ == '__main__':
    main()
