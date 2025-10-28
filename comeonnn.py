import streamlit as st
import base64
import time

# ---- PAGE CONFIG ----
st.set_page_config(
    page_title="App with Controlled Videos",
    layout="wide",
    page_icon="🎥",
)

# ---- STYLES ----
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
        /* Overlay for loading video */
        #loading-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: white;
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999;
        }
    </style>
""", unsafe_allow_html=True)

# ---- FILE PATHS ----
splash_video = "YouCut_20251028_153909796.mp4"  # splash
loading_video = "IVROT_20251028_150435_0000-vmake.mp4"  # loading


def embed_video_overlay(file_path, loop=False):
    """Embed video as full-screen overlay with no controls."""
    with open(file_path, "rb") as f:
        video_bytes = f.read()
    base64_video = base64.b64encode(video_bytes).decode("utf-8")
    loop_attr = "loop" if loop else ""
    html = f"""
        <div id="loading-overlay">
            <video autoplay {loop_attr} muted playsinline>
                <source src="data:video/mp4;base64,{base64_video}" type="video/mp4">
            </video>
        </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# ---- APP LOGIC ----

# Splash screen (only once)
if "splash_played" not in st.session_state:
    st.session_state.splash_played = True
    embed_video_overlay(splash_video, loop=False)
    time.sleep(10)  # Adjust to splash video length
    st.rerun()

# Main interface
st.title("🚀 My Streamlit App")

# Simulated background task with loading overlay
if st.button("Run Task"):
    # Show full-screen loading video overlay
    embed_video_overlay(loading_video, loop=True)

    # Simulate background process
    with st.spinner("Processing..."):
        time.sleep(5)  # Replace with your actual long-running code

    # Hide overlay by rerunning app
    st.rerun()

else:
    st.info("Click the button above to start a task.")
