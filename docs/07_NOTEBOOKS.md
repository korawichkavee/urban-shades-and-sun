# Jupyter Notebooks Guide

## Overview

Interactive notebooks for exploratory analysis, prototyping, and visualization development.

Located in: `notebooks/`

## Available Notebooks

### Data Exploration

#### `prelim_data_analysis.ipynb`
Initial exploratory data analysis of street view imagery dataset.

**Purpose**: Understand data distributions, patterns, and quality issues.

**Contents**:
- Dataset size and coverage statistics
- Geographic distribution of images
- Temporal distribution (time of day, day of week)
- Basic image quality metrics
- Missing data analysis

**Key Outputs**:
- Summary statistics tables
- Distribution histograms
- Geographic scatter plots
- Temporal patterns

**When to Use**: Starting analysis on new city or dataset.

---

#### `02_metadata.ipynb`
Deep dive into image metadata structure and enrichment.

**Purpose**: Analyze and validate metadata fields.

**Contents**:
- Metadata schema exploration
- Timestamp formats and timezone handling
- Coordinate precision and accuracy
- Sequence ID analysis
- Camera angle distributions

**Key Insights**:
- Metadata completeness by source (Mapillary vs KartaView)
- Temporal coverage gaps
- Geographic sampling density

---

### Data Processing

#### `df_aggregator.ipynb`
Aggregates data from multiple cities into unified datasets.

**Purpose**: Combine city-level CSVs with proper handling of schema differences.

**Contents**:
- Schema normalization
- Column mapping across cities
- Handling missing columns
- Concatenation strategies
- Deduplication

**Usage Pattern**:
```python
# Load notebook in Jupyter
# Modify CITY_LIST variable
# Run all cells
# Output: combined_dataset.csv
```

**When to Use**: Before cross-city analysis or visualization.

---

#### `prelim_filtering_more_efficient.ipynb`
Optimized filtering approach for large datasets.

**Purpose**: Develop and test efficient filtering logic.

**Contents**:
- Vectorized filtering operations
- Memory-efficient chunking
- Filter performance benchmarking
- Different filtering strategies comparison

**Key Techniques**:
- Pandas query optimization
- Boolean indexing
- Chunked processing

**Output**: Production-ready filtering code (used in `prelim_filtering_tmux.py`).

---

### City Analysis

#### `full_city_list_filtering.ipynb`
Filters and analyzes the complete city list for hot day identification.

**Purpose**: Identify cities with sufficient hot days for analysis.

**Contents**:
- Load city temperature data
- Define "hot day" threshold
- Count hot days per city
- Filter by minimum hot day count
- Population and coverage criteria

**Output**:
- `docs/hot_cities.txt` - List of cities meeting criteria
- `docs/hot_cities_ids.txt` - City IDs for API queries

**Criteria Used**:
- At least 10 hot days (>30°C)
- Population > 200,000
- Minimum Mapillary coverage

---

#### `city_pop_histogram.ipynb`
Visualizes city population distributions in the dataset.

**Purpose**: Understand population distribution across analyzed cities.

**Contents**:
- Population histogram
- Relationship between population and image count
- Urban area size vs coverage
- Statistical summaries

**Key Insights**:
- Sampling bias toward large cities
- Coverage gaps in mid-size cities

---

### Geographic Analysis

#### `10_osm.ipynb`
OpenStreetMap data integration and exploration.

**Purpose**: Prototype OSM data enrichment workflows.

**Contents**:
- OSMnx library usage examples
- Street network download
- Spatial join operations
- Street type classification
- Walkability scoring

**Key Functions Developed**:
- `get_nearest_street()` - Find closest OSM street to image
- `classify_walkability()` - Determine if street is walkable
- `extract_street_features()` - Get street width, surface, etc.

**Output**: Logic integrated into `scripts/processing/append_osmnx.py`.

---

### Experimental Notebooks

#### `zen_svi_test.ipynb`
Tests ZenSVI library for street view downloads.

**Purpose**: Evaluate alternative SVI download method.

**Status**: Experimental, not used in main pipeline.

**Findings**:
- ZenSVI is simpler API but limited filtering options
- No efficient date filtering
- Slower than direct Mapillary API

**Conclusion**: Direct Mapillary API preferred.

---

#### `image_sampler.ipynb`
Random image sampling for annotation and quality checks.

**Purpose**: Create balanced sample for manual review or annotation.

**Contents**:
- Stratified sampling by city
- Time-stratified sampling
- Temperature-stratified sampling
- Export sample for annotation tools

**Usage**:
```python
# Sample 100 images per city
sample = stratified_sample(df, n_per_city=100)
sample.to_csv('annotation_sample.csv')
```

---

## Notebook Best Practices

### Running Notebooks

```bash
# Start Jupyter
cd /home/kieran/Documents/Python/sunny_day_SVI
jupyter notebook

# Or Jupyter Lab (recommended)
jupyter lab
```

### Kernel Management

```bash
# Install project as kernel
python -m ipykernel install --user --name sunny_svi --display-name "Sunny Day SVI"

# List kernels
jupyter kernelspec list

# Remove kernel
jupyter kernelspec uninstall sunny_svi
```

### Memory Management

For large datasets:

```python
# Read in chunks
chunks = pd.read_csv('large_file.csv', chunksize=10000)
for chunk in chunks:
    process(chunk)

# Clear variables
del large_dataframe
import gc
gc.collect()

# Monitor memory
import psutil
print(f"Memory: {psutil.virtual_memory().percent}%")
```

---

## Common Workflows

### Exploratory Analysis on New City

1. Start with `prelim_data_analysis.ipynb`
   - Load city CSV
   - Run basic statistics
   - Identify data quality issues

2. Check metadata with `02_metadata.ipynb`
   - Validate timestamps
   - Check coordinate coverage
   - Assess completeness

3. Add OSM context using `10_osm.ipynb`
   - Download street network
   - Spatial join
   - Classify streets

4. Create visualizations (custom cells or new notebook)

---

### Developing New Processing Logic

1. Create new notebook in `notebooks/`
2. Prototype logic on small sample
3. Test on full dataset (or subset)
4. Optimize for performance
5. Extract to Python script in `scripts/`

**Example**:
```python
# In notebook: prototype UTCI calculation
def calculate_utci_prototype(temp, rh, wind):
    # ... logic ...
    return utci

# Test on sample
sample['utci'] = sample.apply(lambda r: calculate_utci_prototype(r.temp, r.rh, r.wind), axis=1)

# Once working, move to scripts/processing/utci_calculator.py
```

---

### Analyzing Pipeline Results

After running pipeline:

1. Load processed data in notebook
2. Compute summary statistics
3. Generate diagnostic plots
4. Identify outliers or errors
5. Iterate on pipeline parameters

```python
# Load results
df = pd.read_csv('data/processed/Bangkok_annotated_with_utci.csv')

# Quick checks
print(df.describe())
print(df['utci_celsius'].hist(bins=50))
print(df[df['utci_celsius'] > 50])  # Outliers?
```

---

## Converting Notebooks to Scripts

### Manual Conversion

Extract code cells to `.py` file:
- Remove exploratory/debugging code
- Add proper imports and functions
- Add command-line argument parsing
- Add error handling and logging

### Automated Conversion

```bash
# Convert notebook to Python script
jupyter nbconvert --to script notebooks/my_notebook.ipynb

# Output: notebooks/my_notebook.py
# Then clean up and move to scripts/
```

### Papermill (Parameterized Notebooks)

Run notebooks programmatically:

```bash
pip install papermill

# Run notebook with parameters
papermill notebooks/analysis.ipynb outputs/results.ipynb \
  -p city "Bangkok" \
  -p date "2023-07-15"
```

---

## Notebook Organization Tips

### Cell Structure

```python
# --- Configuration ---
DATA_DIR = Path('data/processed')
CITY = 'Bangkok'

# --- Load Data ---
df = pd.read_csv(DATA_DIR / f'{CITY}_with_utci.csv')

# --- Analysis ---
# ... analysis cells ...

# --- Visualization ---
# ... plot cells ...

# --- Export ---
results.to_csv('output.csv')
```

### Version Control

- Commit notebooks with cleared output:
  ```bash
  jupyter nbconvert --clear-output --inplace notebooks/*.ipynb
  ```

- Use `nbdime` for better notebook diffs:
  ```bash
  pip install nbdime
  nbdime config-git --enable
  ```

### Documentation in Notebooks

Use markdown cells for:
- Section headers
- Explanation of analysis steps
- Interpretation of results
- TODOs and notes

---

## Visualization in Notebooks

### Interactive Plots

```python
# Plotly for interactive exploration
import plotly.express as px

fig = px.scatter(df, x='utci_celsius', y='shade_ratio',
                 color='city', hover_data=['captured_at'])
fig.show()
```

### Inline vs External Plots

```python
# Inline (for exploration)
%matplotlib inline
plt.plot(x, y)

# External window (for detailed inspection)
%matplotlib qt
plt.plot(x, y)

# High-res export
plt.savefig('figure.png', dpi=300, bbox_inches='tight')
```

---

## Performance Optimization

### Profiling

```python
# Time a cell
%%time
# ... code to time ...

# Profile a cell
%load_ext line_profiler
%lprun -f function_name function_name(args)
```

### Caching Results

```python
from functools import lru_cache
import pickle

# Cache function results
@lru_cache(maxsize=1000)
def expensive_computation(param):
    # ...
    return result

# Cache dataframes
cache_file = 'cache/processed_df.pkl'
if Path(cache_file).exists():
    df = pd.read_pickle(cache_file)
else:
    df = expensive_processing()
    df.to_pickle(cache_file)
```

---

## Troubleshooting

### Kernel Dies

Common causes:
- Out of memory → Reduce dataset size or process in chunks
- Infinite loop → Check loop conditions
- Segmentation fault → Update libraries (numpy, pandas)

### Import Errors

```python
# Add project root to path
import sys
sys.path.append('/home/kieran/Documents/Python/sunny_day_SVI')

# Now can import project modules
from enhanced_utci import get_enhanced_utci_data
```

### Slow Notebook

- Restart kernel and run only essential cells
- Use `%%time` to identify slow cells
- Move heavy computation to scripts, load results in notebook

---

## Sharing Notebooks

### Clean Before Sharing

```bash
# Clear outputs
jupyter nbconvert --clear-output --inplace notebook.ipynb

# Or use nbstripout (automatic)
pip install nbstripout
nbstripout --install  # Adds pre-commit hook
```

### Export Formats

```bash
# HTML (interactive, no code execution needed)
jupyter nbconvert --to html notebook.ipynb

# PDF (via LaTeX)
jupyter nbconvert --to pdf notebook.ipynb

# Markdown
jupyter nbconvert --to markdown notebook.ipynb
```

### NBViewer

Share static view online:
```
https://nbviewer.org/github/{user}/{repo}/blob/main/notebooks/analysis.ipynb
```
