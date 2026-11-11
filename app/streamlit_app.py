import csv

import streamlit as st

csv_path = "data/sample/nyc311_2026-10_first10000.csv"
points = []
total = 0

with open(csv_path, "r", newline="") as file:
    for row in csv.DictReader(file):
        total += 1
        if row["longitude"] and row["latitude"]:
            longitude = float(row["longitude"])
            latitude = float(row["latitude"])
            if -180 <= longitude <= 180 and -90 <= latitude <= 90:
                points.append({"longitude": longitude, "latitude": latitude})

st.set_page_config(page_title="CivicOS | NYC 311", layout="wide")
st.title("NYC 311 request map")
st.caption(
    f"October 1, 2026 · Partial day · {len(points):,} of {total:,} "
    "sample requests have map coordinates."
)
st.map(points, size=40, color="#FF0000")
