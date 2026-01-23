# ABOUTME: Adds timezone and datetime metadata to hot cities CSVs
# ABOUTME: Uses time_metadata_enrichment functions to add timezone, utc-offset, and datetime-local columns

import os
from tqdm import tqdm
from time_metadata_enrichment import append_local_time

if __name__ == '__main__':
    hot_cities_dir = '/home/kieran/Documents/Python/sunny_day_SVI/hot_cities'
    files = [f for f in os.listdir(hot_cities_dir) if f.endswith('.csv')]

    print(f"Processing {len(files)} cities")
    print("=" * 80)

    success_count = 0
    error_count = 0
    errors = []

    for file in tqdm(files, desc="Adding datetime data"):
        try:
            csvfilepath = os.path.join(hot_cities_dir, file)
            city_df = append_local_time(csvfilepath)
            city_df.to_csv(csvfilepath, index=False)
            success_count += 1
        except Exception as e:
            error_count += 1
            errors.append((file, str(e)))
            print(f"\nError processing {file}: {e}")

    print("\n" + "=" * 80)
    print(f"Complete! Success: {success_count}, Errors: {error_count}")

    if errors:
        print("\nFailed files:")
        for file, error in errors:
            print(f"  - {file}: {error}")
