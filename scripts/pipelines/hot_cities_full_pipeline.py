#!/usr/bin/env python3
# ABOUTME: Complete pipeline for hot cities - sunny/shade classification + weather data
# ABOUTME: Processes each city fully before moving to next, with comprehensive logging

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
from datetime import datetime, timedelta
import meteostat
from metpy.calc import wet_bulb_temperature
from metpy.units import units
from tenacity import retry, wait_exponential, stop_after_attempt
import json
import logging

meteostat.Hourly.max_age = 0  # disable caching

# Logging configuration
LOG_INTERVAL = 50  # Log detailed progress every N images
CHECKPOINT_INTERVAL = 100  # Save progress every N images


def setup_logging(log_file='pipeline.log'):
    """Set up comprehensive logging to file and console."""
    # Create logger
    logger = logging.getLogger('hot_cities_pipeline')
    logger.setLevel(logging.DEBUG)

    # Remove existing handlers
    logger.handlers = []

    # File handler - detailed logs
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    fh.setFormatter(file_formatter)

    # Console handler - important messages only
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(message)s')
    ch.setFormatter(console_formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger


def log_separator(logger, char='=', length=80):
    """Log a separator line."""
    logger.info(char * length)


def log_progress_report(logger, stats):
    """Log detailed progress report."""
    elapsed = (time.time() - stats['start_time']) / 3600
    rate = stats['processed'] / (elapsed * 3600) if elapsed > 0 else 0
    remaining = stats['total'] - stats['processed']
    eta_hours = remaining / (rate * 3600) if rate > 0 else 0

    logger.info("")
    logger.info(f"Progress Report - {stats['city']}")
    logger.info("-" * 80)
    logger.info(f"Processed: {stats['processed']}/{stats['total']} ({stats['processed']/stats['total']*100:.1f}%)")
    logger.info(f"  Sunny images: {stats['sunny']}")
    logger.info(f"  Weather data added: {stats['weather_added']}")
    logger.info(f"  Weather data failed: {stats['weather_failed']}")
    logger.info(f"  Errors: {stats['errors']}")
    logger.info(f"Performance:")
    logger.info(f"  Elapsed time: {elapsed:.2f} hours")
    logger.info(f"  Processing rate: {rate:.2f} images/second")
    logger.info(f"  Estimated time remaining: {eta_hours:.1f} hours")
    logger.info("-" * 80)
    logger.info("")


def download_image_from_url(image_url, dst_path):
    """Download image from URL to destination path."""
    try:
        with urllib.request.urlopen(image_url) as web_file:
            data = web_file.read()
            with open(dst_path, mode='wb') as local_file:
                local_file.write(data)
        return True
    except Exception as e:
        return False


def get_image_url(image_id):
    """Get Mapillary image URL for given image ID."""
    try:
        random_t = random.randint(1, 10) / 10
        time.sleep(random_t)
        image_url = mly.image_thumbnail(image_id, 2048)
        return image_url
    except Exception as e:
        return None


def download_mapillary_image(image_id, dst_path):
    """Download Mapillary image by ID to destination path."""
    image_url = get_image_url(image_id)
    if image_url:
        return download_image_from_url(image_url, dst_path)
    return False


@retry(wait=wait_exponential(multiplier=1, min=0, max=10), stop=stop_after_attempt(5))
def get_meteostat_hourly(img_point, start_time, end_time, retrieval_timezone):
    """Retrieve hourly weather data with retry logic."""
    data = meteostat.Hourly(img_point, start_time, end_time, retrieval_timezone)
    return data


def get_hourly_weather(row):
    """Get weather data for a single image row."""
    lat = row['lat']
    lon = row['lon']
    img_point = meteostat.Point(lat, lon, 0)
    img_point.alt_range = 2000

    img_time = row['datetime-local']
    img_time = pd.to_datetime(img_time, format='ISO8601', utc=True)

    time_range = timedelta(hours=1)
    start_time = img_time - time_range
    end_time = img_time + time_range

    retrieval_timezone = str(start_time.tz)
    start_time = start_time.replace(tzinfo=None)
    end_time = end_time.replace(tzinfo=None)

    data = get_meteostat_hourly(img_point, start_time, end_time, retrieval_timezone)
    data = data.aggregate('d')
    data = data.fetch()

    if data.empty:
        return None, None, None, None

    dry_bulb_temp = data['temp']
    rel_humidity = data['rhum']
    sunshine_time = data['tsun']
    dew_point = data['dwpt']
    air_pressure = data['pres']

    wet_bulb_temp = wet_bulb_temperature(
        air_pressure.to_numpy() * units.hPa,
        dry_bulb_temp.to_numpy() * units.degC,
        dew_point.to_numpy() * units.degC
    )

    wbulb_val = wet_bulb_temp.magnitude
    if hasattr(wbulb_val, '__len__'):
        wbulb = float(wbulb_val[0]) if len(wbulb_val) > 0 else None
    else:
        wbulb = float(wbulb_val)

    dbulb = float(dry_bulb_temp.to_numpy()[0])
    tsun = float(sunshine_time.to_numpy()[0]) if not pd.isna(sunshine_time.to_numpy()[0]) else None
    rhum = float(rel_humidity.to_numpy()[0]) if not pd.isna(rel_humidity.to_numpy()[0]) else None

    return wbulb, dbulb, tsun, rhum


class HotCitiesPipeline:
    """Complete pipeline for sunny/shade classification + weather data."""

    def __init__(self, vit_model_path="models/vit_binary.pth", yolo_model_path="models/yolo_best.pt",
                 mapillary_token=None, logger=None):
        """Initialize pipeline with models."""
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.logger = logger or logging.getLogger('hot_cities_pipeline')

        self.logger.info(f"Initializing pipeline...")
        self.logger.info(f"  Device: {self.device}")
        self.logger.info(f"  GPU available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            self.logger.info(f"  GPU name: {torch.cuda.get_device_name(0)}")
            self.logger.info(f"  GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")

        # Set Mapillary token
        if mapillary_token:
            mly.set_access_token(mapillary_token)
        else:
            mly.set_access_token('MLY|9798203303595429|e2d4e749e96af419787ec1ca33019e3f')

        # Load ViT model
        self.logger.info("Loading ViT model for sunny classification...")
        self.vit_model = models.vit_b_16(pretrained=False)
        self.vit_model.heads = nn.Sequential(
            nn.Linear(self.vit_model.heads.head.in_features, 1)
        )
        self.vit_model.load_state_dict(torch.load(vit_model_path, map_location=self.device))
        self.vit_model.to(self.device)
        self.vit_model.eval()
        self.logger.info("  ✓ ViT model loaded")

        self.vit_transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=(0.5, 0.5, 0.5), std=(0.5, 0.5, 0.5))
        ])

        # Load YOLO model
        self.logger.info("Loading YOLO model for shade detection...")
        self.yolo_model = YOLO(yolo_model_path)
        self.class_names = {0: 'person', 1: 'inshade', 2: 'outshade'}
        self.logger.info("  ✓ YOLO model loaded")
        self.logger.info("Pipeline initialization complete")

    def classify_sunny(self, image_path):
        """Classify whether an image is sunny or not."""
        try:
            img = Image.open(image_path).convert("RGB")
            x = self.vit_transform(img).unsqueeze(0).to(self.device)

            with torch.no_grad():
                output = self.vit_model(x).squeeze(1)
                prob = torch.sigmoid(output).item()
                is_sunny = prob > 0.5

            return is_sunny, prob
        except Exception as e:
            return False, 0.0

    def detect_shade(self, image_path):
        """Detect people and classify as in shade or out of shade."""
        counts = {'person': 0, 'inshade': 0, 'outshade': 0}

        try:
            results = self.yolo_model(image_path, verbose=False)

            for result in results:
                if result.boxes is not None:
                    for box in result.boxes:
                        class_id = int(box.cls.item())
                        class_name = self.class_names.get(class_id, 'unknown')
                        if class_name in counts:
                            counts[class_name] += 1

        except Exception as e:
            pass

        return counts

    def process_city(self, csv_path, output_csv=None, batch_size=50, max_retries=2):
        """Process single city CSV with full pipeline."""
        csv_path = Path(csv_path)
        city_name = csv_path.stem.split('_walkable')[0]

        log_separator(self.logger)
        self.logger.info(f"Processing City: {city_name}")
        log_separator(self.logger)

        if not csv_path.exists():
            self.logger.error(f"CSV file does not exist: {csv_path}")
            raise ValueError(f"CSV file does not exist: {csv_path}")

        # Load CSV
        df = pd.read_csv(csv_path)
        total_rows = len(df)
        self.logger.info(f"Input CSV: {csv_path.name}")
        self.logger.info(f"Total images: {total_rows:,}")

        # Add result columns if needed
        for col in ['is_sunny', 'sunny_probability', 'person_count', 'inshade_count', 'outshade_count', 'wbulb', 'dbulb', 'tsun', 'rhum']:
            if col not in df.columns:
                df[col] = None

        # Output CSV path
        if output_csv is None:
            output_csv = csv_path.parent / 'output' / f"{csv_path.stem}_annotated.csv"
        output_csv.parent.mkdir(parents=True, exist_ok=True)

        # Temp directory for images
        temp_dir = Path(tempfile.mkdtemp(prefix=f'hot_cities_{city_name}_'))
        self.logger.debug(f"Temporary directory: {temp_dir}")

        # Statistics
        stats = {
            'city': city_name,
            'total': total_rows,
            'processed': 0,
            'sunny': 0,
            'errors': 0,
            'weather_added': 0,
            'weather_failed': 0,
            'start_time': time.time()
        }

        try:
            # Process each row
            for idx, row in tqdm(df.iterrows(), total=total_rows, desc=f"{city_name}"):
                # Skip if already fully processed
                if pd.notna(row.get('is_sunny')) and pd.notna(row.get('wbulb')):
                    stats['processed'] += 1
                    continue

                image_id = str(row['id'])
                temp_image_path = temp_dir / f"{image_id}.jpeg"
                retry_count = 0
                success = False

                # Retry loop for this image
                while retry_count < max_retries and not success:
                    try:
                        # Step 1: Download image (if not already done)
                        if pd.isna(row.get('is_sunny')):
                            download_success = download_mapillary_image(image_id, temp_image_path)

                            if not download_success or not temp_image_path.exists():
                                retry_count += 1
                                continue

                            # Step 2: Classify sunny/shade
                            is_sunny, sunny_prob = self.classify_sunny(temp_image_path)

                            if is_sunny:
                                shade_counts = self.detect_shade(temp_image_path)
                                stats['sunny'] += 1
                            else:
                                shade_counts = {'person': 0, 'inshade': 0, 'outshade': 0}

                            # Store sunny/shade results
                            df.at[idx, 'is_sunny'] = is_sunny
                            df.at[idx, 'sunny_probability'] = sunny_prob
                            df.at[idx, 'person_count'] = shade_counts['person']
                            df.at[idx, 'inshade_count'] = shade_counts['inshade']
                            df.at[idx, 'outshade_count'] = shade_counts['outshade']

                            # Delete image
                            if temp_image_path.exists():
                                temp_image_path.unlink()

                        # Step 3: Add weather data (if not already done)
                        if pd.isna(row.get('wbulb')):
                            wbulb, dbulb, tsun, rhum = get_hourly_weather(df.iloc[idx])

                            df.at[idx, 'wbulb'] = wbulb
                            df.at[idx, 'dbulb'] = dbulb
                            df.at[idx, 'tsun'] = tsun
                            df.at[idx, 'rhum'] = rhum

                            if wbulb is not None:
                                stats['weather_added'] += 1
                            else:
                                stats['weather_failed'] += 1

                        stats['processed'] += 1
                        success = True

                    except Exception as e:
                        retry_count += 1
                        if retry_count >= max_retries:
                            stats['errors'] += 1
                            self.logger.warning(f"Failed to process image {image_id} after {max_retries} retries: {type(e).__name__}: {str(e)}")
                        else:
                            self.logger.debug(f"Retry {retry_count}/{max_retries} for image {image_id}: {type(e).__name__}")

                    finally:
                        # Always clean up temp image
                        if temp_image_path.exists():
                            temp_image_path.unlink()

                # Save progress periodically
                if stats['processed'] % batch_size == 0 and stats['processed'] > 0:
                    df.to_csv(output_csv, index=False)
                    self.logger.debug(f"Checkpoint saved at {stats['processed']} images")

                # Log progress periodically
                if stats['processed'] % LOG_INTERVAL == 0 and stats['processed'] > 0:
                    log_progress_report(self.logger, stats)

            # Final save
            df.to_csv(output_csv, index=False)

            # Calculate final stats
            stats['elapsed_hours'] = (time.time() - stats['start_time']) / 3600

            self.logger.info("")
            log_separator(self.logger)
            self.logger.info(f"City Complete: {city_name}")
            log_separator(self.logger)
            self.logger.info(f"Summary:")
            self.logger.info(f"  Total images: {stats['total']:,}")
            self.logger.info(f"  Successfully processed: {stats['processed']:,}")
            self.logger.info(f"  Sunny images: {stats['sunny']:,}")
            self.logger.info(f"  Weather data added: {stats['weather_added']:,}")
            self.logger.info(f"  Weather data failed: {stats['weather_failed']:,}")
            self.logger.info(f"  Errors: {stats['errors']:,}")
            self.logger.info(f"  Processing time: {stats['elapsed_hours']:.2f} hours")
            self.logger.info(f"  Output saved to: {output_csv}")
            log_separator(self.logger)

        finally:
            # Clean up temp directory
            if temp_dir.exists():
                import shutil
                shutil.rmtree(temp_dir)

        return stats


def process_all_cities(data_dir, output_dir, batch_size=50, log_file='pipeline.log'):
    """Process all walkable CSVs with comprehensive logging."""
    data_dir = Path(data_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Set up logging
    logger = setup_logging(log_file)

    # Get all walkable CSVs
    csv_files = sorted(list(data_dir.glob('*_walkable_*.csv')))
    # Filter out test files
    csv_files = [f for f in csv_files if 'test' not in f.name.lower()]

    log_separator(logger)
    logger.info("Hot Cities Full Pipeline")
    log_separator(logger)
    logger.info("")
    logger.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Data directory: {data_dir}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Log file: {log_file}")
    logger.info(f"Found {len(csv_files)} cities to process")
    logger.info("")
    logger.info("Cities:")
    for i, f in enumerate(csv_files, 1):
        city_name = f.stem.split('_walkable')[0]
        num_images = len(pd.read_csv(f))
        logger.info(f"  {i}. {city_name}: {num_images:,} images")
    logger.info("")

    # Initialize pipeline
    pipeline = HotCitiesPipeline(logger=logger)

    # Overall statistics
    all_stats = []
    overall_start = time.time()

    # Process each city
    for i, csv_file in enumerate(csv_files, 1):
        city_name = csv_file.stem.split('_walkable')[0]

        logger.info("")
        logger.info("")
        log_separator(logger)
        logger.info(f"City {i}/{len(csv_files)}: {city_name}")
        log_separator(logger)
        logger.info("")

        output_csv = output_dir / f"{csv_file.stem}_annotated.csv"

        try:
            stats = pipeline.process_city(csv_file, output_csv, batch_size)
            all_stats.append(stats)

            logger.info("")
            logger.info(f"✓ City {i}/{len(csv_files)} complete: {city_name}")
            logger.info(f"  Progress: {i}/{len(csv_files)} cities ({i/len(csv_files)*100:.1f}%)")

            # Calculate overall progress
            overall_elapsed = (time.time() - overall_start) / 3600
            cities_per_hour = i / overall_elapsed if overall_elapsed > 0 else 0
            remaining_cities = len(csv_files) - i
            eta_hours = remaining_cities / cities_per_hour if cities_per_hour > 0 else 0
            logger.info(f"  Overall time: {overall_elapsed:.2f} hours")
            logger.info(f"  Estimated time remaining: {eta_hours:.1f} hours")
            logger.info("")

        except Exception as e:
            logger.error("")
            logger.error(f"✗ FATAL ERROR processing {city_name}")
            logger.error(f"  {type(e).__name__}: {str(e)}")
            logger.error(f"  Moving to next city...")
            logger.error("")
            continue

    # Final summary
    overall_elapsed = (time.time() - overall_start) / 3600
    total_processed = sum(s['processed'] for s in all_stats)
    total_images = sum(s['total'] for s in all_stats)
    total_sunny = sum(s['sunny'] for s in all_stats)
    total_weather = sum(s['weather_added'] for s in all_stats)
    total_errors = sum(s['errors'] for s in all_stats)

    logger.info("")
    logger.info("")
    log_separator(logger, '=')
    logger.info("ALL CITIES COMPLETE")
    log_separator(logger, '=')
    logger.info("")
    logger.info(f"Completion time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Total processing time: {overall_elapsed:.2f} hours ({overall_elapsed/24:.1f} days)")
    logger.info("")
    logger.info(f"Overall Statistics:")
    logger.info(f"  Cities processed: {len(all_stats)}/{len(csv_files)}")
    logger.info(f"  Total images processed: {total_processed:,}/{total_images:,}")
    logger.info(f"  Sunny images: {total_sunny:,}")
    logger.info(f"  Weather data added: {total_weather:,}")
    logger.info(f"  Total errors: {total_errors:,}")
    logger.info("")
    logger.info("Per-city summary:")
    log_separator(logger, '-')
    for s in all_stats:
        logger.info(f"  {s['city']:20s} | {s['processed']:>6,}/{s['total']:>6,} | "
                   f"Sunny: {s['sunny']:>5,} | Weather: {s['weather_added']:>5,} | "
                   f"Errors: {s['errors']:>3,} | Time: {s['elapsed_hours']:>5.1f}h")
    log_separator(logger, '-')
    logger.info("")
    logger.info(f"Annotated CSVs saved to: {output_dir}")
    logger.info("")
    log_separator(logger, '=')


if __name__ == "__main__":
    import sys

    data_dir = sys.argv[1] if len(sys.argv) > 1 else "data"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"

    process_all_cities(data_dir, output_dir)
