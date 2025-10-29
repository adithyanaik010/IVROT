# comeonnn_full_theming_with_shipdata_no_toggle.py
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

import time

import streamlit as st
import base64
import time
from pathlib import Path

# -------------------------------
# CONFIG
# -------------------------------
INTRO_VIDEO = "YouCut_20251028_153909796.mp4"  # your intro video file
VIDEO_DURATION = 12  # seconds – adjust to your actual video length

st.set_page_config(page_title="IVROT", layout="wide")

# -------------------------------
# FUNCTION TO EMBED VIDEO
# -------------------------------
def embed_intro_video(video_path):
    """Play intro video full-screen once."""
    try:
        video_bytes = Path(video_path).read_bytes()
    except FileNotFoundError:
        st.error(f"❌ Video not found: {video_path}")
        return

    b64 = base64.b64encode(video_bytes).decode()
    html = f"""
    <div style="
        position:fixed;
        top:0; left:0;
        width:100%; height:100%;
        background-color:black;
        display:flex;
        justify-content:center;
        align-items:center;
        z-index:9999;">
        <video autoplay muted playsinline style="width:100%; height:100%; object-fit:cover;">
            <source src="data:video/mp4;base64,{b64}" type="video/mp4">
        </video>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

if "intro_played" not in st.session_state:
    # First time: play intro video
    embed_intro_video(INTRO_VIDEO)
    st.session_state.intro_played = True
    time.sleep(VIDEO_DURATION)  # wait until video finishes
    st.rerun()


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
SHIP_CSV = r"ship_data.csv"

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
    denom = 0.32 + (Fn ** 2 if Fn is not None else 0.0)
    Rr = (1.1 + 0.3 * (Cp if not pd.isna(Cp) else 0.0)) * ((2 * Fn) / denom if denom != 0 else 0.0) * 0.5 * rho * g * ((nabla * (2 / 3)) if (nabla and nabla > 0) else 0.0)
    Rt = Rf + Rr
    return {'Rt': Rt, 'Rf': Rf, 'Rr': Rr}

# default embedded ship CSV (used if ship_data.csv missing)
csv_data = """ShipType,v,rho,nu,LWL,LPP,Ld,B,T,nabla,S,Cp,Cm,lcb,iE,dCF,CB,CWP,ABT,hB,AT,Cstern,Sapp,k2_factor
Cargo Ship,15,1025,1.19E-06,140,135,N/A,22,8.5,12000,3400,0.68,0.99,-1.5,22,0.0005,0.67,0.78,30,4.5,25,80,30,0.3
Tanker,14,1025,1.19E-06,240,230,N/A,42,15.5,85000,14500,0.81,0.995,0.5,18,0.0005,0.8,0.88,80,8,70,120,80,0.3
Container,22,1025,1.19E-06,280,270,N/A,32.2,13.5,65000,12100,0.65,0.985,1.2,12,0.0005,0.64,0.75,60,7,40,90,60,0.2
Passenger,20,1025,1.19E-06,210,200,N/A,28,8,30000,6800,0.7,0.99,0.8,15,0.0005,0.69,0.79,20,6,55,70,50,0.25
Fishing Vessel,12,1025,1.19E-06,45,42,43.5,9.5,4.5,750,550,0.62,0.9,-3.5,30,0.0005,0.55,0.85,0,0,0,5,0,0.05
"""

# load ship data CSV if available, else fallback to embedded
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

# ---------- CSV helpers for voyages & ships ----------
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
        # create file with header
        with open(path, "w", newline="", encoding="utf-8") as f:
            if header_fields:
                writer = csv.DictWriter(f, fieldnames=header_fields, quoting=csv.QUOTE_MINIMAL)
                writer.writeheader()
            else:
                f.write("")

def append_voyage_to_csv(path, data):
    ensure_csv_exists(path, FIELDNAMES)
    # ensure all keys exist
    row = {k: ("" if data.get(k) is None else data.get(k)) for k in FIELDNAMES}
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(row)

def update_feedback_in_csv(path, timestamp, rating, text):
    try:
        ensure_csv_exists(path, FIELDNAMES)
        rows = []
        found = False
        # read using DictReader
        with open(path, "r", encoding="utf-8", newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("TIMESTAMP", "") == timestamp:
                    row["FEEDBACK_RATING"] = str(rating)
                    row["FEEDBACK_TEXT"] = text
                    found = True
                rows.append(row)
        if not found:
            new_row = {k: "" for k in FIELDNAMES}
            new_row["TIMESTAMP"] = timestamp
            new_row["FEEDBACK_RATING"] = str(rating)
            new_row["FEEDBACK_TEXT"] = text
            rows.append(new_row)
        # write back
        with open(path, "w", encoding="utf-8", newline='') as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES, quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()
            for r in rows:
                writer.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in FIELDNAMES})
        return True
    except Exception as e:
        st.error(f"Failed to update feedback in CSV: {e}")
        return False

# helpers for ship CSV
def save_ship_df(df):
    try:
        df.to_csv(SHIP_CSV, index=False)
        return True
    except Exception as e:
        st.error(f"Failed to save ship data: {e}")
        return False

# ---------- Page config ----------
page_icon = str(ICO_PATH) if ICO_PATH.exists() else None
st.set_page_config(page_title="IVROT", layout="wide", page_icon=page_icon)

# ---------- Session state defaults ----------
# Removed theme_flag; app will use Streamlit default theme + transparent header/backgrounds.
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

# keep ship dataframe in session for responsiveness
if "ship_df" not in st.session_state:
    st.session_state["ship_df"] = res_df.copy()

if "ship_editor_state" not in st.session_state:
    st.session_state["ship_editor_state"] = {"mode": None}

# NEW: store user-clicked waypoints (first click = initial, last click = final)
if "waypoints" not in st.session_state:
    st.session_state["waypoints"] = []  # list of (lat, lon) tuples, in order clicked

# preserve existing start/end/route/clusters defaults for backward compatibility
if "start" not in st.session_state:
    st.session_state.start = [None, None]
if "end" not in st.session_state:
    st.session_state.end = [None, None]
if "route" not in st.session_state:
    st.session_state.route = None
if "clusters" not in st.session_state:
    st.session_state.clusters = []

if "land" not in st.session_state:
    # geopandas read may be slow; keep in session
    try:
        st.session_state.land = gpd.read_file(r"ne_10m_land.shp")
    except Exception:
        st.session_state.land = gpd.GeoDataFrame()

def is_water(lat, lon):
    if st.session_state.land.empty:
        return True
    point = Point(lon, lat)
    return not st.session_state.land.contains(point).any()

# ---------- Inject CSS (transparent + white text where background transparent) ----------

root_vars = """
    :root {
      --ivrot-bg: #ffffff;
      --ivrot-text: #0f1724;
      --ivrot-border: rgba(2,6,23,0.06);
      --ivrot-hover-shadow: 0 8px 18px rgba(2,6,23,0.06);
    }
    """
# Use a single f-string only where safe (root_vars inserted); other large CSS blocks will be concatenated to avoid brace parsing.
st.markdown(
    "<style>\n" + root_vars + """
    /* background: allow Streamlit default + use provided background image but keep containers transparent */
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
      .ivrot-left img { height:40px; }
      .ivrot-title { font-size:16px; }
      .ivrot-nav-row { margin-top:8px; transform: translateY(8px); }
      .ivrot-nav-row button { padding:8px 12px; font-size:13px; }
      .ivrot-header { padding:8px 12px; }
    }

    /* Sidebar theming: ensure form controls and labels visible on the background image */
    div[data-testid="stSidebar"] * {
      color: var(--ivrot-text) !important;
    }

    div[data-testid="stSidebar"] input,
    div[data-testid="stSidebar"] textarea,
    div[data-testid="stSidebar"] select,
    div[data-testid="stSidebar"] .stTextInput>div>input,
    div[data-testid="stSidebar"] .stNumberInput>div>input,
    div[data-testid="stSidebar"] .stSelectbox>div>div,
    div[data-testid="stSidebar"] .stSlider>div,
    div[data-testid="stSidebar"] .stSlider>div label {
      background: transparent !important;
      color: var(--ivrot-text) !important;
      border: 1px solid rgba(255,255,255,0.12) !important;
      box-shadow: none !important;
    }

    div[data-testid="stSidebar"] .stSelectbox select,
    div[data-testid="stSidebar"] .stSelectbox div[role="listbox"],
    div[data-testid="stSidebar"] .stSelectbox .st-bg {
      background: transparent !important;
      color: var(--ivrot-text) !important;
      border: 1px solid rgba(255,255,255,0.12) !important;
    }

    div[data-testid="stSidebar"] label,
    div[data-testid="stSidebar"] .css-1adrfps,
    div[data-testid="stSidebar"] .css-1v3fvcr {
      color: var(--ivrot-text) !important;
    }

    div[data-testid="stSidebar"] .stButton > button,
    div[data-testid="stSidebar"] button {
      background: rgba(255,255,255,0.06) !important;
      color: var(--ivrot-text) !important;
      border: 1px solid rgba(255,255,255,0.12) !important;
    }

    /* Make text white when background is transparent */
    .ivrot-header,
    .ivrot-title,
    .ivrot-subtitle,
    .ivrot-nav-row,
    .ivrot-left img,
    .ivrot-right,
    div[data-testid="stSidebar"] {
      color: var(--ivrot-text) !important;
    }

    </style>
    """,
    unsafe_allow_html=True,
)

# No JS to toggle dark class — removed theme toggle entirely so Streamlit default applies.

# --- Feedback box solid background (use transparent + white text) ---
fb_bg = "transparent"
fb_text = "#ffffff"

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
    "  background: transparent !important;\n"
    "  color: var(--ivrot-feedback-text) !important;\n"
    "  padding: 12px 14px !important;\n"
    "  border-radius: 10px !important;\n"
    "  box-shadow: none !important;\n"
    "}\n"
    "div[data-testid=\"stExpander\"] textarea,\n"
    "div[data-testid=\"stExpander\"] input,\n"
    ".stExpander textarea,\n"
    ".stExpander input {\n"
    "  color: var(--ivrot-feedback-text) !important;\n"
    "  background: transparent !important;\n"
    "}\n"
    "div[data-testid=\"stExpander\"] .stButton > button,\n"
    ".stExpander .stButton > button {\n"
    "  color: var(--ivrot-feedback-text) !important;background: transparent !important;\n  border-color: var(--ivrot-feedback-text) !important;\n"
    "}\n"
    "</style>\n"
)

st.markdown(feedback_css, unsafe_allow_html=True)


# ---------- Header HTML ----------
# Use light logo if present; we picked a single logo since no theme toggle exists.
logo_uri = logo_light_uri or logo_dark_uri or ""
logo_html = f'<img src="{logo_uri}" alt="IVROT logo">' if logo_uri else "<div style='font-weight:800;color:white'>IVROT</div>"

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
    # create 4 nav buttons in the center (no theme toggle)
    col_nav1, col_nav2, col_nav3, col_nav4 = st.columns([1,1,1,1])
    with col_nav1:
        if st.button("HOME", key="nav_home"):
            st.session_state["nav"] = "HOME"
    with col_nav2:
        if st.button("NEW TRAJECTORY", key="nav_new"):
            st.session_state["nav"] = "NEW TRAJECTORY"
    with col_nav3:
        if st.button("HISTORY", key="nav_hist"):
            st.session_state["nav"] = "HISTORY"
    with col_nav4:
        if st.button("SHIP DATA", key="nav_shipdata"):
            st.session_state["nav"] = "SHIP DATA"

# ---------- Active button highlight ----------
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
    <div style="font-size:20px; font-weight:700; line-height:1.5; color: white;">
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
    # (start/end/route/clusters/waypoints/land already initialized earlier)

    # Ensure last click tracker to avoid double-appending same click on rerun
    if "last_map_click" not in st.session_state:
        st.session_state["last_map_click"] = None

    # --- Sidebar for NEW TRAJECTORY ---
    with st.sidebar.expander("Route Points & Ship"):
        start_lat = st.number_input("Start Latitude", value=st.session_state.start[0] or 0.0)
        start_lon = st.number_input("Start Longitude", value=st.session_state.start[1] or 0.0)
        end_lat = st.number_input("End Latitude", value=st.session_state.end[0] or 0.0)
        end_lon = st.number_input("End Longitude", value=st.session_state.end[1] or 0.0)

        wave = st.slider("WAVE", 0, 100, 50)
        wind = st.slider("WIND", 0, 100, 50)
        current = st.slider("CURRENT", 0, 100, 50)

        # ship type selectbox populated from ship_data.csv
        ship_names = list(st.session_state.get("ship_df", res_df)["ShipType"].astype(str).tolist())
        if not ship_names:
            ship_names = ["Unknown"]
        ship_type = st.selectbox("Select Ship Type", ship_names)
        ship_speed_knots = st.slider("Ship Speed (knots)", 5, 30, 15)
        start_date = st.date_input("Select ETD Date", value=date.today())

        reset = st.button("Reset Trajectory")
        generate = st.button("Generate Route")

        # If user types start/end in sidebar and there are no waypoints yet, seed them
        if (start_lat != 0.0 or start_lon != 0.0) and not st.session_state.waypoints:
            st.session_state.start = [start_lat, start_lon]
            st.session_state.waypoints = [(float(start_lat), float(start_lon))]
        if (end_lat != 0.0 or end_lon != 0.0) and not st.session_state.waypoints:
            # if start was seeded above, now append end
            if st.session_state.waypoints:
                st.session_state.waypoints.append((float(end_lat), float(end_lon)))
            else:
                st.session_state.waypoints = [(float(end_lat), float(end_lon))]
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
        st.session_state.waypoints = []
        st.session_state.last_map_click = None

    # --- Map for selecting points ---
    map_container = st.container()
    with map_container:
        m = folium.Map(location=[20.5937,78.9629], zoom_start=5, tiles="CartoDB positron")

        # display waypoints in order (first green, intermediates blue, last red)
        if st.session_state.waypoints:
            for idx, (lat, lon) in enumerate(st.session_state.waypoints):
                if idx == 0:
                    icon = folium.Icon(color="green")
                    popup = f"Start (WP {idx+1})"
                elif idx == len(st.session_state.waypoints) - 1:
                    icon = folium.Icon(color="red")
                    popup = f"End (WP {idx+1})"
                else:
                    icon = folium.Icon(color="blue")
                    popup = f"WP {idx+1}"
                folium.Marker([lat, lon], popup=popup, icon=icon).add_to(m)
        else:
            # fallback to previously stored start/end markers (if any)
            if st.session_state.start != [None, None]:
                folium.Marker(st.session_state.start, popup="Start", icon=folium.Icon(color="green")).add_to(m)
            if st.session_state.end != [None, None]:
                folium.Marker(st.session_state.end, popup="End", icon=folium.Icon(color="red")).add_to(m)

        # get clicks
        map_click = st_folium(m, width="100%", height=600, key="click_map")

    # Append every new click (in order) to waypoints.
    # Use a last-click guard so reruns don't duplicate the same click.
    if map_click and map_click.get("last_clicked"):
        lat = float(map_click["last_clicked"]["lat"])
        lon = float(map_click["last_clicked"]["lng"])
        this_click = (round(lat, 6), round(lon, 6))
        if st.session_state.last_map_click != this_click:
            st.session_state.last_map_click = this_click
            # Append click regardless of whether water or land so user picks exact ordered waypoints.
            # We'll perform lightweight avoidance when generating the route.
            st.session_state.waypoints.append(this_click)
            # update start/end to reflect first/last clicked
            if st.session_state.waypoints:
                st.session_state.start = [st.session_state.waypoints[0][0], st.session_state.waypoints[0][1]]
                st.session_state.end = [st.session_state.waypoints[-1][0], st.session_state.waypoints[-1][1]]

    # --- Helper: take a straight segment and split/insert detours if it crosses land ---
    def build_segment_avoiding_land(p1, p2, max_depth=8):
        """
        Returns an ordered list of points starting at p2 that are reachable from p1 without hitting land
        using a simple recursive midpoint-detour method.
        p1, p2 are (lat, lon) tuples.
        """
        # internal recursive function
        def _recurse(a, b, depth):
            # safety
            if depth > max_depth:
                return [b]

            # sample along the straight line; if any sample point lies on land, we need to detour
            n_samples = 8
            for i in range(1, n_samples):
                t = i / float(n_samples)
                lat = a[0] + (b[0] - a[0]) * t
                lon = a[1] + (b[1] - a[1]) * t
                if not is_water(lat, lon):
                    # found land along the segment; compute midpoint and search for nearest water around it
                    mid = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
                    # try offsets with increasing radius (degrees). small radii first.
                    radii = [0.05, 0.1, 0.2, 0.5, 1.0, 2.0]
                    angles = list(range(0, 360, 30))
                    for r in radii:
                        for ang in angles:
                            rad = math.radians(ang)
                            cand_lat = mid[0] + r * math.cos(rad)
                            cand_lon = mid[1] + r * math.sin(rad)
                            if is_water(cand_lat, cand_lon):
                                left = _recurse(a, (cand_lat, cand_lon), depth + 1)
                                right = _recurse((cand_lat, cand_lon), b, depth + 1)
                                # left includes its endpoint; combine carefully to avoid duplicates
                                return left[:-1] + right
                    # if no nearby water found, fallback by returning b (give up)
                    return [b]
            # no land samples -> straight segment OK
            return [b]

        return _recurse(p1, p2, 0)

    # --- Generate route ---
    if generate:
        # require at least two waypoints (ordered by clicks) OR sidebar-provided start+end if waypoints empty
        if st.session_state.waypoints and len(st.session_state.waypoints) >= 2:
            clicked_route = [(float(lat), float(lon)) for lat, lon in st.session_state.waypoints]
            # Build final_route by checking each consecutive segment and inserting detours when required
            final_route = [clicked_route[0]]
            for i in range(len(clicked_route) - 1):
                a = final_route[-1]
                b = clicked_route[i + 1]
                seg_points = build_segment_avoiding_land(a, b)  # returns list of points ending at b (or detours)
                # seg_points is list of endpoints (p2) in recursion; append them sequentially
                for p in seg_points:
                    # avoid duplicate consecutive points
                    if (round(final_route[-1][0],6), round(final_route[-1][1],6)) != (round(p[0],6), round(p[1],6)):
                        final_route.append((float(p[0]), float(p[1])))
            st.session_state.route = final_route
            # ensure session start/end reflect clicked sequence first/last exactly
            st.session_state.start = [clicked_route[0][0], clicked_route[0][1]]
            st.session_state.end = [clicked_route[-1][0], clicked_route[-1][1]]
        elif st.session_state.start != [None, None] and st.session_state.end != [None, None]:
            # fallback: retain original randomized-intermediate behavior between start & end (no waypoints clicked)
            num_waypoints = 5
            lats = [st.session_state.start[0]]
            lons = [st.session_state.start[1]]
            for i in range(1, num_waypoints):
                frac = i / num_waypoints
                lat = st.session_state.start[0] + (st.session_state.end[0] - st.session_state.start[0]) * frac
                lon = st.session_state.start[1] + (st.session_state.end[1] - st.session_state.start[1]) * frac
                attempt = 0
                while True:
                    lat_offset = random.uniform(-2, 2)
                    lon_offset = random.uniform(-2, 2)
                    new_lat = lat + lat_offset
                    new_lon = lon + lon_offset
                    if is_water(new_lat, new_lon) or attempt > 10:
                        break
                    attempt += 1
                lats.append(new_lat)
                lons.append(new_lon)
            lats.append(st.session_state.end[0])
            lons.append(st.session_state.end[1])
            st.session_state.route = list(zip(lats, lons))
        else:
            st.error("Please click at least two points on the map (first click = start, last click = end) or fill start and end coordinates in the sidebar.")
            st.session_state.route = None

        # proceed with cluster generation and CSV if route was created
        if st.session_state.route:
            clusters = []
            for i in range(len(st.session_state.route) - 1):
                lat1, lon1 = st.session_state.route[i]
                lat2, lon2 = st.session_state.route[i + 1]
                for step in range(15):
                    lat = lat1 + (lat2 - lat1) * step / 20
                    lon = lon1 + (lon2 - lon1) * step / 20
                    for _ in range(8):
                        attempt = 0
                        while True:
                            offset_lat = random.gauss(0, 0.2)
                            offset_lon = random.gauss(0, 0.2)
                            new_lat = lat + offset_lat
                            new_lon = lon + offset_lon
                            if is_water(new_lat, new_lon) or attempt > 10:
                                break
                            attempt += 1
                        clusters.append({
                            "lat": new_lat, "lon": new_lon,
                            "wave": random.randint(5, 40),
                            "wind": random.randint(5, 40),
                            "current": random.randint(5, 40)
                        })
                    for _ in range(10):
                        attempt = 0
                        while True:
                            offset_lat = random.gauss(0, 0.8)
                            offset_lon = random.gauss(0, 0.8)
                            new_lat = lat + offset_lat
                            new_lon = lon + offset_lon
                            if is_water(new_lat, new_lon) or attempt > 10:
                                break
                            attempt += 1
                        clusters.append({
                            "lat": new_lat, "lon": new_lon,
                            "wave": random.randint(50, 100),
                            "wind": random.randint(50, 100),
                            "current": random.randint(50, 100)
                        })
            st.session_state.clusters = clusters

            st.session_state["route_generated"] = True
            st.session_state["show_res"] = False

            # compute voyage metrics and append to CSV (same as before)
            def haversine(lat1, lon1, lat2, lon2):
                R = 6371.0
                phi1, phi2 = math.radians(lat1), math.radians(lat2)
                dphi = math.radians(lat2 - lat1)
                dlambda = math.radians(lon2 - lon1)
                a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
                c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
                return R * c

            total_distance_km = 0
            for i in range(len(st.session_state.route) - 1):
                lat1, lon1 = st.session_state.route[i]
                lat2, lon2 = st.session_state.route[i + 1]
                total_distance_km += haversine(lat1, lon1, lat2, lon2)
            total_distance_nm = total_distance_km / 1.852
            hours_needed = total_distance_nm / ship_speed_knots
            etd = datetime.combine(start_date, datetime.min.time())
            eta = etd + timedelta(hours=hours_needed)

            # Update start/end in session (already set from waypoints)
            if st.session_state.route and len(st.session_state.route) >= 1:
                st.session_state.start = [st.session_state.route[0][0], st.session_state.route[0][1]]
                st.session_state.end = [st.session_state.route[-1][0], st.session_state.route[-1][1]]

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

    # --- Final Map with route & clusters (unchanged display logic) ---
    map_container2 = st.container()
    with map_container2:
        m2 = folium.Map(location=[20.5937,78.9629], zoom_start=5, tiles="CartoDB positron")
        if st.session_state.waypoints:
            for idx, (lat, lon) in enumerate(st.session_state.waypoints):
                if idx == 0:
                    icon = folium.Icon(color="green")
                    popup = f"Start (WP {idx+1})"
                elif idx == len(st.session_state.waypoints) - 1:
                    icon = folium.Icon(color="red")
                    popup = f"End (WP {idx+1})"
                else:
                    icon = folium.Icon(color="blue")
                    popup = f"WP {idx+1}"
                folium.Marker([lat, lon], popup=popup, icon=icon).add_to(m2)
        else:
            if st.session_state.start != [None, None]:
                folium.Marker(st.session_state.start, popup="Start", icon=folium.Icon(color="green")).add_to(m2)
            if st.session_state.end != [None, None]:
                folium.Marker(st.session_state.end, popup="End", icon=folium.Icon(color="red")).add_to(m2)

        if st.session_state.route:
            folium.PolyLine(st.session_state.route, color="blue", weight=3).add_to(m2)
        if st.session_state.clusters:
            for point in st.session_state.clusters:
                total = point["wave"] + point["wind"] + point["current"]
                tooltip_text = f"Wave: {point['wave']} | Wind: {point['wind']} | Current: {point['current']} (Total: {total}/300)"
                folium.CircleMarker(location=[point["lat"], point["lon"]],
                                    radius=2, color="green", fill=True, fill_opacity=0.6,
                                    tooltip=tooltip_text).add_to(m2)
        st_folium(m2, width="100%", height=600, key="final_map")

# ---------- SHIP DATA PAGE ----------
elif st.session_state["nav"] == "SHIP DATA":
    st.header("Ship Data")
    # ensure ship CSV exists
    ensure_csv_exists(SHIP_CSV, SHIP_FIELDS)
    # refresh session dataframe from disk
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
                    # use concat instead of deprecated append
                    df_new = pd.concat([df_new, pd.DataFrame([new_vals])], ignore_index=True)
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

# ---------- HISTORY PAGE ----------
elif st.session_state["nav"] == "HISTORY":
    st.header("Voyage History")
    try:
        ensure_csv_exists(CSV_PATH, FIELDNAMES)
        df = pd.read_csv(CSV_PATH)
        st.dataframe(df,use_container_width=True)
    except Exception as e:
        st.error(f"Error loading CSV: {e}")

# End of file
