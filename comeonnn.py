import streamlit as st
import base64
import time
from pathlib import Path

# -------------------------------
# CONFIG
# -------------------------------
INTRO_VIDEO = "YouCut_20251028_153909796.mp4"  # your intro video file
VIDEO_DURATION = 5  # seconds – adjust to your actual video length

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


# -------------------------------
# MAIN APP LOGIC
# -------------------------------
if "intro_played" not in st.session_state:
    # First time: play intro video
    embed_intro_video(INTRO_VIDEO)
    st.session_state.intro_played = True
    time.sleep(VIDEO_DURATION)  # wait until video finishes
    st.rerun()

# -------------------------------
# MAIN APP CONTENT (AFTER INTRO)
# -------------------------------
st.title("🌊 IVROT System Home Page")
st.write("Welcome! The intro video has played once and won’t repeat until you refresh the browser.")
