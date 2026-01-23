# Weather Data Processing - Overnight Instructions

## Quick Start

### 1. Test on Small Sample (RECOMMENDED FIRST)
```bash
cd /home/kieran/Documents/Python/sunny_day_SVI
python3 test_weather_sample.py
```

This tests weather retrieval on 10 images (~20 seconds). Verify it works before running overnight.

### 2. Run Full Dataset in Tmux (Overnight)
```bash
cd /home/kieran/Documents/Python/sunny_day_SVI
./run_weather_tmux.sh
```

The script will:
- Create a tmux session named `weather_processing`
- Run weather data addition for all walkable street images
- Save progress every 50 rows
- Allow you to detach and leave running overnight

### 3. Tmux Commands

**Detach (leave running in background):**
- Press `Ctrl+B`, then press `D`

**Reattach to view progress:**
```bash
tmux attach -t weather_processing
```

**List all tmux sessions:**
```bash
tmux ls
```

**Kill session (if needed):**
```bash
tmux kill-session -t weather_processing
```

## Files Created

- `weather_processing.log` - Timestamped log of all processing
- `weather_checkpoint.json` - Resume point if interrupted
- `*_walkable_*.csv` - Updated with weather columns (wbulb, dbulb, tsun, rhum)

## Resume After Interruption

If processing is interrupted (crash, disconnect, etc.):
1. Re-run `./run_weather_tmux.sh`
2. It will detect the checkpoint and ask if you want to resume
3. Choose 'y' to continue from where it left off

## Expected Processing Time

**Current dataset:**
- Buenos Aires: 21,397 walkable images
- Rate: ~0.5 rows/sec (2 sec per row due to API calls)
- **Estimated time: 11-12 hours**

Other cities (if images are downloaded):
- Madrid: 12,534 images (~7 hours)
- Istanbul: 13,870 images (~8 hours)
- Singapore: 6,953 images (~4 hours)
- Cape Town: 7,330 images (~4 hours)
- Mumbai: 2,551 images (~1.5 hours)

## Monitoring Progress

The log file updates in real-time with:
- Current row being processed
- Success/error counts
- Processing rate
- Estimated time remaining

View live updates:
```bash
tail -f weather_processing.log
```

## Troubleshooting

**If tmux session won't start:**
- Check for existing session: `tmux ls`
- Kill old session: `tmux kill-session -t weather_processing`
- Re-run: `./run_weather_tmux.sh`

**If processing seems stuck:**
- Attach to session: `tmux attach -t weather_processing`
- Check log file: `tail weather_processing.log`
- Meteostat API may be rate-limited (usually resolves automatically)

**If you need to stop:**
- Attach: `tmux attach -t weather_processing`
- Press `Ctrl+C` to stop
- Progress is saved every 50 rows
- Re-run to resume from checkpoint

## Output Columns

After processing, each CSV will have:
- `wbulb` - Wet bulb temperature (°C)
- `dbulb` - Dry bulb temperature (°C)
- `tsun` - Sunshine duration (minutes)
- `rhum` - Relative humidity (%)

All values are hourly averages within ±1 hour of image capture time.
