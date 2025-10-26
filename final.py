import streamlit as st
from pathlib import Path
import base64
import pandas as pd
from streamlit_folium import st_folium
import folium
import random
import math
from datetime import datetime, timedelta, date
import geopandas as gpd
from shapely.geometry import Point

import streamlit as st

# ------------------ CUSTOM CSS ------------------
st.markdown(
    """
    <style>
    /* Reduce top padding of header so buttons are visible */
    header { 
        height: 5px;
        padding: 0px 0px;
    }

    /* Move main content down slightly */
    .block-container {
        padding-top: 1px;
    }

    /* Optional: adjust button margin if still hidden */
    button {
        margin-top: 2px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ------------------ YOUR APP ------------------
st.title("IVROT")

# Example buttons
st.button("Button 1")


# Rest of your code...

# ---------- Paths (update if needed) ----------
BG_IMAGE = r"C:\Users\P ADITHYA M NAIK\Desktop\IVROT\Navigation_2.jpg"
LOGO_LIGHT_PNG = Path(r"C:\Users\P ADITHYA M NAIK\Desktop\IVROT\IVROT-removebg-preview.png")
LOGO_DARK_PNG = Path(r"C:\Users\P ADITHYA M NAIK\Desktop\IVROT\DARK-removebg-preview.png")
LOGO_LIGHT_JPG = LOGO_LIGHT_PNG.with_suffix(".jpg")
LOGO_DARK_JPG = LOGO_DARK_PNG.with_suffix(".jpg")
ICO_PATH = Path(r"C:\Users\P ADITHYA M NAIK\Desktop\IVROT\IVROT.ico")
CSV_PATH = r"C:\Users\P ADITHYA M NAIK\Desktop\IVROT\voyages.csv"

# ---------- Helpers ----------
def file_to_data_uri(path: Path):
    if not path.exists():
        return ""
    mime = "image/png"
    if path.suffix.lower() in (".jpg", ".jpeg"):
        mime = "image/jpeg"
    if path.suffix.lower() == ".ico":
        mime = "image/x-icon"
    b = path.read_bytes()
    return f"data:{mime};base64,{base64.b64encode(b).decode()}"

bg_uri = file_to_data_uri(Path(BG_IMAGE))
logo_light_path = LOGO_LIGHT_JPG if LOGO_LIGHT_JPG.exists() else LOGO_LIGHT_PNG
logo_dark_path = LOGO_DARK_JPG if LOGO_DARK_JPG.exists() else LOGO_DARK_PNG
logo_light_uri = file_to_data_uri(logo_light_path) if logo_light_path.exists() else ""
logo_dark_uri = file_to_data_uri(logo_dark_path) if logo_dark_path.exists() else ""
ico_uri = file_to_data_uri(ICO_PATH) if ICO_PATH.exists() else ""

# ---------- Page config ----------
page_icon = str(ICO_PATH) if ICO_PATH.exists() else None
st.set_page_config(page_title="IVROT", layout="wide", page_icon=page_icon)

# ---------- Session state defaults ----------
if "theme_flag" not in st.session_state:
    st.session_state["theme_flag"] = 0
if "nav" not in st.session_state:
    st.session_state["nav"] = "HOME"

theme = st.session_state["theme_flag"]

def toggle_theme_flag():
    st.session_state["theme_flag"] = 1 if st.session_state["theme_flag"] == 0 else 0

# ---------- Inject CSS ----------
if st.session_state["theme_flag"] == 0:
    root_vars = """
    :root {
      --ivrot-bg: #ffffff;
      --ivrot-text: #0f1724;
      --ivrot-border: rgba(2,6,23,0.06);
      --ivrot-hover-shadow: 0 8px 18px rgba(2,6,23,0.06);
    }
    """
    set_dark_script = "<script>document.documentElement.classList.remove('dark')</script>"
else:
    root_vars = """
    :root {
      --ivrot-bg: #0f1724;
      --ivrot-text: #f8fafc;
      --ivrot-border: rgba(248,250,252,0.06);
      --ivrot-hover-shadow: 0 8px 18px rgba(248,250,252,0.04);
    }
    """
    set_dark_script = "<script>document.documentElement.classList.add('dark')</script>"

st.markdown(
    f"""
    <style>
    {root_vars}

    /* background */
    [data-testid="stAppViewContainer"] {{
      background: url("{bg_uri}") no-repeat center center fixed;
      background-size: cover;
    }}

    /* Header */
    .ivrot-header {{
      position: fixed;
      top: 60px;
      left: 0;
      right: 0;
      width: 100%;
      height: 25%;
      z-index: 999;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 50px;
      box-sizing: border-box;
      border-radius: 0 0 12px 12px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.12);
      transition: background-color 200ms ease, color 200ms ease;
      background: var(--ivrot-bg) !important;
      color: var(--ivrot-text) !important;
      overflow: visible !important;
    }}

    .ivrot-left {{ display:flex; align-items:center; gap:16px; min-width:40px; }}
    .ivrot-left img {{ height:200px; width:auto; display:block; }}

    .ivrot-center {{ display:flex; flex-direction:column; align-items:left; gap:5px; flex:1 1 auto; }}
    .ivrot-title {{ font-weight:800; font-size:50px; margin:0; color:var(--ivrot-text) !important; }}
    .ivrot-subtitle {{ font-size:30px; margin:0; opacity:0.85; color:var(--ivrot-text) !important; }}

    .ivrot-nav-row {{
      display:flex;
      flex-direction:column;
      gap:16px; /* increased gap between buttons */
      align-items:center;
      margin-top:20px; /* lowered buttons below header */
      transform: translateY(40px); /* move buttons lower */
      transition: transform 160ms ease;
      pointer-events: auto;
    }}

    .ivrot-nav-row button,
    .stButton > button,
    div.stButton > button {{
      background: var(--ivrot-bg) !important;
      color: var(--ivrot-text) !important;
      border: 1px solid var(--ivrot-border) !important;
      padding: 14px 24px !important; /* bigger buttons */
      border-radius: 12px !important;
      font-weight:700 !important;
      cursor:pointer !important;
      font-size:18px !important; /* larger text */
      transition: transform 120ms ease, box-shadow 120ms ease, background-color 120ms ease, color 120ms ease, border-color 120ms ease !important;
    }}

    .ivrot-nav-row button:hover,
    .stButton > button:hover,
    div.stButton > button:hover {{
      transform: translateY(-2px) !important;
      box-shadow: var(--ivrot-hover-shadow) !important;
    }}

    .ivrot-nav-row button[data-active="true"],
    .stButton > button[data-active="true"],
    div.stButton > button[data-active="true"] {{
      box-shadow: none !important;
      border-width: 2px !important;
    }}

    .ivrot-right button {{
      background: transparent !important;
      border: none !important;
      font-size:20px !important;
      cursor:pointer !important;
      padding:8px !important;
      border-radius:8px !important;
      color: var(--ivrot-text) !important;
      font-weight:700 !important;
    }}
    .ivrot-right button:hover {{ background: rgba(0,0,0,0.06) !important; }}

    @media (max-width: 800px) {{
      .ivrot-left img {{ height:64px; }}
      .ivrot-title {{ font-size:16px; }}
      .ivrot-nav-row {{ margin-top:10px; transform: translateY(24px); }}
      .ivrot-nav-row button {{ padding:10px 16px; font-size:16px; }}
      .ivrot-header {{ padding:10px 14px; }}
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


st.markdown(set_dark_script, unsafe_allow_html=True)

# ---------- Header HTML ----------
logo_uri = logo_light_uri if st.session_state["theme_flag"] == 0 else logo_dark_uri
logo_html = f'<img src="{logo_uri}" alt="IVROT logo">' if logo_uri else "<div style='font-weight:800'>IVROT</div>"

st.markdown(
    f"""
    <div class="ivrot-header" role="banner" aria-label="IVROT header">
      <div class="ivrot-left">{logo_html}</div>
      <div class="ivrot-center">
        <div>
          <div class="ivrot-title">IVROT</div>
          <div class="ivrot-subtitle">Integrated Vessel Route Optimisation Toolkit</div>
        </div>
        <div class="ivrot-nav-row" id="nav-buttons-placeholder" style="display:flex; gap:10px;"></div>
      </div>
      <div class="ivrot-right" id="theme-toggle-placeholder"></div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------- Header Buttons ----------
c1, c2, c3 = st.columns([1,4,1])
with c2:
    col_nav1, col_nav2, col_nav3 = st.columns([1,1,1])
    with col_nav1:
        if st.button("HOME", key="nav_home"):
            st.session_state["nav"] = "HOME"
    with col_nav2:
        if st.button("NEW TRAJECTORY", key="nav_new"):
            st.session_state["nav"] = "NEW TRAJECTORY"
    with col_nav3:
        if st.button("HISTORY", key="nav_hist"):
            st.session_state["nav"] = "HISTORY"

with c3:
    icon = "☼" if st.session_state["theme_flag"] == 0 else "☽"
    if st.button(icon, key="theme_toggle_btn"):
        toggle_theme_flag()
        if st.session_state["theme_flag"] == 1:
            st.markdown("<script>document.documentElement.classList.add('dark')</script>", unsafe_allow_html=True)
        else:
            st.markdown("<script>document.documentElement.classList.remove('dark')</script>", unsafe_allow_html=True)

# ---------- Active button highlight ----------
active = st.session_state["nav"]
st.markdown(
    f"""
    <script>
      const btns = document.querySelectorAll('.ivrot-nav-row button, .stButton > button, div.stButton > button');
      btns.forEach(b => b.removeAttribute('data-active'));
      btns.forEach(b => {{
        const txt = (b.innerText || b.textContent || '').trim().toUpperCase();
        if (txt === "{active}") {{
          b.setAttribute('data-active', 'true');
        }}
      }});
    </script>
    """,
    unsafe_allow_html=True,
)

# ---------- PAGE CONTENT ----------
st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

# ---------- HOME PAGE ----------
if st.session_state["nav"] == "HOME":
    st.header("Welcome to IVROT")

# ---------- NEW TRAJECTORY PAGE ----------
elif st.session_state["nav"] == "NEW TRAJECTORY":
    st.header("New Trajectory")

    # --- Trajectory session state ---
    if "start" not in st.session_state:
        st.session_state.start = [None, None]
    if "end" not in st.session_state:
        st.session_state.end = [None, None]
    if "route" not in st.session_state:
        st.session_state.route = None
    if "clusters" not in st.session_state:
        st.session_state.clusters = []

    if "land" not in st.session_state:
        st.session_state.land = gpd.read_file(r"C:\Users\P ADITHYA M NAIK\Desktop\IVROT\ne_10m_land.shp")

    def is_water(lat, lon):
        point = Point(lon, lat)
        return not st.session_state.land.contains(point).any()

    # --- Sidebar for NEW TRAJECTORY ---
    with st.sidebar.expander("Route Points & Ship"):
        start_lat = st.number_input("Start Latitude", value=st.session_state.start[0] or 0.0)
        start_lon = st.number_input("Start Longitude", value=st.session_state.start[1] or 0.0)
        end_lat = st.number_input("End Latitude", value=st.session_state.end[0] or 0.0)
        end_lon = st.number_input("End Longitude", value=st.session_state.end[1] or 0.0)

        wave = st.slider("WAVE", 0, 100, 50)
        wind = st.slider("WIND", 0, 100, 50)
        current = st.slider("CURRENT", 0, 100, 50)

        ship_type = st.selectbox("Select Ship Type", ["Cargo Vessel","Oil Tanker","Container Ship","Fishing Vessel","Passenger Ship"])
        ship_speed_knots = st.slider("Ship Speed (knots)", 5, 30, 15)
        start_date = st.date_input("Select ETD Date", value=date.today())

        reset = st.button("Reset Trajectory")
        generate = st.button("Generate Route")

    if reset:
        st.session_state.start = [None, None]
        st.session_state.end = [None, None]
        st.session_state.route = None
        st.session_state.clusters = []

    # --- Map for selecting points ---
    map_container = st.container()
    with map_container:
        m = folium.Map(location=[20.5937,78.9629], zoom_start=5, tiles="CartoDB positron")
        if st.session_state.start != [None, None]:
            folium.Marker(st.session_state.start, popup="Start", icon=folium.Icon(color="green")).add_to(m)
        if st.session_state.end != [None, None]:
            folium.Marker(st.session_state.end, popup="End", icon=folium.Icon(color="red")).add_to(m)
        map_click = st_folium(m, width="100%", height=600, key="click_map")

    if map_click and map_click["last_clicked"]:
        lat = map_click["last_clicked"]["lat"]
        lon = map_click["last_clicked"]["lng"]
        if st.session_state.start == [None, None] and is_water(lat, lon):
            st.session_state.start = [lat, lon]
        elif st.session_state.end == [None, None] and is_water(lat, lon):
            st.session_state.end = [lat, lon]

    # --- Generate route ---
    if generate and st.session_state.start != [None,None] and st.session_state.end != [None,None]:
        num_waypoints = 5
        lats = [st.session_state.start[0]]
        lons = [st.session_state.start[1]]
        for i in range(1,num_waypoints):
            frac = i/num_waypoints
            lat = st.session_state.start[0] + (st.session_state.end[0]-st.session_state.start[0])*frac
            lon = st.session_state.start[1] + (st.session_state.end[1]-st.session_state.start[1])*frac
            attempt=0
            while True:
                lat_offset = random.uniform(-2,2)
                lon_offset = random.uniform(-2,2)
                new_lat = lat+lat_offset
                new_lon = lon+lon_offset
                if is_water(new_lat,new_lon) or attempt>10:
                    break
                attempt+=1
            lats.append(new_lat)
            lons.append(new_lon)
        lats.append(st.session_state.end[0])
        lons.append(st.session_state.end[1])
        st.session_state.route = list(zip(lats,lons))

        # Generate clusters
        clusters=[]
        for i in range(len(st.session_state.route)-1):
            lat1,lon1 = st.session_state.route[i]
            lat2,lon2 = st.session_state.route[i+1]
            for step in range(15):
                lat = lat1 + (lat2-lat1)*step/20
                lon = lon1 + (lon2-lon1)*step/20
                for _ in range(8):
                    attempt=0
                    while True:
                        offset_lat=random.gauss(0,0.2)
                        offset_lon=random.gauss(0,0.2)
                        new_lat = lat+offset_lat
                        new_lon = lon+offset_lon
                        if is_water(new_lat,new_lon) or attempt>10:
                            break
                        attempt+=1
                    clusters.append({
                        "lat":new_lat,"lon":new_lon,
                        "wave":random.randint(5,40),
                        "wind":random.randint(5,40),
                        "current":random.randint(5,40)
                    })
                for _ in range(10):
                    attempt=0
                    while True:
                        offset_lat=random.gauss(0,0.8)
                        offset_lon=random.gauss(0,0.8)
                        new_lat = lat+offset_lat
                        new_lon = lon+offset_lon
                        if is_water(new_lat,new_lon) or attempt>10:
                            break
                        attempt+=1
                    clusters.append({
                        "lat":new_lat,"lon":new_lon,
                        "wave":random.randint(50,100),
                        "wind":random.randint(50,100),
                        "current":random.randint(50,100)
                    })
        st.session_state.clusters = clusters

    # --- Final Map with route & clusters ---
    map_container2 = st.container()
    with map_container2:
        m2 = folium.Map(location=[20.5937,78.9629], zoom_start=5, tiles="CartoDB positron")
        if st.session_state.start != [None,None]:
            folium.Marker(st.session_state.start, popup="Start", icon=folium.Icon(color="green")).add_to(m2)
        if st.session_state.end != [None,None]:
            folium.Marker(st.session_state.end, popup="End", icon=folium.Icon(color="red")).add_to(m2)
        if st.session_state.route:
            folium.PolyLine(st.session_state.route, color="blue", weight=3).add_to(m2)
        if st.session_state.clusters:
            for point in st.session_state.clusters:
                total = point["wave"]+point["wind"]+point["current"]
                tooltip_text=f"Wave: {point['wave']} | Wind: {point['wind']} | Current: {point['current']} (Total: {total}/300)"
                folium.CircleMarker(location=[point["lat"],point["lon"]],
                                    radius=2,color="green",fill=True,fill_opacity=0.6,
                                    tooltip=tooltip_text).add_to(m2)
        st_folium(m2, width="100%", height=600, key="final_map")

    # --- Distance & ETA calculation ---
    if st.session_state.route:
        def haversine(lat1, lon1, lat2, lon2):
            R=6371.0
            phi1,phi2=math.radians(lat1),math.radians(lat2)
            dphi=math.radians(lat2-lat1)
            dlambda=math.radians(lon2-lon1)
            a=math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
            c=2*math.atan2(math.sqrt(a),math.sqrt(1-a))
            return R*c
        total_distance_km=0
        for i in range(len(st.session_state.route)-1):
            lat1,lon1=st.session_state.route[i]
            lat2,lon2=st.session_state.route[i+1]
            total_distance_km+=haversine(lat1,lon1,lat2,lon2)
        total_distance_nm=total_distance_km/1.852
        hours_needed=total_distance_nm/ship_speed_knots
        etd=datetime.combine(start_date,datetime.min.time())
        eta=etd+timedelta(hours=hours_needed)
        st.sidebar.markdown("### Voyage Info")
        st.sidebar.write(f"**Ship Type:** {ship_type}")
        st.sidebar.write(f"**Distance:** {total_distance_nm:.1f} NM ({total_distance_km:.1f} km)")
        st.sidebar.write(f"**ETD:** {etd.strftime('%Y-%m-%d %H:%M')}")
        st.sidebar.write(f"**ETA:** {eta.strftime('%Y-%m-%d %H:%M')}")
        st.sidebar.write(f"**Duration:** {hours_needed:.1f} hrs")

# ---------- HISTORY PAGE ----------
elif st.session_state["nav"] == "HISTORY":
    st.header("Voyage History")
    try:
        df = pd.read_csv(CSV_PATH)
        st.dataframe(df,use_container_width=True)
    except Exception as e:
        st.error(f"Error loading CSV: {e}")
