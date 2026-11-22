"""Synthetic fixture test for the PDHL portfolio demo (not spy-pdhl-v1)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "pdhl_demo" / "pdhl_backtest.py"
FIXTURE = ROOT / "examples" / "pdhl_demo" / "fixtures" / "failed_break_retest.csv"


def _load_demo():
    spec = importlib.util.spec_from_file_location("pdhl_backtest", DEMO)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_failed_break_produces_one_retest_trade_to_pdl() -> None:
    demo = _load_demo()
    minutes = pd.read_csv(FIXTURE)
    trades = demo.run_failed_break_retest(minutes, round_trip_cost_points=0.14)

    assert len(trades) == 1
    trade = trades[0]
    assert trade.direction == -1
    assert trade.entry_price == pytest.approx(trade.pdh)
    assert trade.exit_price == pytest.approx(trade.pdl)
    assert trade.exit_price == pytest.approx(499.50)
    assert trade.gross_points == pytest.approx(trade.entry_price - trade.exit_price)
    assert trade.net_points == pytest.approx(trade.gross_points - 0.14)
