"""Streamlit entry point for the TerraTrend Global Phase 1 MVP."""

import plotly.express as px
import streamlit as st

from terratrend.data import load_observations
from terratrend.registry import INDICATOR_REGISTRY
from terratrend.statistics import indicator_summary, regional_means

st.set_page_config(page_title="TerraTrend Global", page_icon="🌍", layout="wide")
st.title("TerraTrend Global")
st.caption("Phase 1 environmental-change intelligence MVP")
st.warning(
    "All values in this dashboard are deterministic synthetic fixtures. "
    "They are not NASA data and must not be used for scientific or operational decisions."
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
