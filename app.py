



import streamlit as st
import pandas as pd
import datetime


st.set_page_config(page_title="Strava Summary") #, layout="wide"
st.title("🏃‍♀️ Strava Activity Summary Dashboard")

# 📁 Load the CSV
file_path = r'C:\Users\zablo\strefa_poza_onedrive\Projects\my_portfolio\strava\data\sample.csv'

try:
    df = pd.read_csv(file_path)
except FileNotFoundError:
    st.error(f"File not found: {file_path}")
    st.stop()



# Create a fake row with today's date
today = datetime.datetime.today().date()

fake_row = pd.DataFrame([{
    'start_date_local': pd.to_datetime(today),
    'distance': 0,
    'moving_time': 0,
    'total_elevation_gain': 0,
    'max_speed': 0,
    'sport_type': 'FAKE'  # Mark it clearly so we can ignore it later
}])

# Combine it with your real data
df = pd.concat([df, fake_row], ignore_index=True)





# 🗓️ Convert date & extract year
df['start_date_local'] = pd.to_datetime(df['start_date_local'], errors='coerce')
df['year'] = df['start_date_local'].dt.year

# 🧮 Group and summarize
summary = (
    df.groupby(['sport_type', 'year'])
    .agg({
        'distance': 'sum',
        'moving_time': 'sum',
        'total_elevation_gain': 'sum',
        'max_speed': 'max'
    })
    .reset_index()
)

# ✨ Clean column names for display
summary.columns = [
    'Sport Type',
    'Year',
    'Total Distance (m)',
    'Total Moving Time (s)',
    'Total Elevation Gain (m)',
    'Max Speed (m/s)'
]

# 📊 Display summary table
st.subheader("📊 Overview by Sport & Year")
st.dataframe(summary)




st.set_page_config(page_title="Strava Explorer", layout="wide") #
st.title("🚴 Strava Top Activities Explorer")


# Sidebar filters
st.sidebar.header("🔎 Filter your activities")

# Sport selector
sport_types = df['sport_type'].dropna().unique().tolist()
selected_sports = st.sidebar.multiselect("Choose sport type(s)", sport_types, default=sport_types)



# Dataset date boundaries
min_date = df['start_date_local'].min().date()
max_date = df['start_date_local'].max().date()

# Safe default range: latest 30 days or just dataset span if less
delta = datetime.timedelta(days=30)
default_start = max(min_date, max_date - delta)
default_end = max_date

# Sidebar filters
st.sidebar.header("Filters")

# 🟢 Safely controlled date picker
start_date, end_date = st.sidebar.date_input(
    "Select Date Range",
    value=(default_start, default_end),
    min_value=min_date,
    max_value=max_date
)

# Handle both single and tuple case
if isinstance(start_date, datetime.date) and isinstance(end_date, datetime.date):
    # 🟢 Filter data
    filtered_df = df[
        (df['start_date_local'].dt.date >= start_date) &
        (df['start_date_local'].dt.date <= end_date)
    ]
else:
    st.error("Please select a valid date range.")
    st.stop()





# Filter dataframe
filtered_df = df[
    (df['sport_type'].isin(selected_sports)) &
    (df['start_date_local'].dt.date >= start_date) &
    (df['start_date_local'].dt.date <= end_date)
]



## --- Sidebar: Metric selector ---
sort_option = st.sidebar.selectbox(
    "Sort Top 10 By",
    options=["Distance (km)", "Max Speed (km/h)", "Elevation Gain (m)", "Moving Time (min)"],
    index=0
)

# --- Prepare data with conversions ---
filtered_df['distance_km'] = (filtered_df['distance'] / 1000).round(2)
filtered_df['moving_time_min'] = (filtered_df['moving_time'] / 60).round(1)
filtered_df['elevation_gain_m'] = filtered_df['total_elevation_gain'].round(1)
filtered_df['max_speed_kmh'] = (filtered_df['max_speed'] * 3.6).round(1)

# --- Mapping from label to column ---
sort_column_map = {
    "Distance (km)": "distance_km",
    "Max Speed (km/h)": "max_speed_kmh",
    "Elevation Gain (m)": "elevation_gain_m",
    "Moving Time (min)": "moving_time_min"
}

sort_col = sort_column_map[sort_option]

# --- Sort and display ---
top_activities = (
    filtered_df
    .sort_values(by=sort_col, ascending=False)
    .head(10)
)

st.subheader(f"🏆 Top 10 Activities by {sort_option}")
st.dataframe(
    top_activities[[
        'name', 'sport_type', 'start_date_local',
        'distance_km', 'moving_time_min', 'elevation_gain_m', 'max_speed_kmh'
    ]].rename(columns={
        'name': 'Activity Name',
        'sport_type': 'Sport',
        'start_date_local': 'Date',
        'distance_km': 'Distance (km)',
        'moving_time_min': 'Moving Time (min)',
        'elevation_gain_m': 'Elevation Gain (m)',
        'max_speed_kmh': 'Max Speed (km/h)'
    }),
    use_container_width=True
)