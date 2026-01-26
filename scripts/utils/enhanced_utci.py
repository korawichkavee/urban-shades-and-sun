# ABOUTME: Enhanced UTCI data collection including prior/next day averages and precipitation.
# ABOUTME: Fetches current UTCI, daily averages for surrounding days, and rain data from ERA5.

import math
import requests
import numpy as np
import thermofeel
from datetime import datetime, timezone, timedelta
from typing import Dict, Tuple, Optional
from pathlib import Path
import diskcache

# Persistent disk cache for ERA5 data
_cache_dir = Path(__file__).parent.parent.parent / "cache" / "era5_cache"
_cache_dir.mkdir(parents=True, exist_ok=True)
_era5_cache = diskcache.Cache(str(_cache_dir), size_limit=10e9)  # 10GB limit


def _round_coord_for_cache(lat, lon, decimals=2):
    """Round coordinates for cache key to enable reuse for nearby locations."""
    return round(lat, decimals), round(lon, decimals)


def _fetch_era5_multi_day(lat, lon, start_date_str, end_date_str):
    """
    Fetch ERA5 hourly data for multiple days at a given location.
    Includes temperature, dewpoint, wind speed, and precipitation.
    Returns the 'hourly' dict from Open-Meteo.
    """
    lat_q, lon_q = _round_coord_for_cache(lat, lon)
    cache_key = (lat_q, lon_q, start_date_str, end_date_str)

    if cache_key in _era5_cache:
        return _era5_cache[cache_key]

    url = (
        "https://archive-api.open-meteo.com/v1/era5"
        f"?latitude={lat_q}"
        f"&longitude={lon_q}"
        f"&start_date={start_date_str}"
        f"&end_date={end_date_str}"
        "&hourly=temperature_2m,dewpoint_2m,wind_speed_10m,precipitation"
        "&timezone=UTC"
    )

    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] ERA5 request failed for ({lat_q}, {lon_q}, {start_date_str}-{end_date_str}): {e}")
        return None

    if "error" in data:
        print(f"[ERROR] Open-Meteo ERA5 API error: {data.get('reason')}")
        return None

    if "hourly" not in data:
        print(f"[ERROR] ERA5 response missing 'hourly' for ({lat_q}, {lon_q}, {start_date_str}-{end_date_str})")
        return None

    hourly = data["hourly"]
    _era5_cache[cache_key] = hourly
    return hourly


def _calculate_utci_from_met(Ta_C, Td_C, Va):
    """Calculate UTCI from meteorological variables."""
    if Ta_C is None or Td_C is None or Va is None:
        return math.nan, math.nan

    if math.isnan(Ta_C) or math.isnan(Td_C) or math.isnan(Va):
        return math.nan, math.nan

    Ta_K = np.array([Ta_C + 273.15])
    Td_K = np.array([Td_C + 273.15])
    Va_a = np.array([Va])

    # MRT approximation: use air temperature
    Tr_K = Ta_K.copy()

    # Relative humidity & vapour pressure
    rh_pc = thermofeel.calculate_relative_humidity_percent(Ta_K, Td_K)
    es_hPa = thermofeel.calculate_saturation_vapour_pressure(Ta_K)
    ehPa = es_hPa * rh_pc / 100.0

    utci_K = thermofeel.calculate_utci(Ta_K, Va_a, Tr_K, ehPa=ehPa)
    utci_C = utci_K - 273.15

    return utci_K.item(), utci_C.item()


def _calculate_daily_average_utci(hourly_data, date_str):
    """Calculate average UTCI for a specific day from hourly data."""
    time_strings = hourly_data.get("time", [])
    temps = hourly_data.get("temperature_2m", [])
    dews = hourly_data.get("dewpoint_2m", [])
    winds = hourly_data.get("wind_speed_10m") or hourly_data.get("windspeed_10m")

    if not time_strings or not temps or not dews or winds is None:
        return math.nan

    utci_values = []

    for i, time_str in enumerate(time_strings):
        if time_str.startswith(date_str):
            Ta_C = temps[i]
            Td_C = dews[i]
            Va = winds[i]

            _, utci_C = _calculate_utci_from_met(Ta_C, Td_C, Va)
            if not math.isnan(utci_C):
                utci_values.append(utci_C)

    if utci_values:
        return np.mean(utci_values)
    return math.nan


def _check_daily_rain(hourly_data, date_str, threshold_mm=1.0):
    """Check if a specific day had rain (total precipitation > threshold)."""
    time_strings = hourly_data.get("time", [])
    precip = hourly_data.get("precipitation", [])

    if not time_strings or not precip:
        return None

    daily_precip = 0.0

    for i, time_str in enumerate(time_strings):
        if time_str.startswith(date_str):
            if precip[i] is not None and not math.isnan(precip[i]):
                daily_precip += precip[i]

    return daily_precip > threshold_mm


def get_enhanced_utci_data(lat, lon, timestamp) -> Dict:
    """
    Compute enhanced UTCI data for a given location and time.

    Returns dict with:
    - utci_K, utci_C: Current UTCI
    - utci_timestamp: Matched timestamp
    - prior_day_utci_avg_C: Average UTCI for prior day
    - next_day_utci_avg_C: Average UTCI for next day
    - prior_day_rain: Boolean indicating if prior day had rain
    - next_day_rain: Boolean indicating if next day had rain
    """
    # Parse and normalize timestamp to UTC
    if isinstance(timestamp, str):
        target = datetime.fromisoformat(timestamp)
    else:
        target = timestamp

    if target is None:
        raise ValueError("timestamp must not be None")

    if target.tzinfo is not None:
        target_utc = target.astimezone(timezone.utc)
    else:
        target_utc = target.replace(tzinfo=timezone.utc)

    target_utc_naive = target_utc.replace(tzinfo=None)
    current_date = target_utc_naive.date()

    prior_date = current_date - timedelta(days=1)
    next_date = current_date + timedelta(days=1)

    # Fetch data for all three days
    start_date_str = prior_date.isoformat()
    end_date_str = next_date.isoformat()

    hourly = _fetch_era5_multi_day(lat, lon, start_date_str, end_date_str)

    result = {
        'utci_K': math.nan,
        'utci_C': math.nan,
        'utci_timestamp': None,
        'wind_speed_10m': math.nan,
        'temperature_2m': math.nan,
        'dewpoint_2m': math.nan,
        'prior_day_utci_avg_C': math.nan,
        'next_day_utci_avg_C': math.nan,
        'prior_day_rain': None,
        'next_day_rain': None,
    }

    if hourly is None:
        return result

    # Find nearest hour to target time for current UTCI
    time_strings = hourly.get("time", [])
    if not time_strings:
        return result

    times = [datetime.fromisoformat(t) for t in time_strings]
    idx = min(range(len(times)), key=lambda i: abs(times[i] - target_utc_naive))
    matched_time = times[idx].isoformat()
    result['utci_timestamp'] = matched_time

    # Calculate current UTCI
    temps = hourly.get("temperature_2m", [])
    dews = hourly.get("dewpoint_2m", [])
    winds = hourly.get("wind_speed_10m") or hourly.get("windspeed_10m")

    if temps and dews and winds:
        Ta_C = temps[idx]
        Td_C = dews[idx]
        Va = winds[idx]

        utci_K, utci_C = _calculate_utci_from_met(Ta_C, Td_C, Va)
        result['utci_K'] = utci_K
        result['utci_C'] = utci_C
        result['wind_speed_10m'] = Va
        result['temperature_2m'] = Ta_C
        result['dewpoint_2m'] = Td_C

    # Calculate daily averages and rain for prior/next days
    result['prior_day_utci_avg_C'] = _calculate_daily_average_utci(hourly, prior_date.isoformat())
    result['next_day_utci_avg_C'] = _calculate_daily_average_utci(hourly, next_date.isoformat())

    result['prior_day_rain'] = _check_daily_rain(hourly, prior_date.isoformat())
    result['next_day_rain'] = _check_daily_rain(hourly, next_date.isoformat())

    return result


if __name__ == "__main__":
    # Test with Bangkok
    lat, lon = 13.75, 100.51
    ts_str = "2021-05-14T18:08:44+07:00"

    print("Testing enhanced UTCI data collection...")
    result = get_enhanced_utci_data(lat, lon, ts_str)

    print(f"\nResults for {ts_str}:")
    print(f"  Current UTCI: {result['utci_C']:.2f} °C at {result['utci_timestamp']}")
    print(f"  Prior day avg UTCI: {result['prior_day_utci_avg_C']:.2f} °C")
    print(f"  Next day avg UTCI: {result['next_day_utci_avg_C']:.2f} °C")
    print(f"  Prior day rain: {result['prior_day_rain']}")
    print(f"  Next day rain: {result['next_day_rain']}")
