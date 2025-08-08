import pandas as pd
import os
from pathlib import Path
import sys
import time
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import meteostat
from tqdm import tqdm
import pickle

#add sys path for import
sys.path.append('/home/kieran/Documents/Datasets/Global streetscapes/global-streetscapes/code/raw_download')
from raw_download import download_pts_csv

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
    city_point.alt_range = 2000#2km alt range to be generous
    try:
        data = meteostat.Daily(city_point,start,end) #get data for stuff
    except:
        print('temp data failed')
        return 0
    data.fetch()
    hot_days = hot_day_classifier(data)
    return hot_days



def hot_day_classifier(temp_data_daily):
    hot_days = temp_data_daily[temp_data_daily['tmax'] >= 34]
    return hot_days

#TODO: Finish this implementation 
def mapillary_download_hot_days(city,hot_days,save_dir):
    hot_date_list = list(hot_days.index.date) #get it as a list?
    hot_date_list = hot_date_list.sort() #order them (why not?)
    for date in hot_date_list:#TODO: Having each download point to the same location may not work. Ideally CSVs for each city would append?
        start_date = date #TODO: may need to tweak these to have 1 day gap (may find zero imgs for all cases)
        end_date = date
        download_pts_csv(city,save_dir,start_date,end_date,zoom = 14) # other zoom levels are not supported by Mapillary SDK (according to NUS fxn)



def main():
    #get list of cities:
    df_world_cities = pd.read_csv('/home/kieran/Documents/Datasets/Global streetscapes/global-streetscapes/code/raw_download/data/worldcities.csv')

    city_id_list = df_world_cities['id']

    for city in city_id_list: #TODO: Implement logging? exception catching lol?
        city_data = df_world_cities[df_world_cities['id']==city]
        city_lat = city_data['lat']
        city_lon = city_data['lng']
        city_hot_days = hotDayCity(city_lat,city_lon)
        save_dir = os.path.join('/home/kieran/Documents/Datasets/Global streetscapes/global-streetscapes/code/raw_download/city_testing_tmux',city_data['city_ascii'])
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
    # pass

if __name__ == "__main__":
    main()
