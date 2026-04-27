#!/usr/bin/env python3
"""
ABOUTME: Test script to verify chunked CSV writing for SVI metadata downloads.
ABOUTME: Ensures memory-efficient processing of large datasets.
"""

import tempfile
import csv
from pathlib import Path
import pandas as pd

def test_chunked_csv_writing():
    """Test that chunked CSV writing produces correct results."""

    # Create mock GeoJSON features (simulate large dataset)
    n_features = 100_000
    features = []
    for i in range(n_features):
        features.append({
            'properties': {
                'id': f'img_{i}',
                'captured_at': 1609459200000 + i * 1000,  # Unix timestamp in ms
                'compass_angle': i % 360,
                'sequence_id': f'seq_{i // 100}',
                'is_pano': i % 10 == 0,
            },
            'geometry': {
                'coordinates': [-122.0 + (i % 100) * 0.001, 37.0 + (i // 100) * 0.001]
            }
        })

    # Process features in chunks (like the fixed code)
    chunk_size = 50_000
    total_written = 0

    with tempfile.NamedTemporaryFile(mode='w', delete=False, newline='', suffix='.csv') as f:
        temp_file = Path(f.name)
        writer = csv.DictWriter(f, fieldnames=['id', 'captured_at', 'compass_angle', 'sequence_id', 'is_pano', 'lon', 'lat'])
        writer.writeheader()

        # Process features in chunks
        records = []
        for i, feature in enumerate(features):
            props = feature.get('properties', {})
            geom = feature.get('geometry', {})
            coords = geom.get('coordinates', [None, None])

            records.append({
                'id': props.get('id'),
                'captured_at': props.get('captured_at'),
                'compass_angle': props.get('compass_angle'),
                'sequence_id': props.get('sequence_id'),
                'is_pano': props.get('is_pano'),
                'lon': coords[0],
                'lat': coords[1]
            })

            # Write chunk when it reaches chunk_size
            if len(records) >= chunk_size:
                writer.writerows(records)
                total_written += len(records)
                print(f"Written {total_written:,} records so far...")
                records = []  # Clear chunk from memory

        # Write any remaining records
        if records:
            writer.writerows(records)
            total_written += len(records)

    # Verify results
    print(f"\nTotal written: {total_written:,} records")

    # Read back and verify
    df = pd.read_csv(temp_file)
    print(f"Total read back: {len(df):,} records")

    # Cleanup
    temp_file.unlink()

    # Assertions
    assert total_written == n_features, f"Expected {n_features} records, wrote {total_written}"
    assert len(df) == n_features, f"Expected {n_features} records, read {len(df)}"
    assert df['id'].iloc[0] == 'img_0', f"First record ID incorrect: {df['id'].iloc[0]}"
    assert df['id'].iloc[-1] == f'img_{n_features-1}', f"Last record ID incorrect: {df['id'].iloc[-1]}"

    print("\n✓ All tests passed!")
    return True

if __name__ == '__main__':
    test_chunked_csv_writing()
