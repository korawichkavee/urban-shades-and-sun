import math
import requests
import numpy as np
import thermofeel
from datetime import datetime, timezone

# Simple in-memory cache: {(lat_q, lon_q, date_utc): hourly_dict}
_era5_cache = {}


def _round_coord_for_cache(lat, lon, decimals=2):
    """
    Round coordinates a bit so nearby locations share the same cache entry.
    ERA5 is on a coarse grid anyway, so 0.01° is safe.
    """
    return round(lat, decimals), round(lon, decimals)


def _fetch_era5_hourly(lat, lon, date_utc_str):
    """
    Fetch ERA5 hourly data for a single day at a given location.
    Uses a small cache so multiple calls on the same day/area reuse results.
    Returns the 'hourly' dict from Open-Meteo.
    """
    lat_q, lon_q = _round_coord_for_cache(lat, lon)
    cache_key = (lat_q, lon_q, date_utc_str)

    if cache_key in _era5_cache:
        return _era5_cache[cache_key]

    url = (
        "https://archive-api.open-meteo.com/v1/era5"
        f"?latitude={lat_q}"
        f"&longitude={lon_q}"
        f"&start_date={date_utc_str}"
        f"&end_date={date_utc_str}"
        "&hourly=temperature_2m,dewpoint_2m,wind_speed_10m"
        "&timezone=UTC"
    )

    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] ERA5 request failed for ({lat_q}, {lon_q}, {date_utc_str}): {e}")
        return None

    if "error" in data:
        print(f"[ERROR] Open-Meteo ERA5 API error: {data.get('reason')}")
        return None

    if "hourly" not in data:
        print(f"[ERROR] ERA5 response missing 'hourly' for ({lat_q}, {lon_q}, {date_utc_str})")
        return None

    hourly = data["hourly"]
    _era5_cache[cache_key] = hourly
    return hourly


def get_utci_from_coords(lat, lon, timestamp):
    """
    Compute UTCI at (lat, lon) for the given timestamp.

    timestamp can be:
      - ISO string with timezone, e.g. '2021-05-14T18:08:44+07:00'
      - a datetime object (naive or aware)

    Logic:
      1. Normalize timestamp to UTC.
      2. Grab ERA5 hourly data for that UTC date.
      3. Find the nearest hourly record to the target time.
      4. Compute UTCI using thermofeel.
    """
    # --- 1. Parse and normalize timestamp to UTC ---
    if isinstance(timestamp, str):
        # handles '2022-12-26T05:43:25+07:00' and similar
        target = datetime.fromisoformat(timestamp)
    else:
        target = timestamp  # already a datetime

    if target is None:
        raise ValueError("timestamp must not be None for historical UTCI computation.")

    if target.tzinfo is not None:
        # convert to UTC
        target_utc = target.astimezone(timezone.utc)
    else:
        # assume already UTC if naive (you can change this if needed)
        target_utc = target.replace(tzinfo=timezone.utc)

    # We'll compare using naive UTC datetimes
    target_utc_naive = target_utc.replace(tzinfo=None)
    date_utc_str = target_utc_naive.date().isoformat()  # YYYY-MM-DD

    # --- 2. Fetch ERA5 hourly data for that day ---
    hourly = _fetch_era5_hourly(lat, lon, date_utc_str)
    if hourly is None:
        # API error; propagate NaN so outer code can continue
        return math.nan, math.nan, None

    # --- 3. Find nearest hour to target time ---
    time_strings = hourly.get("time", [])
    if not time_strings:
        print(f"[WARN] No hourly times returned for {date_utc_str} at ({lat}, {lon})")
        return math.nan, math.nan, None

    times = [datetime.fromisoformat(t) for t in time_strings]  # all naive UTC
    idx = min(range(len(times)), key=lambda i: abs(times[i] - target_utc_naive))
    matched_time = times[idx].isoformat()

    # --- 4. Extract met variables at that hour ---
    temps = hourly.get("temperature_2m", [])
    dews  = hourly.get("dewpoint_2m", [])

    # wind key can be 'wind_speed_10m' or 'windspeed_10m' depending on endpoint
    winds = hourly.get("wind_speed_10m") or hourly.get("windspeed_10m")

    if not temps or not dews or winds is None:
        print(f"[WARN] Missing met variables for {matched_time} at ({lat}, {lon})")
        return math.nan, math.nan, matched_time

    Ta_C = temps[idx]
    Td_C = dews[idx]
    Va   = winds[idx]

    # Debug for sanity
    print(f"Chosen time (UTC): {matched_time}")
    print("Ta_C:", Ta_C, "Td_C:", Td_C, "Va:", Va)

    # --- 5. Compute UTCI with thermofeel ---
    Ta_K = np.array([Ta_C + 273.15])
    Td_K = np.array([Td_C + 273.15])
    Va_a = np.array([Va])

    # First approximation: MRT ≈ air temp
    Tr_K = Ta_K.copy()

    # Relative humidity & vapour pressure
    rh_pc = thermofeel.calculate_relative_humidity_percent(Ta_K, Td_K)
    es_hPa = thermofeel.calculate_saturation_vapour_pressure(Ta_K)
    ehPa = es_hPa * rh_pc / 100.0

    utci_K = thermofeel.calculate_utci(Ta_K, Va_a, Tr_K, ehPa=ehPa)
    utci_C = utci_K - 273.15

    return utci_K.item(), utci_C.item(), matched_time


if __name__ == "__main__":
    # Quick self-test: UTCI in Bangkok for some past date
    lat, lon = 13.75, 100.51
    ts_str = "2021-05-14T18:08:44+07:00"
    utci_K, utci_C, ts = get_utci_from_coords(lat, lon, ts_str)
    print(f"UTCI at {ts} (UTC) for {ts_str} local: {utci_K:.2f} K ({utci_C:.2f} °C)")
