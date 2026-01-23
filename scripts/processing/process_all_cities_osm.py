#!/usr/bin/env python3
# ABOUTME: Processes all city CSVs to snap images to OSM roads and extract road classifications
# ABOUTME: Creates snapped CSVs with road type info for filtering walkable streets

import osmnx as ox
import pandas as pd
import geopandas as gp
import numpy as np
import os
from pathlib import Path
from tqdm import tqdm

# City center coordinates (used for OSM download)
CITY_COORDS = {
    '1032717330': {'name': 'Buenos Aires', 'lat': -34.5997, 'lon': -58.3819},
    '1710680650': {'name': 'Cape Town', 'lat': -33.9249, 'lon': 18.4241},
    '1792756324': {'name': 'Istanbul', 'lat': 41.0082, 'lon': 28.9784},
    '1724616994': {'name': 'Madrid', 'lat': 40.4168, 'lon': -3.7038},
    '1356226629': {'name': 'Mumbai', 'lat': 19.0760, 'lon': 72.8777},
    '1702341327': {'name': 'Singapore', 'lat': 1.3521, 'lon': 103.8198},
    '1392685764': {'name': 'Tokyo', 'lat': 35.6762, 'lon': 139.6503}
}

def snap_photos_to_roads(points, roads, tolerance):
    """
    Snap street view points to nearest roads within tolerance.

    inputs:
        points = GeoDataFrame of points to be snapped
        roads = GeoDataFrame of lines where points are to be snapped to
        tolerance = only if a point is within this distance (meters) of a line, it will be snapped to the line
    output:
        a GeoDataFrame of snapped points with road attributes
    """

    points_bbox = points.bounds + [-tolerance, -tolerance, tolerance, tolerance]

    hits = points_bbox.apply(lambda row: list(roads.sindex.intersection(row)), axis=1)

    tmp = pd.DataFrame({
        "pt_idx": np.repeat(hits.index, hits.apply(len)),
        "line_i": np.concatenate(hits.values)
    })

    if tmp.empty:
        empty_df = gp.GeoDataFrame(columns=['geometry'], geometry='geometry')
        return empty_df

    else:
        roads_2 = roads.rename(columns={"width": "road_width"})
        tmp = tmp.join(roads_2.reset_index(drop=True), on="line_i")

        points_2 = points.rename(columns={"geometry": "og_point"})
        tmp = tmp.join(points_2, on="pt_idx")

        tmp = gp.GeoDataFrame(tmp, geometry="geometry", crs=points.crs)

        tmp["snap_dist"] = tmp.geometry.distance(gp.GeoSeries(tmp['og_point']))

        tmp = tmp.loc[tmp.snap_dist <= tolerance]

        tmp = tmp.sort_values(by=["snap_dist"])

        closest = tmp.groupby("pt_idx").first()

        closest = gp.GeoDataFrame(closest, geometry="geometry", crs=points.crs)

        pos = closest.geometry.project(gp.GeoSeries(closest['og_point']))

        snapped_pts = closest.geometry.interpolate(pos)

        closest_2 = closest.rename(columns={"geometry": "line_geometry"})

        snapped = gp.GeoDataFrame(closest_2, geometry=snapped_pts).reset_index()

        return snapped

def append_road_info(city_id, images, snap_tolerance, save_folder, save_folder_osm):
    """Process a single city to get OSM road data and snap images."""

    city_info = CITY_COORDS.get(str(city_id))
    if not city_info:
        print(f"  ERROR: No coordinates found for city_id {city_id}")
        return False

    city_name = city_info['name']
    print(f"\nProcessing {city_name} (ID: {city_id})")

    # Convert city_id to int for comparison
    points = images[images['city_id'] == int(city_id)]
    print(f"  Images to process: {len(points)}")

    location = (city_info['lat'], city_info['lon'])

    print(f"  Downloading OSM road network from {location}...")
    try:
        G = ox.graph_from_point(location, dist=5000, network_type='all')  # 5km from city center
        G = ox.convert.to_undirected(G)
        df_G = ox.graph_to_gdfs(G)[1]  # Get edges (roads)
    except Exception as e:
        print(f"  ERROR downloading OSM data: {e}")
        return False

    print(f"  Downloaded {len(df_G)} road segments")

    roads = df_G.reset_index().reset_index()
    roads_proj = ox.projection.project_gdf(df_G).reset_index().reset_index()
    roads['geometry_wkt'] = roads['geometry'].to_wkt()
    roads_proj['geometry_wkt'] = roads_proj['geometry'].to_wkt()

    # Save OSM road data
    save_path1 = os.path.join(save_folder_osm, f'{city_name.replace(" ", "-")}_osm.csv')
    save_path2 = os.path.join(save_folder_osm, f'{city_name.replace(" ", "-")}_osm_proj.csv')
    roads.drop(columns=['geometry']).to_csv(save_path1, index=False)
    roads_proj.drop(columns=['geometry']).to_csv(save_path2, index=False)
    print(f"  Saved OSM road data")

    # Snap images to roads
    print(f"  Snapping images to roads...")
    points_proj = ox.projection.project_gdf(points)
    snapped = snap_photos_to_roads(points_proj, roads_proj, snap_tolerance)

    if snapped.empty:
        print(f"  WARNING: No images within {snap_tolerance}m of any roads")
        return False
    else:
        print(f"  Successfully snapped {len(snapped)} images to roads")
        snapped['l_geom_wkt'] = snapped['line_geometry'].to_wkt()
        snapped['og_pt_wkt'] = snapped['og_point'].to_wkt()
        snapped['snp_pt_wkt'] = snapped['geometry'].to_wkt()
        save_path = os.path.join(save_folder, f'{city_name.replace(" ", "-")}_snapped.csv')
        pd.DataFrame(snapped.drop(columns=['geometry', 'line_geometry', 'og_point'])).to_csv(save_path, index=False)
        print(f"  Saved snapped data to {save_path}")
        return True

def check_processed_cities(save_folder):
    """Check which cities have already been processed."""
    processed = set()
    if not os.path.exists(save_folder):
        return processed

    for name in os.listdir(save_folder):
        if name.endswith('_snapped.csv'):
            city_name = name.replace('_snapped.csv', '').replace('-', ' ')
            # Find matching city_id
            for city_id, info in CITY_COORDS.items():
                if info['name'] == city_name:
                    processed.add(city_id)
                    break
    return processed

def main():
    """Process all city CSVs to snap images to OSM roads."""

    print("="*60)
    print("OSM Road Snapping for All Cities")
    print("="*60)

    base_dir = Path('/home/kieran/Documents/Python/sunny_day_SVI/city7sample')
    save_folder = base_dir / 'snapped'
    save_folder_osm = base_dir / 'osm'

    save_folder.mkdir(parents=True, exist_ok=True)
    save_folder_osm.mkdir(parents=True, exist_ok=True)

    # Load all city CSVs
    print("\nLoading city CSV files...")
    all_images = []
    for city_id, info in CITY_COORDS.items():
        csv_path = base_dir / f"{info['name'].replace(' ', '-')}_{city_id}.csv"
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            df['city_id'] = int(city_id)  # Ensure city_id is set
            all_images.append(df)
            print(f"  Loaded {info['name']}: {len(df)} rows")
        else:
            print(f"  WARNING: {csv_path} not found")

    if not all_images:
        print("ERROR: No city CSV files found")
        return

    images_df = pd.concat(all_images, ignore_index=True)
    print(f"\nTotal images loaded: {len(images_df)}")

    # Convert to GeoDataFrame
    images = gp.GeoDataFrame(
        images_df, geometry=gp.points_from_xy(images_df.lon, images_df.lat), crs=4326
    )

    snap_tolerance = 10  # meters
    already_processed = check_processed_cities(save_folder)

    print(f"\nCities already processed: {len(already_processed)}")
    print(f"Cities to process: {len(CITY_COORDS) - len(already_processed)}")

    success_count = 0
    error_count = 0
    skip_count = 0

    for city_id in CITY_COORDS.keys():
        if city_id in already_processed:
            print(f"\n✓ {CITY_COORDS[city_id]['name']} - Already processed, skipping")
            skip_count += 1
            continue

        try:
            success = append_road_info(city_id, images, snap_tolerance, save_folder, save_folder_osm)
            if success:
                success_count += 1
            else:
                error_count += 1
        except Exception as e:
            print(f"\n✗ ERROR processing {CITY_COORDS[city_id]['name']}:")
            print(f"  {type(e).__name__}: {str(e)}")
            error_count += 1

    print("\n" + "="*60)
    print("Processing Complete!")
    print("="*60)
    print(f"Success: {success_count}")
    print(f"Skipped (already done): {skip_count}")
    print(f"Errors: {error_count}")
    print()

if __name__ == '__main__':
    main()
