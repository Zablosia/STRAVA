



import streamlit as st
import pandas as pd
import datetime
import requests


st.set_page_config(page_title="Strava Summary") #, layout="wide"
st.title("🏃‍♀️ Strava Activity Summary Dashboard")

# 📁 Load the CSV
file_path = r'C:\Users\zablo\strefa_poza_onedrive\Projects\my_portfolio\strava\STRAVA\sample.csv'



try:
    df = pd.read_csv(file_path) #pd.read_csv('STRAVA\sample.csv')
except FileNotFoundError:
    st.error(f"File not found: {'sample.csv'}")
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

st.write('THE END')

# === Funkcja do odświeżania tokena dostępowego ===
def refresh_access_token(client_id, client_secret, refresh_token):
    response = requests.post(
        url="https://www.strava.com/oauth/token",
        data={
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }
    )
    return response.json()['access_token']

# ---- CONFIG ----
CLIENT_ID = '169100'
CLIENT_SECRET = 'fe0aa78460770e9d5fec67f94365ead6e603d68f'
REFRESH_TOKEN = '60565a46079e4ded709ce74e799e9290751b4c88'
access_token = refresh_access_token(CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN)
ACCESS_TOKEN = access_token

HEADERS = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
BOUNDS = "1.2124,103.6020,1.4807,104.0130"  # Singapore

# ---- API CALL ----
@st.cache_data
def get_starred_segments():
    url = "https://www.strava.com/api/v3/segments/starred"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()  # returns a list of segments
    else:
        st.error(f"Failed to load starred segments: {response.status_code}")
        return []

# ---- UI ----
st.title("⭐ My Starred Strava Segments")

segments = get_starred_segments()

if segments:
    # Create dropdown list: segment name + distance
    options = [f"{s['name']} ({int(s['distance'])} m)" for s in segments]
    selected = st.selectbox("Choose a segment:", options)

    index = options.index(selected)
    segment = segments[index]

    st.subheader("Segment Details")
    st.write(f"**Name:** {segment['name']}")
    st.write(f"**Distance:** {int(segment['distance'])} m")
    st.write(f"**Average Grade:** {segment['average_grade']}%")
    #st.write(f"**Elevation Gain:** {segment['total_elevation_gain']} m")
    st.write(f"**Climb Category:** {segment['climb_category']}")
    st.write(f"**City/State:** {segment.get('city', 'N/A')} / {segment.get('state', 'N/A')}")
    st.write(f"**Segment ID:** {segment['id']}")
else:
    st.warning("No starred segments found. Go to Strava and star a few segments first.")



    # --- API CALL ---
@st.cache_data
def get_segment_efforts(segment_id):
    url = f"https://www.strava.com/api/v3/segment_efforts"
    params = {
        "segment_id": segment_id
    }
    response = requests.get(url, headers=HEADERS, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to fetch efforts: {response.status_code} - {response.text}")
        return []

# --- UI ---
st.title("🔁 My Past Efforts on a Segment")

segment_id_input = st.text_input("Enter Segment ID:", "")

if segment_id_input:
    try:
        segment_id = int(segment_id_input)
        efforts = get_segment_efforts(segment_id)

        if efforts:
            st.success(f"Found {len(efforts)} effort(s).")
            for effort in efforts:
                st.markdown(f"""
                    - 📅 Date: **{effort['start_date_local']}**
                    - ⏱️ Elapsed Time: **{effort['elapsed_time']} sec**
                    - 🚴‍♀️ Activity ID: [{effort['activity']['id']}](https://www.strava.com/activities/{effort['activity']['id']})
                    - 🔗 Segment Effort ID: {effort['id']}
                    ---
                """)
        else:
            st.warning("No past efforts found on this segment.")
    except ValueError:
        st.error("Please enter a valid segment ID (number).")