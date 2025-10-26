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

# ------------------ CUSTOM CSS ------------------
st.markdown("""
<style>
header { 
    height: 5px;
    padding: 0px 0px;
}
.block-container { padding-top: 1px; }

/* Custom panel under header */
.new-trajectory-panel {
    position: relative;
    z-index: 900;
    background-color: rgba(255,255,255,0.95);
    border-radius: 12px;
    padding: 16px;
    margin-top: 300px; /* push below header */
    width: 300px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.12);
}

/* Fix panel header */
.new-trajectory-panel h3 {
    margin-top: 0;
}

/* Floating panel inside main content */
@media (max-width:800px){
    .new-trajectory-panel { width: 90%; margin-left:auto; margin-right:auto; margin-top:220px; }
}
</style>
""", unsafe_allow_html=True)

# ------------------ APP ------------------
st.title("IVROT")
st.button("Button 1")

# ---------- Paths ----------
BG_IMAGE = r"C:\Users\P ADITHYA M NAIK\Desktop\IVROT\Navigation_2.jpg"
LOGO_LIGHT_PNG = Path(r"C:\Users\P ADITHYA M NAIK\Desktop\IVROT\IVROT-removebg-preview.png")
LOGO_DARK_PNG = Path(r"C:\Users\P ADITHYA M NAIK\Desktop\IVROT\DARK-removebg-preview.png")
LOGO_LIGHT_JPG = LOGO_LIGHT_PNG.with_suffix(".jpg")
LOGO_DARK_JPG = LOGO_DARK_PNG.with_suffix(".jpg")
ICO_PATH = Path(r"C:\Users\P ADITHYA M NAIK\Desktop\IVROT\IVROT.ico")
CSV_PATH = r"C:\Users\P ADITHYA M NAIK\Desktop\IVROT\voyages.csv"

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

st.set_page_config(page_title="IVROT", layout="wide", page_icon=str(ICO_PATH) if ICO_PATH.exists() else None)

# ---------- Session state ----------
if "theme_flag" not in st.session_state: st.session_state["theme_flag"] = 0
if "nav" not in st.session_state: st.session_state["nav"] = "HOME"

def toggle_theme_flag():
    st.session_state["theme_flag"] = 1 if st.session_state["theme_flag"] == 0 else 0

# ---------- HEADER ----------
logo_uri = logo_light_uri if st.session_state["theme_flag"] == 0 else logo_dark_uri
st.markdown(f'<div style="position:fixed; top:60px; left:0; right:0; z-index:999; background:white; padding:10px 50px; box-shadow:0 8px 24px rgba(0,0,0,0.12);"><img src="{logo_uri}" style="height:100px;"/><span style="font-weight:800; font-size:30px; margin-left:16px;">IVROT</span></div>', unsafe_allow_html=True)

# ---------- PAGE NAVIGATION ----------
c1,c2,c3 = st.columns([1,4,1])
with c2:
    col_nav1,col_nav2,col_nav3 = st.columns([1,1,1])
    with col_nav1:
        if st.button("HOME"): st.session_state["nav"] = "HOME"
    with col_nav2:
        if st.button("NEW TRAJECTORY"): st.session_state["nav"] = "NEW TRAJECTORY"
    with col_nav3:
        if st.button("HISTORY"): st.session_state["nav"] = "HISTORY"
with c3:
    icon = "☼" if st.session_state["theme_flag"]==0 else "☽"
    if st.button(icon): toggle_theme_flag()

# ---------- PAGE CONTENT ----------
st.markdown("<div style='height:180px'></div>", unsafe_allow_html=True)

# ---------- NEW TRAJECTORY ----------
if st.session_state["nav"]=="NEW TRAJECTORY":
    st.header("New Trajectory")

    if "start" not in st.session_state: st.session_state.start=[None,None]
    if "end" not in st.session_state: st.session_state.end=[None,None]
    if "route" not in st.session_state: st.session_state.route=None
    if "clusters" not in st.session_state: st.session_state.clusters=[]
    if "land" not in st.session_state: st.session_state.land=gpd.read_file(r"C:\Users\P ADITHYA M NAIK\Desktop\IVROT\ne_10m_land.shp")

    def is_water(lat,lon):
        point = Point(lon,lat)
        return not st.session_state.land.contains(point).any()

    # ---------- Custom panel under header ----------
    st.markdown('<div class="new-trajectory-panel">', unsafe_allow_html=True)
    st.markdown("### Route Points & Ship")

    start_lat = st.number_input("Start Latitude", value=st.session_state.start[0] or 0.0)
    start_lon = st.number_input("Start Longitude", value=st.session_state.start[1] or 0.0)
    end_lat = st.number_input("End Latitude", value=st.session_state.end[0] or 0.0)
    end_lon = st.number_input("End Longitude", value=st.session_state.end[1] or 0.0)

    wave = st.slider("WAVE",0,100,50)
    wind = st.slider("WIND",0,100,50)
    current = st.slider("CURRENT",0,100,50)

    ship_type = st.selectbox("Select Ship Type", ["Cargo Vessel","Oil Tanker","Container Ship","Fishing Vessel","Passenger Ship"])
    ship_speed_knots = st.slider("Ship Speed (knots)",5,30,15)
    start_date = st.date_input("Select ETD Date", value=date.today())

    reset = st.button("Reset Trajectory")
    generate = st.button("Generate Route")
    st.markdown('</div>', unsafe_allow_html=True)

# ---------- Rest of your route generation, map, clusters, and ETA code goes here ----------
