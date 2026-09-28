#!/usr/bin/env python3
# ABOUTME: Annotates household travel survey trip data with UTCI (Universal Thermal Climate Index)
# ABOUTME: Fetches historical weather data and computes thermal comfort metrics for trip dates/times

from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
from typing import Optional, Tuple
import logging
from pythermalcomfort.models import utci as compute_utci_proper

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Paths
ROOT = Path(__file__).resolve().parents[2]
FINAL_CITIES = ROOT / 'final_cities'
OUTPUT_DIR = ROOT / 'outputs/analysis'

# City configurations with weather station info
CITY_CONFIGS = {
    'seattle': {
        'trip_file': FINAL_CITIES / 'Puget sound' / 'Household_Travel_Survey_Trips_8962432402648352214.csv',
        'date_col': 'travel_date',
        'time_cols': ('depart_time_hour', 'depart_time_minute'),
        'lat': 47.6062,
        'lon': -122.3321,
        'timezone': 'America/Los_Angeles',
        'mode_col': 'mode_1',
        'walk_values': ['Walk (or jog/wheelchair)'],
    },
    'nyc': {
        'trip_file': FINAL_CITIES / 'NYC' / 'Citywide_Mobility_Survey_-_Trip_2022_20260313.csv',
        'date_col': 'depart_date',
        'time_cols': ('depart_hour', 'depart_minute'),
        'lat': 40.7128,
        'lon': -74.0060,
        'timezone': 'America/New_York',
        'mode_col': 'mode_type_nyc',
        'walk_values': [9],  # Walk mode code
    },
}


def fetch_open_meteo_weather(lat: float, lon: float, date: str) -> Optional[dict]:
    """
    Fetch hourly weather data from Open-Meteo API for a specific date.

    Args:
        lat: Latitude
        lon: Longitude
        date: Date string in YYYY-MM-DD format

    Returns:
        Dictionary with hourly weather data or None if failed
    """
    # Open-Meteo historical weather API
    url = "https://archive-api.open-meteo.com/v1/archive"

    params = {
        'latitude': lat,
        'longitude': lon,
        'start_date': date,
        'end_date': date,
        'hourly': [
            'temperature_2m',
            'relative_humidity_2m',
            'wind_speed_10m',
            'surface_pressure',
            'shortwave_radiation',
        ],
        'temperature_unit': 'celsius',
        'wind_speed_unit': 'ms',
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch weather for {date}: {e}")
        return None


def compute_utci(temp_c: float, rh_percent: float, wind_ms: float, mrt_c: Optional[float] = None) -> float:
    """
    Compute Universal Thermal Climate Index (UTCI) using proper formula.

    Uses pythermalcomfort library for accurate UTCI calculation.

    Args:
        temp_c: Air temperature in Celsius
        rh_percent: Relative humidity in percent
        wind_ms: Wind speed in m/s
        mrt_c: Mean radiant temperature in Celsius (defaults to air temp)

    Returns:
        UTCI value in Celsius
    """
    if pd.isna(temp_c) or pd.isna(rh_percent) or pd.isna(wind_ms):
        return np.nan

    # If no MRT provided, estimate from air temp (simplified assumption)
    if mrt_c is None or pd.isna(mrt_c):
        mrt_c = temp_c

    try:
        # Use proper UTCI calculation from pythermalcomfort
        result = compute_utci_proper(tdb=temp_c, tr=mrt_c, v=wind_ms, rh=rh_percent)
        return result.utci
    except Exception as e:
        logger.warning(f"UTCI computation failed for T={temp_c}, RH={rh_percent}, wind={wind_ms}: {e}")
        return np.nan


def estimate_mrt_from_radiation(temp_c: float, radiation_wm2: float) -> float:
    """
    Estimate mean radiant temperature from shortwave radiation.

    Args:
        temp_c: Air temperature in Celsius
        radiation_wm2: Shortwave radiation in W/m²

    Returns:
        Estimated MRT in Celsius
    """
    if pd.isna(radiation_wm2) or radiation_wm2 <= 0:
        return temp_c

    # Simplified MRT estimate: higher radiation increases perceived temperature
    # This is a rough approximation
    radiation_effect = (radiation_wm2 / 100) * 2.0  # ~2°C per 100 W/m²
    mrt = temp_c + radiation_effect

    return mrt


def annotate_trips_with_weather(city_name: str, sample_frac: Optional[float] = None) -> pd.DataFrame:
    """
    Annotate trip data with weather information and UTCI.

    Args:
        city_name: Name of city ('seattle' or 'nyc')
        sample_frac: Optional fraction of data to sample for testing

    Returns:
        DataFrame with trips annotated with weather data
    """
    config = CITY_CONFIGS[city_name.lower()]
    logger.info(f"Processing {city_name}...")

    # Load trip data
    logger.info(f"Loading trip data from {config['trip_file']}")
    df = pd.read_csv(config['trip_file'])

    if sample_frac:
        df = df.sample(frac=sample_frac, random_state=42)
        logger.info(f"Sampled {len(df)} trips ({sample_frac*100:.1f}%)")

    logger.info(f"Loaded {len(df):,} trips")

    # Parse dates
    date_col = config['date_col']
    time_hour_col, time_min_col = config['time_cols']

    # Convert to datetime
    df['date'] = pd.to_datetime(df[date_col], errors='coerce')
    df['hour'] = pd.to_numeric(df[time_hour_col], errors='coerce')
    df['minute'] = pd.to_numeric(df[time_min_col], errors='coerce')

    # Filter valid dates/times
    df = df.dropna(subset=['date', 'hour'])
    logger.info(f"Retained {len(df):,} trips with valid date/time")

    # Get unique dates for weather fetching
    unique_dates = df['date'].dt.date.unique()
    logger.info(f"Fetching weather for {len(unique_dates)} unique dates...")

    # Fetch weather data
    weather_cache = {}
    for i, date in enumerate(unique_dates):
        if (i + 1) % 10 == 0:
            logger.info(f"  Fetched {i+1}/{len(unique_dates)} dates...")

        date_str = date.strftime('%Y-%m-%d')
        weather_data = fetch_open_meteo_weather(config['lat'], config['lon'], date_str)

        if weather_data and 'hourly' in weather_data:
            weather_cache[date] = pd.DataFrame(weather_data['hourly'])
            weather_cache[date]['time'] = pd.to_datetime(weather_cache[date]['time'])
            weather_cache[date]['hour'] = weather_cache[date]['time'].dt.hour
        else:
            logger.warning(f"No weather data for {date_str}")

    logger.info("Weather data fetched. Merging with trips...")

    # Merge weather data with trips
    weather_columns = []
    for _, row in df.iterrows():
        trip_date = row['date'].date()
        trip_hour = int(row['hour'])

        if trip_date in weather_cache:
            weather_df = weather_cache[trip_date]
            weather_hour = weather_df[weather_df['hour'] == trip_hour]

            if len(weather_hour) > 0:
                weather_columns.append(weather_hour.iloc[0].to_dict())
            else:
                weather_columns.append({})
        else:
            weather_columns.append({})

    # Add weather columns
    weather_df = pd.DataFrame(weather_columns)
    for col in weather_df.columns:
        if col not in ['time', 'hour']:
            df[f'weather_{col}'] = weather_df[col].values

    # Compute UTCI
    logger.info("Computing UTCI...")

    # Estimate MRT from radiation
    df['estimated_mrt'] = df.apply(
        lambda row: estimate_mrt_from_radiation(
            row.get('weather_temperature_2m', np.nan),
            row.get('weather_shortwave_radiation', 0)
        ),
        axis=1
    )

    # Compute UTCI
    df['utci'] = df.apply(
        lambda row: compute_utci(
            row.get('weather_temperature_2m', np.nan),
            row.get('weather_relative_humidity_2m', np.nan),
            row.get('weather_wind_speed_10m', np.nan),
            row.get('estimated_mrt', None)
        ),
        axis=1
    )

    # Identify walking trips
    mode_col = config['mode_col']
    walk_values = config['walk_values']
    df['is_walk'] = df[mode_col].isin(walk_values)

    # Add UTCI comfort categories
    df['utci_category'] = pd.cut(
        df['utci'],
        bins=[-np.inf, 9, 18, 26, 32, 38, np.inf],
        labels=['Extreme Cold', 'Cold', 'Cool/Comfortable', 'Warm', 'Hot', 'Extreme Heat']
    )

    logger.info(f"Annotated {df['utci'].notna().sum():,} trips with UTCI")
    logger.info(f"Identified {df['is_walk'].sum():,} walking trips")

    return df


def main():
    """Main execution function."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Process each city
    for city_name in ['seattle', 'nyc']:
        try:
            # For initial testing, use sample
            # df = annotate_trips_with_weather(city_name, sample_frac=0.01)

            # Full dataset
            df = annotate_trips_with_weather(city_name, sample_frac=None)

            # Save annotated data
            output_file = OUTPUT_DIR / f'{city_name}_trips_with_utci.csv'
            df.to_csv(output_file, index=False)
            logger.info(f"Saved {city_name} annotated trips to {output_file}")

            # Save summary statistics
            summary = {
                'city': city_name,
                'total_trips': len(df),
                'trips_with_utci': df['utci'].notna().sum(),
                'walking_trips': df['is_walk'].sum(),
                'walking_trips_with_utci': (df['is_walk'] & df['utci'].notna()).sum(),
                'mean_utci': df['utci'].mean(),
                'median_utci': df['utci'].median(),
                'mean_temp_c': df['weather_temperature_2m'].mean(),
                'walk_pct': df['is_walk'].mean() * 100,
            }

            logger.info(f"\n{city_name.upper()} Summary:")
            for key, value in summary.items():
                logger.info(f"  {key}: {value}")

        except Exception as e:
            logger.error(f"Failed to process {city_name}: {e}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    main()
