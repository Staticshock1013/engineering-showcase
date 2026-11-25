# Setup diagnostics

Local research dashboard for NQ minute bars. It loads one Massive file at a time, runs two placeholder setups, and shows where those setups make and lose index points.

This is not a live trading system. The placeholder rules are there so the dashboard runs before your own entries and exits are plugged in. Sample bars checked into a run are fictional.

## Run

```bash
cd projects/08-setup-diagnostics
python -m pip install -r requirements.txt
streamlit run app.py
```

`./run-local.sh` does the same install and launch. Tests:

```bash
./test.sh
```

## Data

The loader looks, in order, at the path typed in the sidebar, `SETUP_DATA_PATH`, then:

`/Users/zelly/market-takeover/backtests/stop-regime-v1/data/nq_front_1m_2023_2026.parquet`

That file is the rolled NQ front-month 1-minute series (about 25 MB, 2023-01-03 through 2026-11-20). If it is not on this machine, the app writes a labeled synthetic parquet under `data/sample_nq_1m.parquet` and says so on screen.

Inspect columns without loading a full backtest:

```bash
python data_loader.py --inspect /path/to/nq_front_1m_2023_2026.parquet
```

Expected front-month columns: `ticker`, `session_end_date`, `window_start`, `open`, `high`, `low`, `close`, `volume`. `window_start` is a UTC nanosecond epoch. `1672700400000000000` is 2023-01-02 18:00 America/New_York. Raw daily files also have `exchange`, `dollar_volume`, and `transactions`. Continuous parquets use `ts` and `session_date`.

NQ outrights are kept with `^NQ[HMUZ]\d$`. Spreads and other CME products are dropped.

Do not point the app at `data/massive/cme/`. That tree is more than a thousand daily files. The loader refuses more than 8 files unless `SETUP_ALLOW_WIDE_SCAN=1`. Prefer the front-month parquet, or one yearly file in `data/ff_nq/`.

A session range longer than about four months defaults to the last 90 days. Warmup bars before the start date are loaded so the volatility tercile has history, then trades outside the range are dropped.

## What the placeholder does

Both setups are in `strategy_engine.py`. Replace `signals_breakout` and `signals_mean_reversion` with your rules. Keep the trade log columns.

- **Setup_A_Breakout** — first 09:45–11:00 ET close through the 09:30–09:45 opening range, in the direction of the last completed 15-minute 20-EMA. Stop at the other side of the range. Target is 2.5R. Time exit 15:55 ET.
- **Setup_B_MeanReversion** — midday fade of a 12-point extension from session VWAP. Stop is 8 points. Target is VWAP. No trend filter, so trend days can show the bleed.

Costs are 0.75 index points per round trip: $2.50 commission per side ($20 per NQ point) plus 1 tick of slippage per side. `pnl_net` is in index points. The overview also shows that figure times $20.

`atr_regime` is the tercile of the 08:00–09:30 ET high-low range versus a trailing 60 sessions. That range is known before 09:45. `trend_regime` is `above` or `below` the last completed 15-minute EMA. MAE and MFE are positive point distances while the trade is open. If stop and target print on the same bar, the fill is the stop.

Every run writes `outputs/trades.parquet`.

## Tabs

1. **Overview** — net points, win rate, profit factor, expectancy in R, max drawdown, Sharpe of daily summed R, equity curve with the drawdown shaded.
2. **Setup failure diagnostics** — setup table, hour-by-weekday heatmaps, net points by volatility regime and by EMA regime.
3. **MAE / MFE** — excursion versus net points for each setup.
4. **Trade inspector** — trade table. Select a row or a trade id to plot the surrounding candles with entry, exit, stop, target, VWAP, and the 15-minute EMA.

Sharpe needs at least two exit days and a non-zero standard deviation. Empty filter cells on the heatmap stay blank.

## Layout

- `data_loader.py` — Polars lazy scan, ET conversion, resample, file budget
- `strategy_engine.py` — features, placeholder setups, trade log
- `metrics.py` — KPIs, filters, heatmaps
- `sample_data.py` — fictional NQ minute bars
- `app.py` — Streamlit dashboard
