# TerraTrend Global — Phase 1

TerraTrend Global is a small, transparent MVP for exploring how a global environmental-change
dashboard can organize indicators, display regional context, and calculate repeatable summaries.

> **Data status:** every value shipped in Phase 1 is a labeled deterministic synthetic fixture.
> It is not real Earth observation data, is not derived from NASA products, and is unsuitable for
> scientific, policy, or operational decisions.

## What is included

- A typed global indicator registry for surface temperature, vegetation, and precipitation anomalies.
- A validated CSV fixture with 18 clearly labeled synthetic regional observations.
- A reusable, dependency-free statistics module for descriptive and regional summaries.
- A Streamlit dashboard with indicator selection, global map, regional comparison, and provenance
  disclosure.
- Deterministic pytest coverage for data labeling, empty inputs, numerical summaries, and grouping.

## Architecture

```mermaid
flowchart LR
  F[Labeled synthetic CSV] --> V[Fixture validation]
  R[Indicator registry] --> V
  V --> S[Statistics module]
  V --> D[Streamlit dashboard]
  S --> D
```

## Run locally

Python 3.12+ is recommended.

```bash
cd projects/06-terratrend-global
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

## Test

```bash
cd projects/06-terratrend-global
python -m pytest
```

## NASA access investigation (minimal)

On 2026-11-13, a request to the official NASA Common Metadata Repository (CMR) catalog endpoint
returned one matching collection for `short_name=MOD13Q1`:

```text
https://cmr.earthdata.nasa.gov/search/collections.json?short_name=MOD13Q1&page_size=1
```

The returned collection identifier was `C1748066515-LPCLOUD`. This verifies only that the public
catalog endpoint was reachable from the development environment at that time. It does **not**
verify Earthdata Login authorization, protected data-download access, API rate limits, product
selection, or a working production ingestion pipeline. No NASA credentials were requested,
stored, or used, and this MVP does not fetch live NASA data.

## Known limitations

- The map uses one representative coordinate per synthetic region, not gridded geospatial data.
- Two fixture months support UI prototyping only; they do not establish trends.
- Values are simple anomalies with no uncertainty, quality flags, temporal aggregation, or
  scientific baseline provenance.
- No live API connector, authentication flow, caching, or database is included in Phase 1.

## Next steps

1. Select authoritative products and document their spatial, temporal, and quality semantics.
2. Implement credential-safe, rate-aware ingestion after confirming authorized access.
3. Add provenance, uncertainty, quality flags, and tests around transformation rules.
