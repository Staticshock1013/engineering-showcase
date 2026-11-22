# quant-lab

Research-only equity and futures backtesting lab for ML engineering portfolio work.

**No live trading. No broker order placement.** Credentials stay in a local `.env` (gitignored). Raw market data stays under `data/` (gitignored); only small fixtures ship with the repo.

Path in this monorepo: `projects/06-quant-lab/`.

## Goals

1. Backtest equity strategies on local Robinhood CSV/Parquet exports.
2. Backtest futures strategies on Massive NQ front-month aggregates (1-min and daily).
3. Study moving-average behavior and which stocks track NQ (lag + strength).
4. Train one simple ML direction model with walk-forward validation vs a naive baseline.

## Status

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Scaffold | Done |
| 2 | Data layer + front-month roll (fixture-only) | Done |
| 3 | Backtest engine + cost model | Planned |
| 4 | MA study (20/50/200) | Planned |
| 5 | NQ→stock lead/lag analysis | Planned |
| 6 | Walk-forward ML vs baseline | Planned |
| 7 | Results + limitations in README | Planned |

## Data access (confirmed)

### Massive futures (Polygon rebrand)

Verified against current Massive docs:

- Base URL: `https://api.massive.com`
- Contracts: `GET /futures/v1/contracts`
- Aggregates: `GET /futures/v1/aggs/{ticker}` with `resolution=1min` or `1day`
- **No continuous NQ series** — front month is built by highest session volume (see `src/quant_lab/data/roll.py`)

Live downloads stay disabled until `MASSIVE_API_KEY` is set as a Cursor/GitHub secret (never paste keys into chat). Until then, use fixtures:

```bash
quant-lab download-data --source fixtures
```

### Robinhood equities

Local CSV/Parquet exports only via `ROBINHOOD_DATA_DIR`. No unofficial API client.

```bash
quant-lab download-data --source robinhood
```

Robinhood minute history is short (~2 weeks). Longer SPY cash history should come from Massive once a key is configured. **SPY 0DTE / option premium is a separate experiment** and is not part of the NQ roll pipeline.

## Quick start

```bash
cd projects/06-quant-lab
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # fill locally; never commit .env
quant-lab download-data --source fixtures
pytest
ruff check src tests
quant-lab version
```

## Experiment protocol

Before any test run:

1. Write `experiments/<name>/SPEC.md` (hypothesis, data window, metric, threshold, baseline, holdout).
2. Save `SHA-256` of that spec to `experiments/<name>/HASH.txt`.
3. Results must be checked against the frozen spec; holdout windows are never used for tuning.
4. Use walk-forward validation (not random splits). State transaction costs and slippage explicitly.

NQ futures experiments and SPY 0DTE experiments must live in **separate** folders. See `experiments/README.md`.

## Layout

```
projects/06-quant-lab/
  src/quant_lab/     data, features, backtest, models, analysis
  experiments/       pre-registered SPEC.md + HASH.txt per experiment
  tests/             unit tests (roll, costs, features, no-lookahead)
  data/              local cache (gitignored) + fixtures/ (committed samples)
  notebooks/         optional summary notebook only — no business logic
```

## Results summary

_Pending — filled after pre-registered experiments run._

## Limitations

- Research only; results are not investment advice and ignore many real-world frictions.
- Step 2 is fixture-only for Massive until `MASSIVE_API_KEY` is configured.
- Front-month series is unadjusted by default; rolls introduce price jumps unless back-adjust is enabled.
- Options / SPY 0DTE premium data is out of scope for the NQ data layer.
- Holdout policy and cost assumptions will be documented per experiment SPEC.

## License

MIT (same as the parent engineering-showcase repo).
