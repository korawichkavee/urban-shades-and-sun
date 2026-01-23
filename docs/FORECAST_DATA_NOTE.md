# Historical Forecast Data

## Request
Collect what the forecast was for the next day at the time of the street view image (for average temperature and rain).

## Status
**Not yet implemented** - Historical forecast data requires different data sources than ERA5 reanalysis.

## Technical Considerations

### ERA5 vs Forecast Data
- **ERA5** (currently used): Reanalysis data - the "actual" weather conditions after the fact
- **Historical Forecasts**: What the forecast predicted beforeprior to the actual date

### Potential Data Sources

1. **Open-Meteo Historical Forecast API**
   - May have limited historical forecast archive
   - Need to investigate availability and date range
   - URL: https://open-meteo.com/en/docs/historical-forecast-api

2. **Weather Service Archives**
   - NOAA/NWS archives (US-focused)
   - ECMWF forecast archives (global, but may require subscription)
   - National weather service archives for specific regions

3. **Commercial APIs**
   - Weather Underground historical forecasts
   - Visual Crossing Weather
   - May have cost implications

### Implementation Challenges

1. **Date Range**: Historical forecasts may not be available for all dates in the dataset
2. **Lead Time**: Need to specify forecast lead time (e.g., 24-hour ahead forecast)
3. **Data Availability**: Different cities may have different forecast archive availability
4. **API Complexity**: May require different API endpoints/credentials

### Recommended Approach

1. First complete the current implementation with ERA5 reanalysis data
2. Analyze results to determine if forecast data would significantly improve the analysis
3. If valuable, investigate Open-Meteo Historical Forecast API as first option
4. Consider adding forecast data as an optional enhancement layer

## Current Data Collected

The enhanced UTCI script currently collects:
- ✓ Current UTCI temperature
- ✓ Prior day UTCI average (ERA5 reanalysis)
- ✓ Next day UTCI average (ERA5 reanalysis)
- ✓ Prior day rain (ERA5 reanalysis)
- ✓ Next day rain (ERA5 reanalysis)
- ✗ Forecast for next day at time of image (not yet implemented)

## Next Steps

If forecast data is deemed critical:
1. Test Open-Meteo Historical Forecast API with sample dates
2. Determine data availability for our date range
3. Create separate module for forecast data collection
4. Add as optional column to the dataset
