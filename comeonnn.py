# app.py
# IVROT full app with splash + blocking-but-rendered loading overlay (no threads / no experimental_rerun)
# Put your videos in same dir:
#  - Splash: YouCut_20251028_153909796.mp4
#  - Loading: IVROT_20251028_150435_0000-vmake.mp4

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
import numpy as np
import matplotlib.pyplot as plt
from io import StringIO
import os
import csv
import time
import traceback
# ------------------------- Splash handling (synchronous) -------------------------
splash_b64 = get_base64(SPLASH_VIDEO_FILE)
loading_b64 = get_base64(LOADING_VIDEO_FILE)

SPLASH_DURATION = 11 # adjust to actual video length (seconds)

if not st.session_state.splash_played:
    # show splash overlay synchronously (the browser will render and play while we wait)
    placeholder_splash = st.empty()
    if splash_b64:
 placeholder_splash.markdown(overlay_video_html(splash_b64, loop=False,overlay_id="splash"), unsafe_allow_html=True)
        # Allow small pause so the browser can start playing the video before we block for duration
        time.sleep(0.1)
        # Wait for the duration (the user will see the video)
        time.sleep(SPLASH_DURATION)
    st.session_state.splash_played = True
    # remove the overlay
    try:
        placeholder_splash.empty()
    except Exception:
        pass
    # continue (no rerun needed)

       
# ------------------------- Configuration & helpers -------------------------
st.set_page_config(page_title="IVROT", layout="wide", page_icon="🎥")

# Filenames for videos (edit if different)
SPLASH_VIDEO_FILE = "YouCut_20251028_153909796.mp4"
LOADING_VIDEO_FILE = "IVROT_20251028_150435_0000-vmake.mp4"

# Images / icons used by UI (if present)
BG_IMAGE = r"Navigation_2.jpg"
LOGO_LIGHT_PNG = Path(r"IVROT-removebg-preview.png")
LOGO_DARK_PNG = Path(r"DARK-removebg-preview.png")
LOGO_LIGHT_JPG = LOGO_LIGHT_PNG.with_suffix(".jpg")
LOGO_DARK_JPG = LOGO_DARK_PNG.with_suffix(".jpg")
ICO_PATH = Path(r"IVROT.ico")

CSV_PATH = r"voyages.csv"
SHIP_CSV = r"ship_data.csv"

# ---------- Utility to convert binary file to base64 for inline data: URIs ----------
def read_file_base64_safe(path):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return ""

# Cache the base64 conversions to avoid repeated reads on reruns
@st.cache_data(show_spinner=False)
def get_base64(path):
    return read_file_base64_safe(path)

# Helper to create overlay HTML for a base64-encoded mp4
def overlay_video_html(base64_mp4, loop=False, overlay_id="overlay"):
    if not base64_mp4:
        return ""
    loop_attr = "loop" if loop else ""
    html = f"""
    <div id="{overlay_id}" style="
        position: fixed;
        top: 0; left: 0;
        width: 100%; height: 100%;
        background: white;
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 999999;
    ">
        <video autoplay {loop_attr} muted playsinline style="width:100vw; height:100vh; object-fit: contain; background:white; outline:none;">
            <source src="data:video/mp4;base64,{base64_mp4}" type="video/mp4">
        </video>
    </div>
    """
    return html

# Helper for embedding small images as data URIs for CSS
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

# ------------------------- Minimal resistance models (kept from your app) -------------------------
def resistance_hol(Lpp, B, T, V, rho, nu, Cb, S, lcb, Cwp, Cp, Cm, Abt, hb, At, Cstern, iE, dCF):
    Re = V * Lpp / nu if nu and Lpp else 0.0
    Cf = 0.075 / ((np.log10(Re) - 2) ** 2) if Re > 0 else 0.0
    k1 = 1 + 0.15 * (Cb if not pd.isna(Cb) else 0.0)
    Rf = 0.5 * rho * V**2 * S * Cf * k1
    Fn = V / np.sqrt(9.81 * Lpp) if Lpp > 0 else 0.0
    Rr = 0.5 * rho * V**2 * S * (0.004 + 0.002 * (Cb if not pd.isna(Cb) else 0.0)**2) * (1 + 0.6 * np.exp(-((Fn - 0.25)/0.05)**2))
    Rt = Rf + Rr
    return {'Rt': Rt, 'Rf': Rf, 'Rr': Rr}

def resistance_van(LWL, B, T, V, rho, nu, nabla, S, Cp, k2_factor):
    g = 9.81
    Rn = V * LWL / nu if nu and LWL else 0.0
    Cf = 0.075 / (np.log10(Rn) - 2)**2 if Rn > 0 else 0.0
    Rf = 0.5 * rho * S * V**2 * (Cf + (k2_factor if not pd.isna(k2_factor) else 0.0))
    Fn = V / np.sqrt(g * LWL) if LWL > 0 else 0.0
    Rr = (1.1 + 0.3 * (Cp if not pd.isna(Cp) else 0.0)) * (Fn**2 / (0.3**2 + Fn**2)) * 0.5 * rho * g * ((nabla**(2/3)) if nabla and nabla > 0 else 0.0)
    Rt = Rf + Rr
    return {'Rt': Rt, 'Rf': Rf, 'Rr': Rr}

# ---------- default ship CSV content (fallback) ----------
csv_data = """ShipType,v,rho,nu,LWL,LPP,Ld,B,T,nabla,S,Cp,Cm,lcb,iE,dCF,CB,CWP,ABT,hB,AT,Cstern,Sapp,k2_factor
Cargo Ship,15,1025,1.19E-06,140,135,N/A,22,8.5,12000,3400,0.68,0.99,-1.5,22,0.0005,0.67,0.78,30,4.5,25,80,30,0.3
Tanker,14,1025,1.19E-06,240,230,N/A,42,15.5,85000,14500,0.81,0.995,0.5,18,0.0005,0.8,0.88,80,8,70,120,80,0.3
Container,22,1025,1.19E-06,280,270,N/A,32.2,13.5,65000,12100,0.65,0.985,1.2,12,0.0005,0.64,0.75,60,7,40,90,60,0.2
Passenger,20,1025,1.19E-06,210,200,N/A,28,8,30000,6800,0.7,0.99,0.8,15,0.0005,0.69,0.79,20,6,55,70,50,0.25
Fishing Vessel,12,1025,1.19E-06,45,42,43.5,9.5,4.5,750,550,0.62,0.9,-3.5,30,0.0005,0.55,0.85,0,0,0,5,0,0.05
"""

# ---------- load ship_data.csv or fallback ----------
if os.path.exists(SHIP_CSV):
    try:
        res_df = pd.read_csv(SHIP_CSV)
    except Exception:
        res_df = pd.read_csv(StringIO(csv_data))
        try:
            res_df.to_csv(SHIP_CSV, index=False)
        except Exception:
            pass
else:
    res_df = pd.read_csv(StringIO(csv_data))
    try:
        res_df.to_csv(SHIP_CSV, index=False)
    except Exception:
        pass

FIELDNAMES = [
    "TIMESTAMP", "START_LAT", "START_LON", "END_LAT", "END_LON",
    "SHIP_TYPE", "SHIP_SPEED_KNOTS", "ETD", "ETA",
    "DISTANCE_NM", "DISTANCE_KM", "DURATION_HOURS",
    "WAVE", "WIND", "CURRENT",
    "NUM_WAYPOINTS", "NUM_CLUSTERS",
    "FEEDBACK_RATING", "FEEDBACK_TEXT"
]
SHIP_FIELDS = list(res_df.columns)

def ensure_csv_exists(path, header_fields=None):
    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            if header_fields:
                writer = csv.DictWriter(f, fieldnames=header_fields, quoting=csv.QUOTE_MINIMAL)
                writer.writeheader()
            else:
                f.write("")

def append_voyage_to_csv(path, data):
    ensure_csv_exists(path, FIELDNAMES)
    row = {k: ("" if data.get(k) is None else data.get(k)) for k in FIELDNAMES}
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(row)

def update_feedback_in_csv(path, timestamp, rating, text):
    try:
        ensure_csv_exists(path, FIELDNAMES)
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if not lines:
            return False
        updated_rows = []
        found = False
        for raw in lines[1:]:
            raw = raw.rstrip("\n")
            parts = raw.split(",")
            if len(parts) > len(FIELDNAMES):
                fixed = parts[: len(FIELDNAMES) - 1] + [",".join(parts[len(FIELDNAMES) - 1 :])]
                parts = fixed
            if len(parts) < len(FIELDNAMES):
                parts = parts + [""] * (len(FIELDNAMES) - len(parts))
            row = dict(zip(FIELDNAMES, parts))
            if row.get("TIMESTAMP", "") == timestamp:
                row["FEEDBACK_RATING"] = str(rating)
                row["FEEDBACK_TEXT"] = text
                found = True
            updated_rows.append(row)
        if not found:
            new_row = {k: "" for k in FIELDNAMES}
            new_row["TIMESTAMP"] = timestamp
            new_row["FEEDBACK_RATING"] = str(rating)
            new_row["FEEDBACK_TEXT"] = text
            updated_rows.append(new_row)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES, quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()
            for r in updated_rows:
                out = {k: ("" if r.get(k) is None else r.get(k)) for k in FIELDNAMES}
                writer.writerow(out)
        return True
    except Exception as e:
        st.error(f"Failed to update feedback in CSV: {e}")
        return False

def save_ship_df(df):
    try:
        df.to_csv(SHIP_CSV, index=False)
        return True
    except Exception as e:
        st.error(f"Failed to save ship data: {e}")
        return False

# ------------------------- Session defaults -------------------------
if "theme_flag" not in st.session_state: st.session_state["theme_flag"] = 0
if "nav" not in st.session_state: st.session_state["nav"] = "HOME"
if "route_generated" not in st.session_state: st.session_state["route_generated"] = False
if "show_res" not in st.session_state: st.session_state["show_res"] = False
if "voyage_saved" not in st.session_state: st.session_state["voyage_saved"] = False
if "voyage_timestamp" not in st.session_state: st.session_state["voyage_timestamp"] = None
if "feedback_rating" not in st.session_state: st.session_state["feedback_rating"] = 3
if "feedback_text" not in st.session_state: st.session_state["feedback_text"] = "Average: Routine voyage with some manageable issues."
if "open_feedback" not in st.session_state: st.session_state["open_feedback"] = False
if "ship_df" not in st.session_state: st.session_state["ship_df"] = res_df.copy()
if "ship_editor_state" not in st.session_state: st.session_state["ship_editor_state"] = {"mode": None}
if "start" not in st.session_state: st.session_state.start = [None, None]
if "end" not in st.session_state: st.session_state.end = [None, None]
if "route" not in st.session_state: st.session_state.route = None
if "clusters" not in st.session_state: st.session_state.clusters = []
if "splash_played" not in st.session_state: st.session_state.splash_played = False

# ------------------------- CSS + header -------------------------
# Small layout CSS and theme variables
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
    "<style>\n" + root_vars + f"""
    [data-testid="stAppViewContainer"] {{
      background: url("{bg_uri}") no-repeat center center fixed;
      background-size: cover;
    }}
    header {{ height: 5px; padding: 0; }}
    .block-container {{ padding-top: 1px; }}
    .ivrot-header {{ position: relative; top: 25px; left:0; right:0; display:flex; align-items:center; justify-content:space-between; padding:8px 50px; box-sizing:border-box; background:var(--ivrot-bg) !important; color:var(--ivrot-text) !important; border-radius:0 0 12px 12px; box-shadow:0 8px 24px rgba(0,0,0,0.12); }}
    .ivrot-left img {{ height:200px; width:auto; display:block; }}
    .ivrot-title {{ font-weight:800; font-size:50px; margin:0; color:var(--ivrot-text) !important; }}
    .ivrot-subtitle {{ font-size:30px; margin:0; opacity:0.85; color:var(--ivrot-text) !important; }}
    .ivrot-nav-row {{ display:flex; gap:16px; align-items:center; margin-top:20px; transform:translateY(40px); }}
    .ivrot-nav-row button, .stButton > button {{ padding:14px 24px !important; border-radius:12px !important; font-weight:700 !important; }}
    @media (max-width: 800px) {{
      .ivrot-left img {{ height:64px; }} .ivrot-title {{ font-size:16px; }} .ivrot-nav-row {{ margin-top:10px; transform: translateY(24px); }} .ivrot-header {{ padding:10px 14px; }}
    }}
    </style>
    """,
    unsafe_allow_html=True
)
st.markdown(set_dark_script, unsafe_allow_html=True)

logo_uri = logo_light_uri if st.session_state["theme_flag"] == 0 else logo_dark_uri
logo_html = f'<img src="{logo_uri}" alt="IVROT logo">' if logo_uri else "<div style='font-weight:800'>IVROT</div>"

st.markdown(f"""
<div class="ivrot-header" role="banner">
  <div class="ivrot-left">{logo_html}</div>
  <div style="display:flex; flex-direction:column; gap:6px;">
    <div class="ivrot-title">IVROT</div>
    <div class="ivrot-subtitle">Integrated Vessel Route Optimisation Toolkit</div>
  </div>
  <div class="ivrot-right"></div>
</div>
""", unsafe_allow_html=True)

# header buttons
c1, c2, c3 = st.columns([1,4,1])
with c2:
    nav_col1, nav_col2, nav_col3, nav_col4 = st.columns([1,1,1,1])
    with nav_col1:
        if st.button("HOME", key="nav_home"): st.session_state["nav"] = "HOME"
    with nav_col2:
        if st.button("NEW TRAJECTORY", key="nav_new"): st.session_state["nav"] = "NEW TRAJECTORY"
    with nav_col3:
        if st.button("HISTORY", key="nav_hist"): st.session_state["nav"] = "HISTORY"
    with nav_col4:
        if st.button("SHIP DATA", key="nav_shipdata"): st.session_state["nav"] = "SHIP DATA"
with c3:
    icon = "☼" if st.session_state["theme_flag"] == 0 else "☽"
    if st.button(icon, key="theme_toggle_btn"):
        st.session_state["theme_flag"] = 1 if st.session_state["theme_flag"] == 0 else 0
        if st.session_state["theme_flag"] == 1:
            st.markdown("<script>document.documentElement.classList.add('dark')</script>", unsafe_allow_html=True)
        else:
            st.markdown("<script>document.documentElement.classList.remove('dark')</script>", unsafe_allow_html=True)

# active nav highlight (JS)
active = st.session_state["nav"]
st.markdown(f"""
<script>
const btns = document.querySelectorAll('.ivrot-nav-row button, .stButton > button, div.stButton > button');
btns.forEach(b => b.removeAttribute('data-active'));
btns.forEach(b => {{
  const txt = (b.innerText || b.textContent || '').trim().toUpperCase();
  if (txt === "{active}") b.setAttribute('data-active','true');
}});
</script>
""", unsafe_allow_html=True)

 
st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

# ------------------------- Page: HOME -------------------------
if st.session_state["nav"] == "HOME":
    st.markdown("<h1 style='font-size:42px; font-weight:700;'>Welcome to IVROT</h1>", unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size:20px; font-weight:700; line-height:1.5;">
        <b>IVROT (Integrated Vessel Route Optimisation Toolkit)</b> helps maritime professionals plan and optimize vessel routes efficiently, reducing fuel use and enhancing safety.
        <br><br>
        <b>Key Features:</b><br>
        - Optimal route generation considering environmental factors.<br>
        - Integration of wave, wind, and current data.<br>
        - Customizable ship profiles (speed, ETD, type).<br>
        - Voyage history tracking.<br>
        - Feedback system for improving user experience.<br><br>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<div style='height:300px'></div>", unsafe_allow_html=True)

# ------------------------- Page: NEW TRAJECTORY -------------------------
elif st.session_state["nav"] == "NEW TRAJECTORY":
    st.header("New Trajectory")

    # land shapefile (optional)
    if "land" not in st.session_state:
        try:
            st.session_state.land = gpd.read_file(r"ne_10m_land.shp")
        except Exception:
            st.session_state.land = gpd.GeoDataFrame()

    def is_water(lat, lon):
        if st.session_state.land.empty:
            return True
        point = Point(lon, lat)
        return not st.session_state.land.contains(point).any()

    with st.sidebar.expander("Route Points & Ship"):
        start_lat = st.number_input("Start Latitude", value=st.session_state.start[0] or 0.0)
        start_lon = st.number_input("Start Longitude", value=st.session_state.start[1] or 0.0)
        end_lat = st.number_input("End Latitude", value=st.session_state.end[0] or 0.0)
        end_lon = st.number_input("End Longitude", value=st.session_state.end[1] or 0.0)

        wave = st.slider("WAVE", 0, 100, 50)
        wind = st.slider("WIND", 0, 100, 50)
        current = st.slider("CURRENT", 0, 100, 50)

        ship_names = list(st.session_state.get("ship_df", res_df)["ShipType"].astype(str).tolist())
        if not ship_names:
            ship_names = ["Unknown"]
        ship_type = st.selectbox("Select Ship Type", ship_names)
        ship_speed_knots = st.slider("Ship Speed (knots)", 5, 30, 15)
        start_date = st.date_input("Select ETD Date", value=date.today())

        reset = st.button("Reset Trajectory")
        generate = st.button("Generate Route")

        if (start_lat != 0.0 or start_lon != 0.0):
            st.session_state.start = [start_lat, start_lon]
        if (end_lat != 0.0 or end_lon != 0.0):
            st.session_state.end = [end_lat, end_lon]

    if reset:
        st.session_state.start = [None, None]
        st.session_state.end = [None, None]
        st.session_state.route = None
        st.session_state.clusters = []
        st.session_state["route_generated"] = False
        st.session_state["show_res"] = False
        st.session_state["voyage_saved"] = False
        st.session_state["voyage_timestamp"] = None
        st.session_state["feedback_rating"] = 3
        st.session_state["feedback_text"] = "Average: Routine voyage with some manageable issues."

    # --- Map for selecting points ---
    map_container = st.container()
    with map_container:
        m = folium.Map(location=[20.5937,78.9629], zoom_start=5, tiles="CartoDB positron")
        if st.session_state.start != [None, None]:
            folium.Marker(st.session_state.start, popup="Start", icon=folium.Icon(color="green")).add_to(m)
        if st.session_state.end != [None, None]:
            folium.Marker(st.session_state.end, popup="End", icon=folium.Icon(color="red")).add_to(m)
        map_click = st_folium(m, width="100%", height=600, key="click_map")
    if map_click and map_click.get("last_clicked"):
        lat = map_click["last_clicked"]["lat"]
        lon = map_click["last_clicked"]["lng"]
        if st.session_state.start == [None, None] and is_water(lat, lon):
            st.session_state.start = [lat, lon]
        elif st.session_state.end == [None, None] and is_water(lat, lon):
            st.session_state.end = [lat, lon]

    # ----------------- Synchronous route generation with overlay -----------------
    def generate_route_sync(start_coords, end_coords, ship_speed_knots_local, ship_type_local, wave_local, wind_local, current_local, start_date_local):
        """Runs synchronously in the same Streamlit run while overlay is shown."""
        # Show overlay placeholder
        overlay_placeholder = st.empty()
        html = overlay_video_html(loading_b64, loop=True, overlay_id="loading")
        if html:
            overlay_placeholder.markdown(html, unsafe_allow_html=True)
            # short pause to allow browser to start loading/playing
            time.sleep(0.15)

        try:
            # compute route (heavy work can go here)
            num_waypoints = 5
            lats = [start_coords[0]]
            lons = [start_coords[1]]
            for i in range(1, num_waypoints):
                frac = i/num_waypoints
                lat = start_coords[0] + (end_coords[0]-start_coords[0])*frac
                lon = start_coords[1] + (end_coords[1]-start_coords[1])*frac
                attempt = 0
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
            lats.append(end_coords[0])
            lons.append(end_coords[1])
            route = list(zip(lats,lons))

            # Generate clusters (may take time)
            clusters=[]
            for i in range(len(route)-1):
                lat1,lon1 = route[i]
                lat2,lon2 = route[i+1]
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

            # compute voyage metrics
            def haversine(lat1, lon1, lat2, lon2):
                R=6371.0
                phi1,phi2=math.radians(lat1),math.radians(lat2)
                dphi=math.radians(lat2-lat1)
                dlambda=math.radians(lon2-lon1)
                a=math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
                c=2*math.atan2(math.sqrt(a),math.sqrt(1-a))
                return R*c
            total_distance_km=0
            for i in range(len(route)-1):
                lat1,lon1=route[i]
                lat2,lon2=route[i+1]
                total_distance_km+=haversine(lat1,lon1,lat2,lon2)
            total_distance_nm=total_distance_km/1.852
            hours_needed=total_distance_nm/ship_speed_knots_local if ship_speed_knots_local else 0
            etd=datetime.combine(start_date_local,datetime.min.time())
            eta=etd+timedelta(hours=hours_needed)

            ts = datetime.now().isoformat()
            voyage_row = {
                "TIMESTAMP": ts,
                "START_LAT": start_coords[0],
                "START_LON": start_coords[1],
                "END_LAT": end_coords[0],
                "END_LON": end_coords[1],
                "SHIP_TYPE": ship_type_local,
                "SHIP_SPEED_KNOTS": ship_speed_knots_local,
                "ETD": etd.strftime('%d-%m-%Y %H:%M'),
                "ETA": eta.strftime('%d-%m-%Y %H:%M'),
                "DISTANCE_NM": round(total_distance_nm, 2),
                "DISTANCE_KM": round(total_distance_km, 2),
                "DURATION_HOURS": round(hours_needed, 2),
                "WAVE": wave_local,
                "WIND": wind_local,
                "CURRENT": current_local,
                "NUM_WAYPOINTS": len(route),
                "NUM_CLUSTERS": len(clusters),
                "FEEDBACK_RATING": st.session_state.get("feedback_rating", 3),
                "FEEDBACK_TEXT": st.session_state.get("feedback_text", "Average: Routine voyage with some manageable issues.")
            }
            try:
                append_voyage_to_csv(CSV_PATH, voyage_row)
                saved_ok = True
            except Exception as e:
                saved_ok = False
                print("Failed saving voyage:", e)

            # Update session state (done after heavy compute)
            st.session_state.route = route
            st.session_state.clusters = clusters
            st.session_state["route_generated"] = True
            st.session_state["show_res"] = False
            st.session_state["voyage_saved"] = saved_ok
            st.session_state["voyage_timestamp"] = ts

        except Exception as e:
            st.error(f"Route generation failed: {e}")
            traceback.print_exc()

        finally:
            # hide overlay
            try:
                overlay_placeholder.empty()
            except Exception:
                pass

    # If user clicked the generate button, run the synchronous generator with overlay
    if generate:
        if st.session_state.start == [None, None] or st.session_state.end == [None, None]:
            st.warning("Please set start and end coordinates (via map click or the sidebar) before generating.")
        else:
            # Run heavy function synchronously while overlay is present
            generate_route_sync(
                start_coords=st.session_state.start.copy(),
                end_coords=st.session_state.end.copy(),
                ship_speed_knots_local=ship_speed_knots,
                ship_type_local=ship_type,
                wave_local=wave,
                wind_local=wind,
                current_local=current,
                start_date_local=start_date
            )
            # After the synchronous function completes, page continues to render normally

    # --- Show final map with route & clusters (if available) ---
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

    # --- Buttons for resistance & feedback (post generate) ---
    if st.session_state.get("route_generated", False):
        col_a, col_b = st.columns([1,1])
        with col_a:
            if st.button("Show Resistance Curve", key="show_res_btn"):
                st.session_state["show_res"] = True
        with col_b:
            if st.button("Feedback", key="feedback_btn"):
                st.session_state["open_feedback"] = True

    # Resistance plot
    if st.session_state.get("show_res", False):
        try:
            ship_df_local = st.session_state.get("ship_df", res_df)
            mask = ship_df_local['ShipType'].astype(str).str.strip().str.upper() == str(ship_type).strip().upper()
            if mask.any():
                ship_row = ship_df_local[mask].iloc[0]
            else:
                contains_mask = ship_df_local['ShipType'].astype(str).str.strip().str.upper().str.contains(str(ship_type).strip().upper())
                if contains_mask.any():
                    ship_row = ship_df_local[contains_mask].iloc[0]
                else:
                    ship_row = ship_df_local.iloc[0]

            speeds_knots = np.linspace(0.1, 25, 100)
            speeds_ms = speeds_knots * 0.514444
            total_resistance = []
            LWL_val = ship_row.get('LWL', ship_row.get('LPP', 0))
            try:
                LWL_num = float(LWL_val)
            except Exception:
                LWL_num = 0

            if LWL_num > 100:
                for v_ms in speeds_ms:
                    res = resistance_hol(
                        float(ship_row.get('LPP', 0) or 0), float(ship_row.get('B', 0) or 0), float(ship_row.get('T', 0) or 0),
                        v_ms, float(ship_row.get('rho', 1025) or 1025), float(ship_row.get('nu', 1.19e-6) or 1.19e-6),
                        float(ship_row.get('CB', 0) or 0), float(ship_row.get('S', 0) or 0), float(ship_row.get('lcb', 0) or 0),
                        ship_row.get('CWP', 0), ship_row.get('Cp', 0), ship_row.get('Cm', 0), ship_row.get('ABT', 0), ship_row.get('hB', 0),
                        ship_row.get('AT', 0), ship_row.get('Cstern', 0), ship_row.get('iE', 0), ship_row.get('dCF', 0)
                    )
                    total_resistance.append(res['Rt'])
            else:
                for v_ms in speeds_ms:
                    res = resistance_van(
                        float(ship_row.get('LWL', 0) or 0), float(ship_row.get('B', 0) or 0), float(ship_row.get('T', 0) or 0),
                        v_ms, float(ship_row.get('rho', 1025) or 1025), float(ship_row.get('nu', 1.19e-6) or 1.19e-6),
                        float(ship_row.get('nabla', 0) or 0), float(ship_row.get('S', 0) or 0), float(ship_row.get('Cp', 0) or 0), float(ship_row.get('k2_factor', 0) or 0)
                    )
                    total_resistance.append(res['Rt'])

            fig, ax = plt.subplots(figsize=(12, 6))
            ax.plot(speeds_knots, np.array(total_resistance) / 1000, marker='o', linestyle='-', markersize=4)
            ax.set_title(f"Total resistance vs speed for {int(LWL_num) if LWL_num else 'N/A'} m {ship_row.get('ShipType','')}")
            ax.set_xlabel('Speed (kn)')
            ax.set_ylabel('Total resistance (kN)')
            ax.grid(True, which='major', linestyle='--', linewidth=0.5)
            ax.minorticks_on()
            st.subheader("Resistance plot for selected ship")
            st.pyplot(fig)
            plt.close(fig)
        except Exception as e:
            st.warning(f"Could not generate resistance plot: {e}")

    # Feedback expander
    if st.session_state.get("open_feedback", False):
        with st.expander("Voyage Feedback", expanded=True):
            st.write("Please provide your feedback for this voyage.")
            with st.form("feedback_form"):
                rating = st.slider("Rating (1-5)", min_value=1, max_value=5, value=st.session_state.get('feedback_rating',3))
                text = st.text_area("Feedback text", value=st.session_state.get('feedback_text', "Average: Routine voyage with some manageable issues."), height=150)
                submitted = st.form_submit_button("Submit Feedback")
                if submitted:
                    st.session_state['feedback_rating'] = int(rating)
                    st.session_state['feedback_text'] = text.strip() if text.strip() else "Average: Routine voyage with some manageable issues."
                    if st.session_state.get('voyage_timestamp'):
                        success = update_feedback_in_csv(CSV_PATH, st.session_state['voyage_timestamp'], st.session_state['feedback_rating'], st.session_state['feedback_text'])
                        if success:
                            st.success("Thank you — your feedback has been saved.")
                    st.session_state['open_feedback'] = False

    # Sidebar voyage info
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
        hours_needed=total_distance_nm/ship_speed_knots if ship_speed_knots else 0
        etd=datetime.combine(start_date,datetime.min.time())
        eta=etd+timedelta(hours=hours_needed)
        st.sidebar.markdown("### Voyage Info")
        st.sidebar.write(f"**Ship Type:** {ship_type}")
        st.sidebar.write(f"**Distance:** {total_distance_nm:.1f} NM ({total_distance_km:.1f} km)")
        st.sidebar.write(f"**ETD:** {etd.strftime('%Y-%m-%d %H:%M')}")
        st.sidebar.write(f"**ETA:** {eta.strftime('%Y-%m-%d %H:%M')}")
        st.sidebar.write(f"**Duration:** {hours_needed:.1f} hrs")

# ------------------------- Page: SHIP DATA -------------------------
elif st.session_state["nav"] == "SHIP DATA":
    st.header("Ship Data")
    ensure_csv_exists(SHIP_CSV, SHIP_FIELDS)
    try:
        df_ships = pd.read_csv(SHIP_CSV)
        st.session_state["ship_df"] = df_ships.copy()
    except Exception:
        df_ships = st.session_state.get("ship_df", res_df)
    st.dataframe(df_ships, use_container_width=True)
    st.markdown("---")
    col1, col2, col3 = st.columns([1,1,1])
    with col1:
        if st.button("Add Ship"):
            st.session_state["ship_editor_state"] = {"mode": "add"}
    with col2:
        if st.button("Edit Ship"):
            st.session_state["ship_editor_state"] = {"mode": "edit"}
    with col3:
        if st.button("Delete Ship"):
            st.session_state["ship_editor_state"] = {"mode": "delete"}
    mode = st.session_state.get("ship_editor_state", {}).get("mode")
    if mode == "add":
        st.subheader("Add new ship row")
        with st.form("add_ship_form"):
            new_vals = {}
            for col in SHIP_FIELDS:
                new_vals[col] = st.text_input(col, value="")
            submitted = st.form_submit_button("Save new ship")
            if submitted:
                try:
                    df_new = st.session_state.get("ship_df", res_df).copy()
                    df_new = df_new.append(new_vals, ignore_index=True)
                    if save_ship_df(df_new):
                        st.success("New ship saved to ship_data.csv")
                        st.session_state["ship_df"] = df_new
                        st.session_state["ship_editor_state"] = {"mode": None}
                except Exception as e:
                    st.error(f"Failed to add ship: {e}")
    elif mode == "edit":
        st.subheader("Edit existing ship row")
        ship_list = st.session_state.get("ship_df", res_df)["ShipType"].astype(str).tolist()
        selected = st.selectbox("Select ship to edit", ship_list)
        if selected:
            row = st.session_state.get("ship_df", res_df)
            row_idx = row[row["ShipType"].astype(str) == str(selected)].index
            if not row_idx.empty:
                i = int(row_idx[0])
                current = row.loc[i].to_dict()
                with st.form("edit_ship_form"):
                    edited = {}
                    for col in SHIP_FIELDS:
                        edited[col] = st.text_input(col, value=str(current.get(col, "")))
                    submitted2 = st.form_submit_button("Save changes")
                    if submitted2:
                        try:
                            df_edit = st.session_state.get("ship_df", res_df).copy()
                            for col in SHIP_FIELDS:
                                df_edit.at[i, col] = edited[col]
                            if save_ship_df(df_edit):
                                st.success("Ship data updated")
                                st.session_state["ship_df"] = df_edit
                                st.session_state["ship_editor_state"] = {"mode": None}
                        except Exception as e:
                            st.error(f"Failed to edit ship: {e}")
    elif mode == "delete":
        st.subheader("Delete ship row")
        ship_list = st.session_state.get("ship_df", res_df)["ShipType"].astype(str).tolist()
        selected_del = st.selectbox("Select ship to delete", ship_list)
        if selected_del:
            if st.button("Confirm delete"):
                try:
                    df_del = st.session_state.get("ship_df", res_df).copy()
                    df_del = df_del[df_del["ShipType"].astype(str) != str(selected_del)]
                    if save_ship_df(df_del):
                        st.success("Ship deleted")
                        st.session_state["ship_df"] = df_del
                        st.session_state["ship_editor_state"] = {"mode": None}
                except Exception as e:
                    st.error(f"Failed to delete ship: {e}")

# ------------------------- Page: HISTORY -------------------------
elif st.session_state["nav"] == "HISTORY":
    st.header("Voyage History")
    try:
        ensure_csv_exists(CSV_PATH, FIELDNAMES)
        df = pd.read_csv(CSV_PATH)
        st.dataframe(df,use_container_width=True)
    except Exception as e:
        st.error(f"Error loading CSV: {e}")

# End of file
