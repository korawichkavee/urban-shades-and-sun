#!/usr/bin/env python3
# ABOUTME: Filters snapped images for walkable street types and copies to walk_images folders
# ABOUTME: Creates subsets of images from residential/pedestrian streets for weather analysis

import pandas as pd
import shutil
import os
from pathlib import Path
from tqdm import tqdm

# OSM highway types considered "walkable" for street view analysis
WALKABLE_HIGHWAY_TYPES = {
    'residential',
    'pedestrian',
    'footway',
    'living_street',
    'path',
    'track',
    'service',
    'unclassified',  # Often smaller local roads
    'tertiary',      # Smaller roads
    'tertiary_link'
}

# City info
CITY_INFO = {
    'Buenos-Aires': '1032717330',
    'Cape-Town': '1710680650',
    'Istanbul': '1792756324',
    'Madrid': '1724616994',
    'Mumbai': '1356226629',
    'Singapore': '1702341327',
    'Tokyo': '1392685764'
}

def filter_walkable_images(snapped_csv_path, city_name):
    """Filter snapped images for walkable street types.

    Args:
        snapped_csv_path: Path to snapped CSV with OSM road data
        city_name: Name of city (e.g., 'Buenos-Aires')

    Returns:
        DataFrame of images on walkable streets
    """
    print(f"\n  Loading snapped data from {snapped_csv_path.name}")
    df = pd.read_csv(snapped_csv_path)

    print(f"    Total snapped images: {len(df)}")

    # Filter for walkable highway types
    if 'highway' not in df.columns:
        print(f"    ERROR: 'highway' column not found in snapped data")
        return None

    # Count images by highway type
    highway_counts = df['highway'].value_counts()
    print(f"    Highway types found: {len(highway_counts)}")
    print(f"    Top 5 types: {dict(list(highway_counts.head().items()))}")

    # Filter for walkable types
    walkable_df = df[df['highway'].isin(WALKABLE_HIGHWAY_TYPES)]
    print(f"    Walkable street images: {len(walkable_df)} ({len(walkable_df)/len(df)*100:.1f}%)")

    if len(walkable_df) == 0:
        print(f"    WARNING: No walkable streets found!")

    return walkable_df

def copy_walk_images(walkable_df, city_name, base_dir):
    """Copy images from walkable streets to walk_images folder.

    Args:
        walkable_df: DataFrame of images on walkable streets
        city_name: Name of city
        base_dir: Base directory containing city data
    """
    # Determine source images directory
    source_img_dir = base_dir / f"{city_name}img"

    # Check multiple possible subdirectories for images
    possible_subdirs = ['walk_images', 'images', '']
    img_source = None

    for subdir in possible_subdirs:
        test_dir = source_img_dir / subdir if subdir else source_img_dir
        if test_dir.exists():
            # Check if there are any jpeg files
            test_files = list(test_dir.glob('*.jpeg')) + list(test_dir.glob('*.jpg'))
            if test_files:
                img_source = test_dir
                break

    if img_source is None:
        print(f"    ERROR: Could not find image source directory for {city_name}")
        print(f"    Tried: {source_img_dir}")
        return 0, 0

    print(f"    Image source: {img_source}")

    # Create walk_images directory
    walk_img_dir = source_img_dir / "walk_images"
    walk_img_dir.mkdir(parents=True, exist_ok=True)

    # Copy images
    copied = 0
    missing = 0

    print(f"    Copying {len(walkable_df)} images...")
    for idx, row in tqdm(walkable_df.iterrows(), total=len(walkable_df), desc="    Copying"):
        img_id = str(row['id'])

        # Try different extensions
        source_img = None
        for ext in ['.jpeg', '.jpg', '.JPEG', '.JPG']:
            test_path = img_source / f"{img_id}{ext}"
            if test_path.exists():
                source_img = test_path
                break

        if source_img and source_img.exists():
            dest_img = walk_img_dir / source_img.name
            if not dest_img.exists():  # Don't re-copy if already exists
                shutil.copy2(source_img, dest_img)
                copied += 1
            else:
                copied += 1  # Count as copied (already there)
        else:
            missing += 1

    print(f"    Copied: {copied}, Missing: {missing}")
    return copied, missing

def create_walkable_csv(walkable_df, city_name, base_dir):
    """Create a CSV of just the walkable images for weather processing.

    Args:
        walkable_df: DataFrame of images on walkable streets
        city_name: Name of city
        base_dir: Base directory containing city data
    """
    # Get original CSV to merge with walkable data
    city_id = CITY_INFO[city_name]
    original_csv = base_dir / f"{city_name}_{city_id}.csv"

    if not original_csv.exists():
        print(f"    WARNING: Original CSV not found: {original_csv}")
        return None

    orig_df = pd.read_csv(original_csv)

    # Merge to get full row data for walkable images
    walkable_ids = set(walkable_df['id'].astype(str))
    walkable_full = orig_df[orig_df['id'].astype(str).isin(walkable_ids)]

    # Save walkable subset
    output_csv = base_dir / f"{city_name}_walkable_{city_id}.csv"
    walkable_full.to_csv(output_csv, index=False)
    print(f"    Saved walkable CSV: {output_csv.name} ({len(walkable_full)} rows)")

    return output_csv

def main():
    """Filter all cities for walkable streets and copy images."""

    print("="*60)
    print("Filter Walkable Streets and Copy Images")
    print("="*60)

    base_dir = Path('/home/kieran/Documents/Python/sunny_day_SVI/city7sample')
    snapped_dir = base_dir / 'snapped'

    if not snapped_dir.exists():
        print(f"ERROR: Snapped directory not found: {snapped_dir}")
        return

    # Get all snapped CSVs
    snapped_files = list(snapped_dir.glob('*_snapped.csv'))
    print(f"\nFound {len(snapped_files)} snapped CSV files")

    total_walkable = 0
    total_copied = 0
    success_count = 0
    error_count = 0

    for snapped_file in snapped_files:
        try:
            # Extract city name from filename
            city_name = snapped_file.stem.replace('_snapped', '')
            print(f"\nProcessing {city_name}...")

            # Filter for walkable streets
            walkable_df = filter_walkable_images(snapped_file, city_name)

            if walkable_df is None or len(walkable_df) == 0:
                print(f"  ✗ No walkable images found for {city_name}")
                error_count += 1
                continue

            total_walkable += len(walkable_df)

            # Copy images to walk_images folder
            copied, missing = copy_walk_images(walkable_df, city_name, base_dir)
            total_copied += copied

            # Create walkable CSV for weather processing
            walkable_csv = create_walkable_csv(walkable_df, city_name, base_dir)

            print(f"  ✓ {city_name} complete - {len(walkable_df)} walkable images, {copied} copied")
            success_count += 1

        except Exception as e:
            print(f"  ✗ ERROR processing {city_name}:")
            print(f"    {type(e).__name__}: {str(e)}")
            error_count += 1

    print("\n" + "="*60)
    print("Processing Complete!")
    print("="*60)
    print(f"Cities processed: {success_count}")
    print(f"Errors: {error_count}")
    print(f"Total walkable images: {total_walkable}")
    print(f"Total images copied: {total_copied}")
    print()

if __name__ == '__main__':
    main()
