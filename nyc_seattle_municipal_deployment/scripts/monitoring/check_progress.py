#!/usr/bin/env python3
# ABOUTME: Check progress of municipal shadow analysis pipeline

from pathlib import Path
import pandas as pd
import sys

def check_progress():
    """Check progress for all cities."""
    base_dir = Path(__file__).parent.parent.parent

    cities = {
        'new-york-city': {
            'metadata': base_dir / 'data/metadata/new-york-city_svi_municipal_only.csv',
            'output': base_dir / 'outputs/new-york-city/new-york-city_shadow_annotated.csv',
            'display_name': 'New York City'
        },
        'seattle': {
            'metadata': base_dir / 'data/metadata/seattle_svi_municipal_only.csv',
            'output': base_dir / 'outputs/seattle/seattle_shadow_annotated.csv',
            'display_name': 'Seattle'
        }
    }

    print("="*70)
    print("MUNICIPAL SHADOW ANALYSIS PIPELINE PROGRESS")
    print("="*70)
    print()

    for city_key, config in cities.items():
        print(f"{config['display_name']}:")

        if not config['metadata'].exists():
            print(f"  ⚠ Metadata file not found")
            print()
            continue

        total_df = pd.read_csv(config['metadata'])
        total = len(total_df)

        if not config['output'].exists():
            print(f"  Total images: {total:,}")
            print(f"  Processed: 0 (0.0%)")
            print(f"  Status: Not started")
        else:
            processed_df = pd.read_csv(config['output'])
            processed = len(processed_df)
            pct = (processed / total) * 100

            print(f"  Total images: {total:,}")
            print(f"  Processed: {processed:,} ({pct:.1f}%)")
            print(f"  Remaining: {total - processed:,}")

            if processed == total:
                print(f"  Status: ✓ Complete")
            else:
                print(f"  Status: In progress...")

        print()

    print("="*70)


if __name__ == '__main__':
    check_progress()
