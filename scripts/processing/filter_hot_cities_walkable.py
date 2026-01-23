#!/usr/bin/env python3
# ABOUTME: Filters snapped hot cities CSVs for walkable street types
# ABOUTME: Creates walkable subset CSVs with only images from pedestrian-friendly roads

import pandas as pd
import os
from pathlib import Path
from tqdm import tqdm
import glob

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

def filter_walkable_streets(snapped_csv_path, city_name, city_id):
    """Filter snapped CSV for walkable street types.

    Args:
        snapped_csv_path: Path to snapped CSV with OSM road data
        city_name: Name of city (e.g., 'Manila')
        city_id: City ID string

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
        return None

    return walkable_df

def create_walkable_csv(walkable_df, city_name, city_id, base_dir, output_dir):
    """Create a CSV of just the walkable images.

    Args:
        walkable_df: DataFrame of images on walkable streets
        city_name: Name of city
        city_id: City ID string
        base_dir: Base directory containing original CSVs
        output_dir: Directory to save walkable CSVs

    Returns:
        Path to created CSV or None
    """
    # Get original CSV to merge with walkable data (to ensure all original columns)
    original_csv = base_dir / f"{city_name}_{city_id}.csv"

    if not original_csv.exists():
        print(f"    WARNING: Original CSV not found: {original_csv}")
        # Use snapped data directly
        output_csv = output_dir / f"{city_name}_walkable_{city_id}.csv"
        walkable_df.to_csv(output_csv, index=False)
        print(f"    Saved walkable CSV: {output_csv.name} ({len(walkable_df)} rows)")
        return output_csv

    orig_df = pd.read_csv(original_csv)

    # Merge to get full original row data for walkable images
    # Use 'id' column to match
    walkable_ids = set(walkable_df['id'].astype(str))
    walkable_full = orig_df[orig_df['id'].astype(str).isin(walkable_ids)]

    # Save walkable subset
    output_csv = output_dir / f"{city_name}_walkable_{city_id}.csv"
    walkable_full.to_csv(output_csv, index=False)
    print(f"    Saved walkable CSV: {output_csv.name} ({len(walkable_full)} rows)")

    return output_csv

def main():
    """Filter all snapped hot cities for walkable streets."""

    print("="*80)
    print("Filter Hot Cities for Walkable Streets")
    print("="*80)

    base_dir = Path('/home/kieran/Documents/Python/sunny_day_SVI/hot_cities')
    snapped_dir = base_dir / 'snapped'
    output_dir = base_dir  # Save walkable CSVs in hot_cities folder

    if not snapped_dir.exists():
        print(f"ERROR: Snapped directory not found: {snapped_dir}")
        return

    # Get all snapped CSVs
    snapped_files = sorted(list(snapped_dir.glob('*_snapped.csv')))
    print(f"\nFound {len(snapped_files)} snapped CSV files")
    print("="*80)

    total_walkable = 0
    success_count = 0
    error_count = 0
    results = []

    for snapped_file in snapped_files:
        try:
            # Extract city name from filename
            city_name = snapped_file.stem.replace('_snapped', '')

            # Find matching original CSV to get city_id
            original_csvs = list(base_dir.glob(f"{city_name}_*.csv"))
            # Filter out _snapped and _walkable files
            original_csvs = [f for f in original_csvs if '_snapped' not in f.name and '_walkable' not in f.name]

            if not original_csvs:
                print(f"\n✗ {city_name} - Could not find original CSV")
                error_count += 1
                continue

            # Extract city_id from filename
            city_id = original_csvs[0].stem.split('_')[-1]

            print(f"\nProcessing {city_name} (ID: {city_id})...")

            # Filter for walkable streets
            walkable_df = filter_walkable_streets(snapped_file, city_name, city_id)

            if walkable_df is None or len(walkable_df) == 0:
                print(f"  ✗ No walkable images found for {city_name}")
                error_count += 1
                continue

            total_walkable += len(walkable_df)

            # Create walkable CSV
            walkable_csv = create_walkable_csv(walkable_df, city_name, city_id, base_dir, output_dir)

            print(f"  ✓ {city_name} complete - {len(walkable_df)} walkable images")
            success_count += 1

            results.append({
                'city': city_name,
                'total_snapped': len(pd.read_csv(snapped_file)),
                'walkable': len(walkable_df),
                'walkable_pct': len(walkable_df) / len(pd.read_csv(snapped_file)) * 100
            })

        except Exception as e:
            print(f"\n✗ ERROR processing {snapped_file.name}:")
            print(f"    {type(e).__name__}: {str(e)}")
            error_count += 1

    print("\n" + "="*80)
    print("Processing Complete!")
    print("="*80)
    print(f"Cities processed: {success_count}")
    print(f"Errors: {error_count}")
    print(f"Total walkable images: {total_walkable:,}")

    if results:
        print("\nSummary by city:")
        print("-" * 80)
        for r in sorted(results, key=lambda x: x['walkable'], reverse=True):
            print(f"{r['city']:25s} {r['walkable']:>6,} / {r['total_snapped']:>6,} ({r['walkable_pct']:>5.1f}%)")
    print()

if __name__ == '__main__':
    main()
