#!/usr/bin/env python3
"""
Scan entire file for unique dates - memory efficient
"""
import pandas as pd
from datetime import datetime

print("Scanning entire file for dates...")
all_dates = set()
chunk_num = 0

for chunk in pd.read_csv('data/img_dat(1).csv',
                         names=['id', 'filename', 'url', 'size', 'timestamp'],
                         usecols=['timestamp'],
                         chunksize=500000):
    chunk['date'] = pd.to_datetime(chunk['timestamp']).dt.date
    all_dates.update(chunk['date'].unique())
    chunk_num += 1
    if chunk_num % 10 == 0:
        print(f"  Processed {chunk_num * 500000:,} rows, found {len(all_dates)} unique dates so far...")

print(f"\nTotal rows processed: {chunk_num * 500000:,}")
print(f"Total unique dates: {len(all_dates)}")

# Sort and analyze
sorted_dates = sorted(all_dates)
print(f"\nDate range: {sorted_dates[0]} to {sorted_dates[-1]}")
total_span = (sorted_dates[-1] - sorted_dates[0]).days + 1
print(f"Total span: {total_span} days")
print(f"Coverage: {len(sorted_dates)}/{total_span} days ({100*len(sorted_dates)/total_span:.1f}%)")

# Seasonal breakdown
from collections import defaultdict
season_map = {
    12: 'Winter', 1: 'Winter', 2: 'Winter',
    3: 'Spring', 4: 'Spring', 5: 'Spring',
    6: 'Summer', 7: 'Summer', 8: 'Summer',
    9: 'Fall', 10: 'Fall', 11: 'Fall'
}

seasons = defaultdict(list)
months = defaultdict(int)

for date in sorted_dates:
    season = season_map[date.month]
    seasons[season].append(date)
    months[date.month] += 1

print(f"\n{'='*70}")
print("SEASONAL DISTRIBUTION")
print(f"{'='*70}")
for season in ['Winter', 'Spring', 'Summer', 'Fall']:
    if season in seasons:
        print(f"  {season:8s}: {len(seasons[season]):2d} days")
    else:
        print(f"  {season:8s}:  0 days ⚠️")

print(f"\n{'='*70}")
print("MONTHLY BREAKDOWN")
print(f"{'='*70}")
month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
               'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
for month_num, month_name in enumerate(month_names, 1):
    count = months.get(month_num, 0)
    if count > 0:
        print(f"  {month_name}: {count:2d} days")
    else:
        print(f"  {month_name}:  0 days")
