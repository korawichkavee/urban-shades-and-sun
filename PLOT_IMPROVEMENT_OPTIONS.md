# Plot Improvement Options for shade_preference_adjustment_progression.png

## Current Issues Identified

**From code review (plot_shade_preference_adjustment_progression.py):**
1. ❌ **Lines connecting points** (`linestyle='-'` on line 204) - inappropriate for discrete point estimates
2. ❌ **Generic colors** - manually chosen (#e74c3c, #f39c12, etc.), not verified colorblind-friendly
3. ❌ **Basic grid styling** - simple `alpha=0.3`, could be more refined
4. ❌ **Font styling** - only uses `fontweight='bold'`, no font family specified
5. ❌ **Generic title** - "Shade Response Parameter Estimate\nProgressive Adjustments for Selection Bias"
6. ⚠️ **X-axis labeling** - may be sparse depending on bin count
7. ⚠️ **Error bar styling** - basic, could be refined
8. ⚠️ **Legend position** - bottom center with `bbox_to_anchor` might not be optimal

---

## Research Findings: Publication-Quality Plot Best Practices

### 1. **Remove Connecting Lines for Point Estimates**
**Source:** Jake VanderPlas Python Data Science Handbook, matplotlib errorbar docs

**Best practice:** When plotting discrete measurements/point estimates (not continuous functions), use scatter-style markers WITHOUT connecting lines.

**Implementation:**
```python
# Current (BAD):
linestyle='-'  # Connects points

# Option A - No line:
linestyle='none'  # or linestyle=''

# Option B - Just markers:
fmt='o'  # Marker only, specified in fmt parameter
```

### 2. **Colorblind-Friendly Palettes**
**Source:** pypubfigs, seaborn colorblind palette, tableau-colorblind10

**Best practice:** ~8% of people have color vision deficiency. Use verified colorblind-safe palettes.

**Options:**
- **Seaborn colorblind palette:** `sns.color_palette("colorblind")`
- **Tableau colorblind 10:** `plt.rcParams['axes.prop_cycle'] = plt.cycler(color=plt.cm.tab10.colors)`
- **Paul Tol's palettes:** Bright, Muted, or High Contrast sets
- **Custom verified set:** `['#0173B2', '#DE8F05', '#029E73', '#CC78BC']` (from pypubfigs)

### 3. **Typography**
**Source:** Publication-quality matplotlib guides (2024-2025)

**Best practices:**
- Use specific font families (Helvetica, Arial for sans-serif; Times for serif)
- Match journal requirements
- Use LaTeX rendering for math symbols
- Avoid overly bold text (makes plots look cluttered)

**Options:**
```python
# Option A - Sans-serif (Nature, Science style):
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']

# Option B - Serif (more traditional):
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif']

# Remove bold from labels (lighter weight is cleaner):
fontweight='normal' instead of 'bold'
```

### 4. **Grid Styling**
**Source:** Matplotlib grid tutorials, publication figure guides

**Best practices:**
- Tighter/denser grids help with reading values
- Use minor gridlines for precision
- Lighter colors (higher alpha) for grids behind data
- Grid should be subtle, not dominant

**Options:**
```python
# Option A - Tight grid with major + minor:
ax.grid(True, which='major', alpha=0.3, linestyle='-', linewidth=0.8)
ax.grid(True, which='minor', alpha=0.15, linestyle=':', linewidth=0.5)
ax.minorticks_on()

# Option B - Subtle background grid:
ax.grid(True, alpha=0.2, linestyle='-', linewidth=0.5, color='gray')
ax.set_axisbelow(True)  # Grid behind data

# Option C - Use seaborn ticks style:
sns.set_style("ticks")  # Or "whitegrid" with customization
```

### 5. **X-Axis Labeling**
**Source:** Matplotlib ticker documentation

**Best practice:** For scientific data, show all major values clearly. Use minor ticks for finer reference.

**Options:**
```python
# Option A - Explicit tick locations every 5°C:
ax.set_xticks(np.arange(-20, 35, 5))

# Option B - Major ticks every 5°C, minor every 2.5°C:
from matplotlib.ticker import MultipleLocator
ax.xaxis.set_major_locator(MultipleLocator(5))
ax.xaxis.set_minor_locator(MultipleLocator(2.5))

# Option C - Show all bin centers (if not too many):
ax.set_xticks(results_df['utci'].values)
```

### 6. **Title Improvement**
**Source:** Scientific writing best practices

**Current:** "Shade Response Parameter Estimate\nProgressive Adjustments for Selection Bias"

**Issues:**
- Too generic ("estimate")
- Title line break is awkward
- Doesn't describe what the plot shows (declining trend)

**Options:**
- **Option A (Descriptive):** "Shade Preference vs Temperature with Bias Corrections"
- **Option B (Minimal):** "Shade Preference by UTCI Temperature"
- **Option C (Informative):** "Effect of Bias Corrections on Shade Preference Estimates"
- **Option D (No title):** Remove title, rely on figure caption in paper

### 7. **Error Bar Styling**
**Source:** Matplotlib errorbar best practices

**Current:** Basic error bars with capsize=3

**Options:**
```python
# Option A - Thicker caps for visibility:
capsize=5, capthick=2.0

# Option B - Transparent error bars to reduce clutter:
elinewidth=1.5, alpha=0.6

# Option C - Colored error bars matching points:
ecolor=color (same as marker color)
```

---

## Proposed Improvement Options

### **Option 1: Minimal Changes (Conservative)**

**Changes:**
1. Remove connecting lines: `linestyle='none'` or `fmt='o'`
2. Add more x-axis ticks: every 5°C
3. Tighten grid: add minor gridlines
4. Change title to: "Shade Preference by UTCI Temperature"

**Why:** Fixes the most glaring issue (lines) with minimal risk. Good for quick improvement.

**Code changes:** ~5 lines

---

### **Option 2: Moderate Overhaul (Recommended)**

**Changes:**
1. ✅ Remove connecting lines: `linestyle='none'`
2. ✅ Use colorblind-friendly palette: seaborn "colorblind" or tab10
3. ✅ Change font family: Arial/Helvetica, remove bold
4. ✅ Add minor gridlines: `ax.minorticks_on()` + styling
5. ✅ More x-axis labels: every 5°C with minor at 2.5°C
6. ✅ Improve title: "Effect of Bias Corrections on Shade Preference"
7. ✅ Refine error bars: larger caps, slight transparency

**Why:** Addresses all major issues while maintaining current structure. Publication-ready result.

**Code changes:** ~20 lines

---

### **Option 3: Complete Redesign (Aggressive)**

**Changes from Option 2, plus:**
8. ✅ Separate subplots for each correction level (2x2 grid) instead of overlapping
9. ✅ Add small table/annotation with effect sizes from ablation
10. ✅ Use different marker shapes + colors for better discrimination
11. ✅ Add reference line at 50% shade preference
12. ✅ Annotate key temperatures (e.g., -15°C max, 27°C min)

**Why:** Maximum clarity and information density. Best for main paper figure.

**Code changes:** ~50+ lines (significant refactor)

---

### **Option 4: Alternative Visualization - Offset Points (Advanced)**

**Instead of overlapping 4 curves, offset each slightly on x-axis:**

```
Raw:          o o o o o
Temp:          · · · · ·  (offset +0.3°C)
SR-IPW:         △ △ △ △ △  (offset +0.6°C)
Full:            ◇ ◇ ◇ ◇ ◇  (offset +0.9°C)
```

**Why:** Makes individual points visible even when values are similar. Common in experimental science.

**Code changes:** ~15 lines (modify x-coordinates before plotting)

---

## Specific Code Recommendations

### Fix 1: Remove Lines (ESSENTIAL)

**Current (line 204):**
```python
linestyle='-'
```

**Replace with:**
```python
linestyle='none'  # No connecting lines
```

**OR use fmt parameter:**
```python
# Replace entire errorbar call structure:
ax.errorbar(
    results_df['utci'],
    results_df['shade_pref'],
    yerr=[...],
    fmt=marker,  # Just the marker, no line
    color=color,
    markersize=8,  # Slightly larger
    label=label,
    capsize=4,
    capthick=2.0,
    elinewidth=1.5,
    alpha=0.85
)
```

---

### Fix 2: Colorblind-Friendly Palette

**Current (lines 173-177):**
```python
adjustments = [
    (raw_results, 'Raw (unadjusted)', '#e74c3c', 'o'),
    (temp_adjusted_results, 'Temperature adjustment', '#f39c12', 's'),
    ...
]
```

**Replace with:**
```python
# Option A - Seaborn colorblind:
colors = sns.color_palette("colorblind", 4)
markers = ['o', 's', '^', 'D']

adjustments = [
    (raw_results, 'Raw (unadjusted)', colors[0], markers[0]),
    (temp_adjusted_results, 'Temperature adjustment', colors[1], markers[1]),
    (temp_sr_results, 'Temp + shade ratio', colors[2], markers[2]),
    (full_results, 'Temp + shade ratio + DCWP', colors[3], markers[3])
]

# Option B - Explicit colorblind-safe colors:
cb_colors = ['#0173B2', '#DE8F05', '#029E73', '#CC78BC']  # Blue, Orange, Green, Purple
```

---

### Fix 3: Typography

**Add after imports (line 10):**
```python
# Set font family
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']
plt.rcParams['font.size'] = 11  # Slightly larger base size
```

**Change labels (lines 208-211):**
```python
ax.set_xlabel('UTCI Temperature (°C)', fontsize=13, fontweight='normal')
ax.set_ylabel('Shade Preference (%)', fontsize=13, fontweight='normal')
ax.set_title('Effect of Bias Corrections on Shade Preference',
             fontsize=14, fontweight='normal', pad=15)
```

---

### Fix 4: Grid Styling

**Replace line 213:**
```python
# Current:
ax.grid(True, alpha=0.3)

# Option A - Tight grid with major + minor:
ax.minorticks_on()
ax.grid(True, which='major', alpha=0.25, linestyle='-', linewidth=0.8, color='gray')
ax.grid(True, which='minor', alpha=0.12, linestyle=':', linewidth=0.5, color='gray')
ax.set_axisbelow(True)  # Grid behind data

# Option B - Simple improvement:
ax.grid(True, alpha=0.2, linestyle='-', linewidth=0.6, color='#CCCCCC')
ax.set_axisbelow(True)
```

---

### Fix 5: X-Axis Labels

**Add before ax.grid() (around line 213):**
```python
from matplotlib.ticker import MultipleLocator

# Option A - Every 5°C:
ax.set_xticks(np.arange(-20, 35, 5))

# Option B - Major every 5°C, minor every 2.5°C:
ax.xaxis.set_major_locator(MultipleLocator(5))
ax.xaxis.set_minor_locator(MultipleLocator(2.5))

# Option C - Rotate if crowded:
ax.set_xticks(np.arange(-20, 35, 5))
ax.tick_params(axis='x', rotation=0)  # Or rotation=45 if needed
```

---

### Fix 6: Improve Error Bars

**In errorbar call (lines 189-205):**
```python
ax.errorbar(
    results_df['utci'],
    results_df['shade_pref'],
    yerr=[...],
    label=label,
    color=color,
    marker=marker,
    markersize=7,          # Slightly larger markers
    linestyle='none',      # NO LINES
    linewidth=0,           # Ensure no line
    capsize=4,             # Visible caps
    capthick=2.0,          # Thicker caps
    elinewidth=1.8,        # Thicker error bars
    alpha=0.85             # Slight transparency to see overlaps
)
```

---

## My Recommendation: **Option 2 (Moderate Overhaul)**

**Rationale:**
1. Fixes all critical issues (lines, colors, fonts, grid)
2. Doesn't require restructuring the plot
3. Publication-ready result
4. ~20 lines of code changes (manageable)
5. Can commit incrementally for safety

**Implementation order:**
1. ✅ Remove lines (1 line change) → test → commit
2. ✅ Fix colors (colorblind palette, 5 lines) → test → commit
3. ✅ Fix typography (5 lines) → test → commit
4. ✅ Fix grid (5 lines) → test → commit
5. ✅ Fix x-axis labels (3 lines) → test → commit
6. ✅ Improve error bars (modify errorbar call) → test → commit
7. ✅ Update title (1 line) → test → commit

**Total: 7 commits, each tested independently**

---

## Questions for You

Before I start making changes, please confirm:

1. **Which option do you prefer?** (1=minimal, 2=moderate, 3=complete redesign, 4=offset points)

2. **Color palette preference?**
   - Seaborn "colorblind" (auto-generated)
   - Tab10 (matplotlib default colorblind-safe)
   - Explicit colors: Blue/Orange/Green/Purple
   - Keep current colors but verify against colorblind simulator

3. **Font preference?**
   - Sans-serif (Arial/Helvetica) - modern, clean
   - Serif (Times) - traditional, academic
   - Keep current (whatever matplotlib default is)

4. **Title preference?**
   - "Effect of Bias Corrections on Shade Preference"
   - "Shade Preference by UTCI Temperature"
   - Remove title (rely on figure caption)
   - Keep current

5. **Grid style preference?**
   - Tight grid with minor ticks (Option A)
   - Simple subtle grid (Option B)
   - Current style (just lighter)

6. **X-axis ticks?**
   - Every 5°C
   - Every 5°C major, 2.5°C minor
   - Show all bin centers

Let me know your preferences and I'll implement them incrementally with git commits at each step!
