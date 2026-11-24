# 2–3 minute demo walkthrough

## 0:00–0:20 — Scope

Open the dashboard. Point out the warning above the global charts: those global indicators are
deterministic synthetic fixtures, not NASA observations. State that verified NASA data appears in
separate panels and is never relabeled as global coverage.

## 0:20–0:50 — Verified period data and provenance

Use **Verified processed data variable** to select the New York City MOD13A2 NDVI cache. Explain
that it is one validated 16-day period. Expand **Verified sample provenance** and show the product,
version, CMR concept ID, granule, QC rule, product guide, query, and source URL.

## 0:50–1:20 — Safe city comparison

In **Compare two verified city caches**, choose the New York City and London daytime LST entries
for 2024-06-25. Show the resulting period-level comparison. Explain that the control refuses
different variables, units, periods, aggregation states, or processing methods; it is not an
annual comparison.

## 1:20–2:05 — Fixed-season history

Scroll to the NYC and London fixed-season NDVI panels. Explain that each uses one MOD13A2
DOY-177 16-day composite per year from 2010–2024, subject to product, scale, QA, spatial, and
valid-pixel checks. Point out the slope, 95% confidence interval, p-value, and valid-year count.

## 2:05–2:30 — Limitations and handoff

State that the series is fixed-season rather than annual. The London series is a tile-contained
central/west analysis window, and its 2021 observation is excluded by the 10% valid-pixel
threshold. Close with the [limitations](limitations.md), [requirements audit](requirements-audit.md),
and [final run instructions](final-run.md).
