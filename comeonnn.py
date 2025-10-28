import streamlit as st
import time

# Set up page layout
st.set_page_config(
    page_title="App with Video Loading Screens",
    layout="wide",
    page_icon="🎬",
)

# Inject CSS to center everything and make background white
st.markdown("""
    <style>
        body {
            background-color: white;
        }
        .block-container {
            padding-top: 0;
            padding-bottom: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        video {
            border-radius: 10px;
            max-width: 100vw;
            height: 100vh;
            object-fit: contain;
        }
        .stApp {
            background-color: white;
        }
    </style>
""", unsafe_allow_html=True)

# Define file paths
intro_video = "1761651966208.mp4"  # plays once at app start
loading_video = "IVROT_20251028_150435_0000-vmake.mp4"  # loops while processing

# --- Show splash/loading screen on app startup ---
if "splash_played" not in st.session_state:
    st.session_state.splash_played = True

    # Display first loading video (splash)
    video_bytes = open(intro_video, 'rb').read()
    st.video(video_bytes)

    # Wait for the splash video to finish (you can adjust the time)
    time.sleep(3)  # Adjust this duration to match your video length

    st.rerun()

# --- Main App Interface ---
st.title("🚀 My Streamlit App")

task = st.button("Run Task")

if task:
    with st.spinner("Processing..."):
        st.markdown("<h3 style='text-align:center;'>Processing, please wait...</h3>", unsafe_allow_html=True)

        # Display looping video while working
        video_file = open(loading_video, 'rb')
        video_bytes = video_file.read()

        st.video(video_bytes, start_time=0)

        # Simulate a long-running task
        time.sleep(6)

        st.success("✅ Task complete!")
else:
    st.info("Click the button above to start a task.")
