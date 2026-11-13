"""City-level availability states for verified MOD11A2 expansion coverage.

Availability is derived from credential-free processed caches and explicit unavailable
markers. Failed preferred windows are recorded rather than fabricated. Alternate verified
periods remain period-level only and are never treated as city-wide or annual values.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Callable

from .cache import load_verified_cache_registry
from .nasa import VERIFIED_LST_CITIES, City
from .registry import CITY_LST_COVERAGE, VERIFIED_DATA_REGISTRY

AVAILABILITY_DIRECTORY = Path(__file__).parent / "availability"
PREFERRED_SHARED_WINDOW = ("2024-06-25", "2024-07-02")
LST_PRODUCT_KEY = "mod11a2_v061_daytime_lst"
NDVI_PRODUCT_KEY = "mod13a2_v061_ndvi"


@dataclass(frozen=True)
class CityAvailability:
    """One verified city's LST (and optional NDVI) state for dashboard/map display."""

    city: str
    status: str
    latitude: float
    longitude: float
    bounding_box: tuple[float, float, float, float]
    product_key: str
    shared_window_status: str
    period_start: str | None
    period_end: str | None
    cache_path: str | None
    reason: str | None
    mean_celsius: float | None
    valid_pixel_count: int | None
    selected_pixel_count: int | None
    ndvi_status: str = "unavailable"
    ndvi_cache_path: str | None = None
    registry_coverage: str | None = None


def _bbox_center(bounding_box: tuple[float, float, float, float]) -> tuple[float, float]:
    west, south, east, north = bounding_box
    return (south + north) / 2.0, (west + east) / 2.0


def _load_unavailable_markers(directory: Path) -> dict[str, dict[str, Any]]:
    markers: dict[str, dict[str, Any]] = {}
    if not directory.exists():
        return markers
    for path in sorted(directory.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("status") != "unavailable":
            raise ValueError(f"Availability marker must declare unavailable status: {path.name}.")
        if payload.get("data_product_key") != LST_PRODUCT_KEY:
            raise ValueError(f"Availability marker product key is invalid: {path.name}.")
        if payload.get("claim") != "no_fabricated_value":
            raise ValueError(f"Unavailable marker must declare no_fabricated_value: {path.name}.")
        if "mean_celsius" in payload:
            raise ValueError(f"Unavailable marker must not include fabricated means: {path.name}.")
        city = payload.get("city")
        if not city:
            raise ValueError(f"Availability marker is missing city: {path.name}.")
        markers[city] = {**payload, "marker_path": path.name}
    return markers


def _caches_by_city(
    caches: list[dict[str, Any]], product_key: str
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for cache in caches:
        if cache.get("data_product_key") != product_key:
            continue
        city = cache["composite"]["city"]
        grouped.setdefault(city, []).append(cache)
    for city_caches in grouped.values():
        city_caches.sort(key=lambda entry: entry["composite"]["time_start"])
    return grouped


def _shared_window_cache(caches: list[dict[str, Any]]) -> dict[str, Any] | None:
    preferred_start, preferred_end = PREFERRED_SHARED_WINDOW
    for cache in caches:
        composite = cache["composite"]
        if (
            composite["time_start"][:10] == preferred_start
            and composite["time_end"][:10] == preferred_end
        ):
            return cache
    return None


def _ndvi_status_for_city(caches: list[dict[str, Any]]) -> tuple[str, str | None]:
    if not caches:
        return "unavailable", None
    selected = caches[-1]
    return "verified_period", selected.get("cache_path")


def build_lst_city_availability(
    cities: tuple[City, ...] = VERIFIED_LST_CITIES,
    *,
    cache_loader: Callable[[], list[dict[str, Any]]] = load_verified_cache_registry,
    availability_directory: Path = AVAILABILITY_DIRECTORY,
) -> list[CityAvailability]:
    """Combine all six verified cities, LST caches, NDVI period flags, and unavailable markers."""
    if LST_PRODUCT_KEY not in VERIFIED_DATA_REGISTRY:
        raise ValueError("MOD11A2 daytime LST product is missing from the verified registry.")
    all_caches = cache_loader()
    caches_by_city = _caches_by_city(all_caches, LST_PRODUCT_KEY)
    ndvi_by_city = _caches_by_city(all_caches, NDVI_PRODUCT_KEY)
    unavailable = _load_unavailable_markers(availability_directory)
    rows: list[CityAvailability] = []
    for city in cities:
        latitude, longitude = _bbox_center(city.bounding_box)
        city_caches = caches_by_city.get(city.name, [])
        shared = _shared_window_cache(city_caches)
        marker = unavailable.get(city.name)
        ndvi_status, ndvi_path = _ndvi_status_for_city(ndvi_by_city.get(city.name, []))
        coverage = CITY_LST_COVERAGE.get(city.name)
        if shared:
            composite = shared["composite"]
            rows.append(
                CityAvailability(
                    city=city.name,
                    status="verified",
                    latitude=latitude,
                    longitude=longitude,
                    bounding_box=city.bounding_box,
                    product_key=LST_PRODUCT_KEY,
                    shared_window_status="verified",
                    period_start=composite["time_start"],
                    period_end=composite["time_end"],
                    cache_path=shared.get("cache_path"),
                    reason=None,
                    mean_celsius=composite.get("mean_celsius"),
                    valid_pixel_count=composite.get("valid_pixel_count"),
                    selected_pixel_count=composite.get("selected_pixel_count"),
                    ndvi_status=ndvi_status,
                    ndvi_cache_path=ndvi_path,
                    registry_coverage=coverage,
                )
            )
            continue
        if city_caches:
            # Prefer disclosing an alternate verified period when the shared window failed.
            selected = city_caches[-1]
            composite = selected["composite"]
            reason = marker.get("reason") if marker else None
            rows.append(
                CityAvailability(
                    city=city.name,
                    status="verified_alternate_period",
                    latitude=latitude,
                    longitude=longitude,
                    bounding_box=city.bounding_box,
                    product_key=LST_PRODUCT_KEY,
                    shared_window_status="unavailable",
                    period_start=composite["time_start"],
                    period_end=composite["time_end"],
                    cache_path=selected.get("cache_path"),
                    reason=reason,
                    mean_celsius=composite.get("mean_celsius"),
                    valid_pixel_count=composite.get("valid_pixel_count"),
                    selected_pixel_count=composite.get("selected_pixel_count"),
                    ndvi_status=ndvi_status,
                    ndvi_cache_path=ndvi_path,
                    registry_coverage=coverage,
                )
            )
            continue
        if marker:
            rows.append(
                CityAvailability(
                    city=city.name,
                    status="unavailable",
                    latitude=latitude,
                    longitude=longitude,
                    bounding_box=city.bounding_box,
                    product_key=LST_PRODUCT_KEY,
                    shared_window_status="unavailable",
                    period_start=marker.get("period_start"),
                    period_end=marker.get("period_end"),
                    cache_path=None,
                    reason=marker.get("reason"),
                    mean_celsius=None,
                    valid_pixel_count=None,
                    selected_pixel_count=None,
                    ndvi_status=ndvi_status,
                    ndvi_cache_path=ndvi_path,
                    registry_coverage=coverage,
                )
            )
            continue
        rows.append(
            CityAvailability(
                city=city.name,
                status="unavailable",
                latitude=latitude,
                longitude=longitude,
                bounding_box=city.bounding_box,
                product_key=LST_PRODUCT_KEY,
                shared_window_status="unavailable",
                period_start=PREFERRED_SHARED_WINDOW[0],
                period_end=PREFERRED_SHARED_WINDOW[1],
                cache_path=None,
                reason="No verified cache or unavailable marker exists for this city.",
                mean_celsius=None,
                valid_pixel_count=None,
                selected_pixel_count=None,
                ndvi_status=ndvi_status,
                ndvi_cache_path=ndvi_path,
                registry_coverage=coverage,
            )
        )
    return rows


def availability_map_rows(states: list[CityAvailability]) -> list[dict[str, Any]]:
    """Return map-ready rows that never invent LST values for unavailable cities."""
    rows = []
    for state in states:
        rows.append(
            {
                "city": state.city,
                "latitude": state.latitude,
                "longitude": state.longitude,
                "lst_availability": state.status,
                "shared_window": state.shared_window_status,
                "ndvi_availability": state.ndvi_status,
                "period_start": state.period_start,
                "period_end": state.period_end,
                "mean_celsius": state.mean_celsius,
                "reason": state.reason,
            }
        )
    return rows
