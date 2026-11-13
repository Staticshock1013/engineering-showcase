"""Fail-closed cache state for the Streamlit dashboard."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Callable

from .availability import CityAvailability, build_lst_city_availability
from .cache import load_verified_cache_registry


@dataclass(frozen=True)
class VerifiedCacheState:
    """A safe dashboard state for verified processed data."""

    status: str
    entries: list[dict[str, Any]]


@dataclass(frozen=True)
class LstAvailabilityState:
    """Fail-closed expansion-city LST availability for map and status panels."""

    status: str
    cities: list[CityAvailability]


def load_verified_cache_state(
    loader: Callable[[], list[dict[str, Any]]] = load_verified_cache_registry,
) -> VerifiedCacheState:
    """Return ready, empty, or unavailable without exposing invalid cache contents."""
    try:
        entries = loader()
    except (OSError, ValueError, json.JSONDecodeError):
        return VerifiedCacheState("unavailable", [])
    return VerifiedCacheState("ready", entries) if entries else VerifiedCacheState("empty", [])


def load_lst_availability_state(
    loader: Callable[[], list[CityAvailability]] = build_lst_city_availability,
) -> LstAvailabilityState:
    """Return ready expansion-city states, or unavailable when markers/caches are invalid."""
    try:
        cities = loader()
    except (OSError, ValueError, json.JSONDecodeError):
        return LstAvailabilityState("unavailable", [])
    return LstAvailabilityState("ready", cities) if cities else LstAvailabilityState("empty", [])
