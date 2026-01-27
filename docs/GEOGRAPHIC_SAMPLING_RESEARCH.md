# Geographic Sampling Research: Best Practices

## Research Objective
Determine recommended procedures for randomly sampling points within geographic boundaries (ZIP codes and counties) for travel survey thermal comfort analysis.

## Key Findings

### 1. Recommended Method: GeoPandas `sample_points()`

**Best Practice**: Use GeoPandas built-in `sample_points()` method rather than implementing custom rejection sampling.

**Rationale**:
- Official GeoPandas API specifically designed for this purpose
- Implements efficient uniform random sampling using numpy
- Handles edge cases (multipolygons, holes, islands) automatically
- Supports reproducible seeding via `rng` parameter
- Well-tested and maintained by the GIS community

**API**:
```python
import geopandas as gpd

# Load shapefile
gdf = gpd.read_file('counties.shp')

# Sample 1 random point from each polygon, reproducible with seed
sampled_points = gdf.sample_points(size=1, method='uniform', rng=42)
```

### 2. Sampling Methods Comparison

#### Triangulation-Based Sampling
- **Performance**: ~20x faster than rejection sampling for complex polygons
- **Algorithm**: Triangulate polygon → sample triangle by area → sample point in triangle
- **Pros**: Excellent for complex geometries, guaranteed uniform distribution
- **Cons**: Requires triangulation preprocessing, more implementation complexity

#### Rejection Sampling
- **Performance**: Simple but inefficient for complex shapes (high rejection rate)
- **Algorithm**: Sample from bounding box → reject if outside polygon
- **Pros**: Simple to implement, fast for simple shapes
- **Cons**: Inefficient for irregular polygons, wasted computation

#### GeoPandas Method
- **Performance**: Uses numpy.random.uniform (likely optimized internally)
- **Algorithm**: Not explicitly documented, but likely triangulation-based
- **Pros**: Best of both worlds - efficient + simple API
- **Cons**: None for our use case

### 3. Travel Survey Spatial Sampling Literature

From academic research on geographic sampling in surveys:

**Random Geographic Cluster Sampling (RGCS)**:
- Used in development surveys when household maps unavailable
- Generate random coordinates within districts/regions
- Survey all eligible respondents at that location
- Successfully applied in Malawi surveys with nationally representative results

**Key Principles**:
1. **Reproducibility**: Always use fixed seed for scientific reproducibility
2. **Stratification**: Sample within each geographic unit independently
3. **Uniform Distribution**: Ensure no location bias within boundaries
4. **Documentation**: Record sampling method and seed used

### 4. Implementation Recommendations

For our travel survey analysis:

1. **Use GeoPandas `sample_points()`** with `rng=42` for reproducibility
2. **Sample 1 point per trip** from the available geographic unit (ZIP or county)
3. **Priority order**: ZIP > County > State (use finest resolution available)
4. **Seed variation**: Use household ID + geographic unit to vary points while maintaining reproducibility
5. **Caching**: Cache sampled points by geographic unit to avoid recomputation

### 5. Validation Approaches

Best practices for validating spatial sampling:

1. **Visual inspection**: Plot sampled points on map to check distribution
2. **Coverage test**: Ensure points spread across entire polygon, not clustered
3. **Edge cases**: Verify handling of multipolygons, islands, holes
4. **Statistical test**: Check uniformity with spatial statistics (e.g., Ripley's K)

## Implementation Plan

### Geographic Sampler Design

```python
class GeographicSampler:
    def __init__(self, zip_shapefile, county_shapefile, state_centroids, seed=42):
        self.zip_gdf = gpd.read_file(zip_shapefile)
        self.county_gdf = gpd.read_file(county_shapefile)
        self.state_centroids = state_centroids
        self.base_seed = seed
        self.cache = {}  # Cache sampled points

    def get_location(self, zip_code=None, county_fips=None, state=None,
                     variation_key=''):
        # Priority: ZIP > County > State
        # Use variation_key (e.g., household_id) to get different points
        # within same geographic unit while maintaining reproducibility

        # Generate unique seed for this combination
        seed = self.base_seed + hash(variation_key + str(zip_code or county_fips or state))

        if zip_code:
            return self._sample_from_zip(zip_code, seed)
        elif county_fips:
            return self._sample_from_county(county_fips, seed)
        else:
            return self._get_state_centroid(state)

    def _sample_from_zip(self, zip_code, seed):
        # Use GeoPandas sample_points with unique seed
        polygon = self.zip_gdf[self.zip_gdf['ZCTA5CE20'] == zip_code]
        if len(polygon) == 0:
            return None
        point = polygon.sample_points(size=1, method='uniform', rng=seed)
        return point.geometry.iloc[0].coords[0]  # (lon, lat)
```

### Advantages of This Approach

1. **Efficient**: Leverages optimized GeoPandas implementation
2. **Reproducible**: Fixed seed + variation ensures same points every run
3. **Flexible**: Variation key allows different samples from same geography
4. **Cached**: Avoid recomputing for repeated queries
5. **Validated**: Uses well-tested library code

## References

1. GeoPandas Documentation - Sampling Points
   https://geopandas.org/en/stable/docs/user_guide/sampling.html

2. "An Algorithm to Generate Random Points in Polygon Based on Triangulation"
   ResearchGate (2020) - Shows triangulation ~20x faster than rejection sampling

3. "A random spatial sampling method in a rural developing nation"
   BMC Public Health (2014) - Travel survey geographic sampling methodology

4. ESRI "Create Spatial Sampling Locations" Documentation
   ArcGIS Pro 3.3 (2024) - Current industry standards for spatial sampling

## Conclusion

**Recommendation**: Use GeoPandas `sample_points()` method with reproducible seeding based on household ID. This follows current GIS best practices, provides efficient performance, and ensures scientific reproducibility while handling all edge cases automatically.
