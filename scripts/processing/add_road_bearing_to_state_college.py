# ABOUTME: Annotates State College SVI with OSM road bearing to determine camera-sidewalk alignment
# ABOUTME: Adds: road_bearing_deg, camera_road_angle_diff, camera_facing_side

import math
from pathlib import Path

import pandas as pd
import geopandas as gpd
import osmnx as ox
from tqdm import tqdm

INPUT_PATH  = Path(__file__).parent.parent.parent / 'data' / 'state-college' / 'state-college_svi_with_shadow.csv'
OUTPUT_PATH = Path(__file__).parent.parent.parent / 'data' / 'state-college' / 'state-college_svi_with_road_bearing.csv'

MARGIN_DEG = 0.01  # Extra margin for road network fetch


def get_road_bearing(geometry):
    """
    Compute bearing of road segment from start to end node (0-360°).
    0° = North, 90° = East, 180° = South, 270° = West.
    """
    try:
        coords = list(geometry.coords)
        if len(coords) < 2:
            return math.nan
        x1, y1 = coords[0]
        x2, y2 = coords[-1]
        bearing = math.degrees(math.atan2(x2 - x1, y2 - y1)) % 360
        return bearing
    except Exception:
        return math.nan


def main():
    print('=' * 70)
    print('ADD ROAD BEARING TO STATE COLLEGE SVI')
    print(f'Input:  {INPUT_PATH}')
    print(f'Output: {OUTPUT_PATH}')
    print('=' * 70)
    print()

    # Load data
    print('Loading data...')
    df = pd.read_csv(INPUT_PATH, low_memory=False)
    print(f'  Loaded {len(df):,} rows')
    print()

    # Get bounding box
    bounds = (df['lon'].min() - MARGIN_DEG, df['lat'].min() - MARGIN_DEG,
              df['lon'].max() + MARGIN_DEG, df['lat'].max() + MARGIN_DEG)
    print(f'Bounding box: ({bounds[1]:.4f}, {bounds[0]:.4f}) to ({bounds[3]:.4f}, {bounds[2]:.4f})')
    print()

    # Fetch road network
    print('Fetching OSM road network...')
    try:
        G = ox.graph_from_bbox(bbox=bounds, network_type='all')
        roads_gdf = ox.graph_to_gdfs(G, nodes=False)
        roads_gdf = roads_gdf.reset_index(drop=True)
        print(f'  Road segments: {len(roads_gdf):,}')
    except Exception as e:
        print(f'  ERROR: Failed to fetch road network: {e}')
        return

    # Project to UTM for distance calculations
    utm_crs = roads_gdf.estimate_utm_crs()
    roads_utm = roads_gdf.to_crs(utm_crs)
    print(f'  Projected to {utm_crs}')
    print()

    # Compute road bearings
    print('Computing road bearings...')
    roads_utm['bearing'] = roads_utm.geometry.apply(get_road_bearing)
    print(f'  Bearings computed for {roads_utm["bearing"].notna().sum():,} segments')
    print()

    # Convert SVI points to GeoDataFrame and project
    print('Matching images to roads...')
    gdf = gpd.GeoDataFrame(
        df, geometry=gpd.points_from_xy(df['lon'], df['lat']), crs='EPSG:4326'
    )
    gdf_utm = gdf.to_crs(utm_crs)

    # For each image, find nearest road and its bearing
    road_bearing_arr = []
    angle_diff_arr = []
    facing_side_arr = []

    for idx, row in tqdm(gdf_utm.iterrows(), total=len(gdf_utm), desc='  Processing'):
        pt = row.geometry

        try:
            # Find nearest road
            result = roads_utm.sindex.nearest(pt, return_all=False)
            tree_idx = result[1][0] if hasattr(result[1], '__len__') else result[1]
            nearest_road = roads_utm.iloc[int(tree_idx)]

            road_bearing = nearest_road['bearing']
            camera_angle = df.loc[idx, 'compass_angle']

            # Compute angle difference (shortest angular distance)
            angle_diff = abs((camera_angle - road_bearing + 180) % 360 - 180)

            # Determine which sidewalk camera faces
            # If aligned with road direction (angle_diff < 90):
            #   -> Camera follows road direction -> sees RIGHT sidewalk
            # If opposed to road direction (angle_diff >= 90):
            #   -> Camera opposes road direction -> sees LEFT sidewalk
            if angle_diff < 90:
                facing_side = 'right'
            else:
                facing_side = 'left'

            road_bearing_arr.append(road_bearing)
            angle_diff_arr.append(angle_diff)
            facing_side_arr.append(facing_side)

        except Exception:
            road_bearing_arr.append(math.nan)
            angle_diff_arr.append(math.nan)
            facing_side_arr.append('unknown')

    # Add new columns
    df['road_bearing_deg'] = road_bearing_arr
    df['camera_road_angle_diff'] = angle_diff_arr
    df['camera_facing_side'] = facing_side_arr

    print()
    print('Statistics:')
    print(f'  Roads with bearing: {df["road_bearing_deg"].notna().sum():,} / {len(df):,}')
    print(f'  Camera facing left:  {(df["camera_facing_side"] == "left").sum():,}')
    print(f'  Camera facing right: {(df["camera_facing_side"] == "right").sum():,}')
    print(f'  Unknown:             {(df["camera_facing_side"] == "unknown").sum():,}')
    print()

    # Save
    df.to_csv(OUTPUT_PATH, index=False)
    print(f'Saved {len(df):,} rows -> {OUTPUT_PATH}')
    print('Done.')


if __name__ == '__main__':
    main()
