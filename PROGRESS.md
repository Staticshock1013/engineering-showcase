# Build Log

One entry per working day, newest first. Each entry lists what shipped, how it was verified, and what
comes next.

## 2026-11-25 — Setup diagnostics dashboard

- Added `projects/08-setup-diagnostics/`: Polars loader, two placeholder NQ setups, and a Streamlit failure dashboard.
- The Mac front-month parquet is the preferred input. This environment cannot see that disk, so the app generates a labeled synthetic sample and the tests run on it.
- Verified: `cd projects/08-setup-diagnostics && ./test.sh`.
- Next: on the Mac, open the front-month parquet in the sidebar and replace `signals_breakout` / `signals_mean_reversion`.

## 2026-11-24 — TerraTrend on the main portfolio

- Merged [PR #1](https://github.com/Staticshock1013/engineering-showcase/pull/1) so
  `projects/06-terratrend-global/` is on `main`.
- Featured TerraTrend Global as project 6 in the root README (Verified MVP), with matching ROADMAP
  section and honest period-level scope (no annual / decision-ready claims).
- Verified: `cd projects/06-terratrend-global && ./test.sh` — 52 passed.
- Next: keep portfolio listing accurate as later TerraTrend work lands; projects 1–5 remain Planned.

## 2026-10-22 — Repository setup

- Created the showcase repository, roadmap, and daily build playbook.
- Next: begin Project 1 (Developer Portfolio Website), milestone 1 — scaffold and CI.
