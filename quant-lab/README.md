# quant-lab

Research-only equity and futures backtesting lab for ML engineering portfolio work.

**No live trading. No broker order placement.** Credentials stay in a local `.env` (gitignored). Raw market data stays under `data/` (gitignored); only small fixtures ship with the repo.

## Goals

1. Backtest equity strategies on Robinhood price data.
2. Backtest futures strategies on Massive NQ front-month aggregates (1-min and daily).
3. Study moving-average behavior and which stocks track NQ (lag + strength).
4. Train one simple ML direction model with walk-forward validation vs a naive baseline.

## Status

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Scaffold (this commit) | Done |
| 2 | Data layer + front-month roll | Planned |
| 3 | Backtest engine + cost model | Planned |
| 4 | MA study (20/50/200) | Planned |
| 5 | NQ→stock lead/lag analysis | Planned |
| 6 | Walk-forward ML vs baseline | Planned |
| 7 | Results + limitations in README | Planned |

## Quick start

```bash
cd quant-lab
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # fill credentials locally; never commit .env
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

## Layout

```
quant-lab/
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
- Data vendor APIs and symbol calendars may change; fixtures keep CI deterministic.
- Holdout policy and cost assumptions will be documented per experiment SPEC.
- Full limitations list lands after phase 7.

## License

MIT (same as the parent engineering-showcase repo).
