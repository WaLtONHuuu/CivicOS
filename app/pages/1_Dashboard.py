import pandas as pd
import plotly.express as px
import streamlit as st

st.title("Statistics")
st.caption("10,000 sample rows from one partial day (2026-10-01). Good for a demo, not for real conclusions.")

# line color
BOROUGH_COLORS = {
    "BROOKLYN": "#2a78d6",
    "QUEENS": "#eb6834",
    "MANHATTAN": "#1baf7a",
    "BRONX": "#eda100",
    "STATEN ISLAND": "#e87ba4",
    "Unspecified": "#9a9a9a",
    "New York total": "#6250d6"
}
MIN_CLOSED = 20  # groups with fewer closed requests are too small to compare

# Load the raw data
df = pd.read_csv("data/sample/nyc311_2026-10_first10000.csv")
df["hour"] = pd.to_datetime(df["created_date"]).dt.hour  # 0-23, used by most charts below
created = pd.to_datetime(df["created_date"])
closed_at = pd.to_datetime(df["closed_date"])
df["hours"] = (closed_at - created).dt.total_seconds() / 3600  # used for the time-to-close chart; negative values are invalid and will be dropped

last_hour = df["hour"].max()  # The sample stops in the middle of its last hour. Hourly charts only use complete hours.

all_total = len(df)#Numbers for the whole cith, used to compare with the filtered numbers
all_rate = (df["status"] == "Closed").sum() / all_total * 100
all_closed_df = df[(df["status"] == "Closed") & (df["hours"] >= 0)]
all_median = all_closed_df["hours"].median()

st.sidebar.header("Filters")#Filter the data by different labels.

boroughs = sorted(df["borough"].dropna().unique())
picked_boroughs = st.sidebar.multiselect("Boroughs", boroughs, default=boroughs)
df = df[df["borough"].isin(picked_boroughs)]

statuses = sorted(df["status"].dropna().unique())
picked_statuses = st.sidebar.multiselect("Status", statuses, default=statuses)
df = df[df["status"].isin(picked_statuses)]

start_hour, end_hour = st.sidebar.slider("Hour of the day", 0, 23, (0, 23))
df = df[(df["hour"] >= start_hour) & (df["hour"] <= end_hour)]

complaint_types = ["All"] + sorted(df["complaint_type"].dropna().unique())
complaint_type = st.sidebar.selectbox("Complaint type", complaint_types)
if complaint_type != "All":
    df = df[df["complaint_type"] == complaint_type]



if len(df) == 0:# stop here if nothing is left after filtering
    st.warning("No requests match these filters. Try changing them in the sidebar.")
    st.stop()

closed_df = df[(df["status"] == "Closed") & (df["hours"] >= 0)]#close time for the closed requests.


total = len(df)#Headline lines for the filtered data
closed = (df["status"] == "Closed").sum()
rate = closed / total * 100
is_filtered = total < all_total  # only compare when some filter is on

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total requests", f"{total:,}")
col2.metric("Closed", f"{closed:,}")
if is_filtered:
    col3.metric("Closed rate", f"{rate:.1f}%", f"{rate - all_rate:+.1f} pts vs all")
else:
    col3.metric("Closed rate", f"{rate:.1f}%")
if len(closed_df) == 0:
    col4.metric("Median time to close", "N/A")
elif is_filtered:
    median = closed_df["hours"].median()
    # delta_color="inverse": a shorter time is good, so show it in green
    col4.metric("Median time to close", f"{median:.1f} h", f"{median - all_median:+.1f} h vs all",
                delta_color="inverse")
else:
    col4.metric("Median time to close", f"{closed_df['hours'].median():.1f} h")


tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["Requests per hour", "Share by borough", "Complaint types",
     "Time to close", "Space-time view", "Raw data"]
)#charts in taps.


with tab1:# Line chart
    hourly = df[df["hour"] < last_hour].groupby(["hour", "borough"]).size().reset_index(name="requests")
    if len(hourly) == 0:
        st.info("No complete hours in this time range. The sample stops at 20:07.")
    else:# Add line for whole city
        city = hourly.groupby("hour")["requests"].sum().reset_index()
        city["borough"] = "New York total"
        hourly = pd.concat([hourly, city])  # stack the city rows under the borough rows
        fig = px.line(hourly, x="hour", y="requests", color="borough", markers=True,
                      color_discrete_map=BOROUGH_COLORS,
                      labels={"hour": "Hour of day", "requests": "Requests", "borough": "Borough"})
        fig.update_layout(hovermode="x unified")  # hover shows every borough at that hour
        st.plotly_chart(fig)


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

        counts = closed_df[column].value_counts()#Count the number of closed requests for each group (borough or complaint type)
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


with tab5:#3D scatter plot
    points = df.dropna(subset=["latitude", "longitude"])
    fig = px.scatter_3d(points, x="longitude", y="latitude", z="hour", color="borough",
                        color_discrete_map=BOROUGH_COLORS, hover_name="complaint_type",
                        height=650, labels={"hour": "Hour of day", "borough": "Borough"})
    fig.update_traces(marker={"size": 2})
    st.plotly_chart(fig)
    st.caption("Drag to rotate. Each dot is one request: the floor is the map, height is the time of day.")


with tab6:#raw data
    columns = ["unique_key", "created_date", "complaint_type", "borough", "status"]
    st.dataframe(df[columns])
    csv = df[columns].to_csv(index=False)
    st.download_button("Download as CSV", csv, "filtered_requests.csv", "text/csv")
