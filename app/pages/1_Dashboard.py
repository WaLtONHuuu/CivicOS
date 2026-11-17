import pandas as pd
import plotly.express as px
import streamlit as st

from db import (
    get_dashboard_baseline,
    get_dashboard_boroughs,
    get_dashboard_complaint_types,
    get_dashboard_requests,
    get_dashboard_statuses,
)

from ui_helpers import date_controls, show_data_info

st.title("Statistics")


# line color
BOROUGH_COLORS = {
    "BROOKLYN": "#2a78d6",
    "QUEENS": "#eb6834",
    "MANHATTAN": "#1baf7a",
    "BRONX": "#eda100",
    "STATEN ISLAND": "#e87ba4",
    "Unspecified": "#9a9a9a",
    "Selected total": "#6250d6"
}
MIN_CLOSED = 20  # groups with fewer closed requests are too small to compare

info = show_data_info()
st.sidebar.header("Filters")
start_date, end_date = date_controls(info)
baseline = get_dashboard_baseline(start_date, end_date)
all_total = baseline["total"]
all_rate = baseline["closed_rate"]
all_median = baseline["median"]
last_hour = baseline["last_hour"]

boroughs = get_dashboard_boroughs(start_date, end_date)
picked_boroughs = st.sidebar.multiselect("Boroughs", boroughs, default=boroughs)

statuses = get_dashboard_statuses(picked_boroughs, start_date, end_date)
picked_statuses = st.sidebar.multiselect("Status", statuses, default=statuses)

start_hour, end_hour = st.sidebar.slider("Hour of the day", 0, 23, (0, 23))
complaint_types = ["All"] + get_dashboard_complaint_types(
    picked_boroughs, picked_statuses, start_hour, end_hour, start_date, end_date
)
complaint_type = st.sidebar.selectbox("Complaint type", complaint_types)

df = get_dashboard_requests(
    picked_boroughs, picked_statuses, start_hour, end_hour, complaint_type, start_date, end_date
)

if len(df) == 0:# Nothing to show.
    st.warning("No requests match these filters. Try changing them in the sidebar.")
    st.stop()

closed_df = df[(df["status"] == "Closed") & (df["hours"] >= 0)]# Keep valid closed requests.


total = len(df)# Numbers for the current filters.
closed = (df["status"] == "Closed").sum()
rate = closed / total * 100
is_filtered = total < all_total  # only compare when some filter is on

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total requests", f"{total:,}")
col2.metric("Closed", f"{closed:,}")
if is_filtered:
    col3.metric("Closed rate", f"{rate:.1f}%", f"{rate - all_rate:+.1f} pts vs date range")
else:
    col3.metric("Closed rate", f"{rate:.1f}%")
if len(closed_df) == 0:
    col4.metric("Median time to close", "N/A")
elif is_filtered:
    median = closed_df["hours"].median()
    # delta_color="inverse": a shorter time is good, so show it in green
    col4.metric("Median time to close", f"{median:.1f} h", f"{median - all_median:+.1f} h vs date range",
                delta_color="inverse")
else:
    col4.metric("Median time to close", f"{closed_df['hours'].median():.1f} h")


tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["Request trend", "Share by borough", "Complaint types",
     "Time to close", "Space-time view", "Raw data"]
)# The six views use the same filters.


with tab1:
    interval = st.radio("Group time by", ["Hour", "Day"], horizontal=True)
    trend_rows = df.copy()
    if interval == "Hour":
        # This sample ends at 20:07, so its last hour is only partly recorded.
        sample_day = (
            info["total"] == 10000
            and info["first_record"][:10] == "2026-10-01"
            and info["last_record"][:16] == "2026-10-01T20:07"
        )
        if sample_day:
            keep_partial = st.checkbox("Include the partial final hour", value=False)
            if not keep_partial:
                trend_rows = trend_rows[trend_rows["hour"] < last_hour]
        trend_rows["time"] = pd.to_datetime(trend_rows["created_date"]).dt.floor("h")
    else:
        trend_rows["time"] = pd.to_datetime(trend_rows["created_date"]).dt.normalize()

    trend = trend_rows.groupby(["time", "borough"]).size().reset_index(name="requests")
    if trend.empty:
        st.info("No complete hours to plot. Try including the partial final hour.")
    else:
        total_line = trend.groupby("time")["requests"].sum().reset_index()
        total_line["borough"] = "Selected total"
        trend = pd.concat([trend, total_line])
        fig = px.line(
            trend, x="time", y="requests", color="borough", markers=True,
            color_discrete_map=BOROUGH_COLORS,
            labels={"time": "New York local time", "requests": "Requests"},
        )
        fig.update_layout(hovermode="x unified")
        st.plotly_chart(fig)
        st.download_button("Download trend", trend.to_csv(index=False), "request_trend.csv", "text/csv")


with tab2:# Pie chart
    by_borough = df["borough"].value_counts().reset_index()  # columns: borough, count
    fig = px.pie(by_borough, names="borough", values="count", color="borough",
                 color_discrete_map=BOROUGH_COLORS, hole=0.4)
    fig.update_traces(textinfo="percent+label")
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig)


with tab3:# Most common complaint types
    top_n = st.slider("How many complaint types to show", 5, 30, 10)
    top_types = df["complaint_type"].value_counts().head(top_n).reset_index()
    fig = px.bar(top_types, x="count", y="complaint_type", orientation="h",
                 labels={"count": "Requests", "complaint_type": "Complaint type"},
                 height=300 + top_n * 15)
    fig.update_yaxes(autorange="reversed")  # biggest bar on top
    st.plotly_chart(fig)


with tab4:# Time to close
    if len(closed_df) == 0:
        st.info("No closed requests for these filters.")
    else:
        group_by = st.radio("Group by", ["Borough", "Complaint type"], horizontal=True)
        stat = st.radio("Statistic", ["Median", "Average"], horizontal=True)
        column = "borough" if group_by == "Borough" else "complaint_type"

        counts = closed_df[column].value_counts()# Count valid rows in each group.
        big_groups = counts[counts >= MIN_CLOSED].index
        kept_df = closed_df[closed_df[column].isin(big_groups)]

        if len(kept_df) == 0:
            st.info(f"No group has at least {MIN_CLOSED} closed requests.")
        else:
            if stat == "Median":
                hours = kept_df.groupby(column)["hours"].median()
            else:
                hours = kept_df.groupby(column)["hours"].mean()
            hours = hours.round(1).sort_values(ascending=False).reset_index()

            if group_by == "Borough":
                fig = px.bar(hours, x="borough", y="hours", color="borough",
                             color_discrete_map=BOROUGH_COLORS,
                             labels={"borough": "Borough", "hours": f"{stat} hours to close"})
                fig.update_layout(showlegend=False)
            else:
                hours = hours.head(15)  # the 15 slowest types
                fig = px.bar(hours, x="hours", y="complaint_type", orientation="h",
                             labels={"complaint_type": "Complaint type",
                                     "hours": f"{stat} hours to close"}, height=550)
                fig.update_yaxes(autorange="reversed")  # slowest on top
            st.plotly_chart(fig)

            skipped = len(counts) - len(big_groups)
            if skipped > 0:
                st.caption(f"Not shown (fewer than {MIN_CLOSED} closed requests): {skipped}")
            st.caption("Median is usually smaller: a few very slow requests pull the average up.")


with tab5:  # 3D scatter plot
    points = df[df["latitude"].between(-90, 90) & df["longitude"].between(-180, 180)]
    point_limit = st.slider("3D point limit", 500, 10000, 5000, 500)
    available = len(points)
    if available > point_limit:
        points = points.sample(point_limit, random_state=42)
    st.caption(f"Showing {len(points):,} of {available:,} valid points.")
    points = points.copy()
    points["plot_time"] = pd.to_datetime(points["created_date"])
    fig = px.scatter_3d(points, x="longitude", y="latitude", z="plot_time", color="borough",
                        color_discrete_map=BOROUGH_COLORS, hover_name="complaint_type",
                        height=650, labels={"plot_time": "Created time", "borough": "Borough"})
    fig.update_traces(marker={"size": 2})
    st.plotly_chart(fig)
    st.caption("Drag to rotate. Each dot is one request: the floor is the map, height is the creation time.")


with st.expander("Status counts and coordinate coverage"):
    status_counts = df["status"].fillna("Unspecified").value_counts().reset_index()
    status_counts.columns = ["Status", "Requests"]
    st.dataframe(status_counts, hide_index=True)
    good_coordinates = df["latitude"].between(-90, 90) & df["longitude"].between(-180, 180)
    st.write(f"Valid coordinates: {good_coordinates.sum():,} / {total:,}")
    st.write(f"Coordinate coverage: {good_coordinates.mean() * 100:.1f}%")


with tab6:  # Raw data
    columns = ["unique_key", "created_date", "complaint_type", "borough", "status"]
    search = st.text_input("Search request ID")
    shown = df
    if search:
        shown = df[df["unique_key"].str.contains(search, regex=False, na=False)]
    st.caption(f"{len(shown):,} matching rows. The table shows up to 1,000.")
    st.dataframe(shown[columns].head(1000), hide_index=True)
    csv = shown[columns].to_csv(index=False)
    st.download_button("Download as CSV", csv, "filtered_requests.csv", "text/csv")
