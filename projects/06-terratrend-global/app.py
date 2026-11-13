"""Streamlit entry point for the TerraTrend Global Phase 1 MVP."""

import plotly.express as px
import streamlit as st

from terratrend.cache import load_verified_cache_registry
from terratrend.data import load_observations
from terratrend.registry import INDICATOR_REGISTRY
from terratrend.statistics import indicator_summary, regional_means

st.set_page_config(page_title="TerraTrend Global", page_icon="🌍", layout="wide")
st.title("TerraTrend Global")
st.caption("Phase 1 environmental-change intelligence MVP")
st.warning(
    "The global charts below use deterministic synthetic fixtures only. They are not NASA data "
    "and must not be used for scientific or operational decisions."
)

verified_caches = load_verified_cache_registry()
if verified_caches:
    processed = st.selectbox(
        "Verified processed MOD11A2 cache",
        verified_caches,
        format_func=lambda item: (
            f"{item['composite']['city']} — {item['composite']['time_start'][:10]} "
            f"to {item['composite']['time_end'][:10]}"
        ),
    )
    composite = processed["composite"]
    st.info(
        "Verified real-data state: the selected MOD11A2 v6.1 daytime 8-day composite is "
        "locally processed and registry-validated. It is not an annual or global result."
    )
    verified_columns = st.columns(3)
    verified_columns[0].metric("Verified sample mean (°C)", composite["mean_celsius"])
    verified_columns[1].metric("QC-passing pixels", composite["valid_pixel_count"])
    verified_columns[2].metric("Spatially sampled pixels", composite["selected_pixel_count"])
    with st.expander("Verified MOD11A2 sample provenance"):
        st.json(
            {
                "data_status": processed["data_status"],
                "product": processed["provenance"]["product_short_name"],
                "version": processed["provenance"]["product_version"],
                "granule": processed["provenance"]["granule_ur"],
                "time_start": composite["time_start"],
                "time_end": composite["time_end"],
                "qc_rule": processed["processing"]["qc_rule"],
            }
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
        "This MVP contains a compact registry and labeled, deterministic CSV fixtures only. "
        "A live data connector is intentionally out of scope for Phase 1."
    )
    st.code(definition.source_family)
