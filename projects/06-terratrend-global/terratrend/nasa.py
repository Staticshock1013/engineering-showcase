"""NASA CMR metadata adapter with explicit protected-data failure modes.

This module searches public catalog metadata only. It deliberately does not download
or decode MODIS HDF data: a caller must establish authorized Earthdata access and
implement an auditable science pipeline before producing observations.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

CMR_GRANULES_ENDPOINT = "https://cmr.earthdata.nasa.gov/search/granules.umm_json"


class NasaAccessError(RuntimeError):
    """Base error for an unsuccessful NASA catalog or data-access operation."""


class AuthenticationRequiredError(NasaAccessError):
    """Raised before protected data access without a configured token."""


class NoGranulesFoundError(NasaAccessError):
    """Raised when CMR returns no granules for an explicit spatiotemporal query."""


class LiveDataUnavailableError(NasaAccessError):
    """Raised because this Phase 2 adapter intentionally does not decode HDF files."""


@dataclass(frozen=True)
class City:
    """Named point-of-interest search bounds, not a scientific area-of-interest geometry."""

    name: str
    bounding_box: tuple[float, float, float, float]


NEW_YORK_CITY = City("New York City", (-74.10, 40.60, -73.70, 40.90))
LONDON = City("London", (-0.35, 51.30, 0.20, 51.70))


@dataclass(frozen=True)
class ProductSpecification:
    """Product semantics that must be preserved when an ingestion pipeline is added."""

    short_name: str
    version: str
    source_variable: str
    quality_variable: str
    temporal_composite_days: int
    scale_factor: float
    offset_celsius: float
    quality_rule: str

    def raw_to_celsius(self, raw_value: int) -> float:
        """Convert a valid MOD11A2 LST raw digital number to degrees Celsius."""
        return raw_value * self.scale_factor + self.offset_celsius


MOD11A2_V061 = ProductSpecification(
    short_name="MOD11A2",
    version="061",
    source_variable="LST_Day_1km",
    quality_variable="QC_Day",
    temporal_composite_days=8,
    scale_factor=0.02,
    offset_celsius=-273.15,
    quality_rule=(
        "Accept pixels only after decoding QC_Day; retain the raw QA value and "
        "document the selected mandatory-QA bits and any uncertainty threshold."
    ),
)


@dataclass(frozen=True)
class GranuleProvenance:
    """Catalog facts saved alongside any future derived observation."""

    product_short_name: str
    product_version: str
    granule_ur: str
    cmr_concept_id: str
    provider: str
    time_start: str
    time_end: str
    data_url: str
    query_url: str


def build_granule_query(
    product: ProductSpecification, city: City, start: date, end: date
) -> str:
    """Create the reproducible public CMR metadata query for one city/time window."""
    west, south, east, north = city.bounding_box
    parameters = {
        "short_name": product.short_name,
        "version": product.version,
        "bounding_box": f"{west},{south},{east},{north}",
        "temporal": f"{start.isoformat()}T00:00:00Z,{end.isoformat()}T00:00:00Z",
        "page_size": "1",
    }
    return f"{CMR_GRANULES_ENDPOINT}?{urlencode(parameters)}"


def parse_granule_provenance(
    payload: dict[str, Any], product: ProductSpecification, query_url: str
) -> GranuleProvenance:
    """Validate the first CMR UMM result and retain catalog-provided provenance."""
    items = payload.get("items", [])
    if not items:
        raise NoGranulesFoundError("CMR returned no granules for the requested city and period.")
    item = items[0]
    metadata = item["meta"]
    umm = item["umm"]
    collection = umm["CollectionReference"]
    if collection["ShortName"] != product.short_name or collection["Version"] != product.version:
        raise NasaAccessError("CMR result does not match the requested product specification.")

    data_urls = [
        related["URL"]
        for related in umm.get("RelatedUrls", [])
        if related.get("Type") == "GET DATA"
    ]
    if not data_urls:
        raise NasaAccessError("CMR result has no declared GET DATA URL.")
    period = umm["TemporalExtent"]["RangeDateTime"]
    return GranuleProvenance(
        product_short_name=collection["ShortName"],
        product_version=collection["Version"],
        granule_ur=umm["GranuleUR"],
        cmr_concept_id=metadata["concept-id"],
        provider=metadata["provider-id"],
        time_start=period["BeginningDateTime"],
        time_end=period["EndingDateTime"],
        data_url=data_urls[0],
        query_url=query_url,
    )


def search_granule_metadata(
    product: ProductSpecification,
    city: City,
    start: date,
    end: date,
    opener: Callable[..., Any] = urlopen,
) -> GranuleProvenance:
    """Call public CMR metadata and return provenance, never an observation."""
    query_url = build_granule_query(product, city, start, end)
    request = Request(query_url, headers={"Accept": "application/json"})
    try:
        with opener(request, timeout=20) as response:
            payload = json.load(response)
    except HTTPError as error:
        if error.code in {401, 403}:
            raise AuthenticationRequiredError(
                "NASA rejected the request; configure authorized Earthdata access outside source control."
            ) from error
        raise NasaAccessError(f"NASA CMR request failed with HTTP {error.code}.") from error
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        raise NasaAccessError(f"NASA CMR metadata request failed: {error}") from error
    return parse_granule_provenance(payload, product, query_url)


def protected_download_headers() -> dict[str, str]:
    """Return a token header only when a preconfigured safe environment variable exists."""
    token = os.environ.get("EARTHDATA_TOKEN")
    if not token:
        raise AuthenticationRequiredError(
            "No EARTHDATA_TOKEN is configured. No protected download was attempted."
        )
    return {"Authorization": f"Bearer {token}"}


def fetch_observations(*_: Any, **__: Any) -> None:
    """Block accidental production claims until a vetted HDF/QA pipeline exists."""
    raise LiveDataUnavailableError(
        "Live MOD11A2 decoding is not implemented. Do not create observations from catalog metadata."
    )
