# Limitations

- The global dashboard charts are synthetic fixture visualizations, not real global indicators.
- Verified real-data caches cover six cities with city-level eight-day MOD11A2 periods
  (New York City, London, Lagos, Tokyo, Mumbai, São Paulo) plus MOD13A2 NDVI period samples for
  New York City and São Paulo. Expansion cities use tile-contained sampling windows, not
  administrative city extents, and are neither annual measurements nor multiyear time series.
- Lagos, Tokyo, and Mumbai have no QC-passing pixels for the preferred 2024-06-25–07-02 shared
  LST window; that failure is recorded as unavailable rather than fabricated. Their alternate
  verified LST periods are not comparable to the shared-window cities.
- The São Paulo shared-window LST sample has a very low QC-passing fraction (4 of 662 pixels) and
  must not be treated as a representative city-wide temperature.
- MOD11A2 is daytime land-surface temperature, not near-surface air temperature. Its selected
  QC criteria and city bounding-box mean are implementation choices recorded in provenance.
- No uncertainty interval, station comparison, land-cover stratification, or urban/rural
  representativeness analysis is included.
- NDVI is an optical vegetation index, not a direct biomass, carbon, or vegetation-health
  measurement. The NYC and São Paulo NDVI period caches are period-level only and cannot support
  annual vegetation claims; São Paulo has a period cache, not a multiyear fixed-season series.
- The NYC 2010–2024 NDVI output samples one 16-day DOY-177 composite each year, not annual
  coverage. Its OLS slope, confidence interval, and p-value are descriptive fixed-season
  statistics contingent on the selected period, QC threshold, and city bounding box; they do not
  establish an annual trend, causation, or attribution.
- The London seasonal series covers only a tile-contained central/west analysis window, not the
  full London bbox, because the latter spans two MODIS tiles. Its qualified comparison with NYC is
  side-by-side descriptive reporting, not a formal test of city slope differences.
- Runtime batch caches require a bounded explicit apply action and are not automatically exposed
  in the dashboard.
- An annual result requires complete contiguous annual coverage; a trend requires at least three
  complete annual results. Neither condition is currently satisfied, so the MVP makes no trend,
  climate-change, policy, or operational claim.
