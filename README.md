# Engineering Showcase

Real-world software projects by **Denzell Richardson**, built in small, reviewable daily milestones.
Each project targets a concrete problem from IT support, cloud operations, QA, or security work, and is
held to the same quality bar: it runs, it is tested, and it is documented honestly.

## Projects

| # | Project | Stack | Status | Target roles |
|---|---------|-------|--------|--------------|
| 1 | Developer Portfolio Website | React, TypeScript, Tailwind, Vercel | Planned | All technical roles |
| 2 | IT Service Desk Simulator | React, TypeScript, FastAPI, SQLite, Python | Planned | Help Desk, IT Support, Junior Developer |
| 3 | Cloud Infrastructure Monitor | Python, FastAPI, Docker, Linux, C++ probe | Planned | Cloud Support, IT Operations, Data Center Tech |
| 4 | Security Operations Lab | Python, C++ log parser, Linux | Planned | SOC Trainee, Security Support |
| 5 | QA Automation Testing Suite | Playwright, TypeScript, GitHub Actions | Planned | QA Intern, Junior QA Engineer |
| 6 | [TerraTrend Global](projects/06-terratrend-global/) | Python, Streamlit, Plotly, NASA MODIS | Verified MVP | Data / Python, Geospatial, Climate tech |
| 8 | [Setup diagnostics](projects/08-setup-diagnostics/) | Python, Polars, Streamlit, Plotly | Local research tool | Quant research, Python, data |

**TerraTrend Global** — Streamlit dashboard with authenticated NASA MODIS LST samples (six cities), NDVI period caches, and fixed-season NYC/London series kept separate from labeled synthetic fixtures. Period-level verified samples only; not annual means, city-wide extents, or decision-ready products. See [`projects/06-terratrend-global/`](projects/06-terratrend-global/).

**Setup diagnostics** — Streamlit dashboard that scores two placeholder NQ setups on 1-minute bars and breaks losses down by hour, volatility regime, and MAE/MFE. It reads one Massive parquet or gzip at a time. Without the local front-month file it runs on a labeled synthetic sample. Not a live trading system. See [`projects/08-setup-diagnostics/`](projects/08-setup-diagnostics/).

Also featured (separate repo): **Career Intelligence OS** — an AI-assisted career planning app built in TypeScript.

See [ROADMAP.md](ROADMAP.md) for milestones and [PROGRESS.md](PROGRESS.md) for the daily build log.

## Standards every project meets

- A working live demo or a reproducible local setup (one command where possible).
- A README covering the problem, architecture, technologies, and how to run and test it.
- Meaningful automated tests that run in CI.
- A "Technical challenges solved" section.
- A short demo video (recorded by the author; a recording script is provided until then).
- No secrets in the repo, no fabricated users, no invented production metrics. All sample data is
  fictional and labeled as such.

## License

[MIT](LICENSE)
