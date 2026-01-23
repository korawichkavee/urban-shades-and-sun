#!/usr/bin/env python3
# ABOUTME: Adds weather data to walkable street images with checkpointing and resume
# ABOUTME: Designed for long-running tmux sessions with progress tracking and error handling

import pandas as pd
from pathlib import Path
from datetime import datetime
import time
import json
from add_weather_data import get_hourly_weather

# Configuration
CHECKPOINT_INTERVAL = 50  # Save progress every N rows
LOG_FILE = Path('weather_processing.log')
CHECKPOINT_FILE = Path('weather_checkpoint.json')

def log_message(message):
    """Write timestamped message to log file and print to console."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    with open(LOG_FILE, 'a') as f:
        f.write(log_entry + '\n')

def save_checkpoint(csv_path, last_processed_idx, stats):
    """Save processing checkpoint to file."""
    checkpoint = {
        'csv_path': str(csv_path),
        'last_processed_idx': last_processed_idx,
        'stats': stats,
        'timestamp': datetime.now().isoformat()
    }
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(checkpoint, f, indent=2)

def load_checkpoint(csv_path):
    """Load checkpoint if exists for this CSV."""
    if not CHECKPOINT_FILE.exists():
        return None

    with open(CHECKPOINT_FILE, 'r') as f:
        checkpoint = json.load(f)

    # Check if checkpoint is for the same file
    if checkpoint['csv_path'] == str(csv_path):
        return checkpoint
    return None

def process_csv_with_checkpoints(csv_path, start_idx=0):
    """Process CSV with checkpointing and resume capability."""

    log_message("="*60)
    log_message(f"Processing: {csv_path.name}")
    log_message("="*60)

    # Load CSV
    df = pd.read_csv(csv_path)
    total_rows = len(df)
    log_message(f"Total rows: {total_rows}")

    if start_idx > 0:
        log_message(f"Resuming from row {start_idx}")
    else:
        log_message("Starting from beginning")

    # Check if weather columns already exist
    if 'wbulb' not in df.columns:
        df['wbulb'] = None
        df['dbulb'] = None
        df['tsun'] = None
        df['rhum'] = None

    # Statistics
    stats = {
        'success': 0,
        'errors': 0,
        'skipped': 0,
        'start_time': time.time()
    }

    # Process rows
    for idx in range(start_idx, total_rows):
        # Skip if already has weather data
        if pd.notna(df.at[idx, 'wbulb']):
            stats['skipped'] += 1
            continue

        try:
            row = df.iloc[idx]
            row_with_weather = get_hourly_weather(row)

            # Update dataframe
            df.at[idx, 'wbulb'] = row_with_weather.get('wbulb')
            df.at[idx, 'dbulb'] = row_with_weather.get('dbulb')
            df.at[idx, 'tsun'] = row_with_weather.get('tsun')
            df.at[idx, 'rhum'] = row_with_weather.get('rhum')

            stats['success'] += 1

        except Exception as e:
            log_message(f"  ERROR on row {idx} (image {df.at[idx, 'id']}): {type(e).__name__}: {str(e)}")
            stats['errors'] += 1

        # Checkpoint and progress report
        if (idx + 1) % CHECKPOINT_INTERVAL == 0:
            # Save checkpoint
            save_checkpoint(csv_path, idx, stats)

            # Save progress to CSV
            df.to_csv(csv_path, index=False)

            # Calculate progress
            processed = idx + 1 - start_idx
            elapsed = time.time() - stats['start_time']
            rate = processed / elapsed if elapsed > 0 else 0
            remaining = total_rows - (idx + 1)
            eta_seconds = remaining / rate if rate > 0 else 0
            eta_hours = eta_seconds / 3600

            log_message(f"Progress: {idx+1}/{total_rows} ({(idx+1)/total_rows*100:.1f}%)")
            log_message(f"  Success: {stats['success']}, Errors: {stats['errors']}, Skipped: {stats['skipped']}")
            log_message(f"  Rate: {rate:.2f} rows/sec, ETA: {eta_hours:.1f} hours")

    # Final save
    df.to_csv(csv_path, index=False)

    # Calculate final stats
    elapsed = time.time() - stats['start_time']
    log_message("")
    log_message("="*60)
    log_message(f"Processing Complete: {csv_path.name}")
    log_message("="*60)
    log_message(f"Total rows: {total_rows}")
    log_message(f"Success: {stats['success']}")
    log_message(f"Errors: {stats['errors']}")
    log_message(f"Skipped (already had weather): {stats['skipped']}")
    log_message(f"Total time: {elapsed/3600:.2f} hours")
    log_message("")

    return stats

def main():
    """Process all walkable CSVs with resume capability."""

    log_message("="*60)
    log_message("Weather Data Addition - Overnight Processing")
    log_message("="*60)

    base_dir = Path('/home/kieran/Documents/Python/sunny_day_SVI/city7sample')

    # Find all walkable CSVs
    walkable_csvs = sorted(base_dir.glob('*_walkable_*.csv'))

    if not walkable_csvs:
        log_message("No walkable CSV files found")
        return

    log_message(f"\nFound {len(walkable_csvs)} walkable CSV files:")
    for csv_file in walkable_csvs:
        df = pd.read_csv(csv_file, nrows=1)
        total = len(pd.read_csv(csv_file))
        has_weather = 'wbulb' in df.columns
        log_message(f"  {csv_file.name}: {total} images, has weather: {has_weather}")

    log_message("")

    # Process each CSV
    all_stats = []
    for csv_file in walkable_csvs:
        # Check for checkpoint
        checkpoint = load_checkpoint(csv_file)
        start_idx = 0

        if checkpoint:
            log_message(f"\nFound checkpoint for {csv_file.name}")
            log_message(f"  Last processed: row {checkpoint['last_processed_idx']}")
            log_message(f"  Previous stats: {checkpoint['stats']}")
            response = input("Resume from checkpoint? (y/n): ")
            if response.lower() == 'y':
                start_idx = checkpoint['last_processed_idx'] + 1

        # Process
        try:
            stats = process_csv_with_checkpoints(csv_file, start_idx)
            all_stats.append((csv_file.name, stats))

            # Clear checkpoint after successful completion
            if CHECKPOINT_FILE.exists():
                CHECKPOINT_FILE.unlink()

        except KeyboardInterrupt:
            log_message("\n\nProcessing interrupted by user")
            log_message("Progress has been saved. Re-run to resume from last checkpoint.")
            return

        except Exception as e:
            log_message(f"\n\nFATAL ERROR processing {csv_file.name}:")
            log_message(f"  {type(e).__name__}: {str(e)}")
            log_message("Progress has been saved. Fix error and re-run to resume.")
            return

    # Final summary
    log_message("\n" + "="*60)
    log_message("ALL PROCESSING COMPLETE")
    log_message("="*60)
    for csv_name, stats in all_stats:
        log_message(f"{csv_name}:")
        log_message(f"  Success: {stats['success']}, Errors: {stats['errors']}, Skipped: {stats['skipped']}")
    log_message("")

if __name__ == '__main__':
    # Change to script directory
    import os
    os.chdir(Path(__file__).parent)
    main()
