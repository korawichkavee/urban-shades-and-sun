# ABOUTME: Renames YOLO label files to match image filenames by removing hash prefix
# ABOUTME: Converts format from "hash__imageID.txt" to "imageID.txt"

import os
from pathlib import Path

# Define paths
BASE_DIR = Path("/home/kieran/Documents/Python/sunny_day_SVI/city7sample/images_to_label/batch2/sunny_batch")
LABELS_DIR = BASE_DIR / "labels"

def extract_image_id(label_filename):
    """Extract the image ID from a label filename.

    Label format: hash__imageID.txt
    Returns: imageID (without extension)
    """
    stem = Path(label_filename).stem
    if "__" in stem:
        return stem.split("__")[1]
    return stem

def main():
    for split in ["train", "val"]:
        split_dir = LABELS_DIR / split
        if not split_dir.exists():
            print(f"Directory not found: {split_dir}")
            continue

        label_files = [f for f in os.listdir(split_dir) if f.endswith('.txt')]
        renamed_count = 0

        print(f"\nProcessing {split}/ directory...")
        print(f"Found {len(label_files)} label files")

        for label_file in label_files:
            if "__" in label_file:
                image_id = extract_image_id(label_file)
                new_filename = f"{image_id}.txt"

                old_path = split_dir / label_file
                new_path = split_dir / new_filename

                old_path.rename(new_path)
                renamed_count += 1

        print(f"Renamed {renamed_count} files")

    print("\nLabel renaming complete!")

if __name__ == "__main__":
    main()
