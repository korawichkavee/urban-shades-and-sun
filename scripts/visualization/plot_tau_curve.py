#!/usr/bin/env python3
"""
Plot the DCWP tau curve for presentation.

Shows the exponential distance decay function:
w_DCWP = exp(-distance / tau)

Used to reweight sun-standers based on their distance to nearest shade.
"""

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Set style for presentation
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# Create figure
fig, ax = plt.subplots(figsize=(10, 6))

# Distance range (0 to 100 meters)
distance = np.linspace(0, 100, 1000)

# Tau value used in analysis
tau = 20.0

# Compute weight
weight = np.exp(-distance / tau)

# Plot
ax.plot(distance, weight, linewidth=4, color='#2E86AB')

# Labels and title
ax.set_xlabel('Distance to Nearest Shade (meters)', fontsize=16, fontweight='bold')
ax.set_ylabel('DCWP Weight', fontsize=16, fontweight='bold')
ax.set_title('Distance-Conditioned Walk Preference (DCWP) Weighting',
             fontsize=18, fontweight='bold', pad=20)

# Grid
ax.grid(True, alpha=0.3)

# Set limits
ax.set_xlim(0, 100)
ax.set_ylim(0, 1.05)

plt.tight_layout()

# Save
output_dir = 'outputs/analysis/seasonally_adjusted_plots'
plt.savefig(f'{output_dir}/tau_curve_presentation.png', dpi=300, bbox_inches='tight')
plt.savefig(f'{output_dir}/tau_curve_presentation.pdf', bbox_inches='tight')

print(f"✓ Saved tau curve plots to {output_dir}/")
print(f"  - tau_curve_presentation.png (300 dpi)")
print(f"  - tau_curve_presentation.pdf")
print(f"\nKey parameters:")
print(f"  τ = {tau} m")
