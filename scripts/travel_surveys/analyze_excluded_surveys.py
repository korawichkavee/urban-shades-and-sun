# ABOUTME: Analyzes XML metadata for surveys excluded from standardization.
# ABOUTME: Determines if any excluded surveys can be recovered for temperature analysis.

import pandas as pd
from pathlib import Path
import xml.etree.ElementTree as ET
import re

def parse_xml_metadata(xml_path):
    """Parse XML metadata to extract variable information."""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        variables = {}

        # Try multiple XML formats
        # Format 1: <variable name="..." desc="...">
        for var in root.findall('.//variable'):
            var_name = var.get('name', var.get('id', ''))
            desc = var.get('desc', var.get('label', ''))

            if var_name:
                variables[var_name.lower()] = {
                    'name': var_name,
                    'label': desc,
                    'question': ''
                }

        # Format 2: DDI format - <var> elements
        if len(variables) == 0:
            for var in root.findall('.//{*}var'):
                var_id = var.get('ID', var.get('id', var.get('name', '')))
                var_name = var.get('name', var_id)

                # Get label
                label_elem = var.find('.//{*}labl')
                label = label_elem.text if label_elem is not None else ''

                # Get question text
                qstn_elem = var.find('.//{*}qstn/{*}qstnLit')
                qstn = qstn_elem.text if qstn_elem is not None else ''

                if var_name:
                    variables[var_name.lower()] = {
                        'name': var_name,
                        'label': label,
                        'question': qstn
                    }

        return variables
    except Exception as e:
        return {'error': str(e)}


def check_for_required_fields(variables):
    """Check if survey has required fields for standardization."""

    # Time patterns
    time_patterns = [
        'time', 'strttime', 'endtime', 'deptime', 'arrtime', 'begtime',
        'hour', 'minute', 'depart', 'arrive', 'gend', 'gbeg'
    ]

    # Location patterns
    location_patterns = [
        'zip', 'county', 'fips', 'cnty', 'geoid', 'tract', 'block',
        'geozip', 'homecnty', 'ozip', 'dzip'
    ]

    # Mode patterns
    mode_patterns = [
        'mode', 'tran', 'pubtrans', 'trppub', 'wk_mode', 'vehtype'
    ]

    # Household ID patterns
    hhid_patterns = [
        'sampno', 'hhid', 'newid', 'household', 'diaryid', 'hh_id'
    ]

    findings = {
        'time_vars': [],
        'location_vars': [],
        'mode_vars': [],
        'hhid_vars': []
    }

    for var_name, var_info in variables.items():
        var_str = f"{var_name} {var_info['label']} {var_info['question']}".lower()

        if any(p in var_str for p in time_patterns):
            findings['time_vars'].append(var_info['name'])
        if any(p in var_str for p in location_patterns):
            findings['location_vars'].append(var_info['name'])
        if any(p in var_str for p in mode_patterns):
            findings['mode_vars'].append(var_info['name'])
        if any(p in var_str for p in hhid_patterns):
            findings['hhid_vars'].append(var_info['name'])

    return findings


def main():
    # Load raw and standardized surveys
    df_raw = pd.read_csv('data/transit_surveys/processed/metro_surveys_raw_merged_flexible.csv',
                         low_memory=False)
    df_std = pd.read_csv('data/transit_surveys/processed/metro_surveys_standardized_flexible.csv',
                         low_memory=False)

    raw_surveys = set(df_raw['survey'].unique())
    std_surveys = set(df_std['survey'].unique())
    excluded = raw_surveys - std_surveys

    print("="*80)
    print(f"ANALYZING {len(excluded)} EXCLUDED SURVEYS")
    print("="*80)

    xml_dir = Path('data/transit_surveys/metro/xml_metadata')

    results = []

    for survey in sorted(excluded):
        # Get trip count
        trip_count = len(df_raw[df_raw['survey'] == survey])

        # Find XML file
        xml_patterns = [
            f"mtsa-{survey}-xml-metadata.xml",
            f"{survey}-xml-metadata.xml"
        ]

        xml_file = None
        for pattern in xml_patterns:
            candidate = xml_dir / pattern
            if candidate.exists():
                xml_file = candidate
                break

        result = {
            'survey': survey,
            'trips': trip_count,
            'xml_found': xml_file is not None,
            'has_time': False,
            'has_location': False,
            'has_mode': False,
            'has_hhid': False,
            'time_vars': [],
            'location_vars': [],
            'mode_vars': [],
            'hhid_vars': [],
            'recoverable': 'Unknown'
        }

        if xml_file:
            variables = parse_xml_metadata(xml_file)
            if 'error' not in variables:
                findings = check_for_required_fields(variables)

                result['has_time'] = len(findings['time_vars']) > 0
                result['has_location'] = len(findings['location_vars']) > 0
                result['has_mode'] = len(findings['mode_vars']) > 0
                result['has_hhid'] = len(findings['hhid_vars']) > 0

                result['time_vars'] = findings['time_vars'][:5]  # First 5
                result['location_vars'] = findings['location_vars'][:5]
                result['mode_vars'] = findings['mode_vars'][:5]
                result['hhid_vars'] = findings['hhid_vars'][:5]

                # Determine recoverability
                if all([result['has_time'], result['has_location'],
                       result['has_mode'], result['has_hhid']]):
                    result['recoverable'] = 'YES - All fields present'
                elif result['has_time'] and result['has_location'] and result['has_mode']:
                    result['recoverable'] = 'MAYBE - Missing household ID'
                elif result['has_time'] and result['has_location']:
                    result['recoverable'] = 'MAYBE - Missing mode'
                else:
                    missing = []
                    if not result['has_time']: missing.append('time')
                    if not result['has_location']: missing.append('location')
                    if not result['has_mode']: missing.append('mode')
                    result['recoverable'] = f"NO - Missing {', '.join(missing)}"

        results.append(result)

    # Print detailed results
    print("\nDETAILED ANALYSIS:")
    print("="*80)

    for r in results:
        print(f"\n{r['survey'].upper()} ({r['trips']:,} trips)")
        print("-"*80)
        print(f"XML metadata: {'Found' if r['xml_found'] else 'NOT FOUND'}")
        print(f"Recoverable: {r['recoverable']}")

        if r['xml_found']:
            print(f"\nField availability:")
            print(f"  Time:     {'✓' if r['has_time'] else '✗'} - {r['time_vars'][:3]}")
            print(f"  Location: {'✓' if r['has_location'] else '✗'} - {r['location_vars'][:3]}")
            print(f"  Mode:     {'✓' if r['has_mode'] else '✗'} - {r['mode_vars'][:3]}")
            print(f"  HH ID:    {'✓' if r['has_hhid'] else '✗'} - {r['hhid_vars'][:3]}")

    # Summary table
    df_results = pd.DataFrame(results)

    print("\n" + "="*80)
    print("SUMMARY TABLE")
    print("="*80)

    summary = df_results.groupby('recoverable').agg({
        'trips': ['count', 'sum']
    }).reset_index()
    summary.columns = ['Status', 'N_Surveys', 'Total_Trips']
    summary = summary.sort_values('Total_Trips', ascending=False)

    print(summary.to_string(index=False))

    print("\n" + "="*80)
    print("POTENTIALLY RECOVERABLE SURVEYS")
    print("="*80)

    recoverable = df_results[df_results['recoverable'].str.contains('YES|MAYBE')]
    recoverable = recoverable.sort_values('trips', ascending=False)

    if len(recoverable) > 0:
        print(f"\nFound {len(recoverable)} potentially recoverable surveys")
        print(f"Total trips: {recoverable['trips'].sum():,}")
        print("\nTop candidates:")
        for _, row in recoverable.head(10).iterrows():
            print(f"  {row['survey']:40s} {row['trips']:>8,} trips - {row['recoverable']}")
    else:
        print("\nNo recoverable surveys found.")

    # Save detailed results
    output_path = Path('data/transit_surveys/processed/excluded_survey_analysis.csv')
    df_results.to_csv(output_path, index=False)
    print(f"\nDetailed results saved to: {output_path}")


if __name__ == '__main__':
    main()
