import pandas as pd
import os
import threading
import mapillary.interface as mly
import time
from download_jpegs import download_csv
from pathlib import Path
import glob
from download_jpegs_mapillary import download_image

def main():
    access_token = 'MLY|9798203303595429|e2d4e749e96af419787ec1ca33019e3f' # update your mapillary access token
    mly.set_access_token(access_token)
    start_dir = '/volume1/hot-svi-proj/mapillary_city_data'
    #start_dir = '/home/kieran/Documents/Python/sunny_day_SVI/city_data'
    city_list = os.listdir(start_dir)
    for city in city_list:
        city_folder = os.path.join(start_dir,city)
        #find csv in path
        csv_file = glob.glob(os.path.join(city_folder,"*.csv"))
        csv_file = csv_file[0]
        #print(csv_file)
        img_output_dir = os.path.join(city_folder,'img')
        #print(city_folder)
        #print(img_output_dir)
        
        download_csv(csv_file,img_output_dir)

if __name__ == '__main__':
    #main()
    access_token = 'MLY|9798203303595429|e2d4e749e96af419787ec1ca33019e3f' # update your mapillary access token
    mly.set_access_token(access_token)
    csv_path = '/home/kieran/Documents/Python/sunny_day_SVI/test_svi_download/Thu Duc/Thu-Duc_1704361621.csv'
    out_dir = '/home/kieran/Documents/Python/sunny_day_SVI/test_svi_download/Thu Duc'
    download_csv(csv_path,out_dir)
    #out_path = '/home/kieran/Documents/Python/sunny_day_SVI/test_svi_download/test1.png'
    #img_id = 412070930384924
    #img_id = 915410099191728
    #download_image(img_id,out_path)