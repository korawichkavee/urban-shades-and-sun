# ABOUTME: Analyzes temperature adjustments in Bangkok walkable data
# ABOUTME: Compares original vs adjusted dry bulb and wet bulb temperatures with error statistics

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from metpy.calc import wet_bulb_temperature
from metpy.units import units
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from statsmodels.nonparametric.smoothers_lowess import lowess

# Read the data
df = pd.read_csv('Bangkok_walkable_with_local_temp.csv')

# Filter out rows with missing values for the relevant columns
df_clean = df.dropna(subset=['dbulb', 'local_temp_C', 'wbulb', 'rhum'])

print(f"Total rows: {len(df)}")
print(f"Rows with complete data: {len(df_clean)}")
print()

# =============================================================================
# Part 1: Dry Bulb Temperature Analysis
# =============================================================================

print("="*80)
print("DRY BULB TEMPERATURE: Original vs Adjusted (local_temp_C)")
print("="*80)

original_dbulb = df_clean['dbulb'].values
adjusted_dbulb = df_clean['local_temp_C'].values

# Calculate error statistics
mae_dbulb = mean_absolute_error(original_dbulb, adjusted_dbulb)
rmse_dbulb = np.sqrt(mean_squared_error(original_dbulb, adjusted_dbulb))
r2_dbulb = r2_score(original_dbulb, adjusted_dbulb)
bias_dbulb = np.mean(adjusted_dbulb - original_dbulb)

print(f"Mean Absolute Error (MAE):     {mae_dbulb:.4f} °C")
print(f"Root Mean Square Error (RMSE): {rmse_dbulb:.4f} °C")
print(f"R² Score:                      {r2_dbulb:.4f}")
print(f"Mean Bias (adjusted - original): {bias_dbulb:.4f} °C")
print(f"Min original: {original_dbulb.min():.2f} °C, Max: {original_dbulb.max():.2f} °C")
print(f"Min adjusted: {adjusted_dbulb.min():.2f} °C, Max: {adjusted_dbulb.max():.2f} °C")
print()

# Create plot
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Scatter plot
axes[0].scatter(original_dbulb, adjusted_dbulb, alpha=0.5, s=10)
axes[0].plot([original_dbulb.min(), original_dbulb.max()],
             [original_dbulb.min(), original_dbulb.max()],
             'r--', label='1:1 line')
axes[0].set_xlabel('Original Dry Bulb Temperature (°C)', fontsize=12)
axes[0].set_ylabel('Adjusted Dry Bulb Temperature (°C)', fontsize=12)
axes[0].set_title('Original vs Adjusted Dry Bulb Temperature', fontsize=14, fontweight='bold')
axes[0].legend()
axes[0].grid(True, alpha=0.3)
axes[0].text(0.05, 0.95, f'R² = {r2_dbulb:.4f}\nRMSE = {rmse_dbulb:.4f} °C\nBias = {bias_dbulb:.4f} °C',
             transform=axes[0].transAxes, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

# Residual plot
residuals_dbulb = adjusted_dbulb - original_dbulb
axes[1].scatter(original_dbulb, residuals_dbulb, alpha=0.3, s=10, label='Residuals')
axes[1].axhline(y=0, color='r', linestyle='--', alpha=0.5, label='Zero line')

# Add LOESS smoothing
loess_dbulb = lowess(residuals_dbulb, original_dbulb, frac=0.2)
axes[1].plot(loess_dbulb[:, 0], loess_dbulb[:, 1], 'b-', linewidth=2, label='LOESS trend')

axes[1].set_xlabel('Original Dry Bulb Temperature (°C)', fontsize=12)
axes[1].set_ylabel('Residuals (Adjusted - Original) (°C)', fontsize=12)
axes[1].set_title('Residual Plot: Dry Bulb Temperature', fontsize=14, fontweight='bold')
axes[1].legend()
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('plots/drybulb_comparison.png', dpi=300, bbox_inches='tight')
print("Saved plot: plots/drybulb_comparison.png")
print()

# =============================================================================
# Part 2: Wet Bulb Temperature Analysis
# =============================================================================

print("="*80)
print("WET BULB TEMPERATURE: Computing adjusted values using adjusted dry bulb")
print("="*80)

# Compute adjusted wet bulb temperature using metpy
# Need: temperature, dewpoint (or RH), and pressure
# We have temperature (adjusted), RH, so we need to calculate dewpoint or use a standard pressure

# Using standard atmospheric pressure (1013.25 hPa)
pressure = 1013.25 * units.hPa

# Convert temperatures to units
temp_adjusted = adjusted_dbulb * units.degC
temp_original = original_dbulb * units.degC

# For wet bulb calculation, we need dewpoint. We can calculate it from RH and temperature
# Using original temperature and RH to get dewpoint, then use that dewpoint with adjusted temperature
# Actually, that's not quite right. Let me think about this differently.

# The proper way: use adjusted temperature with the same relative humidity
# MetPy's wet_bulb_temperature needs temperature, dewpoint, and pressure
# I'll calculate dewpoint from the original temp and RH, then recalculate wet bulb with adjusted temp

from metpy.calc import dewpoint_from_relative_humidity

# Calculate dewpoint from original temperature and RH (dewpoint should remain relatively stable)
dewpoint = dewpoint_from_relative_humidity(temp_original, df_clean['rhum'].values * units.percent)

# Calculate adjusted wet bulb using adjusted temperature and original dewpoint
adjusted_wbulb_values = []
for i in range(len(df_clean)):
    try:
        wb = wet_bulb_temperature(pressure, temp_adjusted[i], dewpoint[i])
        adjusted_wbulb_values.append(wb.magnitude)
    except Exception as e:
        adjusted_wbulb_values.append(np.nan)
        print(f"Warning: Could not calculate wet bulb for row {i}: {e}")

adjusted_wbulb = np.array(adjusted_wbulb_values)

# Filter out any NaN values that may have been introduced
valid_mask = ~np.isnan(adjusted_wbulb)
original_wbulb = df_clean['wbulb'].values[valid_mask]
adjusted_wbulb = adjusted_wbulb[valid_mask]

print(f"Successfully calculated adjusted wet bulb for {len(adjusted_wbulb)} rows")
print()

# Calculate error statistics for wet bulb
mae_wbulb = mean_absolute_error(original_wbulb, adjusted_wbulb)
rmse_wbulb = np.sqrt(mean_squared_error(original_wbulb, adjusted_wbulb))
r2_wbulb = r2_score(original_wbulb, adjusted_wbulb)
bias_wbulb = np.mean(adjusted_wbulb - original_wbulb)

print("="*80)
print("WET BULB TEMPERATURE: Original vs Adjusted")
print("="*80)
print(f"Mean Absolute Error (MAE):     {mae_wbulb:.4f} °C")
print(f"Root Mean Square Error (RMSE): {rmse_wbulb:.4f} °C")
print(f"R² Score:                      {r2_wbulb:.4f}")
print(f"Mean Bias (adjusted - original): {bias_wbulb:.4f} °C")
print(f"Min original: {original_wbulb.min():.2f} °C, Max: {original_wbulb.max():.2f} °C")
print(f"Min adjusted: {adjusted_wbulb.min():.2f} °C, Max: {adjusted_wbulb.max():.2f} °C")
print()

# Create plot
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Scatter plot
axes[0].scatter(original_wbulb, adjusted_wbulb, alpha=0.5, s=10)
axes[0].plot([original_wbulb.min(), original_wbulb.max()],
             [original_wbulb.min(), original_wbulb.max()],
             'r--', label='1:1 line')
axes[0].set_xlabel('Original Wet Bulb Temperature (°C)', fontsize=12)
axes[0].set_ylabel('Adjusted Wet Bulb Temperature (°C)', fontsize=12)
axes[0].set_title('Original vs Adjusted Wet Bulb Temperature', fontsize=14, fontweight='bold')
axes[0].legend()
axes[0].grid(True, alpha=0.3)
axes[0].text(0.05, 0.95, f'R² = {r2_wbulb:.4f}\nRMSE = {rmse_wbulb:.4f} °C\nBias = {bias_wbulb:.4f} °C',
             transform=axes[0].transAxes, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

# Residual plot
residuals_wbulb = adjusted_wbulb - original_wbulb
axes[1].scatter(original_wbulb, residuals_wbulb, alpha=0.3, s=10, label='Residuals')
axes[1].axhline(y=0, color='r', linestyle='--', alpha=0.5, label='Zero line')

# Add LOESS smoothing
loess_wbulb = lowess(residuals_wbulb, original_wbulb, frac=0.2)
axes[1].plot(loess_wbulb[:, 0], loess_wbulb[:, 1], 'b-', linewidth=2, label='LOESS trend')

axes[1].set_xlabel('Original Wet Bulb Temperature (°C)', fontsize=12)
axes[1].set_ylabel('Residuals (Adjusted - Original) (°C)', fontsize=12)
axes[1].set_title('Residual Plot: Wet Bulb Temperature', fontsize=14, fontweight='bold')
axes[1].legend()
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('plots/wetbulb_comparison.png', dpi=300, bbox_inches='tight')
print("Saved plot: plots/wetbulb_comparison.png")
print()

print("="*80)
print("ANALYSIS COMPLETE")
print("="*80)
