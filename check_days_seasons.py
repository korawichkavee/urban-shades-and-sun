#!/usr/bin/env python3
"""
Quick check of days with coverage and seasonal distribution
"""
import pandas as pd
from collections import Counter

print("Reading sample of data...")
# Read first 1M rows to get temporal coverage
df = pd.read_csv('data/img_dat(1).csv',
                 names=['id', 'filename', 'url', 'size', 'timestamp'],
                 nrows=1000000)

df['timestamp'] = pd.to_datetime(df['timestamp'])
df['date'] = df['timestamp'].dt.date
df['month'] = df['timestamp'].dt.month
df['season'] = df['timestamp'].dt.month.map({
    12: 'Winter', 1: 'Winter', 2: 'Winter',
    3: 'Spring', 4: 'Spring', 5: 'Spring',
    6: 'Summer', 7: 'Summer', 8: 'Summer',
    9: 'Fall', 10: 'Fall', 11: 'Fall'
})

unique_dates = sorted(df['date'].unique())
print(f"\n{'='*70}")
print("DAYS WITH COVERAGE")
print(f"{'='*70}")
print(f"Days with data: {len(unique_dates)}")
print(f"Date range: {unique_dates[0]} to {unique_dates[-1]}")
total_span = (unique_dates[-1] - unique_dates[0]).days + 1
print(f"Total span: {total_span} days")
print(f"Coverage: {len(unique_dates)}/{total_span} days ({100*len(unique_dates)/total_span:.1f}%)")

print(f"\n{'='*70}")
print("SEASONAL DISTRIBUTION")
print(f"{'='*70}")

# Count records by season
season_counts = df['season'].value_counts().sort_index()
print("\nRecords by season (in sample):")
for season, count in season_counts.items():
    print(f"  {season:8s}: {count:,} records")

# Count days by season
days_by_season = df.groupby('season')['date'].nunique()
print("\nDays with data by season:")
for season in ['Winter', 'Spring', 'Summer', 'Fall']:
    if season in days_by_season:
        print(f"  {season:8s}: {days_by_season[season]} days")
    else:
        print(f"  {season:8s}: 0 days ⚠️")

# Month breakdown
print(f"\n{'='*70}")
print("MONTHLY BREAKDOWN")
print(f"{'='*70}")
month_names = {1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
               7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}
days_by_month = df.groupby('month')['date'].nunique()
for month in range(1, 13):
    if month in days_by_month.index:
        print(f"  {month_names[month]}: {days_by_month[month]} days")
    else:
        print(f"  {month_names[month]}: 0 days")

print(f"\n{'='*70}")
print(f"Note: Based on sample of {len(df):,} records")
print(f"{'='*70}")
