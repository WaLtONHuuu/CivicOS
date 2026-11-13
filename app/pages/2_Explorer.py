import plotly.express as px
import streamlit as st

import db

st.title("Map Explorer")

try:
    boroughs = db.get_map_boroughs()
except FileNotFoundError as error:
    st.error(str(error))
    st.stop()

borough = st.selectbox("Select a borough", ["All"] + boroughs)
complaint_types = db.get_map_complaint_types(borough)
complaint_type = st.selectbox("Select a complaint type", ["All"] + complaint_types)

points = db.get_map_points(borough, complaint_type)
st.write("Points on the map:", len(points))
if points.empty:
    st.info("No requests with map coordinates match these filters.")
    st.stop()

fig = px.scatter_map(points, lat="latitude", lon="longitude", color="borough",
                     hover_name="complaint_type", zoom=9, height=600,
                     center={"lat": 40.7128, "lon": -74.0060},
                     map_style="carto-positron")
st.plotly_chart(fig)
