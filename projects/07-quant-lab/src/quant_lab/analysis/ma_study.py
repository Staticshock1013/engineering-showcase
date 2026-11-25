"""NQ moving-average cross study vs random-entry baseline (research only)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from quant_lab.backtest.costs import FuturesCostModel
from quant_lab.features.moving_averages import ma_bundle

WindowName = Literal["development", "holdout"]

DEV_START = "2020-01-02"
DEV_END = "2023-12-29"
HOLDOUT_START = "2024-01-02"
HOLDOUT_END = "2024-12-31"

FAMILY_MEMBERS = {
    "ma20_family": ("price_cross_ma20_up", "price_cross_ma20_down"),
    "cross_family": ("golden_cross", "death_cross"),
}


@dataclass(frozen=True)
class EventStats:
    signal_id: str
    window: str
    n: int
    hit_rate: float
    mean_net_pnl: float
    baseline_hit_rate: float
    baseline_mean_net_pnl: float
    hit_rate_edge: float


def _cross_up(prev: pd.Series, curr: pd.Series) -> pd.Series:
    return (prev <= 0) & (curr > 0)


def _cross_down(prev: pd.Series, curr: pd.Series) -> pd.Series:
    return (prev >= 0) & (curr < 0)


def detect_signals(bars: pd.DataFrame) -> pd.DataFrame:
    """Return one row per bar with signal direction columns (0 if no event)."""
    frame = bars.sort_values("timestamp").reset_index(drop=True).copy()
    mas = ma_bundle(frame["close"])
    close = mas["close"]
    ma20 = mas["ma20"]
    ma50 = mas["ma50"]
    ma200 = mas["ma200"]

    vs20 = close - ma20
    vs_cross = ma50 - ma200

    signals = pd.DataFrame(
        {
            "timestamp": frame["timestamp"],
            "close": close,
            "ma20": ma20,
            "ma50": ma50,
            "ma200": ma200,
            "price_cross_ma20_up": np.where(
                _cross_up(vs20.shift(1), vs20), 1.0, 0.0
            ),
            "price_cross_ma20_down": np.where(
                _cross_down(vs20.shift(1), vs20), -1.0, 0.0
            ),
            "golden_cross": np.where(_cross_up(vs_cross.shift(1), vs_cross), 1.0, 0.0),
            "death_cross": np.where(
                _cross_down(vs_cross.shift(1), vs_cross), -1.0, 0.0
            ),
        }
    )
    # Forward one-session point change (known only after t+1; used for evaluation).
    signals["fwd_point_change"] = close.diff().shift(-1)
    return signals


def _window_mask(timestamps: pd.Series, start: str, end: str) -> pd.Series:
    ts = pd.to_datetime(timestamps, utc=True)
    return (ts >= pd.Timestamp(start, tz="UTC")) & (ts <= pd.Timestamp(end, tz="UTC"))


def slice_window(signals: pd.DataFrame, window: WindowName) -> pd.DataFrame:
    if window == "development":
        mask = _window_mask(signals["timestamp"], DEV_START, DEV_END)
    else:
        mask = _window_mask(signals["timestamp"], HOLDOUT_START, HOLDOUT_END)
    out = signals.loc[mask].copy()
    # Drop events without a forward return (last bar) or without MA readiness.
    return out


def _event_rows(signals: pd.DataFrame, signal_id: str) -> pd.DataFrame:
    direction = signals[signal_id]
    events = signals.loc[direction != 0.0, ["timestamp", "fwd_point_change"]].copy()
    events["direction"] = direction.loc[direction != 0.0].to_numpy()
    events = events.dropna(subset=["fwd_point_change"])
    return events.reset_index(drop=True)


def _hit_rate(direction: np.ndarray, fwd: np.ndarray) -> float:
    if len(direction) == 0:
        return float("nan")
    hits = (np.sign(fwd) == np.sign(direction)) & (fwd != 0.0)
    return float(hits.mean())


def _mean_net_pnl(
    direction: np.ndarray,
    fwd: np.ndarray,
    cost_model: FuturesCostModel,
) -> float:
    if len(direction) == 0:
        return float("nan")
    # One-session round trip: gross = direction * points * point_value; costs = 2 sides.
    gross = direction * fwd * cost_model.point_value
    net = gross - (2.0 * cost_model.cost_per_side_usd())
    return float(net.mean())


def evaluate_signal(
    signals: pd.DataFrame,
    signal_id: str,
    *,
    window: WindowName,
    rng_seed: int,
    cost_model: FuturesCostModel | None = None,
) -> EventStats:
    model = cost_model or FuturesCostModel(contract="NQ")
    if model.contract != "NQ":
        raise ValueError("ma-study is NQ-only")
    windowed = slice_window(signals, window)
    events = _event_rows(windowed, signal_id)
    direction = events["direction"].to_numpy(dtype=float)
    fwd = events["fwd_point_change"].to_numpy(dtype=float)
    hit = _hit_rate(direction, fwd)
    mean_net = _mean_net_pnl(direction, fwd, model)

    rng = np.random.default_rng(rng_seed)
    random_dir = rng.choice(np.array([1.0, -1.0]), size=len(direction))
    base_hit = _hit_rate(random_dir, fwd)
    base_net = _mean_net_pnl(random_dir, fwd, model)
    edge = hit - base_hit if len(direction) else float("nan")
    return EventStats(
        signal_id=signal_id,
        window=window,
        n=len(direction),
        hit_rate=hit,
        mean_net_pnl=mean_net,
        baseline_hit_rate=base_hit,
        baseline_mean_net_pnl=base_net,
        hit_rate_edge=edge,
    )


def evaluate_family(
    signals: pd.DataFrame,
    family: str,
    *,
    window: WindowName,
    rng_seed: int,
    cost_model: FuturesCostModel | None = None,
) -> EventStats:
    model = cost_model or FuturesCostModel(contract="NQ")
    members = FAMILY_MEMBERS[family]
    windowed = slice_window(signals, window)
    parts = [_event_rows(windowed, sid) for sid in members]
    events = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    if events.empty:
        return EventStats(
            signal_id=family,
            window=window,
            n=0,
            hit_rate=float("nan"),
            mean_net_pnl=float("nan"),
            baseline_hit_rate=float("nan"),
            baseline_mean_net_pnl=float("nan"),
            hit_rate_edge=float("nan"),
        )
    # Stable order by timestamp for reproducible baseline pairing.
    events = events.sort_values("timestamp").reset_index(drop=True)
    direction = events["direction"].to_numpy(dtype=float)
    fwd = events["fwd_point_change"].to_numpy(dtype=float)
    hit = _hit_rate(direction, fwd)
    mean_net = _mean_net_pnl(direction, fwd, model)
    rng = np.random.default_rng(rng_seed)
    random_dir = rng.choice(np.array([1.0, -1.0]), size=len(direction))
    base_hit = _hit_rate(random_dir, fwd)
    base_net = _mean_net_pnl(random_dir, fwd, model)
    return EventStats(
        signal_id=family,
        window=window,
        n=len(direction),
        hit_rate=hit,
        mean_net_pnl=mean_net,
        baseline_hit_rate=base_hit,
        baseline_mean_net_pnl=base_net,
        hit_rate_edge=hit - base_hit,
    )


def holdout_pass(family_stats: list[EventStats]) -> tuple[bool, str]:
    """Apply the frozen holdout threshold from SPEC.md."""
    reasons: list[str] = []
    for stats in family_stats:
        if stats.window != "holdout":
            continue
        if stats.n >= 30 and stats.hit_rate_edge >= 0.02:
            return True, (
                f"PASS via {stats.signal_id}: n={stats.n}, "
                f"edge={stats.hit_rate_edge:.4f}"
            )
        reasons.append(
            f"{stats.signal_id}: n={stats.n}, edge={stats.hit_rate_edge!r}"
        )
    return False, "FAIL holdout threshold; " + "; ".join(reasons)
