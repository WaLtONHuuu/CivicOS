from datetime import date

import pandas as pd
import streamlit as st

from db import DEFAULT_DB_PATH, get_data_info, get_db_path


def show_data_info():
    path = get_db_path()
    if not path.is_file():
        st.error(f"Database file not found: {path}")
        if path == DEFAULT_DB_PATH:
            st.info("Run py app/db.py from your project folder first.")
        st.stop()
    try:
        info = get_data_info()
    except (pd.errors.DatabaseError, ValueError) as error:
        st.error(f"Could not read this database: {error}")
        st.stop()
    if info["total"] == 0:
        st.info("This database is empty. Import a CSV first.")
        st.stop()
    st.caption(
        f"Available records: {info['first_record']} to {info['last_record']} "
        "(New York local time)."
    )
    st.caption("Counts describe imported records. Date coverage alone does not confirm complete days.")
    with st.expander("About the data"):
        st.write(f"Database: {path.name}")
        st.write(f"Requests: {int(info['total']):,}")
        st.write(f"Valid coordinates: {int(info['geocoded']):,}")
        st.write(f"Missing or invalid coordinates: {int(info['total'] - info['geocoded']):,}")
    return info


def date_controls(info):
    first = date.fromisoformat(info["first_record"][:10])
    last = date.fromisoformat(info["last_record"][:10])
    # Start with one day so a large database opens more quickly.
    start = st.sidebar.date_input("Start date", last, min_value=first, max_value=last)
    end = st.sidebar.date_input("End date", last, min_value=first, max_value=last)
    if start > end:
        st.warning("Start date needs to be on or before end date.")
        st.stop()
    return start, end
