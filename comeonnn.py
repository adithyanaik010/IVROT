import streamlit as st
import time

# Page config
st.set_page_config(
    page_title="App with Controlled Videos",
    layout="wide",
    page_icon="🎥",
)

# White background and centered layout
st.markdown("""
    <style>
        body, .stApp {
            background-color: white;
            margin: 0;
            padding: 0;
            overflow: hidden;
        }
        .block-container {
            padding: 0;
            margin: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }
        video {
            width: 100vw;
            height: 100vh;
            object-fit: contain;
            background-color: white;
        }
    </style>
""", unsafe_allow_html=True)

# File paths
splash_video = "1761651966208.mp4"  # first video (startup)
loading_video = "IVROT_20251028_150435_0000-vmake.mp4"  # second video (while processing)


def play_video(file, loop=False):
    """Embed a video that auto-plays and cannot be controlled by the user."""
    loop_attr = "loop" if loop else ""
    video_html = f"""
        <video autoplay {loop_attr} muted playsinline>
            <source src="{file}" type="video/mp4">
        </video>
    """
    st.markdown(video_html, unsafe_allow_html=True)


# --- SPLASH SCREEN (plays once on app start) ---
if "splash_played" not in st.session_state:
    st.session_state.splash_played = True
    play_video(splash_video, loop=False)
    time.sleep(3)  # wait for splash duration (adjust as per your video length)
    st.rerun()

# --- MAIN APP UI ---
st.title("🚀 My Streamlit App")

if st.button("Run Task"):
    # Show looping video while task is running
    play_video(loading_video, loop=True)
    with st.spinner("Processing..."):
        time.sleep(5)  # simulate work
    st.success("✅ Task Complete!")
else:
    st.info("Click the button above to start a task.")
