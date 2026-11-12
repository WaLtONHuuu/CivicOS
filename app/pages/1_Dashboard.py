import numpy as np
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

# Load the raw data
df = pd.read_csv("data/sample/nyc311_2026-10_first10000.csv")
df["created_date"] = pd.to_datetime(df["created_date"])
df["closed_date"] = pd.to_datetime(df["closed_date"])
df["hour"] = df["created_date"].dt.hour  # 0-23, used by most charts below
df["hours_to_close"] = (df["closed_date"] - df["created_date"]).dt.total_seconds() / 3600

last_hour = df["hour"].max() # The sample stops in the middle of its last hour. HOurly charts only use complete hours.
full_hours = list(range(last_hour))

# Filter 
top_types = df["complaint_type"].value_counts().head(15)  # the 15 most common types
choice = st.selectbox("Complaint type", ["All"] + list(top_types.index))
if choice != "All":
    df = df[df["complaint_type"] == choice]

# Headline numbers
closed = df[df["hours_to_close"] >= 0]  # skip open requests and bad timestamps
col1, col2, col3 = st.columns(3)
col1.metric("Requests", f"{len(df):,}")
col2.metric("Closed", f"{len(closed) / len(df):.0%}")
col3.metric("Median time to close", f"{closed['hours_to_close'].median():.1f} h")

# Line chart
st.subheader("Requests per hour")
hourly = df[df["hour"] < last_hour].groupby(["hour", "borough"]).size().reset_index(name="requests")
# Add line for whole city
city = hourly.groupby("hour")["requests"].sum().reset_index()
city["borough"] = "New York total"
hourly = pd.concat([hourly, city])  # stack the city rows under the borough rows
fig = px.line(hourly, x="hour", y="requests", color="borough", markers=True,
              color_discrete_map=BOROUGH_COLORS,
              labels={"hour": "Hour of day", "requests": "Requests", "borough": "Borough"})
fig.update_layout(hovermode="x unified")  # hover shows every borough at that hour
st.plotly_chart(fig)

# Pie chart
st.subheader("Share by borough")
by_borough = df["borough"].value_counts().reset_index()  # columns: borough, count
fig = px.pie(by_borough, names="borough", values="count", color="borough",
             color_discrete_map=BOROUGH_COLORS, hole=0.4)
fig.update_traces(textinfo="percent+label")
fig.update_layout(showlegend=False)
st.plotly_chart(fig)

# Scatter and curve fit
st.subheader("Running total with a fitted curve")
per_hour = df["hour"].value_counts().reindex(full_hours, fill_value=0)  # requests in each full hour
x = np.array(full_hours) + 1
y = per_hour.cumsum().values

# Fit a polynomial
degree = st.slider("Polynomial degree", 1, 3, 3)
coeffs = np.polyfit(x, y, degree)   # finds the best coefficients, highest power first
predicted = np.polyval(coeffs, x)   # the curve's value at each data point
r2 = 1 - ((y - predicted) ** 2).sum() / ((y - y.mean()) ** 2).sum()  # 1.0 = perfect fit

# fitted formula
terms = []
for i in range(degree + 1):
    power = degree - i
    if power == 0:
        terms.append(f"{coeffs[i]:.3f}")
    elif power == 1:
        terms.append(f"{coeffs[i]:.3f}x")
    else:
        terms.append(f"{coeffs[i]:.3f}x^{power}")
formula = "y = " + " + ".join(terms)
formula = formula.replace("+ -", "- ")  

fig = px.scatter(x=x, y=y, labels={"x": "Hour of day", "y": "Requests so far"})
curve_x = np.linspace(1, 24, 100)  # 100 points make curve smooth
fig.add_scatter(x=curve_x, y=np.polyval(coeffs, curve_x), mode="lines",
                line={"dash": "dash", "color": "#eb6834"}, name="Fitted curve")
st.plotly_chart(fig)
st.latex(formula)  # x = hour of day, y = requests so far
st.write(f"R² = **{r2:.4f}**. Forecast total by midnight: **{np.polyval(coeffs, 24):,.0f}**.")
st.caption("A higher degree follows the past points more closely, but its forecast beyond the data is less reliable.")

# 3D chart x = longitude y = latitude z = hour
st.subheader("Space-time view")
points = df.dropna(subset=["latitude", "longitude"])
fig = px.scatter_3d(points, x="longitude", y="latitude", z="hour", color="borough",
                    color_discrete_map=BOROUGH_COLORS, hover_name="complaint_type",
                    height=650, labels={"hour": "Hour of day", "borough": "Borough"})
fig.update_traces(marker={"size": 2})
st.plotly_chart(fig)
st.caption("Drag to rotate. Each dot is one request: the floor is the map, height is the time of day.")
