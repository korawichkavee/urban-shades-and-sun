# UTCI Annotation Job Status

**Started**: 2026-01-27 13:58:16 EST
**Session**: nhts_utci_annotation
**Status**: RUNNING

**UPDATE**: Restarted with improved datetime handling
- Now uses TRAVDAY to select appropriate day-of-week from month
- Random seed (42) ensures reproducibility
- Reduces temporal uncertainty from ±15 days to ±7 days (within-week variation)

## Job Details

- **Total trips**: 923,556
- **Processing mode**: Chunked with checkpoints (5,000 trips per chunk)
- **Workers**: 15 parallel threads
- **Estimated duration**: 5-8 hours (depending on API rate limits and cache hits)

## Files

### Logs
- **Main log**: `logs/tmux_utci_20260127_135017.log`
- **Detailed log**: `logs/utci_chunked_20260127_135018.log`

### Output Files
- **Checkpoint** (during run): `data/transit_surveys/processed/nhts_2017_standardized_with_utci_checkpoint.csv`
- **Final output**: `data/transit_surveys/processed/nhts_2017_standardized_with_utci.csv`

## Monitoring

### View real-time progress
```bash
tail -f logs/tmux_utci_20260127_135017.log
```

### Attach to tmux session
```bash
tmux attach -t nhts_utci_annotation
# Detach: Ctrl+B, then D
```

### Check session status
```bash
tmux list-sessions | grep nhts
```

## Features

### Checkpointing
- Saves progress every 5,000 trips
- Safe to interrupt with Ctrl+C
- Resume with: `python scripts/travel_surveys/add_utci_chunked.py --resume`

### Progress Tracking
- Real-time progress bar for each chunk
- ETA calculation after each chunk
- Completion rates logged

### Location Annotation
- **location_is_placeholder**: Boolean field indicating when state centroid is used
- All NHTS trips use state-level approximations (location_is_placeholder=True)
- Future surveys with precise coordinates will have location_is_placeholder=False

## Completion

Upon completion:
1. Desktop notification sent
2. Checkpoint file removed
3. Final output saved to: `data/transit_surveys/processed/nhts_2017_standardized_with_utci.csv`

## Next Steps (After Completion)

### Run Visualization
```bash
python scripts/travel_surveys/visualize_pedestrian_vs_temperature.py
```

### Check Outputs
```bash
ls -lh outputs/travel_surveys/
# pedestrian_mode_vs_temperature.png
# temperature_distribution_by_mode.png
```

## Troubleshooting

### If job is interrupted
The checkpoint system allows seamless resumption:
```bash
python scripts/travel_surveys/add_utci_chunked.py --resume
```

### If rate limited
Reduce workers and resume:
```bash
python scripts/travel_surveys/add_utci_chunked.py --resume --workers 10
```

### Kill running job
```bash
tmux kill-session -t nhts_utci_annotation
```

## Expected Completion

Based on initial processing rate (~30-80 trips/sec), estimated completion:
- **Optimistic** (high cache hit rate): ~3-4 hours
- **Realistic** (moderate cache): ~5-6 hours
- **Conservative** (low cache, rate limits): ~7-8 hours

Check progress periodically to monitor actual rate.
