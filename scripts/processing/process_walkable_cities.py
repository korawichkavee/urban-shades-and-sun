# ABOUTME: Processes walkable images through sunny/shade pipeline for all cities
# ABOUTME: Merges results back into walkable CSV files with new columns for shade analysis

import sys
import pandas as pd
from pathlib import Path
from sunny_shade_pipeline import SunnyShadePipeline

# City configuration
cities = [
    ("Buenos-Aires_walkable_1032717330.csv", "Buenos-Airesimg", "Buenos Aires"),
    ("Cape-Town_walkable_1710680650.csv", "Cape-Townimg", "Cape Town"),
    ("Istanbul_walkable_1792756324.csv", "Istanbulimg", "Istanbul"),
    ("Madrid_walkable_1724616994.csv", "Madridimg", "Madrid"),
    ("Mumbai_walkable_1356226629.csv", "Mumbaiimg", "Mumbai"),
    ("Singapore_walkable_1702341327.csv", "Singaporeimg", "Singapore"),
]

base_dir = Path("/home/kieran/Documents/Python/sunny_day_SVI/city7sample")

print("=" * 70)
print("Processing Walkable Images with Sunny/Shade Pipeline")
print("=" * 70)
print()

# Initialize pipeline once (loads models)
print("Initializing models...")
pipeline = SunnyShadePipeline(
    vit_model_path="vit_binary.pth",
    yolo_model_path="sunny_batch_train4/weights/best.pt"
)
print()

for csv_file, img_folder, city_name in cities:
    print(f"{'='*70}")
    print(f"Processing {city_name}")
    print(f"{'='*70}")

    # Paths
    csv_path = base_dir / csv_file
    walkable_images_dir = base_dir / img_folder / "walkable_images"
    temp_results_csv = base_dir / f"{img_folder}_shade_results.csv"

    # Check paths exist
    if not csv_path.exists():
        print(f"  ✗ CSV not found: {csv_path}")
        print()
        continue

    if not walkable_images_dir.exists():
        print(f"  ✗ Images directory not found: {walkable_images_dir}")
        print()
        continue

    # Count images
    image_count = len(list(walkable_images_dir.glob("*.jpeg"))) + len(list(walkable_images_dir.glob("*.jpg")))
    print(f"  Images to process: {image_count}")

    if image_count == 0:
        print(f"  ✗ No images found in {walkable_images_dir}")
        print()
        continue

    # Run pipeline
    print(f"  Running sunny/shade analysis...")
    try:
        results_df = pipeline.process_folder(walkable_images_dir, output_csv=str(temp_results_csv))
    except Exception as e:
        print(f"  ✗ Error running pipeline: {e}")
        print()
        continue

    # Load original CSV
    print(f"  Merging results with original CSV...")
    original_df = pd.read_csv(csv_path)

    # Convert id to string for matching
    original_df['id'] = original_df['id'].astype(str)
    results_df['image_id'] = results_df['image_id'].astype(str)

    # Merge on image_id = id
    merged_df = original_df.merge(
        results_df,
        left_on='id',
        right_on='image_id',
        how='left'
    )

    # Drop duplicate image_id column
    if 'image_id' in merged_df.columns:
        merged_df = merged_df.drop(columns=['image_id'])

    # Save merged CSV
    merged_df.to_csv(csv_path, index=False)
    print(f"  ✓ Saved updated CSV: {csv_path}")
    print(f"    Added columns: is_sunny, sunny_probability, person_count, inshade_count, outshade_count")

    # Clean up temp file
    if temp_results_csv.exists():
        temp_results_csv.unlink()

    # Summary
    sunny_count = merged_df['is_sunny'].sum() if 'is_sunny' in merged_df.columns else 0
    print(f"    Total rows: {len(merged_df)}")
    print(f"    Sunny images: {sunny_count}")
    print()

print("=" * 70)
print("Processing Complete!")
print("=" * 70)
