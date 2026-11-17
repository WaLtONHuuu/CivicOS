import plotly.express as px
import streamlit as st

from db import get_map_boroughs, get_map_complaint_types, get_map_counts, get_map_preview
from ui_helpers import date_controls, show_data_info


st.title("Map Explorer")
info = show_data_info()
st.sidebar.header("Filters")
start_date, end_date = date_controls(info)

boroughs = ["All"] + get_map_boroughs(start_date, end_date)
borough = st.selectbox("Select a borough", boroughs)
types = ["All"] + get_map_complaint_types(borough, start_date, end_date)
complaint_type = st.selectbox("Select a complaint type", types)
limit = st.slider("Maximum map points", 500, 20000, 10000, 500)

total, geocoded = get_map_counts(borough, complaint_type, start_date, end_date)
points = get_map_preview(borough, complaint_type, start_date, end_date, limit)

col1, col2, col3 = st.columns(3)
col1.metric("Matching requests", f"{total:,}")
col2.metric("Valid coordinates", f"{geocoded:,}")
col3.metric("Points shown", f"{len(points):,}")
if geocoded > len(points):
    st.caption("Showing the earliest matching points, ordered by creation time and request ID.")
st.caption(f"Requests without valid coordinates: {total - geocoded:,}")

if points.empty:
    st.info("No map points match these filters.")
    st.stop()

# Center the map on the points we are showing.
fig = px.scatter_map(
    points, lat="latitude", lon="longitude", color="borough",
    hover_name="complaint_type",
    hover_data=["unique_key", "created_date"],
    center={"lat": points["latitude"].median(), "lon": points["longitude"].median()},
    zoom=9, height=600, map_style="carto-positron",
)
st.plotly_chart(fig)
with st.expander("View displayed points"):
    st.dataframe(points.head(1000), hide_index=True)
    st.caption("The table shows up to 1,000 rows. The download includes every displayed map point.")
    st.download_button(
        "Download displayed points", points.to_csv(index=False),
        "map_points.csv", "text/csv"
    )
