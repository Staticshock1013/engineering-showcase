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


def linear_trend(
    years: Iterable[int], values: Iterable[float], confidence: float = 0.95
) -> dict[str, float | int]:
    """Fit an OLS linear trend with a two-sided slope confidence interval and p-value."""
    x, y = list(years), list(values)
    if len(x) != len(y) or len(x) < 3:
        raise ValueError("A trend requires at least three paired annual or seasonal observations.")
    if len(set(x)) != len(x):
        raise ValueError("Trend years must be unique.")
    if not 0 < confidence < 1:
        raise ValueError("Confidence must be between zero and one.")
    try:
        from scipy.stats import linregress, t
    except ImportError as error:
        raise RuntimeError("scipy is required for trend confidence intervals and p-values.") from error

    regression = linregress(x, y)
    degrees_of_freedom = len(x) - 2
    critical_value = t.ppf((1 + confidence) / 2, degrees_of_freedom)
    margin = critical_value * regression.stderr
    return {
        "count": len(x),
        "slope_per_year": round(float(regression.slope), 6),
        "intercept": round(float(regression.intercept), 6),
        "r_squared": round(float(regression.rvalue**2), 6),
        "p_value": round(float(regression.pvalue), 6),
        "confidence_level": confidence,
        "slope_ci_lower": round(float(regression.slope - margin), 6),
        "slope_ci_upper": round(float(regression.slope + margin), 6),
    }
