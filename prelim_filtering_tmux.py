import pandas as pd
import os
from pathlib import Path
import sys
import time
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
import meteostat
from tqdm import tqdm
import logging
from time import sleep

#add sys path for import
sys.path.append('/home/kieran/Documents/Datasets/Global streetscapes/global-streetscapes/code/raw_download')
from raw_download import download_pts_csv

logger = logging.getLogger(__name__)


def hotDayFinder(city_ascii,city_lat,city_lon,df_streetscapes):
    flag = 0
    start = datetime(2018,1,1)
    end = datetime(2025,1,1)
    #print(city_ascii)
    city_point = meteostat.Point(city_lat,city_lon,0) #altitude of 0 since idk
    city_point.alt_range = 2000#2km alt range to be generous 
    #print(city_point)
    try:
        data = meteostat.Daily(city_point,start,end) #get data for stuff
    except:
        print('temp data failed')
        return 0,flag
    data = data.fetch()#ping a req for data
    hot_days = data[data['tmax'] >= 34] #arbitrary max setting, could be based on stdev of location? Also in C (assumed to be standard across all countries?)
    if len(hot_days) <1:
        print('no hot days')
        flag = 1
        return 0,flag
    hot_days_list = hot_days.index.date #list of hot dates?
    hot_days_set = set(hot_days_list)
    df_city = df_streetscapes[df_streetscapes['city_ascii']== city_ascii]
    
    img_dates = pd.to_datetime(df_city['datetime_local'],format = 'ISO8601',utc = True) #utc is actually not true, preventing an error?
    #print(img_dates)
    img_date_set = set(img_dates.dt.date)#making it into a set guarantees unique vals (no dupes). Turning it into dates makes stuff only days, no mins/sec
    intersecting_days = list(hot_days_set.intersection(img_date_set))
    if len(intersecting_days) <1:
        print('no intersecting days')
        flag = 1
        return 0,flag
    return intersecting_days,flag

def hotDayCity(city_lat,city_lon): #find the hot days in a specific city?
    
    start = datetime(2018,1,1) #TODO: Make arbitrary (for all time?)
    end = datetime(2025,1,1)
    

    city_point = meteostat.Point(city_lat,city_lon,0) #altitude of 0 since idk
    city_point.alt_range = 2000#2km altitude range to be generous
    city_point.radius = 1000 #in m
    
    sleep(5)
    data = meteostat.Daily(city_point,start,end)
    # try:
    #     data = meteostat.Daily(city_point,start,end) #TODO: fix whatever is going on here?
    # except:
    #     logger.info('No weather stations in range/temp data failed')
    #     return 0
    data = data.fetch()
    #print(data)
    hot_days = hot_day_classifier(data)
    return hot_days



def hot_day_classifier(temp_data_daily):
    hot_days = temp_data_daily[temp_data_daily['tmax'] >= 30]
    if len(hot_days) <1:
        return 0
    #else
    return hot_days

#TODO: Finish this implementation 
def mapillary_download_hot_days(city,hot_days,save_dir):
    if hot_days.empty:#if there are no hot days
        #do nothing
        print('no hot days')
        return#end fxn
    
    hot_date_list = list(hot_days.index.date) #get it as a list?
    print('hot days')
    #print(hot_days)
    #print(hot_date_list)
    for date in hot_date_list:#TODO: Having each download point to the same location may not work. Ideally CSVs for each city would append?
        start_date = date 
        end_date = date + timedelta(days = 1) #add a day after to allow for images to be collected
        #convert datetimes into strings to make compatible with mapillary API (take strings in YYYY-MM-DD, not datetime)
        start_date = start_date.strftime("%Y-%m-%d")
        end_date = end_date.strftime("%Y-%m-%d")

        print(start_date)
        print(end_date)
        download_pts_csv(city,save_dir,start_date,end_date,zoom = 14) # other zoom levels are not supported by Mapillary SDK (according to NUS fxn)



def main():
    #get list of cities:
    
    logging.basicConfig(filename='myapp.log', level=logging.INFO)
    #logger.info('Started')
    df_world_cities = pd.read_csv('/home/kieran/Documents/Datasets/Global streetscapes/global-streetscapes/code/raw_download/data/worldcities.csv')
    df_world_cities = df_world_cities.dropna(subset=['city_ascii','lat','lng'])#drop where any value is NaN
    #logger.info('Obtained cities')
    city_id_list = df_world_cities['id']

    for city in tqdm(city_id_list): 
        
        city = df_world_cities[df_world_cities['id']==city].iloc[0] #change to city as df
        #print(city_data['city_ascii'].iloc[0])
        #print(city_data)
        city_lat = city['lat']
        city_lon = city['lng']
        
        city_hot_days = hotDayCity(city_lat,city_lon)
        
        #print(city_data['city_ascii'].iloc[0])
        save_dir = os.path.join('/home/kieran/Documents/Datasets/Global streetscapes/global-streetscapes/code/raw_download/city_testing_tmux',city['city_ascii'])#0 to un
        #make directory to save stuff
        os.makedirs(save_dir,exist_ok=True)
        #print('hot days length')
        #print(len(city_hot_days))
        mapillary_download_hot_days(city,city_hot_days,save_dir)
    







    #get list of cities
    # df_cities = pd.read_csv('/home/kieran/.cache/huggingface/hub/datasets--NUS-UAL--global-streetscapes/snapshots/7bd2e7697a3cb5f74ff05bd718babdb927f8b60d/cities688.csv')
    # df_streetscapes = pd.read_csv(
    # "/home/kieran/.cache/huggingface/hub/datasets--NUS-UAL--global-streetscapes/snapshots/7bd2e7697a3cb5f74ff05bd718babdb927f8b60d/data/simplemaps.csv"
    # )

    # #add in another dataset to get the year of the image -> check for covid?
    # df_metadata = pd.read_csv('/home/kieran/.cache/huggingface/hub/datasets--NUS-UAL--global-streetscapes/snapshots/7bd2e7697a3cb5f74ff05bd718babdb927f8b60d/data/metadata_common_attributes.csv')
    # df_streetscapes = df_streetscapes.merge(df_metadata, on = ["uuid","source","orig_id"])
    # df_metadata = None

    # unique_cities = df_streetscapes['city_ascii'].unique()
    # #unique_cities = unique_cities[10:20]
    # hot_days = []
    # hot_cities = []
    # for city in tqdm(unique_cities):
    #     city_lat = df_cities[df_cities['city_ascii'] == city]['city_lat']
    #     city_lon = df_cities[df_cities['city_ascii']== city]['city_lon']
    #     city_lat = city_lat.values[0]
    #     city_lon = city_lon.values[0]
    #     #print(city_lat)
    #     #print(city_lon)
    #     temp_output, flag = hotDayFinder(city,city_lat,city_lon,df_streetscapes)
    #     if flag ==0:
    #         hot_days.append(temp_output)
    #         hot_cities.append(city)
    # filepath = 'test_day_list_2.pkl'
    # with open(filepath,'wb') as f:
    #     pickle.dump(hot_days,f)
    # filepath = 'test_city_list_2.pkl'
    # with open(filepath,'wb') as f:
    #     pickle.dump(hot_cities,f)
    pass

if __name__ == "__main__":
    main()
