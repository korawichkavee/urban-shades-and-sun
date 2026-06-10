#!/usr/bin/env python3
"""
Analyze spatiotemporal coverage of img_dat(1).csv
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys

print("Loading data...")
# Read CSV in chunks to handle large file
chunksize = 100000
chunks = []

# First, let's sample the data to understand coverage patterns
for i, chunk in enumerate(pd.read_csv('data/img_dat(1).csv',
                                      names=['id', 'filename', 'url', 'size', 'timestamp'],
                                      chunksize=chunksize)):
    chunks.append(chunk)
    if i % 10 == 0:
        print(f"Processed {(i+1) * chunksize:,} rows...")
    # Limit to first 50 chunks for initial analysis (5M rows)
    if i >= 49:
        break

print("\nCombining chunks...")
df = pd.concat(chunks, ignore_index=True)
print(f"Loaded {len(df):,} rows for analysis")

# Parse timestamps
print("\nParsing timestamps...")
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Extract camera IDs from URLs
df['camera_id'] = df['url'].str.extract(r'cameras/([^/]+)/image')

# Basic statistics
print("\n" + "="*70)
print("BASIC STATISTICS")
print("="*70)
print(f"Total records analyzed: {len(df):,}")
print(f"Unique cameras: {df['camera_id'].nunique():,}")
print(f"Unique image IDs: {df['id'].nunique():,}")

# Temporal coverage
print("\n" + "="*70)
print("TEMPORAL COVERAGE")
print("="*70)
print(f"Start date: {df['timestamp'].min()}")
print(f"End date: {df['timestamp'].max()}")
print(f"Total time span: {df['timestamp'].max() - df['timestamp'].min()}")

# Group by date to see daily coverage
df['date'] = df['timestamp'].dt.date
daily_counts = df.groupby('date').size()
print(f"\nRecords per day:")
print(f"  Mean: {daily_counts.mean():,.0f}")
print(f"  Median: {daily_counts.median():,.0f}")
print(f"  Min: {daily_counts.min():,}")
print(f"  Max: {daily_counts.max():,}")

# Check for gaps in dates
date_range = pd.date_range(start=df['timestamp'].min().date(),
                           end=df['timestamp'].max().date(),
                           freq='D')
missing_dates = set(date_range.date) - set(daily_counts.index)
if missing_dates:
    print(f"\n⚠️  MISSING DATES: {len(missing_dates)} days with no data")
    if len(missing_dates) <= 20:
        for date in sorted(missing_dates):
            print(f"  - {date}")
else:
    print("\n✓ No missing dates in the analyzed range")

# Spatial coverage (per camera)
print("\n" + "="*70)
print("SPATIAL COVERAGE")
print("="*70)
camera_counts = df.groupby('camera_id').size().sort_values(ascending=False)
print(f"\nRecords per camera:")
print(f"  Mean: {camera_counts.mean():,.0f}")
print(f"  Median: {camera_counts.median():,.0f}")
print(f"  Min: {camera_counts.min():,}")
print(f"  Max: {camera_counts.max():,}")

print(f"\nTop 10 cameras by record count:")
for i, (cam, count) in enumerate(camera_counts.head(10).items(), 1):
    print(f"  {i:2d}. {cam}: {count:,} records")

print(f"\nBottom 10 cameras by record count:")
for i, (cam, count) in enumerate(camera_counts.tail(10).items(), 1):
    print(f"  {i:2d}. {cam}: {count:,} records")

# Temporal gaps per camera
print("\n" + "="*70)
print("TEMPORAL GAPS ANALYSIS")
print("="*70)
print("Analyzing time gaps between consecutive images per camera...")

gaps_summary = []
for camera_id in df['camera_id'].unique()[:50]:  # Check first 50 cameras
    cam_data = df[df['camera_id'] == camera_id].sort_values('timestamp')
    if len(cam_data) > 1:
        time_diffs = cam_data['timestamp'].diff().dt.total_seconds() / 60  # minutes
        gaps_summary.append({
            'camera_id': camera_id,
            'n_records': len(cam_data),
            'mean_gap_min': time_diffs.mean(),
            'median_gap_min': time_diffs.median(),
            'max_gap_min': time_diffs.max(),
        })

gaps_df = pd.DataFrame(gaps_summary)
print(f"\nTime gaps between consecutive images (minutes):")
print(f"  Mean gap: {gaps_df['mean_gap_min'].mean():.1f} minutes")
print(f"  Median gap: {gaps_df['median_gap_min'].median():.1f} minutes")

large_gaps = gaps_df[gaps_df['max_gap_min'] > 60*24]  # > 1 day
if len(large_gaps) > 0:
    print(f"\n⚠️  {len(large_gaps)} cameras have gaps > 24 hours:")
    for _, row in large_gaps.head(10).iterrows():
        print(f"  Camera {row['camera_id'][:8]}... : max gap = {row['max_gap_min']/60:.1f} hours")

print("\n" + "="*70)
print("ANALYSIS COMPLETE")
print("="*70)
print(f"Note: This analysis was performed on a sample of {len(df):,} records")
print("For full coverage analysis, modify the chunk limit in the script.")
