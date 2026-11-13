import csv
from io import StringIO

from terratrend.cache import load_verified_cache_registry
from terratrend.data import load_observations
from terratrend.presentation import (
    compare_verified_cities,
    synthetic_fixture_csv,
    verified_cache_csv,
)
from terratrend.registry import INDICATOR_REGISTRY


def _caches():
    entries = load_verified_cache_registry()
    lst = [entry for entry in entries if entry["data_product_key"] == "mod11a2_v061_daytime_lst"]
    ndvi = next(entry for entry in entries if entry["data_product_key"] == "mod13a2_v061_ndvi")
    return lst, ndvi


def test_city_comparison_refuses_different_composite_periods():
    lst, _ = _caches()
    incompatible_pair = [
        next(entry for entry in lst if entry["composite"]["city"] == "London"),
        next(
            entry
            for entry in lst
            if entry["composite"]["city"] == "New York City"
            and entry["composite"]["time_start"].startswith("2024-01-01")
        ),
    ]

    comparison = compare_verified_cities(incompatible_pair)

    assert not comparison.compatible
    assert "same composite period" in comparison.reason


def test_city_comparison_refuses_different_products():
    lst, ndvi = _caches()

    comparison = compare_verified_cities([lst[0], ndvi])

    assert not comparison.compatible
    assert "same verified product" in comparison.reason


def test_city_comparison_allows_matching_verified_metadata():
    lst, _ = _caches()
    matching_period = [
        entry
        for entry in lst
        if entry["composite"]["time_start"].startswith("2024-06-25")
        and entry["composite"]["time_end"].startswith("2024-07-02")
    ]

    comparison = compare_verified_cities(matching_period)

    assert comparison.compatible
    assert {row["city"] for row in comparison.rows} == {"London", "New York City"}
    assert all(row["unit"] == "°C" for row in comparison.rows)


def test_verified_csv_includes_provenance_and_period_coverage():
    _, ndvi = _caches()

    rows = list(csv.DictReader(StringIO(verified_cache_csv([ndvi]))))

    assert rows[0]["data_class"] == "verified_period_cache"
    assert rows[0]["coverage_status"] == "period_level_not_annual"
    assert rows[0]["cmr_concept_id"] == ndvi["provenance"]["cmr_concept_id"]
    assert rows[0]["qc_rule"] == ndvi["processing"]["qc_rule"]


def test_synthetic_csv_preserves_synthetic_label_and_methodology():
    observations = load_observations()
    definition = INDICATOR_REGISTRY["vegetation_index_anomaly"]
    selected = [row for row in observations if row["indicator"] == definition.key]

    rows = list(csv.DictReader(StringIO(synthetic_fixture_csv(selected, definition))))

    assert {row["data_class"] for row in rows} == {"synthetic_fixture"}
    assert {row["data_status"] for row in rows} == {"synthetic_not_real_earth_observation_data"}
    assert all("Deterministic synthetic" in row["methodology"] for row in rows)
