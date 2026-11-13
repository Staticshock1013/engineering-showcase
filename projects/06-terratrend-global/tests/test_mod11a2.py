from datetime import date, timedelta

import numpy as np
import pytest

from terratrend.mod11a2 import (
    Mod11A2ValidationError,
    ProcessedComposite,
    annual_mean_celsius,
    bbox_fully_covered_by_tile,
    good_daytime_qc,
    tile_pixel_centers,
)


def _composite(start: str, end: str, value: float, days: int) -> ProcessedComposite:
    return ProcessedComposite(
        granule_ur="MOD11A2.A2024001.h12v04.061.2024011195232",
        time_start=start,
        time_end=end,
        city="New York City",
        bounding_box=(-74.1, 40.6, -73.7, 40.9),
        mean_celsius=value,
        selected_pixel_count=10,
        valid_pixel_count=8,
        temporal_days=days,
    )


def test_qc_keeps_only_good_mandatory_qa_with_error_at_most_two_kelvin():
    # QC bits 0-1 are mandatory QA; bits 6-7 are LST error.
    quality = [0b00000000, 0b01000000, 0b10000000, 0b00000001, 0b00000010]

    assert good_daytime_qc(np.array(quality)).tolist() == [
        True,
        True,
        False,
        False,
        False,
    ]


def test_sinusoidal_pixel_centers_are_deterministic_for_modis_tile():
    latitude, longitude = tile_pixel_centers(
        "MOD11A2.A2024001.h12v04.061.2024011195232", (1200, 1200)
    )

    assert latitude.shape == (1200, 1200)
    assert longitude.shape == (1200, 1200)
    assert latitude[0, 0] > latitude[-1, 0]
    assert longitude[0, 0] < longitude[0, -1]


def test_bbox_coverage_helper_distinguishes_complete_and_partial_tiles():
    nyc_bbox = (-74.1, 40.6, -73.7, 40.9)
    london_bbox = (-0.35, 51.3, 0.2, 51.7)

    assert bbox_fully_covered_by_tile(
        "MOD11A2.A2024177.h12v04.061.2024186041340", nyc_bbox
    )
    assert not bbox_fully_covered_by_tile(
        "MOD11A2.A2024177.h17v03.061.2024186042347", london_bbox
    )


def test_annual_mean_is_weighted_for_short_final_composite():
    composites = []
    start = date(2024, 1, 1)
    while start.year == 2024:
        end = min(start + timedelta(days=7), date(2024, 12, 31))
        days = (end - start).days + 1
        value = 20.0 if end == date(2024, 12, 31) else 10.0
        composites.append(
            _composite(
                f"{start.isoformat()}T00:00:00Z",
                f"{end.isoformat()}T23:59:59Z",
                value,
                days,
            )
        )
        start = end + timedelta(days=1)

    assert annual_mean_celsius(composites, 2024) == 10.1639


def test_annual_mean_refuses_incomplete_coverage():
    with pytest.raises(Mod11A2ValidationError, match="coverage through December 31"):
        annual_mean_celsius(
            [_composite("2024-01-01T00:00:00Z", "2024-01-08T23:59:59Z", 10.0, 8)],
            2024,
        )
