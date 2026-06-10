#!/usr/bin/env python3
"""
Analyze temporal coverage patterns per camera
"""
import pandas as pd
from collections import defaultdict

print("Scanning file for camera-specific temporal coverage...")

# Track dates per camera
camera_dates = defaultdict(set)
camera_records = defaultdict(int)
all_cameras = set()
chunk_num = 0

for chunk in pd.read_csv('data/img_dat(1).csv',
                         names=['id', 'filename', 'url', 'size', 'timestamp'],
                         usecols=['url', 'timestamp'],
                         chunksize=500000):

    # Extract camera IDs
    chunk['camera_id'] = chunk['url'].str.extract(r'cameras/([^/]+)/image')[0]
    chunk['date'] = pd.to_datetime(chunk['timestamp']).dt.date

    # Update tracking
    for camera_id, date in zip(chunk['camera_id'], chunk['date']):
        if pd.notna(camera_id):
            camera_dates[camera_id].add(date)
            camera_records[camera_id] += 1
            all_cameras.add(camera_id)

    chunk_num += 1
    if chunk_num % 10 == 0:
        print(f"  Processed {chunk_num * 500000:,} rows, tracking {len(all_cameras)} cameras...")

print(f"\n{'='*70}")
print("CAMERA COUNT")
print(f"{'='*70}")
print(f"Total unique cameras: {len(all_cameras)}")
print(f"Total records processed: {chunk_num * 500000:,}")

print(f"\n{'='*70}")
print("TEMPORAL COVERAGE BY CAMERA")
print(f"{'='*70}")

# Analyze coverage patterns
coverage_stats = []
for camera_id in all_cameras:
    dates = sorted(camera_dates[camera_id])
    if len(dates) > 0:
        span = (dates[-1] - dates[0]).days + 1
        coverage_stats.append({
            'camera_id': camera_id,
            'days_active': len(dates),
            'first_date': dates[0],
            'last_date': dates[-1],
            'span_days': span,
            'coverage_pct': 100 * len(dates) / span if span > 0 else 100,
            'records': camera_records[camera_id]
        })

coverage_df = pd.DataFrame(coverage_stats).sort_values('days_active', ascending=False)

print(f"\nDays active per camera:")
print(f"  Mean: {coverage_df['days_active'].mean():.1f} days")
print(f"  Median: {coverage_df['days_active'].median():.1f} days")
print(f"  Min: {coverage_df['days_active'].min()} days")
print(f"  Max: {coverage_df['days_active'].max()} days")

print(f"\nRecords per camera:")
print(f"  Mean: {coverage_df['records'].mean():,.0f}")
print(f"  Median: {coverage_df['records'].median():,.0f}")
print(f"  Min: {coverage_df['records'].min():,}")
print(f"  Max: {coverage_df['records'].max():,}")

print(f"\n{'='*70}")
print("CAMERAS WITH MOST DAYS ACTIVE")
print(f"{'='*70}")
for i, row in coverage_df.head(10).iterrows():
    print(f"  {row['camera_id'][:8]}...: {row['days_active']:3d} days "
          f"({row['first_date']} to {row['last_date']}, {row['records']:,} records)")

print(f"\n{'='*70}")
print("CAMERAS WITH FEWEST DAYS ACTIVE")
print(f"{'='*70}")
for i, row in coverage_df.tail(10).iterrows():
    print(f"  {row['camera_id'][:8]}...: {row['days_active']:3d} days "
          f"({row['first_date']} to {row['last_date']}, {row['records']:,} records)")

# Check if all cameras have same date range
all_first_dates = coverage_df['first_date'].unique()
all_last_dates = coverage_df['last_date'].unique()

print(f"\n{'='*70}")
print("DATE RANGE VARIATION")
print(f"{'='*70}")
print(f"Unique first dates: {len(all_first_dates)}")
print(f"Unique last dates: {len(all_last_dates)}")

if len(all_first_dates) > 1:
    print(f"\n⚠️  Cameras have different start dates:")
    print(f"  Earliest start: {coverage_df['first_date'].min()}")
    print(f"  Latest start: {coverage_df['first_date'].max()}")

if len(all_last_dates) > 1:
    print(f"\n⚠️  Cameras have different end dates:")
    print(f"  Earliest end: {coverage_df['last_date'].min()}")
    print(f"  Latest end: {coverage_df['last_date'].max()}")

# Check seasonal coverage variation
print(f"\n{'='*70}")
print("SEASONAL COVERAGE VARIATION")
print(f"{'='*70}")

season_map = {
    12: 'Winter', 1: 'Winter', 2: 'Winter',
    3: 'Spring', 4: 'Spring', 5: 'Spring',
    6: 'Summer', 7: 'Summer', 8: 'Summer',
    9: 'Fall', 10: 'Fall', 11: 'Fall'
}

camera_seasons = defaultdict(lambda: defaultdict(int))
for camera_id, dates in camera_dates.items():
    for date in dates:
        season = season_map[date.month]
        camera_seasons[camera_id][season] += 1

# Count cameras active in each season
cameras_per_season = defaultdict(int)
for camera_id, seasons in camera_seasons.items():
    for season in seasons:
        cameras_per_season[season] += 1

print(f"\nCameras active by season:")
for season in ['Winter', 'Spring', 'Summer', 'Fall']:
    count = cameras_per_season.get(season, 0)
    pct = 100 * count / len(all_cameras) if len(all_cameras) > 0 else 0
    print(f"  {season:8s}: {count:3d} cameras ({pct:.1f}%)")

print(f"\n{'='*70}")
print("ANALYSIS COMPLETE")
print(f"{'='*70}")
