import json

import pytest

from terratrend.cache import load_verified_cache_registry


def _cache_payload(city: str = "London") -> dict:
    return {
        "data_product_key": "mod11a2_v061_daytime_lst",
        "data_status": "verified_real_mod11a2_8_day_composite_not_annual",
        "composite": {
            "city": city,
            "time_start": "2024-06-25T00:00:00.000Z",
            "time_end": "2024-07-02T23:59:59.000Z",
        },
        "provenance": {"product_short_name": "MOD11A2", "product_version": "061"},
    }


def test_verified_cache_registry_accepts_matching_product_and_status(tmp_path):
    (tmp_path / "london.json").write_text(json.dumps(_cache_payload()), encoding="utf-8")

    entries = load_verified_cache_registry(tmp_path)

    assert entries[0]["composite"]["city"] == "London"
    assert entries[0]["cache_path"] == "london.json"


def test_verified_cache_registry_is_empty_when_no_processed_data_exists(tmp_path):
    assert load_verified_cache_registry(tmp_path) == []


def test_verified_cache_registry_rejects_unregistered_status(tmp_path):
    payload = _cache_payload()
    payload["data_status"] = "annual"
    (tmp_path / "invalid.json").write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="does not match"):
        load_verified_cache_registry(tmp_path)


def test_packaged_expansion_city_caches_match_registry():
    entries = load_verified_cache_registry()
    cities = {entry["composite"]["city"] for entry in entries}
    assert {"Lagos", "Tokyo", "Mumbai", "São Paulo"}.issubset(cities)
    lst_entries = [
        entry for entry in entries if entry["data_product_key"] == "mod11a2_v061_daytime_lst"
    ]
    assert all(
        entry["data_status"] == "verified_real_mod11a2_8_day_composite_not_annual"
        for entry in lst_entries
    )
