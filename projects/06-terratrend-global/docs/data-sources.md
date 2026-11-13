# Data sources and provenance

## Synthetic prototype data

`terratrend/fixtures/synthetic_observations.csv` is deterministic fixture data. It drives every
global map and regional-comparison chart, carries an explicit synthetic label, and is not Earth
observation data.

## Verified MOD11A2 samples

The processed cache contains three independently authenticated Terra MODIS `MOD11A2` v061 daytime
eight-day samples:

- New York City: `MOD11A2.A2024001.h12v04.061.2024011195232`, 2024-01-01 to 2024-01-08.
- London: `MOD11A2.A2024177.h17v03.061.2024186042347`, 2024-06-25 to 2024-07-02.
- New York City: `MOD11A2.A2024177.h12v04.061.2024186041340`, 2024-06-25 to 2024-07-02.

The final two samples have the same product, exact period, QC rule, and spatial-sampling method,
so they are eligible for the dashboard's verified period-level city comparison. That comparison
does not make an annual or trend claim.

Each `terratrend/processed/*.json` file records its CMR concept ID, provider, query URL, protected
data URL, temporal extent, product documentation URL, processing rule, and pixel counts. The
dashboard exposes these fields in the verified-sample provenance panel. No token is present in
these files.

Authoritative product semantics are taken from the [MOD11 User Guide
v6.1](https://lpdaac.usgs.gov/documents/715/MOD11_User_Guide_V61.pdf). CMR is used for collection
and granule metadata. The local application does not treat catalog metadata alone as an
observation.

## Verified MOD13A2 NDVI sample

New York City also has one authenticated `MOD13A2` v061 NDVI cache:
`MOD13A2.A2024177.h12v04.061.2024195022551`, covering 2024-06-25 to 2024-07-10. Its provenance is
stored in `terratrend/processed/mod13a2_nyc_2024-06-25.json`. NDVI semantics and QA come from the
[MOD13 User Guide v6.1](https://lpdaac.usgs.gov/documents/621/MOD13_User_Guide_V61.pdf).

The bounded historical fixed-season cache is in `terratrend/series/nyc-mod13a2-doy177/`. Its
manifest records 15 authenticated DOY-177 periods from 2010–2024, their granules, valid-pixel
fractions, threshold decisions, and fixed-season trend statistics. Each referenced period JSON
contains the source URL and CMR provenance; credentials are not stored.

The matching London central/west tile-contained series is in
`terratrend/series/london-west-tile-mod13a2-doy177/`. It contains the same 15 authenticated
DOY-177 source periods. Its manifest marks the 2021 period rejected for insufficient valid-pixel
coverage (9.72% against the 10% threshold), retaining the source cache and provenance.
