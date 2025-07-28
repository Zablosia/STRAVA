import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta

# -------------------- CONFIG --------------------
# Read from secrets
CLIENT_ID = st.secrets["STRAVA"]["client_id"]
CLIENT_SECRET = st.secrets["STRAVA"]["client_secret"]
REFRESH_TOKEN = st.secrets["STRAVA"]["refresh_token"]
##

TOKEN_URL = "https://www.strava.com/oauth/token"
ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"

# -------------------- HELPER FUNCTIONS --------------------

def get_strava_activities():
    # Refresh access token
    response = requests.post(TOKEN_URL, data={
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'refresh_token': REFRESH_TOKEN,
        'grant_type': 'refresh_token'
    })
    access_token = response.json()['access_token']

    # Paginate through activities
    all_data = []
    page = 1
    while True:
        headers = {'Authorization': f'Bearer {access_token}'}
        params = {'per_page': 200, 'page': page}
        res = requests.get(ACTIVITIES_URL, headers=headers, params=params)
        data = res.json()
        if not data:
            break
        all_data.extend(data)
        page += 1

    df = pd.json_normalize(all_data)
    df['start_date_local'] = pd.to_datetime(df['start_date_local'])
    df['year'] = df['start_date_local'].dt.year
    df['week'] = df['start_date_local'].dt.isocalendar().week
    df['date'] = df['start_date_local'].dt.date
    df = df.rename(columns={
        'average_speed': 'avg_speed',
        'max_speed': 'max_speed',
        'average_heartrate': 'avg_hr',
        'max_heartrate': 'max_hr',
        'distance': 'distance_m',
        'total_elevation_gain': 'elev_gain',
        'moving_time': 'moving_time_sec',
        'type': 'activity_type'
    })
    df['distance_km'] = df['distance_m'] / 1000
    df['avg_speed_kmh'] = df['avg_speed'] * 3.6
    df['max_speed_kmh'] = df['max_speed'] * 3.6
    df['moving_time_min'] = df['moving_time_sec'] / 60
    return df



def make_summary_table_advanced(df_filtered, selected_row, metrics):
    summary = []
    for label, col in metrics.items():
        if col not in df_filtered or pd.isna(selected_row[col]):
            continue

        col_values = df_filtered[col].dropna()
        total = len(col_values)
        if total == 0:
            continue

        value = selected_row[col]
        rank = (col_values > value).sum() + 1
        percentile = (col_values < value).mean() * 100

        summary.append({
            'Metric': label,
            'Value': f"{value:.2f}",
            'Rank': f"{rank} / {total}",
            'Percentile': f"{percentile:.1f}%"
        })

    return pd.DataFrame(summary)


def plot_radar_chart(df_filtered, selected_row, metrics):
    categories = []
    values = []
    for label, col in metrics.items():
        if col not in df_filtered or pd.isna(selected_row[col]):
            continue
        col_values = df_filtered[col].dropna()
        if len(col_values) == 0:
            continue
        value = selected_row[col]
        percentile = (col_values < value).mean() * 100
        categories.append(label)
        values.append(percentile)

    fig = go.Figure(
        data=[go.Scatterpolar(r=values, theta=categories, fill='toself')],
        layout=go.Layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False)
    )
    return fig


def compare_date_ranges(df, start_date, end_date):
    df['date'] = pd.to_datetime(df['date'])
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    current_range = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
    delta = end_date - start_date
    prior_start = start_date - delta - timedelta(days=1)
    prior_end = start_date - timedelta(days=1)
    prior_range = df[(df['date'] >= prior_start) & (df['date'] <= prior_end)]

    summary = lambda d: pd.Series({
        'Distance (km)': d['distance_km'].sum(),
        'Moving Time (min)': d['moving_time_min'].sum(),
        'Elevation Gain (m)': d['elev_gain'].sum()
    })

    current_summary = summary(current_range)
    prior_summary = summary(prior_range)

    compare_df = pd.DataFrame({'Current': current_summary, 'Previous': prior_summary})
    compare_df['% Change'] = ((compare_df['Current'] - compare_df['Previous']) / compare_df['Previous'].replace(0, np.nan)) * 100

    metrics = compare_df.index.tolist()

    figs = []
    for metric in metrics:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=['Previous', 'Current'],
            y=[compare_df.loc[metric, 'Previous'], compare_df.loc[metric, 'Current']],
            text=[f"{compare_df.loc[metric, 'Previous']:.1f}", f"{compare_df.loc[metric, 'Current']:.1f}"],
            textposition='auto',
            marker_color=['lightgray', 'steelblue']
        ))
        fig.update_layout(
            title=f"{metric} (% Change: {compare_df.loc[metric, '% Change']:.1f}%)",
            yaxis_title=metric,
            xaxis_title="Period",
            height=400,
            width=350
        )
        figs.append(fig)

    return figs

# -------------------- STREAMLIT UI --------------------
st.set_page_config(page_title="Strava Dashboard", layout="wide")
st.title("📊 Strava Activity Dashboard")

with st.spinner("Fetching data from Strava..."):
    df = get_strava_activities()

# Filters
col1, col2 = st.columns(2)
activity_types = df['activity_type'].dropna().unique()
with col1:
    selected_type = st.selectbox("Choose Activity Type", options=sorted(activity_types))
with col2:
    years = df[df['activity_type'] == selected_type]['year'].dropna().unique()
    selected_year = st.selectbox("Choose Year", options=sorted(years, reverse=True))

# Filter dataset
df_filtered = df[(df['activity_type'] == selected_type) & (df['year'] == selected_year)].copy()
if df_filtered.empty:
    st.warning("No activities found for this type and year.")
    st.stop()

# Date Range Comparison
st.subheader("📆 Weekly Comparison")
start_date, end_date = st.date_input("Select Date Range for Comparison", value=(df_filtered['start_date_local'].min(), df_filtered['start_date_local'].max()))
if start_date < end_date:
    figs = compare_date_ranges(df_filtered, start_date, end_date)
    col1, col2, col3 = st.columns(3)
    cols = [col1, col2, col3]
    for i, fig in enumerate(figs):
        cols[i % 3].plotly_chart(fig, use_container_width=True)
else:
    st.info("Please select a valid date range.")

# Select activity
st.subheader("🏁 Individual Activity Analysis")
activity_names = df_filtered['name'].tolist()
selected_name = st.selectbox("Select Activity to Analyze", options=activity_names)
selected_row = df_filtered[df_filtered['name'] == selected_name].iloc[0]

# Metrics mapping
metrics = {
    'Avg Speed (km/h)': 'avg_speed_kmh',
    'Max Speed (km/h)': 'max_speed_kmh',
    'Distance (km)': 'distance_km',
    'Moving Time (min)': 'moving_time_min',
    'Elevation Gain (m)': 'elev_gain',
    'Avg HR (bpm)': 'avg_hr',
    'Max HR (bpm)': 'max_hr'
}

# Radar Chart
st.subheader("📈 Percentile Radar Chart")
fig = plot_radar_chart(df_filtered, selected_row, metrics)
st.plotly_chart(fig, use_container_width=True)

# Summary Table
st.subheader("📋 Performance Table")
summary_df = make_summary_table_advanced(df_filtered, selected_row, metrics)
st.dataframe(summary_df.set_index("Metric"), use_container_width=True)

# Top 10 Activities by Selected Metric
st.subheader("🏅 Top 10 Activities Table")
sort_param_label = st.selectbox("Choose Parameter to Rank Activities", options=list(metrics.keys()))
sort_param_col = metrics[sort_param_label]
df_top10 = df_filtered[['name', 'start_date_local', 'distance_km', 'moving_time_min', 'elev_gain', 'avg_speed_kmh', 'max_speed_kmh', 'avg_hr', 'max_hr']].copy()
df_top10 = df_top10.sort_values(by=sort_param_col, ascending=False).head(10)
st.dataframe(df_top10.reset_index(drop=True), use_container_width=True)

# Yearly Summary Table (moved to bottom and reordered)
st.subheader("📌 Yearly Summary by Activity Type")
df_summary = df.groupby(['activity_type', 'year']).agg({
    'max_speed_kmh': 'max',
    'avg_speed_kmh': 'mean',
    'moving_time_min': 'sum',
    'distance_km': 'sum',
    'elev_gain': 'sum',
    'max_hr': 'max',
    'avg_hr': 'mean'
}).reset_index()
st.dataframe(df_summary, use_container_width=True)
