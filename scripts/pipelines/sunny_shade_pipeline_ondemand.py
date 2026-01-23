#!/usr/bin/env python3
# ABOUTME: Pipeline to process walkable CSVs with on-demand image download
# ABOUTME: Downloads images from Mapillary, classifies sunny/shade, deletes images, saves annotated CSV

import torch
import torch.nn as nn
from torchvision import models, transforms
from ultralytics import YOLO
from PIL import Image
from pathlib import Path
import pandas as pd
import argparse
from tqdm import tqdm
import os
import tempfile
import mapillary.interface as mly
import urllib.request
import time
import random


def download_image_from_url(image_url, dst_path):
    """Download image from URL to destination path."""
    try:
        with urllib.request.urlopen(image_url) as web_file:
            data = web_file.read()
            with open(dst_path, mode='wb') as local_file:
                local_file.write(data)
        return True
    except Exception as e:
        print(f'Error downloading from URL: {e}')
        return False


def get_image_url(image_id):
    """Get Mapillary image URL for given image ID."""
    try:
        random_t = random.randint(1, 10) / 10
        time.sleep(random_t)
        image_url = mly.image_thumbnail(image_id, 2048)
        return image_url
    except Exception as e:
        print(f'Error getting image URL: {e}')
        return None


def download_mapillary_image(image_id, dst_path):
    """Download Mapillary image by ID to destination path."""
    image_url = get_image_url(image_id)
    if image_url:
        return download_image_from_url(image_url, dst_path)
    return False


class SunnyShadePipeline:
    """Pipeline for classifying images and detecting people in shade."""

    def __init__(self, vit_model_path="models/vit_binary.pth", yolo_model_path="models/yolo_best.pt", mapillary_token=None):
        """
        Initialize the pipeline with both models.

        Args:
            vit_model_path: Path to trained ViT binary classification model
            yolo_model_path: Path to trained YOLO model for shade detection
            mapillary_token: Mapillary API access token
        """
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Using device: {self.device}")

        # Set Mapillary token
        if mapillary_token:
            mly.set_access_token(mapillary_token)
        else:
            # Default token
            mly.set_access_token('MLY|9798203303595429|e2d4e749e96af419787ec1ca33019e3f')

        # Load ViT model for sunny/not-sunny classification
        print("Loading ViT model for sunny classification...")
        self.vit_model = models.vit_b_16(pretrained=False)
        self.vit_model.heads = nn.Sequential(
            nn.Linear(self.vit_model.heads.head.in_features, 1)
        )
        self.vit_model.load_state_dict(torch.load(vit_model_path, map_location=self.device))
        self.vit_model.to(self.device)
        self.vit_model.eval()

        # ViT preprocessing transforms
        self.vit_transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=(0.5, 0.5, 0.5), std=(0.5, 0.5, 0.5))
        ])

        # Load YOLO model for shade detection
        print("Loading YOLO model for shade detection...")
        self.yolo_model = YOLO(yolo_model_path)

        # YOLO class names: ['person', 'inshade', 'outshade']
        self.class_names = {0: 'person', 1: 'inshade', 2: 'outshade'}

    def classify_sunny(self, image_path):
        """
        Classify whether an image is sunny or not.

        Args:
            image_path: Path to image file

        Returns:
            tuple: (is_sunny (bool), probability (float))
        """
        try:
            img = Image.open(image_path).convert("RGB")
            x = self.vit_transform(img).unsqueeze(0).to(self.device)

            with torch.no_grad():
                output = self.vit_model(x).squeeze(1)
                prob = torch.sigmoid(output).item()
                is_sunny = prob > 0.5

            return is_sunny, prob
        except Exception as e:
            print(f"Error classifying {image_path}: {e}")
            return False, 0.0

    def detect_shade(self, image_path):
        """
        Detect people and classify them as in shade or out of shade.

        Args:
            image_path: Path to image file

        Returns:
            dict: Counts of each class {'person': int, 'inshade': int, 'outshade': int}
        """
        counts = {'person': 0, 'inshade': 0, 'outshade': 0}

        try:
            # Run YOLO inference
            results = self.yolo_model(image_path, verbose=False)

            # Count detections by class
            for result in results:
                if result.boxes is not None:
                    for box in result.boxes:
                        class_id = int(box.cls.item())
                        class_name = self.class_names.get(class_id, 'unknown')
                        if class_name in counts:
                            counts[class_name] += 1

        except Exception as e:
            print(f"Error detecting shade in {image_path}: {e}")

        return counts

    def process_csv_ondemand(self, csv_path, output_csv=None, batch_size=100):
        """
        Process walkable CSV with on-demand image download.

        Args:
            csv_path: Path to walkable CSV file
            output_csv: Path to output annotated CSV (default: input_annotated.csv)
            batch_size: Save results after processing this many images

        Returns:
            DataFrame with annotated results
        """
        csv_path = Path(csv_path)

        if not csv_path.exists():
            raise ValueError(f"CSV file does not exist: {csv_path}")

        # Load CSV
        print(f"Loading CSV: {csv_path}")
        df = pd.read_csv(csv_path)
        print(f"Found {len(df)} images to process")

        # Check required column
        if 'id' not in df.columns:
            raise ValueError("CSV must have 'id' column with Mapillary image IDs")

        # Add result columns if they don't exist
        if 'is_sunny' not in df.columns:
            df['is_sunny'] = None
        if 'sunny_probability' not in df.columns:
            df['sunny_probability'] = None
        if 'person_count' not in df.columns:
            df['person_count'] = None
        if 'inshade_count' not in df.columns:
            df['inshade_count'] = None
        if 'outshade_count' not in df.columns:
            df['outshade_count'] = None

        # Output CSV path
        if output_csv is None:
            output_csv = csv_path.parent / f"{csv_path.stem}_annotated.csv"

        # Create temp directory for images
        temp_dir = Path(tempfile.mkdtemp(prefix='sunny_shade_'))
        print(f"Temporary image directory: {temp_dir}")

        processed_count = 0
        error_count = 0

        try:
            # Process each row
            for idx, row in tqdm(df.iterrows(), total=len(df), desc="Processing images"):
                # Skip if already processed (in case of resume)
                if pd.notna(row.get('is_sunny')):
                    processed_count += 1
                    continue

                image_id = str(row['id'])
                temp_image_path = temp_dir / f"{image_id}.jpeg"

                try:
                    # Download image
                    download_success = download_mapillary_image(image_id, temp_image_path)

                    if not download_success or not temp_image_path.exists():
                        print(f"\nFailed to download image {image_id}")
                        error_count += 1
                        continue

                    # Classify as sunny/not sunny
                    is_sunny, sunny_prob = self.classify_sunny(temp_image_path)

                    # If sunny, detect people and shade
                    if is_sunny:
                        shade_counts = self.detect_shade(temp_image_path)
                    else:
                        shade_counts = {'person': 0, 'inshade': 0, 'outshade': 0}

                    # Store results in DataFrame
                    df.at[idx, 'is_sunny'] = is_sunny
                    df.at[idx, 'sunny_probability'] = sunny_prob
                    df.at[idx, 'person_count'] = shade_counts['person']
                    df.at[idx, 'inshade_count'] = shade_counts['inshade']
                    df.at[idx, 'outshade_count'] = shade_counts['outshade']

                    processed_count += 1

                    # Delete image to save space
                    if temp_image_path.exists():
                        temp_image_path.unlink()

                except Exception as e:
                    print(f"\nError processing image {image_id}: {e}")
                    error_count += 1

                    # Clean up temp image if it exists
                    if temp_image_path.exists():
                        temp_image_path.unlink()

                # Save progress periodically
                if processed_count % batch_size == 0 and processed_count > 0:
                    df.to_csv(output_csv, index=False)
                    print(f"\nProgress saved: {processed_count}/{len(df)} images processed")

            # Final save
            df.to_csv(output_csv, index=False)
            print(f"\nResults saved to: {output_csv}")

            # Print summary statistics
            sunny_count = df['is_sunny'].sum()
            print(f"\nSummary:")
            print(f"  Total images: {len(df)}")
            print(f"  Successfully processed: {processed_count}")
            print(f"  Errors: {error_count}")
            print(f"  Sunny images: {sunny_count} ({sunny_count/len(df)*100:.1f}%)")
            print(f"  Images with people in shade: {(df['inshade_count'] > 0).sum()}")
            print(f"  Images with people out of shade: {(df['outshade_count'] > 0).sum()}")

        finally:
            # Clean up temp directory
            if temp_dir.exists():
                import shutil
                shutil.rmtree(temp_dir)
                print(f"\nCleaned up temporary directory")

        return df


def main():
    parser = argparse.ArgumentParser(
        description="Process walkable CSV with on-demand image download and sunny/shade classification"
    )
    parser.add_argument(
        "csv_file",
        type=str,
        help="Path to walkable CSV file with image IDs"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output annotated CSV file path (default: <input>_annotated.csv)"
    )
    parser.add_argument(
        "--vit-model",
        type=str,
        default="models/vit_binary.pth",
        help="Path to ViT model weights (default: models/vit_binary.pth)"
    )
    parser.add_argument(
        "--yolo-model",
        type=str,
        default="models/yolo_best.pt",
        help="Path to YOLO model weights (default: models/yolo_best.pt)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Save progress after processing this many images (default: 100)"
    )
    parser.add_argument(
        "--mapillary-token",
        type=str,
        default=None,
        help="Mapillary API access token (optional)"
    )

    args = parser.parse_args()

    # Initialize pipeline
    pipeline = SunnyShadePipeline(
        vit_model_path=args.vit_model,
        yolo_model_path=args.yolo_model,
        mapillary_token=args.mapillary_token
    )

    # Process CSV
    pipeline.process_csv_ondemand(
        args.csv_file,
        args.output,
        batch_size=args.batch_size
    )


if __name__ == "__main__":
    main()
