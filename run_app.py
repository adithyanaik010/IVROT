# run.py
import subprocess
import sys
import time
import webbrowser
import tkinter as tk
from PIL import Image, ImageTk
import os

# ----------------- CONFIG -----------------
SCRIPT = "final.py"
PORT = 8502
LOGO_PATH = r"C:\Users\P ADITHYA M NAIK\Desktop\IVROT\Please wait....png"
SPLASH_DURATION = 5000  # milliseconds

# ----------------- SPLASH SCREEN -----------------
root = tk.Tk()
root.overrideredirect(True)
root.attributes('-topmost', True)

# Screen dimensions
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

# Load image
if os.path.exists(LOGO_PATH):
    img = Image.open(LOGO_PATH)
    try:
        img = img.resize((screen_width, screen_height), resample=Image.Resampling.LANCZOS)
    except AttributeError:
        img = img.resize((screen_width, screen_height), resample=Image.LANCZOS)
    photo = ImageTk.PhotoImage(img)
    label = tk.Label(root, image=photo)
    label.pack()
else:
    label = tk.Label(root, text="Please wait...", font=("Arial", 50))
    label.pack(expand=True)

root.after(SPLASH_DURATION, root.destroy)
root.mainloop()

# ----------------- LAUNCH STREAMLIT -----------------
cmd = [
    sys.executable,
    "-m",
    "streamlit",
    "run",
    SCRIPT,
    "--server.port", str(PORT),
    "--server.headless", "true"   # Prevent Streamlit from opening a browser
]

if sys.platform.startswith("win"):
    DETACHED_PROCESS = 0x00000008
    subprocess.Popen(
        cmd,
        creationflags=DETACHED_PROCESS,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
else:
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# Wait for Streamlit server to start
time.sleep(3)

# ----------------- OPEN BROWSER -----------------
try:
    webbrowser.open(f"http://localhost:{PORT}")
except:
    print(f"Please open your browser and go to http://localhost:{PORT}")

print(f"Streamlit launched on http://localhost:{PORT}")
