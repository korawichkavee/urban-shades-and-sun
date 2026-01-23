# ABOUTME: Streamlined script to fetch street view images from Mapillary and KartaView with metadata
# ABOUTME: Filters images by local time (8-10am or 4-6pm) using automatic timezone detection

"""
Fetches street view image metadata from Mapillary and KartaView for specified cities.
Filters images to only those taken during 8-10am or 4-6pm local time.

Input: YAML config file specifying cities to process
Output: CSV files with filtered SVI metadata including datetime and location
"""

import mapillary.interface as mly
import requests
import mpmath as mp
import math
import pandas as pd
import geopandas as gp
import os
import yaml
import datetime
from pathlib import Path
from timezonefinder import TimezoneFinder
from zoneinfo import ZoneInfo
import argparse
import sys


class SVIFetcher:
    """Fetches and filters street view images from multiple sources."""

    def __init__(self, mapillary_token=None):
        self.mapillary_token = mapillary_token
        if mapillary_token:
            mly.set_access_token(mapillary_token)
        self.tf = TimezoneFinder()

    def get_city_timezone(self, lat, lon):
        """Get timezone for a city based on coordinates."""
        tz_name = self.tf.timezone_at(lat=lat, lng=lon)
        if tz_name is None:
            raise ValueError(f"Could not determine timezone for coordinates {lat}, {lon}")
        return ZoneInfo(tz_name)

    def filter_by_time_of_day(self, df, lat, lon, source='mapillary'):
        """
        Filter dataframe to only include images taken during 8-10am or 4-6pm local time.

        Args:
            df: DataFrame with datetime column
            lat: City latitude for timezone detection
            lon: City longitude for timezone detection
            source: 'mapillary' or 'kartaview' to determine datetime column

        Returns:
            Filtered DataFrame
        """
        if df.empty:
            return df

        print(f'  Total points before time filtering: {len(df)}', flush=True)

        # Get city timezone
        city_tz = self.get_city_timezone(lat, lon)

        # Convert timestamps to local time using vectorized operations
        if source == 'mapillary':
            # Mapillary uses 'captured_at' in milliseconds from Unix epoch
            df['datetime_utc'] = pd.to_datetime(df['captured_at'], unit='ms')
        elif source == 'kartaview':
            # KartaView uses 'shotDate' in format '%Y-%m-%d %H:%M:%S' (assumed UTC)
            df['shotDate'] = df['shotDate'].str.replace(r'\.000$', '', regex=True)
            df['datetime_utc'] = pd.to_datetime(df['shotDate'], format='%Y-%m-%d %H:%M:%S')

        # Convert to local time
        df['datetime_local'] = df['datetime_utc'].dt.tz_localize('UTC').dt.tz_convert(city_tz)

        # Extract hour
        df['hour'] = df['datetime_local'].dt.hour

        # Filter for 8-10am (hour 8 or 9) or 4-6pm (hour 16 or 17)
        morning_mask = (df['hour'] >= 8) & (df['hour'] < 10)
        evening_mask = (df['hour'] >= 16) & (df['hour'] < 18)
        df_filtered = df[morning_mask | evening_mask].copy()

        # Drop temporary columns but keep datetime_local for reference
        df_filtered = df_filtered.drop(columns=['hour', 'datetime_utc'])

        print(f'  Points after time filtering (8-10am or 4-6pm): {len(df_filtered)}', flush=True)

        return df_filtered

    def fetch_mapillary_data(self, city, start_date=None, end_date=None):
        """
        Fetch Mapillary data for a city.

        Args:
            city: Dict with 'city', 'lat', 'lng', 'id' keys
            start_date: Optional start date string 'YYYY-MM-DD'
            end_date: Optional end date string 'YYYY-MM-DD'

        Returns:
            GeoDataFrame with Mapillary data
        """
        cityname = city['city']
        print(f'Fetching Mapillary data for {cityname}...', flush=True)
        lon = city['lng']
        lat = city['lat']

        try:
            data = mly.get_image_close_to(longitude=lon, latitude=lat)
            dict_data = data.to_dict()
            gdf = gp.GeoDataFrame.from_features(dict_data)

            if not gdf.empty:
                # Apply date filtering if specified
                if start_date or end_date:
                    print(f'Filtering data for date range {start_date} to {end_date}...', flush=True)
                    gdf = self._filter_date_mapillary(gdf, start_date, end_date)

                # Apply time-of-day filtering
                print(f'Filtering data for 8-10am and 4-6pm local time...', flush=True)
                gdf = self.filter_by_time_of_day(gdf, lat, lon, source='mapillary')

                if not gdf.empty:
                    gdf['city_id'] = city['id']
                    gdf['lat'] = gdf.geometry.y
                    gdf['lon'] = gdf.geometry.x
                    gdf['source'] = 'Mapillary'
                    nSeqs = gdf['sequence_id'].nunique()
                    print(f'Mapillary: Collected {nSeqs} sequences, {len(gdf)} points', flush=True)
                else:
                    print(f'No Mapillary data found in target time windows for {cityname}', flush=True)

            return gdf
        except Exception as e:
            print(f'Error fetching Mapillary data: {e}', flush=True)
            import traceback
            traceback.print_exc()
            return gp.GeoDataFrame()

    def _filter_date_mapillary(self, df, start_date, end_date):
        """Filter Mapillary data by date range."""
        df["date"] = pd.to_datetime(df["captured_at"], unit="ms")

        if start_date is not None:
            try:
                start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
                df = df[df["date"] >= start_date]
            except ValueError:
                raise ValueError("Incorrect start_date format, should be YYYY-MM-DD")

        if end_date is not None:
            try:
                end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")
                df = df[df["date"] <= end_date]
            except ValueError:
                raise ValueError("Incorrect end_date format, should be YYYY-MM-DD")

        df = df.drop(columns="date")
        return df


def load_config(config_path):
    """Load YAML configuration file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def get_cities_from_config(config, worldcities_path):
    """
    Get city information from config and worldcities database.

    Args:
        config: Dict with 'cities' list containing city names or IDs
        worldcities_path: Path to worldcities.csv

    Returns:
        DataFrame with city information
    """
    wc = pd.read_csv(worldcities_path)

    cities_to_fetch = config['cities']
    city_ids = []

    for city_spec in cities_to_fetch:
        if isinstance(city_spec, int):
            # Direct city ID
            city_ids.append(city_spec)
        elif isinstance(city_spec, dict):
            # Lookup by name and country
            city_name = city_spec.get('name')
            country = city_spec.get('country')

            query = wc['city'] == city_name
            if country:
                query = query & (wc['country'] == country)

            matches = wc[query]
            if matches.empty:
                print(f"Warning: City '{city_name}' in '{country}' not found in worldcities database", flush=True)
            else:
                city_ids.extend(matches['id'].tolist())

    return wc[wc['id'].isin(city_ids)]


def main():
    parser = argparse.ArgumentParser(
        description='Fetch street view images with time filtering (8-10am, 4-6pm local time)'
    )
    parser.add_argument('config', help='Path to YAML config file')
    parser.add_argument('--mapillary-token', help='Mapillary API access token (or set in config)')
    parser.add_argument('--worldcities', default='data/raw/worldcities.csv',
                       help='Path to worldcities.csv database')

    args = parser.parse_args()

    # Load config
    config = load_config(args.config)

    # Get Mapillary token
    mapillary_token = args.mapillary_token or config.get('mapillary_token')
    if not mapillary_token:
        print("Warning: No Mapillary token provided. Mapillary data will not be fetched.", flush=True)

    # Setup paths
    worldcities_path = Path(args.worldcities)
    if not worldcities_path.is_absolute():
        # Make relative to script location
        script_dir = Path(__file__).parent.parent.parent
        worldcities_path = script_dir / worldcities_path

    output_dir = Path(config.get('output_dir', 'data/raw/svi_filtered'))
    if not output_dir.is_absolute():
        script_dir = Path(__file__).parent.parent.parent
        output_dir = script_dir / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get cities to process
    cities = get_cities_from_config(config, worldcities_path)

    if cities.empty:
        print("No cities found to process!", flush=True)
        return

    print(f"\nProcessing {len(cities)} cities:", flush=True)
    for _, city in cities.iterrows():
        print(f"  - {city['city']}, {city['country']} (ID: {city['id']})", flush=True)
    print("", flush=True)

    # Initialize fetcher
    fetcher = SVIFetcher(mapillary_token=mapillary_token)

    # Get date range from config
    start_date = config.get('start_date')
    end_date = config.get('end_date')

    # Get sources to fetch
    sources = config.get('sources', ['mapillary', 'kartaview'])
    fetch_mapillary = 'mapillary' in sources and mapillary_token

    # Process each city
    for idx, (_, city) in enumerate(cities.iterrows(), 1):
        print(f"\n{'='*60}", flush=True)
        print(f"Processing {idx}/{len(cities)}: {city['city']}, {city['country']}", flush=True)
        print(f"{'='*60}", flush=True)

        all_data = []

        # Fetch Mapillary data
        if fetch_mapillary:
            try:
                mly_data = fetcher.fetch_mapillary_data(city, start_date, end_date)
                if not mly_data.empty:
                    # Convert to regular DataFrame (drop geometry)
                    mly_df = pd.DataFrame(mly_data.drop(columns='geometry', errors='ignore'))
                    all_data.append(mly_df)
            except Exception as e:
                print(f"Error fetching Mapillary data: {e}", flush=True)
                import traceback
                traceback.print_exc()

        # Combine and save
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)

            # Save to CSV
            filename = city['city_ascii'].replace(" ", "-") + '_' + str(city['id']) + '.csv'
            output_path = output_dir / filename
            combined_df.to_csv(output_path, index=False)

            print(f"\nSaved {len(combined_df)} filtered points to {output_path}", flush=True)
        else:
            print(f"\nNo data collected for {city['city']}", flush=True)

    print(f"\n{'='*60}", flush=True)
    print("Processing complete!", flush=True)
    print(f"{'='*60}", flush=True)


if __name__ == '__main__':
    main()
