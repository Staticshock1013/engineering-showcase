# ma-study results (synthetic — SPENT, not evidence)

## Status

**HOLDOUT: SPENT ON SYNTHETIC DATA — NOT EVIDENCE.**

The synthetic-data holdout evaluation below is **void for claims**. It must not be
presented as a pass, fail, or supportive result for the MA study. Development and
holdout windows used here are spent for the synthetic series only.

A separate real-data evaluation uses local NQ 1-minute bars under `data/ff_nq/`,
with a **new** holdout window recorded in `experiments/ma-study-ff-nq/SPEC.md`
before that run.

## Synthetic run archive (non-evidential)

- SPEC SHA-256: `dd4419213df4d74c313538496fc0b031d8dd34d24260922d392882ba9d035e96`
- Data: `data/fixtures/nq_daily_synthetic.csv` (**synthetic**)
- Contract / costs: NQ, `$2.50` per side (`usd_per_contract_per_side`)
- Decision label from the voided run (do not cite): former “PASS via ma20_family” on hit-rate only; secondary net PnL did not beat baseline. **Neither metric is evidence.**

| window | signal | n | hit_rate | baseline | edge | mean_net_pnl | baseline_net |
|--------|--------|---|----------|----------|------|--------------|--------------|
| development | price_cross_ma20_up | 66 | 0.5455 | 0.5303 | 0.0152 | 70.56 | -78.98 |
| development | price_cross_ma20_down | 65 | 0.4923 | 0.4462 | 0.0462 | 109.76 | -147.94 |
| development | golden_cross | 4 | 0.5000 | 0.2500 | 0.2500 | 169.23 | -391.77 |
| development | death_cross | 3 | 0.3333 | 0.6667 | -0.3333 | 12.60 | 147.23 |
| development | ma20_family | 131 | 0.5191 | 0.4885 | 0.0305 | 90.01 | -113.18 |
| development | cross_family | 7 | 0.4286 | 0.4286 | 0.0000 | 102.10 | -161.20 |
| holdout (SPENT/synthetic) | price_cross_ma20_up | 18 | 0.6111 | 0.7222 | -0.1111 | 193.02 | 447.17 |
| holdout (SPENT/synthetic) | price_cross_ma20_down | 19 | 0.4211 | 0.6316 | -0.2105 | -398.66 | 218.36 |
| holdout (SPENT/synthetic) | golden_cross | 1 | 0.0000 | 1.0000 | -1.0000 | -601.79 | 571.79 |
| holdout (SPENT/synthetic) | death_cross | 1 | 1.0000 | 1.0000 | 0.0000 | 499.22 | 499.22 |
| holdout (SPENT/synthetic) | ma20_family | 37 | 0.5135 | 0.4595 | 0.0541 | -110.82 | -77.65 |
| holdout (SPENT/synthetic) | cross_family | 2 | 0.5000 | 1.0000 | -0.5000 | -51.29 | 535.50 |

See `experiments/ma-study-ff-nq/` for the real-data protocol.
