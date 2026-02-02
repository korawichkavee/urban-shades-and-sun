# ABOUTME: Maps field names for 12 recoverable surveys to standardized schema
# ABOUTME: Each survey has custom column names; this maps them to common fields

"""
Field mappings for 12 recoverable travel surveys.

This module maps survey-specific field names to standardized categories:
- time: timestamp, departure/arrival time fields
- location: geographic identifiers (county, tract, ZIP, etc.)
- mode: transportation mode fields
- household_id: household/sample identifiers
- person_id: person identifiers within household
"""

# Primary trip file for each survey
# NOTE: baltimore-2001 excluded - time fields corrupted (stored as dates 1960-01-01, 1899-12-30)
TRIP_FILES = {
    'anchorage-2002': 'survey_trips.csv',
    'baltimore-1977': 'survey_data.csv',
    # 'baltimore-2001': 'survey_travel_day.csv',  # EXCLUDED: corrupt time data
    'boston-1991': 'survey_trip.csv',
    'detroit-1994': 'survey_trip.csv',
    'idaho-2002': 'survey_trips.csv',
    'kentuckiana-2001': 'survey.csv',
    'los-angeles-2001': 'survey_data.csv',
    'philadelphia-2000': 'survey_trips.csv',
    'salt-lake-city-1993': 'survey_trip.csv',
    'san-francisco-1990': 'survey_data.csv',
    'washington-dc-1968': 'survey_data.csv'
}

# Field mappings for each survey
FIELD_MAPPINGS = {
    'anchorage-2002': {
        'time': ['arrive', 'depart', 'dephour'],
        'location': ['ctfip'],
        'mode': ['mode', 'o_mode'],
        'household_id': ['sampn'],
        'person_id': ['perno']
    },
    'baltimore-1977': {
        'time': ['tlo', 'tad', 'htlo', 'htad'],
        'location': ['ozone', 'dzone'],
        'mode': ['mode', 'trandist', 'tranivt'],
        'household_id': ['batch', 'sampno'],
        'person_id': ['perno']
    },
    'baltimore-2001': {
        'time': ['strttime', 'endtime', 'trvlhrs', 'trvl_min'],
        'location': ['trpblock', 'hhcnty', 'origtaz00', 'desttaz00'],
        'mode': ['pubtrans', 'trppub', 'pubtype'],
        'household_id': ['sampno'],
        'person_id': ['perno']
    },
    'boston-1991': {
        'time': ['begtime', 'fintime'],
        'location': ['ocounty', 'otract90', 'oblock90', 'dcounty', 'dtract90', 'dblock90'],
        'mode': ['mode1', 'mode2', 'mode3', 'mode4', 'mode5', 'mode6'],
        'household_id': ['sampno'],
        'person_id': ['persno']
    },
    'detroit-1994': {
        'time': ['dep_hr', 'dep_min', 'dep_ampm', 'arr_hr', 'arr_min', 'arr_ampm'],
        'location': [],  # Will use household 'area' via sampno join with survey_household.csv
        'mode': ['travmode', 'acc_mode'],
        'household_id': ['sampno'],
        'person_id': ['perno'],
        'household_file': 'survey_household.csv',  # For area lookup
        'household_location_fields': ['area']
    },
    'idaho-2002': {
        'time': ['dep_hr', 'dep_min', 'arr_hr', 'arr_min'],
        'location': ['ocounty', 'ozip', 'oav_zone', 'dcounty', 'dzip'],
        'mode': ['mode', 'othmode'],
        'household_id': ['sampno'],
        'person_id': ['perno']
    },
    'kentuckiana-2001': {
        'time': ['leavetime', 'leaveamorpm', 'arrivetime', 'arriveamorpm', 'triptimeminutes'],
        'location': ['tripstartcounty', 'tripendcnty', 'starttaz', 'endtaz'],
        'mode': ['modeoftravel'],
        'household_id': ['sampno'],
        'person_id': ['perno']
    },
    'los-angeles-2001': {
        'time': ['arrive', 'depart'],
        'location': ['county', 'region', 'fipstract'],
        'mode': ['mode', 'othmode', 'transrte'],
        'household_id': ['sampno'],
        'person_id': ['perno']
    },
    'philadelphia-2000': {
        'time': ['atime', 'dtime'],
        'location': ['cpa', 'region'],
        'mode': ['tran1', 'tran2', 'tran3', 'tran4'],
        'household_id': ['sampno'],
        'person_id': ['perno']
    },
    'salt-lake-city-1993': {
        'time': ['starttrv', 'endtrav', 'starthr'],
        'location': ['origcnty', 'destcnty', 'origtaz', 'desttaz'],
        'mode': ['mode1', 'mode2', 'mode3', 'mode4', 'mode5', 'mode6'],
        'household_id': ['sampno', 'key_id'],
        'person_id': ['persno']
    },
    'san-francisco-1990': {
        'time': ['otime', 'dtime'],
        'location': ['hometrct', 'countyres'],
        'mode': ['mode', 'tranoper'],
        'household_id': ['sampno'],
        'person_id': ['perno']
    },
    'washington-dc-1968': {
        'time': ['begtime', 'endtime'],
        'location': ['origzone', 'destzone', 'homezone'],
        'mode': ['mode', 'begwalk', 'endwalk', 'bustransf'],
        'household_id': ['sampno'],
        'person_id': ['perno']
    }
}
