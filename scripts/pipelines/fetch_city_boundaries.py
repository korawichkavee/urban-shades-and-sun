# ABOUTME: Fetches and caches city administrative boundaries from OpenStreetMap
# ABOUTME: Uses OSMnx to get actual municipal polygons for accurate SVI coverage

import osmnx as ox
import geopandas as gpd
from pathlib import Path
import json
import logging

# Cache directory for boundaries
BOUNDARY_CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "city_boundaries"
BOUNDARY_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_city_boundary(city_name, state=None, country="USA"):
    """
    Fetch city administrative boundary from OpenStreetMap.

    Args:
        city_name: Name of the city (e.g., "Boston", "Los Angeles")
        state: State abbreviation (e.g., "MA", "CA") - helps disambiguate
        country: Country name (default: "USA")

    Returns:
        GeoDataFrame with city boundary polygon, or None if not found
    """
    # Create cache filename
    cache_name = f"{city_name.lower().replace(' ', '_')}_{state or 'unknown'}.geojson"
    cache_path = BOUNDARY_CACHE_DIR / cache_name

    # Check cache first
    if cache_path.exists():
        logging.info(f"  Loading cached boundary for {city_name}")
        return gpd.read_file(cache_path)

    # Try to fetch from OSM
    try:
        # Build query string
        if state:
            query = f"{city_name}, {state}, {country}"
        else:
            query = f"{city_name}, {country}"

        logging.info(f"  Fetching boundary from OSM: {query}")

        # Fetch the boundary
        # which_result: 1 = first result (usually the city proper)
        gdf = ox.geocode_to_gdf(query, which_result=1)

        # Save to cache
        gdf.to_file(cache_path, driver='GeoJSON')
        logging.info(f"  ✓ Cached boundary for {city_name}")

        return gdf

    except Exception as e:
        logging.warning(f"  Could not fetch boundary for {city_name}: {e}")
        logging.warning(f"  Will fall back to bounding box approach")
        return None


def boundary_to_bbox(gdf):
    """
    Convert boundary GeoDataFrame to bounding box.

    Args:
        gdf: GeoDataFrame with boundary polygon

    Returns:
        Dict with keys: west, south, east, north
    """
    bounds = gdf.total_bounds  # minx, miny, maxx, maxy
    return {
        'west': bounds[0],
        'south': bounds[1],
        'east': bounds[2],
        'north': bounds[3]
    }


def get_city_bbox(city_config):
    """
    Get bounding box for a city, preferring actual boundary over radius.

    Args:
        city_config: Dict with keys: name, state, lat, lon

    Returns:
        Dict with bbox (west, south, east, north) and boundary GeoDataFrame if available
    """
    # Try to get actual boundary
    boundary_gdf = get_city_boundary(
        city_config['name'],
        city_config.get('state'),
        city_config.get('country', 'USA')
    )

    if boundary_gdf is not None:
        bbox = boundary_to_bbox(boundary_gdf)
        return {
            'bbox': bbox,
            'boundary': boundary_gdf,
            'method': 'osm_boundary'
        }

    # Fallback to radius-based bbox
    bbox_size = 0.15  # ~10km radius
    bbox = {
        'west': city_config['lon'] - bbox_size,
        'south': city_config['lat'] - bbox_size,
        'east': city_config['lon'] + bbox_size,
        'north': city_config['lat'] + bbox_size
    }

    return {
        'bbox': bbox,
        'boundary': None,
        'method': 'radius_fallback'
    }


if __name__ == "__main__":
    # Test with a few cities
    logging.basicConfig(level=logging.INFO)

    test_cities = [
        {"name": "Boston", "state": "MA", "lat": 42.32, "lon": -71.08},
        {"name": "Los Angeles", "state": "CA", "lat": 34.11, "lon": -118.41},
        {"name": "Seattle", "state": "WA", "lat": 47.62, "lon": -122.32},
    ]

    for city in test_cities:
        print(f"\n{'='*60}")
        print(f"Testing: {city['name']}, {city['state']}")
        print(f"{'='*60}")

        result = get_city_bbox(city)
        bbox = result['bbox']

        print(f"Method: {result['method']}")
        print(f"Bounding box:")
        print(f"  West: {bbox['west']:.4f}")
        print(f"  South: {bbox['south']:.4f}")
        print(f"  East: {bbox['east']:.4f}")
        print(f"  North: {bbox['north']:.4f}")

        if result['boundary'] is not None:
            area_km2 = result['boundary'].to_crs(epsg=3857).area.sum() / 1e6
            print(f"  Area: {area_km2:.2f} km²")
