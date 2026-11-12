import pandas as pd
import plotly.express as px
import streamlit as st

st.title("NYC 311 Dashboard")
st.caption("October 1, 2026 · First 10,000 requests, through 8:07 PM · Downloaded November 10, 2026 (UTC).")

df = pd.read_csv("data/sample/nyc311_2026-10_first10000.csv") # read the csv file as pandas dataframe
df["hour"] = pd.to_datetime(df["created_date"]).dt.floor("h") # neglect the min and sec, only keep the hour part of the time
sample_hours = pd.date_range(df["hour"].min(), df["hour"].max(), freq="h")

boroughs = ["All"] + sorted(df["borough"].dropna().unique()) # picking up according to borough
borough = st.selectbox("Select a borough", boroughs)
if borough != "All":
    df = df[df["borough"] == borough]

complaint_types = ["All"] + sorted(df["complaint_type"].dropna().unique()) # picking up according to complaint type
complaint_type = st.selectbox("Select a complaint type", complaint_types)
if complaint_type != "All":
    df = df[df["complaint_type"] == complaint_type]

total, types = st.columns(2) # show two columns
total.metric("Matching requests", f"{len(df):,}")
types.metric("Complaint types", df["complaint_type"].nunique())
st.caption("Counts include requests without map coordinates.")

st.subheader("Requests by hour")
hourly_counts = df["hour"].value_counts().reindex(sample_hours, fill_value=0) # set the num of complaint as 0 if there is no complaint in that hour
st.line_chart(hourly_counts, x_label="Hour (New York time)", y_label="Requests")
st.caption("The last hour only includes records through 8:07 PM.")

st.subheader("Requests by borough")
borough_counts = df["borough"].value_counts()
fig = px.bar(x=borough_counts.index, y=borough_counts.values, labels={"x": "Borough", "y": "Requests"}) # draw a bar chart to show the number of complaints in each borough
st.plotly_chart(fig)

st.subheader("Top 10 complaint types")
top_types = df["complaint_type"].value_counts().head(10)
fig = px.bar(x=top_types.values, y=top_types.index, orientation="h", labels={"x": "Requests", "y": "Complaint type"}) # draw a horizontal bar chart to show the top 10 complaint types
fig.update_yaxes(autorange="reversed")
st.plotly_chart(fig)
