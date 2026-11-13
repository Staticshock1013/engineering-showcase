import io
from datetime import date
from urllib.parse import parse_qs, urlparse

import pytest

from terratrend.nasa import (
    AuthenticationRequiredError,
    LAGOS,
    LONDON,
    LST_EXPANSION_CITIES,
    LiveDataUnavailableError,
    VERIFIED_LST_CITIES,
    MOD11A2_V061,
    MUMBAI,
    NEW_YORK_CITY,
    SAO_PAULO,
    TOKYO,
    build_granule_query,
    fetch_observations,
    protected_download_headers,
    search_granule_metadata,
)


def test_mod11a2_query_is_reproducible_for_new_york_city():
    query = build_granule_query(
        MOD11A2_V061, NEW_YORK_CITY, date(2024, 1, 1), date(2024, 2, 1)
    )
    parameters = parse_qs(urlparse(query).query)

    assert parameters["short_name"] == ["MOD11A2"]
    assert parameters["version"] == ["061"]
    assert parameters["bounding_box"] == ["-74.1,40.6,-73.7,40.9"]
    assert parameters["temporal"] == ["2024-01-01T00:00:00Z,2024-02-01T00:00:00Z"]
    assert MOD11A2_V061.raw_to_celsius(15000) == pytest.approx(26.85)


def test_london_city_bounds_are_explicit_for_reproducible_sampling():
    assert LONDON.name == "London"
    assert LONDON.bounding_box == (-0.35, 51.30, 0.20, 51.70)


def test_expansion_city_bounds_are_explicit_tile_contained_windows():
    assert LAGOS.bounding_box == (-3.50, 6.40, -3.25, 6.55)
    assert TOKYO.bounding_box == (139.60, 35.60, 139.85, 35.75)
    assert MUMBAI.bounding_box == (72.80, 18.90, 73.00, 19.10)
    assert SAO_PAULO.bounding_box == (-46.75, -23.65, -46.50, -23.45)
    assert LST_EXPANSION_CITIES == (LAGOS, TOKYO, MUMBAI, SAO_PAULO)
    assert len(VERIFIED_LST_CITIES) == 6
    assert VERIFIED_LST_CITIES[-1] == SAO_PAULO


def test_catalog_adapter_returns_metadata_provenance_without_observations():
    payload = {
        "items": [
            {
                "meta": {
                    "concept-id": "G2834222407-LPCLOUD",
                    "provider-id": "LPCLOUD",
                },
                "umm": {
                    "GranuleUR": "MOD11A2.A2024001.h12v04.061.2024011195232",
                    "CollectionReference": {"ShortName": "MOD11A2", "Version": "061"},
                    "TemporalExtent": {
                        "RangeDateTime": {
                            "BeginningDateTime": "2024-01-01T00:00:00.000Z",
                            "EndingDateTime": "2024-01-08T23:59:59.000Z",
                        }
                    },
                    "RelatedUrls": [
                        {
                            "Type": "GET DATA",
                            "URL": "https://example.invalid/lp-prod-protected/granule.hdf",
                        }
                    ],
                },
            }
        ]
    }

    provenance = search_granule_metadata(
        MOD11A2_V061,
        NEW_YORK_CITY,
        date(2024, 1, 1),
        date(2024, 2, 1),
        opener=lambda *_args, **_kwargs: io.StringIO(__import__("json").dumps(payload)),
    )

    assert provenance.granule_ur == "MOD11A2.A2024001.h12v04.061.2024011195232"
    assert provenance.cmr_concept_id == "G2834222407-LPCLOUD"
    assert provenance.data_url.endswith("granule.hdf")


def test_protected_download_refuses_missing_token_and_live_decoding():
    with pytest.MonkeyPatch.context() as patch:
        patch.delenv("EARTHDATA_TOKEN", raising=False)
        with pytest.raises(AuthenticationRequiredError, match="No EARTHDATA_TOKEN"):
            protected_download_headers()

    with pytest.raises(LiveDataUnavailableError, match="not implemented"):
        fetch_observations()
