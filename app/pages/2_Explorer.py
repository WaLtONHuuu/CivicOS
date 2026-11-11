import pandas as pd
import plotly.express as px
import streamlit as st

st.title("Map Explorer")


df = pd.read_csv("data/sample/nyc311_2026-10_first10000.csv") #Read the csv file into a pandas dataframe.


df = df.dropna(subset=["latitude", "longitude"]) #Drop rows where latitude or longitude is NaN.

boroughs = ["All"] + list(df["borough"].dropna().unique()) #Used for pick up a borough. 
choice = st.selectbox("Select a borough", boroughs)
if choice != "All":
    df = df[df["borough"] == choice]

st.write("Points on the map:", len(df))

fig = px.scatter_map(df, lat="latitude", lon="longitude", color="borough",
                     hover_name="complaint_type", zoom=9, height=600,
                     center={"lat": 40.7128, "lon": -74.0060},
                     map_style="carto-positron") #Visualize the nyc map with the points of the complaints; carto-positron is a free street basemap
st.plotly_chart(fig)
