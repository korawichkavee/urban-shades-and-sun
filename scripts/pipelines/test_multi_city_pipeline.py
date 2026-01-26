#!/usr/bin/env python3
# ABOUTME: Small-scale test of multi-city pipeline with limited images
# ABOUTME: Validates download, analysis, and cleanup before overnight run

import sys
from pathlib import Path
import pandas as pd
import logging
from multi_city_overnight_pipeline import (
    setup_logging,
    process_city_batch,
    MAPILLARY_TOKEN,
    CITY_CONFIG
)
import mapillary.interface as mly
from sunny_shade_pipeline import SunnyShadePipeline


# Test configuration - test all cities with limited images per city
TEST_CITIES = [
    {"name": "Madrid", "country": "ESP", "id": 1724616994},
    {"name": "Cape Town", "country": "ZAF", "id": 1710680650},
    {"name": "Istanbul", "country": "TUR", "id": 1792756324},
    {"name": "Osaka", "country": "JPN", "id": 1392419823},
    {"name": "Singapore", "country": "SGP", "id": 1702341327},
    {"name": "Buenos Aires", "country": "ARG", "id": 1032717330},
    {"name": "Mumbai", "country": "IND", "id": 1356226629},
]
TEST_IMAGES_PER_CITY = 5  # Test with 5 images per city


def test_city_limited(city_config, worldcities_csv, output_dir, pipeline, logger, max_images=20):
    """Test processing with limited number of images."""
    from multi_city_overnight_pipeline import fetch_city_metadata
    import asyncio
    import shutil
    from multi_city_overnight_pipeline import download_images_batch_async

    city_name = city_config['name'].replace(' ', '-')
    city_dir = output_dir / city_name
    city_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 80)
    logger.info(f"TEST: {city_config['name']} (limited to {max_images} images)")
    logger.info("=" * 80)

    # Fetch metadata
    csv_path = fetch_city_metadata(city_config, worldcities_csv, city_dir, logger)
    if not csv_path or not csv_path.exists():
        logger.error("FAILED: Could not fetch metadata")
        return False

    # Load and limit metadata
    df = pd.read_csv(csv_path)
    logger.info(f"Full dataset has {len(df)} images")

    df_limited = df.head(max_images)
    logger.info(f"Testing with {len(df_limited)} images")

    # Create temp images directory
    images_dir = city_dir / "images_test"
    images_dir.mkdir(parents=True, exist_ok=True)

    # Test download
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

    # Test analysis
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

    # Test cleanup
    logger.info("Testing cleanup...")
    try:
        shutil.rmtree(images_dir)
        logger.info("✓ Cleanup successful")
    except Exception as e:
        logger.warning(f"Cleanup warning: {e}")

    # Test merging
    logger.info("Testing metadata merge...")
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

    output_csv = city_dir / f"{city_name}_test_analyzed.csv"
    merged.to_csv(output_csv, index=False)
    logger.info(f"✓ Merged CSV saved: {output_csv}")

    logger.info("")
    logger.info("=" * 80)
    logger.info("TEST PASSED ✓")
    logger.info("=" * 80)
    logger.info("")

    return True


def main():
    print("=" * 80)
    print("MULTI-CITY PIPELINE TEST")
    print("=" * 80)
    print("")
    print("This test will:")
    print(f"  1. Test all {len(TEST_CITIES)} cities")
    print(f"  2. Download {TEST_IMAGES_PER_CITY} images per city ({len(TEST_CITIES) * TEST_IMAGES_PER_CITY} total)")
    print("  3. Run sunny/shade analysis")
    print("  4. Test cleanup and merging")
    print("  5. Verify all components work")
    print("")
    print("Cities to test:")
    for city in TEST_CITIES:
        print(f"  - {city['name']}, {city['country']}")
    print("")
    print(f"Expected duration: 3-7 minutes")
    print("=" * 80)
    print("")

    # Setup
    output_dir = Path("data/pipeline_test")
    output_dir.mkdir(parents=True, exist_ok=True)

    logger = setup_logging(output_dir)
    mly.set_access_token(MAPILLARY_TOKEN)

    # Initialize pipeline
    logger.info("Initializing models...")

    # Try package structure first (models/), then development structure (outputs/models/)
    script_dir = Path(__file__).parent
    package_root = script_dir.parent.parent

    vit_candidates = [
        package_root / "models" / "vit_binary.pth",  # Package structure
        Path("models/vit_binary.pth"),  # Package relative
        Path("outputs/models/vit_binary.pth"),  # Development structure
    ]

    yolo_candidates = [
        package_root / "models" / "yolo_best.pt",  # Package structure
        Path("models/yolo_best.pt"),  # Package relative
        Path("outputs/models/sunny_batch_train4/weights/best.pt"),  # Development structure
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

    # Run test
    worldcities_candidates = [
        package_root / "data" / "worldcities.csv",  # Package structure
        Path("data/worldcities.csv"),  # Package relative
        Path("/home/kieran/Documents/Datasets/Global streetscapes/global-streetscapes/code/raw_download/data/worldcities.csv"),  # Development
    ]

    worldcities_csv = None
    for candidate in worldcities_candidates:
        if candidate.exists():
            worldcities_csv = str(candidate)
            break

    if not worldcities_csv:
        logger.error(f"Worldcities CSV not found. Tried: {[str(c) for c in worldcities_candidates]}")
        logger.error("Please provide worldcities.csv in data/ directory")
        return 1

    logger.info(f"Using worldcities CSV: {worldcities_csv}")

    # Test all cities
    all_success = True
    successes = []
    failures = []

    for city_config in TEST_CITIES:
        try:
            success = test_city_limited(
                city_config,
                worldcities_csv,
                output_dir,
                pipeline,
                logger,
                max_images=TEST_IMAGES_PER_CITY
            )
            if success:
                successes.append(city_config['name'])
            else:
                failures.append(city_config['name'])
                all_success = False
        except Exception as e:
            logger.error(f"Exception testing {city_config['name']}: {e}")
            failures.append(city_config['name'])
            all_success = False

    # Print summary
    print("")
    print("=" * 80)
    if all_success:
        print("✓ ALL TESTS PASSED")
    else:
        print("⚠ SOME TESTS FAILED")
    print("=" * 80)
    print("")
    print(f"Success: {len(successes)}/{len(TEST_CITIES)} cities")
    if successes:
        print("  ✓ " + ", ".join(successes))
    if failures:
        print(f"  ✗ " + ", ".join(failures))
    print("")

    if all_success:
        print("The pipeline is ready for overnight run!")
        print("")
        print("To run full pipeline:")
        print("  python scripts/pipelines/multi_city_overnight_pipeline.py")
        print("")
        print("To run in background with nohup:")
        print("  nohup python scripts/pipelines/multi_city_overnight_pipeline.py > pipeline.log 2>&1 &")
        print("")
        return 0
    else:
        print("Check the logs in data/pipeline_test/ for details")
        print("")
        return 1


if __name__ == "__main__":
    sys.exit(main())
