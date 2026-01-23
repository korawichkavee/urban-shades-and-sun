# ABOUTME: Copies images from walk_images folders to walkable_images subfolders
# ABOUTME: Based on image IDs present in walkable CSV files with temperature data

import pandas as pd
from pathlib import Path
import shutil
from tqdm import tqdm

# City configuration: (csv_file, image_folder, city_name)
cities = [
    ("Buenos-Aires_walkable_1032717330.csv", "Buenos-Airesimg", "Buenos Aires"),
    ("Cape-Town_walkable_1710680650.csv", "Cape-Townimg", "Cape Town"),
    ("Istanbul_walkable_1792756324.csv", "Istanbulimg", "Istanbul"),
    ("Madrid_walkable_1724616994.csv", "Madridimg", "Madrid"),
    ("Mumbai_walkable_1356226629.csv", "Mumbaiimg", "Mumbai"),
    ("Singapore_walkable_1702341327.csv", "Singaporeimg", "Singapore"),
]

base_dir = Path("/home/kieran/Documents/Python/sunny_day_SVI/city7sample")

print("=" * 60)
print("Copying Walkable Images with Temperature Data")
print("=" * 60)
print()

total_copied = 0
total_missing = 0

for csv_file, img_folder, city_name in cities:
    print(f"Processing {city_name}...")

    # Read CSV
    csv_path = base_dir / csv_file
    if not csv_path.exists():
        print(f"  ✗ CSV not found: {csv_path}")
        continue

    df = pd.read_csv(csv_path)
    print(f"  Found {len(df)} walkable images in CSV")

    # Get image IDs
    image_ids = df['id'].astype(str).tolist()

    # Setup directories - detect source directory automatically
    img_folder_path = base_dir / img_folder
    dest_dir = img_folder_path / "walkable_images"

    # Try walk_images first (Buenos Aires structure)
    source_dir = img_folder_path / "walk_images"

    # If walk_images doesn't exist, look for 1_<number> pattern
    if not source_dir.exists():
        subdirs = [d for d in img_folder_path.iterdir() if d.is_dir() and d.name.startswith("1_")]
        if subdirs:
            source_dir = subdirs[0]
        else:
            print(f"  ✗ No source directory found in {img_folder_path}")
            continue

    print(f"  Using source: {source_dir.name}")

    # Create destination directory
    dest_dir.mkdir(exist_ok=True)

    # Copy images
    copied = 0
    missing = 0

    for image_id in tqdm(image_ids, desc=f"  Copying {city_name}", leave=False):
        # Try with .jpeg extension first
        source_file = source_dir / f"{image_id}.jpeg"

        if not source_file.exists():
            # Try .jpg
            source_file = source_dir / f"{image_id}.jpg"

        if source_file.exists():
            dest_file = dest_dir / source_file.name
            shutil.copy2(source_file, dest_file)
            copied += 1
        else:
            missing += 1

    print(f"  ✓ Copied {copied} images to {dest_dir}")
    if missing > 0:
        print(f"  ⚠ {missing} images not found in source directory")

    total_copied += copied
    total_missing += missing
    print()

print("=" * 60)
print("Summary")
print("=" * 60)
print(f"Total images copied: {total_copied}")
print(f"Total images missing: {total_missing}")
print()
