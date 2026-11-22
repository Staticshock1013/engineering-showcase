"""Front-month futures roll: highest session volume wins.

Massive does not publish continuous NQ series. Per Massive docs, pick the
contract with the most volume in each session, then join sessions. Prices are
unadjusted by default (jumps at rolls are expected); optional back-adjust is
available for return studies.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from quant_lab.data.schema import SESSION_VOLUME_COLUMNS


@dataclass(frozen=True)
class RollEvent:
    """A session where the front-month ticker changes."""

    session_end_date: str
    from_ticker: str
    to_ticker: str
    from_close: float
    to_close: float


@dataclass(frozen=True)
class ContinuousSeries:
    """Front-month series plus roll metadata."""

    bars: pd.DataFrame
    rolls: tuple[RollEvent, ...]
    adjusted: bool


def select_front_month(session_volumes: pd.DataFrame) -> pd.DataFrame:
    """For each session_end_date, keep the row with the highest volume.

    Ties break by ticker ascending for determinism.
    """
    required = ("session_end_date", "ticker", "volume")
    missing = [c for c in required if c not in session_volumes.columns]
    if missing:
        raise ValueError(f"session_volumes missing columns: {missing}")
    if session_volumes.empty:
        return session_volumes.copy()

    ordered = session_volumes.sort_values(
        ["session_end_date", "volume", "ticker"],
        ascending=[True, False, True],
        kind="mergesort",
    )
    front = ordered.groupby("session_end_date", as_index=False, sort=True).head(1)
    return front.reset_index(drop=True)


def detect_rolls(front_month: pd.DataFrame) -> list[RollEvent]:
    """Emit a RollEvent whenever the winning ticker changes between sessions."""
    if front_month.empty:
        return []
    required = {"session_end_date", "ticker", "close"}
    missing = required - set(front_month.columns)
    if missing:
        raise ValueError(f"front_month missing columns: {sorted(missing)}")

    events: list[RollEvent] = []
    prev_ticker: str | None = None
    prev_close: float | None = None
    for row in front_month.sort_values("session_end_date").itertuples(index=False):
        ticker = str(row.ticker)
        close = float(row.close)
        session = str(row.session_end_date)
        if prev_ticker is not None and ticker != prev_ticker:
            events.append(
                RollEvent(
                    session_end_date=session,
                    from_ticker=prev_ticker,
                    to_ticker=ticker,
                    from_close=float(prev_close) if prev_close is not None else float("nan"),
                    to_close=close,
                )
            )
        prev_ticker = ticker
        prev_close = close
    return events


def build_continuous_series(
    session_volumes: pd.DataFrame,
    *,
    back_adjust: bool = False,
) -> ContinuousSeries:
    """Build an unadjusted (or Panama back-adjusted) front-month daily series."""
    missing = [c for c in SESSION_VOLUME_COLUMNS if c not in session_volumes.columns]
    if missing:
        raise ValueError(f"session_volumes missing columns: {missing}")

    front = select_front_month(session_volumes)
    rolls = detect_rolls(front)
    bars = front.rename(columns={"ticker": "symbol"}).copy()
    bars["timestamp"] = pd.to_datetime(bars["session_end_date"], utc=True)
    keep = [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "symbol",
        "session_end_date",
    ]
    bars = bars.loc[:, keep]

    if back_adjust and rolls:
        # Panama adjustment: add cumulative close gaps so pre-roll history is level-shifted.
        adjust = 0.0
        adjusted_closes: list[float] = []
        # Walk newest → oldest accumulating gaps, then reverse.
        roll_by_date = {r.session_end_date: r for r in rolls}
        for row in bars.iloc[::-1].itertuples(index=False):
            session = str(row.session_end_date)
            close = float(row.close) + adjust
            adjusted_closes.append(close)
            if session in roll_by_date:
                event = roll_by_date[session]
                adjust += event.to_close - event.from_close
        bars = bars.copy()
        bars["close"] = list(reversed(adjusted_closes))
        # Shift OHLC by the same per-row close delta for a consistent level.
        original_close = front["close"].astype(float).to_numpy()
        delta = bars["close"].to_numpy() - original_close
        for col in ("open", "high", "low"):
            bars[col] = front[col].astype(float).to_numpy() + delta

    return ContinuousSeries(
        bars=bars.reset_index(drop=True),
        rolls=tuple(rolls),
        adjusted=back_adjust,
    )
