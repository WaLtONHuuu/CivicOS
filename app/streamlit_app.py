import streamlit as st

from ui_helpers import show_data_info


st.title("CivicOS")
st.write("Explore NYC 311 requests by date, borough, and complaint type.")
show_data_info()
st.page_link("pages/1_Dashboard.py", label="Open Dashboard")
st.page_link("pages/2_Explorer.py", label="Open Map Explorer")
