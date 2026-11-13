"""A small, explicit indicator registry for the Phase 1 dashboard."""

from dataclasses import dataclass


@dataclass(frozen=True)
class IndicatorDefinition:
    """Metadata needed to display and interpret an environmental indicator."""

    key: str
    name: str
    unit: str
    direction_note: str
    source_family: str
    description: str


@dataclass(frozen=True)
class VerifiedDataDefinition:
    """A source product approved for credential-free cached display."""

    key: str
    product_short_name: str
    version: str
    temporal_resolution: str
    data_status: str


INDICATOR_REGISTRY = {
    "surface_temperature_anomaly": IndicatorDefinition(
        key="surface_temperature_anomaly",
        name="Surface temperature anomaly",
        unit="°C",
        direction_note="Positive values are warmer than the reference baseline.",
        source_family="NASA Earth observation (planned)",
        description="Synthetic regional temperature anomaly relative to a stated baseline.",
    ),
    "vegetation_index_anomaly": IndicatorDefinition(
        key="vegetation_index_anomaly",
        name="Vegetation index anomaly",
        unit="NDVI anomaly",
        direction_note="Negative values indicate less vegetation greenness than the baseline.",
        source_family="NASA Earth observation (planned)",
        description="Synthetic regional vegetation anomaly suitable for dashboard prototyping.",
    ),
    "precipitation_anomaly": IndicatorDefinition(
        key="precipitation_anomaly",
        name="Precipitation anomaly",
        unit="mm/month",
        direction_note="Negative values indicate drier-than-baseline conditions.",
        source_family="NASA Earth observation (planned)",
        description="Synthetic monthly precipitation departure from a reference baseline.",
    ),
}

VERIFIED_DATA_REGISTRY = {
    "mod11a2_v061_daytime_lst": VerifiedDataDefinition(
        key="mod11a2_v061_daytime_lst",
        product_short_name="MOD11A2",
        version="061",
        temporal_resolution="8-day composite",
        data_status="verified_real_mod11a2_8_day_composite_not_annual",
    )
}
