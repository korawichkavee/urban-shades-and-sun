# ABOUTME: Downloads actual street view images from CSV metadata
# ABOUTME: Supports both Mapillary and KartaView sources

"""
Downloads street view images based on filtered CSV metadata.
Handles both Mapillary and KartaView sources.

Usage:
    python download_images_from_csv.py --input filtered.csv --output ./images/
"""

import pandas as pd
import os
import urllib.request
import threading
import mapillary.interface as mly
import time
import random
from pathlib import Path
import argparse
from tqdm import tqdm


def download_image_from_url(image_url, dst_path):
    """Download image from URL to destination path."""
    try:
        with urllib.request.urlopen(image_url, timeout=30) as web_file:
            data = web_file.read()
            with open(dst_path, mode='wb') as local_file:
                local_file.write(data)
        return True
    except Exception as e:
        print(f'Error downloading {dst_path}: {e}')
        return False


def get_mapillary_image_url(image_id):
    """Get Mapillary image URL for given image ID."""
    try:
        time.sleep(random.randint(1, 10)/10)  # Rate limiting
        image_url = mly.image_thumbnail(image_id, 2048)
        return image_url
    except Exception as e:
        print(f'Error getting Mapillary URL for {image_id}: {e}')
        return None


def download_mapillary_image(image_id, dst_path):
    """Download a Mapillary image."""
    url = get_mapillary_image_url(image_id)
    if url:
        return download_image_from_url(url, dst_path)
    return False


def download_kartaview_image(image_id, sequence_id, dst_path):
    """Download a KartaView image."""
    # KartaView image URL pattern
    url = f"https://api.openstreetcam.org/2.0/photo/{image_id}"
    return download_image_from_url(url, dst_path)


def check_existing_images(image_folder):
    """Check which images already exist."""
    ids = set()
    if os.path.exists(image_folder):
        for name in os.listdir(image_folder):
            if name.endswith(('.jpg', '.jpeg', '.png')):
                ids.add(name.split('.')[0])
    return ids


def main():
    parser = argparse.ArgumentParser(
        description='Download street view images from filtered CSV metadata'
    )
    parser.add_argument('--input', required=True, help='Input CSV file with filtered metadata')
    parser.add_argument('--output', required=True, help='Output directory for images')
    parser.add_argument('--mapillary-token', help='Mapillary API token (or set via environment)')
    parser.add_argument('--threads', type=int, default=10, help='Number of download threads (default: 10)')
    parser.add_argument('--max-images', type=int, help='Maximum number of images to download (for testing)')

    args = parser.parse_args()

    # Setup Mapillary token
    mapillary_token = args.mapillary_token or os.environ.get('MAPILLARY_TOKEN')
    if mapillary_token:
        mly.set_access_token(mapillary_token)
    else:
        print("Warning: No Mapillary token provided. Mapillary downloads will fail.")
        print("Set via --mapillary-token or MAPILLARY_TOKEN environment variable")

    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load CSV
    print(f"Loading CSV from {args.input}...")
    df = pd.read_csv(args.input)
    print(f"Found {len(df)} images in CSV")

    # Limit if requested
    if args.max_images:
        df = df.head(args.max_images)
        print(f"Limited to {len(df)} images for testing")

    # Check existing images
    existing_ids = check_existing_images(output_dir)
    print(f"Found {len(existing_ids)} existing images, will skip these")

    # Filter to images that need downloading
    df_to_download = df[~df['id'].astype(str).isin(existing_ids)]
    print(f"Will download {len(df_to_download)} new images")

    if df_to_download.empty:
        print("No images to download!")
        return

    # Download images by source
    mapillary_images = df_to_download[df_to_download['source'] == 'Mapillary']
    kartaview_images = df_to_download[df_to_download['source'] == 'KartaView']

    total_downloaded = 0
    total_failed = 0

    # Download Mapillary images
    if not mapillary_images.empty and mapillary_token:
        print(f"\nDownloading {len(mapillary_images)} Mapillary images...")

        for idx, row in tqdm(mapillary_images.iterrows(), total=len(mapillary_images)):
            image_id = str(row['id'])
            dst_path = output_dir / f"{image_id}.jpg"

            if download_mapillary_image(image_id, dst_path):
                total_downloaded += 1
            else:
                total_failed += 1

    # Download KartaView images
    if not kartaview_images.empty:
        print(f"\nDownloading {len(kartaview_images)} KartaView images...")

        for idx, row in tqdm(kartaview_images.iterrows(), total=len(kartaview_images)):
            image_id = str(row['id'])
            sequence_id = str(row.get('sequenceId', ''))
            dst_path = output_dir / f"{image_id}.jpg"

            if download_kartaview_image(image_id, sequence_id, dst_path):
                total_downloaded += 1
            else:
                total_failed += 1

    print(f"\n{'='*60}")
    print(f"Download Complete!")
    print(f"{'='*60}")
    print(f"Successfully downloaded: {total_downloaded}")
    print(f"Failed: {total_failed}")
    print(f"Output directory: {output_dir}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
