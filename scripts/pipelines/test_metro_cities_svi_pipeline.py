#!/usr/bin/env python3
# ABOUTME: Small-scale test of metro cities pipeline with limited images
# ABOUTME: Validates download, analysis, and output formatting for all cities before full run

import sys
from pathlib import Path
import pandas as pd
import logging
import asyncio
import shutil
from tqdm import tqdm
from metro_cities_svi_pipeline import (
    setup_logging,
    fetch_city_metadata_bbox,
    download_images_batch_async,
    MAPILLARY_TOKEN,
    METRO_CITIES
)
import mapillary.interface as mly
from sunny_shade_pipeline import SunnyShadePipeline


TEST_IMAGES_PER_CITY = 5  # Test with 5 images per city


def test_city_limited(city_config, output_dir, pipeline, logger, max_images=5):
    """Test processing with limited number of images."""
    city_name = city_config['name'].replace(' ', '-').lower()
    city_dir = output_dir / city_name
    city_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 80)
    logger.info(f"TEST: {city_config['name']}, {city_config['state']} (limited to {max_images} images)")
    logger.info("=" * 80)

    # Step 1: Fetch metadata (use small bbox for testing - ~1km radius instead of ~10km)
    logger.info("Testing metadata fetch (using small 1km bbox)...")
    csv_path = fetch_city_metadata_bbox(city_config, city_dir, logger, bbox_size=0.01)
    if not csv_path or not csv_path.exists():
        logger.error("FAILED: Could not fetch metadata")
        return False

    # Load and limit metadata
    df = pd.read_csv(csv_path)
    logger.info(f"Small bbox dataset has {len(df)} images")

    # Check if we have enough images
    if len(df) < max_images:
        logger.warning(f"Only {len(df)} images available in test area, adjusting test size")
        max_images = len(df)

    if len(df) == 0:
        logger.error("FAILED: No images found in test area")
        return False

    df_limited = df.head(max_images)
    logger.info(f"Testing with {len(df_limited)} images")

    # Step 2: Test download
    images_dir = city_dir / "images_test"
    images_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Testing async download...")
    download_tasks = []
    for _, row in df_limited.iterrows():
        image_id = str(row['id'])
        filename = f"{image_id}.jpg"
        download_tasks.append((image_id, filename))

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    success, failed = loop.run_until_complete(
        download_images_batch_async(download_tasks, images_dir, logger, MAPILLARY_TOKEN)
    )
    loop.close()

    logger.info(f"Download results: {success} success, {failed} failed")

    if success == 0:
        logger.error("FAILED: No images downloaded")
        return False

    # Step 3: Test analysis
    logger.info("Testing sunny/shade analysis...")
    try:
        results = pipeline.process_folder(images_dir, output_csv=None)
        logger.info(f"Analysis results: {len(results)} images processed")

        if 'is_sunny' in results.columns:
            sunny_count = results['is_sunny'].sum()
            logger.info(f"  Sunny images: {sunny_count}/{len(results)}")

        if 'person_count' in results.columns:
            people_total = results['person_count'].sum()
            logger.info(f"  Total people detected: {people_total}")

    except Exception as e:
        logger.error(f"FAILED: Analysis error: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Step 4: Test cleanup
    logger.info("Testing cleanup...")
    try:
        shutil.rmtree(images_dir)
        logger.info("✓ Cleanup successful")
    except Exception as e:
        logger.warning(f"Cleanup warning: {e}")

    # Step 5: Test metadata merge and output format
    logger.info("Testing metadata merge and output format...")
    try:
        df_limited['id'] = df_limited['id'].astype(str)
        results['image_id'] = results['image_id'].astype(str)

        merged = df_limited.merge(
            results,
            left_on='id',
            right_on='image_id',
            how='left'
        )

        if 'image_id' in merged.columns:
            merged = merged.drop(columns=['image_id'])

        # Verify expected columns exist
        required_cols = ['id', 'captured_at', 'is_sunny']
        missing_cols = [col for col in required_cols if col not in merged.columns]
        if missing_cols:
            logger.error(f"FAILED: Missing required columns: {missing_cols}")
            return False

        output_csv = city_dir / f"{city_name}_test_analyzed.csv"
        merged.to_csv(output_csv, index=False)
        logger.info(f"✓ Merged CSV saved: {output_csv}")
        logger.info(f"  Columns: {list(merged.columns)}")

    except Exception as e:
        logger.error(f"FAILED: Merge/output error: {e}")
        import traceback
        traceback.print_exc()
        return False

    logger.info("")
    logger.info("=" * 80)
    logger.info(f"TEST PASSED ✓ - {city_config['name']}")
    logger.info("=" * 80)
    logger.info("")

    return True


def main():
    print("=" * 80)
    print("METRO CITIES SVI PIPELINE TEST")
    print("=" * 80)
    print("")
    print("This test will:")
    print(f"  1. Test ALL {len(METRO_CITIES)} metro cities")
    print(f"  2. Fetch metadata from small 1km bbox (fast, ~100-1000 images)")
    print(f"  3. Download {TEST_IMAGES_PER_CITY} images per city (~{len(METRO_CITIES) * TEST_IMAGES_PER_CITY} total)")
    print("  4. Run sunny/shade analysis on each city")
    print("  5. Test cleanup and CSV output format")
    print("  6. Verify all components work before full run")
    print("")
    print("Metro cities to test:")
    print("  Recoverable surveys (7 cities):")
    for city in METRO_CITIES[:7]:
        print(f"    - {city['name']}, {city['state']}")
    print("  Existing metro surveys (12 cities):")
    for city in METRO_CITIES[7:]:
        print(f"    - {city['name']}, {city['state']}")
    print("")
    print(f"Expected duration: 5-10 minutes")
    print("=" * 80)
    print("")

    # Setup
    output_dir = Path("data/metro_pipeline_test")
    output_dir.mkdir(parents=True, exist_ok=True)

    logger = setup_logging(output_dir)
    mly.set_access_token(MAPILLARY_TOKEN)

    # Initialize pipeline
    logger.info("Initializing models...")

    # Try package structure first (models/), then development structure (outputs/models/)
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

    vit_model = None
    for candidate in vit_candidates:
        if candidate.exists():
            vit_model = str(candidate)
            break

    yolo_model = None
    for candidate in yolo_candidates:
        if candidate.exists():
            yolo_model = str(candidate)
            break

    if not vit_model:
        logger.error(f"ViT model not found. Tried: {[str(c) for c in vit_candidates]}")
        logger.error("Please ensure models are available")
        return 1

    if not yolo_model:
        logger.error(f"YOLO model not found. Tried: {[str(c) for c in yolo_candidates]}")
        logger.error("Please ensure models are available")
        return 1

    logger.info(f"Using ViT model: {vit_model}")
    logger.info(f"Using YOLO model: {yolo_model}")

    try:
        pipeline = SunnyShadePipeline(
            vit_model_path=vit_model,
            yolo_model_path=yolo_model
        )
        logger.info("✓ Models loaded")
        logger.info("")
    except Exception as e:
        logger.error(f"Failed to load models: {e}")
        return 1

    # Test all cities with progress bar
    all_success = True
    successes = []
    failures = []

    print("")
    print("=" * 80)
    print("Testing all metro cities...")
    print("=" * 80)
    print("")

    # Use tqdm progress bar
    with tqdm(total=len(METRO_CITIES), desc="Testing cities", unit="city",
              bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]') as pbar:
        for city_config in METRO_CITIES:
            pbar.set_description(f"Testing {city_config['name']:<20s}")
            try:
                success = test_city_limited(
                    city_config,
                    output_dir,
                    pipeline,
                    logger,
                    max_images=TEST_IMAGES_PER_CITY
                )
                if success:
                    successes.append(city_config['name'])
                    pbar.set_postfix_str("✓")
                else:
                    failures.append(city_config['name'])
                    all_success = False
                    pbar.set_postfix_str("✗ FAILED")
            except Exception as e:
                logger.error(f"Exception testing {city_config['name']}: {e}")
                import traceback
                traceback.print_exc()
                failures.append(city_config['name'])
                all_success = False
                pbar.set_postfix_str("✗ ERROR")

            pbar.update(1)

    # Print summary
    print("")
    print("=" * 80)
    if all_success:
        print("✓ ALL TESTS PASSED")
    else:
        print("⚠ SOME TESTS FAILED")
    print("=" * 80)
    print("")
    print(f"Success: {len(successes)}/{len(METRO_CITIES)} cities")
    if successes:
        print("  ✓ " + ", ".join(successes))
    if failures:
        print(f"  ✗ " + ", ".join(failures))
    print("")

    if all_success:
        print("The pipeline is ready for full run!")
        print("")
        print("To run full pipeline:")
        print("  python scripts/pipelines/metro_cities_svi_pipeline.py")
        print("")
        print("To run in background with nohup:")
        print("  nohup python scripts/pipelines/metro_cities_svi_pipeline.py > logs/metro_pipeline.log 2>&1 &")
        print("")
        return 0
    else:
        print("Check the logs in data/metro_pipeline_test/ for details")
        print("")
        return 1


if __name__ == "__main__":
    sys.exit(main())
