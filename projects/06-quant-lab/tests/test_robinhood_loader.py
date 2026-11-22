"""Robinhood local export loader tests."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from quant_lab.data.robinhood import RobinhoodLoader, normalize_equity_frame

FIXTURES = Path(__file__).resolve().parents[1] / "data" / "fixtures"


def test_normalize_equity_frame_from_fixture_csv() -> None:
    raw = pd.read_csv(FIXTURES / "equity_spy_sample.csv")
    bars = normalize_equity_frame(raw, default_symbol="SPY")
    assert list(bars.columns) == ["timestamp", "open", "high", "low", "close", "volume", "symbol"]
    assert bars["symbol"].unique().tolist() == ["SPY"]
    assert len(bars) == 5
    assert bars["timestamp"].is_monotonic_increasing


def test_loader_reads_csv_export(tmp_path: Path) -> None:
    src = FIXTURES / "equity_spy_sample.csv"
    (tmp_path / "SPY.csv").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    loader = RobinhoodLoader(tmp_path)
    assert loader.list_symbols() == ["SPY"]
    bars = loader.load_symbol("spy")
    assert bars.iloc[0]["close"] == pytest.approx(511.30)


def test_loader_missing_symbol_raises(tmp_path: Path) -> None:
    (tmp_path / "QQQ.csv").write_text(
        "timestamp,open,high,low,close,volume\n2024-01-02,1,1,1,1,1\n",
        encoding="utf-8",
    )
    loader = RobinhoodLoader(tmp_path)
    with pytest.raises(FileNotFoundError):
        loader.load_symbol("SPY")
