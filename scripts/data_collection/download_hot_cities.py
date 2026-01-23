# ABOUTME: Downloads street view image metadata for hot cities from Mapillary
# ABOUTME: Creates CSV files with image metadata for each city

import pandas as pd
import os
from pathlib import Path
import mapillary.interface as mly
from download_mly_points import get_mly_gdf, save_csv, check_id

if __name__ == '__main__':
    access_token = 'MLY|9798203303595429|e2d4e749e96af419787ec1ca33019e3f'
    mly.set_access_token(access_token)

    # Load hot cities IDs
    hot_cities = pd.read_csv('/home/kieran/Documents/Python/sunny_day_SVI/hot_cities_matched.csv')
    targets = hot_cities['id'].tolist()

    print(f"Downloading metadata for {len(targets)} hot cities")
    print("=" * 80)

    # Download all available data (no date restrictions)
    start_date = None
    end_date = None

    # Output directory
    save_folder = Path(__file__).parent / 'hot_cities'
    Path(save_folder).mkdir(parents=True, exist_ok=True)
    print(f"Output folder: {save_folder}")

    # Load worldcities database
    wc = pd.read_csv('/home/kieran/Documents/Datasets/Global streetscapes/global-streetscapes/code/raw_download/data/worldcities.csv')

    # Check for already downloaded cities
    already_id = check_id(save_folder)
    total = len(targets)
    index = 0
    start_size = len([entry for entry in os.listdir(save_folder)
                     if os.path.isfile(os.path.join(save_folder, entry))])

    cities = wc[wc['id'].isin(targets)]

    for _, city in cities.iterrows():
        if str(city['id']) in already_id:
            print(f"Skipping {city['city']} (already downloaded)")
            continue

        index += 1
        print(f"\n[{index}/{total-len(already_id)}] Downloading: {city['city']}, {city['country']}")
        print("-" * 80)

        try:
            gdf = get_mly_gdf(city, start_date, end_date)
            if gdf is not None and not gdf.empty:
                save_csv(gdf, city, save_folder)
            else:
                print(f"No data found for {city['city']}")
        except Exception as e:
            print(f"Error downloading {city['city']}: {e}")

        print(f"Progress: {index}/{total-len(already_id)}, Already: {len(already_id)}")

    end_size = len([entry for entry in os.listdir(save_folder)
                   if os.path.isfile(os.path.join(save_folder, entry))])
    increase = end_size - start_size
    print("\n" + "=" * 80)
    print(f"Download complete!")
    print(f"New cities with data: {increase}/{total-len(already_id)}")
    print(f"Total cities in folder: {end_size}")
