"""Causal moving averages (no centered / future windows)."""

from __future__ import annotations

import pandas as pd


def sma(close: pd.Series, window: int) -> pd.Series:
    """Trailing simple moving average using only data up to each timestamp."""
    if window < 1:
        raise ValueError("window must be >= 1")
    return close.astype(float).rolling(window=window, min_periods=window).mean()


def ma_bundle(close: pd.Series) -> pd.DataFrame:
    """Compute the pre-registered 20/50/200 SMAs."""
    return pd.DataFrame(
        {
            "close": close.astype(float),
            "ma20": sma(close, 20),
            "ma50": sma(close, 50),
            "ma200": sma(close, 200),
        },
        index=close.index,
    )
