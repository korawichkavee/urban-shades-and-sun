import pandas as pd
import os
from tqdm import tqdm
from datetime import datetime,timedelta,timezone
import meteostat
from metpy.calc import wet_bulb_temperature
from metpy.units import units
from tenacity import retry, wait_exponential, stop_after_attempt
meteostat.Hourly.max_age = 0 #disable caching since it was causing error
#import asyncio


@retry(wait=wait_exponential(multiplier=1, min=0, max=10), stop=stop_after_attempt(5))
def get_meteostat_hourly(img_point, start_time,end_time,retrieval_timezone):
    data = meteostat.Hourly(img_point,start_time,end_time,retrieval_timezone)
    return data

def get_meteostat_point(lat,lon,alt):
    img_point = meteostat.Point(lat,lon,alt) 
    #35km weather station range is default (what I used, more or less)
    return img_point
def get_hourly_weather(row):
    print('id of img')
    print(row['id'] )
    lat = row['lat']
    lon = row['lon']
    img_point = get_meteostat_point(lat,lon,0)#alt of 0 to make assumption
    img_point.alt_range = 2000#2km alt range to be generous
    img_time = row['datetime-local']
    img_time = pd.to_datetime(img_time,format = 'ISO8601',utc = True)
    time_range = timedelta(hours = 1)
    start_time = img_time -time_range #1 hr before
    end_time = img_time +time_range #1hr after
    #print((start_time.tz))
    #print((end_time.tz))
    retrieval_timezone = str(start_time.tz)
    #print(type(retrieval_timezone))]
    start_time = start_time.replace(tzinfo=None)
    end_time = end_time.replace(tzinfo=None)
    data = get_meteostat_hourly(img_point, start_time,end_time,retrieval_timezone)
    data = data.aggregate('d') #aggregate it all to get 1 value guaranteed?
    data = data.fetch()
    #Pick first row of data only
    #data = data.iloc[0]#get first row only
    dry_bulb_temp = data['temp'] #C
    rel_humidity = data['rhum']
    sunshine_time = data['tsun'] #min
    dew_point = data['dwpt']#C
    air_pressure = data['pres'] #hPA
    #get non-pandas array values to make metpy happy
    #air_pressure = air_pressure.to_numpy()
    
    #print(type(air_pressure))
    #print(air_pressure)
    wet_bulb_temp = wet_bulb_temperature(air_pressure.to_numpy() * units.hPa,dry_bulb_temp.to_numpy() * units.degC, dew_point.to_numpy() * units.degC) #intakes pressure, temp, dewpoint in that order
    row['wbulb'] = wet_bulb_temp.magnitude
    #convert to nice format and unpack
    row['dbulb'] = dry_bulb_temp.to_numpy()[0]
    row['tsun'] = sunshine_time.to_numpy()[0]
    #raise Exception('stop here?')
    
    print('get complete')
    return row

def csv_weather_annotations(csvpath):
    df_city = pd.read_csv(csvpath)
    df_city = df_city.apply(lambda row: get_hourly_weather(row),axis = 1)
    return df_city

def main():
    #target_csv = '/home/kieran/Documents/Python/sunny_day_SVI/mapillary_city_data/Abu Dhabi/Abu-Dhabi_1784176710.csv'

    #df_test = csv_weather_annotations(target_csv)
    #print(df_test.head())
    #df_test.to_csv(target_csv)
    starting_dir = '/home/kieran/Documents/Python/sunny_day_SVI/mapillary_city_data'
    dirs = os.listdir(starting_dir)
    for dir in tqdm(dirs):
        try:
            temp_dir = os.path.join(starting_dir,dir)
            
            temp_files = os.listdir(temp_dir)
            
            csvfile = temp_files[0]
            csvfilepath = os.path.join(temp_dir,csvfile)
            city_df = csv_weather_annotations(csvfilepath)
            city_df.to_csv(csvfilepath)
            #df_temp = pd.read_csv(os.path.join(temp_dir,csvfile))
            #city_dfs.append(df_temp)

        except:
            print('error')
    pass


if __name__ == '__main__':

    starting_dir = '/home/kieran/Documents/Python/sunny_day_SVI/city7sample'
    dirs = os.listdir(starting_dir)
    for file in tqdm(dirs):
        try:
            
            csvfilepath = os.path.join(starting_dir,file)
            city_df = csv_weather_annotations(csvfilepath)
            city_df.to_csv(csvfilepath)
            #df_temp = pd.read_csv(os.path.join(temp_dir,csvfile))
            #city_dfs.append(df_temp)

        except:
            print('error')
    #main()
    #target_csv = '/home/kieran/Documents/Python/sunny_day_SVI/test_svi_download/Berlin/Berlin_1276451290.csv'

    #df_test = csv_weather_annotations(target_csv)
    #print(df_test.head())
    #df_test.to_csv(target_csv)