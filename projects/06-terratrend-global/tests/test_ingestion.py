from dataclasses import asdict
from datetime import date
import json

import pytest

from terratrend.ingestion import (
    BatchPlan,
    IngestionSafetyError,
    PlannedPeriod,
    build_batch_plan,
    coverage_summary,
    execute_batch_plan,
    require_multiyear_trend_claim,
)
from terratrend.mod11a2 import ProcessedComposite
from terratrend.nasa import LONDON


def _composite(period: PlannedPeriod, value: float = 10.0) -> ProcessedComposite:
    start, end = date.fromisoformat(period.start), date.fromisoformat(period.end)
    return ProcessedComposite(
        granule_ur="MOD11A2.A2024001.h17v03.061.2024011195232",
        time_start=f"{period.start}T00:00:00Z",
        time_end=f"{period.end}T23:59:59Z",
        city="London",
        bounding_box=LONDON.bounding_box,
        mean_celsius=value,
        selected_pixel_count=100,
        valid_pixel_count=80,
        temporal_days=(end - start).days + 1,
    )


def test_annual_plan_is_product_aligned_and_performs_no_network_in_dry_run(tmp_path):
    plan = build_batch_plan(LONDON, [2024])

    assert len(plan.periods) == 46
    assert plan.periods[0] == PlannedPeriod("2024-01-01", "2024-01-08")
    assert plan.periods[-1] == PlannedPeriod("2024-12-26", "2024-12-31")

    manifest = execute_batch_plan(plan, tmp_path, dry_run=True)

    assert manifest["run_mode"] == "dry_run"
    assert {item["status"] for item in manifest["outcomes"]} == {"planned_no_network"}
    saved = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert saved["trend_claim"].startswith("refused")


def test_apply_refuses_unbounded_annual_downloads_before_network_access(tmp_path):
    plan = build_batch_plan(LONDON, [2024])

    with pytest.raises(IngestionSafetyError, match="exceeding"):
        execute_batch_plan(plan, tmp_path, dry_run=False, max_downloads=1)


def test_complete_annual_coverage_is_eligible_but_partial_coverage_is_not():
    plan = build_batch_plan(LONDON, [2024])
    complete = [_composite(period) for period in plan.periods]

    annual = coverage_summary(plan, complete, 2024)
    incomplete = coverage_summary(plan, complete[:-1], 2024)

    assert annual["status"] == "verified_complete_annual"
    assert annual["annual_celsius"] == 10.0
    assert incomplete["status"] == "insufficient_coverage"
    assert incomplete["annual_celsius"] is None


def test_coverage_threshold_never_turns_partial_annual_data_into_a_trend_claim():
    plan = build_batch_plan(LONDON, [2024], minimum_coverage_fraction=0.9)
    composites = [_composite(period) for period in plan.periods[:-1]]

    summary = coverage_summary(plan, composites, 2024)

    assert summary["status"] == "incomplete_annual_no_trend_claim"
    assert summary["annual_celsius"] is None


def test_fixed_season_never_claims_an_annual_result():
    plan = build_batch_plan(
        LONDON,
        [2024],
        mode="fixed-season",
        season_start=(6, 1),
        season_end=(8, 31),
        minimum_coverage_fraction=0.95,
    )

    summary = coverage_summary(plan, [_composite(period) for period in plan.periods], 2024)

    assert summary["status"] == "verified_fixed_season_not_annual"
    assert summary["annual_celsius"] is None


def test_apply_resumes_existing_period_without_metadata_or_download(tmp_path):
    plan = BatchPlan(
        city=LONDON,
        years=(2024,),
        mode="fixed-season",
        periods=(PlannedPeriod("2024-06-01", "2024-06-08"),),
        target_windows=(PlannedPeriod("2024-06-01", "2024-06-08"),),
        minimum_coverage_fraction=1.0,
    )
    output = tmp_path / "processed" / "london_2024-06-01.json"
    output.parent.mkdir()
    output.write_text(json.dumps({"composite": asdict(_composite(plan.periods[0]))}), encoding="utf-8")

    manifest = execute_batch_plan(
        plan,
        tmp_path,
        dry_run=False,
        metadata_lookup=lambda *_: pytest.fail("resumed data must not query metadata"),
    )

    assert manifest["outcomes"][0]["status"] == "resumed"


def test_trend_claim_refuses_incomplete_or_too_short_annual_series():
    plan = build_batch_plan(LONDON, [2024])
    complete = coverage_summary(plan, [_composite(period) for period in plan.periods], 2024)

    with pytest.raises(IngestionSafetyError, match="at least three"):
        require_multiyear_trend_claim([complete])
