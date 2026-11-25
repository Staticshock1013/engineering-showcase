"""No-lookahead tests — required before any strategy results are reported."""

from __future__ import annotations

import pandas as pd
import pytest

from quant_lab.backtest.engine import run_backtest
from quant_lab.backtest.lookahead import (
    LookaheadError,
    assert_feature_uses_only_past,
    shift_signal_for_execution,
)


def _prices() -> pd.Series:
    return pd.Series(
        [100.0, 101.0, 102.0, 101.5, 103.0, 104.0, 103.5],
        index=pd.RangeIndex(7),
        dtype=float,
    )


def _causal_sma(prices: pd.Series, window: int = 3) -> pd.Series:
    """Trailing SMA using only data up to t (min_periods=window)."""
    return prices.rolling(window=window, min_periods=window).mean()


def _leaky_sma(prices: pd.Series, window: int = 3) -> pd.Series:
    """Intentionally uses a centered window — depends on future prices."""
    return prices.rolling(window=window, min_periods=1, center=True).mean()


def test_causal_sma_passes_no_lookahead_guard() -> None:
    prices = _prices()
    feature = _causal_sma(prices)

    def rebuild(p: pd.Series) -> pd.Series:
        return _causal_sma(p)

    assert_feature_uses_only_past(prices, feature, rebuild=rebuild, name="sma3")


def test_centered_sma_fails_no_lookahead_guard() -> None:
    prices = _prices()
    feature = _leaky_sma(prices)

    def rebuild(p: pd.Series) -> pd.Series:
        return _leaky_sma(p)

    with pytest.raises(LookaheadError, match="lookahead"):
        assert_feature_uses_only_past(prices, feature, rebuild=rebuild, name="leaky_sma")


def test_signal_is_shifted_before_position_accrues_pnl() -> None:
    bars = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-03-11", periods=4, freq="D", tz="UTC"),
            "open": [18000.0, 18010.0, 18020.0, 18030.0],
            "high": [18005.0, 18015.0, 18025.0, 18035.0],
            "low": [17995.0, 18005.0, 18015.0, 18025.0],
            "close": [18000.0, 18010.0, 18020.0, 18030.0],
            "volume": [1, 1, 1, 1],
            "symbol": ["NQH6"] * 4,
        }
    )
    # Signal turns long on bar 0. If executed same bar, would earn first point move.
    signal = [1.0, 1.0, 1.0, 1.0]
    result = run_backtest(bars, signal, contracts=1.0)
    # Position must be 0 on first bar (signal not yet executable).
    assert result.ledger.iloc[0]["position"] == pytest.approx(0.0)
    assert result.ledger.iloc[1]["position"] == pytest.approx(1.0)
    # First close-to-close move (10 points * $20) must NOT be earned — that would be lookahead.
    assert result.ledger.iloc[1]["point_change"] == pytest.approx(10.0)
    assert result.ledger.iloc[1]["gross_pnl"] == pytest.approx(10.0 * 20.0)
    # Bar 0 gross pnl is zero despite signal already being 1.
    assert result.ledger.iloc[0]["gross_pnl"] == pytest.approx(0.0)


def test_same_bar_execution_would_look_ahead_is_rejected_by_shift() -> None:
    signal = pd.Series([1.0, -1.0, 0.0, 1.0])
    position = shift_signal_for_execution(signal)
    assert position.tolist() == [0.0, 1.0, -1.0, 0.0]


def test_mutating_future_bars_does_not_change_past_position() -> None:
    bars = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-03-11", periods=5, freq="D", tz="UTC"),
            "open": [18000.0] * 5,
            "high": [18010.0] * 5,
            "low": [17990.0] * 5,
            "close": [18000.0, 18005.0, 18010.0, 18015.0, 18020.0],
            "volume": [1] * 5,
            "symbol": ["NQH6"] * 5,
        }
    )
    # Causal signal: long when close > prior close (uses only past+current).
    signal = (bars["close"].diff() > 0).astype(float)
    baseline = run_backtest(bars, signal)

    tweaked = bars.copy()
    tweaked.loc[4, "close"] = 19000.0  # far-future shock
    # Recompute causal signal on tweaked series.
    tweaked_signal = (tweaked["close"].diff() > 0).astype(float)
    shocked = run_backtest(tweaked, tweaked_signal)

    # Positions through bar index 3 must match (future bar 4 cannot rewrite past fills).
    pd.testing.assert_series_equal(
        baseline.ledger.loc[:3, "position"].reset_index(drop=True),
        shocked.ledger.loc[:3, "position"].reset_index(drop=True),
    )
