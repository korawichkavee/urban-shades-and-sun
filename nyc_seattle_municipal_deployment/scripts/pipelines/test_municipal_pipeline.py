#!/usr/bin/env python3
# ABOUTME: Pre-flight test script for municipal shadow analysis pipeline
# ABOUTME: Tests all components before multi-day production run

import sys
from pathlib import Path
import pandas as pd
import logging
import asyncio

sys.path.insert(0, str(Path(__file__).parent))
from municipal_shadow_pipeline import (
    setup_logging,
    download_batch_async,
    MAPILLARY_TOKEN,
    CITIES
)
from sunny_shade_pipeline import SunnyShadePipeline


TEST_IMAGES_PER_CITY = 5  # Test with small number


def test_metadata_loading(logger):
    """Test that all metadata files load correctly."""
    logger.info("="*60)
    logger.info("TEST 1: Metadata Loading")
    logger.info("="*60)

    for city_key, config in CITIES.items():
        metadata_path = Path(__file__).parent.parent.parent / config['metadata_file']
        logger.info(f"\nTesting {city_key}...")

        if not metadata_path.exists():
            logger.error(f"  ✗ Metadata not found: {metadata_path}")
            return False

        df = pd.read_csv(metadata_path)
        logger.info(f"  ✓ Loaded {len(df):,} images")

        # Check required columns
        required_cols = ['id', 'captured_at', 'lon', 'lat']
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            logger.error(f"  ✗ Missing columns: {missing}")
            return False

        logger.info(f"  ✓ All required columns present")

    logger.info("\n✓ Metadata loading test passed")
    return True


def test_model_loading(logger):
    """Test that ML models load correctly."""
    logger.info("\n" + "="*60)
    logger.info("TEST 2: Model Loading")
    logger.info("="*60)

    base_dir = Path(__file__).parent.parent.parent
    vit_path = base_dir / "models" / "vit_binary.pth"
    yolo_path = base_dir / "models" / "yolo_best.pt"

    if not vit_path.exists():
        logger.error(f"  ✗ ViT model not found: {vit_path}")
        return False

    if not yolo_path.exists():
        logger.error(f"  ✗ YOLO model not found: {yolo_path}")
        return False

    try:
        pipeline = SunnyShadePipeline(
            vit_model_path=str(vit_path),
            yolo_model_path=str(yolo_path)
        )
        logger.info("  ✓ ViT model loaded")
        logger.info("  ✓ YOLO model loaded")
        logger.info("\n✓ Model loading test passed")
        return True, pipeline
    except Exception as e:
        logger.error(f"  ✗ Model loading failed: {e}")
        return False, None


def test_download_functionality(logger):
    """Test that image download works."""
    logger.info("\n" + "="*60)
    logger.info("TEST 3: Download Functionality")
    logger.info("="*60)

    # Get sample image IDs from NYC
    base_dir = Path(__file__).parent.parent.parent
    metadata_path = base_dir / CITIES['new-york-city']['metadata_file']
    df = pd.read_csv(metadata_path, nrows=5)

    temp_dir = base_dir / "outputs" / "test_download"
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        logger.info(f"  Testing download of {len(df)} images...")
        successful, failed = asyncio.run(
            download_batch_async(df['id'].tolist(), temp_dir, MAPILLARY_TOKEN, max_concurrent=5)
        )

        logger.info(f"  Downloaded: {successful}, Failed: {failed}")

        if successful > 0:
            logger.info("  ✓ Download test passed")
            return True
        else:
            logger.error("  ✗ No images downloaded")
            return False

    except Exception as e:
        logger.error(f"  ✗ Download test failed: {e}")
        return False
    finally:
        # Cleanup
        import shutil
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


def test_cleanup_pattern(logger):
    """Test that cleanup pattern is implemented."""
    logger.info("\n" + "="*60)
    logger.info("TEST 4: Storage Cleanup Pattern")
    logger.info("="*60)

    # Check that pipeline script has cleanup code
    pipeline_script = Path(__file__).parent / "municipal_shadow_pipeline.py"
    content = pipeline_script.read_text()

    if "shutil.rmtree" in content:
        logger.info("  ✓ Cleanup code found (shutil.rmtree)")
    else:
        logger.error("  ✗ No cleanup code found!")
        return False

    if "DELETE_AFTER_PROCESSING" in content:
        logger.info("  ✓ DELETE_AFTER_PROCESSING flag found")
    else:
        logger.warning("  ⚠ No DELETE_AFTER_PROCESSING flag")

    if "finally:" in content:
        logger.info("  ✓ Finally block found (ensures cleanup)")
    else:
        logger.error("  ✗ No finally block found!")
        return False

    logger.info("\n✓ Cleanup pattern test passed")
    return True


def main():
    print("="*60)
    print("NYC & SEATTLE MUNICIPAL PIPELINE PRE-FLIGHT TESTS")
    print("="*60)
    print()

    # Setup logging
    base_dir = Path(__file__).parent.parent.parent
    logs_dir = base_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(__name__)
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('[%(asctime)s] %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    all_passed = True

    # Run tests
    if not test_metadata_loading(logger):
        all_passed = False

    result = test_model_loading(logger)
    if isinstance(result, tuple):
        passed, pipeline = result
        if not passed:
            all_passed = False
    else:
        if not result:
            all_passed = False

    if not test_download_functionality(logger):
        all_passed = False

    if not test_cleanup_pattern(logger):
        all_passed = False

    # Summary
    print()
    print("="*60)
    if all_passed:
        print("✓ ALL TESTS PASSED")
        print("="*60)
        print()
        print("Pipeline is ready for production run!")
        print()
        print("To start production:")
        print("  ./run_pipeline.sh")
        print()
        return 0
    else:
        print("✗ SOME TESTS FAILED")
        print("="*60)
        print()
        print("Please fix errors before running production pipeline.")
        print()
        return 1


if __name__ == '__main__':
    sys.exit(main())
