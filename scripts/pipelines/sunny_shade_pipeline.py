# ABOUTME: Pipeline to classify street view images as sunny/not-sunny, then detect people in/out of shade
# ABOUTME: Combines ViT binary classification with YOLO object detection for shade analysis

import torch
import torch.nn as nn
from torchvision import models, transforms
from ultralytics import YOLO
from PIL import Image
from pathlib import Path
import pandas as pd
import argparse
from tqdm import tqdm
import sys


class SunnyShadePipeline:
    """Pipeline for classifying images and detecting people in shade."""

    def __init__(self, vit_model_path="vit_binary.pth", yolo_model_path="sunny_batch_train4/weights/best.pt"):
        """
        Initialize the pipeline with both models.

        Args:
            vit_model_path: Path to trained ViT binary classification model
            yolo_model_path: Path to trained YOLO model for shade detection
        """
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Using device: {self.device}")

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
            print(f"Error processing {image_path}: {e}")
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

    def process_folder(self, image_folder, output_csv=None):
        """
        Process all images in a folder through the pipeline.

        Args:
            image_folder: Path to folder containing images
            output_csv: Path to output CSV file (default: image_folder_results.csv)

        Returns:
            DataFrame with results
        """
        image_folder = Path(image_folder)

        if not image_folder.exists():
            raise ValueError(f"Image folder does not exist: {image_folder}")

        # Get all image files
        image_extensions = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}
        image_files = [f for f in image_folder.iterdir()
                      if f.suffix in image_extensions]

        if not image_files:
            raise ValueError(f"No images found in {image_folder}")

        print(f"Found {len(image_files)} images to process")

        results = []

        # Process each image
        for image_path in tqdm(image_files, desc="Processing images"):
            # Extract image ID from filename (remove extension)
            image_id = image_path.stem

            # Step 1: Classify as sunny/not sunny
            is_sunny, sunny_prob = self.classify_sunny(image_path)

            # Step 2: If sunny, detect people and shade
            if is_sunny:
                shade_counts = self.detect_shade(image_path)
            else:
                shade_counts = {'person': 0, 'inshade': 0, 'outshade': 0}

            # Store results
            results.append({
                'image_id': image_id,
                'is_sunny': is_sunny,
                'sunny_probability': sunny_prob,
                'person_count': shade_counts['person'],
                'inshade_count': shade_counts['inshade'],
                'outshade_count': shade_counts['outshade']
            })

        # Create DataFrame
        df = pd.DataFrame(results)

        # Save to CSV
        if output_csv is None:
            output_csv = f"{image_folder.name}_results.csv"

        df.to_csv(output_csv, index=False)
        print(f"\nResults saved to: {output_csv}")

        # Print summary statistics
        sunny_count = df['is_sunny'].sum()
        print(f"\nSummary:")
        print(f"  Total images: {len(df)}")
        print(f"  Sunny images: {sunny_count} ({sunny_count/len(df)*100:.1f}%)")
        print(f"  Images with people in shade: {(df['inshade_count'] > 0).sum()}")
        print(f"  Images with people out of shade: {(df['outshade_count'] > 0).sum()}")

        return df


def main():
    parser = argparse.ArgumentParser(
        description="Process street view images to classify sunny/not-sunny and detect people in/out of shade"
    )
    parser.add_argument(
        "image_folder",
        type=str,
        help="Path to folder containing images to process"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output CSV file path (default: <folder_name>_results.csv)"
    )
    parser.add_argument(
        "--vit-model",
        type=str,
        default="vit_binary.pth",
        help="Path to ViT model weights (default: vit_binary.pth)"
    )
    parser.add_argument(
        "--yolo-model",
        type=str,
        default="sunny_batch_train4/weights/best.pt",
        help="Path to YOLO model weights (default: sunny_batch_train4/weights/best.pt)"
    )

    args = parser.parse_args()

    # Initialize pipeline
    pipeline = SunnyShadePipeline(
        vit_model_path=args.vit_model,
        yolo_model_path=args.yolo_model
    )

    # Process images
    pipeline.process_folder(args.image_folder, args.output)


if __name__ == "__main__":
    main()
