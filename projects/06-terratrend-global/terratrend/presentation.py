"""Safe comparison and CSV presentation helpers for fixture and verified data."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from io import StringIO
from typing import Any, Iterable

from .registry import INDICATOR_REGISTRY, VERIFIED_DATA_REGISTRY, IndicatorDefinition


@dataclass(frozen=True)
class CityComparison:
    """A comparison result that is either explicitly compatible or refused."""

    compatible: bool
    reason: str
    rows: tuple[dict[str, Any], ...] = ()


def _mean_value(cache: dict[str, Any]) -> float:
    composite = cache["composite"]
    value = composite.get("mean_celsius", composite.get("mean_ndvi"))
    if value is None:
        raise ValueError("Verified cache has no supported mean value.")
    return float(value)


def compare_verified_cities(caches: Iterable[dict[str, Any]]) -> CityComparison:
    """Compare exactly two equivalent verified periods, otherwise return a refusal."""
    entries = list(caches)
    if len(entries) != 2:
        return CityComparison(False, "Select exactly two verified city caches to compare.")
    if any(entry.get("data_product_key") not in VERIFIED_DATA_REGISTRY for entry in entries):
        return CityComparison(False, "Synthetic fixtures and unregistered data cannot be city-compared.")
    definitions = [VERIFIED_DATA_REGISTRY[entry["data_product_key"]] for entry in entries]
    if len({definition.key for definition in definitions}) != 1:
        return CityComparison(False, "Comparison requires the same verified product and variable.")
    if len({definition.unit for definition in definitions}) != 1:
        return CityComparison(False, "Comparison requires identical units.")
    composites = [entry["composite"] for entry in entries]
    if len({composite["city"] for composite in composites}) != 2:
        return CityComparison(False, "Comparison requires two distinct cities.")
    if len({(composite["time_start"], composite["time_end"]) for composite in composites}) != 1:
        return CityComparison(False, "Comparison requires the exact same composite period.")
    if len({entry["data_status"] for entry in entries}) != 1:
        return CityComparison(False, "Comparison requires matching aggregation and coverage status.")
    processing_keys = ("source_variable", "qc_rule", "spatial_sampling")
    if any(len({entry["processing"].get(key) for entry in entries}) != 1 for key in processing_keys):
        return CityComparison(False, "Comparison requires matching processing and spatial-sampling methods.")
    definition = definitions[0]
    rows = tuple(
        {
            "city": composite["city"],
            "mean_value": _mean_value(entry),
            "unit": definition.unit,
            "period_start": composite["time_start"],
            "period_end": composite["time_end"],
            "valid_pixel_count": composite["valid_pixel_count"],
            "selected_pixel_count": composite["selected_pixel_count"],
            "valid_pixel_fraction": round(
                composite["valid_pixel_count"] / composite["selected_pixel_count"], 6
            ),
            "data_status": entry["data_status"],
        }
        for entry, composite in zip(entries, composites, strict=True)
    )
    return CityComparison(True, "Compatible verified period comparison.", rows)


def _csv_text(rows: list[dict[str, Any]], fields: list[str]) -> str:
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def verified_cache_csv(caches: Iterable[dict[str, Any]]) -> str:
    """Export verified period-level data with product, processing, and provenance fields."""
    rows = []
    for cache in caches:
        key = cache.get("data_product_key")
        definition = VERIFIED_DATA_REGISTRY.get(key)
        if not definition:
            raise ValueError("Only registered verified caches can be exported as verified data.")
        composite, processing, provenance = cache["composite"], cache["processing"], cache["provenance"]
        rows.append(
            {
                "data_class": "verified_period_cache",
                "data_status": cache["data_status"],
                "product_key": key,
                "product_short_name": provenance["product_short_name"],
                "product_version": provenance["product_version"],
                "variable_name": definition.variable_name,
                "unit": definition.unit,
                "aggregation": definition.temporal_resolution,
                "coverage_status": "period_level_not_annual",
                "city": composite["city"],
                "period_start": composite["time_start"],
                "period_end": composite["time_end"],
                "period_days": composite["temporal_days"],
                "mean_value": _mean_value(cache),
                "selected_pixel_count": composite["selected_pixel_count"],
                "valid_pixel_count": composite["valid_pixel_count"],
                "valid_pixel_fraction": round(
                    composite["valid_pixel_count"] / composite["selected_pixel_count"], 6
                ),
                "source_variable": processing["source_variable"],
                "qc_rule": processing["qc_rule"],
                "spatial_sampling": processing["spatial_sampling"],
                "product_documentation": cache["product_documentation"],
                "cmr_concept_id": provenance["cmr_concept_id"],
                "provider": provenance["provider"],
                "granule_ur": provenance["granule_ur"],
                "cmr_query_url": provenance["query_url"],
                "source_data_url": provenance["data_url"],
            }
        )
    return _csv_text(rows, list(rows[0]) if rows else ["data_class", "data_status"])


def synthetic_fixture_csv(
    observations: Iterable[dict[str, Any]], definition: IndicatorDefinition
) -> str:
    """Export synthetic fixtures with explicit non-observational provenance and coverage."""
    rows = [
        {
            "data_class": "synthetic_fixture",
            "data_status": "synthetic_not_real_earth_observation_data",
            "indicator": definition.key,
            "indicator_name": definition.name,
            "unit": definition.unit,
            "aggregation": "deterministic fixture month",
            "coverage_status": "prototype_fixture_not_validated_coverage",
            "region": row["region"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "period": row["month"],
            "value": row["value"],
            "baseline": row["baseline"],
            "source": row["source"],
            "methodology": "Deterministic synthetic fixture for interface prototyping.",
            "provenance": row["label"],
        }
        for row in observations
    ]
    fields = list(rows[0]) if rows else [
        "data_class",
        "data_status",
        "indicator",
        "indicator_name",
        "unit",
    ]
    return _csv_text(rows, fields)
