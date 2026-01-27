# ABOUTME: Geographic sampler for travel surveys using reproducible random sampling.
# ABOUTME: Samples points within ZIP/county boundaries using GeoPandas best practices.

import geopandas as gpd
import pandas as pd
from pathlib import Path
import logging


class GeographicSampler:
    """
    Samples random geographic coordinates within ZIP codes and counties
    using reproducible seeding and GeoPandas built-in methods.

    Best practices based on:
    - GeoPandas sampling documentation
    - GIS spatial sampling literature
    - Travel survey methodology
    """

    def __init__(self, zip_shapefile, county_shapefile, state_centroids_df, base_seed=42):
        """
        Initialize sampler with shapefiles and state centroids.

        Args:
            zip_shapefile: Path to ZIP code (ZCTA) shapefile
            county_shapefile: Path to county shapefile
            state_centroids_df: DataFrame with columns: state, lat, lon
            base_seed: Base random seed for reproducibility (default: 42)
        """
        self.logger = logging.getLogger(__name__)
        self.base_seed = base_seed
        self.cache = {}

        # Load shapefiles
        self.logger.info("Loading geographic shapefiles...")
        self.zip_gdf = gpd.read_file(zip_shapefile)
        self.county_gdf = gpd.read_file(county_shapefile)
        self.state_centroids = state_centroids_df

        # Normalize ZIP codes (5 digits with leading zeros)
        if 'ZCTA5CE20' in self.zip_gdf.columns:
            self.zip_gdf['ZCTA5CE20'] = self.zip_gdf['ZCTA5CE20'].astype(str).str.zfill(5)
            self.zip_col = 'ZCTA5CE20'
        elif 'ZCTA5' in self.zip_gdf.columns:
            self.zip_gdf['ZCTA5'] = self.zip_gdf['ZCTA5'].astype(str).str.zfill(5)
            self.zip_col = 'ZCTA5'
        else:
            raise ValueError("Could not find ZIP code column in shapefile")

        # Normalize county FIPS (5 digits with leading zeros)
        if 'GEOID' in self.county_gdf.columns:
            self.county_gdf['GEOID'] = self.county_gdf['GEOID'].astype(str).str.zfill(5)
            self.county_col = 'GEOID'
        elif 'COUNTYFP' in self.county_gdf.columns:
            self.county_gdf['COUNTYFP'] = self.county_gdf['COUNTYFP'].astype(str).str.zfill(5)
            self.county_col = 'COUNTYFP'
        else:
            raise ValueError("Could not find county FIPS column in shapefile")

        # Convert state centroids to dictionary for fast lookup
        self.state_centroid_dict = self.state_centroids.set_index('state')[['lat', 'lon']].to_dict('index')

        self.logger.info(f"  Loaded {len(self.zip_gdf):,} ZIP codes")
        self.logger.info(f"  Loaded {len(self.county_gdf):,} counties")
        self.logger.info(f"  Loaded {len(self.state_centroids):,} state centroids")

    def get_location(self, zip_code=None, county_fips=None, state=None, variation_key=''):
        """
        Get geographic coordinates using best available data.

        Priority order: ZIP > County > State
        Uses variation_key to generate different points within same geography
        while maintaining reproducibility.

        Args:
            zip_code: 5-digit ZIP code string (e.g., '30301')
            county_fips: 5-digit county FIPS code string (e.g., '13121')
            state: 2-letter state code (e.g., 'GA')
            variation_key: String to vary samples (e.g., household_id)

        Returns:
            tuple: (lat, lon, source) where source is 'zip', 'county', or 'state'
            or (None, None, None) if location not found
        """
        # Try ZIP first
        if zip_code and pd.notna(zip_code):
            result = self._sample_from_zip(str(zip_code).zfill(5), variation_key)
            if result:
                return (*result, 'zip')

        # Try county second
        if county_fips and pd.notna(county_fips):
            result = self._sample_from_county(str(county_fips).zfill(5), variation_key)
            if result:
                return (*result, 'county')

        # Fall back to state centroid
        if state and pd.notna(state):
            result = self._get_state_centroid(state)
            if result:
                return (*result, 'state')

        # No valid location found
        return (None, None, None)

    def _sample_from_zip(self, zip_code, variation_key):
        """
        Sample random point within ZIP code boundary.

        Uses GeoPandas sample_points() with reproducible seeding.

        Args:
            zip_code: 5-digit ZIP code string
            variation_key: String to vary samples

        Returns:
            tuple: (lat, lon) or None if ZIP not found
        """
        cache_key = f"zip_{zip_code}_{variation_key}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Find polygon
        polygon = self.zip_gdf[self.zip_gdf[self.zip_col] == zip_code]
        if len(polygon) == 0:
            return None

        # Generate unique seed for this ZIP + variation
        seed = self.base_seed + abs(hash(cache_key)) % 100000

        # Sample point using GeoPandas
        try:
            sampled = polygon.sample_points(size=1, method='uniform', rng=seed)
            if len(sampled) == 0:
                return None

            # Extract coordinates (lon, lat from shapefile -> lat, lon for our use)
            # sample_points returns a GeoSeries of geometries (could be Point or MultiPoint)
            point_geom = sampled.iloc[0]

            if point_geom.is_empty:
                return None

            # Handle both Point and MultiPoint
            if point_geom.geom_type == 'Point':
                lon, lat = point_geom.x, point_geom.y
            elif point_geom.geom_type == 'MultiPoint':
                first_point = list(point_geom.geoms)[0]
                lon, lat = first_point.x, first_point.y
            else:
                self.logger.warning(f"Unexpected geometry type for ZIP {zip_code}: {point_geom.geom_type}")
                return None

            result = (lat, lon)

            # Cache result
            self.cache[cache_key] = result
            return result

        except Exception as e:
            self.logger.warning(f"Error sampling from ZIP {zip_code}: {e}")
            return None

    def _sample_from_county(self, county_fips, variation_key):
        """
        Sample random point within county boundary.

        Uses GeoPandas sample_points() with reproducible seeding.

        Args:
            county_fips: 5-digit county FIPS code string
            variation_key: String to vary samples

        Returns:
            tuple: (lat, lon) or None if county not found
        """
        cache_key = f"county_{county_fips}_{variation_key}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Find polygon
        polygon = self.county_gdf[self.county_gdf[self.county_col] == county_fips]
        if len(polygon) == 0:
            return None

        # Generate unique seed for this county + variation
        seed = self.base_seed + abs(hash(cache_key)) % 100000

        # Sample point using GeoPandas
        try:
            sampled = polygon.sample_points(size=1, method='uniform', rng=seed)
            if len(sampled) == 0:
                return None

            # Extract coordinates (lon, lat from shapefile -> lat, lon for our use)
            # sample_points returns a GeoSeries of geometries (could be Point or MultiPoint)
            point_geom = sampled.iloc[0]

            if point_geom.is_empty:
                return None

            # Handle both Point and MultiPoint
            if point_geom.geom_type == 'Point':
                lon, lat = point_geom.x, point_geom.y
            elif point_geom.geom_type == 'MultiPoint':
                first_point = list(point_geom.geoms)[0]
                lon, lat = first_point.x, first_point.y
            else:
                self.logger.warning(f"Unexpected geometry type for county {county_fips}: {point_geom.geom_type}")
                return None

            result = (lat, lon)

            # Cache result
            self.cache[cache_key] = result
            return result

        except Exception as e:
            self.logger.warning(f"Error sampling from county {county_fips}: {e}")
            return None

    def _get_state_centroid(self, state):
        """
        Get state centroid as fallback.

        Args:
            state: 2-letter state code

        Returns:
            tuple: (lat, lon) or None if state not found
        """
        state = state.upper()
        if state in self.state_centroid_dict:
            centroid = self.state_centroid_dict[state]
            return (centroid['lat'], centroid['lon'])
        return None

    def get_cache_stats(self):
        """
        Get cache statistics for performance monitoring.

        Returns:
            dict: Cache statistics
        """
        zip_cached = sum(1 for k in self.cache.keys() if k.startswith('zip_'))
        county_cached = sum(1 for k in self.cache.keys() if k.startswith('county_'))

        return {
            'total_cached': len(self.cache),
            'zip_cached': zip_cached,
            'county_cached': county_cached
        }


def test_sampler():
    """
    Test the geographic sampler with sample data.
    """
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    project_root = Path(__file__).parent.parent.parent

    # Setup paths
    zip_shapefile = project_root / "data" / "geographic_shapefiles" / "zcta" / "tl_2023_us_zcta520.shp"
    county_shapefile = project_root / "data" / "geographic_shapefiles" / "counties" / "cb_2023_us_county_500k.shp"

    # Create sample state centroids
    state_centroids = pd.DataFrame([
        {'state': 'GA', 'lat': 32.6781, 'lon': -83.2238},
        {'state': 'CA', 'lat': 37.2727, 'lon': -119.2712},
    ])

    # Initialize sampler
    sampler = GeographicSampler(
        zip_shapefile=zip_shapefile,
        county_shapefile=county_shapefile,
        state_centroids_df=state_centroids,
        base_seed=42
    )

    # Test cases
    logger.info("\n" + "="*60)
    logger.info("Testing Geographic Sampler")
    logger.info("="*60)

    # Test 1: ZIP code (Atlanta)
    lat, lon, source = sampler.get_location(zip_code='30309', variation_key='household_1')
    logger.info(f"\nTest 1 - ZIP 30309 (Atlanta):")
    if lat is not None:
        logger.info(f"  Result: ({lat:.6f}, {lon:.6f}) from {source}")
    else:
        logger.info(f"  Result: Not found")

    # Test 2: Same ZIP, different variation
    lat2, lon2, source2 = sampler.get_location(zip_code='30309', variation_key='household_2')
    logger.info(f"\nTest 2 - ZIP 30309 (different household):")
    if lat2 is not None:
        logger.info(f"  Result: ({lat2:.6f}, {lon2:.6f}) from {source2}")
        if lat is not None:
            distance_deg = ((lat2 - lat)**2 + (lon2 - lon)**2)**0.5
            logger.info(f"  Distance from Test 1: {distance_deg:.6f} degrees")
    else:
        logger.info(f"  Result: Not found")

    # Test 3: County (Fulton County, GA)
    lat, lon, source = sampler.get_location(county_fips='13121', variation_key='household_3')
    logger.info(f"\nTest 3 - County 13121 (Fulton, GA):")
    if lat is not None:
        logger.info(f"  Result: ({lat:.6f}, {lon:.6f}) from {source}")
    else:
        logger.info(f"  Result: Not found")

    # Test 4: State fallback
    lat, lon, source = sampler.get_location(state='CA', variation_key='household_4')
    logger.info(f"\nTest 4 - State CA (fallback):")
    if lat is not None:
        logger.info(f"  Result: ({lat:.6f}, {lon:.6f}) from {source}")
    else:
        logger.info(f"  Result: Not found")

    # Cache stats
    logger.info("\n" + "="*60)
    logger.info("Cache Statistics:")
    stats = sampler.get_cache_stats()
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")
    logger.info("="*60)


if __name__ == '__main__':
    test_sampler()
