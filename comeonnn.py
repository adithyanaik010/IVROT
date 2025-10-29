import streamlit as st
import time
import base64
from pathlib import Path

# -------------------------------
# CONFIGURATION
# -------------------------------
INTRO_VIDEO = "YouCut_20251028_153909796.mp4"
LOOP_VIDEO = "IVROT_20251028_150435_0000-vmake.mp4"

st.set_page_config(page_title="IVROT", layout="wide")

# -------------------------------
# UTILITY FUNCTIONS
# -------------------------------

def play_video(video_path, autoplay=True, loop=False):
    """Embed a video file into Streamlit using HTML for more control."""
    video_bytes = Path(video_path).read_bytes()
    b64 = base64.b64encode(video_bytes).decode()
    loop_attr = "loop" if loop else ""
    auto_attr = "autoplay" if autoplay else ""
    html = f"""
    <video {auto_attr} {loop_attr} muted playsinline style="width:100%; height:100%; object-fit:cover;">
        <source src="data:video/mp4;base64,{b64}" type="video/mp4">
    </video>
    """
    st.markdown(html, unsafe_allow_html=True)


def show_intro():
    """Play intro video once."""
    st.session_state.intro_played = True
    play_video(INTRO_VIDEO, autoplay=True, loop=False)
    time.sleep(3)  # Adjust to your video duration


def show_loading():
    """Show looping loading video."""
    placeholder = st.empty()
    with placeholder.container():
        play_video(LOOP_VIDEO, autoplay=True, loop=True)
    return placeholder


def simulate_long_task(seconds=5):
    """Example of background computation."""
    time.sleep(seconds)


# -------------------------------
# MAIN APP
# -------------------------------

# Initialize state
if "intro_played" not in st.session_state:
    st.session_state.intro_played = False

# If intro hasn't been played, show it and stop here
if not st.session_state.intro_played:
    show_intro()
    st.rerun()  # reload to show the main UI next

# -------------------------------
# MAIN UI AFTER INTRO
# -------------------------------

st.title("🌊 IVROT System Home Page")

st.markdown("This is your main app interface after the intro video.")

# Example button to simulate heavy background work
if st.button("Start Heavy Task"):
    loading_placeholder = show_loading()  # show loop video
    simulate_long_task(6)  # simulate heavy computation
    loading_placeholder.empty()  # remove video once done
    st.success("✅ Background task completed successfully!")

st.write("You can continue using your app here...")
