"""Validated local processing for authenticated MOD13A2 Collection 6.1 NDVI files."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import json
from pathlib import Path
from typing import Any

import numpy as np

from .mod11a2 import Mod11A2ValidationError, tile_pixel_centers
from .nasa import City, GranuleProvenance
from .registry import VERIFIED_DATA_REGISTRY

PRODUCT_SHORT_NAME = "MOD13A2"
PRODUCT_VERSION = "061"
NDVI_DATASET = "1 km 16 days NDVI"
DETAILED_QA_DATASET = "1 km 16 days VI Quality"
PIXEL_RELIABILITY_DATASET = "1 km 16 days pixel reliability"
NDVI_SCALE_DIVISOR = 10_000.0
NDVI_FILL_VALUE = -3000
NDVI_VALID_RANGE = (-2000, 10000)
PRODUCT_DOCUMENTATION_URL = "https://lpdaac.usgs.gov/documents/621/MOD13_User_Guide_V61.pdf"
QC_RULE = "detailed_vi_quality_bits_0_1=00 and pixel_reliability=0"


@dataclass(frozen=True)
class ProcessedNDVIComposite:
    """A spatial mean from one validated MOD13A2 16-day composite."""

    granule_ur: str
    time_start: str
    time_end: str
    city: str
    bounding_box: tuple[float, float, float, float]
    mean_ndvi: float
    selected_pixel_count: int
    valid_pixel_count: int
    temporal_days: int
    qc_rule: str = QC_RULE


def good_ndvi_qc(detailed_qa: np.ndarray, pixel_reliability: np.ndarray) -> np.ndarray:
    """Accept only documented good MODLAND VI quality and summary reliability pixels."""
    return ((detailed_qa & 0b11) == 0) & (pixel_reliability == 0)


def _require_attribute(attributes: dict[str, Any], name: str) -> Any:
    if name not in attributes:
        raise Mod11A2ValidationError(f"Required MOD13A2 attribute is missing: {name}.")
    return attributes[name]


def _validate_ndvi_metadata(attributes: dict[str, Any]) -> None:
    """Validate the product guide's NDVI range and scale against in-file metadata."""
    if float(_require_attribute(attributes, "scale_factor")) != NDVI_SCALE_DIVISOR:
        raise Mod11A2ValidationError("MOD13A2 NDVI scale divisor does not match in-file metadata.")
    if float(_require_attribute(attributes, "add_offset")) != 0.0:
        raise Mod11A2ValidationError("MOD13A2 NDVI offset must be zero.")
    if int(_require_attribute(attributes, "_FillValue")) != NDVI_FILL_VALUE:
        raise Mod11A2ValidationError("MOD13A2 NDVI fill value does not match the product guide.")
    if tuple(_require_attribute(attributes, "valid_range")) != NDVI_VALID_RANGE:
        raise Mod11A2ValidationError("MOD13A2 NDVI valid range does not match the product guide.")
    if attributes.get("units") != "NDVI":
        raise Mod11A2ValidationError("MOD13A2 NDVI units are invalid.")


def _validate_quality_metadata(detailed: dict[str, Any], reliability: dict[str, Any]) -> None:
    if int(_require_attribute(detailed, "_FillValue")) != 65535:
        raise Mod11A2ValidationError("MOD13A2 detailed QA fill value is invalid.")
    if tuple(_require_attribute(detailed, "valid_range")) != (0, 65534):
        raise Mod11A2ValidationError("MOD13A2 detailed QA range is invalid.")
    if int(_require_attribute(reliability, "_FillValue")) != -1:
        raise Mod11A2ValidationError("MOD13A2 pixel reliability fill value is invalid.")
    if tuple(_require_attribute(reliability, "valid_range")) != (0, 3):
        raise Mod11A2ValidationError("MOD13A2 pixel reliability range is invalid.")


def process_hdf4_ndvi_composite(
    path: Path, provenance: GranuleProvenance, city: City
) -> ProcessedNDVIComposite:
    """Decode one validated MOD13A2 file into a bounded-city NDVI mean."""
    if provenance.product_short_name != PRODUCT_SHORT_NAME or provenance.product_version != PRODUCT_VERSION:
        raise Mod11A2ValidationError("Provenance does not identify MOD13A2 Collection 6.1.")
    try:
        from pyhdf.SD import SD, SDC
    except ImportError as error:
        raise Mod11A2ValidationError("pyhdf is required to decode MOD13A2 HDF4 files.") from error

    hdf = SD(str(path), SDC.READ)
    try:
        ndvi_dataset = hdf.select(NDVI_DATASET)
        detailed_dataset = hdf.select(DETAILED_QA_DATASET)
        reliability_dataset = hdf.select(PIXEL_RELIABILITY_DATASET)
        _validate_ndvi_metadata(ndvi_dataset.attributes())
        _validate_quality_metadata(detailed_dataset.attributes(), reliability_dataset.attributes())
        ndvi = np.asarray(ndvi_dataset.get())
        detailed_qa = np.asarray(detailed_dataset.get())
        pixel_reliability = np.asarray(reliability_dataset.get())
    finally:
        hdf.end()

    if ndvi.shape != detailed_qa.shape or ndvi.shape != pixel_reliability.shape:
        raise Mod11A2ValidationError("MOD13A2 NDVI and QA datasets must have matching dimensions.")
    latitude, longitude = tile_pixel_centers(provenance.granule_ur, ndvi.shape)
    west, south, east, north = city.bounding_box
    if not (
        longitude.min() <= west <= longitude.max()
        and longitude.min() <= east <= longitude.max()
        and latitude.min() <= south <= latitude.max()
        and latitude.min() <= north <= latitude.max()
    ):
        raise Mod11A2ValidationError("City bounding box is not fully represented by the MODIS tile.")
    spatial = (longitude >= west) & (longitude <= east) & (latitude >= south) & (latitude <= north)
    selected_pixel_count = int(np.count_nonzero(spatial))
    if not selected_pixel_count:
        raise Mod11A2ValidationError("No MOD13A2 pixels intersect the requested city bounding box.")
    valid_ndvi = (ndvi >= NDVI_VALID_RANGE[0]) & (ndvi <= NDVI_VALID_RANGE[1]) & (ndvi != NDVI_FILL_VALUE)
    accepted = spatial & valid_ndvi & good_ndvi_qc(detailed_qa, pixel_reliability)
    valid_pixel_count = int(np.count_nonzero(accepted))
    if not valid_pixel_count:
        raise Mod11A2ValidationError("No MOD13A2 pixels pass spatial, NDVI, and QC validation.")
    start = provenance.time_start[:10]
    end = provenance.time_end[:10]
    return ProcessedNDVIComposite(
        granule_ur=provenance.granule_ur,
        time_start=provenance.time_start,
        time_end=provenance.time_end,
        city=city.name,
        bounding_box=city.bounding_box,
        mean_ndvi=round(float(np.mean(ndvi[accepted].astype(np.float64) / NDVI_SCALE_DIVISOR)), 4),
        selected_pixel_count=selected_pixel_count,
        valid_pixel_count=valid_pixel_count,
        temporal_days=(date.fromisoformat(end) - date.fromisoformat(start)).days + 1,
    )


def save_processed_ndvi_composite(
    output_path: Path, composite: ProcessedNDVIComposite, provenance: GranuleProvenance
) -> None:
    """Write a credential-free, period-level MOD13A2 cache and provenance."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "data_product_key": "mod13a2_v061_ndvi",
        "data_status": VERIFIED_DATA_REGISTRY["mod13a2_v061_ndvi"].data_status,
        "product_documentation": PRODUCT_DOCUMENTATION_URL,
        "processing": {
            "source_variable": NDVI_DATASET,
            "scale_factor": 0.0001,
            "in_file_scale_divisor": NDVI_SCALE_DIVISOR,
            "qc_rule": QC_RULE,
            "spatial_sampling": "MODIS sinusoidal pixel centers inside the complete stated bounding box",
        },
        "composite": asdict(composite),
        "provenance": asdict(provenance),
    }
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
