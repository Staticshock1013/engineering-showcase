import json
from pathlib import Path

import pytest

from terratrend.availability import (
    PREFERRED_SHARED_WINDOW,
    availability_map_rows,
    build_lst_city_availability,
)
from terratrend.dashboard import load_lst_availability_state
from terratrend.nasa import LAGOS, LST_EXPANSION_CITIES, MUMBAI, SAO_PAULO, TOKYO
from terratrend.registry import LST_EXPANSION_COVERAGE


def _verified_cache(city: str, start: str, end: str, mean: float = 20.0) -> dict:
    return {
        "data_product_key": "mod11a2_v061_daytime_lst",
        "data_status": "verified_real_mod11a2_8_day_composite_not_annual",
        "cache_path": f"mod11a2_{city.lower().replace(' ', '_')}.json",
        "composite": {
            "city": city,
            "time_start": f"{start}T00:00:00.000Z",
            "time_end": f"{end}T23:59:59.000Z",
            "mean_celsius": mean,
            "valid_pixel_count": 12,
            "selected_pixel_count": 100,
            "bounding_box": [-1.0, -1.0, 1.0, 1.0],
        },
    }


def test_expansion_cities_are_tile_contained_named_windows():
    assert [city.name for city in LST_EXPANSION_CITIES] == [
        "Lagos",
        "Tokyo",
        "Mumbai",
        "São Paulo",
    ]
    assert LAGOS.bounding_box[2] > LAGOS.bounding_box[0]
    assert TOKYO.bounding_box[1] < TOKYO.bounding_box[3]
    assert MUMBAI.name == "Mumbai"
    assert SAO_PAULO.name == "São Paulo"
    assert LST_EXPANSION_COVERAGE["São Paulo"] == "verified_shared_window"
    assert PREFERRED_SHARED_WINDOW == ("2024-06-25", "2024-07-02")


def test_shared_window_verified_city_is_marked_verified(tmp_path: Path):
    states = build_lst_city_availability(
        cache_loader=lambda: [
            _verified_cache("São Paulo", "2024-06-25", "2024-07-02", mean=20.0)
        ],
        availability_directory=tmp_path,
    )
    sao_paulo = next(state for state in states if state.city == "São Paulo")

    assert sao_paulo.status == "verified"
    assert sao_paulo.shared_window_status == "verified"
    assert sao_paulo.mean_celsius == 20.0


def test_failed_shared_window_keeps_alternate_period_without_fabricating(tmp_path: Path):
    marker = {
        "status": "unavailable",
        "data_product_key": "mod11a2_v061_daytime_lst",
        "city": "Lagos",
        "period_start": "2024-06-25",
        "period_end": "2024-07-02",
        "reason": "No QC-passing pixels in preferred shared window.",
        "claim": "no_fabricated_value",
    }
    (tmp_path / "mod11a2_lagos_2024-06-25.json").write_text(
        json.dumps(marker), encoding="utf-8"
    )

    states = build_lst_city_availability(
        cache_loader=lambda: [_verified_cache("Lagos", "2024-01-01", "2024-01-08", mean=27.9)],
        availability_directory=tmp_path,
    )
    lagos = next(state for state in states if state.city == "Lagos")

    assert lagos.status == "verified_alternate_period"
    assert lagos.shared_window_status == "unavailable"
    assert lagos.period_start.startswith("2024-01-01")
    assert lagos.reason == "No QC-passing pixels in preferred shared window."


def test_unavailable_marker_without_cache_exposes_no_mean(tmp_path: Path):
    marker = {
        "status": "unavailable",
        "data_product_key": "mod11a2_v061_daytime_lst",
        "city": "Tokyo",
        "period_start": "2024-06-25",
        "period_end": "2024-07-02",
        "reason": "validation failed",
        "claim": "no_fabricated_value",
    }
    (tmp_path / "tokyo.json").write_text(json.dumps(marker), encoding="utf-8")

    states = build_lst_city_availability(
        (TOKYO,),
        cache_loader=lambda: [],
        availability_directory=tmp_path,
    )

    assert states[0].status == "unavailable"
    assert states[0].mean_celsius is None
    assert availability_map_rows(states)[0]["mean_celsius"] is None


def test_fabricated_unavailable_marker_is_rejected(tmp_path: Path):
    marker = {
        "status": "unavailable",
        "data_product_key": "mod11a2_v061_daytime_lst",
        "city": "Mumbai",
        "claim": "no_fabricated_value",
        "mean_celsius": 30.0,
    }
    (tmp_path / "bad.json").write_text(json.dumps(marker), encoding="utf-8")

    with pytest.raises(ValueError, match="must not include fabricated means"):
        build_lst_city_availability(
            (MUMBAI,),
            cache_loader=lambda: [],
            availability_directory=tmp_path,
        )


def test_dashboard_availability_state_fails_closed():
    state = load_lst_availability_state(loader=lambda: (_ for _ in ()).throw(ValueError("bad")))

    assert state.status == "unavailable"
    assert state.cities == []
