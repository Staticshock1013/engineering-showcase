"""Placeholder setups: schema, cost math, and both win and loss paths."""

from __future__ import annotations

import numpy as np
import polars as pl

from metrics import filter_trades, kpis
from sample_data import build_sample_frame
from strategy_engine import (
    COST_POINTS,
    TRADE_COLUMNS,
    label_volatility_regimes,
    run_setups,
    walk_exit,
)


def test_same_bar_stop_and_target_fills_the_stop() -> None:
    outcome = walk_exit(
        high=np.array([10.0, 15.0]),
        low=np.array([9.0, 7.0]),
        close=np.array([10.0, 12.0]),
        start_index=1,
        end_index=1,
        direction=1,
        stop=8.0,
        target=14.0,
        entry=10.0,
    )
    assert outcome.reason == "stop"
    assert outcome.price == 8.0
    assert outcome.mfe == 0.0
    assert outcome.mae >= 2.0


def test_target_fills_when_the_stop_is_not_touched() -> None:
    outcome = walk_exit(
        high=np.array([10.0, 11.0, 14.5]),
        low=np.array([9.5, 9.6, 10.5]),
        close=np.array([10.0, 10.8, 14.0]),
        start_index=1,
        end_index=2,
        direction=1,
        stop=9.0,
        target=14.0,
        entry=10.0,
    )
    assert outcome.reason == "target"
    assert outcome.price == 14.0
    assert outcome.mfe >= 4.0


def test_volatility_labels_cover_low_and_high() -> None:
    values = [1.0, 1.0, 12.0, 30.0] * 6
    labels = label_volatility_regimes(values)
    assert set(labels) <= {"Low", "Med", "High"}
    assert "Low" in labels
    assert "High" in labels


def test_sample_setups_log_the_trade_schema() -> None:
    bars_raw = build_sample_frame(sessions=40)
    # Run through the loader's column contract by renaming to the in-memory shape
    # the engine expects: timestamp already in ET, plus session tags.
    from data_loader import load_bars
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "sample.parquet"
        bars_raw.write_parquet(path)
        bars, meta = load_bars(path, warmup_days=0)
    assert meta["synthetic"] is False or meta["rows"] > 0
    trades = run_setups(bars)
    assert trades.columns == TRADE_COLUMNS
    names = set(trades["setup_name"].unique().to_list())
    assert names == {"Setup_A_Breakout", "Setup_B_MeanReversion"}
    assert trades["direction"].is_in(["Long", "Short"]).all()
    assert set(trades["atr_regime"].unique().to_list()) <= {"Low", "Med", "High"}
    assert set(trades["trend_regime"].unique().to_list()) <= {"above", "below"}
    for row in trades.iter_rows(named=True):
        sign = 1 if row["direction"] == "Long" else -1
        gross = sign * (row["exit_price"] - row["entry_price"])
        assert row["commission_slippage"] == COST_POINTS
        assert abs(row["pnl_gross"] - gross) < 1e-9
        assert abs(row["pnl_net"] - (gross - COST_POINTS)) < 1e-9
        assert abs(row["r_multiple"] - row["pnl_net"] / row["risk_points"]) < 1e-9
        assert row["mae"] >= 0
        assert row["mfe"] >= 0
        assert row["entry_time"] < row["exit_time"]
    assert (trades["pnl_net"] > 0).any()
    assert (trades["pnl_net"] < 0).any()
    breakout = trades.filter(pl.col("setup_name") == "Setup_A_Breakout")
    high = breakout.filter(pl.col("atr_regime") == "High")["pnl_net"].sum()
    low = breakout.filter(pl.col("atr_regime") == "Low")["pnl_net"].sum()
    assert high > 0
    assert low < 0
    stats = kpis(trades)
    assert stats["trades"] == trades.height
    assert stats["win_rate"] is not None
    narrowed = filter_trades(trades, setups=["Setup_A_Breakout"], directions=["Long"])
    assert narrowed["setup_name"].n_unique() == 1
