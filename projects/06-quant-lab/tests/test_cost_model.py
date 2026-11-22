"""Cost-model unit tests — must pass before any strategy results are reported."""

from __future__ import annotations

import pandas as pd
import pytest

from quant_lab.backtest.costs import FuturesCostModel
from quant_lab.backtest.engine import run_backtest
from quant_lab.backtest.metrics import assert_costs_reduce_pnl, summarize


def _nq_bars() -> pd.DataFrame:
    # Synthetic NQ-like daily closes with clear point moves.
    closes = [18000.0, 18010.0, 18005.0, 18025.0, 18020.0]
    rows = []
    for i, close in enumerate(closes):
        rows.append(
            {
                "timestamp": pd.Timestamp("2024-03-11", tz="UTC") + pd.Timedelta(days=i),
                "open": close - 2.0,
                "high": close + 5.0,
                "low": close - 5.0,
                "close": close,
                "volume": 1000 + i,
                "symbol": "NQH6",
            }
        )
    return pd.DataFrame(rows)


def test_nq_default_cost_per_side_is_commission_plus_slippage() -> None:
    model = FuturesCostModel(
        commission_per_side=2.50,
        slippage_ticks=1.0,
        tick_size=0.25,
        point_value=20.0,
    )
    # 1 tick * 0.25 points * $20 = $5 slippage; + $2.50 commission = $7.50 / side
    assert model.slippage_per_side_usd() == pytest.approx(5.0)
    assert model.cost_per_side_usd() == pytest.approx(7.50)
    assert model.cost_for_trade(1.0) == pytest.approx(7.50)
    assert model.cost_for_trade(2.0) == pytest.approx(15.0)
    assumptions = model.as_assumptions()
    assert assumptions["round_trip_1_contract_usd"] == pytest.approx(15.0)


def test_cost_for_trade_rejects_negative_turnover() -> None:
    with pytest.raises(ValueError):
        FuturesCostModel().cost_for_trade(-1.0)


def test_backtest_charges_costs_on_position_changes() -> None:
    bars = _nq_bars()
    # Flat, then long 1, stay long, then flat — two one-sided trades of 1 contract.
    signal = [0.0, 1.0, 1.0, 0.0, 0.0]
    model = FuturesCostModel(
        commission_per_side=2.50,
        slippage_ticks=1.0,
        tick_size=0.25,
        point_value=20.0,
    )
    result = run_backtest(bars, signal, cost_model=model, contracts=1.0)
    # Position becomes 1 on bar index 2 (signal[1] shifted), back to 0 on index 4.
    traded = result.ledger["contracts_traded"].tolist()
    assert traded[0] == pytest.approx(0.0)
    assert sum(traded) == pytest.approx(2.0)
    assert result.total_costs == pytest.approx(2.0 * model.cost_per_side_usd())
    assert_costs_reduce_pnl(result)
    summary = summarize(result)
    assert summary.total_costs == pytest.approx(result.total_costs)
    assert "commission_per_side_usd" in summary.cost_assumptions


def test_zero_turnover_has_zero_costs() -> None:
    bars = _nq_bars()
    result = run_backtest(bars, [0.0] * len(bars), cost_model=FuturesCostModel())
    assert result.total_costs == pytest.approx(0.0)
    assert result.net_pnl == pytest.approx(result.gross_pnl)
