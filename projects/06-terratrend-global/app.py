"""Streamlit entry point for the TerraTrend Global Phase 1 MVP."""

import json
from pathlib import Path

import plotly.express as px
import streamlit as st

from terratrend.availability import availability_map_rows
from terratrend.data import load_observations
from terratrend.dashboard import load_lst_availability_state, load_verified_cache_state
from terratrend.presentation import (
    compare_fixed_season_trends,
    compare_verified_cities,
    synthetic_fixture_csv,
    verified_cache_csv,
)
from terratrend.registry import INDICATOR_REGISTRY, LST_EXPANSION_COVERAGE, VERIFIED_DATA_REGISTRY
from terratrend.ndvi_series import load_fixed_season_series
from terratrend.statistics import indicator_summary, regional_means

NDVI_SERIES_DIRECTORIES = (
    Path(__file__).parent / "terratrend" / "series" / "nyc-mod13a2-doy177",
    Path(__file__).parent / "terratrend" / "series" / "london-west-tile-mod13a2-doy177",
)

st.set_page_config(page_title="TerraTrend Global", page_icon="🌍", layout="wide")
st.title("TerraTrend Global")
st.caption("Environmental-change intelligence MVP — synthetic global prototype with verified samples")
st.warning(
    "The global charts below use deterministic synthetic fixtures only. They are not NASA data "
    "and must not be used for scientific or operational decisions."
)

cache_state = load_verified_cache_state()
verified_caches = cache_state.entries
availability_state = load_lst_availability_state()
if cache_state.status == "unavailable":
    st.error(
        "Verified processed data could not be loaded, so it is not displayed. "
        "The global charts remain labeled synthetic fixtures."
    )
if availability_state.status == "unavailable":
    st.error(
        "Expansion-city LST availability could not be loaded. No fabricated city values are shown."
    )
elif availability_state.cities:
    st.subheader("Expansion-city MOD11A2 LST availability")
    st.caption(
        "Lagos, Tokyo, Mumbai, and São Paulo use tile-contained sampling windows. "
        "The preferred shared period is 2024-06-25 to 2024-07-02 when a single MODIS tile "
        "fully covers the bbox. Failed preferred windows are marked unavailable; alternate "
        "verified periods are not forced into cross-city comparison and are not city-wide or annual."
    )
    availability_rows = [
        {
            "city": city.city,
            "status": city.status,
            "shared_window": city.shared_window_status,
            "period_start": (city.period_start or "")[:10] or None,
            "period_end": (city.period_end or "")[:10] or None,
            "mean_celsius": city.mean_celsius,
            "valid_pixels": city.valid_pixel_count,
            "selected_pixels": city.selected_pixel_count,
            "registry_coverage": LST_EXPANSION_COVERAGE.get(city.city),
            "reason": city.reason,
        }
        for city in availability_state.cities
    ]
    st.dataframe(availability_rows, hide_index=True)
    availability_map = px.scatter_geo(
        availability_map_rows(availability_state.cities),
        lat="latitude",
        lon="longitude",
        color="availability",
        hover_name="city",
        hover_data={
            "shared_window": True,
            "period_start": True,
            "period_end": True,
            "mean_celsius": True,
            "reason": True,
            "latitude": False,
            "longitude": False,
        },
        projection="natural earth",
        title="Verified LST expansion cities (availability states, not synthetic fixtures)",
    )
    st.plotly_chart(availability_map, width="stretch")
if verified_caches:
    processed = st.selectbox(
        "Verified processed data variable",
        verified_caches,
        format_func=lambda item: (
            f"{VERIFIED_DATA_REGISTRY[item['data_product_key']].variable_name}: "
            f"{item['composite']['city']} — {item['composite']['time_start'][:10]} "
            f"to {item['composite']['time_end'][:10]}"
        ),
    )
    composite = processed["composite"]
    verified_definition = VERIFIED_DATA_REGISTRY[processed["data_product_key"]]
    mean_value = composite.get("mean_celsius", composite.get("mean_ndvi"))
    st.info(
        f"Verified real-data state: the selected {verified_definition.product_short_name} v"
        f"{verified_definition.version} {verified_definition.temporal_resolution} is locally "
        "processed and registry-validated. It is not an annual or global result."
    )
    verified_columns = st.columns(3)
    verified_columns[0].metric(f"Verified sample mean ({verified_definition.unit})", mean_value)
    verified_columns[1].metric("QC-passing pixels", composite["valid_pixel_count"])
    verified_columns[2].metric("Spatially sampled pixels", composite["selected_pixel_count"])
    with st.expander("Verified sample provenance"):
        st.json(
            {
                "data_status": processed["data_status"],
                "variable": verified_definition.variable_name,
                "product": processed["provenance"]["product_short_name"],
                "version": processed["provenance"]["product_version"],
                "provider": processed["provenance"]["provider"],
                "cmr_concept_id": processed["provenance"]["cmr_concept_id"],
                "granule": processed["provenance"]["granule_ur"],
                "time_start": composite["time_start"],
                "time_end": composite["time_end"],
                "qc_rule": processed["processing"]["qc_rule"],
                "product_documentation": processed["product_documentation"],
                "cmr_query": processed["provenance"]["query_url"],
                "source_data_url": processed["provenance"]["data_url"],
            }
        )
    st.download_button(
        "Download all verified period caches as CSV",
        data=verified_cache_csv(verified_caches),
        file_name="terratrend-verified-period-caches.csv",
        mime="text/csv",
        help="Includes product, QC, spatial sampling, temporal coverage, and CMR provenance.",
    )

    cache_by_path = {cache["cache_path"]: cache for cache in verified_caches}
    selected_cache_paths = st.multiselect(
        "Compare two verified city caches",
        options=list(cache_by_path),
        format_func=lambda path: (
            f"{VERIFIED_DATA_REGISTRY[cache_by_path[path]['data_product_key']].variable_name}: "
            f"{cache_by_path[path]['composite']['city']} — "
            f"{cache_by_path[path]['composite']['time_start'][:10]}"
        ),
        help=(
            "Only two caches with the same product, unit, QC/spatial method, and exact period "
            "can be compared. Synthetic fixtures are never eligible."
        ),
    )
    if selected_cache_paths:
        comparison = compare_verified_cities(
            [cache_by_path[path] for path in selected_cache_paths]
        )
        if comparison.compatible:
            st.success(comparison.reason)
            st.dataframe(comparison.rows, hide_index=True)
        else:
            st.warning(f"City comparison refused: {comparison.reason}")
else:
    st.info(
        "No verified processed cache is available. Only the clearly labeled synthetic global "
        "prototype is shown."
    )

ndvi_series_list = []
for series_directory in NDVI_SERIES_DIRECTORIES:
    try:
        ndvi_series = load_fixed_season_series(series_directory)
    except (OSError, ValueError, json.JSONDecodeError):
        ndvi_series = None
        st.error("Fixed-season NDVI series cache could not be loaded and is not displayed.")
    if ndvi_series:
        ndvi_series_list.append(ndvi_series)

for ndvi_series in ndvi_series_list:
    trend = ndvi_series["trend"]
    st.subheader(f"{ndvi_series['city']['name']} fixed-season NDVI series (DOY 177)")
    st.caption(
        "One validated MOD13A2 16-day composite near late June/early July per year (2010–2024). "
        "This is a fixed-season series, not annual NDVI."
    )
    if trend["status"] == "verified_fixed_season_ndvi_trend":
        st.info(
            "Trend is descriptive OLS over fixed-season composites only. It does not establish "
            "annual vegetation change, causation, or a general vegetation-health trend."
        )
        trend_columns = st.columns(4)
        trend_columns[0].metric("Slope (NDVI/year)", trend["slope_per_year"])
        trend_columns[1].metric(
            "95% slope interval",
            f"{trend['slope_ci_lower']} to {trend['slope_ci_upper']}",
        )
        trend_columns[2].metric("p-value", trend["p_value"])
        trend_columns[3].metric("Valid years", trend["count"])
        st.dataframe(ndvi_series["periods"], hide_index=True)
    else:
        st.warning(f"Fixed-season trend refused: {trend['reason']}")

if len(ndvi_series_list) >= 2:
    seasonal_comparison = compare_fixed_season_trends(ndvi_series_list)
    if seasonal_comparison.compatible:
        st.subheader("Qualified NYC/London fixed-season NDVI trend comparison")
        st.success(seasonal_comparison.reason)
        st.caption(
            "The comparison shows independently fitted, method-matched fixed-season trends. "
            "It does not test a difference between slopes and is not an annual comparison."
        )
        st.dataframe(seasonal_comparison.rows, hide_index=True)
    else:
        st.warning(f"Fixed-season city trend comparison refused: {seasonal_comparison.reason}")

observations = load_observations()
indicator_key = st.sidebar.selectbox(
    "Indicator",
    options=list(INDICATOR_REGISTRY),
    format_func=lambda key: INDICATOR_REGISTRY[key].name,
)
definition = INDICATOR_REGISTRY[indicator_key]
selected = [row for row in observations if row["indicator"] == indicator_key]
summary = indicator_summary(observations, indicator_key)

st.subheader(definition.name)
st.caption(f"{definition.description} Unit: {definition.unit}. {definition.direction_note}")

metric_columns = st.columns(4)
metric_columns[0].metric("Observations", summary["count"])
metric_columns[1].metric(f"Mean ({definition.unit})", summary["mean"])
metric_columns[2].metric("Minimum", summary["minimum"])
metric_columns[3].metric("Maximum", summary["maximum"])

map_frame = {
    "region": [row["region"] for row in selected],
    "latitude": [row["latitude"] for row in selected],
    "longitude": [row["longitude"] for row in selected],
    "month": [row["month"] for row in selected],
    "value": [row["value"] for row in selected],
}
map_figure = px.scatter_geo(
    map_frame,
    lat="latitude",
    lon="longitude",
    color="value",
    hover_name="region",
    hover_data={"month": True, "value": ":.2f", "latitude": False, "longitude": False},
    projection="natural earth",
    color_continuous_scale="RdBu_r",
    title="Synthetic observations by representative regional location",
)
st.plotly_chart(map_figure, width="stretch")

regional = regional_means(observations, indicator_key)
bar_figure = px.bar(
    regional,
    x="region",
    y="mean_value",
    labels={"mean_value": definition.unit, "region": "Region"},
    title="Mean synthetic value by region",
)
st.plotly_chart(bar_figure, width="stretch")
st.download_button(
    "Download selected synthetic fixture as CSV",
    data=synthetic_fixture_csv(selected, definition),
    file_name=f"terratrend-synthetic-{indicator_key}.csv",
    mime="text/csv",
    help="This CSV is explicitly labeled synthetic and is not verified Earth-observation data.",
)

with st.expander("Data provenance and scope"):
    st.write(
        "The global map and regional bars use labeled deterministic fixtures. Verified MOD11A2 "
        "entries, when available above, are separate authenticated source-data caches with "
        "product, CMR, and processing provenance. Expansion-city availability states disclose "
        "shared-window failures without fabricating values. No single 8-day sample is annual, "
        "city-wide, or global."
    )
    st.code(definition.source_family)
