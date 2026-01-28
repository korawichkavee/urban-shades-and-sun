# ABOUTME: UTCI data collection from ERA5 climate data via Open-Meteo API
# ABOUTME: Fetches current UTCI, temperature, dewpoint, and wind speed at image timestamp

import sys
import math
import requests
import numpy as np
import thermofeel
from datetime import datetime, timezone, timedelta
from typing import Dict, Tuple, Optional
from pathlib import Path
import diskcache

# Add config to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'config'))
from api_config import get_era5_url

# Persistent disk cache for ERA5 data
_cache_dir = Path(__file__).parent.parent.parent / "cache" / "era5_cache"
_cache_dir.mkdir(parents=True, exist_ok=True)
_era5_cache = diskcache.Cache(str(_cache_dir), size_limit=10e9)  # 10GB limit


def _round_coord_for_cache(lat, lon, decimals=2):
    """Round coordinates for cache key to enable reuse for nearby locations."""
    return round(lat, decimals), round(lon, decimals)


def _fetch_era5_single_day(lat, lon, date_str, max_retries=3):
    """
    Fetch ERA5 hourly data for a single day at a given location.
    Includes temperature, dewpoint, and wind speed.
    Returns the 'hourly' dict from Open-Meteo.

    Uses exponential backoff for rate limit errors (429).
    """
    import time

    lat_q, lon_q = _round_coord_for_cache(lat, lon)
    cache_key = (lat_q, lon_q, date_str)

    if cache_key in _era5_cache:
        return _era5_cache[cache_key]

    url = get_era5_url(
        latitude=lat_q,
        longitude=lon_q,
        start_date=date_str,
        end_date=date_str,
        hourly_vars="temperature_2m,dewpoint_2m,wind_speed_10m",
        timezone="UTC"
    )

    for attempt in range(max_retries):
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            if "error" in data:
                print(f"[ERROR] Open-Meteo ERA5 API error: {data.get('reason')}")
                return None

            if "hourly" not in data:
                print(f"[ERROR] ERA5 response missing 'hourly' for ({lat_q}, {lon_q}, {date_str})")
                return None

            hourly = data["hourly"]
            _era5_cache[cache_key] = hourly
            return hourly

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:  # Rate limit
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + (attempt * 0.5)  # Exponential backoff: 1s, 2.5s, 5s
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"[ERROR] ERA5 rate limit exceeded after {max_retries} retries: ({lat_q}, {lon_q}, {date_str})")
                    return None
            else:
                print(f"[ERROR] ERA5 HTTP error for ({lat_q}, {lon_q}, {date_str}): {e}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] ERA5 request failed for ({lat_q}, {lon_q}, {date_str}): {e}")
            return None

    return None


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


def get_enhanced_utci_data(lat, lon, timestamp) -> Dict:
    """
    Compute UTCI data for a given location and time.

    Returns dict with:
    - utci_K, utci_C: Current UTCI (Kelvin and Celsius)
    - utci_timestamp: Matched timestamp from ERA5 data
    - wind_speed_10m: Wind speed at 10m height (m/s)
    - temperature_2m: Air temperature at 2m height (°C)
    - dewpoint_2m: Dewpoint temperature at 2m height (°C)
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

    # Fetch data for current day only
    date_str = current_date.isoformat()

    hourly = _fetch_era5_single_day(lat, lon, date_str)

    result = {
        'utci_K': math.nan,
        'utci_C': math.nan,
        'utci_timestamp': None,
        'wind_speed_10m': math.nan,
        'temperature_2m': math.nan,
        'dewpoint_2m': math.nan,
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

    return result


if __name__ == "__main__":
    # Test with Bangkok
    lat, lon = 13.75, 100.51
    ts_str = "2021-05-14T18:08:44+07:00"

    print("Testing UTCI data collection...")
    result = get_enhanced_utci_data(lat, lon, ts_str)

    print(f"\nResults for {ts_str}:")
    print(f"  UTCI: {result['utci_C']:.2f} °C at {result['utci_timestamp']}")
    print(f"  Temperature: {result['temperature_2m']:.2f} °C")
    print(f"  Dewpoint: {result['dewpoint_2m']:.2f} °C")
    print(f"  Wind speed: {result['wind_speed_10m']:.2f} m/s")
