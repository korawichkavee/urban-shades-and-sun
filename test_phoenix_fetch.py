# ABOUTME: Quick test script for Phoenix SVI fetching
# ABOUTME: Simplified version to debug the full fetch script

import sys
import mapillary.interface as mly
import geopandas as gp
import pandas as pd
from zoneinfo import ZoneInfo
from timezonefinder import TimezoneFinder

# Set token
mly.set_access_token('MLY|9798203303595429|e2d4e749e96af419787ec1ca33019e3f')

print('Step 1: Fetching Mapillary data...', flush=True)
data = mly.get_image_close_to(longitude=-112.0891, latitude=33.5722)

print('Step 2: Converting to dict...', flush=True)
dict_data = data.to_dict()
print(f'  Features: {len(dict_data.get("features", []))}', flush=True)

print('Step 3: Converting to GeoDataFrame...', flush=True)
gdf = gp.GeoDataFrame.from_features(dict_data)
print(f'  GDF length: {len(gdf)}', flush=True)

if gdf.empty:
    print('ERROR: Empty GDF!', flush=True)
    sys.exit(1)

print('Step 4: Get timezone...', flush=True)
tf = TimezoneFinder()
tz_name = tf.timezone_at(lat=33.5722, lng=-112.0891)
city_tz = ZoneInfo(tz_name)
print(f'  Timezone: {tz_name}', flush=True)

print('Step 5: Filter by time...', flush=True)
print(f'  Before: {len(gdf)} points', flush=True)

# Convert timestamps
gdf['datetime_utc'] = pd.to_datetime(gdf['captured_at'], unit='ms')
gdf['datetime_local'] = gdf['datetime_utc'].dt.tz_localize('UTC').dt.tz_convert(city_tz)
gdf['hour'] = gdf['datetime_local'].dt.hour

# Filter
morning_mask = (gdf['hour'] >= 8) & (gdf['hour'] < 10)
evening_mask = (gdf['hour'] >= 16) & (gdf['hour'] < 18)
gdf_filtered = gdf[morning_mask | evening_mask].copy()

print(f'  After: {len(gdf_filtered)} points', flush=True)

print('Step 6: Add metadata...', flush=True)
gdf_filtered['city_id'] = 1840020568
gdf_filtered['lat'] = gdf_filtered.geometry.y
gdf_filtered['lon'] = gdf_filtered.geometry.x
gdf_filtered['source'] = 'Mapillary'

print('Step 7: Save to CSV...', flush=True)
df_out = pd.DataFrame(gdf_filtered.drop(columns='geometry'))
df_out.to_csv('data/raw/svi_filtered/Phoenix_1840020568.csv', index=False)

print(f'SUCCESS: Saved {len(df_out)} points to Phoenix_1840020568.csv', flush=True)
