# Visualization Guide

## Overview

Scripts for generating plots and visualizations of shade-seeking behavior and thermal comfort analysis.

Located in: `scripts/visualization/`

## Core Visualization Scripts

### `visualize_shade_ratios.py` ⭐ PRIMARY SCRIPT

Generates comprehensive visualizations comparing shade-seeking behavior across temperature measures.

**Purpose**: Create publication-quality plots for behavioral analysis.

**Usage**:
```bash
python scripts/visualization/visualize_shade_ratios.py
```

**Input**:
- Processed CSVs from `data/processed/city_estimate_outcomes/`
- Files ending in `_with_utci.csv`

**Output**:
- Plots saved to `outputs/plots/`
- Two main categories: shade_behavior and people_count

---

### Generated Visualizations

#### Shade Behavior Plots (7 plots)

**Per-City LOESS Plots** (3 plots):
- `shade_behavior/percity_loess_vs_wbulb.png`
- `shade_behavior/percity_loess_vs_dbulb.png`
- `shade_behavior/percity_loess_vs_utci.png`

Shows shade ratio vs temperature for each city individually.

**Overall LOESS Plots** (3 plots):
- `shade_behavior/overall_loess_vs_wbulb.png`
- `shade_behavior/overall_loess_vs_dbulb.png`
- `shade_behavior/overall_loess_vs_utci.png`

Cross-city analysis with balanced sampling.

**Time of Day Analysis** (1 plot):
- `shade_behavior/time_of_day.png`

Shade-seeking patterns by hour of day.

---

#### People Count Plots (12 plots)

Three filtering strategies × three temperature measures = 9 plots:

**Sunny + With People**:
- `people_count/sunny_withpeople_vs_wbulb.png`
- `people_count/sunny_withpeople_vs_dbulb.png`
- `people_count/sunny_withpeople_vs_utci.png`

Only sunny images with at least one person.

**All Rows**:
- `people_count/allrows_vs_wbulb.png`
- `people_count/allrows_vs_dbulb.png`
- `people_count/allrows_vs_utci.png`

All images regardless of conditions.

**Sunny Only**:
- `people_count/sunnyonly_vs_wbulb.png`
- `people_count/sunnyonly_vs_dbulb.png`
- `people_count/sunnyonly_vs_utci.png`

All sunny images including those with zero people.

**Additional People Count Plots** (3 plots):
- Per-city comparisons
- Distribution histograms
- Temperature binned analysis

---

### `visualize_shade_ratios_ipw.py`

Interactive version using Jupyter widgets for exploration.

**Purpose**: Interactive parameter tuning and visualization.

**Usage**:
```python
# In Jupyter notebook
from scripts.visualization.visualize_shade_ratios_ipw import create_interactive_plot
create_interactive_plot()
```

**Features**:
- Temperature measure selection
- City filtering
- Time range adjustment
- Real-time plot updates

---

### Person Count Analysis

#### `plot_person_capture_probability.py`

Analyzes probability of capturing people in images based on temperature.

**Purpose**: Understand sampling bias - are people less likely to be outside when hot?

**Usage**:
```bash
python scripts/visualization/plot_person_capture_probability.py
```

**Output**:
- `outputs/plots/person_probability_*.png`
- Statistical summaries

**Analysis**:
- Logistic regression: P(person present) vs temperature
- Stratified by city and time of day
- Controls for confounders

---

#### `calculate_person_probability_weights.py`

Calculates inverse probability weights to correct for sampling bias.

**Purpose**: Weight observations to account for temperature-dependent visibility.

**Usage**:
```bash
python scripts/visualization/calculate_person_probability_weights.py
```

**Output**:
- CSV with `ipw` (inverse probability weight) column
- Weight distribution diagnostics

**Application**:
Used in regression models to adjust for selection bias.

---

## Plot Interpretation Guide

### Shade Behavior Plots

**What They Show**:
- X-axis: Temperature (°C)
- Y-axis: Shade ratio (0-1)
- Shade ratio = people_in_shade / total_people

**Reading LOESS Curves**:
- Upward slope: More shade-seeking at higher temperatures
- Steeper slope: Stronger behavioral response
- Plateau: Saturation (everyone already in shade)
- Confidence bands: Statistical uncertainty

**Comparing Temperature Measures**:
- **Wet Bulb**: Accounts for humidity
- **Dry Bulb**: Standard air temperature
- **UTCI**: Comprehensive thermal comfort (humidity + wind + radiation)

**Key Question**: Which measure shows the strongest relationship?

---

### People Count Plots

**What They Show**:
- X-axis: Temperature (°C)
- Y-axis: Number of people per image
- Scatter points: Raw data
- LOESS curve: Smoothed trend

**Interpretation**:
- Downward slope: Fewer people at higher temperatures
- Flat line: No temperature effect on outdoor activity
- Different curves across filters reveal:
  - Selection bias effects
  - Weather vs temperature influences

**Filtering Strategy Effects**:
- **Sunny + With People**: Isolates shade-seeking behavior
- **All Rows**: Shows overall outdoor activity
- **Sunny Only**: Separates sun/cloud from temperature effects

---

## Customizing Visualizations

### Modifying `visualize_shade_ratios.py`

Key parameters to adjust:

```python
# LOESS smoothing
LOESS_FRAC = 0.3  # Smoothing fraction (0.1-0.9)

# Sample size for cross-city analysis
SAMPLES_PER_CITY = 500  # Balanced sampling

# Temperature range
TEMP_MIN = 15  # °C
TEMP_MAX = 40  # °C

# Figure size
FIGSIZE = (12, 8)  # inches
```

### Adding New Plot Types

Template for new visualization:

```python
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Load data
data_dir = Path('data/processed/city_estimate_outcomes')
dfs = []
for csv_file in data_dir.glob('*_with_utci.csv'):
    df = pd.read_csv(csv_file)
    dfs.append(df)
combined = pd.concat(dfs, ignore_index=True)

# Create plot
plt.figure(figsize=(10, 6))
# ... your plotting code ...

# Save
output_dir = Path('outputs/plots/custom')
output_dir.mkdir(parents=True, exist_ok=True)
plt.savefig(output_dir / 'my_plot.png', dpi=300, bbox_inches='tight')
plt.close()
```

---

## Output Organization

### Directory Structure

```
outputs/plots/
├── shade_behavior/
│   ├── overall_loess_vs_wbulb.png
│   ├── overall_loess_vs_dbulb.png
│   ├── overall_loess_vs_utci.png
│   ├── percity_loess_vs_wbulb.png
│   ├── percity_loess_vs_dbulb.png
│   ├── percity_loess_vs_utci.png
│   └── time_of_day.png
│
├── people_count/
│   ├── sunny_withpeople_vs_*.png
│   ├── allrows_vs_*.png
│   ├── sunnyonly_vs_*.png
│   └── distribution_*.png
│
└── README.md  # Interpretation guide
```

### File Naming Convention

- `{analysis_type}_{filter}_{vs}_{temp_measure}.png`
- Examples:
  - `overall_loess_vs_utci.png`
  - `sunny_withpeople_vs_wbulb.png`

---

## Common Workflows

### Regenerating All Plots

```bash
# Delete old plots
rm -rf outputs/plots/shade_behavior/
rm -rf outputs/plots/people_count/

# Regenerate
python scripts/visualization/visualize_shade_ratios.py
```

### Generating Plots for Specific Cities

Modify script to filter cities:

```python
# In visualize_shade_ratios.py
CITIES_TO_PLOT = ['Bangkok', 'Singapore', 'Mumbai']

# Filter data
df = df[df['city'].isin(CITIES_TO_PLOT)]
```

### Batch Export for Presentations

```bash
# High-resolution export
python scripts/visualization/visualize_shade_ratios.py --dpi 600

# PDF format
python scripts/visualization/visualize_shade_ratios.py --format pdf
```

(Note: May require script modifications to support these flags)

---

## Statistical Methods

### LOESS Smoothing

**What**: Locally Estimated Scatterplot Smoothing
**Why**: Reveals non-linear relationships without parametric assumptions
**Parameters**:
- `frac`: Smoothing span (0.3 = 30% of data per window)
- Higher frac → smoother curve
- Lower frac → follows data more closely

### Balanced Sampling

**Why**: Cities have different sample sizes
**Method**: Sample equal numbers from each city
**Benefit**: Prevents large cities from dominating cross-city analysis

### Confidence Intervals

- 95% confidence bands on LOESS curves
- Bootstrap resampling (1000 iterations)
- Shows statistical uncertainty

---

## Dependencies

### Python Libraries

```python
matplotlib        # Base plotting
seaborn          # Statistical visualizations
pandas           # Data manipulation
numpy            # Numerical operations
scipy            # LOESS smoothing
statsmodels      # Statistical models
```

### Style Configuration

Default style in scripts:

```python
import seaborn as sns
sns.set_style("whitegrid")
sns.set_palette("husl")
plt.rcParams['figure.dpi'] = 300
```

---

## Troubleshooting

### Memory Issues

Large datasets can cause memory problems:

```python
# Process cities individually
for city_file in data_files:
    df = pd.read_csv(city_file)
    # Generate plot
    # ...
    del df  # Free memory
```

### Missing Data

Handle missing values:

```python
# Drop rows with missing temperature or shade ratio
df = df.dropna(subset=['utci_celsius', 'shade_ratio'])

# Or fill with interpolation
df['utci_celsius'].fillna(method='linear', inplace=True)
```

### Plot Quality Issues

- **Overlapping labels**: Adjust `figsize` or reduce point density
- **Unclear trends**: Adjust LOESS `frac` parameter
- **Poor colors**: Use colorblind-friendly palettes (`sns.color_palette("colorblind")`)

---

## Advanced Visualizations

### Interactive Dashboards

Using Plotly for web-based exploration:

```python
import plotly.express as px

fig = px.scatter(df, x='utci_celsius', y='shade_ratio',
                 color='city', trendline='lowess',
                 hover_data=['captured_at', 'num_people'])
fig.write_html('outputs/plots/interactive_shade.html')
```

### Animation (Time Series)

Show temporal evolution:

```python
import matplotlib.animation as animation

# Animate shade ratio over time of day
# Code example in advanced visualization notebook
```

### Geographic Maps

Spatial distribution of shade-seeking:

```python
import folium
from folium.plugins import HeatMap

# Create heatmap of shade ratios
# Color by temperature
# See notebooks/mapping_examples.ipynb
```

---

## Publication Guidelines

### Resolution
- Screen: 150 DPI
- Print: 300+ DPI
- Large posters: 600 DPI

### Formats
- PNG: General use, web
- PDF: Vector graphics, publications
- SVG: Editable vector format

### Color Schemes
- Use colorblind-safe palettes
- High contrast for readability
- Consistent across figure series

### Fonts
- Minimum 8pt for axis labels
- 10-12pt for titles
- Sans-serif for clarity (Arial, Helvetica)
