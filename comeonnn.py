import streamlit as st
import base64
import time
from pathlib import Path

# -------------------------------
# CONFIG
# -------------------------------
INTRO_VIDEO = "YouCut_20251028_153909796.mp4"
LOOP_VIDEO = "IVROT_20251028_150435_0000-vmake.mp4"

st.set_page_config(page_title="IVROT", layout="wide")

# -------------------------------
# VIDEO HELPERS
# -------------------------------

def embed_video(video_path, autoplay=True, loop=False, muted=True):
    """Embed MP4 video using raw HTML so autoplay + loop work properly."""
    try:
        video_bytes = Path(video_path).read_bytes()
    except FileNotFoundError:
        st.error(f"❌ Video file not found: {video_path}")
        return

    b64 = base64.b64encode(video_bytes).decode()
    auto = "autoplay" if autoplay else ""
    loop_tag = "loop" if loop else ""
    mute_tag = "muted" if muted else ""
    html_code = f"""
    <div style="position:fixed; top:0; left:0; width:100%; height:100%;
                display:flex; justify-content:center; align-items:center;
                background-color:black; z-index:9999;">
        <video {auto} {loop_tag} {mute_tag} playsinline
               style="width:100%; height:100%; object-fit:cover;">
            <source src="data:video/mp4;base64,{b64}" type="video/mp4">
        </video>
    </div>
    """
    st.markdown(html_code, unsafe_allow_html=True)

# -------------------------------
# INTRO SEQUENCE
# -------------------------------
if "intro_played" not in st.session_state:
    st.session_state.intro_played = False

if not st.session_state.intro_played:
    # Play intro video full-screen
    embed_video(INTRO_VIDEO, autoplay=True, loop=False)
    st.session_state.intro_played = True
    # Wait for video duration (adjust this to your actual video length)
    time.sleep(5)
    st.rerun()

# -------------------------------
# MAIN APP
# -------------------------------
st.title("🌊 IVROT System Home Page")
st.markdown("This is your main app after the intro video.")

# Example button to simulate a heavy process
if st.button("Start Heavy Task"):
    # Show loading animation in foreground
    loading_placeholder = st.empty()
    with loading_placeholder:
        embed_video(LOOP_VIDEO, autoplay=True, loop=True)
    # Simulate a heavy background process
    time.sleep(7)
    # Remove the looping video
    loading_placeholder.empty()
    st.success("✅ Task completed successfully!")

st.write("Continue exploring your app below...")
