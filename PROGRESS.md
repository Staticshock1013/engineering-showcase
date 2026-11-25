# Build Log

One entry per working day, newest first. Each entry lists what shipped, how it was verified, and what
comes next.

## 2026-11-25 — Job-ready portfolio + quant-lab on showcase path

- Merged `main` (TerraTrend as project 6) into the quant-lab branch; renumbered quant-lab to
  `projects/07-quant-lab/` so both shipped projects coexist.
- Rewrote the root README as a hire-ready portfolio: role targets, skills table, dual featured
  projects with run commands, architecture visual for quant-lab.
- Verified: `projects/07-quant-lab` pytest (34 passed) + PDHL demo; TerraTrend remains on `main`.
- Next: merge this PR so `main` shows quant-lab when opening the repo; sync `data/ff_nq/` for
  real-data MA evaluation; optional Portfolio site refresh.

## 2026-11-24 — quant-lab portfolio polish

- Featured **quant-lab** on the root README with architecture visual.
- Rewrote quant-lab README: mermaid pipeline, honest SPENT ma-study results, PDHL demo, challenges.
- Verified: `pytest -q` (34 passed) and PDHL demo under `examples/pdhl_demo/`.

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
