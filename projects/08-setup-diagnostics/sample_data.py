"""Synthetic NQ front-month minute bars for the dashboard.

The path is fictional and labeled synthetic. It uses the same columns as
``nq_front_1m_2023_2026.parquet`` so the loader can be exercised without the
Mac copy of the Massive files. Day types are planted so the placeholder
setups win and lose in different volatility regimes.
"""

from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import polars as pl

ET = ZoneInfo("America/New_York")
SAMPLE_TICKER = "NQH4"
SAMPLE_SESSIONS = 40
SAMPLE_START = date(2024, 1, 2)

MANIFEST_NAME = "sample_nq_1m.manifest.json"


def weekday_dates(start: date, count: int) -> list[date]:
    """Return ``count`` weekdays beginning at ``start`` (inclusive)."""
    days: list[date] = []
    cursor = start
    while len(days) < count:
        if cursor.weekday() < 5:
            days.append(cursor)
        cursor += timedelta(days=1)
    return days


def day_kind(session_day: date) -> str:
    """Planted regime for a session date. Monday=0."""
    return {
        0: "chop",
        1: "trend_up",
        2: "chop",
        3: "trend_down",
        4: "chop_high",
    }[session_day.weekday()]


def _trend_up_offset(hour: int, minute: int) -> float:
    now = hour * 60 + minute
    if hour >= 18 or hour < 9 or (hour == 9 and minute < 30):
        return 0.0
    if hour == 9 and minute < 45:
        return (minute - 30) * (8 / 14)
    rally_end = 10 * 60 + 30
    if now <= rally_end:
        elapsed = now - (9 * 60 + 45)
        return 10 + elapsed * ((48 - 10) / 45)
    if now < 14 * 60:
        elapsed = now - rally_end
        span = 14 * 60 - rally_end
        return 48 + elapsed * (22 / span)
    return 70.0


def _chop_offset(hour: int, minute: int, *, deep: bool) -> float:
    if hour >= 18 or hour < 9 or (hour == 9 and minute < 30):
        return 4.0
    if hour == 9 and minute < 45:
        return (minute - 30) * (10 / 14)
    if hour == 9:
        if minute <= 52:
            return 11 + (minute - 45) * ((30 - 11) / 7)
        return 30 - (minute - 52) * (8 / 7)
    if hour == 10 and minute < 50:
        return 22 - (minute / 49) * 26
    if hour < 11:
        return -2.0
    if hour == 11 and 15 <= minute <= 50:
        floor = -30.0 if deep else -14.0
        if minute <= 32:
            return 2 + (minute - 15) / 17 * (floor - 2)
        return floor + (minute - 32) / 18 * ((-4) - floor)
    if hour == 11:
        return 2.0
    if hour == 12 and minute < 40:
        return -4 + (minute / 39) * 8
    return 4.0


def close_offset(kind: str, hour: int, minute: int) -> float:
    """Intraday close offset in index points, relative to the session base."""
    if kind == "trend_up":
        return _trend_up_offset(hour, minute)
    if kind == "trend_down":
        return -_trend_up_offset(hour, minute)
    if kind == "chop_high":
        return _chop_offset(hour, minute, deep=True)
    return _chop_offset(hour, minute, deep=False)


def bar_volume(kind: str, hour: int) -> int:
    if kind.startswith("trend"):
        return 50 if 9 <= hour < 16 else 180
    if 9 <= hour < 11:
        return 800
    if 11 <= hour < 14:
        return 300
    return 160


def _quantize(price: float) -> float:
    return round(price * 4) / 4


def _session_minutes(session_day: date) -> list[datetime]:
    """18:00 ET on the prior evening through 16:59 ET on ``session_day``."""
    start = datetime.combine(session_day - timedelta(days=1), time(18, 0), tzinfo=ET)
    return [start + timedelta(minutes=i) for i in range(23 * 60)]


def build_sample_frame(
    *,
    sessions: int = SAMPLE_SESSIONS,
    start: date = SAMPLE_START,
) -> pl.DataFrame:
    """Build a front-month-shaped 1-minute frame. Prices are index points."""
    days = weekday_dates(start, sessions)
    tickers: list[str] = []
    session_dates: list[date] = []
    window_starts: list[int] = []
    opens: list[float] = []
    highs: list[float] = []
    lows: list[float] = []
    closes: list[float] = []
    volumes: list[int] = []

    for index, session_day in enumerate(days):
        kind = day_kind(session_day)
        base = 18000.0 + index * 2.0
        previous = _quantize(base + close_offset(kind, 18, 0))
        for stamp in _session_minutes(session_day):
            offset = close_offset(kind, stamp.hour, stamp.minute)
            close_px = _quantize(base + offset)
            open_px = previous
            high_px = max(open_px, close_px)
            low_px = min(open_px, close_px)
            if stamp.hour == 8 and stamp.minute == 10:
                if kind.startswith("trend"):
                    high_px = max(high_px, _quantize(base + 25))
                    low_px = min(low_px, _quantize(base - 1))
                elif kind == "chop_high":
                    high_px = max(high_px, _quantize(base + 12))
            high_px = _quantize(high_px + 0.25)
            low_px = _quantize(low_px - 0.25)
            utc = stamp.astimezone(timezone.utc)
            tickers.append(SAMPLE_TICKER)
            session_dates.append(session_day)
            window_starts.append(int(utc.timestamp()) * 1_000_000_000)
            opens.append(open_px)
            highs.append(high_px)
            lows.append(low_px)
            closes.append(close_px)
            volumes.append(bar_volume(kind, stamp.hour))
            previous = close_px

    return pl.DataFrame(
        {
            "ticker": tickers,
            "session_end_date": session_dates,
            "window_start": window_starts,
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
        }
    )


def write_sample(path: Path, *, sessions: int = SAMPLE_SESSIONS) -> Path:
    """Write the synthetic parquet and a manifest that marks it as synthetic."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = build_sample_frame(sessions=sessions)
    frame.write_parquet(path)
    manifest = {
        "synthetic": True,
        "ticker": SAMPLE_TICKER,
        "sessions": sessions,
        "rows": frame.height,
        "note": (
            "Fictional NQ minute bars for the setup-diagnostics dashboard. "
            "Not Massive market data."
        ),
    }
    path.with_name(MANIFEST_NAME).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path
