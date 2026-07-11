"""
UAC Program — System Capacity & Care Load Analytics Dashboard
================================================================
A Streamlit dashboard for monitoring the CBP -> HHS care pipeline for
unaccompanied children: system load, capacity strain, and flow balance.

Data expected: uac_features.csv (produced by the Phase 1-4 notebooks),
placed in the same folder as this file.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# -----------------------------------------------------------------------
# PAGE CONFIG — must be the first Streamlit command in the script
# -----------------------------------------------------------------------
st.set_page_config(
    page_title="UAC Care Load Analytics",
    page_icon="📊",
    layout="wide",
)

# -----------------------------------------------------------------------
# DATA LOADING
# @st.cache_data means Streamlit only re-reads the CSV when the file
# changes, instead of on every single user interaction -- keeps the app fast.
# -----------------------------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv("uac_features.csv", parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


df = load_data()

# -----------------------------------------------------------------------
# SIDEBAR — User Capabilities: date range, metric toggles, granularity
# -----------------------------------------------------------------------
st.sidebar.title("Controls")

min_date, max_date = df["date"].min().date(), df["date"].max().date()

date_range = st.sidebar.date_input(
    "Date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)
# date_input returns a single date while the user is mid-selection --
# guard against that so the app doesn't crash before both dates are picked
if len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

granularity = st.sidebar.radio(
    "Time granularity",
    options=["Daily", "Weekly", "Monthly"],
    index=0,
)

st.sidebar.markdown("---")
st.sidebar.subheader("Metric toggles")
show_7d = st.sidebar.checkbox("Show 7-day rolling average", value=True)
show_14d = st.sidebar.checkbox("Show 14-day rolling average", value=True)
show_strain_threshold = st.sidebar.checkbox("Show strain threshold (75th pct)", value=True)

st.sidebar.markdown("---")
st.sidebar.caption(
    "Data source: HHS Unaccompanied Alien Children Program. "
    "Reporting is irregular (not every calendar day) -- see the "
    "methodology notes in the research paper for how gaps are handled."
)

# -----------------------------------------------------------------------
# FILTER by selected date range
# -----------------------------------------------------------------------
mask = (df["date"].dt.date >= start_date) & (df["date"].dt.date <= end_date)
filtered = df.loc[mask].copy()

if filtered.empty:
    st.warning("No data in the selected date range. Please widen your selection.")
    st.stop()


# -----------------------------------------------------------------------
# RESAMPLE by chosen granularity (applies to the trend charts)
# -----------------------------------------------------------------------
def resample_for_granularity(data: pd.DataFrame, granularity: str) -> pd.DataFrame:
    freq_map = {"Daily": "D", "Weekly": "W", "Monthly": "M"}
    freq = freq_map[granularity]
    if freq == "D":
        return data  # already daily, nothing to do

    numeric_cols = [
        "cbp_in_custody", "hhs_in_care", "total_system_load",
        "net_daily_intake", "load_7d_avg", "load_14d_avg", "volatility_7d",
        "backlog_streak_days", "discharge_offset_ratio",
    ]
    resampled = (
        data.set_index("date")[numeric_cols]
        .resample(freq)
        .mean()
        .reset_index()
    )
    return resampled


chart_data = resample_for_granularity(filtered, granularity)

# -----------------------------------------------------------------------
# TITLE
# -----------------------------------------------------------------------
st.title("📊 UAC Program — System Capacity & Care Load Analytics")
st.caption(
    f"Showing {granularity.lower()} data from **{start_date}** to **{end_date}** "
    f"({len(filtered)} reporting days in range)"
)

# -----------------------------------------------------------------------
# MODULE 1 — KPI SUMMARY CARDS
# Recomputed live on the FILTERED range so the cards react to the date
# picker, rather than always showing the all-time snapshot.
# -----------------------------------------------------------------------
st.subheader("KPI Summary")

latest = filtered.iloc[-1]
earliest_in_window = filtered.iloc[0]

total_now = latest["total_system_load"]
total_change_pct = (
    (total_now - earliest_in_window["total_system_load"])
    / earliest_in_window["total_system_load"] * 100
    if earliest_in_window["total_system_load"] else 0
)

avg_net_intake = filtered["net_daily_intake"].dropna().mean()
avg_volatility = filtered["volatility_7d"].dropna().mean()
pct_days_backlog = filtered["backlog_indicator"].mean() * 100
avg_discharge_ratio = filtered["discharge_offset_ratio"].dropna().mean()

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Children Under Care", f"{int(total_now):,}", f"{total_change_pct:+.1f}% in range")
col2.metric(
    "Net Intake Pressure",
    f"{avg_net_intake:+.1f}/day" if pd.notna(avg_net_intake) else "N/A",
    "Building" if avg_net_intake and avg_net_intake > 0 else "Relieving",
)
col3.metric("Care Load Volatility", f"{avg_volatility:.2f}" if pd.notna(avg_volatility) else "N/A")
col4.metric("Backlog Accumulation Rate", f"{pct_days_backlog:.1f}% of days")
col5.metric(
    "Discharge Offset Ratio",
    f"{avg_discharge_ratio:.2f}" if pd.notna(avg_discharge_ratio) else "N/A",
    "Relieving" if avg_discharge_ratio and avg_discharge_ratio > 1 else "Falling behind",
)

st.markdown("---")

# -----------------------------------------------------------------------
# MODULE 2 — SYSTEM LOAD OVERVIEW PANE
# -----------------------------------------------------------------------
st.subheader("System Load Overview")

fig_overview = go.Figure()
fig_overview.add_trace(go.Scatter(
    x=chart_data["date"], y=chart_data["total_system_load"],
    name="Total System Load", line=dict(color="#4C78A8", width=2),
))
if show_7d:
    fig_overview.add_trace(go.Scatter(
        x=chart_data["date"], y=chart_data["load_7d_avg"],
        name="7-day avg", line=dict(color="#F58518", width=1.5, dash="dot"),
    ))
if show_14d:
    fig_overview.add_trace(go.Scatter(
        x=chart_data["date"], y=chart_data["load_14d_avg"],
        name="14-day avg", line=dict(color="#54A24B", width=1.5, dash="dot"),
    ))
if show_strain_threshold:
    threshold = df["total_system_load"].quantile(0.75)  # computed on FULL history, a stable reference line
    fig_overview.add_hline(
        y=threshold, line_dash="dash", line_color="gray",
        annotation_text="75th pct strain threshold (all-time)",
    )

fig_overview.update_layout(
    height=420, xaxis_title="Date", yaxis_title="Children under care/custody",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=10, r=10, t=30, b=10),
)
st.plotly_chart(fig_overview, use_container_width=True)

# -----------------------------------------------------------------------
# MODULE 3 — CBP vs HHS LOAD COMPARISON
# -----------------------------------------------------------------------
st.subheader("CBP vs HHS Load Comparison")

fig_compare = go.Figure()
fig_compare.add_trace(go.Scatter(
    x=chart_data["date"], y=chart_data["cbp_in_custody"],
    name="CBP Custody", stackgroup="one", line=dict(color="#E45756"),
))
fig_compare.add_trace(go.Scatter(
    x=chart_data["date"], y=chart_data["hhs_in_care"],
    name="HHS Care", stackgroup="one", line=dict(color="#4C78A8"),
))
fig_compare.update_layout(
    height=380, xaxis_title="Date", yaxis_title="Children",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=10, r=10, t=30, b=10),
)
st.plotly_chart(fig_compare, use_container_width=True)
st.caption(
    "Stacked areas show each agency's share of the total system load -- "
    "the combined height at any point equals Total System Load above."
)

# -----------------------------------------------------------------------
# MODULE 4 — NET INTAKE & BACKLOG TRENDS
# -----------------------------------------------------------------------
st.subheader("Net Intake & Backlog Trends")

fig_intake = go.Figure()
bar_colors = ["#E45756" if v and v > 0 else "#54A24B" for v in chart_data["net_daily_intake"]]
fig_intake.add_trace(go.Bar(
    x=chart_data["date"], y=chart_data["net_daily_intake"],
    name="Net Daily Intake", marker_color=bar_colors,
))
fig_intake.add_trace(go.Scatter(
    x=chart_data["date"], y=chart_data["backlog_streak_days"],
    name="Backlog Streak (days)", yaxis="y2",
    line=dict(color="#B279A2", width=2),
))
fig_intake.update_layout(
    height=380, xaxis_title="Date",
    yaxis=dict(title="Net Daily Intake (transfers - discharges)"),
    yaxis2=dict(title="Backlog streak (days)", overlaying="y", side="right"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=10, r=10, t=30, b=10),
)
st.plotly_chart(fig_intake, use_container_width=True)
st.caption(
    "Red bars = more children arriving than discharging that period (load building). "
    "Green bars = discharges keeping pace or ahead (load relieving)."
)

# -----------------------------------------------------------------------
# RAW DATA (optional, expandable — useful for grading/verification)
# -----------------------------------------------------------------------
with st.expander("View underlying data table"):
    st.dataframe(filtered, use_container_width=True)
