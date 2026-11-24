# Build Log

One entry per working day, newest first. Each entry lists what shipped, how it was verified, and what
comes next.

## 2026-11-24 — quant-lab portfolio polish

- Featured **quant-lab** on the root README with architecture visual (`projects/06-quant-lab/docs/architecture.jpg`).
- Rewrote `projects/06-quant-lab/README.md` for portfolio clarity: mermaid pipeline, honest SPENT ma-study results, PDHL demo, challenges.
- Verified: `pytest -q` (34 passed) and PDHL demo script under `examples/pdhl_demo/`.
- Next: sync `data/ff_nq/` for real-data MA evaluation; add frozen `experiments/spy-pdhl-v1/` when SPEC is available; lead/lag (phase 5).

## 2026-10-22 — Repository setup

- Created the showcase repository, roadmap, and daily build playbook.
- Next: begin Project 1 (Developer Portfolio Website), milestone 1 — scaffold and CI.
