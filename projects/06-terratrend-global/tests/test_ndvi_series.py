import json

import pytest

from terratrend.ndvi_series import (
    FixedSeasonIngestionError,
    build_fixed_season_plan,
    evaluate_fixed_season_series,
    execute_fixed_season_series,
)


def _period(year: int, value: float, valid: int = 500, selected: int = 1000) -> dict:
    return {
        "data_status": "verified_real_mod13a2_16_day_composite_not_annual",
        "composite": {
            "time_start": f"{year}-06-25T00:00:00.000Z",
            "time_end": f"{year}-07-10T23:59:59.000Z",
            "mean_ndvi": value,
            "selected_pixel_count": selected,
            "valid_pixel_count": valid,
            "granule_ur": f"MOD13A2.A{year}177.h12v04.061.test",
        },
    }


def test_fixed_season_plan_uses_same_day_of_year_not_annual_windows():
    plan = build_fixed_season_plan([2010, 2012, 2024])

    assert [(period.year, period.start, period.end) for period in plan] == [
        (2010, "2010-06-26", "2010-07-11"),
        (2012, "2012-06-25", "2012-07-10"),
        (2024, "2024-06-25", "2024-07-10"),
    ]


def test_fixed_season_trend_has_statistics_and_never_annual_status():
    result = evaluate_fixed_season_series(
        [_period(2010, 0.40), _period(2011, 0.41), _period(2012, 0.42)]
    )

    assert result["series_status"] == "verified_fixed_season_ndvi_not_annual"
    assert result["trend"]["status"] == "verified_fixed_season_ndvi_trend"
    assert result["trend"]["slope_per_year"] == 0.01
    assert "p_value" in result["trend"]
    assert "slope_ci_lower" in result["trend"]


def test_fixed_season_trend_refuses_insufficient_valid_coverage_or_years():
    result = evaluate_fixed_season_series(
        [_period(2010, 0.4, valid=50), _period(2011, 0.41), _period(2012, 0.42)]
    )

    assert result["accepted_year_count"] == 2
    assert result["trend"]["status"] == "refused_insufficient_valid_years"


def test_dry_run_writes_no_network_manifest_and_apply_is_bounded(tmp_path):
    manifest = execute_fixed_season_series(tmp_path, [2010, 2011], dry_run=True)

    assert manifest["series_status"] == "planned_fixed_season_ndvi_no_network"
    assert json.loads((tmp_path / "manifest.json").read_text())["trend"]["status"] == "refused_no_observations"

    with pytest.raises(FixedSeasonIngestionError, match="exceeding"):
        execute_fixed_season_series(tmp_path, [2010, 2011], dry_run=False, max_downloads=1)
