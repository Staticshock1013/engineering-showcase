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
6. Expansion cities (Lagos, Tokyo, Mumbai, São Paulo) use tile-contained sampling windows. When
   ingesting those cities, the decoder can require the retrieved MODIS tile to fully cover the
   sampling bbox. The preferred shared window is 2024-06-25–07-02; if that window fails QC or
   coverage validation, an explicit unavailable marker is written and no value is fabricated.
   An alternate verified period may be retained without forcing cross-city comparability.

Annual aggregation is duration-weighted and requires complete contiguous calendar coverage.
Fixed-season runs are explicitly not annual. Incomplete annual coverage, fixed-season values, and
fewer than three complete annual results cannot produce a trend claim.

Use `python -m terratrend.ingestion --city london --years 2024` to review a no-network plan.
See the root project README for the bounded one-period apply command.

## MOD13A2 NDVI

The verified NDVI path supports `MOD13A2` Collection 6.1 16-day 1 km composites. It validates
in-file NDVI range (-2000 to 10000), fill value (-3000), detailed-QA schema, and pixel-reliability
schema. The product guide publishes a 0.0001 scale; the validated HDF file records the inverse
divisor 10000, so raw NDVI is divided by 10000. A pixel must have detailed VI-quality bits 0–1
equal to `00` and pixel reliability `0`. The implementation rejects city bboxes not fully covered
by the retrieved MODIS tile, preventing a partial tile from being labeled as a city sample.
São Paulo’s packaged DOY-177 period cache additionally required a ≥10% QC-passing pixel fraction
before acceptance; failed preferred LST windows remain unavailable markers rather than fabricated
values.

## NYC fixed-season series

The historical series uses one MOD13A2 composite beginning on day-of-year 177 each year, which is
June 25 in leap years and June 26 otherwise. Every period uses the same NYC bounding box, product
version, scale/divisor validation, QA rule, spatial method, and a minimum 10% QC-passing pixel
fraction. The series is rate-limited, resumable, and each period retains its own provenance cache.

The reusable `statistics.linear_trend` function applies OLS and reports a two-sided 95% slope
interval and p-value only when at least three periods pass the threshold. These are conditional
fixed-season statistics—not annual aggregation or causal inference.

London uses a separate tile-contained central/west analysis window (`-0.30, 51.35, -0.05, 51.65`)
because the broader London bbox crosses MODIS h17/h18. NYC/London trend display additionally
requires matching product/version, DOY, period definition, QC/spatial method, threshold, and
eligible trend status. It presents side-by-side estimates only; it does not test a difference
between slopes.
