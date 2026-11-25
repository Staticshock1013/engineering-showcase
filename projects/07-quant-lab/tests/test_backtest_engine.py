"""NQ futures backtest engine smoke tests."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from quant_lab.backtest.costs import FuturesCostModel
from quant_lab.backtest.engine import run_backtest
from quant_lab.backtest.metrics import assert_finite_ledger, summarize
from quant_lab.data.massive import load_session_volumes_fixture
from quant_lab.data.roll import build_continuous_series

FIXTURES = Path(__file__).resolve().parents[1] / "data" / "fixtures"


def test_engine_runs_on_fixture_front_month() -> None:
    sessions = load_session_volumes_fixture(FIXTURES / "nq_session_volumes.json")
    continuous = build_continuous_series(sessions, back_adjust=False)
    bars = continuous.bars.rename(columns={}).copy()
    bars = bars.loc[:, ["timestamp", "open", "high", "low", "close", "volume", "symbol"]]
    # Always-long after first bar — research smoke only, not a reported result.
    signal = [1.0] * len(bars)
    result = run_backtest(bars, signal, cost_model=FuturesCostModel(), contracts=1.0)
    assert_finite_ledger(result)
    summary = summarize(result)
    assert summary.bars == len(bars)
    assert summary.gross_pnl != 0.0 or len(bars) < 2


def test_engine_rejects_duplicate_timestamps() -> None:
    bars = pd.DataFrame(
        {
            "timestamp": [pd.Timestamp("2024-01-01", tz="UTC")] * 2,
            "open": [1.0, 1.0],
            "high": [1.0, 1.0],
            "low": [1.0, 1.0],
            "close": [1.0, 1.0],
            "volume": [1, 1],
            "symbol": ["NQH6", "NQH6"],
        }
    )
    with pytest.raises(ValueError, match="duplicate"):
        run_backtest(bars, [0.0, 0.0])
