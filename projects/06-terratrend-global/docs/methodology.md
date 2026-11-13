# Methodology

The verified path supports Terra MODIS `MOD11A2` Collection 6.1 daytime land-surface-temperature
eight-day composites for an explicit city bounding box.

1. CMR metadata must match short name `MOD11A2` and version `061`.
2. A protected HDF4 file is retrieved only by an explicit bounded apply action using preconfigured
   Earthdata authentication. Credentials are never written to cache, source, or provenance.
3. The decoder validates in-file `LST_Day_1km` metadata: Kelvin units, valid range 7500–65535,
   fill value 0, scale factor 0.02, and offset 0.
4. It accepts `QC_Day` pixels only when mandatory QA bits 0–1 are `00` and LST-error bits 6–7 are
   `00` or `01` (reported error ≤2 K).
5. MODIS sinusoidal pixel centers are transformed to latitude/longitude and included only when
   they fall within the city bounding box. Accepted raw values are converted to Celsius with
   `raw * 0.02 - 273.15`; the cache stores counts and a mean.

Annual aggregation is duration-weighted and requires complete contiguous calendar coverage.
Fixed-season runs are explicitly not annual. Incomplete annual coverage, fixed-season values, and
fewer than three complete annual results cannot produce a trend claim.

Use `python -m terratrend.ingestion --city london --years 2024` to review a no-network plan.
See the root project README for the bounded one-period apply command.
