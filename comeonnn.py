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
    </style>
""", unsafe_allow_html=True)

# ---- FILE PATHS ----
splash_video = "YouCut_20251028_153909796.mp4"  # first video
loading_video = "IVROT_20251028_150435_0000-vmake.mp4"  # second video


def embed_video(file_path, loop=False):
    """Reads a video file and embeds it as a base64 HTML video with no controls."""
    with open(file_path, "rb") as f:
        video_bytes = f.read()
    base64_video = base64.b64encode(video_bytes).decode("utf-8")
    loop_attr = "loop" if loop else ""
    video_html = f"""
        <video autoplay {loop_attr} muted playsinline>
            <source src="data:video/mp4;base64,{base64_video}" type="video/mp4">
        </video>
    """
    st.markdown(video_html, unsafe_allow_html=True)


# ---- APP LOGIC ----

# Splash screen (only once per session)
if "splash_played" not in st.session_state:
    st.session_state.splash_played = True
    embed_video(splash_video, loop=False)
    time.sleep(10) # Adjust based on video duration
    st.rerun()

# Main app interface
st.title("🚀 My Streamlit App")

if st.button("Run Task"):
    # Play looping loading video while processing
    embed_video(loading_video, loop=True)

    with st.spinner("Processing..."):
        time.sleep(5)  # Simulated task

    st.success("✅ Task Complete!")

else:
    st.info("Click the button above to start a task.")
