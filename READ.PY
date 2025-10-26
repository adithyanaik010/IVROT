import streamlit as st
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io

# -------------------- CONFIG --------------------
st.set_page_config(
    page_title="IVROT - Intelligent Voyage Route Optimizer",
    page_icon="IVROT.ico",
    layout="wide"
)

# Paths
BASE_DIR = Path(__file__).parent
LOGO_PATH = BASE_DIR / "IVROT.ico"
BG_PATH = BASE_DIR / "Navigation_2.jpg"
VOYAGE_CSV = BASE_DIR / "voyages.csv"

# -------------------- CUSTOM CSS --------------------
def set_background():
    if BG_PATH.exists():
        bg_str = f"""
        <style>
        [data-testid="stAppViewContainer"] {{
            background: linear-gradient(rgba(255,255,255,0.65), rgba(255,255,255,0.65)),
                        url("file://{BG_PATH}") no-repeat center center fixed;
            background-size: cover;
        }}
        [data-testid="stHeader"] {{
            background: rgba(0,0,0,0);
        }}
        .header-bar {{
            display:flex;
            align-items:center;
            justify-content:space-between;
            padding:0.5rem 1.2rem;
            background-color:rgba(255,255,255,0.8);
            border-radius:16px;
            margin-bottom:0.8rem;
            box-shadow:0 0 10px rgba(0,0,0,0.15);
        }}
        .header-left {{
            display:flex;
            align-items:center;
            gap:0.8rem;
        }}
        .header-left img {{
            height:40px;
            width:40px;
            border-radius:8px;
        }}
        .header-title {{
            font-size:1.4rem;
            font-weight:700;
            color:#222;
        }}
        .theme-toggle {{
            cursor:pointer;
            font-size:1.2rem;
            padding:0.3rem 0.7rem;
            border-radius:12px;
            background-color:#f0f0f0;
            transition:all 0.3s;
        }}
        .theme-toggle:hover {{
            background-color:#e0e0e0;
        }}
        </style>
        """
        st.markdown(bg_str, unsafe_allow_html=True)

set_background()

# -------------------- HEADER --------------------
col1, col2, col3 = st.columns([1,6,1])
with col1:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), use_column_width=True)
with col2:
    st.markdown(
        "<div class='header-bar'><div class='header-left'>"
        f"<img src='file://{LOGO_PATH}' alt='logo'><div class='header-title'>IVROT - Intelligent Voyage Route Optimizer</div>"
        "</div></div>", unsafe_allow_html=True
    )

st.markdown("---")

# -------------------- PAGE SELECTION --------------------
page = st.sidebar.radio("📘 Navigation", [
    "New Trajectory",
    "Voyage History",
    "Resistance Plots",
    "Feedback"
])

# -------------------- SIMULATED DATA & HELPERS --------------------
def generate_cluster_data(n_clusters=10, n_points=200):
    rng = np.random.default_rng(42)
    clusters = []
    for c in range(n_clusters):
        center = rng.uniform(-90, 90, size=2)
        lat, lon = center
        pts = np.clip(np.column_stack([
            lat + rng.normal(0, 5, n_points),
            lon + rng.normal(0, 5, n_points)
        ]), -90, 90)
        weights = rng.integers(30, 100, size=(n_points, 3))
        clusters.append(pd.DataFrame({
            "Latitude": pts[:, 0],
            "Longitude": pts[:, 1],
            "Wave": weights[:, 0],
            "Wind": weights[:, 1],
            "Current": weights[:, 2]
        }))
    return clusters

def calculate_route_score(df):
    total = df[["Wave", "Wind", "Current"]].sum(axis=1)
    return total.mean()

def plot_resistance_chart():
    fig, ax = plt.subplots()
    speed = np.linspace(5, 30, 10)
    resistance = 0.05 * speed**2 + np.random.rand(10)*5
    ax.plot(speed, resistance, marker='o')
    ax.set_xlabel("Speed (knots)")
    ax.set_ylabel("Resistance (kN)")
    ax.set_title("Sample Ship Resistance Curve")
    st.pyplot(fig)

# -------------------- PAGE 1: NEW TRAJECTORY --------------------
if page == "New Trajectory":
    st.subheader("🗺️ Generate New Voyage Trajectory")

    colA, colB = st.columns(2)
    with colA:
        n_clusters = st.slider("Number of clusters", 3, 20, 10)
    with colB:
        n_points = st.slider("Points per cluster", 50, 300, 150)

    if st.button("Generate Trajectory"):
        clusters = generate_cluster_data(n_clusters, n_points)
        st.session_state["clusters"] = clusters
        st.success("Trajectory generated successfully!")

    if "clusters" in st.session_state:
        clusters = st.session_state["clusters"]
        st.write(f"Generated {len(clusters)} clusters.")
        scores = [calculate_route_score(df) for df in clusters]
        best_idx = int(np.argmin(scores))
        st.info(f"Optimal route cluster: {best_idx+1} with avg weight {scores[best_idx]:.2f}")

        fig, ax = plt.subplots()
        for i, df in enumerate(clusters):
            color = "blue" if i == best_idx else "gray"
            ax.scatter(df["Longitude"], df["Latitude"], s=10, c=color, alpha=0.6)
        ax.set_title("Optimized Voyage Trajectory (lowest total resistance)")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        st.pyplot(fig)

# -------------------- PAGE 2: VOYAGE HISTORY --------------------
elif page == "Voyage History":
    st.subheader("🗃️ Voyage History")

    if VOYAGE_CSV.exists():
        df = pd.read_csv(VOYAGE_CSV)
        st.dataframe(df)
        if st.button("Clear History"):
            VOYAGE_CSV.unlink()
            st.warning("Voyage history cleared.")
    else:
        st.info("No voyage records found yet.")

# -------------------- PAGE 3: RESISTANCE PLOTS --------------------
elif page == "Resistance Plots":
    st.subheader("📊 Resistance Curve Simulation")
    plot_resistance_chart()

# -------------------- PAGE 4: FEEDBACK --------------------
elif page == "Feedback":
    st.subheader("💬 Captain's Feedback")
    name = st.text_input("Captain Name")
    msg = st.text_area("Feedback / Observations")
    if st.button("Submit Feedback"):
        if name and msg:
            st.success("Feedback received. Thank you, Captain!")
        else:
            st.warning("Please fill both fields before submitting.")
