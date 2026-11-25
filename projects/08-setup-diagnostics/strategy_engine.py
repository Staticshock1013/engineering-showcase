"""Placeholder NQ setups and the trade log they write.

Replace ``signals_breakout`` and ``signals_mean_reversion`` with real rules.
Everything downstream only needs the trade schema. PnL is in index points.
NQ is $20 per point; that conversion is left to the dashboard.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time
from pathlib import Path

import numpy as np
import polars as pl

TICK = 0.25
POINT_VALUE_USD = 20.0
COMMISSION_PER_SIDE_USD = 2.50
SLIPPAGE_TICKS_PER_SIDE = 1
COST_POINTS = 2 * (COMMISSION_PER_SIDE_USD / POINT_VALUE_USD + SLIPPAGE_TICKS_PER_SIDE * TICK)

BREAKOUT_TARGET_R = 2.5
MR_EXTENSION_POINTS = 12.0
MR_STOP_POINTS = 8.0
TIME_EXIT = time(15, 55)
BREAKOUT_START = time(9, 45)
BREAKOUT_END = time(11, 0)

TRADE_COLUMNS = [
    "trade_id",
    "setup_name",
    "direction",
    "entry_time",
    "exit_time",
    "entry_price",
    "exit_price",
    "pnl_net",
    "r_multiple",
    "commission_slippage",
    "hour_of_day",
    "day_of_week",
    "session",
    "atr_regime",
    "trend_regime",
    "mae",
    "mfe",
    "stop_price",
    "target_price",
    "risk_points",
    "exit_reason",
    "symbol",
    "pnl_gross",
]


@dataclass(frozen=True)
class Exit:
    index: int
    price: float
    reason: str
    mae: float
    mfe: float


def to_tick(price: float) -> float:
    return float(np.round(price / TICK) * TICK)


def walk_exit(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    start_index: int,
    end_index: int,
    direction: int,
    stop: float,
    target: float,
    entry: float,
) -> Exit:
    """Walk bars after the signal. Same-bar stop and target fills the stop.

    MAE and MFE are positive point distances. On a dual hit, MFE does not
    take credit for the favorable extreme of that bar.
    """
    mae = 0.0
    mfe = 0.0
    last = min(end_index, len(close) - 1)
    for index in range(start_index, last + 1):
        if direction == 1:
            stop_hit = low[index] <= stop
            target_hit = high[index] >= target
            adverse = entry - low[index]
            favorable = high[index] - entry
        else:
            stop_hit = high[index] >= stop
            target_hit = low[index] <= target
            adverse = high[index] - entry
            favorable = entry - low[index]
        if stop_hit and target_hit:
            mae = max(mae, abs(entry - stop), adverse)
            return Exit(index, stop, "stop", mae, mfe)
        if stop_hit:
            mae = max(mae, adverse)
            return Exit(index, stop, "stop", mae, mfe)
        if target_hit:
            mfe = max(mfe, favorable)
            return Exit(index, target, "target", mae, mfe)
        mae = max(mae, adverse)
        mfe = max(mfe, favorable)
    return Exit(last, float(close[last]), "time", mae, mfe)


def label_volatility_regimes(values: list[float]) -> list[str]:
    """Terciles of a trailing 60-session window. Short history is Med."""
    labels: list[str] = []
    history: list[float] = []
    for value in values:
        history.append(float(value))
        window = np.asarray(history[-60:], dtype=float)
        if window.size < 8:
            labels.append("Med")
            continue
        q1, q2 = np.quantile(window, [1 / 3, 2 / 3])
        # Upper edge is exclusive so a repeated top value is High, not Med.
        if value <= q1:
            labels.append("Low")
        elif value < q2:
            labels.append("Med")
        else:
            labels.append("High")
    return labels


def _completed_ema(bars: pl.DataFrame) -> pl.DataFrame:
    """20-period EMA of completed 15-minute closes, visible only after the bar closes."""
    bars15 = (
        bars.group_by_dynamic(
            "timestamp",
            every="15m",
            group_by="ticker",
            closed="left",
            label="left",
        )
        .agg(pl.col("close").last())
        .sort("timestamp")
        .with_columns(
            pl.col("close").ewm_mean(span=20, adjust=False).over("ticker").alias("ema_15m"),
            (pl.col("timestamp") + pl.duration(minutes=15)).alias("available_at"),
        )
        .with_columns(pl.col("available_at").cast(bars.schema["timestamp"]))
        .sort(["ticker", "available_at"])
    )
    ordered = bars.sort(["ticker", "timestamp"])
    return ordered.join_asof(
        bars15.select("ticker", "available_at", "ema_15m"),
        left_on="timestamp",
        right_on="available_at",
        by="ticker",
        strategy="backward",
        check_sortedness=False,
    )


def _session_vwap(bars: pl.DataFrame) -> pl.DataFrame:
    typical = (pl.col("high") + pl.col("low") + pl.col("close")) / 3
    return bars.with_columns(
        (
            (typical * pl.col("volume")).cum_sum().over(["ticker", "session_end_date"])
            / pl.col("volume").cum_sum().over(["ticker", "session_end_date"])
        ).alias("vwap")
    )


def _morning_range_regimes(bars: pl.DataFrame) -> pl.DataFrame:
    """Volatility tercile from the 08:00–09:30 ET range, known before 09:45."""
    morning = bars.filter(
        ((pl.col("timestamp").dt.hour() == 8) | ((pl.col("timestamp").dt.hour() == 9) & (pl.col("timestamp").dt.minute() < 30)))
    )
    ranges = (
        morning.group_by(["ticker", "session_end_date"])
        .agg((pl.col("high").max() - pl.col("low").min()).alias("morning_range"))
        .sort(["ticker", "session_end_date"])
    )
    labeled_frames = []
    for ticker in ranges["ticker"].unique().sort().to_list():
        part = ranges.filter(pl.col("ticker") == ticker)
        labels = label_volatility_regimes(part["morning_range"].to_list())
        labeled_frames.append(part.with_columns(pl.Series("atr_regime", labels)))
    labeled = pl.concat(labeled_frames) if labeled_frames else ranges.with_columns(pl.lit("Med").alias("atr_regime"))
    return labeled.select("ticker", "session_end_date", "atr_regime", "morning_range")


def prepare_features(bars: pl.DataFrame) -> pl.DataFrame:
    """Add VWAP, completed 15-minute EMA, opening range, and volatility regime."""
    featured = _session_vwap(bars.sort(["ticker", "timestamp"]))
    featured = _completed_ema(featured)
    opening = featured.filter(
        (pl.col("timestamp").dt.hour() == 9)
        & (pl.col("timestamp").dt.minute() >= 30)
        & (pl.col("timestamp").dt.minute() < 45)
    )
    or_levels = opening.group_by(["ticker", "session_end_date"]).agg(
        pl.col("high").max().alias("or_high"),
        pl.col("low").min().alias("or_low"),
    )
    regimes = _morning_range_regimes(featured)
    featured = featured.join(or_levels, on=["ticker", "session_end_date"], how="left")
    featured = featured.join(regimes, on=["ticker", "session_end_date"], how="left")
    return featured.with_columns(
        pl.when(pl.col("ema_15m").is_null())
        .then(pl.lit("unknown"))
        .when(pl.col("close") > pl.col("ema_15m"))
        .then(pl.lit("above"))
        .otherwise(pl.lit("below"))
        .alias("trend_regime")
    )


def _in_time(hours: np.ndarray, minutes: np.ndarray, start: time, end: time) -> np.ndarray:
    now = hours * 60 + minutes
    return (now >= start.hour * 60 + start.minute) & (now < end.hour * 60 + end.minute)


def signals_breakout(featured: pl.DataFrame) -> np.ndarray:
    """First 09:45–11:00 close through the opening range, aligned with the 15m EMA.

    Long when close > OR high and trend_regime is above. Short when close < OR
    low and trend_regime is below. Placeholder: one signal column of +1/0/-1,
    later reduced to the first signal of each session.
    """
    hours = featured["timestamp"].dt.hour().cast(pl.Int32).to_numpy()
    minutes = featured["timestamp"].dt.minute().cast(pl.Int32).to_numpy()
    window = _in_time(hours, minutes, BREAKOUT_START, BREAKOUT_END)
    close = featured["close"].to_numpy()
    or_high = featured["or_high"].to_numpy()
    or_low = featured["or_low"].to_numpy()
    trend = featured["trend_regime"].to_numpy()
    long = window & np.isfinite(or_high) & (close > or_high) & (trend == "above")
    short = window & np.isfinite(or_low) & (close < or_low) & (trend == "below")
    signal = np.zeros(featured.height, dtype=np.int8)
    signal[long] = 1
    signal[short] = -1
    return signal


def signals_mean_reversion(featured: pl.DataFrame) -> np.ndarray:
    """Fade a 12-point VWAP extension during the midday session.

    No trend filter on purpose: the failure tab should show when fading a
    trend loses. Long below VWAP, short above. Placeholder threshold.
    """
    session = featured["session"].to_numpy()
    close = featured["close"].to_numpy()
    vwap = featured["vwap"].to_numpy()
    extension = close - vwap
    midday = session == "Midday"
    signal = np.zeros(featured.height, dtype=np.int8)
    signal[midday & (extension <= -MR_EXTENSION_POINTS)] = 1
    signal[midday & (extension >= MR_EXTENSION_POINTS)] = -1
    return signal


def _first_signal_per_session(session_ids: np.ndarray, signal: np.ndarray) -> list[int]:
    picks: list[int] = []
    seen: set[object] = set()
    for index, flag in enumerate(signal):
        if flag == 0:
            continue
        key = session_ids[index]
        if key in seen:
            continue
        seen.add(key)
        picks.append(index)
    return picks


def _deadline_index(session_ids: np.ndarray, hours: np.ndarray, minutes: np.ndarray, session_id: object) -> int:
    mask = session_ids == session_id
    indexes = np.flatnonzero(mask)
    clock = hours[indexes] * 60 + minutes[indexes]
    eligible = indexes[clock <= TIME_EXIT.hour * 60 + TIME_EXIT.minute]
    if len(eligible) == 0:
        return int(indexes[-1])
    return int(eligible[-1])


def _simulate_setup(
    featured: pl.DataFrame,
    setup_name: str,
    signal: np.ndarray,
    *,
    target_mode: str,
) -> list[dict[str, object]]:
    session_ids = featured["session_end_date"].to_numpy()
    hours = featured["timestamp"].dt.hour().cast(pl.Int32).to_numpy()
    minutes = featured["timestamp"].dt.minute().cast(pl.Int32).to_numpy()
    high = featured["high"].to_numpy()
    low = featured["low"].to_numpy()
    close = featured["close"].to_numpy()
    timestamps = featured["timestamp"].to_list()
    trades: list[dict[str, object]] = []
    for index in _first_signal_per_session(session_ids, signal):
        direction = int(signal[index])
        entry = float(close[index])
        if target_mode == "r":
            if direction == 1:
                stop = float(featured["or_low"][index])
            else:
                stop = float(featured["or_high"][index])
            risk = abs(entry - stop)
            if risk < 2 * TICK or not np.isfinite(risk):
                continue
            target = entry + direction * BREAKOUT_TARGET_R * risk
        else:
            vwap = float(featured["vwap"][index])
            stop = entry - direction * MR_STOP_POINTS
            target = vwap
            risk = abs(entry - stop)
            if risk < 2 * TICK:
                continue
            # Target must sit on the profitable side of entry.
            if direction == 1 and target <= entry:
                continue
            if direction == -1 and target >= entry:
                continue
        stop = to_tick(stop)
        target = to_tick(target)
        risk = abs(entry - stop)
        deadline = _deadline_index(session_ids, hours, minutes, session_ids[index])
        if index + 1 > deadline:
            continue
        outcome = walk_exit(high, low, close, index + 1, deadline, direction, stop, target, entry)
        gross = direction * (outcome.price - entry)
        net = gross - COST_POINTS
        session_day = session_ids[index]
        session_key = session_day.isoformat() if isinstance(session_day, date) else str(session_day)
        trades.append(
            {
                "trade_id": f"{setup_name}-{session_key}",
                "setup_name": setup_name,
                "direction": "Long" if direction == 1 else "Short",
                "entry_time": timestamps[index],
                "exit_time": timestamps[outcome.index],
                "entry_price": entry,
                "exit_price": float(outcome.price),
                "pnl_net": float(net),
                "r_multiple": float(net / risk),
                "commission_slippage": COST_POINTS,
                "hour_of_day": int(hours[index]),
                "day_of_week": featured["day_of_week"][index],
                "session": featured["session"][index],
                "atr_regime": featured["atr_regime"][index] or "Med",
                "trend_regime": featured["trend_regime"][index],
                "mae": float(max(outcome.mae, 0.0)),
                "mfe": float(max(outcome.mfe, 0.0)),
                "stop_price": stop,
                "target_price": target,
                "risk_points": float(risk),
                "exit_reason": outcome.reason,
                "symbol": featured["ticker"][index],
                "pnl_gross": float(gross),
            }
        )
    return trades


def run_setups(bars: pl.DataFrame) -> pl.DataFrame:
    """Run both placeholder setups and return the trade log."""
    featured = prepare_features(bars)
    breakout = signals_breakout(featured)
    reversion = signals_mean_reversion(featured)
    rows = _simulate_setup(featured, "Setup_A_Breakout", breakout, target_mode="r")
    rows.extend(_simulate_setup(featured, "Setup_B_MeanReversion", reversion, target_mode="vwap"))
    if not rows:
        return pl.DataFrame(schema={name: pl.Utf8 for name in TRADE_COLUMNS})
    frame = pl.DataFrame(rows).select(TRADE_COLUMNS)
    return frame.sort("entry_time")


def write_trades(trades: pl.DataFrame, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    trades.write_parquet(path)
    return path


def default_trades_path() -> Path:
    return Path(__file__).resolve().parent / "outputs" / "trades.parquet"
