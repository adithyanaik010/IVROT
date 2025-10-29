
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
if st.session_state.get("nav") == "NEW TRAJECTORY":
    st.header("New Trajectory (Up/Down segments + Dense clusters)")

    # -----------------------
    # session state defaults
    # -----------------------
    if "land" not in st.session_state:
        try:
            st.session_state.land = gpd.read_file(r"C:\Users\P ADITHYA M NAIK\Desktop\IVROT\ne_10m_land.shp")
        except Exception:
            try:
                st.session_state.land = gpd.read_file("ne_10m_land.shp")
            except Exception:
                st.session_state.land = gpd.GeoDataFrame()

    if "route_points" not in st.session_state:
        st.session_state.route_points = []  # ordered list of (type, lat, lon)
    if "select_mode" not in st.session_state:
        st.session_state.select_mode = None
    if "last_map_click" not in st.session_state:
        st.session_state.last_map_click = None
    if "start" not in st.session_state:
        st.session_state.start = [None, None]
    if "end" not in st.session_state:
        st.session_state.end = [None, None]
    if "route" not in st.session_state:
        st.session_state.route = None
    if "clusters" not in st.session_state:
        st.session_state.clusters = []

    # -----------------------
    # helpers
    # -----------------------
    def is_water(lat, lon):
        if st.session_state.land is None or st.session_state.land.empty:
            return True
        try:
            pt = Point(lon, lat)
            return not st.session_state.land.contains(pt).any()
        except Exception:
            return True

    def haversine_km(lat1, lon1, lat2, lon2):
        R = 6371.0
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def _point_segment_distance_km(p_lat, p_lon, a_lat, a_lon, b_lat, b_lon):
        if a_lat == b_lat and a_lon == b_lon:
            return haversine_km(p_lat, p_lon, a_lat, a_lon)
        R = 6371.0
        mean_lat = math.radians((a_lat + b_lat) / 2.0)
        ax = math.radians(a_lon) * math.cos(mean_lat) * R
        ay = math.radians(a_lat) * R
        bx = math.radians(b_lon) * math.cos(mean_lat) * R
        by = math.radians(b_lat) * R
        px = math.radians(p_lon) * math.cos(mean_lat) * R
        py = math.radians(p_lat) * R
        vx = bx - ax; vy = by - ay
        wx = px - ax; wy = py - ay
        v_len2 = vx * vx + vy * vy
        if v_len2 == 0:
            dx = px - ax; dy = py - ay
            return math.sqrt(dx * dx + dy * dy)
        t = (wx * vx + wy * vy) / v_len2
        t_clamped = max(0.0, min(1.0, t))
        proj_x = ax + t_clamped * vx
        proj_y = ay + t_clamped * vy
        dx = px - proj_x; dy = py - proj_y
        return math.sqrt(dx * dx + dy * dy)

    def distance_to_polyline_km(p_lat, p_lon, poly):
        min_d = float("inf")
        for i in range(len(poly) - 1):
            a_lat, a_lon = poly[i]
            b_lat, b_lon = poly[i + 1]
            d = _point_segment_distance_km(p_lat, p_lon, a_lat, a_lon, b_lat, b_lon)
            if d < min_d:
                min_d = d
        if min_d == float("inf"):
            return haversine_km(p_lat, p_lon, poly[0][0], poly[0][1]) if poly else float("inf")
        return min_d

    # land-avoidance recursion (kept)
    def build_segment_avoiding_land(p1, p2, max_depth=8):
        def _recurse(a, b, depth):
            if depth > max_depth:
                return [b]
            n_samples = 8
            for i in range(1, n_samples):
                t = i / float(n_samples)
                lat = a[0] + (b[0] - a[0]) * t
                lon = a[1] + (b[1] - a[1]) * t
                if not is_water(lat, lon):
                    mid = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
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
                                return left[:-1] + right
                    return [b]
            return [b]
        return _recurse(p1, p2, 0)

    # -----------------------
    # Sidebar: mode, params
    # -----------------------
    with st.sidebar.expander("Route Points & Ship"):
        st.markdown("**Select a point type, then click on the map.** Start must be placed first (green). Add any number of Waypoints (blue). Place End last (red).")
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            if st.button("Start Point", key="select_start_btn"):
                st.session_state.select_mode = "start"
        with c2:
            if st.button("Waypoint", key="select_wp_btn"):
                st.session_state.select_mode = "waypoint"
        with c3:
            if st.button("End Point", key="select_end_btn"):
                st.session_state.select_mode = "end"

        st.markdown(f"**Mode:** {st.session_state.select_mode or 'None'}")

        start_lat = st.number_input("Start Latitude", value=st.session_state.start[0] or 0.0, format="%.6f")
        start_lon = st.number_input("Start Longitude", value=st.session_state.start[1] or 0.0, format="%.6f")
        end_lat = st.number_input("End Latitude", value=st.session_state.end[0] or 0.0, format="%.6f")
        end_lon = st.number_input("End Longitude", value=st.session_state.end[1] or 0.0, format="%.6f")

        wave = st.slider("WAVE", 0, 100, 50)
        wind = st.slider("WIND", 0, 100, 50)
        current = st.slider("CURRENT", 0, 100, 50)

        # ship list from res_df csv
        try:
            ship_names = list(st.session_state.get("ship_df", res_df)["ShipType"].astype(str).tolist())
            if not ship_names:
                raise Exception("empty")
        except Exception:
            ship_names = ["Cargo Vessel", "Oil Tanker", "Container Ship", "Fishing Vessel", "Passenger Ship"]

        ship_type = st.selectbox("Select Ship Type", ship_names)
        ship_speed_knots = st.slider("Ship Speed (knots)", 5, 30, 15)
        start_date = st.date_input("Select ETD Date", value=date.today())

        reset = st.button("Reset Trajectory")
        generate = st.button("Generate Route")

        # sync manual numeric entry into session_state route_points for backward compat
        if (start_lat != 0.0 or start_lon != 0.0) and not any(pt[0] == "start" for pt in st.session_state.route_points):
            st.session_state.start = [float(start_lat), float(start_lon)]
            st.session_state.route_points.insert(0, ("start", float(start_lat), float(start_lon)))
        if (end_lat != 0.0 or end_lon != 0.0) and not any(pt[0] == "end" for pt in st.session_state.route_points):
            st.session_state.end = [float(end_lat), float(end_lon)]
            st.session_state.route_points.append(("end", float(end_lat), float(end_lon)))

    # -----------------------
    # Reset behavior
    # -----------------------
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
        st.session_state.route_points = []
        st.session_state.select_mode = None
        st.session_state.last_map_click = None

    # -----------------------
    # Map for selecting points
    # -----------------------
    map_container = st.container()
    with map_container:
        m = folium.Map(location=[20.5937, 78.9629], zoom_start=5, tiles="CartoDB positron")

        # draw ordered markers
        for idx, item in enumerate(st.session_state.route_points):
            typ, lat, lon = item[0], item[1], item[2]
            if typ == "start":
                folium.Marker([lat, lon], popup=f"Start (pos {idx + 1})", icon=folium.Icon(color="green")).add_to(m)
            elif typ == "end":
                folium.Marker([lat, lon], popup=f"End (pos {idx + 1})", icon=folium.Icon(color="red")).add_to(m)
            else:
                folium.Marker([lat, lon], popup=f"WP {idx + 1}", icon=folium.Icon(color="blue")).add_to(m)

        if not st.session_state.route_points:
            if st.session_state.start != [None, None]:
                folium.Marker(st.session_state.start, popup="Start", icon=folium.Icon(color="green")).add_to(m)
            if st.session_state.end != [None, None]:
                folium.Marker(st.session_state.end, popup="End", icon=folium.Icon(color="red")).add_to(m)

        map_click = st_folium(m, width="100%", height=600, key="click_map")

    # -----------------------
    # Map click handling
    # -----------------------
    if map_click and map_click.get("last_clicked"):
        lat = round(float(map_click["last_clicked"]["lat"]), 6)
        lon = round(float(map_click["last_clicked"]["lng"]), 6)
        click_pair = (lat, lon)
        if st.session_state.last_map_click != click_pair:
            st.session_state.last_map_click = click_pair
            mode = st.session_state.select_mode
            if mode == "start":
                st.session_state.route_points = [pt for pt in st.session_state.route_points if pt[0] != "start"]
                st.session_state.route_points.insert(0, ("start", lat, lon))
                st.session_state.start = [lat, lon]
                # keep end last
                ends = [pt for pt in st.session_state.route_points if pt[0] == "end"]
                if ends and st.session_state.route_points[-1][0] != "end":
                    st.session_state.route_points = [pt for pt in st.session_state.route_points if pt[0] != "end"] + ends
            elif mode == "end":
                st.session_state.route_points = [pt for pt in st.session_state.route_points if pt[0] != "end"]
                st.session_state.route_points.append(("end", lat, lon))
                st.session_state.end = [lat, lon]
            elif mode == "waypoint":
                st.session_state.route_points.append(("wp", lat, lon))
            else:
                st.warning("Please choose Start Point / Waypoint / End Point in the sidebar before clicking the map.")

    # -----------------------
    # Generate route: create up/down style intermediate points between each selected marker
    # then apply light land-avoidance between each pair of consecutive vertices
    # -----------------------
    if generate:
        types = [pt[0] for pt in st.session_state.route_points]
        if ("start" in types) and ("end" in types) and len(st.session_state.route_points) >= 2:
            # build base ordered markers list
            marker_route = [(float(p[1]), float(p[2])) for p in st.session_state.route_points]

            # parameters: how many interpolated control points between each marker
            num_waypoints_between = 5  # user-snippet style: 5
            generated_vertices = []

            for idx in range(len(marker_route) - 1):
                a = marker_route[idx]
                b = marker_route[idx + 1]
                # always append start of segment (except for very first append later)
                if idx == 0:
                    generated_vertices.append(a)

                # linear interpolation + random offsets (like your snippet)
                for i in range(1, num_waypoints_between):
                    frac = i / float(num_waypoints_between)
                    lat = a[0] + (b[0] - a[0]) * frac
                    lon = a[1] + (b[1] - a[1]) * frac

                    attempt = 0
                    # scale offsets by segment length: bigger segments get larger offsets
                    seg_km = haversine_km(a[0], a[1], b[0], b[1])
                    # Base offset magnitude: range [-2,2] degrees scaled by distance factor (clamped)
                    scale = min(2.0, max(0.2, seg_km * 0.02))  # ~2% of segment length in degrees, clamped
                    lat_offset = random.uniform(-scale, scale)
                    lon_offset = random.uniform(-scale, scale)
                    new_lat = lat + lat_offset
                    new_lon = lon + lon_offset
                    while not is_water(new_lat, new_lon) and attempt <= 10:
                        # reduce offset gradually if hitting land
                        lat_offset = random.uniform(-scale * 0.6, scale * 0.6)
                        lon_offset = random.uniform(-scale * 0.6, scale * 0.6)
                        new_lat = lat + lat_offset
                        new_lon = lon + lon_offset
                        attempt += 1
                    # if too many attempts, fallback to base point (still will be used)
                    generated_vertices.append((new_lat, new_lon))

                # append endpoint of segment
                generated_vertices.append(b)

            # Now apply light land-avoidance on consecutive generated vertices to fix any crossings
            final_route = [generated_vertices[0]]
            for i in range(len(generated_vertices) - 1):
                s = final_route[-1]
                e = generated_vertices[i + 1]
                # if midpoint water -> keep straight, else run low-depth detour
                mid_lat = (s[0] + e[0]) / 2.0
                mid_lon = (s[1] + e[1]) / 2.0
                if is_water(mid_lat, mid_lon):
                    if (round(final_route[-1][0], 6), round(final_route[-1][1], 6)) != (round(e[0], 6), round(e[1], 6)):
                        final_route.append((float(e[0]), float(e[1])))
                else:
                    pts = build_segment_avoiding_land(s, e, max_depth=4)
                    for p in pts:
                        if (round(final_route[-1][0], 6), round(final_route[-1][1], 6)) != (round(p[0], 6), round(p[1], 6)):
                            final_route.append((float(p[0]), float(p[1])))

            st.session_state.route = final_route

            # sync start/end session entries
            first = next((pt for pt in st.session_state.route_points if pt[0] == "start"), None)
            last = next((pt for pt in reversed(st.session_state.route_points) if pt[0] == "end"), None)
            if first:
                st.session_state.start = [first[1], first[2]]
            if last:
                st.session_state.end = [last[1], last[2]]
        else:
            st.error("You must place at least one Start and one End point (use sidebar to select mode then click the map).")
            st.session_state.route = None

        # -----------------------
        # Dense cluster generation (based on your snippet but with a safety cap)
        # -----------------------
        if st.session_state.route:
            clusters = []
            MAX_TOTAL_CLUSTERS = 100000  # safety cap - increase if you want more but careful
            total_count = 0

            for i in range(len(st.session_state.route) - 1):
                lat1, lon1 = st.session_state.route[i]
                lat2, lon2 = st.session_state.route[i + 1]

                # steps similar to your snippet
                for step in range(15):
                    if total_count >= MAX_TOTAL_CLUSTERS:
                        break
                    lat = lat1 + (lat2 - lat1) * step / 20.0
                    lon = lon1 + (lon2 - lon1) * step / 20.0

                    # tight cluster (low dispersion)
                    for _ in range(8):
                        if total_count >= MAX_TOTAL_CLUSTERS:
                            break
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
                        total_count += 1

                    # wider cluster (higher dispersion)
                    for _ in range(10):
                        if total_count >= MAX_TOTAL_CLUSTERS:
                            break
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
                        total_count += 1

                if total_count >= MAX_TOTAL_CLUSTERS:
                    break

            # score clusters using env + distance to route (same weighting as before)
            DIST_CAP_KM = 100.0
            ENV_WEIGHT = 0.7
            DIST_WEIGHT = 0.3

            scored_clusters = []
            for pt in clusters:
                env_total = pt["wave"] + pt["wind"] + pt["current"]  # 0..300
                dkm = distance_to_polyline_km(pt["lat"], pt["lon"], st.session_state.route)
                distance_score = min(300, (dkm / DIST_CAP_KM) * 300)
                final_score = int(max(0, min(300, ENV_WEIGHT * env_total + DIST_WEIGHT * distance_score)))
                pt["distance_km_to_route"] = round(dkm, 2)
                pt["score"] = final_score
                scored_clusters.append(pt)

            st.session_state.clusters = scored_clusters
            st.session_state["route_generated"] = True
            st.session_state["show_res"] = False

            # -----------------------
            # compute voyage metrics & save CSV (same format)
            # -----------------------
            total_distance_km = 0.0
            for i in range(len(st.session_state.route) - 1):
                lat1, lon1 = st.session_state.route[i]
                lat2, lon2 = st.session_state.route[i + 1]
                total_distance_km += haversine_km(lat1, lon1, lat2, lon2)
            total_distance_nm = total_distance_km / 1.852
            hours_needed = total_distance_nm / ship_speed_knots
            etd = datetime.combine(start_date, datetime.min.time())
            eta = etd + timedelta(hours=hours_needed)

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
                    "NUM_WAYPOINTS": len([p for p in st.session_state.route_points if p[0] == "wp"]),
                    "NUM_CLUSTERS": len(st.session_state.clusters),
                    "FEEDBACK_RATING": st.session_state.get("feedback_rating", 3),
                    "FEEDBACK_TEXT": st.session_state.get("feedback_text", "Average: Routine voyage with some manageable issues.")
                }
                try:
                    append_voyage_to_csv(CSV_PATH, voyage_row)
                    st.session_state["voyage_saved"] = True
                except Exception as e:
                    st.error(f"Failed to save voyage: {e}")

    # -----------------------
    # Final map: markers, polyline, clusters
    # -----------------------
    map_container2 = st.container()
    with map_container2:
        m2 = folium.Map(location=[20.5937, 78.9629], zoom_start=5, tiles="CartoDB positron")

        # ordered markers
        for idx, item in enumerate(st.session_state.route_points):
            typ, lat, lon = item[0], item[1], item[2]
            if typ == "start":
                folium.Marker([lat, lon], popup=f"Start (pos {idx + 1})", icon=folium.Icon(color="green")).add_to(m2)
            elif typ == "end":
                folium.Marker([lat, lon], popup=f"End (pos {idx + 1})", icon=folium.Icon(color="red")).add_to(m2)
            else:
                folium.Marker([lat, lon], popup=f"WP {idx + 1}", icon=folium.Icon(color="blue")).add_to(m2)

        # route polyline
        if st.session_state.route:
            folium.PolyLine(st.session_state.route, color="blue", weight=3).add_to(m2)

        # clusters
        if st.session_state.clusters:
            for point in st.session_state.clusters:
                total_env = point["wave"] + point["wind"] + point["current"]
                tooltip_text = (f"Wave: {point['wave']} | Wind: {point['wind']} | Current: {point['current']} "
                                f"(Env: {total_env}/300) | Dist to route: {point['distance_km_to_route']} km | Score: {point['score']}/300")
                if point["score"] <= 100:
                    color = "green"
                elif point["score"] <= 200:
                    color = "orange"
                else:
                    color = "red"
                radius = 2 + (point["score"] / 120.0)
                folium.CircleMarker(location=[point["lat"], point["lon"]],
                                    radius=radius, color=color, fill=True, fill_opacity=0.7,
                                    tooltip=tooltip_text).add_to(m2)

        st_folium(m2, width="100%", height=600, key="final_map")

    # -----------------------
    # Buttons:Resistance curve,DP Feedback
    # -----------------------
    if st.session_state.get("route_generated", False):
        col_a, col_b, col_c = st.columns([1, 1, 1])

        with col_a:
            if st.button("Show Resistance Curve", key="show_res_btn"):
                st.session_state["show_res"] = True
        with col_b:
            if st.button("Display Parameters", key="display_params_btn"):
                st.session_state["display_params"] = True
        with col_c:
            if st.button("Feedback", key="feedback_btn"):
                st.session_state["open_feedback"] = True

    # -----------------------
    # Resistance plot (unchanged logic from your earlier code)
    # -----------------------
    if st.session_state.get("show_res", False):
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
            fig, ax = plt.subplots(figsize=(12, 6))
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

    # -----------------------
    # Feedback UI (unchanged)
    # -----------------------
    if st.session_state.get("open_feedback", False):
        with st.expander("Voyage Feedback", expanded=True):
            st.write("Please provide your feedback for this voyage. If you close without submitting, default rating/text will remain.")
            with st.form("feedback_form"):
                rating = st.slider("Rating (1-5)", min_value=1, max_value=5, value=st.session_state.get('feedback_rating', 3))
                text = st.text_area("Feedback text", value=st.session_state.get('feedback_text', "Average: Routine voyage with some manageable issues."), height=150)
                submitted = st.form_submit_button("Submit Feedback")
                if submitted:
                    st.session_state['feedback_rating'] = int(rating)
                    st.session_state['feedback_text'] = text.strip() if text.strip() else "Average: Routine voyage with some manageable issues."
                    if st.session_state.get('voyage_timestamp'):
                        try:
                            success = update_feedback_in_csv(CSV_PATH, st.session_state['voyage_timestamp'], st.session_state['feedback_rating'], st.session_state['feedback_text'])
                            if success:
                                st.success("Thank you — your feedback has been saved.")
                        except Exception as e:
                            st.error(f"Failed to update feedback: {e}")
                    st.session_state['open_feedback'] = False

    
    if st.session_state.get("display_params", False):
        html_path = Path("hotspots_opacity_map_fixed.html").resolve()
        if html_path.exists():
            # Open HTML file in a new browser tab
            webbrowser.open_new_tab(f"file://{html_path}")
            st.success("✅ Map opened in a new browser tab!")
        else:
            st.error("❌ The HTML file was not found. Please make sure it's in the same directory.")
    else:
        st.info("***The Route has been Generated***")

    # -----------------------
    # Sidebar summary (unchanged)
    # -----------------------
    if st.session_state.route:
        total_distance_km = 0.0
        for i in range(len(st.session_state.route) - 1):
            lat1, lon1 = st.session_state.route[i]
            lat2, lon2 = st.session_state.route[i + 1]
            total_distance_km += haversine_km(lat1, lon1, lat2, lon2)
        total_distance_nm = total_distance_km / 1.852
        hours_needed = total_distance_nm / ship_speed_knots
        etd = datetime.combine(start_date, datetime.min.time())
        eta = etd + timedelta(hours=hours_needed)

        avg_score = None
        worst_score = None
        if st.session_state.clusters:
            scores = [c["score"] for c in st.session_state.clusters]
            avg_score = sum(scores) / len(scores)
            worst_score = max(scores)

        st.sidebar.markdown("### Voyage Info")
        st.sidebar.write(f"**Ship Type:** {ship_type}")
        st.sidebar.write(f"**Distance:** {total_distance_nm:.1f} NM ({total_distance_km:.1f} km)")
        st.sidebar.write(f"**ETD:** {etd.strftime('%Y-%m-%d %H:%M')}")
        st.sidebar.write(f"**ETA:** {eta.strftime('%Y-%m-%d %H:%M')}")
        st.sidebar.write(f"**Duration:** {hours_needed:.1f} hrs")
        st.sidebar.write(f"**Waypoints (selected):** {len([p for p in st.session_state.route_points if p[0] == 'wp'])}")
        st.sidebar.write(f"**Clusters generated:** {len(st.session_state.clusters)}")
        if avg_score is not None:
            st.sidebar.write(f"**Avg cluster score:** {avg_score:.1f}/300")
            st.sidebar.write(f"**Worst cluster score:** {worst_score}/300")

# End of NEW TRAJECTORY page


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
