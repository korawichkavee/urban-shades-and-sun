import pandas as pd
import geopandas as gp
import os
import datetime
import pytz
from tzwhere import tzwhere
from tqdm import tqdm
from timezonefinder import TimezoneFinder

def get_timezone_str(city_lat,city_lon):
    
    
    #tzw = tzwhere.tzwhere(forceTZ=True)#location of bug
    tf = TimezoneFinder()
    #city_tz_str = tzw.tzNameAt(city_lat,city_lon,forceTZ=True)
    city_tz_str = tf.timezone_at(lat = city_lat, lng = city_lon)
    #tz_str = tzwhere.tzwhere(city['lat'], city['lng'])
    
    return city_tz_str

def get_utcoffset(city_tz_str):
    tz = pytz.timezone(city_tz_str)
    dt = datetime.datetime.now()
    offset = tz.utcoffset(dt).total_seconds()
    return offset

def get_local_datetime(row):
    timestamp = row['captured_at']/1000
    dt = datetime.datetime.fromtimestamp(timestamp)
    dt2 = dt.astimezone(pytz.timezone(row['timezone']))
    return dt2



def append_local_time(point_csv):
    df_svi = pd.read_csv(point_csv)
    city_lat = df_svi['lat'].iloc[0]#takes first val as good enough approx
    city_lon = df_svi['lon'].iloc[0]
    #tzw = tzwhere.tzwhere(forceTZ=True)
    #city_tz_str = tzw.tzNameAt(city_lat,city_lon,forceTZ=True)
    city_tz_str =  get_timezone_str(city_lat,city_lon)
    city_offset = get_utcoffset(city_tz_str)
    df_svi['timezone'] = city_tz_str#map single val to all rows because I'm lazy
    df_svi['utc-offset'] = city_offset
    #now for lambda fxn
    df_svi['datetime-local'] = df_svi.apply(lambda row: get_local_datetime(row),axis = 1)
    return df_svi



def main():
    starting_dir = '/home/kieran/Documents/Python/sunny_day_SVI/mapillary_city_data'
    dirs = os.listdir(starting_dir)
    for dir in tqdm(dirs):
        try:
            temp_dir = os.path.join(starting_dir,dir)
            
            temp_files = os.listdir(temp_dir)
            
            csvfile = temp_files[0]
            csvfilepath = os.path.join(temp_dir,csvfile)
            city_df = append_local_time(csvfilepath)
            city_df.to_csv(csvfilepath)
            #df_temp = pd.read_csv(os.path.join(temp_dir,csvfile))
            #city_dfs.append(df_temp)

        except:
            print('error')
    #target_csv = '/home/kieran/Documents/Python/sunny_day_SVI/mapillary_city_data/Abu Dhabi/Abu-Dhabi_1784176710.csv'
    #df_abudhabi = append_local_time(target_csv)
    #print(df_abudhabi.head())
    #df_abudhabi.to_csv(target_csv)
    pass




if __name__ == '__main__':
    #main()
    starting_dir = '/home/kieran/Documents/Python/sunny_day_SVI/city7sample'
    dirs = os.listdir(starting_dir)
    for file in tqdm(dirs):
        try:
            
            
            csvfilepath = os.path.join(starting_dir,file)
            city_df = append_local_time(csvfilepath)
            city_df.to_csv(csvfilepath)
            #df_temp = pd.read_csv(os.path.join(temp_dir,csvfile))
            #city_dfs.append(df_temp)

        except:
            print('error')

    pass