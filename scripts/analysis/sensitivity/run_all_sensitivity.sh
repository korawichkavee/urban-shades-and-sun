#!/bin/bash
#
# Run all sensitivity analyses for reviewer response
#
# This script runs all three parameter sensitivity analyses in sequence:
# 1. Winsorization cap (c_percentile)
# 2. Detour decay parameter (tau)
# 3. Walk rate clipping
#
# Then generates visualization for tau sensitivity
#
# Author: Reviewer response
# Date: 2026-09-28
#

set -e  # Exit on error

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../../.." && pwd )"

echo "=========================================================================="
echo "RUNNING ALL SENSITIVITY ANALYSES"
echo "=========================================================================="
echo ""
echo "Project root: $PROJECT_ROOT"
echo "Python: $(which python3)"
echo ""

# Activate virtual environment if it exists
if [ -d "$PROJECT_ROOT/.venv" ]; then
    echo "Activating virtual environment..."
    source "$PROJECT_ROOT/.venv/bin/activate"
    echo ""
fi

# Analysis 1: Winsorization
echo "=========================================================================="
echo "ANALYSIS 1: WINSORIZATION CAP SENSITIVITY"
echo "=========================================================================="
echo ""
python3 "$SCRIPT_DIR/sensitivity_winsorization.py"
echo ""
echo "✓ Winsorization analysis complete"
echo ""

# Analysis 2: Tau
echo "=========================================================================="
echo "ANALYSIS 2: DETOUR DECAY PARAMETER (TAU) SENSITIVITY"
echo "=========================================================================="
echo ""
python3 "$SCRIPT_DIR/sensitivity_tau.py"
echo ""
echo "✓ Tau analysis complete"
echo ""

# Analysis 3: Walk rate clipping
echo "=========================================================================="
echo "ANALYSIS 3: WALK RATE CLIPPING JUSTIFICATION"
echo "=========================================================================="
echo ""
python3 "$SCRIPT_DIR/sensitivity_walk_rate_clip.py"
echo ""
echo "✓ Walk rate clipping analysis complete"
echo ""

# Generate visualizations
echo "=========================================================================="
echo "GENERATING VISUALIZATIONS"
echo "=========================================================================="
echo ""
python3 "$PROJECT_ROOT/scripts/visualization/plot_tau_ablation_sensitivity.py"
echo ""
echo "✓ Visualizations complete"
echo ""

# Summary
echo "=========================================================================="
echo "ALL SENSITIVITY ANALYSES COMPLETE"
echo "=========================================================================="
echo ""
echo "Output files created:"
echo ""
echo "Analysis results:"
echo "  - outputs/analysis/sensitivity/winsorization_sensitivity_detailed.csv"
echo "  - outputs/analysis/sensitivity/supplementary_table_s1_winsorization.csv"
echo "  - outputs/analysis/sensitivity/supplementary_table_s1_winsorization.tex"
echo ""
echo "  - outputs/analysis/sensitivity/tau_sensitivity_detailed.csv"
echo "  - outputs/analysis/sensitivity/supplementary_table_s2_tau.csv"
echo "  - outputs/analysis/sensitivity/supplementary_table_s2_tau.tex"
echo "  - outputs/analysis/sensitivity/tau_sensitivity_for_plotting.csv"
echo ""
echo "  - outputs/analysis/sensitivity/walk_rate_clipping_stats.csv"
echo "  - outputs/analysis/sensitivity/walk_rate_clipping_response.txt"
echo ""
echo "Figures:"
echo "  - outputs/plots/sensitivity/supplementary_figure_s1_tau_sensitivity.pdf"
echo "  - outputs/plots/sensitivity/supplementary_figure_s1_tau_sensitivity.png"
echo "  - outputs/plots/sensitivity/supplementary_figure_s1b_tau_deltas.pdf"
echo "  - outputs/plots/sensitivity/supplementary_figure_s1b_tau_deltas.png"
echo ""
echo "=========================================================================="
echo "Next steps:"
echo "  1. Review output files"
echo "  2. Incorporate results into paper revisions"
echo "  3. Draft response letter to reviewers"
echo "=========================================================================="
