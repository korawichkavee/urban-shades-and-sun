#!/usr/bin/env python3
# ABOUTME: Small-scale validation test for University Park, PA pipeline
# ABOUTME: Fetches ~5 images and verifies download, analysis, and output formatting before full run

import sys
from pathlib import Path
import pandas as pd
import logging
import asyncio
import shutil
from university_park_svi_pipeline import (
    setup_logging,
    fetch_metadata,
    download_images_batch_async,
    MAPILLARY_TOKEN,
    CITY_CONFIG,
)
import mapillary.interface as mly
from sunny_shade_pipeline import SunnyShadePipeline


TEST_IMAGES = 5


def test_pipeline(output_dir, pipeline, logger):
    """Validate all pipeline steps with a small number of images.

    Returns:
        True if all steps pass, False otherwise
    """
    city_slug = CITY_CONFIG['name'].replace(' ', '-').lower()
    city_dir = output_dir / city_slug
    city_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 80)
    logger.info(f"TEST: {CITY_CONFIG['name']}, {CITY_CONFIG['state']} (limited to {TEST_IMAGES} images)")
    logger.info("=" * 80)

    # Step 1: Fetch metadata with small bbox for speed
    logger.info("Step 1: Metadata fetch (small 1km bbox)...")
    csv_path = fetch_metadata(city_dir, logger, bbox_size=0.01)
    if not csv_path or not csv_path.exists():
        logger.error("FAILED: Could not fetch metadata")
        return False

    df = pd.read_csv(csv_path)
    logger.info(f"Small bbox returned {len(df)} images")

    if len(df) == 0:
        logger.error("FAILED: No images found in test area")
        return False

    n_images = min(TEST_IMAGES, len(df))
    if n_images < TEST_IMAGES:
        logger.warning(f"Only {len(df)} images available in test area, using {n_images}")

    df_test = df.head(n_images)
    logger.info(f"Testing with {len(df_test)} images")

    # Step 2: Download images
    images_dir = city_dir / "images_test"
    images_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Step 2: Image download...")
    download_tasks = [(str(row['id']), f"{row['id']}.jpg") for _, row in df_test.iterrows()]

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    success, failed = loop.run_until_complete(
        download_images_batch_async(download_tasks, images_dir, logger, MAPILLARY_TOKEN)
    )
    loop.close()

    logger.info(f"Download: {success} success, {failed} failed")
    if success == 0:
        logger.error("FAILED: No images downloaded")
        return False

    # Step 3: Run analysis
    logger.info("Step 3: Sunny/shade analysis...")
    try:
        results = pipeline.process_folder_batch(images_dir, output_csv=None)
        logger.info(f"Analyzed {len(results)} images")

        if 'is_sunny' in results.columns:
            logger.info(f"  Sunny: {results['is_sunny'].sum()}/{len(results)}")
        if 'person_count' in results.columns:
            logger.info(f"  People detected: {results['person_count'].sum()}")
    except Exception as e:
        logger.error(f"FAILED: Analysis error: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Step 4: Cleanup
    logger.info("Step 4: Cleanup...")
    try:
        shutil.rmtree(images_dir)
        logger.info("  Cleanup successful")
    except Exception as e:
        logger.warning(f"  Cleanup warning: {e}")

    # Step 5: Metadata merge and output format check
    logger.info("Step 5: Metadata merge and output format...")
    try:
        df_test = df_test.copy()
        df_test['id'] = df_test['id'].astype(str)
        results['image_id'] = results['image_id'].astype(str)

        merged = df_test.merge(results, left_on='id', right_on='image_id', how='left')
        if 'image_id' in merged.columns:
            merged = merged.drop(columns=['image_id'])

        required_cols = ['id', 'captured_at', 'is_sunny']
        missing = [c for c in required_cols if c not in merged.columns]
        if missing:
            logger.error(f"FAILED: Missing required columns: {missing}")
            return False

        output_csv = city_dir / f"{city_slug}_test_analyzed.csv"
        merged.to_csv(output_csv, index=False)
        logger.info(f"  Output saved: {output_csv}")
        logger.info(f"  Columns: {list(merged.columns)}")

    except Exception as e:
        logger.error(f"FAILED: Merge/output error: {e}")
        import traceback
        traceback.print_exc()
        return False

    logger.info("")
    logger.info("=" * 80)
    logger.info("TEST PASSED - University Park, PA")
    logger.info("=" * 80)
    logger.info("")
    return True


def main():
    print("=" * 80)
    print("UNIVERSITY PARK, PA SVI PIPELINE TEST")
    print("=" * 80)
    print("")
    print("This test will:")
    print(f"  1. Fetch metadata from a small 1km bbox around {CITY_CONFIG['name']}, {CITY_CONFIG['state']}")
    print(f"  2. Download {TEST_IMAGES} images")
    print("  3. Run sunny/shade analysis (ViT + YOLO)")
    print("  4. Verify output format and required columns")
    print("  5. Clean up temporary files")
    print("")
    print("Expected duration: 2-5 minutes")
    print("=" * 80)
    print("")

    output_dir = Path("data/university_park_test")
    output_dir.mkdir(parents=True, exist_ok=True)

    logger = setup_logging(output_dir)
    mly.set_access_token(MAPILLARY_TOKEN)

    # Locate models - check package layout first, then dev layout
    script_dir = Path(__file__).parent
    package_root = script_dir.parent.parent

    vit_candidates = [
        package_root / "models" / "vit_binary.pth",
        Path("models/vit_binary.pth"),
        Path("outputs/models/vit_binary.pth"),
    ]
    yolo_candidates = [
        package_root / "models" / "yolo_best.pt",
        Path("models/yolo_best.pt"),
        Path("outputs/models/sunny_batch_train4/weights/best.pt"),
    ]

    vit_model = next((str(c) for c in vit_candidates if c.exists()), None)
    yolo_model = next((str(c) for c in yolo_candidates if c.exists()), None)

    if not vit_model:
        logger.error(f"ViT model not found. Tried: {[str(c) for c in vit_candidates]}")
        return 1
    if not yolo_model:
        logger.error(f"YOLO model not found. Tried: {[str(c) for c in yolo_candidates]}")
        return 1

    logger.info(f"ViT model:  {vit_model}")
    logger.info(f"YOLO model: {yolo_model}")

    try:
        pipeline = SunnyShadePipeline(vit_model_path=vit_model, yolo_model_path=yolo_model)
        logger.info("Models loaded")
        logger.info("")
    except Exception as e:
        logger.error(f"Failed to load models: {e}")
        return 1

    passed = test_pipeline(output_dir, pipeline, logger)

    print("")
    print("=" * 80)
    if passed:
        print("ALL TESTS PASSED")
        print("=" * 80)
        print("")
        print("The pipeline is ready for full run:")
        print("  python scripts/pipelines/university_park_svi_pipeline.py")
        print("")
        print("Or with tmux for overnight:")
        print("  tmux new-session -d -s upk_svi \\")
        print("    'python scripts/pipelines/university_park_svi_pipeline.py \\")
        print("       > logs/university_park_svi.log 2>&1'")
        print("")
    else:
        print("TEST FAILED")
        print("=" * 80)
        print("")
        print(f"Check logs in {output_dir}/ for details")
        print("")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
