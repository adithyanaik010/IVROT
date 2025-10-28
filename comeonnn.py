import streamlit as st

# Set page configuration
st.set_page_config(
    page_title="Video Player",
    layout="wide",
    page_icon="🎥",
)

# Add custom CSS for centering and white background
st.markdown("""
    <style>
        body {
            background-color: white;
        }
        .block-container {
            padding-top: 0rem;
            padding-bottom: 0rem;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        video {
            border-radius: 10px;
            box-shadow: 0px 0px 10px rgba(0,0,0,0.2);
            max-width: 90vw;
            height: auto;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center;'>🎬 Video Player</h1>", unsafe_allow_html=True)

# Define video file paths (make sure they are in the same directory as this script)
video_files = [
    "1761651966208.mp4",
    "IVROT_20251028_150435_0000-vmake.mp4"
]

# Display videos centered
for video_file in video_files:
    st.video(video_file)
    st.markdown("<br>", unsafe_allow_html=True)
