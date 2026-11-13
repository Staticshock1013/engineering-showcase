"""Streamlit entry point for the TerraTrend Global Phase 1 MVP."""

import plotly.express as px
import streamlit as st

from terratrend.data import load_observations
from terratrend.dashboard import load_verified_cache_state
from terratrend.registry import INDICATOR_REGISTRY, VERIFIED_DATA_REGISTRY
from terratrend.statistics import indicator_summary, regional_means

st.set_page_config(page_title="TerraTrend Global", page_icon="🌍", layout="wide")
st.title("TerraTrend Global")
st.caption("Environmental-change intelligence MVP — synthetic global prototype with verified samples")
st.warning(
    "The global charts below use deterministic synthetic fixtures only. They are not NASA data "
    "and must not be used for scientific or operational decisions."
)

cache_state = load_verified_cache_state()
verified_caches = cache_state.entries
if cache_state.status == "unavailable":
    st.error(
        "Verified processed data could not be loaded, so it is not displayed. "
        "The global charts remain labeled synthetic fixtures."
    )
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
    with st.expander("Verified MOD11A2 sample provenance"):
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
else:
    st.info(
        "No verified processed cache is available. Only the clearly labeled synthetic global "
        "prototype is shown."
    )

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

with st.expander("Data provenance and scope"):
    st.write(
        "The global map and regional bars use labeled deterministic fixtures. Verified MOD11A2 "
        "entries, when available above, are separate authenticated source-data caches with "
        "product, CMR, and processing provenance. Neither single 8-day sample is annual or global."
    )
    st.code(definition.source_family)
