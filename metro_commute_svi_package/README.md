# Metro Cities Commute-Time SVI Analysis Package

This package contains everything needed to analyze street view imagery during commute hours (8-10am and 4-6pm local time) for 19 US metro cities.

## What's Included

- **Pre-filtered Metadata**: 5.97M images filtered to commute hours only (27% of total)
- **ML Models**: Pre-trained ViT (sunny/cloudy) and YOLO (shade detection) models
- **Pipeline Script**: Automated processing pipeline
- **Dependencies**: Full requirements.txt

## Cities Included

19 US metro cities with travel survey data:
- Phoenix (1.84M commute-time images)
- Los Angeles (964K)
- Seattle (623K)
- Boston (443K)
- San Francisco (385K)
- And 14 more cities

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 2. Run Pipeline

Process all cities:
```bash
python scripts/pipelines/metro_commute_svi_pipeline.py
```

Process specific cities:
```bash
python scripts/pipelines/metro_commute_svi_pipeline.py --cities Boston Seattle
```

Custom output directory:
```bash
python scripts/pipelines/metro_commute_svi_pipeline.py --output-dir my_output
```

## Expected Performance

With RTX 4090 24GB GPU:
- **Conservative**: ~23 days (3 img/sec)
- **Typical**: ~17 days (4 img/sec)
- **Optimistic**: ~14 days (5 img/sec)

With 8GB GPU:
- **Typical**: ~46 days (1.5 img/sec)

CPU only (not recommended):
- ~346 days (0.2 img/sec)

## Output Format

Results are saved as CSV files per city:
- `{city}_svi_analyzed.csv`

Columns:
- `image_id`: Mapillary image ID
- `lat`, `lon`: Image coordinates
- `captured_at`: Timestamp
- `is_sunny`: Binary classification
- `has_shade`: Boolean
- `shade_percentage`: Float (0-100)
- `detection_count`: Number of shade objects detected

## Pre-Filtered Metadata Details

The metadata has been pre-filtered to include only images captured during:
- **Morning commute**: 8:00-10:00 local time
- **Evening commute**: 16:00-18:00 (4-6pm) local time

This reduces the dataset by ~73% while focusing on times when pedestrians are most active.

## System Requirements

**Minimum**:
- Python 3.8+
- 16GB RAM
- 100GB free disk space
- GPU with 8GB VRAM (or CPU mode)

**Recommended**:
- Python 3.10+
- 32GB+ RAM
- 200GB+ free disk space
- RTX 4090 24GB or similar GPU

## Troubleshooting

**Out of memory errors**:
- Reduce batch size in `sunny_shade_pipeline.py`
- Use smaller ViT/YOLO batch sizes (see METRO_SVI_OPTIMIZATIONS.md)

**Rate limiting**:
- Pipeline includes automatic retry with exponential backoff
- Max 100 concurrent downloads (configurable)

**Missing models**:
- Ensure `models/vit_binary.pth` and `models/yolo_best.pt` exist
- Re-extract the package if files are missing

## Citation

If you use this dataset/analysis in your research, please cite:
[Add your citation here]

## License

[Add license information]

## Support

For questions or issues, contact:
[Add contact information]
