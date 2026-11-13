# Limitations

- The global dashboard charts are synthetic fixture visualizations, not real global indicators.
- Verified real-data caches cover three city-level eight-day MOD11A2 periods and one city-level
  16-day MOD13A2 NDVI period. They are neither annual measurements nor a multiyear time series.
- MOD11A2 is daytime land-surface temperature, not near-surface air temperature. Its selected
  QC criteria and city bounding-box mean are implementation choices recorded in provenance.
- No uncertainty interval, station comparison, land-cover stratification, or urban/rural
  representativeness analysis is included.
- NDVI is an optical vegetation index, not a direct biomass, carbon, or vegetation-health
  measurement. The one verified city period cannot support those claims.
- Runtime batch caches require a bounded explicit apply action and are not automatically exposed
  in the dashboard.
- An annual result requires complete contiguous annual coverage; a trend requires at least three
  complete annual results. Neither condition is currently satisfied, so the MVP makes no trend,
  climate-change, policy, or operational claim.
