#!/usr/bin/env python3
# ABOUTME: Download sample images from Mapillary and create annotated visualizations
# ABOUTME: Re-analyzes images with ViT and YOLO models to show predictions

import torch
import torch.nn as nn
from torchvision import models, transforms
from ultralytics import YOLO
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import pandas as pd
import numpy as np
import mapillary.interface as mly
import urllib.request
import time
import random
import warnings
warnings.filterwarnings('ignore')

# Set random seeds
random.seed(42)
np.random.seed(42)
torch.manual_seed(42)

# Configuration
VIT_MODEL_PATH = "outputs/models/vit_binary.pth"
YOLO_MODEL_PATH = "outputs/models/sunny_batch_train6/weights/best.pt"
OUTPUT_DIR = Path("outputs/model_evaluation/sample_images")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Mapillary API token
MAPILLARY_TOKEN = 'MLY|9798203303595429|e2d4e749e96af419787ec1ca33019e3f'
mly.set_access_token(MAPILLARY_TOKEN)

# Number of samples per category per city
SAMPLES_PER_CATEGORY = 3

# Cities to sample from
CITIES = [
    "Buenos-Aires",
    "Cape-Town",
    "Istanbul",
    "Madrid",
    "Mumbai",
    "Osaka",
    "Singapore"
]

print("=" * 80)
print("GENERATING ANNOTATED SAMPLE IMAGES FROM MAPILLARY")
print("=" * 80)
print()

# ============================================================================
# 1. LOAD MODELS
# ============================================================================

print("Loading models...")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"  Device: {device}")

# Load ViT model
print("  Loading ViT binary classification model...")
vit_model = models.vit_b_16(pretrained=False)
vit_model.heads = nn.Sequential(
    nn.Linear(vit_model.heads.head.in_features, 1)
)
vit_model.load_state_dict(torch.load(VIT_MODEL_PATH, map_location=device))
vit_model.to(device)
vit_model.eval()
print("    ✓ ViT model loaded")

vit_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=(0.5, 0.5, 0.5), std=(0.5, 0.5, 0.5))
])

# Load YOLO model
print("  Loading YOLO shade detection model...")
yolo_model = YOLO(YOLO_MODEL_PATH)
yolo_class_names = {0: 'person', 1: 'inshade', 2: 'outshade'}
print("    ✓ YOLO model loaded")
print()

# ============================================================================
# 2. DOWNLOAD FUNCTIONS
# ============================================================================

def get_image_url(image_id):
    """Get Mapillary image URL for given image ID."""
    try:
        random_wait = random.uniform(0.1, 0.5)
        time.sleep(random_wait)
        image_url = mly.image_thumbnail(image_id, 2048)
        return image_url
    except Exception as e:
        print(f"    Error getting URL for {image_id}: {e}")
        return None

def download_image(image_id, output_path):
    """Download Mapillary image by ID to destination path."""
    image_url = get_image_url(image_id)
    if not image_url:
        return False

    try:
        with urllib.request.urlopen(image_url, timeout=30) as web_file:
            data = web_file.read()
            with open(output_path, mode='wb') as local_file:
                local_file.write(data)
        return True
    except Exception as e:
        print(f"    Error downloading {image_id}: {e}")
        return False

# ============================================================================
# 3. ANALYSIS FUNCTIONS
# ============================================================================

def classify_sunny(image_path):
    """Classify image as sunny/not sunny with ViT."""
    try:
        img = Image.open(image_path).convert("RGB")
        x = vit_transform(img).unsqueeze(0).to(device)

        with torch.no_grad():
            output = vit_model(x).squeeze(1)
            prob = torch.sigmoid(output).item()
            is_sunny = prob > 0.5

        return is_sunny, prob
    except Exception as e:
        print(f"    Error classifying {image_path}: {e}")
        return None, None

def detect_shade(image_path):
    """Detect people and shade with YOLO."""
    counts = {'person': 0, 'inshade': 0, 'outshade': 0}
    boxes_data = []

    try:
        results = yolo_model(image_path, verbose=False)

        for result in results:
            if result.boxes is not None:
                for box in result.boxes:
                    class_id = int(box.cls.item())
                    class_name = yolo_class_names.get(class_id, 'unknown')
                    if class_name in counts:
                        counts[class_name] += 1

                        # Store box coordinates for visualization
                        xyxy = box.xyxy[0].cpu().numpy()
                        conf = box.conf.item()
                        boxes_data.append({
                            'class': class_name,
                            'bbox': xyxy,
                            'conf': conf
                        })
    except Exception as e:
        print(f"    Error detecting shade in {image_path}: {e}")

    return counts, boxes_data

def annotate_image(image_path, is_sunny, sunny_prob, shade_counts, boxes_data,
                    utci_c, datetime_local, city_name, csv_is_sunny):
    """Create annotated version of image with predictions and metadata."""
    try:
        # Load image
        img = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(img)

        # Try to load fonts
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
            label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
            small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        except:
            title_font = ImageFont.load_default()
            label_font = ImageFont.load_default()
            small_font = ImageFont.load_default()

        # Draw bounding boxes for YOLO detections
        colors = {
            'person': (255, 255, 0),  # Yellow
            'inshade': (0, 255, 0),   # Green
            'outshade': (255, 0, 0)   # Red
        }

        for box_info in boxes_data:
            bbox = box_info['bbox']
            class_name = box_info['class']
            conf = box_info['conf']
            color = colors.get(class_name, (255, 255, 255))

            # Draw rectangle
            draw.rectangle(
                [(bbox[0], bbox[1]), (bbox[2], bbox[3])],
                outline=color,
                width=4
            )

            # Draw label with background
            label = f"{class_name} {conf:.2f}"
            # Get text bbox for background
            try:
                text_bbox = draw.textbbox((bbox[0], bbox[1] - 25), label, font=small_font)
                draw.rectangle(text_bbox, fill=color)
                draw.text((bbox[0], bbox[1] - 25), label, fill=(0, 0, 0), font=small_font)
            except:
                draw.text((bbox[0], bbox[1] - 20), label, fill=color, font=small_font)

        # Calculate shade preference
        n_total = shade_counts['inshade'] + shade_counts['outshade']
        if n_total > 0:
            shade_pref = shade_counts['inshade'] / n_total
        else:
            shade_pref = 0

        # Add title bar with metadata
        width, height = img.size
        title_height = 140
        title_img = Image.new('RGB', (width, title_height), color=(0, 0, 0))
        title_draw = ImageDraw.Draw(title_img)

        # Parse datetime
        try:
            dt = pd.to_datetime(datetime_local)
            date_str = dt.strftime('%Y-%m-%d')
            time_str = dt.strftime('%H:%M')
            dow_str = dt.strftime('%A')
        except:
            date_str = "N/A"
            time_str = "N/A"
            dow_str = ""

        # Agreement indicator
        agreement = "✓" if is_sunny == csv_is_sunny else "✗"
        agreement_color = (0, 255, 0) if is_sunny == csv_is_sunny else (255, 0, 0)

        # Title text
        title_lines = [
            f"{city_name} | {dow_str} {date_str} @ {time_str}",
            f"Model: Sunny={'Yes' if is_sunny else 'No'} ({sunny_prob:.3f}) | CSV: {'Yes' if csv_is_sunny else 'No'} [{agreement}]",
            f"UTCI: {utci_c:.1f}°C | People: {shade_counts['person']} (In Shade: {shade_counts['inshade']}, Out: {shade_counts['outshade']})" if not pd.isna(utci_c) else f"People: {shade_counts['person']} (In Shade: {shade_counts['inshade']}, Out: {shade_counts['outshade']})",
            f"Shade Preference: {shade_pref:.2f} ({shade_counts['inshade']}/{n_total})" if n_total > 0 else "Shade Preference: N/A (no people detected)"
        ]

        y_offset = 10
        for i, line in enumerate(title_lines):
            # Highlight agreement line
            if i == 1:
                title_draw.text((10, y_offset), line, fill=agreement_color, font=label_font)
            else:
                title_draw.text((10, y_offset), line, fill=(255, 255, 255), font=label_font)
            y_offset += 32

        # Combine title and image
        final_img = Image.new('RGB', (width, height + title_height))
        final_img.paste(title_img, (0, 0))
        final_img.paste(img, (0, title_height))

        return final_img

    except Exception as e:
        print(f"    Error annotating {image_path}: {e}")
        import traceback
        traceback.print_exc()
        return None

# ============================================================================
# 4. SAMPLE SELECTION AND PROCESSING
# ============================================================================

print("Loading city data and selecting samples...")
print()

all_samples_generated = 0

for city_name in CITIES:
    print(f"\n{'='*70}")
    print(f"Processing {city_name}")
    print(f"{'='*70}")

    # Load city CSV
    csv_path = Path(f"data/multi_city_results/{city_name}/{city_name}_analyzed_with_utci.csv")
    if not csv_path.exists():
        print(f"  CSV not found: {csv_path}")
        continue

    df_city = pd.read_csv(csv_path, low_memory=False)
    print(f"  Loaded {len(df_city):,} observations")

    # Define sampling categories
    categories = [
        ("sunny_with_people", df_city[
            (df_city['is_sunny'] == True) &
            ((df_city['inshade_count'] > 0) | (df_city['outshade_count'] > 0))
        ]),
        ("sunny_no_people", df_city[
            (df_city['is_sunny'] == True) &
            (df_city['person_count'] == 0)
        ]),
        ("not_sunny", df_city[df_city['is_sunny'] == False])
    ]

    city_samples = 0

    for category_name, df_cat in categories:
        if len(df_cat) == 0:
            print(f"  {category_name}: No samples available")
            continue

        # Sample up to SAMPLES_PER_CATEGORY
        n_samples = min(SAMPLES_PER_CATEGORY, len(df_cat))
        print(f"  {category_name}: Sampling {n_samples} images...")

        # Sample with preference for higher UTCI (sunny) or variety (not sunny)
        if category_name.startswith("sunny"):
            # For sunny images, sample from higher UTCI values
            df_sorted = df_cat.dropna(subset=['utci_C']).sort_values('utci_C', ascending=False)
            if len(df_sorted) < n_samples:
                df_sorted = df_cat  # Fall back to all if not enough with UTCI
            sampled = df_sorted.head(n_samples * 3).sample(n=n_samples, random_state=42)
        else:
            # For not sunny, random sample
            sampled = df_cat.sample(n=min(n_samples, len(df_cat)), random_state=42)

        for idx, (_, row) in enumerate(sampled.iterrows(), 1):
            image_id = str(row['id'])
            csv_is_sunny = bool(row.get('is_sunny', False))

            print(f"    [{idx}/{n_samples}] Downloading {image_id}...", end=' ')

            # Download image
            temp_image_path = OUTPUT_DIR / f"temp_{image_id}.jpeg"
            success = download_image(image_id, temp_image_path)

            if not success or not temp_image_path.exists():
                print("FAILED (download)")
                continue

            print("✓ Downloaded,", end=' ')

            # Analyze with models
            is_sunny, sunny_prob = classify_sunny(temp_image_path)
            if is_sunny is None:
                print("FAILED (classification)")
                temp_image_path.unlink()
                continue

            print(f"Analyzed (sunny={is_sunny:.0f}),", end=' ')

            shade_counts, boxes_data = detect_shade(temp_image_path)
            print(f"Detected ({shade_counts['person']} people),", end=' ')

            # Get metadata
            utci_c = row.get('utci_C', np.nan)
            datetime_local = row.get('datetime-local', 'N/A')

            # Create annotated image
            annotated = annotate_image(
                temp_image_path, is_sunny, sunny_prob, shade_counts, boxes_data,
                utci_c, datetime_local, city_name, csv_is_sunny
            )

            if annotated is not None:
                output_path = OUTPUT_DIR / f"{city_name}_{category_name}_{idx}.png"
                annotated.save(output_path, quality=95)
                print(f"✓ Saved")
                city_samples += 1
                all_samples_generated += 1
            else:
                print("FAILED (annotation)")

            # Clean up temp file
            if temp_image_path.exists():
                temp_image_path.unlink()

            # Small delay to avoid rate limiting
            time.sleep(0.3)

    print(f"\n  {city_name} complete: {city_samples} samples generated")

print()
print("=" * 80)
print("✓ SAMPLE GENERATION COMPLETE")
print("=" * 80)
print(f"\nTotal samples generated: {all_samples_generated}")
print(f"Output directory: {OUTPUT_DIR}")
print()
print("Sample categories per city:")
print("  - sunny_with_people: Sunny images with detected people")
print("  - sunny_no_people: Sunny images without people")
print("  - not_sunny: Not sunny images")
print()
