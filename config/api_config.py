# ABOUTME: Configuration for Open-Meteo API access
# ABOUTME: Stores API key and endpoint configuration for commercial API access

from pathlib import Path
import json

def load_api_config():
    """
    Load API configuration from config.json file.

    Returns:
        dict with 'api_key' and 'base_url' keys
    """
    config_path = Path(__file__).parent / "config.json"

    if not config_path.exists():
        raise FileNotFoundError(
            f"API config file not found at {config_path}. "
            "Please create config/config.json with your API key."
        )

    with open(config_path, 'r') as f:
        config = json.load(f)

    if 'api_key' not in config:
        raise ValueError("API config must contain 'api_key' field")

    return config

def get_era5_url(latitude, longitude, start_date, end_date, hourly_vars, timezone="UTC"):
    """
    Build ERA5 API URL with API key for commercial access.

    Args:
        latitude: Single lat or comma-separated string of multiple lats
        longitude: Single lon or comma-separated string of multiple lons
        start_date: Date string in YYYY-MM-DD format
        end_date: Date string in YYYY-MM-DD format
        hourly_vars: Comma-separated string of hourly variables
        timezone: Timezone string (default: UTC)

    Returns:
        Complete URL string with API key appended
    """
    config = load_api_config()

    # Convert to strings if needed
    if not isinstance(latitude, str):
        latitude = str(latitude)
    if not isinstance(longitude, str):
        longitude = str(longitude)

    # Use customer archive API endpoint
    base_url = "https://customer-archive-api.open-meteo.com/v1/era5"

    url = (
        f"{base_url}"
        f"?latitude={latitude}"
        f"&longitude={longitude}"
        f"&start_date={start_date}"
        f"&end_date={end_date}"
        f"&hourly={hourly_vars}"
        f"&timezone={timezone}"
        f"&apikey={config['api_key']}"
    )

    return url
