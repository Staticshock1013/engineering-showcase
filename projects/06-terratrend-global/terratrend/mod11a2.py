"""Validated local processing for authenticated MOD11A2 Collection 6.1 files.

This module never obtains credentials or downloads data.  It only decodes an HDF4
file that a caller has already retrieved through authenticated Earthdata access.
The rules implemented below are taken from the official MOD11 User Guide v6.1:
https://lpdaac.usgs.gov/documents/715/MOD11_User_Guide_V61.pdf
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import json
from pathlib import Path
import re
from typing import Any

import numpy as np

from .nasa import City, GranuleProvenance, MOD11A2_V061

EARTH_RADIUS_METERS = 6_371_007.181
MODIS_TILE_WIDTH_METERS = 1_111_950.5196666666
MODIS_HORIZONTAL_TILES = 36
MODIS_VERTICAL_TILES = 18
PIXELS_PER_TILE = 1200
USER_GUIDE_URL = "https://lpdaac.usgs.gov/documents/715/MOD11_User_Guide_V61.pdf"
QC_RULE = "mandatory_qa=00 and lst_error<=2K"


class Mod11A2ValidationError(ValueError):
    """Raised when a file does not match the documented MOD11A2 specification."""


@dataclass(frozen=True)
class ProcessedComposite:
    """A spatial mean from one validated MOD11A2 eight-day composite."""

    granule_ur: str
    time_start: str
    time_end: str
    city: str
    bounding_box: tuple[float, float, float, float]
    mean_celsius: float
    selected_pixel_count: int
    valid_pixel_count: int
    temporal_days: int
    qc_rule: str = QC_RULE


def good_daytime_qc(qc_values: np.ndarray) -> np.ndarray:
    """Keep documented good LST pixels with a reported error no greater than 2 K."""
    mandatory_qa = qc_values & 0b11
    lst_error = (qc_values >> 6) & 0b11
    return (mandatory_qa == 0) & (lst_error <= 1)


def _granule_tile(granule_ur: str) -> tuple[int, int]:
    match = re.search(r"\.h(?P<h>\d{2})v(?P<v>\d{2})\.", granule_ur)
    if not match:
        raise Mod11A2ValidationError("Granule identifier does not contain a MODIS h/v tile.")
    horizontal, vertical = int(match["h"]), int(match["v"])
    if not (0 <= horizontal < MODIS_HORIZONTAL_TILES and 0 <= vertical < MODIS_VERTICAL_TILES):
        raise Mod11A2ValidationError("MODIS h/v tile is outside the documented global grid.")
    return horizontal, vertical


def tile_pixel_centers(granule_ur: str, shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    """Return latitude and longitude of MODIS sinusoidal pixel centers in degrees."""
    if shape != (PIXELS_PER_TILE, PIXELS_PER_TILE):
        raise Mod11A2ValidationError("MOD11A2 1 km tile must be exactly 1200 by 1200 pixels.")
    horizontal, vertical = _granule_tile(granule_ur)
    resolution = MODIS_TILE_WIDTH_METERS / PIXELS_PER_TILE
    x_min = -MODIS_TILE_WIDTH_METERS * (MODIS_HORIZONTAL_TILES / 2) + horizontal * MODIS_TILE_WIDTH_METERS
    y_max = MODIS_TILE_WIDTH_METERS * (MODIS_VERTICAL_TILES / 2) - vertical * MODIS_TILE_WIDTH_METERS
    columns = np.arange(PIXELS_PER_TILE, dtype=np.float64)
    rows = np.arange(PIXELS_PER_TILE, dtype=np.float64)
    x = x_min + (columns + 0.5) * resolution
    y = y_max - (rows + 0.5) * resolution
    latitude = np.degrees(y[:, None] / EARTH_RADIUS_METERS)
    longitude = np.degrees(x[None, :] / (EARTH_RADIUS_METERS * np.cos(np.radians(latitude))))
    return np.broadcast_to(latitude, shape), np.broadcast_to(longitude, shape)


def _attribute_value(attributes: dict[str, Any], name: str) -> Any:
    if name not in attributes:
        raise Mod11A2ValidationError(f"Required dataset attribute is missing: {name}.")
    return attributes[name]


def _validate_lst_metadata(attributes: dict[str, Any]) -> None:
    """Validate documented MOD11A2 LST metadata before using any pixels."""
    if float(_attribute_value(attributes, "scale_factor")) != MOD11A2_V061.scale_factor:
        raise Mod11A2ValidationError("LST scale factor does not match MOD11A2 v6.1 documentation.")
    if float(_attribute_value(attributes, "add_offset")) != 0.0:
        raise Mod11A2ValidationError("LST add offset does not match MOD11A2 v6.1 documentation.")
    if int(_attribute_value(attributes, "_FillValue")) != 0:
        raise Mod11A2ValidationError("LST fill value does not match MOD11A2 v6.1 documentation.")
    valid_range = list(_attribute_value(attributes, "valid_range"))
    if valid_range != [7500, 65535]:
        raise Mod11A2ValidationError("LST valid range does not match MOD11A2 v6.1 documentation.")
    if attributes.get("units") != "K":
        raise Mod11A2ValidationError("LST units must be Kelvin before Celsius conversion.")


def _composite_days(time_start: str, time_end: str) -> int:
    start = date.fromisoformat(time_start[:10])
    end = date.fromisoformat(time_end[:10])
    days = (end - start).days + 1
    if days <= 0:
        raise Mod11A2ValidationError("Granule temporal coverage is invalid.")
    return days


def process_hdf4_composite(path: Path, provenance: GranuleProvenance, city: City) -> ProcessedComposite:
    """Decode one validated MOD11A2 HDF4 granule into a city spatial mean."""
    try:
        from pyhdf.SD import SD, SDC
    except ImportError as error:
        raise Mod11A2ValidationError("pyhdf is required to decode MOD11A2 HDF4 files.") from error

    hdf = SD(str(path), SDC.READ)
    try:
        lst_dataset = hdf.select(MOD11A2_V061.source_variable)
        qc_dataset = hdf.select(MOD11A2_V061.quality_variable)
        _validate_lst_metadata(lst_dataset.attributes())
        lst = np.asarray(lst_dataset.get())
        qc = np.asarray(qc_dataset.get())
    finally:
        hdf.end()

    if lst.shape != qc.shape:
        raise Mod11A2ValidationError("LST and QC datasets must have the same dimensions.")
    latitude, longitude = tile_pixel_centers(provenance.granule_ur, lst.shape)
    west, south, east, north = city.bounding_box
    spatial_mask = (longitude >= west) & (longitude <= east) & (latitude >= south) & (latitude <= north)
    selected_pixel_count = int(np.count_nonzero(spatial_mask))
    if not selected_pixel_count:
        raise Mod11A2ValidationError("The requested bounding box does not intersect the granule tile.")

    valid_raw = (lst >= 7500) & (lst <= 65535) & (lst != 0)
    accepted = spatial_mask & valid_raw & good_daytime_qc(qc)
    valid_pixel_count = int(np.count_nonzero(accepted))
    if not valid_pixel_count:
        raise Mod11A2ValidationError("No pixels pass spatial, LST validity, and QC requirements.")

    celsius = lst[accepted].astype(np.float64) * MOD11A2_V061.scale_factor + MOD11A2_V061.offset_celsius
    return ProcessedComposite(
        granule_ur=provenance.granule_ur,
        time_start=provenance.time_start,
        time_end=provenance.time_end,
        city=city.name,
        bounding_box=city.bounding_box,
        mean_celsius=round(float(np.mean(celsius)), 4),
        selected_pixel_count=selected_pixel_count,
        valid_pixel_count=valid_pixel_count,
        temporal_days=_composite_days(provenance.time_start, provenance.time_end),
    )


def annual_mean_celsius(composites: list[ProcessedComposite], year: int) -> float:
    """Calculate a duration-weighted annual mean only for complete calendar coverage."""
    year_composites = sorted(
        (
            composite
            for composite in composites
            if date.fromisoformat(composite.time_start[:10]).year == year
        ),
        key=lambda composite: composite.time_start,
    )
    if not year_composites:
        raise Mod11A2ValidationError(f"No composites are available for {year}.")
    expected_start = date(year, 1, 1)
    for composite in year_composites:
        start = date.fromisoformat(composite.time_start[:10])
        end = date.fromisoformat(composite.time_end[:10])
        if start != expected_start or composite.temporal_days != (end - start).days + 1:
            raise Mod11A2ValidationError("Annual aggregation requires complete, contiguous coverage.")
        expected_start = date.fromordinal(end.toordinal() + 1)
    if expected_start != date(year + 1, 1, 1):
        raise Mod11A2ValidationError("Annual aggregation requires coverage through December 31.")
    total_days = sum(composite.temporal_days for composite in year_composites)
    return round(
        sum(composite.mean_celsius * composite.temporal_days for composite in year_composites)
        / total_days,
        4,
    )


def save_processed_composite(
    output_path: Path, composite: ProcessedComposite, provenance: GranuleProvenance
) -> None:
    """Write credential-free processed data and reproducible provenance outside fixtures."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "data_status": "verified_real_mod11a2_8_day_composite_not_annual",
        "product_documentation": USER_GUIDE_URL,
        "processing": {
            "source_variable": MOD11A2_V061.source_variable,
            "scale_factor": MOD11A2_V061.scale_factor,
            "offset_celsius": MOD11A2_V061.offset_celsius,
            "qc_rule": QC_RULE,
            "spatial_sampling": "MODIS sinusoidal pixel centers inside the stated bounding box",
        },
        "composite": asdict(composite),
        "provenance": asdict(provenance),
    }
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_processed_composite(path: Path) -> dict[str, Any]:
    """Load a cached, credential-free processed result for dashboard disclosure."""
    return json.loads(path.read_text(encoding="utf-8"))
