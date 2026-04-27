#!/usr/bin/env python3
# ABOUTME: Generates comprehensive markdown report from seasonal bias prescan results
# ABOUTME: Highlights cities with especially low or high seasonal bias

import pandas as pd
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]
INPUT_FILE = ROOT / 'outputs/analysis/metro_seasonal_bias_prescan.csv'
OUTPUT_FILE = ROOT / 'outputs/analysis/METRO_SEASONAL_BIAS_REPORT.md'

def generate_report():
    """Generate comprehensive markdown report."""

    # Load results
    df = pd.read_csv(INPUT_FILE)

    # Filter successful analyses
    df_success = df[df['status'] == 'SUCCESS'].copy()
    df_success = df_success.sort_values('quality_score', ascending=False)

    # Open output file
    with open(OUTPUT_FILE, 'w') as f:
        # Header
        f.write("# Metro Areas Seasonal Bias Analysis Report\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Total Metro Areas Analyzed:** {len(df)}\n\n")
        f.write(f"**Successful Analyses:** {len(df_success)}\n\n")

        # Executive Summary
        f.write("## Executive Summary\n\n")
        f.write("This report analyzes seasonal bias in street view imagery metadata across ")
        f.write("major US metropolitan areas. Seasonal bias occurs when imagery is ")
        f.write("disproportionately collected during specific seasons, which can affect the ")
        f.write("validity of shade-seeking behavior analysis.\n\n")

        # Classification breakdown
        excellent = df_success[df_success['quality_score'] >= 70]
        good = df_success[(df_success['quality_score'] >= 55) & (df_success['quality_score'] < 70)]
        fair = df_success[(df_success['quality_score'] >= 40) & (df_success['quality_score'] < 55)]
        poor = df_success[df_success['quality_score'] < 40]

        f.write(f"- **✅ EXCELLENT (High Priority):** {len(excellent)} cities - Low bias, ready for analysis\n")
        f.write(f"- **⚠️ GOOD (Medium Priority):** {len(good)} cities - Acceptable bias\n")
        f.write(f"- **⚠️ FAIR (Low Priority):** {len(fair)} cities - Moderate bias, use with caution\n")
        f.write(f"- **❌ POOR (Not Recommended):** {len(poor)} cities - High bias, requires correction\n\n")

        # Quality Scoring
        f.write("## Quality Scoring Methodology\n\n")
        f.write("Cities are scored 0-100 based on:\n\n")
        f.write("1. **Seasonal Balance (40 pts):** Lower penalty for even distribution across seasons\n")
        f.write("2. **Sample Size (30 pts):** Sufficient images with people detected\n")
        f.write("3. **Temporal Coverage (15 pts):** Multiple years of data collection\n")
        f.write("4. **Distribution Variance (15 pts):** Low standard deviation in seasonal percentages\n\n")
        f.write("**Thresholds:**\n")
        f.write("- EXCELLENT: ≥70 points\n")
        f.write("- GOOD: 55-69 points\n")
        f.write("- FAIR: 40-54 points\n")
        f.write("- POOR: <40 points\n\n")

        f.write("---\n\n")

        # Top Cities (Excellent Balance)
        f.write("## ✅ EXCELLENT Cities (Low Bias - High Priority)\n\n")
        f.write("These cities have excellent seasonal balance and are ready for immediate shade-seeking analysis.\n\n")

        if len(excellent) > 0:
            f.write("| Rank | City | Pop (M) | Dominant Season | Dom % | n_people | Quality Score |\n")
            f.write("|------|------|---------|-----------------|-------|----------|---------------|\n")

            for idx, (_, row) in enumerate(excellent.iterrows(), 1):
                f.write(f"| {idx} | **{row['city_name']}** | {row['population_millions']:.2f} | "
                       f"{row['dominant_season_all']} | {row['dominant_pct_all']:.1f}% | "
                       f"{int(row['n_with_people']):,} | **{row['quality_score']:.0f}/100** |\n")

            f.write("\n### Highlights\n\n")

            # Best balance (lowest dominant %)
            best = excellent.iloc[0]
            f.write(f"- **Best Seasonal Balance:** {best['city_name']} ({best['dominant_pct_all']:.1f}% {best['dominant_season_all']})\n")

            # Largest sample
            largest = excellent.loc[excellent['n_with_people'].idxmax()]
            if largest['n_with_people'] > 0:
                f.write(f"- **Largest Sample with People:** {largest['city_name']} ({int(largest['n_with_people']):,} images)\n")

            # Longest temporal coverage
            longest = excellent.loc[excellent['years_covered'].idxmax()]
            f.write(f"- **Longest Temporal Coverage:** {longest['city_name']} ({int(longest['years_covered'])} years)\n")

            f.write("\n")

        f.write("---\n\n")

        # Good Cities
        f.write("## ⚠️ GOOD Cities (Moderate Bias - Medium Priority)\n\n")
        f.write("These cities have acceptable seasonal balance but may benefit from stratification.\n\n")

        if len(good) > 0:
            f.write("| City | Pop (M) | Dominant Season | Dom % | Quality Score |\n")
            f.write("|------|---------|-----------------|-------|---------------|\n")

            for _, row in good.iterrows():
                f.write(f"| {row['city_name']} | {row['population_millions']:.2f} | "
                       f"{row['dominant_season_all']} | {row['dominant_pct_all']:.1f}% | "
                       f"{row['quality_score']:.0f}/100 |\n")
            f.write("\n")

        f.write("---\n\n")

        # Fair Cities
        f.write("## ⚠️ FAIR Cities (Moderate-High Bias - Low Priority)\n\n")
        f.write("These cities have notable seasonal bias. Use with caution and consider bias correction.\n\n")

        if len(fair) > 0:
            f.write("| City | Pop (M) | Dominant Season | Dom % | Quality Score |\n")
            f.write("|------|---------|-----------------|-------|---------------|\n")

            for _, row in fair.iterrows():
                f.write(f"| {row['city_name']} | {row['population_millions']:.2f} | "
                       f"{row['dominant_season_all']} | {row['dominant_pct_all']:.1f}% | "
                       f"{row['quality_score']:.0f}/100 |\n")
            f.write("\n")

        f.write("---\n\n")

        # Poor Cities (High Bias)
        f.write("## ❌ POOR Cities (High Bias - Not Recommended)\n\n")
        f.write("**⚠️ WARNING:** These cities have severe seasonal bias and should not be used without ")
        f.write("bias correction methods such as inverse propensity weighting (IPW).\n\n")

        if len(poor) > 0:
            f.write("| City | Pop (M) | Dominant Season | Dom % | Quality Score | Issue |\n")
            f.write("|------|---------|-----------------|-------|---------------|-------|\n")

            for _, row in poor.iterrows():
                # Identify primary issue
                issue = ""
                if row['dominant_pct_all'] > 80:
                    issue = "Extreme bias"
                elif row['dominant_pct_all'] > 70:
                    issue = "Very high bias"
                elif row['n_with_people'] < 100:
                    issue = "Low sample"
                else:
                    issue = "High bias"

                f.write(f"| **{row['city_name']}** | {row['population_millions']:.2f} | "
                       f"{row['dominant_season_all']} | **{row['dominant_pct_all']:.1f}%** | "
                       f"{row['quality_score']:.0f}/100 | {issue} |\n")

            f.write("\n### Highlights of Concern\n\n")

            # Worst bias
            worst = poor.loc[poor['dominant_pct_all'].idxmax()]
            f.write(f"- **Highest Bias:** {worst['city_name']} - {worst['dominant_pct_all']:.1f}% {worst['dominant_season_all']}\n")

            # Lowest score
            lowest_score = poor.loc[poor['quality_score'].idxmin()]
            f.write(f"- **Lowest Quality Score:** {lowest_score['city_name']} - {lowest_score['quality_score']:.0f}/100\n")

            f.write("\n")

        f.write("---\n\n")

        # Complete Rankings
        f.write("## Complete Rankings (All Cities)\n\n")
        f.write("| Rank | City | Pop (M) | Dominant Season | Dom % | Sample Size | Years | Quality Score | Classification |\n")
        f.write("|------|------|---------|-----------------|-------|-------------|-------|---------------|----------------|\n")

        for idx, (_, row) in enumerate(df_success.iterrows(), 1):
            # Add emoji based on classification
            if row['quality_score'] >= 70:
                emoji = "✅"
            elif row['quality_score'] >= 55:
                emoji = "⚠️"
            elif row['quality_score'] >= 40:
                emoji = "⚠️"
            else:
                emoji = "❌"

            f.write(f"| {idx} | {emoji} {row['city_name']} | {row['population_millions']:.2f} | "
                   f"{row['dominant_season_all']} | {row['dominant_pct_all']:.1f}% | "
                   f"{int(row['n_total']):,} | {int(row['years_covered'])} | "
                   f"{row['quality_score']:.0f}/100 | {row['classification']} |\n")

        f.write("\n")
        f.write("---\n\n")

        # Seasonal Patterns Analysis
        f.write("## Seasonal Patterns Across Cities\n\n")

        # Count dominant seasons
        season_counts = df_success['dominant_season_all'].value_counts()

        f.write("### Most Common Dominant Seasons\n\n")
        for season, count in season_counts.items():
            pct = (count / len(df_success)) * 100
            f.write(f"- **{season}:** {count} cities ({pct:.1f}%)\n")

        f.write("\n")

        # Geographic patterns (if available)
        f.write("### Geographic Notes\n\n")
        f.write("Seasonal bias patterns may reflect:\n")
        f.write("- Timing of street view collection campaigns\n")
        f.write("- Climate and weather patterns affecting data collection\n")
        f.write("- Local Mapillary contributor activity patterns\n\n")

        f.write("---\n\n")

        # Recommendations
        f.write("## Recommendations for Analysis\n\n")
        f.write("### 1. Immediate Priority (EXCELLENT cities)\n\n")
        f.write(f"Begin shade-seeking analysis with the **{len(excellent)} EXCELLENT cities**. ")
        f.write("These have low seasonal bias and require minimal adjustment.\n\n")

        f.write("### 2. Secondary Analysis (GOOD cities)\n\n")
        f.write(f"The **{len(good)} GOOD cities** can be included with minor considerations:\n")
        f.write("- Note dominant season in interpretations\n")
        f.write("- Consider seasonal stratification if sample size permits\n\n")

        f.write("### 3. Cautious Use (FAIR cities)\n\n")
        f.write(f"The **{len(fair)} FAIR cities** should be used carefully:\n")
        f.write("- Apply seasonal IPW (inverse propensity weighting)\n")
        f.write("- Report bias metrics alongside results\n")
        f.write("- Consider sensitivity analyses\n\n")

        f.write("### 4. Avoid or Correct (POOR cities)\n\n")
        f.write(f"The **{len(poor)} POOR cities** have severe bias:\n")
        f.write("- **Do not use** for primary analysis without correction\n")
        f.write("- If essential, apply rigorous bias correction (IPW, stratification)\n")
        f.write("- Clearly document limitations in reporting\n\n")

        f.write("---\n\n")

        # Failed analyses
        df_failed = df[df['status'] != 'SUCCESS']
        if len(df_failed) > 0:
            f.write("## Failed Analyses\n\n")
            f.write(f"{len(df_failed)} cities could not be analyzed:\n\n")
            for _, row in df_failed.iterrows():
                f.write(f"- **{row['city_name']}:** {row['status']}\n")
            f.write("\n---\n\n")

        # Footer
        f.write("## Appendix: Methodology\n\n")
        f.write("### Season Definitions\n\n")
        f.write("- **Winter:** January - March\n")
        f.write("- **Spring:** April - June\n")
        f.write("- **Summer:** July - September\n")
        f.write("- **Fall:** October - December\n\n")

        f.write("### Data Source\n\n")
        f.write("Street view imagery metadata from Mapillary, processed through the ")
        f.write("sunny day SVI analysis pipeline.\n\n")

        f.write("### Contact\n\n")
        f.write("For questions about this analysis, refer to:\n")
        f.write("- Analysis script: `scripts/analysis/analyze_metro_seasonal_bias_prescan.py`\n")
        f.write("- Raw data: `outputs/analysis/metro_seasonal_bias_prescan.csv`\n\n")

        f.write("---\n\n")
        f.write("*Report generated automatically from seasonal bias prescan results*\n")

    print(f"✓ Report generated: {OUTPUT_FILE}")
    print(f"  - {len(excellent)} EXCELLENT cities")
    print(f"  - {len(good)} GOOD cities")
    print(f"  - {len(fair)} FAIR cities")
    print(f"  - {len(poor)} POOR cities")

if __name__ == '__main__':
    generate_report()
