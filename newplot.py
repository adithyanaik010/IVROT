import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from io import StringIO

# -----------------------------
# Holtrop–Mennen Resistance Function (for long ships, LWL > 100m)
# -----------------------------
def resistance_hol(Lpp, B, T, V, rho, nu, Cb, S, lcb, Cwp, Cp, Cm, Abt, hb, At, Cstern, iE, dCF):
    """Calculates resistance using a simplified Holtrop-Mennen approach."""
    Re = V * Lpp / nu
    Cf = 0.075 / ((np.log10(Re) - 2) ** 2)
    
    k1 = 1 + 0.15 * Cb
    Rf = 0.5 * rho * V**2 * S * Cf * k1

    Fn = V / np.sqrt(9.81 * Lpp)
    Rr = 0.5 * rho * V**2 * S * (0.004 + 0.002 * Cb**2) * (1 + 0.6 * np.exp(-((Fn - 0.25)/0.05)**2))
    
    Rt = Rf + Rr
    return {'Rt': Rt, 'Rf': Rf, 'Rr': Rr}

# -----------------------------
# Van Oortmerssen Resistance Function (for short ships, LWL <= 100m)
# -----------------------------
def resistance_van(LWL, B, T, V, rho, nu, nabla, S, Cp, k2_factor):
    """Calculates resistance using the Van Oortmerssen method for short ships."""
    g = 9.81
    
    Rn = V * LWL / nu
    if Rn == 0:
        Cf = 0
    else:
        Cf = 0.075 / (np.log10(Rn) - 2)**2
    
    Rf = 0.5 * rho * S * V**2 * (Cf + k2_factor)
    
    Fn = V / np.sqrt(g * LWL)
    Rr = (1.1 + 0.3 * Cp) * (Fn**2 / (0.3**2 + Fn**2)) * 0.5 * rho * g * nabla**(2/3)
    
    Rt = Rf + Rr
    return {'Rt': Rt, 'Rf': Rf, 'Rr': Rr}

# -----------------------------
# CSV DATA
# -----------------------------
csv_data = """ShipType,v,rho,nu,LWL,LPP,Ld,B,T,nabla,S,Cp,Cm,lcb,iE,dCF,CB,CWP,ABT,hB,AT,Cstern,Sapp,k2_factor
Cargo Ship,15,1025,1.19E-06,140,135,N/A,22,8.5,12000,3400,0.68,0.99,-1.5,22,0.0005,0.67,0.78,30,4.5,25,80,30,0.3
Tanker,14,1025,1.19E-06,240,230,N/A,42,15.5,85000,14500,0.81,0.995,0.5,18,0.0005,0.8,0.88,80,8,70,120,80,0.3
Container,22,1025,1.19E-06,280,270,N/A,32.2,13.5,65000,12100,0.65,0.985,1.2,12,0.0005,0.64,0.75,60,7,40,90,60,0.2
Passenger,20,1025,1.19E-06,210,200,N/A,28,8,30000,6800,0.7,0.99,0.8,15,0.0005,0.69,0.79,20,6,55,70,50,0.25
Fishing Vessel,12,1025,1.19E-06,45,42,43.5,9.5,4.5,750,550,0.62,0.9,-3.5,30,0.0005,0.55,0.85,0,0,0,5,0,0.05
"""
df = pd.read_csv(StringIO(csv_data))

# -----------------------------
# PLOT ALL SHIPS
# -----------------------------
for i, row in df.iterrows():
    speeds_knots = np.linspace(0.1, 25, 100)
    speeds_ms = speeds_knots * 0.514444
    
    total_resistance = []
    
    if row['LWL'] > 100:
        method_name = "Holtrop–Mennen"
        for v_ms in speeds_ms:
            res = resistance_hol(row['LPP'], row['B'], row['T'], v_ms, row['rho'], row['nu'],
                                 row['CB'], row['S'], row['lcb'], row['CWP'], row['Cp'], row['Cm'],
                                 row['ABT'], row['hB'], row['AT'], row['Cstern'], row['iE'], row['dCF'])
            total_resistance.append(res['Rt'])
    else:
        method_name = "Van Oortmerssen"
        for v_ms in speeds_ms:
            res = resistance_van(row['LWL'], row['B'], row['T'], v_ms, row['rho'], row['nu'],
                                 row['nabla'], row['S'], row['Cp'], row['k2_factor'])
            total_resistance.append(res['Rt'])
    
    plt.figure(figsize=(10, 6))
    
    plt.plot(speeds_knots, np.array(total_resistance) / 1000, marker='o', linestyle='-', color='b', markersize=4)
    
    plot_title = f"Total resistance vs speed for {row['LWL']} m {row['ShipType']}"
    plt.title(plot_title)
    plt.xlabel('Speed (kn)')
    plt.ylabel('Total resistance (kN)')
    
    plt.grid(True, which='major', linestyle='--', linewidth=0.5, color='gray')
    plt.minorticks_on()
    plt.grid(True, which='minor', linestyle=':', linewidth=0.5, color='lightgray')
    
    # Generate a unique filename and save the plot as a PNG
    filename = f"{row['ShipType']}_Resistance_Plot.png"
    plt.savefig(filename)
    
    # Close the plot to free up memory before the next iteration
    plt.close()

print("All plots have been saved as PNG files.")

