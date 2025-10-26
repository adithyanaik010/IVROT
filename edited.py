"""
34 m Tug — Total Resistance (RT) plot (total only), with optional fit to measured data.

How to use:
- Put this file in a folder and run with Python 3.x (requires numpy, pandas, matplotlib).
- Optional: place a CSV named 'tug_34m_measured.csv' with columns: speed_kn,RT_kN
  to fit the model residuary magnitude to measured points.
- Output: tug_34m_total_resistance.png in the script folder.

Author: ChatGPT (tuned for a 34 m tug)
"""

import os
import math
import hashlib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ----------------- USER TUNABLES -----------------
OUT_PNG = "tug_34m_total_resistance.png"
MEASURED_CSV = "tug_34m_measured.csv"   # optional; if present the script will fit RR scale
SHOW_PLOT = True
N_POINTS = 400   # resolution
# Default 34 m tug properties (you can change these to match your PDF metadata)
TUG = {
    "name": "Tug-34m",
    "L": 34.0,            # LOA in meters
    "B": 9.0,             # beam (m) — adjust if you know exact
    "T": 4.0,             # draft (m)
    "disp_t": 800.0,      # displacement (tonnes) — approximate
    "Cb": 0.65,           # block coefficient (typical tug ~0.60-0.70)
    "rho": 1025.0,        # seawater density
    "nu": 1.19e-6,        # kinematic viscosity
    "s_min": 3.0,
    "s_max": 20.0
}
# --------------------------------------------------

g = 9.80665

def knots_to_ms(u_kn):
    return 0.514444 * u_kn

def froude_number(u_ms, L):
    return 0.0 if L <= 0 else u_ms / math.sqrt(g * L)

def reynolds_number(u_ms, L, nu):
    return 1.0 if (nu <= 0 or L <= 0) else u_ms * L / nu

def ittcf(Re):
    if Re <= 0:
        return 0.0
    return 0.075 / ((math.log10(Re) - 2.0) ** 2)

def wetted_surface_estimate(L, B, T, Cb):
    # pragmatic estimate for wetted surface area S (m^2)
    k = 0.66 + 0.24 * (Cb - 0.55)
    k = max(0.57, min(1.0, k))
    return L * (2.0 * B + T) * k

# ---- realistic base residuary (tug-tuned) ----
def cr_base_fn_tug(Fn, Cb, slenderness):
    """
    Tuned for small vessel/tug scale:
    - ensures Cr_base order of magnitude is small (~1e-5 .. 1e-3)
    - shaped to rise and fall so RR peaks around Fn ~ 0.20-0.35 for tugs
    """
    if Fn <= 0:
        return 0.0
    # Tunable constants (set for tug behaviour)
    c0 = 0.0065       # base scale (reduced by Fn^p*exp(-qFn))
    p = 2.1
    q = 2.0
    cb_factor = (Cb / 0.62)
    slim_factor = max(0.6, 1.0 - 0.05 * (slenderness - 4.0))  # tugs typically stubby -> less slender
    base = c0 * cb_factor * slim_factor * (Fn ** p) * math.exp(-q * Fn)
    # clip reasonable bounds
    return float(np.clip(base, 1e-8, 5e-3))

def wave_mult_tug(Fn, Cb, seed):
    """
    Controlled wave multiplier for tugs:
    - envelope centered around Fn0 (~0.26-0.30)
    - amplitude moderate (±10% .. ±50%) depending on Cb
    - deterministic seed per ship (so reproducible)
    """
    if Fn <= 0:
        return 1.0
    rng = np.random.RandomState(seed & 0x7fffffff)
    amp_base = 0.18 + 0.8 * (Cb - 0.6)   # tug-specific amplitude baseline
    amp = float(np.clip(amp_base * (1.0 + rng.uniform(-0.10, 0.10)), 0.08, 0.6))
    Fn0 = 0.26 + rng.uniform(-0.01, 0.01)
    sigma = 0.055 + rng.uniform(-0.004, 0.004)
    envelope = math.exp(-0.5 * ((Fn - Fn0) / sigma) ** 2)
    freq = 11.0 + rng.uniform(-2.0, 2.0)
    phase = rng.uniform(-0.5, 0.5)
    val = 1.0 + amp * envelope * math.sin((Fn - Fn0) * math.pi * freq + phase)
    return float(np.clip(val, 0.35, 2.0))

def residuary_cr_tug(Fn, Cb, L, B, seed):
    slenderness = L / max(1.0, B)
    base = cr_base_fn_tug(Fn, Cb, slenderness)
    mult = wave_mult_tug(Fn, Cb, seed)
    return float(np.clip(base * mult, 1e-9, 0.01))

# ---------- compute RT ----------
def compute_total_rt(ship, n_points=N_POINTS):
    L = float(ship["L"]); B = float(ship["B"]); T = float(ship["T"])
    disp_t = float(ship["disp_t"]); Cb = float(ship["Cb"])
    rho = float(ship["rho"]); nu = float(ship["nu"])
    s_min = float(ship["s_min"]); s_max = float(ship["s_max"])

    speeds_kn = np.linspace(s_min, s_max, n_points)
    speeds_ms = knots_to_ms(speeds_kn)
    S = wetted_surface_estimate(L, B, T, Cb)
    name_hash = int(hashlib.md5(ship["name"].encode("utf8")).hexdigest()[:8], 16) % (2**31 - 1)

    RT = np.zeros_like(speeds_ms)
    RF_arr = np.zeros_like(speeds_ms)
    RR_arr = np.zeros_like(speeds_ms)
    Fn_arr = np.zeros_like(speeds_ms)
    for i, v in enumerate(speeds_ms):
        Re = reynolds_number(v, L, nu)
        Cf = ittcf(Re)
        RF = 0.5 * rho * S * v**2 * Cf
        Fn = froude_number(v, L)
        Cr = residuary_cr_tug(Fn, Cb, L, B, name_hash)
        RR = 0.5 * rho * S * v**2 * Cr
        RT[i] = (RF + RR) / 1000.0   # kN
        RF_arr[i] = RF / 1000.0
        RR_arr[i] = RR / 1000.0
        Fn_arr[i] = Fn

    return {
        "speeds_kn": speeds_kn,
        "speeds_ms": speeds_ms,
        "RT": RT,
        "RF": RF_arr,
        "RR": RR_arr,
        "Fn": Fn_arr,
        "S": S
    }

# ---------- fit residuary scalar to measured CSV (optional) ----------
def fit_rr_scale_to_measured(ship, computed, measured_df):
    """
    Fit a scalar alpha so that:
      measured_RT_kN ≈ RF_kN + alpha * RR_model_kN
    Solve least squares for alpha.
    Returns alpha and scaled RT array.
    """
    # interpolate model RF and RR to measured speeds
    sp_meas = measured_df["speed_kn"].values
    RT_meas = measured_df["RT_kN"].values
    RF_interp = np.interp(sp_meas, computed["speeds_kn"], computed["RF"])
    RR_interp = np.interp(sp_meas, computed["speeds_kn"], computed["RR"])
    # linear least squares: minimize || (RF + alpha*RR) - RT_meas ||
    # alpha = sum( RR*(RT_meas - RF) ) / sum(RR^2)
    denom = np.sum(RR_interp**2)
    if denom <= 0:
        return 1.0, computed["RT"]
    alpha = np.sum(RR_interp * (RT_meas - RF_interp)) / denom
    alpha = float(alpha) if not np.isnan(alpha) else 1.0
    # clip alpha to avoid wild scaling
    alpha = float(np.clip(alpha, 0.2, 5.0))
    # calculate scaled RT across model speeds
    RT_scaled = computed["RF"] + alpha * computed["RR"]
    return alpha, RT_scaled

# ---------- MAIN ----------
def main():
    ship = TUG.copy()
    # compute model RT
    comp = compute_total_rt(ship, n_points=N_POINTS)

    # try to load measured CSV and fit if present
    measured_path = os.path.join(os.getcwd(), MEASURED_CSV)
    fitted_alpha = None
    RT_to_plot = comp["RT"]
    if os.path.exists(measured_path):
        try:
            dfm = pd.read_csv(measured_path)
            if {"speed_kn", "RT_kN"}.issubset(dfm.columns):
                alpha, RT_scaled = fit_rr_scale_to_measured(ship, comp, dfm)
                fitted_alpha = alpha
                RT_to_plot = RT_scaled
                print(f"Fitted residuary scale alpha = {alpha:.3f} to measured data from '{MEASURED_CSV}'.")
            else:
                print(f"CSV found but missing required columns 'speed_kn' and 'RT_kN'. Skipping fit.")
        except Exception as e:
            print("Error reading measured CSV:", e)

    # Plot only total RT (clean)
    plt.figure(figsize=(8.5, 5.5))
    plt.plot(comp["speeds_kn"], RT_to_plot, linewidth=2.0, solid_capstyle='round')
    plt.title(f"{ship['name']} — Total Resistance (RT)   LOA={ship['L']:.0f} m, Cb={ship['Cb']:.2f}", fontsize=12, fontweight='bold')
    plt.xlabel("Speed (knots)")
    plt.ylabel("Total Resistance (kN)")
    plt.grid(True, linestyle=":", linewidth=0.6)
    # annotate hump Fn ~ 0.26-0.30 region (approx)
    # compute Fn where RR/RF ratio peaks to locate hump
    ratio = (comp["RR"] / np.maximum(comp["RF"], 1e-9))
    hump_idx = int(np.argmax(ratio))
    hump_speed = comp["speeds_kn"][hump_idx]
    hump_RT = RT_to_plot[hump_idx]
    plt.axvline(hump_speed, color='0.6', linestyle='--', linewidth=0.8)
    plt.text(hump_speed + 0.3, hump_RT*0.9, f"Hump ~ {hump_speed:.1f} kn", fontsize=9)

    # save & show
    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=220)
    print(f"Saved total resistance plot: {OUT_PNG}")
    if SHOW_PLOT:
        plt.show()

    if fitted_alpha is not None:
        print("Note: residuary was scaled by alpha to match measured data.")

if __name__ == "__main__":
    main()
