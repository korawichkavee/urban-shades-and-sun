# ABOUTME: Maps city names from hot_cities.txt to worldcities.csv IDs
# ABOUTME: and prepares the list for downloading street view images

import pandas as pd

# Load worldcities database
wc = pd.read_csv('/home/kieran/Documents/Datasets/Global streetscapes/global-streetscapes/code/raw_download/data/worldcities.csv')

# Load hot cities list
hot_cities = []
with open('/home/kieran/Documents/Python/sunny_day_SVI/hot_cities.txt', 'r') as f:
    for line in f:
        line = line.strip()
        if line:
            parts = line.split('\t')
            if len(parts) >= 2:
                city_name = parts[0].strip()
                country = parts[1].strip()
                hot_cities.append({'city': city_name, 'country': country})

print(f"Found {len(hot_cities)} cities in hot_cities.txt")
print("\nMatching cities to worldcities database:")
print("-" * 80)

matched_cities = []
unmatched_cities = []

for hot_city in hot_cities:
    city_name = hot_city['city']
    country_name = hot_city['country']

    # Try to match by city_ascii and country
    matches = wc[(wc['city_ascii'].str.lower() == city_name.lower()) &
                 (wc['country'].str.lower() == country_name.lower())]

    if len(matches) > 0:
        match = matches.iloc[0]
        matched_cities.append({
            'city': city_name,
            'country': country_name,
            'id': match['id'],
            'city_ascii': match['city_ascii'],
            'lat': match['lat'],
            'lng': match['lng'],
            'population': match['population']
        })
        print(f"✓ {city_name:20s} {country_name:20s} -> ID: {match['id']} (pop: {match['population']:,.0f})")
    else:
        unmatched_cities.append({'city': city_name, 'country': country_name})
        print(f"✗ {city_name:20s} {country_name:20s} -> NOT FOUND")

print("\n" + "=" * 80)
print(f"Matched: {len(matched_cities)}/{len(hot_cities)} cities")
print(f"Unmatched: {len(unmatched_cities)} cities")

if unmatched_cities:
    print("\nUnmatched cities:")
    for city in unmatched_cities:
        print(f"  - {city['city']}, {city['country']}")
        # Try to find alternatives
        alternatives = wc[wc['city_ascii'].str.lower().str.contains(city['city'].lower(), na=False)][:3]
        if len(alternatives) > 0:
            print(f"    Possible matches:")
            for _, alt in alternatives.iterrows():
                print(f"      {alt['city_ascii']}, {alt['country']} (ID: {alt['id']})")

# Save matched city IDs
if matched_cities:
    df_matched = pd.DataFrame(matched_cities)
    df_matched.to_csv('/home/kieran/Documents/Python/sunny_day_SVI/hot_cities_matched.csv', index=False)
    print(f"\nSaved matched cities to: hot_cities_matched.csv")

    # Also save just the IDs for easy use
    city_ids = [str(c['id']) for c in matched_cities]
    with open('/home/kieran/Documents/Python/sunny_day_SVI/hot_cities_ids.txt', 'w') as f:
        f.write('\n'.join(city_ids))
    print(f"Saved city IDs to: hot_cities_ids.txt")
