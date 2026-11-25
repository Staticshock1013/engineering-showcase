"""Canonical bar schema used across loaders and the cache."""

from __future__ import annotations

from typing import Final

BAR_COLUMNS: Final[tuple[str, ...]] = (
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "symbol",
)

SESSION_VOLUME_COLUMNS: Final[tuple[str, ...]] = (
    "session_end_date",
    "ticker",
    "volume",
    "open",
    "high",
    "low",
    "close",
)
