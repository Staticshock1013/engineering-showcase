"""No-lookahead guards for features and signals (NQ research)."""

from __future__ import annotations

import numpy as np
import pandas as pd


class LookaheadError(ValueError):
    """Raised when a series depends on future information."""


def assert_feature_uses_only_past(
    prices: pd.Series,
    feature: pd.Series,
    *,
    rebuild,
    name: str = "feature",
) -> None:
    """Fail if ``feature[t]`` changes when future prices after ``t`` are altered.

    ``rebuild`` is ``callable(prices) -> pd.Series`` that recomputes the feature
    from a price series. For each time ``t``, future prices are perturbed and the
    feature value at ``t`` must stay identical.
    """
    if len(prices) != len(feature):
        raise LookaheadError(f"{name}: length mismatch with prices")
    if not prices.index.equals(feature.index):
        raise LookaheadError(f"{name}: index must align with prices")

    baseline = feature.to_numpy(dtype=float, copy=True)
    values = prices.to_numpy(dtype=float, copy=True)
    rng = np.random.default_rng(0)

    for t in range(len(prices) - 1):
        perturbed = values.copy()
        # Scramble only the future path after t.
        noise = rng.normal(0.0, 50.0, size=len(prices) - t - 1)
        perturbed[t + 1 :] = perturbed[t + 1 :] + noise
        rebuilt = rebuild(pd.Series(perturbed, index=prices.index))
        if not np.isclose(rebuilt.iloc[t], baseline[t], equal_nan=True):
            raise LookaheadError(
                f"{name}: value at t={t} changed when future prices were perturbed "
                "(lookahead)"
            )


def shift_signal_for_execution(signal: pd.Series) -> pd.Series:
    """Map end-of-bar signal to next-bar position (classic no-lookahead fill).

    ``signal[t]`` is known after bar ``t`` closes and becomes the position held
    over bar ``t+1``. Position on the first bar is 0.
    """
    return signal.shift(1).fillna(0.0)
