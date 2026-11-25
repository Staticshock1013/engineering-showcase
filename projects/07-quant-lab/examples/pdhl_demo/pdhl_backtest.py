"""SPY Prior-Day High/Low (PDHL) failed-break → retest demo.

Portfolio demo only. Underlying SPY points — no options pricing.
Not the frozen ``experiments/spy-pdhl-v1`` pass/fail evaluation.

Research only. No live trading / order placement.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

# Explicit demo cost in underlying points (round-trip).
ROUND_TRIP_COST_POINTS = 0.14


@dataclass(frozen=True)
class Trade:
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    entry_price: float
    exit_price: float
    direction: int  # -1 short (failed PDH break fade)
    pdh: float
    pdl: float
    gross_points: float
    net_points: float


def prior_day_levels(daily: pd.DataFrame) -> pd.DataFrame:
    """Map each session date to the previous session's high/low."""
    frame = daily.sort_values("session_date").reset_index(drop=True).copy()
    frame["pdh"] = frame["high"].shift(1)
    frame["pdl"] = frame["low"].shift(1)
    return frame


def run_failed_break_retest(
    minutes: pd.DataFrame,
    *,
    round_trip_cost_points: float = ROUND_TRIP_COST_POINTS,
) -> list[Trade]:
    """Detect PDH failed breaks and trade the retest short to PDL.

    Rules (demo):
    1. Build prior-day high/low from daily aggregates of the minute bars.
    2. Failed break: within a session, price trades strictly above PDH, then
       a later bar trades back at or below PDH.
    3. Retest entry: after the fail is confirmed, the first subsequent touch
       of PDH from below (high >= PDH and close <= PDH) enters short at PDH.
    4. Exit: first bar whose low <= PDL exits at PDL (target). If never hit,
       exit at session close (still one trade for bookkeeping).
    5. ``net_points = gross_points - round_trip_cost_points``.
    """
    if minutes.empty:
        return []

    bars = minutes.copy()
    bars["timestamp"] = pd.to_datetime(bars["timestamp"], utc=True)
    bars = bars.sort_values("timestamp").reset_index(drop=True)
    bars["session_date"] = bars["timestamp"].dt.tz_convert("America/New_York").dt.strftime(
        "%Y-%m-%d"
    )

    daily = (
        bars.groupby("session_date", sort=True)
        .agg(
            open=("open", "first"),
            high=("high", "max"),
            low=("low", "min"),
            close=("close", "last"),
        )
        .reset_index()
    )
    levels = prior_day_levels(daily)
    level_map = levels.set_index("session_date")[["pdh", "pdl"]].to_dict("index")

    trades: list[Trade] = []

    for session_date, session in bars.groupby("session_date", sort=True):
        lvl = level_map.get(session_date)
        if lvl is None or pd.isna(lvl["pdh"]) or pd.isna(lvl["pdl"]):
            continue
        pdh = float(lvl["pdh"])
        pdl = float(lvl["pdl"])
        session = session.reset_index(drop=True)

        broke_above = False
        failed = False
        entered = False
        entry_time = None
        entry_price = None

        for row in session.itertuples(index=False):
            if not broke_above and float(row.high) > pdh:
                broke_above = True
                continue

            if broke_above and not failed and float(row.low) <= pdh:
                failed = True
                continue

            if failed and not entered and float(row.high) >= pdh and float(row.close) <= pdh:
                entered = True
                entry_time = row.timestamp
                entry_price = pdh
                continue

            if entered and float(row.low) <= pdl:
                exit_price = pdl
                exit_time = row.timestamp
                # Short: gross = entry - exit
                gross = float(entry_price) - exit_price
                trades.append(
                    Trade(
                        entry_time=entry_time,
                        exit_time=exit_time,
                        entry_price=float(entry_price),
                        exit_price=exit_price,
                        direction=-1,
                        pdh=pdh,
                        pdl=pdl,
                        gross_points=gross,
                        net_points=gross - round_trip_cost_points,
                    )
                )
                break
        else:
            if entered:
                last = session.iloc[-1]
                exit_price = float(last["close"])
                gross = float(entry_price) - exit_price
                trades.append(
                    Trade(
                        entry_time=entry_time,
                        exit_time=last["timestamp"],
                        entry_price=float(entry_price),
                        exit_price=exit_price,
                        direction=-1,
                        pdh=pdh,
                        pdl=pdl,
                        gross_points=gross,
                        net_points=gross - round_trip_cost_points,
                    )
                )

    return trades


def main() -> None:
    fixture = Path(__file__).resolve().parent / "fixtures" / "failed_break_retest.csv"
    minutes = pd.read_csv(fixture)
    trades = run_failed_break_retest(minutes)
    print(f"trades={len(trades)} cost_points={ROUND_TRIP_COST_POINTS}")
    for t in trades:
        print(
            f"{t.entry_time} -> {t.exit_time} short@{t.entry_price} "
            f"exit@{t.exit_price} gross={t.gross_points:.4f} net={t.net_points:.4f}"
        )


if __name__ == "__main__":
    main()
