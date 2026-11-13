"""Deterministic, dependency-free summaries for environmental observations."""

from __future__ import annotations

from collections import defaultdict
from statistics import mean, median
from typing import Any, Iterable


def summarize(values: Iterable[float]) -> dict[str, float | int | None]:
    """Return a stable descriptive summary; empty inputs have null statistics."""
    series = list(values)
    if not series:
        return {"count": 0, "mean": None, "median": None, "minimum": None, "maximum": None}
    return {
        "count": len(series),
        "mean": round(mean(series), 4),
        "median": round(median(series), 4),
        "minimum": min(series),
        "maximum": max(series),
    }


def indicator_summary(
    observations: Iterable[dict[str, Any]], indicator: str
) -> dict[str, float | int | None]:
    """Summarize records for one registry key."""
    return summarize(row["value"] for row in observations if row["indicator"] == indicator)


def regional_means(
    observations: Iterable[dict[str, Any]], indicator: str
) -> list[dict[str, float | str]]:
    """Average an indicator by region in a predictable alphabetical order."""
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in observations:
        if row["indicator"] == indicator:
            grouped[row["region"]].append(row["value"])
    return [
        {"region": region, "mean_value": round(mean(grouped[region]), 4)}
        for region in sorted(grouped)
    ]
