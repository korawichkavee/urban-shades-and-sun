#!/usr/bin/env python3
# ABOUTME: Test people detection on a small sample of multi-city images

import pandas as pd
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent / 'scripts' / 'pipelines'))

from sunny_shade_pipeline import SunnyShadePipeline
import asyncio
import aiohttp
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def download_test_images(image_ids, output_dir, token):
    """Download a few test images."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    async with aiohttp.ClientSession() as session:
        for img_id in image_ids:
            output_path = output_dir / f"{img_id}.jpg"
            if output_path.exists():
                continue

            # Get image URL
            metadata_url = f"https://graph.mapillary.com/{img_id}?fields=thumb_2048_url&access_token={token}"
            try:
                async with session.get(metadata_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        metadata = await response.json()
                        if 'thumb_2048_url' in metadata:
                            image_url = metadata['thumb_2048_url']

                            # Download image
                            async with session.get(image_url, timeout=aiohttp.ClientTimeout(total=30)) as img_response:
                                if img_response.status == 200:
                                    content = await img_response.read()
                                    output_path.write_bytes(content)
                                    logger.info(f"  Downloaded {img_id}")
            except Exception as e:
                logger.error(f"  Failed to download {img_id}: {e}")

def main():
    logger.info("="*80)
    logger.info("TESTING PEOPLE DETECTION ON MULTI-CITY IMAGES")
    logger.info("="*80)

    # Load Singapore data (has most images)
    singapore_csv = Path("data/multi_city_results/Singapore/Singapore_analyzed.csv")
    df = pd.read_csv(singapore_csv)

    logger.info(f"\nLoaded {len(df)} Singapore images")

    # Take 20 random sunny images
    df_sunny = df[df['is_sunny'].astype(str).str.lower() == 'true']
    logger.info(f"Found {len(df_sunny)} sunny images")

    test_sample = df_sunny.sample(min(20, len(df_sunny)), random_state=42)
    logger.info(f"Selected {len(test_sample)} images for testing\n")

    # Download test images
    test_dir = Path("data/people_detection_test")
    test_dir.mkdir(parents=True, exist_ok=True)

    image_ids = test_sample['id'].astype(str).tolist()
    token = 'MLY|9798203303595429|e2d4e749e96af419787ec1ca33019e3f'

    logger.info("Downloading test images...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(download_test_images(image_ids, test_dir / "images", token))
    loop.close()

    # Check how many downloaded
    downloaded_images = list((test_dir / "images").glob("*.jpg"))
    logger.info(f"Downloaded {len(downloaded_images)} images\n")

    if len(downloaded_images) == 0:
        logger.error("No images downloaded, cannot test")
        return

    # Initialize pipeline with models
    logger.info("Initializing SunnyShadePipeline...")
    vit_model = "outputs/models/vit_binary.pth"
    yolo_model = "outputs/models/sunny_batch_train4/weights/best.pt"

    if not Path(vit_model).exists():
        logger.error(f"ViT model not found: {vit_model}")
        return

    if not Path(yolo_model).exists():
        logger.error(f"YOLO model not found: {yolo_model}")
        return

    try:
        pipeline = SunnyShadePipeline(
            vit_model_path=vit_model,
            yolo_model_path=yolo_model
        )
        logger.info("✓ Models loaded\n")
    except Exception as e:
        logger.error(f"Failed to load models: {e}")
        return

    # Run analysis
    logger.info("Running analysis on test images...")
    try:
        results = pipeline.process_folder(test_dir / "images", output_csv=None)

        logger.info("\n" + "="*80)
        logger.info("RESULTS")
        logger.info("="*80)
        logger.info(f"Total images processed: {len(results)}")
        logger.info(f"Sunny images: {results['is_sunny'].sum()}")
        logger.info(f"Total people detected: {results['person_count'].sum()}")
        logger.info(f"Images with people: {(results['person_count'] > 0).sum()}")

        if results['person_count'].sum() > 0:
            logger.info(f"People in shade: {results['inshade_count'].sum()}")
            logger.info(f"People out of shade: {results['outshade_count'].sum()}")

            # Show images with most people
            top_people = results.nlargest(5, 'person_count')[['image_id', 'person_count', 'inshade_count', 'outshade_count']]
            logger.info("\nTop 5 images by people count:")
            logger.info(str(top_people))
        else:
            logger.warning("\n⚠️  NO PEOPLE DETECTED IN ANY IMAGES")
            logger.warning("This matches the overnight run results")

        # Save results
        output_csv = test_dir / "test_results.csv"
        results.to_csv(output_csv, index=False)
        logger.info(f"\nResults saved to: {output_csv}")

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
