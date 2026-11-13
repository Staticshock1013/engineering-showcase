"""Bounded, resumable fixed-season MOD13A2 NDVI series ingestion.

This workflow compares the MODIS composite beginning on the same day-of-year across
years. It is explicitly a fixed-season series, never an annual NDVI product.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta
import json
from pathlib import Path
import time
from typing import Any, Callable, Iterable
from urllib.request import Request, urlopen

from .mod13a2 import process_hdf4_ndvi_composite, save_processed_ndvi_composite
from .nasa import MOD13A2_V061, NEW_YORK_CITY, GranuleProvenance, protected_download_headers, search_granule_metadata
from .statistics import linear_trend

FIXED_SEASON_STATUS = "verified_fixed_season_ndvi_not_annual"
DEFAULT_COMPOSITE_DOY = 177
DEFAULT_MINIMUM_VALID_PIXEL_FRACTION = 0.10


class FixedSeasonIngestionError(RuntimeError):
    """Raised before an unsafe or scientifically incompatible series operation."""


@dataclass(frozen=True)
class FixedSeasonPeriod:
    """One MOD13A2 16-day composite targeted by calendar day-of-year."""

    year: int
    start: str
    end: str


def build_fixed_season_plan(
    years: Iterable[int], composite_doy: int = DEFAULT_COMPOSITE_DOY
) -> tuple[FixedSeasonPeriod, ...]:
    """Create a no-network MODIS-composite plan for the requested years."""
    if not 1 <= composite_doy <= 351:
        raise FixedSeasonIngestionError("Composite day-of-year must leave room for a 16-day period.")
    plan = []
    for year in sorted(set(years)):
        start = date(year, 1, 1) + timedelta(days=composite_doy - 1)
        end = start + timedelta(days=15)
        plan.append(FixedSeasonPeriod(year, start.isoformat(), end.isoformat()))
    if not plan:
        raise FixedSeasonIngestionError("At least one year is required.")
    return tuple(plan)


def _period_path(cache_directory: Path, period: FixedSeasonPeriod) -> Path:
    return cache_directory / "periods" / f"mod13a2_nyc_{period.start}.json"


def _download_granule(provenance: GranuleProvenance, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".part")
    with urlopen(Request(provenance.data_url, headers=protected_download_headers()), timeout=90) as response:
        with temporary.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
    temporary.replace(destination)


def _load_period(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_fixed_season_series(
    periods: Iterable[dict[str, Any]],
    *,
    minimum_valid_pixel_fraction: float = DEFAULT_MINIMUM_VALID_PIXEL_FRACTION,
) -> dict[str, Any]:
    """Assess coverage and calculate a trend only from valid fixed-season periods."""
    if not 0 < minimum_valid_pixel_fraction <= 1:
        raise FixedSeasonIngestionError("Minimum valid-pixel fraction must be in (0, 1].")
    valid = []
    outcomes = []
    for payload in periods:
        composite = payload["composite"]
        fraction = composite["valid_pixel_count"] / composite["selected_pixel_count"]
        record = {
            "year": int(composite["time_start"][:4]),
            "period_start": composite["time_start"],
            "period_end": composite["time_end"],
            "mean_ndvi": composite["mean_ndvi"],
            "selected_pixel_count": composite["selected_pixel_count"],
            "valid_pixel_count": composite["valid_pixel_count"],
            "valid_pixel_fraction": round(fraction, 6),
            "granule_ur": composite["granule_ur"],
        }
        if payload.get("data_status") != "verified_real_mod13a2_16_day_composite_not_annual":
            record["status"] = "rejected_unverified_period"
        elif fraction < minimum_valid_pixel_fraction:
            record["status"] = "rejected_insufficient_pixel_coverage"
        else:
            record["status"] = "accepted_fixed_season_period"
            valid.append(record)
        outcomes.append(record)
    valid.sort(key=lambda record: record["year"])
    result: dict[str, Any] = {
        "series_status": FIXED_SEASON_STATUS,
        "minimum_valid_pixel_fraction": minimum_valid_pixel_fraction,
        "periods": outcomes,
        "accepted_year_count": len(valid),
        "trend": {
            "status": "refused_insufficient_valid_years",
            "reason": "At least three valid fixed-season periods are required for an OLS trend.",
        },
    }
    if len(valid) >= 3:
        result["trend"] = {
            "status": "verified_fixed_season_ndvi_trend",
            "assumptions": (
                "One MOD13A2 DOY-177 16-day composite per year; consistent product, "
                "QC, city bounding box, and valid-pixel threshold. Not annual NDVI."
            ),
            **linear_trend(
                (record["year"] for record in valid),
                (record["mean_ndvi"] for record in valid),
            ),
        }
    return result


def execute_fixed_season_series(
    cache_directory: Path,
    years: Iterable[int] = range(2010, 2025),
    *,
    composite_doy: int = DEFAULT_COMPOSITE_DOY,
    dry_run: bool = True,
    max_downloads: int = 1,
    rate_limit_seconds: float = 1.0,
    minimum_valid_pixel_fraction: float = DEFAULT_MINIMUM_VALID_PIXEL_FRACTION,
    metadata_lookup: Callable[[date, date], GranuleProvenance] | None = None,
    downloader: Callable[[GranuleProvenance, Path], None] = _download_granule,
    sleeper: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Write a dry-run or bounded authenticated fixed-season series manifest."""
    plan = build_fixed_season_plan(years, composite_doy)
    if max_downloads < 1:
        raise FixedSeasonIngestionError("max_downloads must be at least one.")
    if rate_limit_seconds < 0:
        raise FixedSeasonIngestionError("rate_limit_seconds cannot be negative.")
    cache_directory.mkdir(parents=True, exist_ok=True)
    manifest_path = cache_directory / "manifest.json"
    if dry_run:
        manifest = {
            "schema_version": 1,
            "series_status": "planned_fixed_season_ndvi_no_network",
            "city": asdict(NEW_YORK_CITY),
            "composite_day_of_year": composite_doy,
            "periods": [{**asdict(period), "status": "planned_no_network"} for period in plan],
            "trend": {"status": "refused_no_observations"},
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return manifest

    pending = [period for period in plan if not _period_path(cache_directory, period).exists()]
    if len(pending) > max_downloads:
        raise FixedSeasonIngestionError(
            f"Plan has {len(pending)} pending periods, exceeding explicit max_downloads={max_downloads}."
        )
    lookup = metadata_lookup or (
        lambda start, end: search_granule_metadata(MOD13A2_V061, NEW_YORK_CITY, start, end + timedelta(days=1))
    )
    raw_directory = cache_directory / "raw"
    for index, period in enumerate(pending):
        if index:
            sleeper(rate_limit_seconds)
        provenance = lookup(date.fromisoformat(period.start), date.fromisoformat(period.end))
        actual_start = date.fromisoformat(provenance.time_start[:10])
        actual_end = date.fromisoformat(provenance.time_end[:10])
        if actual_start.timetuple().tm_yday != composite_doy or (actual_end - actual_start).days != 15:
            raise FixedSeasonIngestionError("CMR returned a non-comparable MOD13A2 composite period.")
        raw_path = raw_directory / f"{provenance.granule_ur}.hdf"
        if not raw_path.exists():
            downloader(provenance, raw_path)
        composite = process_hdf4_ndvi_composite(raw_path, provenance, NEW_YORK_CITY)
        save_processed_ndvi_composite(_period_path(cache_directory, period), composite, provenance)

    payloads = [_load_period(_period_path(cache_directory, period)) for period in plan if _period_path(cache_directory, period).exists()]
    assessment = evaluate_fixed_season_series(
        payloads, minimum_valid_pixel_fraction=minimum_valid_pixel_fraction
    )
    manifest = {
        "schema_version": 1,
        "city": asdict(NEW_YORK_CITY),
        "product": {"short_name": "MOD13A2", "version": "061"},
        "series_status": FIXED_SEASON_STATUS,
        "composite_day_of_year": composite_doy,
        "period_definition": "One 16-day MOD13A2 composite beginning on DOY 177 each year.",
        "period_cache_directory": "periods",
        **assessment,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def load_fixed_season_series(cache_directory: Path) -> dict[str, Any] | None:
    """Load a completed fixed-season series manifest, if present."""
    path = cache_directory / "manifest.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
