import pandas as pd
import os
import re
import shutil


def sort_image(row):
    #print((row))
    img_name = row['image']
    choice = row['choice']
    print(row)
    img_name = re.search(r"-(.*)", img_name)#only gets the image
    img_name = img_name.group(1)
    #print(img_name)
    full_inpathname = os.path.join(data_dir,img_name)
    print(choice)
    print(img_name)
    full_outpathname = os.path.join(target_dir,choice,img_name)
    
    if choice == 'sunny':
        shutil.copy(full_inpathname,full_outpathname)
    elif choice == 'not_sunny':
        shutil.copy(full_inpathname,full_outpathname)
    else:
        print('error lmao')

    pass#return nothing


if __name__ == "__main__":
    df_labels = pd.read_csv('/home/kieran/Documents/Python/sunny_day_SVI/city7sample/images_to_label/batch2/labeled/labeled_sunny_nsunny_subset.csv')
    df_labels = df_labels.dropna(axis = 0, how = 'any', subset = ['choice','image'])
    print(df_labels.head())
    data_dir = '/home/kieran/Documents/Python/sunny_day_SVI/city7sample/images_to_label/batch2/Korawich'

    target_dir = '/home/kieran/Documents/Python/sunny_day_SVI/city7sample/images_to_label/batch2/labeled/data'
    df_labels.apply(sort_image,axis = 1)