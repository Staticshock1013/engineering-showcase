# PDHL demo (portfolio illustration)

Prior-Day High/Low **failed-break → retest** demo on SPY **underlying points**.

## What this is

- Underlying points only — **no options pricing**
- **Not** the frozen `experiments/spy-pdhl-v1` pass/fail test
- Tested on a **synthetic fixture** only
- **Research only** — no live trading or order placement

## Run

```bash
cd projects/07-quant-lab
python examples/pdhl_demo/pdhl_backtest.py
```

Round-trip cost assumption in the demo: **0.14 SPY points**.
