# comeonnn_fixed_final.py
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

# --- Added imports for resistance plotting (minimal addition) ---
import numpy as np
import matplotlib.pyplot as plt
from io import StringIO
import os
import csv

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

# ---------- Paths (update if needed) ----------
BG_IMAGE = r"Navigation_2.jpg"
LOGO_LIGHT_PNG = Path(r"IVROT-removebg-preview.png")
LOGO_DARK_PNG = Path(r"DARK-removebg-preview.png")
LOGO_LIGHT_JPG = LOGO_LIGHT_PNG.with_suffix(".jpg")
LOGO_DARK_JPG = LOGO_DARK_PNG.with_suffix(".jpg")
ICO_PATH = Path(r"IVROT.ico")
CSV_PATH = r"voyages.csv"

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

# -----------------------------
# --- Resistance utilities (MINIMAL ADDITION) ---
# -----------------------------
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

csv_data = """ShipType,v,rho,nu,LWL,LPP,Ld,B,T,nabla,S,Cp,Cm,lcb,iE,dCF,CB,CWP,ABT,hB,AT,Cstern,Sapp,k2_factor
Cargo Ship,15,1025,1.19E-06,140,135,N/A,22,8.5,12000,3400,0.68,0.99,-1.5,22,0.0005,0.67,0.78,30,4.5,25,80,30,0.3
Tanker,14,1025,1.19E-06,240,230,N/A,42,15.5,85000,14500,0.81,0.995,0.5,18,0.0005,0.8,0.88,80,8,70,120,80,0.3
Container,22,1025,1.19E-06,280,270,N/A,32.2,13.5,65000,12100,0.65,0.985,1.2,12,0.0005,0.64,0.75,60,7,40,90,60,0.2
Passenger,20,1025,1.19E-06,210,200,N/A,28,8,30000,6800,0.7,0.99,0.8,15,0.0005,0.69,0.79,20,6,55,70,50,0.25
Fishing Vessel,12,1025,1.19E-06,45,42,43.5,9.5,4.5,750,550,0.62,0.9,-3.5,30,0.0005,0.55,0.85,0,0,0,5,0,0.05
"""
res_df = pd.read_csv(StringIO(csv_data))
print(res_df)
# ----------------------------- end resistance utilities -----------------------------

# ---------- CSV helpers for voyages ----------
FIELDNAMES = [
    "TIMESTAMP", "START_LAT", "START_LON", "END_LAT", "END_LON",
    "SHIP_TYPE", "SHIP_SPEED_KNOTS", "ETD", "ETA",
    "DISTANCE_NM", "DISTANCE_KM", "DURATION_HOURS",
    "WAVE", "WIND", "CURRENT",
    "NUM_WAYPOINTS", "NUM_CLUSTERS",
    "FEEDBACK_RATING", "FEEDBACK_TEXT"
]

def ensure_csv_exists(path):
    if not os.path.exists(path):
        # create file with header
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES, quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()

def append_voyage_to_csv(path, data):
    ensure_csv_exists(path)
    # ensure all keys exist
    row = {k: ("" if data.get(k) is None else data.get(k)) for k in FIELDNAMES}
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(row)

def update_feedback_in_csv(path, timestamp, rating, text):
    try:
        ensure_csv_exists(path)
        # read raw lines
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if not lines:
            return False

        updated_rows = []
        found = False

        for raw in lines[1:]:
            raw = raw.rstrip("\n")
            parts = raw.split(",")
            # combine extra splits into last field (FEEDBACK_TEXT) if the line had unquoted commas
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

        # write back using csv writer to properly quote fields
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

# ---------- Page config ----------
page_icon = str(ICO_PATH) if ICO_PATH.exists() else None
st.set_page_config(page_title="IVROT", layout="wide", page_icon=page_icon)

# ---------- Session state defaults ----------
if "theme_flag" not in st.session_state:
    st.session_state["theme_flag"] = 0
if "nav" not in st.session_state:
    st.session_state["nav"] = "HOME"
# flags for route & resistance UI
if "route_generated" not in st.session_state:
    st.session_state["route_generated"] = False
if "show_res" not in st.session_state:
    st.session_state["show_res"] = False
# flags for voyage saving & feedback
if "voyage_saved" not in st.session_state:
    st.session_state["voyage_saved"] = False
if "voyage_timestamp" not in st.session_state:
    st.session_state["voyage_timestamp"] = None
if "feedback_rating" not in st.session_state:
    st.session_state["feedback_rating"] = 3
if "feedback_text" not in st.session_state:
    st.session_state["feedback_text"] = "Average: Routine voyage with some manageable issues."
if "open_feedback" not in st.session_state:
    st.session_state["open_feedback"] = False

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

# Use a single f-string only where safe (root_vars inserted); other large CSS blocks will be concatenated to avoid brace parsing.
st.markdown(
    "<style>\n" + root_vars + """
    /* background */
    [data-testid="stAppViewContainer"] {
      background: url(\"""" + bg_uri + """\") no-repeat center center fixed;
      background-size: cover;
    }

    /* Header (styles kept the same) */
    .ivrot-header {
      position:  flexible;  
      top: 25px;
      left: 0;
      right: 0;
      width: 100d%;
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
    }

    .ivrot-left { display:flex; align-items:center; gap:16px; min-width:40px; }
    .ivrot-left img { height:200px; width:auto; display:block; }

    .ivrot-center { display:flex; flex-direction:column; align-items:left; gap:5px; flex:1 1 auto; }
    .ivrot-title { font-weight:800; font-size:50px; margin:0; color:var(--ivrot-text) !important; }
    .ivrot-subtitle { font-size:30px; margin:0; opacity:0.85; color:var(--ivrot-text) !important; }

    .ivrot-nav-row {
      display:flex;
      background: var(--ivrot-bg) !important;
      color: var(--ivrot-text) !important;
      flex-direction:column;
      gap:16px; /* increased gap between buttons */
      align-items:center;
      margin-top:20px; /* lowered buttons below header */
      transform: translateY(40px); /* move buttons lower */
      transition: transform 160ms ease;
      pointer-events: auto;
    }

    .ivrot-nav-row button,
    .stButton > button,
    div.stButton > button {
      background: var(--ivrot-bg) !important;
      color: var(--ivrot-text) !important;
      border: 1px solid var(--ivrot-border) !important;
      padding: 14px 24px !important; /* bigger buttons */
      border-radius: 12px !important;
      font-weight:700 !important;
      cursor:pointer !important;
      font-size:18px !important; /* larger text */
      transition: transform 120ms ease, box-shadow 120ms ease, background-color 120ms ease, color 120ms ease, border-color 120ms ease !important;
    }

    .ivrot-nav-row button:hover,
    .stButton > button:hover,
    div.stButton > button:hover {
      transform: translateY(-2px) !important;
      box-shadow: var(--ivrot-hover-shadow) !important;
    }

    .ivrot-nav-row button[data-active="true"],
    .stButton > button[data-active="true"],
    div.stButton > button[data-active="true"] {
      box-shadow: none !important;
      background: var(--ivrot-bg) !important;
      color: var(--ivrot-text) !important;
      border-width: 2px !important;
    }

    .ivrot-right button {
      background: transparent !important;
      border: none !important;
      font-size:20px !important;
      cursor:pointer !important;
      padding:8px !important;
      border-radius:8px !important;
      color: var(--ivrot-text) !important;
      font-weight:700 !important;
    }
    .ivrot-right button:hover { background: rgba(0,0,0,0.06) !important; }

    @media (max-width: 800px) {
      .ivrot-left img { height:64px; }
      .ivrot-title { font-size:16px; }
      .ivrot-nav-row { margin-top:10px; transform: translateY(24px); }
      .ivrot-nav-row button { padding:10px 16px; font-size:16px; }
      .ivrot-header { padding:10px 14px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(set_dark_script, unsafe_allow_html=True)

# --- Feedback box solid background (white in light theme, dark in dark theme) ---
# Build CSS via concatenation so literal braces don't get parsed by Python format/f-strings.
if st.session_state.get('theme_flag', 0) == 0:
    fb_bg = "#0b1220"
    fb_text = "#f8fafc"
else:
    fb_bg = "#0b1220"
    fb_text = "#f8fafc"

feedback_css = (
    "<style>\n"
    ":root { --ivrot-feedback-bg: " + fb_bg + "; --ivrot-feedback-text: " + fb_text + "; }\n"
    "div[data-testid=\"stExpander\"] > .stExpanderHeader,\n"
    "div[data-testid=\"stExpander\"] > .stExpanderContent,\n"
    ".stExpander,\n"
    ".streamlit-expander,\n"
    ".st-expander,\n"
    ".stExpanderHeader,\n"
    ".stExpanderContent {\n"
    "  background: var(--ivrot-bg) !important;\n"
    "  color: var(--ivrot-text) !important;\n"
    "  padding: 12px 14px !important;\n"
    "  border-radius: 10px !important;\n"
    "  box-shadow: none !important;\n"
    "}\n"
    "div[data-testid=\"stExpander\"] textarea,\n"
    "div[data-testid=\"stExpander\"] input,\n"
    ".stExpander textarea,\n"
    ".stExpander input {\n"
    "  color: var(--ivrot-text) !important;\n"
    "  background: var(--ivrot-bg) !important;\n"
    "}\n"
    "div[data-testid=\"stExpander\"] .stButton > button,\n"
    ".stExpander .stButton > button {\n"
    "  color: var(--ivrot-text) !important;background: var(--ivrot-bg) !important;\n  border-color: white !important;\n"
    "}\n"
    "</style>\n"
)

st.markdown(feedback_css, unsafe_allow_html=True)



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
# Build JS string by concatenation so Python does not try to parse JS braces.
active = st.session_state["nav"]
js_str = (
    "<script>"
    "const btns = document.querySelectorAll('.ivrot-nav-row button, .stButton > button, div.stButton > button');"
    "btns.forEach(b => b.removeAttribute('data-active'));"
    "btns.forEach(b => {"
    "  const txt = (b.innerText || b.textContent || '').trim().toUpperCase();"
    "  if (txt === \"" + str(active) + "\") {"
    "    b.setAttribute('data-active', 'true');"
    "  }"
    "});"
    "</script>"
)
st.markdown(js_str, unsafe_allow_html=True)

# ---------- PAGE CONTENT ----------
st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

# ---------- HOME PAGE ----------
if st.session_state["nav"] == "HOME":
    st.markdown(
    """
    <h1  font-size: 42px; color: WHITE; font-weight: 700;'>
        Welcome to IVROT
    </h1>
    """,
    unsafe_allow_html=True
)
    st.markdown(
    """
    <div style="font-size:20px; font-weight:700; line-height:1.5;">
        <b>IVROT (Integrated Vessel Route Optimisation Toolkit)</b> helps maritime professionals plan and optimize vessel routes efficiently, reducing fuel use and enhancing safety.
        <br><br>
        <b>Key Features:</b><br>
        - Optimal route generation considering environmental factors.<br>
        - Integration of wave, wind, and current data.<br>
        - Customizable ship profiles (speed, ETD, type).<br>
        - Voyage history tracking.<br>
        - Feedback system for improving user experience.<br><br>
        Your go-to tool for smarter and safer maritime navigation.
    </div>
    """,
    unsafe_allow_html=True
)

    st.markdown("<div style='height:400px'></div>", unsafe_allow_html=True)


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
        st.session_state.land = gpd.read_file(r"ne_10m_land.shp")

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

        # ---- SYNC manual sidebar coords into session_state so Generate works even without map clicks ----
        # (minimal and safe: only set if user provided non-zero values)
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

        # mark route generated and reset show flag (no automatic plotting)
        st.session_state["route_generated"] = True
        st.session_state["show_res"] = False

        # --- compute voyage metrics for CSV ---
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

        # --- Prepare voyage dict and append to CSV (defaults used immediately if user doesn't submit feedback) ---
        if not st.session_state.get("voyage_saved", False):
            ts = datetime.now().isoformat()
            st.session_state["voyage_timestamp"] = ts
            voyage_row = {
                "TIMESTAMP": ts,
                "START_LAT": st.session_state.start[0],
                "START_LON": st.session_state.start[1],
                "END_LAT": st.session_state.end[0],
                "END_LON": st.session_state.end[1],
                "SHIP_TYPE": ship_type,
                "SHIP_SPEED_KNOTS": ship_speed_knots,
                "ETD": etd.strftime('%d-%m-%Y %H:%M'),
                "ETA": eta.strftime('%d-%m-%Y %H:%M'),
                "DISTANCE_NM": round(total_distance_nm, 2),
                "DISTANCE_KM": round(total_distance_km, 2),
                "DURATION_HOURS": round(hours_needed, 2),
                "WAVE": wave,
                "WIND": wind,
                "CURRENT": current,
                "NUM_WAYPOINTS": len(st.session_state.route),
                "NUM_CLUSTERS": len(st.session_state.clusters),
                "FEEDBACK_RATING": st.session_state.get("feedback_rating", 3),
                "FEEDBACK_TEXT": st.session_state.get("feedback_text", "Average: Routine voyage with some manageable issues.")
            }
            try:
                append_voyage_to_csv(CSV_PATH, voyage_row)
                st.session_state["voyage_saved"] = True
            except Exception as e:
                st.error(f"Failed to save voyage: {e}")

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

    # --- BUTTONS: Show Resistance Curve & Feedback (appears only after generation) ---
    if st.session_state.get("route_generated", False):
        col_a, col_b = st.columns([1,1])
        with col_a:
            if st.button("Show Resistance Curve", key="show_res_btn"):
                st.session_state["show_res"] = True
        with col_b:
            if st.button("Feedback", key="feedback_btn"):
                st.session_state["open_feedback"] = True

    # If user asked to show resistance curve, compute & display it
    if st.session_state.get("show_res", False):
        # map UI names to CSV names
        name_map = {
            "Cargo Vessel": "Cargo Ship",
            "Oil Tanker": "Tanker",
            "Container Ship": "Container",
            "Passenger Ship": "Passenger",
            "Fishing Vessel": "Fishing Vessel"
        }
        res_name = name_map.get(ship_type, ship_type)
        try:
            ship_row = res_df[res_df['ShipType'].str.strip().str.upper() == res_name.strip().upper()].iloc[0]

            speeds_knots = np.linspace(0.1, 25, 100)
            speeds_ms = speeds_knots * 0.514444

            total_resistance = []
            if ship_row['LWL'] > 100:
                for v_ms in speeds_ms:
                    res = resistance_hol(ship_row['LPP'], ship_row['B'], ship_row['T'], v_ms, ship_row['rho'], ship_row['nu'],
                                         ship_row['CB'], ship_row['S'], ship_row['lcb'], ship_row['CWP'], ship_row['Cp'], ship_row['Cm'],
                                         ship_row['ABT'], ship_row['hB'], ship_row['AT'], ship_row['Cstern'], ship_row['iE'], ship_row['dCF'])
                    total_resistance.append(res['Rt'])
            else:
                for v_ms in speeds_ms:
                    res = resistance_van(ship_row['LWL'], ship_row['B'], ship_row['T'], v_ms, ship_row['rho'], ship_row['nu'],
                                         ship_row['nabla'], ship_row['S'], ship_row['Cp'], ship_row['k2_factor'])
                    total_resistance.append(res['Rt'])

            # Plot and display in Streamlit (inline)
            fig, ax = plt.subplots(figsize=(20, 10))
            ax.plot(speeds_knots, np.array(total_resistance) / 1000, marker='o', linestyle='-', markersize=4)
            ax.set_title(f"Total resistance vs speed for {int(ship_row['LWL'])} m {res_name}")
            ax.set_xlabel('Speed (kn)')
            ax.set_ylabel('Total resistance (kN)')
            ax.grid(True, which='major', linestyle='--', linewidth=0.5)
            ax.minorticks_on()
            st.subheader("Resistance plot for selected ship")
            st.pyplot(fig)
            plt.close(fig)

        except Exception as e:
            st.warning(f"Could not generate resistance plot: {e}")

    # --- Feedback expander handling (non-transparent) ---
    if st.session_state.get("open_feedback", False):
        # Use expander (non-transparent) for feedback UI
        with st.expander("Voyage Feedback", expanded=True):
            st.write("Please provide your feedback for this voyage. If you close without submitting, the default rating/text will remain.")
            with st.form("feedback_form"):
                rating = st.slider("Rating (1-5)", min_value=1, max_value=5, value=st.session_state.get('feedback_rating',3))
                text = st.text_area("Feedback text", value=st.session_state.get('feedback_text', "Average: Routine voyage with some manageable issues."), height=150)
                submitted = st.form_submit_button("Submit Feedback")
                if submitted:
                    st.session_state['feedback_rating'] = int(rating)
                    st.session_state['feedback_text'] = text.strip() if text.strip() else "Average: Routine voyage with some manageable issues."
                    # update CSV entry for this voyage timestamp
                    if st.session_state.get('voyage_timestamp'):
                        success = update_feedback_in_csv(CSV_PATH, st.session_state['voyage_timestamp'], st.session_state['feedback_rating'], st.session_state['feedback_text'])
                        if success:
                            st.success("Thank you — your feedback has been saved.")
                    st.session_state['open_feedback'] = False

    # --- Distance & ETA display in sidebar ---
    if st.session_state.route:
        # recompute distances (as above)
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
        ensure_csv_exists(CSV_PATH)
        df = pd.read_csv(CSV_PATH)
        st.dataframe(df,use_container_width=True)
    except Exception as e:
        st.error(f"Error loading CSV: {e}")





