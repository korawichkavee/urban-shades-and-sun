#!/usr/bin/env python3
# ABOUTME: Converts Label Studio JSON annotations to YOLO polygon format dataset
# ABOUTME: Creates train/val split with images and labels for inshade/outshade classification

import json
import shutil
import random
from pathlib import Path
from collections import defaultdict

# Define paths
BASE_DIR = Path("/home/kieran/Documents/Python/sunny_day_SVI/city7sample")
JSON_FILE = BASE_DIR / "images_to_label/batch2/new_labeled.json"
SOURCE_IMAGES_DIR = BASE_DIR / "Buenos-Airesimg/walk_images"
OUTPUT_DIR = BASE_DIR / "images_to_label/batch2/sunny_batch_from_json"

# Split ratio
VAL_RATIO = 0.3

# Class mapping (Person=0 ignored, inshade=1, outshade=2)
CLASS_MAP = {
    "inshade": 1,
    "outshade": 2
}

def extract_image_id_from_url(url):
    """Extract image ID from Label Studio URL.

    URL format: http://host.docker.internal:8000/sunny200_1/106729198169778.jpeg
    Returns: 106729198169778
    """
    filename = url.split('/')[-1]
    return filename.replace('.jpeg', '')

def bbox_to_polygon(x, y, width, height):
    """Convert bounding box (percentage) to polygon format (normalized).

    Args:
        x, y: Top-left corner in percentage (0-100)
        width, height: Box dimensions in percentage (0-100)

    Returns:
        List of 8 values: [x1, y1, x2, y2, x3, y3, x4, y4] normalized to 0-1
        Corners are: top-left, top-right, bottom-right, bottom-left
    """
    # Convert to normalized coordinates (0-1)
    x_norm = x / 100.0
    y_norm = y / 100.0
    width_norm = width / 100.0
    height_norm = height / 100.0

    # Calculate four corners
    x1, y1 = x_norm, y_norm  # top-left
    x2, y2 = x_norm + width_norm, y_norm  # top-right
    x3, y3 = x_norm + width_norm, y_norm + height_norm  # bottom-right
    x4, y4 = x_norm, y_norm + height_norm  # bottom-left

    return [x1, y1, x2, y2, x3, y3, x4, y4]

def parse_annotations(json_data):
    """Parse JSON annotations and extract image data with labels.

    Returns:
        dict: {image_id: [(class_id, polygon), ...]}
    """
    image_annotations = {}

    for task in json_data:
        # Extract image ID from URL
        image_url = task['data']['image']
        image_id = extract_image_id_from_url(image_url)

        # Skip if no annotations
        if not task['annotations']:
            continue

        # Use the first annotation (there should only be one per task)
        annotation = task['annotations'][0]
        result = annotation['result']

        # Group results by ID (bbox and shade choice share same ID)
        result_groups = defaultdict(dict)
        for item in result:
            item_id = item['id']
            if item['type'] == 'rectanglelabels':
                result_groups[item_id]['bbox'] = item['value']
            elif item['type'] == 'choices':
                result_groups[item_id]['shade'] = item['value']['choices'][0]

        # Convert to polygon format
        labels = []
        for item_id, data in result_groups.items():
            # Skip if missing bbox or shade, or if shade is not in our class map
            if 'bbox' not in data or 'shade' not in data:
                continue

            shade = data['shade']
            if shade not in CLASS_MAP:
                continue

            bbox = data['bbox']
            class_id = CLASS_MAP[shade]
            polygon = bbox_to_polygon(bbox['x'], bbox['y'], bbox['width'], bbox['height'])
            labels.append((class_id, polygon))

        # Only add images that have at least one valid annotation
        if labels:
            image_annotations[image_id] = labels

    return image_annotations

def create_yolo_dataset(image_annotations, output_dir, source_images_dir, val_ratio):
    """Create YOLO dataset with train/val split.

    Args:
        image_annotations: dict mapping image_id to list of (class_id, polygon) tuples
        output_dir: Path to output directory
        source_images_dir: Path to source images
        val_ratio: Fraction of data for validation
    """
    # Create directory structure
    images_train_dir = output_dir / "images/train"
    images_val_dir = output_dir / "images/val"
    labels_train_dir = output_dir / "labels/train"
    labels_val_dir = output_dir / "labels/val"

    for dir_path in [images_train_dir, images_val_dir, labels_train_dir, labels_val_dir]:
        dir_path.mkdir(parents=True, exist_ok=True)

    # Split into train/val
    image_ids = list(image_annotations.keys())
    random.shuffle(image_ids)
    val_count = int(len(image_ids) * val_ratio)
    val_ids = set(image_ids[:val_count])

    print(f"\nDataset split:")
    print(f"  Training: {len(image_ids) - val_count} images")
    print(f"  Validation: {val_count} images")

    # Process each image
    images_copied = 0
    images_missing = 0

    for image_id in image_ids:
        # Determine split
        is_val = image_id in val_ids
        image_dest_dir = images_val_dir if is_val else images_train_dir
        label_dest_dir = labels_val_dir if is_val else labels_train_dir

        # Copy image
        source_image = source_images_dir / f"{image_id}.jpeg"
        if source_image.exists():
            dest_image = image_dest_dir / f"{image_id}.jpeg"
            shutil.copy2(str(source_image), str(dest_image))
            images_copied += 1
        else:
            print(f"  Warning: Image not found: {image_id}.jpeg")
            images_missing += 1
            continue

        # Write label file
        label_file = label_dest_dir / f"{image_id}.txt"
        with open(label_file, 'w') as f:
            for class_id, polygon in image_annotations[image_id]:
                # Format: class_id x1 y1 x2 y2 x3 y3 x4 y4
                line = f"{class_id} " + " ".join(f"{coord}" for coord in polygon)
                f.write(line + "\n")

    print(f"\nImages copied: {images_copied}")
    if images_missing > 0:
        print(f"Images missing: {images_missing}")

    return images_copied, images_missing

def create_config_files(output_dir):
    """Create data.yaml and classes.txt files."""
    # Create data.yaml
    data_yaml_content = f"""
path: {output_dir}
train: images/train
val: images/val

nc: 3
names: ['person','inshade','outshade']
"""
    with open(output_dir / "data.yaml", 'w') as f:
        f.write(data_yaml_content)

    # Create classes.txt
    classes_content = """Person
inshade
outshade
"""
    with open(output_dir / "classes.txt", 'w') as f:
        f.write(classes_content)

    print(f"\nCreated configuration files:")
    print(f"  {output_dir / 'data.yaml'}")
    print(f"  {output_dir / 'classes.txt'}")

def main():
    print("="*60)
    print("Converting Label Studio JSON to YOLO Polygon Format")
    print("="*60)

    # Verify paths exist
    if not JSON_FILE.exists():
        print(f"ERROR: JSON file not found: {JSON_FILE}")
        return

    if not SOURCE_IMAGES_DIR.exists():
        print(f"ERROR: Source images directory not found: {SOURCE_IMAGES_DIR}")
        return

    # Load JSON
    print(f"\nLoading annotations from: {JSON_FILE.name}")
    with open(JSON_FILE, 'r') as f:
        json_data = json.load(f)

    print(f"  Total tasks in JSON: {len(json_data)}")

    # Parse annotations
    print("\nParsing annotations...")
    image_annotations = parse_annotations(json_data)
    print(f"  Images with valid annotations: {len(image_annotations)}")

    # Count total annotations by class
    inshade_count = 0
    outshade_count = 0
    for labels in image_annotations.values():
        for class_id, _ in labels:
            if class_id == 1:
                inshade_count += 1
            elif class_id == 2:
                outshade_count += 1

    print(f"  Total annotations:")
    print(f"    inshade: {inshade_count}")
    print(f"    outshade: {outshade_count}")

    # Create dataset
    print(f"\nCreating YOLO dataset in: {OUTPUT_DIR}")
    create_yolo_dataset(
        image_annotations,
        OUTPUT_DIR,
        SOURCE_IMAGES_DIR,
        VAL_RATIO
    )

    # Create config files
    create_config_files(OUTPUT_DIR)

    print("\n" + "="*60)
    print("Dataset creation complete!")
    print("="*60)
    print(f"\nOutput directory: {OUTPUT_DIR}")
    print(f"  images/train: {len([f for f in (OUTPUT_DIR / 'images/train').glob('*.jpeg')])} images")
    print(f"  images/val: {len([f for f in (OUTPUT_DIR / 'images/val').glob('*.jpeg')])} images")
    print(f"  labels/train: {len([f for f in (OUTPUT_DIR / 'labels/train').glob('*.txt')])} labels")
    print(f"  labels/val: {len([f for f in (OUTPUT_DIR / 'labels/val').glob('*.txt')])} labels")
    print()

if __name__ == "__main__":
    main()
