#!/usr/bin/env python3
# ABOUTME: Processes hot cities CSVs to snap images to OSM roads and extract road classifications
# ABOUTME: Creates snapped CSVs with road type info for filtering walkable streets

import osmnx as ox
import pandas as pd
import geopandas as gp
import numpy as np
import os
from pathlib import Path
from tqdm import tqdm
import glob

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

def append_road_info(city_name, city_lat, city_lon, images, snap_tolerance, save_folder, save_folder_osm):
    """Process a single city to get OSM road data and snap images."""

    print(f"\nProcessing {city_name}")
    print(f"  Location: ({city_lat:.4f}, {city_lon:.4f})")
    print(f"  Images to process: {len(images)}")

    print(f"  Downloading OSM road network...")
    try:
        G = ox.graph_from_point((city_lat, city_lon), dist=5000, network_type='all')  # 5km from city center
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
    save_path1 = os.path.join(save_folder_osm, f'{city_name}_osm.csv')
    save_path2 = os.path.join(save_folder_osm, f'{city_name}_osm_proj.csv')
    roads.drop(columns=['geometry']).to_csv(save_path1, index=False)
    roads_proj.drop(columns=['geometry']).to_csv(save_path2, index=False)
    print(f"  Saved OSM road data")

    # Snap images to roads
    print(f"  Snapping images to roads...")
    points_proj = ox.projection.project_gdf(images)
    snapped = snap_photos_to_roads(points_proj, roads_proj, snap_tolerance)

    if snapped.empty:
        print(f"  WARNING: No images within {snap_tolerance}m of any roads")
        return False
    else:
        print(f"  Successfully snapped {len(snapped)} images to roads")
        snapped['l_geom_wkt'] = snapped['line_geometry'].to_wkt()
        snapped['og_pt_wkt'] = snapped['og_point'].to_wkt()
        snapped['snp_pt_wkt'] = snapped['geometry'].to_wkt()
        save_path = os.path.join(save_folder, f'{city_name}_snapped.csv')
        pd.DataFrame(snapped.drop(columns=['geometry', 'line_geometry', 'og_point'])).to_csv(save_path, index=False)
        print(f"  Saved snapped data")
        return True

def check_processed_cities(save_folder):
    """Check which cities have already been processed."""
    processed = set()
    if not os.path.exists(save_folder):
        return processed

    for name in os.listdir(save_folder):
        if name.endswith('_snapped.csv'):
            city_name = name.replace('_snapped.csv', '')
            processed.add(city_name)
    return processed

def main():
    """Process all hot cities CSVs to snap images to OSM roads."""

    print("="*80)
    print("OSM Road Snapping for Hot Cities")
    print("="*80)

    base_dir = Path('/home/kieran/Documents/Python/sunny_day_SVI/hot_cities')
    save_folder = base_dir / 'snapped'
    save_folder_osm = base_dir / 'osm'

    save_folder.mkdir(parents=True, exist_ok=True)
    save_folder_osm.mkdir(parents=True, exist_ok=True)

    # Load city matched data to get coordinates
    matched_cities = pd.read_csv('/home/kieran/Documents/Python/sunny_day_SVI/hot_cities_matched.csv')
    print(f"\nFound {len(matched_cities)} hot cities")

    # Get all CSV files
    csv_files = sorted(glob.glob(str(base_dir / '*.csv')))
    print(f"Found {len(csv_files)} CSV files")

    snap_tolerance = 10  # meters
    already_processed = check_processed_cities(save_folder)

    print(f"\nCities already processed: {len(already_processed)}")
    print(f"Cities to process: {len(csv_files) - len(already_processed)}")
    print("="*80)

    success_count = 0
    error_count = 0
    skip_count = 0

    for csv_file in csv_files:
        try:
            # Extract city name and ID from filename
            filename = os.path.basename(csv_file)
            city_name = filename.rsplit('_', 1)[0]
            city_id = filename.rsplit('_', 1)[1].replace('.csv', '')

            if city_name in already_processed:
                print(f"\n✓ {city_name} - Already processed, skipping")
                skip_count += 1
                continue

            # Get city coordinates from matched data
            city_info = matched_cities[matched_cities['id'] == int(city_id)]
            if city_info.empty:
                print(f"\n✗ {city_name} - No coordinates found in matched data")
                error_count += 1
                continue

            city_lat = city_info.iloc[0]['lat']
            city_lon = city_info.iloc[0]['lng']

            # Load images
            df = pd.read_csv(csv_file)
            print(f"\nLoaded {city_name}: {len(df)} images")

            # Convert to GeoDataFrame
            images = gp.GeoDataFrame(
                df, geometry=gp.points_from_xy(df.lon, df.lat), crs=4326
            )

            # Process city
            success = append_road_info(city_name, city_lat, city_lon, images,
                                      snap_tolerance, save_folder, save_folder_osm)
            if success:
                success_count += 1
                print(f"  ✓ {city_name} complete")
            else:
                error_count += 1
                print(f"  ✗ {city_name} failed")

        except Exception as e:
            print(f"\n✗ ERROR processing {filename}:")
            print(f"  {type(e).__name__}: {str(e)}")
            error_count += 1

    print("\n" + "="*80)
    print("Processing Complete!")
    print("="*80)
    print(f"Success: {success_count}")
    print(f"Skipped (already done): {skip_count}")
    print(f"Errors: {error_count}")
    print()

if __name__ == '__main__':
    main()
