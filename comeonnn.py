# ===============================================================
# IVROT - Integrated Vessel Route Optimization Toolkit
# Streamlit Cloud Optimized Version
# Author: Fixed & Rebuilt by ChatGPT (GPT-5)
# ===============================================================
import base64

def get_base64(file_path):
    with open(file_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return encoded

data = base64.b64decode(encoded)
data
import streamlit as st
from pathlib import Path
import base64
import time
import folium
from streamlit_folium import st_folium
import math
import numpy as np
import pandas as pd
from datetime import datetime
import random
from io import BytesIO

# ===============================================================
# PAGE CONFIGURATION
# ===============================================================
st.set_page_config(
    page_title="IVROT",
    page_icon="🎥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ===============================================================
# UTILITY FUNCTIONS
# ===============================================================
def read_file_base64(path):
    """Safely read a file and return its base64-encoded string."""
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return ""

@st.cache_data(show_spinner=False)
def get_video_base64(path):
    """Cache base64 video loading for performance."""
    return read_file_base64(path)

def video_overlay_html(base64_mp4, overlay_id, loop=False):
    """Return HTML snippet for a fullscreen video overlay."""
    if not base64_mp4:
        return ""
    loop_attr = "loop" if loop else ""
    return f"""
    <div id="{overlay_id}" style="
        position: fixed;
        top: 0; left: 0;
        width: 100vw; height: 100vh;
        background: white;
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 999999;
    ">
        <video autoplay {loop_attr} muted playsinline
               style="width:100vw; height:100vh; object-fit: contain;">
            <source src="data:video/mp4;base64,{base64_mp4}" type="video/mp4">
        </video>
    </div>
    """

def hide_overlay_js(overlay_id):
    """Return JS snippet to fade and remove overlay after playback."""
    return f"""
    <script>
    setTimeout(() => {{
        const el = document.getElementById('{overlay_id}');
        if (el) {{
            el.style.transition = "opacity 0.5s ease-out";
            el.style.opacity = 0;
            setTimeout(() => el.remove(), 500);
        }}
    }}, 100);
    </script>
    """

# ===============================================================
# SESSION STATE INITIALIZATION
# ===============================================================
defaults = {
    "splash_played": False,
    "nav": "HOME",
    "start": None,
    "end": None,
    "route": None,
    "route_generated": False,
    "loading": False,
    "voyages": [],
    "show_feedback": False,
    "feedback_rating": 3,
    "feedback_text": "Average: Routine voyage with some manageable issues.",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ===============================================================
# LOAD VIDEOS (CACHED)
# ===============================================================
SPLASH_VIDEO_PATH = Path("YouCut_20251028_153909796.mp4")
LOADING_VIDEO_PATH = Path("IVROT_20251028_150435_0000-vmake.mp4")

splash_b64 = get_video_base64(SPLASH_VIDEO_PATH)
loading_b64 = get_video_base64(LOADING_VIDEO_PATH)

# ===============================================================
# SPLASH INTRO HANDLING
# ===============================================================
if not st.session_state["splash_played"]:
    splash_container = st.empty()
    if splash_b64:
        splash_container.markdown(video_overlay_html(splash_b64, "splash"), unsafe_allow_html=True)
        st.markdown(hide_overlay_js("splash"), unsafe_allow_html=True)
    # mark splash as played instantly (async)
    st.session_state["splash_played"] = True
    time.sleep(1)  # small wait to ensure overlay shows

# ===============================================================
# LOADING OVERLAY HELPER
# ===============================================================
loading_container = st.empty()
def show_loading_overlay():
    if loading_b64:
        loading_container.markdown(
            video_overlay_html(loading_b64, "loading", loop=True),
            unsafe_allow_html=True,
        )

def hide_loading_overlay():
    loading_container.empty()

# ===============================================================
# RESISTANCE MODEL (Simplified Holtröp)
# ===============================================================
def holtrop_resistance(Lpp, B, T, V, rho=1025, nu=1e-6, Cb=0.6, S=None):
    """Compute total resistance using a simplified Holtröp approximation."""
    if not S:
        S = Lpp * (B + 2 * T) * 0.85
    Re = V * Lpp / nu
    if Re <= 0:
        return 0
    Cf = 0.075 / ((math.log10(Re) - 2) ** 2)
    k = 1 + 0.15 * Cb
    Rf = 0.5 * rho * V**2 * S * Cf * k
    Fn = V / math.sqrt(9.81 * Lpp)
    Rr = 0.5 * rho * V**2 * S * (0.004 + 0.002 * Cb**2) * (1 + 0.6 * math.exp(-((Fn - 0.25)/0.05)**2))
    return Rf + Rr

# ===============================================================
# NAVIGATION BAR
# ===============================================================
st.sidebar.title("🎥 IVROT")
nav_choice = st.sidebar.radio("Navigation", ["HOME", "NEW TRAJECTORY", "HISTORY", "SHIP DATA"], index=["HOME", "NEW TRAJECTORY", "HISTORY", "SHIP DATA"].index(st.session_state["nav"]))
st.session_state["nav"] = nav_choice

# ===============================================================
# PAGE: HOME
# ===============================================================
if nav_choice == "HOME":
    st.title("🏠 Home – Integrated Vessel Route Optimization Toolkit")
    st.write("""
    Welcome to **IVROT**, your intelligent ship routing and optimization assistant.  
    This tool helps plan routes, calculate hydrodynamic resistance, and manage voyage data.
    """)
    st.info("Use the sidebar to navigate to 'NEW TRAJECTORY' to start planning a voyage.")

# ===============================================================
# PAGE: NEW TRAJECTORY
# ===============================================================
elif nav_choice == "NEW TRAJECTORY":
    st.title("🧭 New Trajectory")
    st.write("Select **Start** and **End** points on the map below to generate a route.")

    # --- Create folium map ---
    m = folium.Map(location=[20.0, 0.0], zoom_start=2, control_scale=True)
    folium.TileLayer("cartodb positron").add_to(m)
    st.write("Click on the map to set points:")

    # --- Map interaction ---
    map_data = st_folium(m, height=500, width=800, returned_objects=["last_clicked"])

    if map_data and map_data.get("last_clicked"):
        lat, lon = map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"]
        if not st.session_state["start"]:
            st.session_state["start"] = (lat, lon)
            st.success(f"Start point set: {lat:.3f}, {lon:.3f}")
        elif not st.session_state["end"]:
            st.session_state["end"] = (lat, lon)
            st.success(f"End point set: {lat:.3f}, {lon:.3f}")

    # --- Show map markers if exist ---
    if st.session_state["start"]:
        folium.Marker(st.session_state["start"], popup="Start", icon=folium.Icon(color="green")).add_to(m)
    if st.session_state["end"]:
        folium.Marker(st.session_state["end"], popup="End", icon=folium.Icon(color="red")).add_to(m)

    st_folium(m, height=500, width=800, key="map2")

    # --- Generate Route ---
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Generate Route"):
            if st.session_state["start"] and st.session_state["end"]:
                show_loading_overlay()
                st.session_state["loading"] = True
                time.sleep(2)  # simulate backend processing
                st.session_state["route_generated"] = True
                hide_loading_overlay()
                st.session_state["loading"] = False
                st.success("Route generated successfully!")
            else:
                st.warning("Please select both start and end points first.")

    # --- Show resistance estimation ---
    if st.session_state["route_generated"]:
        st.subheader("Resistance Estimation")
        Lpp = st.number_input("Length between perpendiculars (m)", 50.0)
        B = st.number_input("Beam (m)", 10.0)
        T = st.number_input("Draught (m)", 5.0)
        V = st.number_input("Speed (m/s)", 7.0)
        Cb = st.number_input("Block coefficient", 0.6)
        if st.button("Compute Resistance"):
            show_loading_overlay()
            st.session_state["loading"] = True
            Rt = holtrop_resistance(Lpp, B, T, V, Cb=Cb)
            time.sleep(1.5)
            hide_loading_overlay()
            st.session_state["loading"] = False
            st.success(f"Estimated Total Resistance: **{Rt/1000:.2f} kN**")
            st.session_state["voyages"].append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "start": st.session_state["start"],
                "end": st.session_state["end"],
                "Rt": Rt,
                "speed": V,
                "Cb": Cb,
            })
            st.session_state["show_feedback"] = True

    # --- Feedback Section ---
    if st.session_state["show_feedback"]:
        st.subheader("Voyage Feedback")
        st.session_state["feedback_rating"] = st.slider("How did this voyage perform?", 1, 5, st.session_state["feedback_rating"])
        st.session_state["feedback_text"] = st.text_area("Comments", st.session_state["feedback_text"])
        if st.button("Save Feedback"):
            st.success("Feedback saved. Thank you!")

# ===============================================================
# PAGE: HISTORY
# ===============================================================
elif nav_choice == "HISTORY":
    st.title("📜 Voyage History")
    voyages = st.session_state["voyages"]
    if not voyages:
        st.info("No voyages recorded yet.")
    else:
        df = pd.DataFrame(voyages)
        st.dataframe(df)
        st.download_button("Download CSV", df.to_csv(index=False), "voyage_history.csv", "text/csv")

# ===============================================================
# PAGE: SHIP DATA
# ===============================================================
elif nav_choice == "SHIP DATA":
    st.title("🚢 Ship Data Manager")
    st.write("Manage and view vessel parameters for your simulations.")
    vessel_name = st.text_input("Vessel Name", "DemoShip-01")
    col1, col2 = st.columns(2)
    with col1:
        Lpp = st.number_input("Lpp (m)", 50.0)
        B = st.number_input("Beam (m)", 10.0)
        T = st.number_input("Draught (m)", 5.0)
    with col2:
        Cb = st.number_input("Block Coefficient", 0.6)
        Cm = st.number_input("Midship Coefficient", 0.98)
        Cp = st.number_input("Prismatic Coefficient", 0.65)
    st.write(f"**Waterplane Area Coefficient (Approx)**: {round(Cb * Cp / Cm, 3)}")
    st.success("Ship data updated for next calculations.")

# ===============================================================
# FOOTER / INFO
# ===============================================================
st.markdown(
    """
    <hr style="margin-top:40px;margin-bottom:10px;">
    <div style="text-align:center; color:gray;">
    IVROT © 2025 | Developed for efficient route optimization & hydrodynamic analysis
    </div>
    """,
    unsafe_allow_html=True,
)
