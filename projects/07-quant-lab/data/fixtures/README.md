# Fixtures

Committed samples for CI and offline research. **Not live market data.**

| File | Purpose |
|------|---------|
| `nq_session_volumes.json` | Front-month roll unit tests |
| `nq_h6_1min_aggs.json` | Massive-shaped 1-min aggregate sample |
| `equity_spy_sample.csv` | Robinhood local-export schema sample (not used by NQ MA study) |
| `nq_daily_synthetic.csv` | Labeled **synthetic** NQ daily series for the pre-registered `ma-study` experiment |

Do not commit real Massive/Robinhood downloads here; those stay under `data/cache/` (gitignored).
