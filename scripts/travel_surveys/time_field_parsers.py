# ABOUTME: Parses various time field formats from travel surveys into standardized 24-hour format
# ABOUTME: Handles split hr/min/ampm, time strings with am/pm, and various encoded formats

import pandas as pd
import numpy as np
from typing import Union, Optional


def convert_12hr_to_24hr(hour_12: Union[int, float], ampm: Union[int, float, str]) -> Optional[int]:
    """
    Convert 12-hour format to 24-hour format.

    Args:
        hour_12: Hour in 12-hour format (1-12)
        ampm: AM/PM indicator (1/2, 'AM'/'PM', 'am'/'pm', etc.)

    Returns:
        Hour in 24-hour format (0-23), or None if invalid
    """
    if pd.isna(hour_12) or pd.isna(ampm):
        return None

    try:
        hour = int(float(hour_12))

        # Determine if PM
        is_pm = False
        if isinstance(ampm, str):
            is_pm = ampm.strip().upper() in ['PM', 'P', '2']
        elif isinstance(ampm, (int, float)):
            is_pm = int(ampm) == 2

        # Convert to 24-hour
        if is_pm:
            if hour != 12:
                hour += 12
        else:  # AM
            if hour == 12:
                hour = 0

        if 0 <= hour <= 23:
            return hour
        else:
            return None

    except (ValueError, TypeError):
        return None


def parse_split_time_to_minutes(hour: Union[int, float],
                                 minute: Union[int, float],
                                 ampm: Union[int, float, str, None] = None) -> Optional[int]:
    """
    Parse split time fields (hour, minute, optional am/pm) into minutes since midnight.

    Args:
        hour: Hour value (12-hour if ampm provided, 24-hour otherwise)
        minute: Minute value (0-59)
        ampm: Optional AM/PM indicator

    Returns:
        Minutes since midnight (0-1439), or None if invalid
    """
    if pd.isna(hour) or pd.isna(minute):
        return None

    try:
        mins = int(float(minute))

        # Convert hour to 24-hour format
        if ampm is not None and not pd.isna(ampm):
            hr = convert_12hr_to_24hr(hour, ampm)
            if hr is None:
                return None
        else:
            hr = int(float(hour))

        # Validate ranges
        if not (0 <= hr <= 23 and 0 <= mins <= 59):
            return None

        return hr * 60 + mins

    except (ValueError, TypeError):
        return None


def parse_hhmm_to_minutes(time_val: Union[int, float, str]) -> Optional[int]:
    """
    Parse HHMM format (e.g., 1430 for 2:30 PM) into minutes since midnight.

    Args:
        time_val: Time in HHMM format (e.g., 1430, 730, 0)

    Returns:
        Minutes since midnight, or None if invalid
    """
    if pd.isna(time_val):
        return None

    try:
        # Convert to integer
        if isinstance(time_val, str):
            time_val = time_val.strip()
            if not time_val:
                return None
            val = int(float(time_val))
        else:
            val = int(float(time_val))

        # Handle negative values as missing
        if val < 0:
            return None

        # Extract hours and minutes
        hours = val // 100
        minutes = val % 100

        # Validate ranges
        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            return None

        return hours * 60 + minutes

    except (ValueError, TypeError):
        return None


def parse_time_string_with_ampm(time_str: Union[str, int, float],
                                 ampm: Union[str, int, float, None] = None) -> Optional[int]:
    """
    Parse time string (e.g., "2:30", "14:30", "230", "1005") with optional separate AM/PM indicator.

    Args:
        time_str: Time string in various formats
        ampm: Optional separate AM/PM indicator

    Returns:
        Minutes since midnight, or None if invalid
    """
    if pd.isna(time_str):
        return None

    try:
        s = str(time_str).strip()

        # Check if ampm is embedded in string
        has_embedded_ampm = any(x in s.upper() for x in ['AM', 'PM', 'A.M.', 'P.M.'])

        if has_embedded_ampm:
            # Parse embedded AM/PM
            is_pm = 'PM' in s.upper() or 'P.M.' in s.upper()
            s = s.upper().replace('AM', '').replace('PM', '').replace('A.M.', '').replace('P.M.', '').strip()

        # Try parsing as HH:MM
        if ':' in s:
            parts = s.split(':')
            if len(parts) == 2:
                hour = int(parts[0])
                minute = int(parts[1])

                if has_embedded_ampm:
                    hour_24 = convert_12hr_to_24hr(hour, 'PM' if is_pm else 'AM')
                    if hour_24 is None:
                        return None
                    return hour_24 * 60 + minute
                elif ampm is not None and not pd.isna(ampm):
                    hour_24 = convert_12hr_to_24hr(hour, ampm)
                    if hour_24 is None:
                        return None
                    return hour_24 * 60 + minute
                else:
                    # Assume 24-hour format
                    if 0 <= hour <= 23 and 0 <= minute <= 59:
                        return hour * 60 + minute
                    else:
                        return None

        # Try parsing as plain number (HHMM format)
        # If ampm provided, treat as 12-hour format
        val = int(float(s))

        # Handle missing codes
        if val < 0 or val > 9999:
            return None

        hours = val // 100
        minutes = val % 100

        # If we have separate AM/PM, convert from 12-hour
        if ampm is not None and not pd.isna(ampm):
            hour_24 = convert_12hr_to_24hr(hours, ampm)
            if hour_24 is None:
                return None
            if 0 <= minutes <= 59:
                return hour_24 * 60 + minutes
            else:
                return None
        else:
            # Assume 24-hour format
            if 0 <= hours <= 23 and 0 <= minutes <= 59:
                return hours * 60 + minutes
            else:
                return None

    except (ValueError, TypeError):
        return None


def combine_split_time_fields(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect and combine split time fields into a standardized 'time_minutes' field.

    Handles patterns like:
    - dep_hr, dep_min, dep_ampm (detroit-1994, idaho-2002)
    - leavetime, leaveamorpm (kentuckiana-2001)
    - arrive, depart (simple HHMM format)

    Args:
        df: DataFrame with potential split time fields

    Returns:
        DataFrame with added 'time_minutes' column (minutes since midnight)
    """
    df = df.copy()

    # Pattern 1: dep_hr, dep_min, dep_ampm
    if all(col in df.columns for col in ['dep_hr', 'dep_min', 'dep_ampm']):
        df['time_minutes'] = df.apply(
            lambda row: parse_split_time_to_minutes(row['dep_hr'], row['dep_min'], row['dep_ampm']),
            axis=1
        )

    # Pattern 2: arr_hr, arr_min, arr_ampm (fallback if no departure)
    elif all(col in df.columns for col in ['arr_hr', 'arr_min', 'arr_ampm']):
        df['time_minutes'] = df.apply(
            lambda row: parse_split_time_to_minutes(row['arr_hr'], row['arr_min'], row['arr_ampm']),
            axis=1
        )

    # Pattern 3: leavetime, leaveamorpm
    elif all(col in df.columns for col in ['leavetime', 'leaveamorpm']):
        df['time_minutes'] = df.apply(
            lambda row: parse_time_string_with_ampm(row['leavetime'], row['leaveamorpm']),
            axis=1
        )

    # Pattern 4: arrivetime, arriveamorpm (fallback)
    elif all(col in df.columns for col in ['arrivetime', 'arriveamorpm']):
        df['time_minutes'] = df.apply(
            lambda row: parse_time_string_with_ampm(row['arrivetime'], row['arriveamorpm']),
            axis=1
        )

    # Pattern 5: Simple HHMM fields (arrive, depart, begtime, etc.)
    elif 'arrive' in df.columns:
        df['time_minutes'] = df['arrive'].apply(parse_hhmm_to_minutes)
    elif 'depart' in df.columns:
        df['time_minutes'] = df['depart'].apply(parse_hhmm_to_minutes)
    elif 'begtime' in df.columns:
        df['time_minutes'] = df['begtime'].apply(parse_hhmm_to_minutes)
    elif 'fintime' in df.columns:
        df['time_minutes'] = df['fintime'].apply(parse_hhmm_to_minutes)
    elif 'otime' in df.columns:
        df['time_minutes'] = df['otime'].apply(parse_hhmm_to_minutes)
    elif 'dtime' in df.columns:
        df['time_minutes'] = df['dtime'].apply(parse_hhmm_to_minutes)
    elif 'atime' in df.columns:
        df['time_minutes'] = df['atime'].apply(parse_hhmm_to_minutes)
    elif 'strttime' in df.columns:
        df['time_minutes'] = df['strttime'].apply(parse_hhmm_to_minutes)
    elif 'endtime' in df.columns:
        df['time_minutes'] = df['endtime'].apply(parse_hhmm_to_minutes)
    elif 'starttrv' in df.columns:
        df['time_minutes'] = df['starttrv'].apply(parse_hhmm_to_minutes)
    elif 'endtrav' in df.columns:
        df['time_minutes'] = df['endtrav'].apply(parse_hhmm_to_minutes)
    elif 'tlo' in df.columns:
        df['time_minutes'] = df['tlo'].apply(parse_hhmm_to_minutes)
    elif 'tad' in df.columns:
        df['time_minutes'] = df['tad'].apply(parse_hhmm_to_minutes)

    return df


def extract_primary_mode(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract primary mode from multiple mode columns.

    Handles:
    - mode1, mode2, mode3, ... (boston-1991, salt-lake-city-1993)
    - tran1, tran2, tran3, ... (philadelphia-2000)

    Args:
        df: DataFrame with potential multiple mode columns

    Returns:
        DataFrame with added 'primary_mode' column
    """
    df = df.copy()

    # Pattern 1: mode1, mode2, mode3, ...
    mode_cols = [c for c in df.columns if c.startswith('mode') and c[-1].isdigit()]
    if mode_cols:
        # Sort by number to get mode1, mode2, etc. in order
        mode_cols = sorted(mode_cols, key=lambda x: int(x.replace('mode', '')))
        # Take first non-null value
        df['primary_mode'] = df[mode_cols].bfill(axis=1).iloc[:, 0]
        return df

    # Pattern 2: tran1, tran2, tran3, ...
    tran_cols = [c for c in df.columns if c.startswith('tran') and c[-1].isdigit()]
    if tran_cols:
        tran_cols = sorted(tran_cols, key=lambda x: int(''.join(filter(str.isdigit, x))))
        df['primary_mode'] = df[tran_cols].bfill(axis=1).iloc[:, 0]
        return df

    # No multi-mode columns found, check for single mode column
    if 'mode' in df.columns:
        df['primary_mode'] = df['mode']
    elif 'travmode' in df.columns:
        df['primary_mode'] = df['travmode']
    elif 'modeoftravel' in df.columns:
        df['primary_mode'] = df['modeoftravel']
    elif 'pubtrans' in df.columns:
        df['primary_mode'] = df['pubtrans']

    return df
