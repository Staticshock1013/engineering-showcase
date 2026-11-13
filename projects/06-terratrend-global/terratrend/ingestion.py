"""Plan-first, resumable MOD11A2 ingestion with strict annual-claim safeguards.

The default workflow is a dry run: it plans expected MOD11A2 eight-day periods without
contacting CMR or downloading HDF files.  Apply mode is intentionally opt-in, bounded by
``max_downloads``, rate limited, and writes credential-free provenance and a manifest.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta
import argparse
import json
from pathlib import Path
import time
from typing import Callable, Iterable, Literal
from urllib.request import Request, urlopen

from .mod11a2 import (
    ProcessedComposite,
    annual_mean_celsius,
    load_processed_composite,
    process_hdf4_composite,
    save_processed_composite,
)
from .nasa import (
    City,
    GranuleProvenance,
    LAGOS,
    LONDON,
    MOD11A2_V061,
    MUMBAI,
    NEW_YORK_CITY,
    SAO_PAULO,
    TOKYO,
    protected_download_headers,
    search_granule_metadata,
)

CITY_CHOICES = {
    "london": LONDON,
    "new-york-city": NEW_YORK_CITY,
    "lagos": LAGOS,
    "tokyo": TOKYO,
    "mumbai": MUMBAI,
    "sao-paulo": SAO_PAULO,
}

Mode = Literal["annual", "fixed-season"]


class IngestionSafetyError(RuntimeError):
    """Raised before an unbounded, incomplete, or unsafe ingestion action."""


@dataclass(frozen=True)
class PlannedPeriod:
    """One expected MOD11A2 eight-day product interval."""

    start: str
    end: str


@dataclass(frozen=True)
class BatchPlan:
    """A deterministic city/time plan that can be reviewed before network access."""

    city: City
    years: tuple[int, ...]
    mode: Mode
    periods: tuple[PlannedPeriod, ...]
    target_windows: tuple[PlannedPeriod, ...]
    minimum_coverage_fraction: float


def _window_for_year(
    year: int, mode: Mode, season_start: tuple[int, int] | None, season_end: tuple[int, int] | None
) -> tuple[date, date]:
    if mode == "annual":
        return date(year, 1, 1), date(year, 12, 31)
    if not season_start or not season_end:
        raise IngestionSafetyError("Fixed-season plans require both season start and end month/day.")
    start, end = date(year, *season_start), date(year, *season_end)
    if end < start:
        raise IngestionSafetyError("Fixed-season ranges must be contained within one calendar year.")
    return start, end


def build_batch_plan(
    city: City,
    years: Iterable[int],
    *,
    mode: Mode = "annual",
    season_start: tuple[int, int] | None = None,
    season_end: tuple[int, int] | None = None,
    minimum_coverage_fraction: float = 1.0,
) -> BatchPlan:
    """Build product-aligned periods without querying CMR or downloading any data."""
    normalized_years = tuple(sorted(set(years)))
    if not normalized_years:
        raise IngestionSafetyError("At least one target year is required.")
    if not 0 < minimum_coverage_fraction <= 1:
        raise IngestionSafetyError("Minimum coverage fraction must be in (0, 1].")
    periods: list[PlannedPeriod] = []
    target_windows: list[PlannedPeriod] = []
    for year in normalized_years:
        window_start, window_end = _window_for_year(year, mode, season_start, season_end)
        target_windows.append(PlannedPeriod(window_start.isoformat(), window_end.isoformat()))
        period_start = date(year, 1, 1)
        while period_start <= date(year, 12, 31):
            period_end = min(period_start + timedelta(days=7), date(year, 12, 31))
            if period_end >= window_start and period_start <= window_end:
                periods.append(PlannedPeriod(period_start.isoformat(), period_end.isoformat()))
            period_start = period_end + timedelta(days=1)
    return BatchPlan(city, normalized_years, mode, tuple(periods), tuple(target_windows), minimum_coverage_fraction)


def _coverage_days(composites: Iterable[ProcessedComposite], start: date, end: date) -> int:
    covered: set[date] = set()
    for composite in composites:
        current = max(date.fromisoformat(composite.time_start[:10]), start)
        finish = min(date.fromisoformat(composite.time_end[:10]), end)
        while current <= finish:
            covered.add(current)
            current += timedelta(days=1)
    return len(covered)


def coverage_summary(plan: BatchPlan, composites: Iterable[ProcessedComposite], year: int) -> dict[str, object]:
    """Report covered days and refuse annual claims when coverage is incomplete."""
    try:
        target_window = next(
            window for window in plan.target_windows if date.fromisoformat(window.start).year == year
        )
    except StopIteration as error:
        raise IngestionSafetyError(f"No configured target window for {year}.") from error
    start, end = date.fromisoformat(target_window.start), date.fromisoformat(target_window.end)
    relevant = [
        composite
        for composite in composites
        if date.fromisoformat(composite.time_end[:10]) >= start
        and date.fromisoformat(composite.time_start[:10]) <= end
    ]
    expected_days = (end - start).days + 1
    covered_days = _coverage_days(relevant, start, end)
    fraction = covered_days / expected_days
    result: dict[str, object] = {
        "year": year,
        "mode": plan.mode,
        "expected_days": expected_days,
        "covered_days": covered_days,
        "coverage_fraction": round(fraction, 6),
        "minimum_coverage_fraction": plan.minimum_coverage_fraction,
        "period_count": len(relevant),
    }
    if fraction < plan.minimum_coverage_fraction:
        result["status"] = "insufficient_coverage"
        result["annual_celsius"] = None
    elif plan.mode != "annual":
        result["status"] = "verified_fixed_season_not_annual"
        result["annual_celsius"] = None
    elif fraction < 1:
        result["status"] = "incomplete_annual_no_trend_claim"
        result["annual_celsius"] = None
    else:
        result["status"] = "verified_complete_annual"
        result["annual_celsius"] = annual_mean_celsius(relevant, year)
    return result


def require_multiyear_trend_claim(summaries: Iterable[dict[str, object]]) -> tuple[int, ...]:
    """Permit a trend claim only for at least three complete annual results."""
    rows = sorted(summaries, key=lambda row: int(row["year"]))
    years = tuple(int(row["year"]) for row in rows)
    if len(years) < 3:
        raise IngestionSafetyError("A trend claim requires at least three complete annual results.")
    if len(set(years)) != len(years) or any(
        row.get("status") != "verified_complete_annual" for row in rows
    ):
        raise IngestionSafetyError("Trend claims require unique years with complete annual coverage.")
    return years


def _processed_output_path(cache_directory: Path, city: City, period: PlannedPeriod) -> Path:
    return cache_directory / "processed" / f"{city.name.lower().replace(' ', '_')}_{period.start}.json"


def _cached_composites(cache_directory: Path, plan: BatchPlan) -> list[ProcessedComposite]:
    composites = []
    for period in plan.periods:
        output_path = _processed_output_path(cache_directory, plan.city, period)
        if output_path.exists():
            cached = load_processed_composite(output_path)["composite"]
            composites.append(
                ProcessedComposite(
                    **{**cached, "bounding_box": tuple(cached["bounding_box"])}
                )
            )
    return composites


def _download_granule(provenance: GranuleProvenance, destination: Path) -> None:
    """Download one authenticated HDF atomically without persisting a credential."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".part")
    with urlopen(Request(provenance.data_url, headers=protected_download_headers()), timeout=90) as response:
        with temporary.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
    temporary.replace(destination)


def execute_batch_plan(
    plan: BatchPlan,
    cache_directory: Path,
    *,
    dry_run: bool = True,
    max_downloads: int = 1,
    rate_limit_seconds: float = 1.0,
    metadata_lookup: Callable[[City, date, date], GranuleProvenance] | None = None,
    downloader: Callable[[GranuleProvenance, Path], None] = _download_granule,
    sleeper: Callable[[float], None] = time.sleep,
) -> dict[str, object]:
    """Execute a bounded plan or write a no-network dry-run manifest.

    Apply mode fails before network access when the planned number of periods exceeds
    ``max_downloads``. Existing processed outputs are retained and recorded as resumed.
    """
    if max_downloads < 1:
        raise IngestionSafetyError("max_downloads must be at least one.")
    if rate_limit_seconds < 0:
        raise IngestionSafetyError("rate_limit_seconds cannot be negative.")
    cache_directory.mkdir(parents=True, exist_ok=True)
    manifest_path = cache_directory / "manifest.json"
    outcomes: list[dict[str, object]] = []
    if dry_run:
        outcomes = [
            {"period_start": period.start, "period_end": period.end, "status": "planned_no_network"}
            for period in plan.periods
        ]
    else:
        pending_periods = [
            period for period in plan.periods if not _processed_output_path(cache_directory, plan.city, period).exists()
        ]
        if len(pending_periods) > max_downloads:
            raise IngestionSafetyError(
                f"Plan has {len(pending_periods)} pending periods, exceeding the explicit max_downloads={max_downloads}."
            )
        lookup = metadata_lookup or (
            lambda city, start, end: search_granule_metadata(MOD11A2_V061, city, start, end)
        )
        raw_directory = cache_directory / "raw"
        for index, period in enumerate(plan.periods):
            output_path = _processed_output_path(cache_directory, plan.city, period)
            if output_path.exists():
                outcomes.append(
                    {"period_start": period.start, "period_end": period.end, "status": "resumed", "output": str(output_path)}
                )
                continue
            if index:
                sleeper(rate_limit_seconds)
            provenance = lookup(plan.city, date.fromisoformat(period.start), date.fromisoformat(period.end))
            raw_path = raw_directory / f"{provenance.granule_ur}.hdf"
            if not raw_path.exists():
                downloader(provenance, raw_path)
            composite = process_hdf4_composite(raw_path, provenance, plan.city)
            save_processed_composite(output_path, composite, provenance)
            outcomes.append(
                {"period_start": period.start, "period_end": period.end, "status": "processed", "output": str(output_path)}
            )
    composites = _cached_composites(cache_directory, plan)
    coverage = [coverage_summary(plan, composites, year) for year in plan.years]
    manifest = {
        "schema_version": 1,
        "plan": {
            "city": asdict(plan.city),
            "years": list(plan.years),
            "mode": plan.mode,
            "minimum_coverage_fraction": plan.minimum_coverage_fraction,
            "periods": [asdict(period) for period in plan.periods],
            "target_windows": [asdict(window) for window in plan.target_windows],
        },
        "run_mode": "dry_run" if dry_run else "apply",
        "outcomes": outcomes,
        "coverage": coverage,
        "trend_claim": "refused_until_multiple_complete_annual_results_exist",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def _parse_season(value: str) -> tuple[tuple[int, int], tuple[int, int]]:
    try:
        start, end = value.split(":")
        return tuple(map(int, start.split("-"))), tuple(map(int, end.split("-")))
    except ValueError as error:
        raise argparse.ArgumentTypeError("Season must use MM-DD:MM-DD.") from error


def main() -> None:
    """Offer an explicit dry-run CLI; --apply is required for any network/download action."""
    parser = argparse.ArgumentParser(description="Plan or boundedly ingest MOD11A2 city composites.")
    parser.add_argument("--city", choices=tuple(CITY_CHOICES), default="london")
    parser.add_argument("--years", required=True, help="Comma-separated calendar years.")
    parser.add_argument("--mode", choices=("annual", "fixed-season"), default="annual")
    parser.add_argument("--season", type=_parse_season, help="Required fixed season: MM-DD:MM-DD.")
    parser.add_argument("--minimum-coverage", type=float, default=1.0)
    parser.add_argument("--cache-dir", type=Path, default=Path(".terratrend-cache"))
    parser.add_argument("--apply", action="store_true", help="Allow bounded authenticated downloads.")
    parser.add_argument("--max-downloads", type=int, default=1)
    parser.add_argument("--rate-limit-seconds", type=float, default=1.0)
    arguments = parser.parse_args()
    season_start, season_end = arguments.season if arguments.season else (None, None)
    city = CITY_CHOICES[arguments.city]
    plan = build_batch_plan(
        city,
        (int(value) for value in arguments.years.split(",")),
        mode=arguments.mode,
        season_start=season_start,
        season_end=season_end,
        minimum_coverage_fraction=arguments.minimum_coverage,
    )
    manifest = execute_batch_plan(
        plan,
        arguments.cache_dir,
        dry_run=not arguments.apply,
        max_downloads=arguments.max_downloads,
        rate_limit_seconds=arguments.rate_limit_seconds,
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
