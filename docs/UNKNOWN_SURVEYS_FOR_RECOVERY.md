# Unknown Surveys Requiring Additional Documentation

## Summary

9 surveys (483,225 trips) were included in raw flexible merge but excluded from standardization.
XML metadata files not found in standard location. Need additional documentation to determine recoverability.

## Unknown Surveys List

### Large Surveys (>50k trips - High Priority)

#### 1. california-2001 (175,860 trips)
**Status in raw data:** ✓ Included
**Fields available:**
- household_id: 100%
- time: 100%
- county: 100% (SAN DIEGO and others)
- mode: 76.3% (23.7% missing)
- zip: 0% (redacted)
- day_of_week: 100%

**Issue:** High missing mode rate (24%), ZIP redacted
**Documentation found:**
- changelog.txt (shows column redactions including tract, xcord, ycord)
- readme.txt (generic TSDC info)

**Recoverability:** MAYBE - Has time + county, but 24% missing mode may be too high

---

#### 2. chicago-1990 (162,755 trips)
**Status in raw data:** ✓ Included
**Documentation found:**
- changelog.txt
- readme.txt

**Recoverability:** UNKNOWN - Need to check actual data columns

---

#### 3. washington-dc-1988 (47,314 trips)
**Status in raw data:** ✓ Included
**Documentation found:**
- changelog.txt
- readme.txt

**Recoverability:** UNKNOWN - Need to check actual data columns

---

#### 4. washington-dc-1994 (42,426 trips)
**Status in raw data:** ✓ Included
**Documentation found:**
- changelog.txt
- readme.txt

**Recoverability:** UNKNOWN - Need to check actual data columns

---

### Smaller Surveys (<25k trips - Lower Priority)

#### 5. minneapolis-st-paul-1982 (21,944 trips)
**Status in raw data:** ✓ Included
**Documentation found:**
- changelog.txt
- readme.txt

**Recoverability:** UNKNOWN - Need to check actual data columns

---

#### 6. ohio-2001 (22,153 trips)
**Status in raw data:** ✓ Included
**Documentation found:**
- changelog.txt
- readme.txt

**Recoverability:** UNKNOWN - Need to check actual data columns

---

#### 7. knoxville-2001 (3,727 trips)
**Status in raw data:** ✓ Included
**Documentation found:**
- changelog.txt
- readme.txt

**Recoverability:** UNKNOWN - Need to check actual data columns

---

#### 8. san-diego-1995 (3,810 trips)
**Status in raw data:** ✓ Included
**Documentation found:**
- changelog.txt
- readme.txt

**Recoverability:** UNKNOWN - Need to check actual data columns

---

#### 9. champaign-urbana-savoy-2002 (3,236 trips)
**Status in raw data:** ✓ Included
**Documentation found:**
- changelog.txt
- readme.txt
- **XML metadata:** `mtsa-champaign-2002-xml-metadata.xml` ✓

**Recoverability:** CHECK XML - Has metadata file with different name pattern

---

## Next Steps

1. **Check champaign XML:** File exists at `mtsa-champaign-2002-xml-metadata.xml`

2. **Read changelogs:** All 9 surveys have changelog.txt files that may contain field mappings

3. **Examine raw data columns:** For each survey, check what columns actually exist in raw data:
   ```python
   df_raw[df_raw['survey'] == 'chicago-1990'].columns
   ```

4. **Check for alternative XML patterns:** Look for variations like:
   - `mtsa-chicago-90-xml-metadata.xml`
   - `chicago-1990-metadata.xml`
   - Files in extracted/*/documentation/ directories

## Commands to Run

```bash
# Check champaign XML
python scripts/travel_surveys/analyze_excluded_surveys.py --survey champaign-urbana-savoy-2002

# Read all changelogs
for survey in california-2001 chicago-1990 washington-dc-1988 washington-dc-1994 \
              minneapolis-st-paul-1982 ohio-2001 knoxville-2001 san-diego-1995 \
              champaign-urbana-savoy-2002; do
    echo "=== $survey ==="
    cat data/transit_surveys/metro/extracted/$survey/documentation/changelog.txt
done

# Check raw data columns for each
python3 << 'EOF'
import pandas as pd
df = pd.read_csv('data/transit_surveys/processed/metro_surveys_raw_merged_flexible.csv', low_memory=False)
for survey in ['california-2001', 'chicago-1990', 'washington-dc-1988',
               'washington-dc-1994', 'minneapolis-st-paul-1982', 'ohio-2001',
               'knoxville-2001', 'san-diego-1995', 'champaign-urbana-savoy-2002']:
    subset = df[df['survey'] == survey]
    print(f"\n{survey}: {len(subset):,} trips")
    for col in ['household_id', 'mode', 'time', 'zip', 'county']:
        pct = 100 * subset[col].notna().sum() / len(subset)
        print(f"  {col}: {pct:.1f}%")
EOF
```

## Priority Order for Recovery

1. **HIGH:** champaign-urbana-savoy-2002 - Has XML metadata file
2. **HIGH:** chicago-1990 - 163k trips, major metro
3. **HIGH:** california-2001 - 176k trips (may be too much missing mode)
4. **MEDIUM:** washington-dc-1988 + washington-dc-1994 - 90k combined
5. **LOW:** Others - Small sample sizes (<25k each)

Total recoverable if all work: 483,225 additional trips
