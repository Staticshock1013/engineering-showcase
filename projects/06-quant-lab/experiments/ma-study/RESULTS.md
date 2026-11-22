# ma-study results

- SPEC SHA-256: `dd4419213df4d74c313538496fc0b031d8dd34d24260922d392882ba9d035e96`
- Data: `/agent/repos/engineering-showcase/projects/06-quant-lab/data/fixtures/nq_daily_synthetic.csv` (synthetic NQ daily fixture unless overridden)
- Contract / costs: `{'contract': 'NQ', 'commission_basis': 'usd_per_contract_per_side', 'commission_per_side_usd': 2.5, 'slippage_ticks': 1.0, 'tick_size': 0.25, 'point_value_usd': 20.0, 'cost_per_side_usd': 7.5, 'round_trip_1_contract_usd': 15.0, 'note': 'NQ $2.50 per side — not MNQ; not $2.50 round-trip'}`
- Holdout decision: **PASS** — PASS via ma20_family: n=37, edge=0.0541

| window | signal | n | hit_rate | baseline | edge | mean_net_pnl | baseline_net |
|--------|--------|---|----------|----------|------|--------------|--------------|
| development | price_cross_ma20_up | 66 | 0.4242 | 0.5152 | -0.0909 | 53.04 | -43.87 |
| development | price_cross_ma20_down | 65 | 0.6154 | 0.5077 | 0.1077 | 127.54 | -56.29 |
| development | golden_cross | 4 | 0.5000 | 0.5000 | 0.0000 | 169.23 | -98.89 |
| development | death_cross | 3 | 0.3333 | 0.6667 | -0.3333 | 12.60 | 147.23 |
| development | ma20_family | 131 | 0.5191 | 0.4885 | 0.0305 | 90.01 | -113.18 |
| development | cross_family | 7 | 0.4286 | 0.4286 | 0.0000 | 102.10 | -161.20 |
| holdout | price_cross_ma20_up | 18 | 0.6111 | 0.7222 | -0.1111 | 193.02 | 447.17 |
| holdout | price_cross_ma20_down | 19 | 0.4211 | 0.6316 | -0.2105 | -398.66 | 218.36 |
| holdout | golden_cross | 1 | 0.0000 | 1.0000 | -1.0000 | -601.79 | 571.79 |
| holdout | death_cross | 1 | 1.0000 | 1.0000 | 0.0000 | 499.22 | 499.22 |
| holdout | ma20_family | 37 | 0.5135 | 0.4595 | 0.0541 | -110.82 | -77.65 |
| holdout | cross_family | 2 | 0.5000 | 1.0000 | -0.5000 | -51.29 | 535.50 |

Development window is spent. Holdout was evaluated once against the frozen threshold.

