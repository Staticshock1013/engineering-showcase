# Data sources and provenance

## Synthetic prototype data

`terratrend/fixtures/synthetic_observations.csv` is deterministic fixture data. It drives every
global map and regional-comparison chart, carries an explicit synthetic label, and is not Earth
observation data.

## Verified MOD11A2 samples

The processed cache contains two independently authenticated Terra MODIS `MOD11A2` v061 daytime
eight-day samples:

- New York City: `MOD11A2.A2024001.h12v04.061.2024011195232`, 2024-01-01 to 2024-01-08.
- London: `MOD11A2.A2024177.h17v03.061.2024186042347`, 2024-06-25 to 2024-07-02.

Each `terratrend/processed/*.json` file records its CMR concept ID, provider, query URL, protected
data URL, temporal extent, product documentation URL, processing rule, and pixel counts. The
dashboard exposes these fields in the verified-sample provenance panel. No token is present in
these files.

Authoritative product semantics are taken from the [MOD11 User Guide
v6.1](https://lpdaac.usgs.gov/documents/715/MOD11_User_Guide_V61.pdf). CMR is used for collection
and granule metadata. The local application does not treat catalog metadata alone as an
observation.
