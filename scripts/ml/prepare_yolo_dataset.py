# ABOUTME: Organizes images and labels into YOLO-compatible train/val split structure
# ABOUTME: Randomly splits labels into test/val folders and copies matching images from source directory

import os
import shutil
import random
from pathlib import Path

# Define paths
BASE_DIR = Path("/home/kieran/Documents/Python/sunny_day_SVI/city7sample")
LABELS_DIR = BASE_DIR / "images_to_label/batch2/sunny_batch/labels"
IMAGES_BASE_DIR = BASE_DIR / "images_to_label/batch2/sunny_batch/images"
SOURCE_IMAGES_DIR = BASE_DIR / "Buenos-Airesimg/walk_images"

# Split ratio
VAL_RATIO = 0.3

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
    # Get all label files
    label_files = [f for f in os.listdir(LABELS_DIR) if f.endswith('.txt')]

    if not label_files:
        print("No label files found!")
        return

    print(f"Found {len(label_files)} label files")

    # Shuffle and split
    random.shuffle(label_files)
    val_count = int(len(label_files) * VAL_RATIO)
    val_labels = label_files[:val_count]
    test_labels = label_files[val_count:]

    print(f"Val split: {len(val_labels)} files ({len(val_labels)/len(label_files)*100:.1f}%)")
    print(f"Train split: {len(test_labels)} files ({len(test_labels)/len(label_files)*100:.1f}%)")

    # Create directory structure
    labels_train_dir = LABELS_DIR / "train"
    labels_val_dir = LABELS_DIR / "val"
    images_train_dir = IMAGES_BASE_DIR / "train"
    images_val_dir = IMAGES_BASE_DIR / "val"

    for dir_path in [labels_train_dir, labels_val_dir, images_train_dir, images_val_dir]:
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {dir_path}")

    # Move labels and copy corresponding images
    splits = [
        ("train", test_labels, labels_train_dir, images_train_dir),
        ("val", val_labels, labels_val_dir, images_val_dir)
    ]

    for split_name, label_list, label_dest, image_dest in splits:
        print(f"\nProcessing {split_name} split...")
        images_found = 0
        images_missing = 0

        for label_file in label_list:
            # Extract image ID and create new label filename (without hash prefix)
            image_id = extract_image_id(label_file)
            new_label_filename = f"{image_id}.txt"

            # Move label file with new name (matching image filename)
            src_label = LABELS_DIR / label_file
            dst_label = label_dest / new_label_filename
            shutil.move(str(src_label), str(dst_label))

            # Find and copy matching image
            source_image = SOURCE_IMAGES_DIR / f"{image_id}.jpeg"

            if source_image.exists():
                dst_image = image_dest / f"{image_id}.jpeg"
                shutil.copy2(str(source_image), str(dst_image))
                images_found += 1
            else:
                images_missing += 1
                print(f"  Warning: Image not found for label {label_file} (looking for {image_id}.jpeg)")

        print(f"  Moved {len(label_list)} labels")
        print(f"  Copied {images_found} images")
        if images_missing > 0:
            print(f"  Missing {images_missing} images")

    print("\nDataset preparation complete!")
    print(f"\nFinal structure:")
    print(f"  Labels: {LABELS_DIR}")
    print(f"    - train/: {len(test_labels)} files")
    print(f"    - val/: {len(val_labels)} files")
    print(f"  Images: {IMAGES_BASE_DIR}")
    print(f"    - train/: images")
    print(f"    - val/: images")

if __name__ == "__main__":
    main()
