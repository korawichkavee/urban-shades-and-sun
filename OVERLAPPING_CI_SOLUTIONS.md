# Solutions for Overlapping Confidence Intervals

## Problem

In `shade_preference_adjustment_progression.png`, we have 4 different correction levels plotted at the same x-axis positions (UTCI temperatures). When the point estimates are similar, the confidence intervals overlap heavily, making it hard to distinguish between the different correction methods.

---

## Research Findings: Best Practices

From publication-quality plotting guides and matplotlib documentation:

### **Primary Solution: X-Axis Position Dodging (Offsetting)**

**What it is:** Manually shift each series slightly left or right so they don't perfectly overlap at the same x-coordinate.

**Why it works:**
- Maintains continuous x-axis (temperature) interpretation
- Allows all confidence intervals to be visible
- Standard approach in scientific publications for comparing multiple groups
- Similar to `position_dodge()` in ggplot2 or `dodge=True` in seaborn

**Example from search:**
```python
# For 4 series with offsets
offset_width = 0.3  # Total spread
offsets = [-1.5*offset_width, -0.5*offset_width, 0.5*offset_width, 1.5*offset_width]

for i, (results_df, label, color, marker) in enumerate(adjustments):
    x_positions = results_df['utci'] + offsets[i]
    ax.errorbar(x_positions, results_df['shade_pref'], yerr=..., ...)
```

---

## Options for Our Plot

### **Option 1: Small Horizontal Offset (Recommended)**

**Changes:** Add small offsets to x-coordinates for each series

**Pros:**
- Minimal disruption to current plot
- Makes overlaps visible
- Standard scientific practice
- Easy to implement

**Cons:**
- X-values are technically shifted from true temperature
- Need to choose offset width carefully

**Implementation:**
```python
# Define offset width (in °C)
dodge_width = 0.4  # Total spread across all 4 series

# Calculate offsets for 4 series (centered around 0)
n_series = 4
offsets = np.linspace(-dodge_width/2, dodge_width/2, n_series)
# Results in: [-0.2, -0.067, 0.067, 0.2] for 4 series

# In plotting loop:
for i, (results_df, label, color, marker) in enumerate(adjustments):
    x_positions = results_df['utci'].values + offsets[i]
    ax.errorbar(x_positions, results_df['shade_pref'], yerr=[...], ...)
```

**Visual example:**
```
At UTCI = 5°C:
Raw:           o  (at 4.8°C)
Temp adj:       o  (at 4.93°C)
SR-IPW:          o  (at 5.07°C)
Full:             o  (at 5.2°C)
```

---

### **Option 2: Larger Horizontal Offset (More Aggressive)**

**Changes:** Larger offset (0.8-1.0°C spread)

**Pros:**
- Complete visual separation
- Very clear which CI belongs to which series
- Good for dense overlapping regions

**Cons:**
- More distortion of true x-values
- May look cluttered

**Implementation:**
```python
dodge_width = 1.0  # Larger spread
offsets = np.linspace(-dodge_width/2, dodge_width/2, 4)
# Results in: [-0.5, -0.167, 0.167, 0.5]
```

---

### **Option 3: Asymmetric Offset (Highlight Key Comparisons)**

**Changes:** Offset only the corrected estimates, keep raw at true x-position

**Pros:**
- Raw estimate stays at true temperature
- Emphasizes comparisons to raw
- Less distortion

**Cons:**
- Asymmetric (may look odd)
- Still have 3 series overlapping

**Implementation:**
```python
# Raw at 0, others offset right
offsets = [0, 0.3, 0.6, 0.9]
```

---

### **Option 4: Alternating Sides (Staggered)**

**Changes:** Place every other series on opposite sides

**Pros:**
- Visually distinct grouping
- Can use larger offsets without clutter

**Cons:**
- May suggest pairing that doesn't exist
- More complex to interpret

**Implementation:**
```python
# Raw and SR-IPW on left, Temp and Full on right
offsets = [-0.3, 0.3, -0.3, 0.3]
```

---

### **Option 5: Combine Offset with Visual Differences (Best Clarity)**

**Changes:** Small offset PLUS enhanced visual distinction

**Pros:**
- Maximum clarity
- Multiple visual cues (position, color, marker, size)
- Publication-quality

**Implementation:**
```python
# Small offset
dodge_width = 0.5
offsets = np.linspace(-dodge_width/2, dodge_width/2, 4)

# Also vary marker sizes or transparency
marker_sizes = [6, 7, 8, 9]  # Increasing size
alphas = [0.7, 0.8, 0.9, 1.0]  # Increasing opacity

# In plotting loop:
ax.errorbar(
    x_positions,
    results_df['shade_pref'],
    yerr=[...],
    markersize=marker_sizes[i],
    alpha=alphas[i],
    ...
)
```

---

### **Option 6: Use Error Band Instead of Error Bars (Alternative Approach)**

**Changes:** Replace discrete error bars with shaded confidence bands

**Pros:**
- Overlapping regions become immediately visible
- Cleaner for continuous data
- Works well for publications

**Cons:**
- Changes visualization style significantly
- May be harder to read exact values
- Requires more code changes

**Implementation:**
```python
# Instead of errorbar:
ax.plot(results_df['utci'], results_df['shade_pref'],
        marker=marker, color=color, label=label, linestyle='none')
ax.fill_between(results_df['utci'],
                results_df['ci_lower'],
                results_df['ci_upper'],
                color=color, alpha=0.2)
```

**Example from research:** "A simple solution with only two groups is to use semi-transparent areas instead of the error bars, which makes it easy to see the overlap and non-overlap of the two groups."

---

### **Option 7: Subplot Grid (Most Clarity, More Space)**

**Changes:** Create 2x2 subplot grid, one panel per correction level

**Pros:**
- Zero overlap
- Can show more detail per correction
- Easy to compare patterns

**Cons:**
- Takes more space
- Harder to compare absolute values across corrections
- Requires significant code restructuring

**Implementation:**
```python
fig, axes = plt.subplots(2, 2, figsize=(14, 10), sharex=True, sharey=True)
axes = axes.flatten()

for i, (results_df, label, color, marker) in enumerate(adjustments):
    ax = axes[i]
    ax.errorbar(results_df['utci'], results_df['shade_pref'], ...)
    ax.set_title(label)
    # Common formatting
```

---

## Recommendation for Your Plot

**I recommend Option 5: Small offset (0.5°C spread) + enhanced visual differences**

**Rationale:**
1. **Your data:** Temperature bins are 2°C wide, so 0.5°C offset is well within bin width
2. **Minimal distortion:** Offset is small relative to x-axis range (-17 to 33°C)
3. **Maximum clarity:** Combines positional separation with visual cues
4. **Publication-ready:** Standard approach in scientific journals
5. **Easy to explain:** "Points are slightly offset horizontally for visibility; all represent estimates for the labeled temperature bin"

**Specific implementation:**
```python
# After creating adjustments list, before plotting loop:
dodge_width = 0.5  # 0.5°C total spread
offsets = np.linspace(-dodge_width/2, dodge_width/2, len(adjustments))
# Results in: [-0.25, -0.083, 0.083, 0.25] for 4 series

# Modified plotting loop:
for i, (results_df, label, color, marker) in enumerate(adjustments):
    # Convert to percentage (existing code)
    results_df = results_df.copy()
    results_df['shade_pref'] = results_df['shade_pref'] * 100
    results_df['ci_lower'] = results_df['ci_lower'] * 100
    results_df['ci_upper'] = results_df['ci_upper'] * 100

    # Apply x-axis offset
    x_positions = results_df['utci'].values + offsets[i]

    # Plot with offset positions
    ax.errorbar(
        x_positions,  # <-- Changed from results_df['utci']
        results_df['shade_pref'],
        yerr=[
            results_df['shade_pref'] - results_df['ci_lower'],
            results_df['ci_upper'] - results_df['shade_pref']
        ],
        label=label,
        color=color,
        marker=marker,
        markersize=7,
        linewidth=0,
        capsize=4,
        capthick=2.0,
        elinewidth=1.8,
        alpha=0.85,
        linestyle='none'
    )
```

**Figure caption addition:**
Add to figure caption: "Points are horizontally offset by ±0.25°C for visibility; all estimates represent the labeled temperature bin."

---

## Alternative: If Offset Doesn't Work

**If you find the offset approach unsatisfying**, I'd recommend:

**Option 6b: Confidence bands for corrected estimates only**
- Keep raw + final as error bars (most important)
- Show intermediate corrections as shaded bands
- Reduces visual clutter while maintaining key comparisons

**Option 7: Subplot grid**
- Best for detailed examination of each correction
- May be better for supplementary materials than main paper

---

## Code Change Summary

**Minimal change (Option 1):**
- Add 3 lines before plotting loop (define offsets)
- Change 1 line in plotting loop (x_positions)
- Add 1 sentence to figure caption

**Moderate change (Option 5):**
- Add 3 lines before plotting loop
- Change 1 line in plotting loop
- Optional: vary marker sizes/alphas (2 more lines)
- Add 1 sentence to figure caption

**Major change (Option 7):**
- Restructure to subplots (~30 lines)
- Adjust figure size and layout
- Update caption significantly

---

## Questions for You

1. **Which option do you prefer?**
   - Option 1: Small offset only (0.5°C spread)
   - Option 5: Small offset + visual variations (recommended)
   - Option 6: Shaded confidence bands instead of bars
   - Option 7: Subplot grid (2x2)

2. **Offset width preference?** (if using offset)
   - Small: 0.4-0.5°C total spread
   - Medium: 0.8-1.0°C total spread
   - Asymmetric: Raw at 0, others offset

3. **Should we also vary other visual properties?**
   - Marker size (6, 7, 8, 9)
   - Transparency/alpha (0.7, 0.8, 0.9, 1.0)
   - Keep uniform

Let me know and I'll implement it!
