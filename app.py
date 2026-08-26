import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import io

# Page Configuration
st.set_page_config(
    page_title="Blast Furnace Burden Thermophysical & Hydrodynamic Simulator",
    page_icon="🔥",
    layout="wide"
)

st.title("🔥 Blast Furnace Multi-Zone Thermophysical & Hydrodynamic Simulator")
st.markdown(r"""
**Model Architecture Features:** 
* **Solid Matrix Scaling:** $C_{p,s}$ and $k_s$ scaled by $(1 - \phi_{\text{eff}})$ for LTNE/Non-LTNE COMSOL domains.
* **Hydrodynamics Engine:** Calculates harmonic mean particle diameter $d_{p,\text{eff}}$, intrinsic permeability $K$, Forchheimer drag $\beta_F$, and Ergun/Brinkman pressure drop profiles ($\Delta P/L$).
* **Tuyere Pressure & Blast Velocity:** Integrates Tuyere inlet pressure ($P_{\text{tuyere}}$), top pressure ($P_{\text{top}}$), blast flow rates, and pressure-corrected gas density $\rho_g(T, P)$.
* **COMSOL Multiphysics Export Engine:** Direct generation of unit-formatted expressions ready for COMSOL Global Definitions / Variables import.
* **2D & 3D Spatial Analytics:** Interactive 2D contours and 3D surface meshes (`go.Surface`) with live camera elevation, azimuth, and distance controls.
* **Dynamic Temperature Sweeps:** Multi-tab visual analytics across temperatures from 273.15 K to 2000 K.
""")

# --- Helper Function: Synchronized Input ---
def paired_input(label, min_val, max_val, default_val, step, key, container=st.sidebar, fmt="%.3f"):
    val_key = f"val_{key}"
    num_key = f"num_{key}"
    slider_key = f"slider_{key}"

    if val_key not in st.session_state: st.session_state[val_key] = float(default_val)
    if num_key not in st.session_state: st.session_state[num_key] = float(default_val)
    if slider_key not in st.session_state: st.session_state[slider_key] = float(default_val)

    def update_from_num():
        st.session_state[slider_key] = st.session_state[num_key]
        st.session_state[val_key] = st.session_state[num_key]

    def update_from_slider():
        st.session_state[num_key] = st.session_state[slider_key]
        st.session_state[val_key] = st.session_state[slider_key]

    col_label, col_input = container.columns([3, 1.2])
    with col_label: container.markdown(f"**{label}**")
    with col_input:
        container.number_input(
            f"{label} num", min_value=float(min_val), max_value=float(max_val), 
            step=float(step), format=fmt, key=num_key, on_change=update_from_num, label_visibility="collapsed"
        )
        
    container.slider(
        f"{label} slider", min_value=float(min_val), max_value=float(max_val), 
        step=float(step), key=slider_key, on_change=update_from_slider, label_visibility="collapsed"
    )
    return st.session_state[val_key]

# --- Sidebar: Zone Selection ---
st.sidebar.header("🗺️ Blast Furnace Region")
bf_zone = st.sidebar.radio("Select Operating Zone", ["Granular Zone (Dry Burden Mix)", "Deadman / Lower Coke Zone (Coke + Melts)"])
is_deadman = "Deadman" in bf_zone

# --- Sidebar: Material Database & Particle Sizes ---
st.sidebar.header("🛠️ Material Database & Particle Sizes")

default_materials = {
    'coke': {'td': 1850.0, 'bd': 480.0, 'mass': 960.0, 'dp': 0.040, 'cpa': 860.0, 'cpb': 5.40e-1, 'cpc': -2.75e7, 'ka': 0.28, 'kb': 1.75e-3, 'kc': -3.20e-7},
    'sinter': {'td': 3450.0, 'bd': 1700.0, 'mass': 5950.0, 'dp': 0.025, 'cpa': 745.0, 'cpb': 2.60e-1, 'cpc': -1.25e7, 'ka': 0.92, 'kb': 0.48e-3, 'kc': 0.85e-7},
    'pellet': {'td': 3350.0, 'bd': 2050.0, 'mass': 6150.0, 'dp': 0.015, 'cpa': 620.5, 'cpb': 6.15e-1, 'cpc': -1.18e7, 'ka': 1.42, 'kb': -0.38e-3, 'kc': 1.15e-7},
    'lump': {'td': 4600.0, 'bd': 2200.0, 'mass': 3300.0, 'dp': 0.030, 'cpa': 615.0, 'cpb': 5.85e-1, 'cpc': -1.15e7, 'ka': 2.15, 'kb': -0.65e-3, 'kc': 0.25e-7}
}

active_mats = ['coke', 'sinter', 'pellet', 'lump'] if not is_deadman else ['coke']

materials = {}
masses = {}
volumes = {}

for mat in active_mats:
    with st.sidebar.expander(f"{mat.capitalize()} Properties", expanded=(mat == 'coke')):
        td = st.number_input("True Density (kg/m³)", value=default_materials[mat]['td'], step=50.0, key=f"{mat}_td")
        bd = st.number_input("Bulk Density (kg/m³)", value=default_materials[mat]['bd'], step=50.0, key=f"{mat}_bd")
        m = st.number_input("Mass (kg)", value=default_materials[mat]['mass'], step=50.0, key=f"{mat}_m")
        dp_val = st.number_input("Particle Diameter d_p (m)", value=default_materials[mat]['dp'], step=0.005, format="%.3f", key=f"{mat}_dp")
        v = m / bd if bd > 0 else 0.0
        st.caption(f"Calculated Bulk Volume: {v:.3f} m³")
            
        masses[mat] = m
        volumes[mat] = v
        
        st.divider()
        st.markdown(r"**$C_p$ Coefficients** ($A + B\cdot T + C\cdot T^{-2}$)")
        col_cpa, col_cpb, col_cpc = st.columns(3)
        cpa = col_cpa.number_input("A", value=float(default_materials[mat]['cpa']), key=f"{mat}_cpa")
        cpb = col_cpb.number_input("B", value=float(default_materials[mat]['cpb']), key=f"{mat}_cpb")
        cpc = col_cpc.number_input("C", value=float(default_materials[mat]['cpc']), key=f"{mat}_cpc")
        
        st.markdown(r"**$k$ Coefficients** ($A + B\cdot T + C\cdot T^2$)")
        col_ka, col_kb, col_kc = st.columns(3)
        ka = col_ka.number_input("A", value=float(default_materials[mat]['ka']), key=f"{mat}_ka")
        kb = col_kb.number_input("B", value=float(default_materials[mat]['kb']), key=f"{mat}_kb")
        kc = col_kc.number_input("C", value=float(default_materials[mat]['kc']), key=f"{mat}_kc")

        materials[mat] = {'true_density': td, 'bulk_density': bd, 'dp': dp_val, 'cp_coeffs': (cpa, cpb, cpc), 'k_coeffs': (ka, kb, kc)}

for mat in ['sinter', 'pellet', 'lump']:
    if mat not in active_mats:
        masses[mat] = 0.0
        volumes[mat] = 0.0
        materials[mat] = materials.get(mat, {'true_density': 1.0, 'bulk_density': 1.0, 'dp': 0.02, 'cp_coeffs': (0,0,0), 'k_coeffs': (0,0,0)})

# --- Sidebar: Liquid Melts Holdup (Deadman Only) ---
s_iron, mu_iron = 0.0, 0.005
rho_iron_A, rho_iron_B = 7000.0, -0.5
cp_iron_A, cp_iron_B = 800.0, 0.05
k_iron_A, k_iron_B = 30.0, 0.0

s_slag, mu_slag = 0.0, 0.05
rho_slag_A, rho_slag_B = 2600.0, -0.2
cp_slag_A, cp_slag_B = 1200.0, 0.1
k_slag_A, k_slag_B = 3.5, 0.0

if is_deadman:
    st.sidebar.header("🧪 Deadman Liquid Melts & Properties")
    with st.sidebar.expander("Liquid Iron Parameters & T-Coeffs", expanded=True):
        s_iron = st.slider("Iron Saturation (s_iron)", 0.0, 0.7, 0.15, 0.01, format="%.2f")
        mu_iron = st.number_input("Iron Viscosity μ_iron (Pa·s)", value=0.005, format="%.4f")
        st.markdown("**Density ρ_iron(T) = A + B·T**")
        col_ri1, col_ri2 = st.columns(2)
        rho_iron_A = col_ri1.number_input("ρ_iron A", value=7000.0, key="ri_a")
        rho_iron_B = col_ri2.number_input("ρ_iron B", value=-0.5, key="ri_b")
        st.markdown("**Specific Heat Cp_iron(T) = A + B·T**")
        col_ci1, col_ci2 = st.columns(2)
        cp_iron_A = col_ci1.number_input("Cp_iron A", value=800.0, key="cpi_a")
        cp_iron_B = col_ci2.number_input("Cp_iron B", value=0.05, key="cpi_b")
        st.markdown("**Conductivity k_iron(T) = A + B·T**")
        col_ki1, col_ki2 = st.columns(2)
        k_iron_A = col_ki1.number_input("k_iron A", value=30.0, key="ki_a")
        k_iron_B = col_ki2.number_input("k_iron B", value=0.0, key="ki_b")

    with st.sidebar.expander("Liquid Slag Parameters & T-Coeffs", expanded=False):
        s_slag = st.slider("Slag Saturation (s_slag)", 0.0, 0.7, 0.10, 0.01, format="%.2f")
        mu_slag = st.number_input("Slag Viscosity μ_slag (Pa·s)", value=0.05, format="%.3f")
        st.markdown("**Density ρ_slag(T) = A + B·T**")
        col_rs1, col_rs2 = st.columns(2)
        rho_slag_A = col_rs1.number_input("ρ_slag A", value=2600.0, key="rs_a")
        rho_slag_B = col_rs2.number_input("ρ_slag B", value=-0.2, key="rs_b")
        st.markdown("**Specific Heat Cp_slag(T) = A + B·T**")
        col_cs1, col_cs2 = st.columns(2)
        cp_slag_A = col_cs1.number_input("Cp_slag A", value=1200.0, key="cps_a")
        cp_slag_B = col_cs2.number_input("Cp_slag B", value=0.1, key="cps_b")
        st.markdown("**Conductivity k_slag(T) = A + B·T**")
        col_ks1, col_ks2 = st.columns(2)
        k_slag_A = col_ks1.number_input("k_slag A", value=3.5, key="ks_a")
        k_slag_B = col_ks2.number_input("k_slag B", value=0.0, key="ks_b")

# --- Sidebar: Gas Flow, Pressure & Tuyere Hydrodynamics ---
st.sidebar.header("💨 Flow Parameters & Tuyere Hydraulics")
temperature_k = paired_input("Bed Temp (K)", 273.15, 2000.0, 1600.0 if is_deadman else 1000.0, 10.0, "temp_k", fmt="%.1f")
vg = paired_input("Bed Superficial Gas Velocity (m/s)", 0.1, 5.0, 1.5, 0.1, "vg_val")

st.sidebar.markdown("---")
st.sidebar.markdown("**🔥 Tuyere & Bed Pressure Configuration**")
p_tuyere_kPa = paired_input("Tuyere Inlet Pressure (kPa abs)", 100.0, 600.0, 350.0, 10.0, "p_tuyere", fmt="%.1f")
p_top_kPa = paired_input("Top Gas Pressure (kPa abs)", 100.0, 300.0, 150.0, 5.0, "p_top", fmt="%.1f")

with st.sidebar.expander("💨 Tuyere Geometry & Blast Velocity Calculator", expanded=False):
    num_tuyeres = st.number_input("Number of Tuyeres", value=32, step=1, key="num_tuyeres")
    d_tuyere_cm = st.number_input("Tuyere Inner Diameter (cm)", value=15.0, step=0.5, key="d_tuyere")
    q_blast_nm3min = st.number_input("Total Blast Flow Rate (Nm³/min)", value=6000.0, step=100.0, key="q_blast")
    
    # Calculate blast velocity at tuyere nose
    a_single_tuyere = np.pi * ((d_tuyere_cm / 100.0) / 2.0) ** 2
    a_total_tuyeres = a_single_tuyere * num_tuyeres
    q_blast_m3s_actual = (q_blast_nm3min / 60.0) * (101.325 / p_tuyere_kPa) * (2000.0 / 273.15) # scaled to blast temperature (~2000K flame)
    v_tuyere_actual = q_blast_m3s_actual / a_total_tuyeres if a_total_tuyeres > 0 else 0.0
    st.info(f"**Calculated Tuyere Nose Velocity:** `{v_tuyere_actual:.1f} m/s`")

bed_height = paired_input("Bed Height L (m)", 0.5, 35.0, 10.0, 0.5, "bed_h", fmt="%.1f")
bed_radius = paired_input("Bed Radius R (m)", 1.0, 10.0, 4.0, 0.5, "bed_r", fmt="%.1f")

with st.sidebar.expander("Gas Density ρ_g_std ($A + BT + CT^2 + DT^3$ @ 1 atm)", expanded=False):
    rhog_A = st.number_input("ρ_g A", value=0.95, format="%.3f", key="rhog_a")
    rhog_B = st.number_input("ρ_g B", value=-7.50e-4, format="%.2e", key="rhog_b")
    rhog_C = st.number_input("ρ_g C", value=2.50e-7, format="%.2e", key="rhog_c")
    rhog_D = st.number_input("ρ_g D", value=0.0, format="%.2e", key="rhog_d")

with st.sidebar.expander("Gas Dynamic Viscosity μ_g ($A + BT + CT^2 + DT^3$)", expanded=False):
    mu_A = st.number_input("μ A", value=1.00e-5, format="%.2e", key="mu_a")
    mu_B = st.number_input("μ B", value=3.50e-8, format="%.2e", key="mu_b")
    mu_C = st.number_input("μ C", value=0.0, format="%.2e", key="mu_c")
    mu_D = st.number_input("μ D", value=0.0, format="%.2e", key="mu_d")

with st.sidebar.expander("Gas Specific Heat C_p,g ($A + BT + CT^2 + DT^3$)", expanded=False):
    cpg_A = st.number_input("Cpg A", value=1000.0, key="cpg_a")
    cpg_B = st.number_input("Cpg B", value=0.15, key="cpg_b")
    cpg_C = st.number_input("Cpg C", value=0.0, format="%.2e", key="cpg_c")
    cpg_D = st.number_input("Cpg D", value=0.0, format="%.2e", key="cpg_d")

with st.sidebar.expander("Gas Thermal Conductivity k_g ($A + BT + CT^2 + DT^3$)", expanded=False):
    kg_A = st.number_input("kg A", value=0.010, format="%.3f", key="kg_a")
    kg_B = st.number_input("kg B", value=5.00e-5, format="%.2e", key="kg_b")
    kg_C = st.number_input("kg C", value=0.0, format="%.2e", key="kg_c")
    kg_D = st.number_input("kg D", value=0.0, format="%.2e", key="kg_d")

# --- Void Fraction & Mass Fraction Calculations ---
total_volume = sum(volumes.values()) or 1.0
total_mass = sum(masses.values()) or 1.0
mass_fractions = {mat: m / total_mass for mat, m in masses.items()}

weighted_void_sum = sum(vol * (1.0 - (materials[mat]['bulk_density'] / materials[mat]['true_density'])) for mat, vol in volumes.items() if materials[mat]['true_density'] > 0)
phi = weighted_void_sum / total_volume

# --- Physics Calculation Engine ---
def calculate_physics(T, P_kPa=p_tuyere_kPa):
    # 1. Solid Mixture Effective Properties
    cp_s, ks_s, rho_s = 0.0, 0.0, 0.0
    cp_A, cp_B, cp_C = 0.0, 0.0, 0.0
    ks_A, ks_B, ks_C = 0.0, 0.0, 0.0
    
    active = {m: w for m, w in mass_fractions.items() if w > 0}
    v_solid = {m: w / materials[m]['true_density'] for m, w in active.items()}
    v_tot = sum(v_solid.values())
    vol_fracs = {m: v / v_tot for m, v in v_solid.items()} if v_tot > 0 else {}
    
    for m, w in active.items():
        A, B, C = materials[m]['cp_coeffs']
        cp_A += w * A; cp_B += w * B; cp_C += w * C
        cp_s += w * (A + B * T + C * (T ** -2))
        
    for m, x in vol_fracs.items():
        A, B, C = materials[m]['k_coeffs']
        ks_A += x * A; ks_B += x * B; ks_C += x * C
        ks_s += x * (A + B * T + C * (T ** 2))
        rho_s += x * materials[m]['true_density']

    rho_bulk = total_mass / total_volume if total_volume > 0 else 0.0

    # Harmonic mean particle diameter for multi-component burden
    inv_dp_sum = sum(vol_fracs[m] / materials[m]['dp'] for m in vol_fracs if materials[m]['dp'] > 0)
    dp_eff = (1.0 / inv_dp_sum) if inv_dp_sum > 0 else 0.025
    r_eff = dp_eff / 2.0

    # 2. Effective Voidage (Accounting for Liquid Holdup in Deadman)
    if is_deadman:
        s_gas = max(0.01, 1.0 - (s_iron + s_slag))
        phi_eff = phi * s_gas
    else:
        s_gas = 1.0
        phi_eff = phi

    cp_s_eff = cp_s * (1.0 - phi_eff)
    ks_s_eff = ks_s * (1.0 - phi_eff)

    # 3. Gas Transport Properties with Ideal Gas Pressure Correction
    rho_g_std = rhog_A + rhog_B * T + rhog_C * (T ** 2) + rhog_D * (T ** 3)
    rho_g = rho_g_std * (P_kPa / 101.325) # Ideal gas pressure scaling relative to 1 atm
    
    mu_g = mu_A + mu_B * T + mu_C * (T ** 2) + mu_D * (T ** 3)
    cp_g = cpg_A + cpg_B * T + cpg_C * (T ** 2) + cpg_D * (T ** 3)
    kg = kg_A + kg_B * T + kg_C * (T ** 2) + kg_D * (T ** 3)

    # 4. Modified Reynolds Number (Re_m) & Explicit Conversion to Superficial (Re_p)
    if (1.0 - phi_eff) > 0 and mu_g > 0:
        Re_m = (rho_g * vg * dp_eff) / ((1.0 - phi_eff) * mu_g)
    else:
        Re_m = 0.0

    # Explicit transformation step back to superficial Re_p for Wakao-Kaguei evaluation
    Re_p = Re_m * (1.0 - phi_eff)

    # 5. Interphase Heat Transfer Coefficients (Wakao & Kaguei, 1982)
    Pr = (cp_g * mu_g) / kg if kg > 0 else 0.0
    Nu = 2.0 + 1.1 * (Pr ** (1/3)) * (Re_p ** 0.6)
    
    h_sf = (Nu * kg) / dp_eff if dp_eff > 0 else 0.0
    a_sf = (6.0 * (1.0 - phi_eff)) / dp_eff if dp_eff > 0 else 0.0
    q_sf_coeff = h_sf * a_sf

    # 6. Packed Bed Pressure Drop Gradients (Ergun / Brinkman)
    if phi_eff > 0 and (1.0 - phi_eff) > 0 and dp_eff > 0:
        K_perm = (phi_eff**3 * (dp_eff**2)) / (150.0 * ((1.0 - phi_eff)**2))
        beta_F = (1.75 * (1.0 - phi_eff)) / (phi_eff**3 * dp_eff)
        dp_viscous_Pa_m = (mu_g / K_perm) * vg
        dp_inertial_Pa_m = beta_F * rho_g * (vg**2)
        dp_total_Pa_m = dp_viscous_Pa_m + dp_inertial_Pa_m
    else:
        K_perm, beta_F, dp_viscous_Pa_m, dp_inertial_Pa_m, dp_total_Pa_m = 1e-10, 0.0, 0.0, 0.0, 0.0

    delta_p_total_kPa = (dp_total_Pa_m * bed_height) / 1000.0

    fluid_state = {'rho': rho_g, 'cp': cp_g, 'k': kg, 'mu': mu_g}
    hydro_state = {
        'dp_eff': dp_eff, 'r_eff': r_eff, 'Re_m': Re_m, 'Re_p': Re_p,
        'K_perm': K_perm, 'beta_F': beta_F,
        'dp_viscous_Pa_m': dp_viscous_Pa_m, 'dp_inertial_Pa_m': dp_inertial_Pa_m,
        'dp_total_Pa_m': dp_total_Pa_m, 'delta_p_total_kPa': delta_p_total_kPa,
        'phi_eff': phi_eff
    }
    
    coeffs = {
        'cp': (cp_A, cp_B, cp_C), 'ks': (ks_A, ks_B, ks_C), 
        'rhog': (rhog_A, rhog_B, rhog_C, rhog_D),
        'mu': (mu_A, mu_B, mu_C, mu_D), 'cpg': (cpg_A, cpg_B, cpg_C, cpg_D), 'kg': (kg_A, kg_B, kg_C, kg_D)
    }
    return (cp_s, ks_s, rho_s, rho_bulk), (cp_s_eff, ks_s_eff), (Re_m, Re_p, Pr, Nu, h_sf, a_sf, q_sf_coeff, fluid_state), hydro_state, coeffs

(cp_s, ks_s, rho_s, rho_bulk), (cp_s_eff, ks_s_eff), fluid_interphase, hydro_state, coeffs = calculate_physics(temperature_k, p_tuyere_kPa)
Re_m, Re_p, Pr, Nu, h_sf, a_sf, q_sf_coeff, fluid_state = fluid_interphase
cp_A, cp_B, cp_C = coeffs['cp']
ks_A, ks_B, ks_C = coeffs['ks']

# --- Section: 2D Spatial Heatmap & 3D Surface Mesh Visualizer ---
st.markdown("---")
st.subheader("🌐 2D/3D Spatial Field Distribution Maps (R x Z Mesh)")

st.sidebar.header("🗺️ 2D & 3D Spatial Controls")
t_bottom = st.sidebar.number_input("Tuyere / Bottom Temp (K)", value=2000.0, step=50.0)
t_top = st.sidebar.number_input("Top Burden Temp (K)", value=400.0, step=25.0)
radial_c_bias = st.sidebar.slider("Central Flow Temperature Bias", 0.0, 0.5, 0.2, 0.05)
wall_porosity_bias = st.sidebar.slider("Wall Channeling Velocity Bias", 0.0, 0.6, 0.25, 0.05)

st.sidebar.header("🧊 3D Camera Controls")
camera_elevation = st.sidebar.slider("Camera Elevation (°)", 0, 90, 35, 5)
camera_azimuth = st.sidebar.slider("Camera Azimuth (°)", -180, 180, 45, 5)
camera_distance = st.sidebar.slider("Camera Distance", 1.0, 4.0, 1.8, 0.1)

# Convert polar angles to 3D Plotly eye coordinates
ele_rad = np.radians(camera_elevation)
azi_rad = np.radians(camera_azimuth)
eye_x = camera_distance * np.cos(ele_rad) * np.sin(azi_rad)
eye_y = -camera_distance * np.cos(ele_rad) * np.cos(azi_rad)
eye_z = camera_distance * np.sin(ele_rad)

camera_config = dict(eye=dict(x=eye_x, y=eye_y, z=eye_z))

# Meshgrid setup
r_vec = np.linspace(-bed_radius, bed_radius, 60)
z_vec = np.linspace(0, bed_height, 60)
R_grid, Z_grid = np.meshgrid(r_vec, z_vec)

# 2D Analytical Fields incorporating local pressure drop P(z)
Z_norm = Z_grid / bed_height
R_norm = R_grid / bed_radius
P_2D_kPa = p_tuyere_kPa - (p_tuyere_kPa - p_top_kPa) * Z_norm
T_2D = t_top + (t_bottom - t_top) * (Z_norm ** 0.85) * (1.0 + radial_c_bias * np.exp(-4.0 * (R_norm ** 2)))
V_2D = vg * (1.0 + radial_c_bias * np.exp(-3.0 * (R_norm ** 2)) + wall_porosity_bias * (R_norm ** 4)) * (T_2D / temperature_k) ** 0.5

K_perm_val = max(hydro_state['K_perm'], 1e-12)
DP_2D = ((fluid_state['mu'] / K_perm_val) * V_2D + hydro_state['beta_F'] * (fluid_state['rho'] * (P_2D_kPa / p_tuyere_kPa)) * (V_2D ** 2)) / 1000.0

tab_map_T, tab_map_V, tab_map_DP, tab_3d_T, tab_3d_V = st.tabs([
    "🔥 2D Temperature Contour", 
    "💨 2D Velocity Contour", 
    "📊 2D Pressure Gradient Contour",
    "🧊 3D Temperature Surface Mesh",
    "🧊 3D Velocity Surface Mesh"
])

with tab_map_T:
    fig_contour_T = go.Figure(data=go.Contour(
        z=T_2D, x=r_vec, y=z_vec,
        colorscale='Hot',
        contours=dict(coloring='heatmap', showlabels=True, labelfont=dict(size=11, color='white')),
        colorbar=dict(title='Temp [K]')
    ))
    fig_contour_T.update_layout(
        title="2D Temperature Distribution Profile T(r, z)",
        xaxis_title="Radial Position r [m]", yaxis_title="Bed Height z [m]",
        height=550
    )
    st.plotly_chart(fig_contour_T, use_container_width=True)

with tab_map_V:
    fig_contour_V = go.Figure(data=go.Contour(
        z=V_2D, x=r_vec, y=z_vec,
        colorscale='Turbo',
        contours=dict(coloring='heatmap', showlabels=True, labelfont=dict(size=11, color='white')),
        colorbar=dict(title='Velocity [m/s]')
    ))
    fig_contour_V.update_layout(
        title="2D Superficial Gas Velocity Distribution Profile v_z(r, z)",
        xaxis_title="Radial Position r [m]", yaxis_title="Bed Height z [m]",
        height=550
    )
    st.plotly_chart(fig_contour_V, use_container_width=True)

with tab_map_DP:
    fig_contour_DP = go.Figure(data=go.Contour(
        z=DP_2D, x=r_vec, y=z_vec,
        colorscale='Viridis',
        contours=dict(coloring='heatmap', showlabels=True, labelfont=dict(size=11, color='white')),
        colorbar=dict(title='ΔP/L [kPa/m]')
    ))
    fig_contour_DP.update_layout(
        title="2D Pressure Drop Gradient Profile ΔP/L(r, z)",
        xaxis_title="Radial Position r [m]", yaxis_title="Bed Height z [m]",
        height=550
    )
    st.plotly_chart(fig_contour_DP, use_container_width=True)

with tab_3d_T:
    fig_3d_T = go.Figure(data=[go.Surface(
        z=T_2D, x=R_grid, y=Z_grid,
        colorscale='Hot',
        colorbar=dict(title='Temp [K]')
    )])
    fig_3d_T.update_layout(
        title="3D Temperature Surface Mesh T(r, z)",
        scene=dict(
            xaxis_title="Radial Position r [m]",
            yaxis_title="Bed Height z [m]",
            zaxis_title="Temperature T [K]",
            camera=camera_config
        ),
        height=650
    )
    st.plotly_chart(fig_3d_T, use_container_width=True)

with tab_3d_V:
    fig_3d_V = go.Figure(data=[go.Surface(
        z=V_2D, x=R_grid, y=Z_grid,
        colorscale='Turbo',
        colorbar=dict(title='Velocity [m/s]')
    )])
    fig_3d_V.update_layout(
        title="3D Superficial Gas Velocity Surface Mesh v_z(r, z)",
        scene=dict(
            xaxis_title="Radial Position r [m]",
            yaxis_title="Bed Height z [m]",
            zaxis_title="Velocity v_z [m/s]",
            camera=camera_config
        ),
        height=650
    )
    st.plotly_chart(fig_3d_V, use_container_width=True)

# --- Dynamic Temperature Sweeps Section (273.15 K to 2000.0 K) ---
st.markdown("---")
st.subheader("📈 Dynamic Temperature Sweeps (273.15 K to 2000 K)")

T_sweep = np.linspace(273.15, 2000.0, 100)
sweep_records = []

for T_i in T_sweep:
    (cp_s_i, ks_s_i, rho_s_i, rho_bulk_i), (cp_s_eff_i, ks_s_eff_i), (Re_m_i, Re_p_i, Pr_i, Nu_i, h_sf_i, a_sf_i, q_sf_coeff_i, fluid_state_i), hydro_state_i, _ = calculate_physics(T_i, p_tuyere_kPa)
    sweep_records.append({
        "Temperature (K)": T_i,
        "Cp Solid (Intrinsic)": cp_s_i,
        "Cp Solid (Scaled [1-φ])": cp_s_eff_i,
        "Cp Pore Fluid": fluid_state_i['cp'],
        "k Solid (Intrinsic)": ks_s_i,
        "k Solid (Scaled [1-φ])": ks_s_eff_i,
        "k Pore Fluid": fluid_state_i['k'],
        "Density Solid (True)": rho_s_i,
        "Density Bulk": rho_bulk_i,
        "Density Pore Fluid": fluid_state_i['rho'],
        "Modified Reynolds (Re_m)": Re_m_i,
        "Superficial Reynolds (Re_p)": Re_p_i,
        "Nusselt Number (Nu)": Nu_i,
        "Volumetric Heat Transfer Coeff (q_sf)": q_sf_coeff_i,
        "Total Pressure Gradient (kPa/m)": hydro_state_i['dp_total_Pa_m'] / 1000.0,
        "Viscous Drag Gradient (kPa/m)": hydro_state_i['dp_viscous_Pa_m'] / 1000.0,
        "Inertial Drag Gradient (kPa/m)": hydro_state_i['dp_inertial_Pa_m'] / 1000.0
    })

df_sweep = pd.DataFrame(sweep_records)

sweep_tab1, sweep_tab2, sweep_tab3, sweep_tab4, sweep_tab5, sweep_tab6 = st.tabs([
    "🔥 Specific Heat (Cp)",
    "🌡️ Thermal Conductivity (k)",
    "⚖️ Density (ρ)",
    "🔄 Reynolds Numbers (Re_m vs Re_p)",
    "♨️ Nusselt Number & Interphase HTC",
    "💨 Ergun Pressure Gradients (ΔP/L)"
])

with sweep_tab1:
    fig_cp = px.line(
        df_sweep, x="Temperature (K)", 
        y=["Cp Solid (Intrinsic)", "Cp Solid (Scaled [1-φ])", "Cp Pore Fluid"],
        title="Specific Heat Capacity vs. Temperature",
        labels={"value": "Specific Heat Cp [J/(kg·K)]", "variable": "Phase"}
    )
    fig_cp.update_layout(hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig_cp, use_container_width=True)

with sweep_tab2:
    fig_k = px.line(
        df_sweep, x="Temperature (K)", 
        y=["k Solid (Intrinsic)", "k Solid (Scaled [1-φ])", "k Pore Fluid"],
        title="Thermal Conductivity vs. Temperature",
        labels={"value": "Thermal Conductivity k [W/(m·K)]", "variable": "Phase"}
    )
    fig_k.update_layout(hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig_k, use_container_width=True)

with sweep_tab3:
    fig_rho = px.line(
        df_sweep, x="Temperature (K)", 
        y=["Density Solid (True)", "Density Bulk", "Density Pore Fluid"],
        title="Phase & Bulk Densities vs. Temperature",
        labels={"value": "Density ρ [kg/m³]", "variable": "Phase"}
    )
    fig_rho.update_layout(hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig_rho, use_container_width=True)

with sweep_tab4:
    fig_re = px.line(
        df_sweep, x="Temperature (K)", 
        y=["Modified Reynolds (Re_m)", "Superficial Reynolds (Re_p)"],
        title="Modified Ergun (Re_m) vs. Superficial Particle (Re_p) Reynolds Numbers",
        labels={"value": "Reynolds Number [-]", "variable": "Definition"}
    )
    fig_re.update_layout(
        hovermode="x unified", 
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_re, use_container_width=True)

with sweep_tab5:
    col_nu, col_qsf = st.columns(2)
    with col_nu:
        fig_nu = px.line(
            df_sweep, x="Temperature (K)", y="Nusselt Number (Nu)",
            title="Interphase Nusselt Number (Nu) vs. Temperature",
            labels={"Nusselt Number (Nu)": "Nusselt Number Nu [-]"}
        )
        fig_nu.update_layout(hovermode="x unified")
        st.plotly_chart(fig_nu, use_container_width=True)
    with col_qsf:
        fig_qsf = px.line(
            df_sweep, x="Temperature (K)", y="Volumetric Heat Transfer Coeff (q_sf)",
            title="Volumetric Interphase Coeff (q_sf/ΔT) vs. Temperature",
            labels={"Volumetric Heat Transfer Coeff (q_sf)": "q_sf [W/(m³·K)]"}
        )
        fig_qsf.update_layout(hovermode="x unified")
        st.plotly_chart(fig_qsf, use_container_width=True)

with sweep_tab6:
    fig_dp = px.line(
        df_sweep, x="Temperature (K)", 
        y=["Total Pressure Gradient (kPa/m)", "Viscous Drag Gradient (kPa/m)", "Inertial Drag Gradient (kPa/m)"],
        title="Ergun & Brinkman Pressure Drop Gradient (ΔP/L) vs. Temperature",
        labels={"value": "Pressure Gradient ΔP/L [kPa/m]", "variable": "Component"}
    )
    fig_dp.update_layout(hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig_dp, use_container_width=True)

# --- COMSOL Multiphysics Model Export Engine ---
st.markdown("---")
st.subheader("⚡ COMSOL Multiphysics Model Export Engine")
st.markdown("""
Copy expressions directly into your COMSOL Multiphysics model under **Global Definitions -> Parameters** or **Component -> Definitions -> Variables**.
""")

# Construct COMSOL parameter expressions
phi_eff_val = hydro_state['phi_eff']
dp_eff_val = hydro_state['dp_eff']
rhog_A, rhog_B, rhog_C, rhog_D = coeffs['rhog']
mu_A, mu_B, mu_C, mu_D = coeffs['mu']

comsol_data = [
    {"Name": "phi_eff", "Expression": f"{phi_eff_val:.4f}", "Unit": "1", "Description": "Effective bed porosity accounting for liquid holdup"},
    {"Name": "dp_eff", "Expression": f"{dp_eff_val:.5f}[m]", "Unit": "m", "Description": "Effective harmonic mean particle diameter"},
    {"Name": "rho_s", "Expression": f"{rho_s:.2f}[kg/m^3]", "Unit": "kg/m^3", "Description": "Solid matrix true density"},
    {"Name": "Cp_s", "Expression": f"({cp_A:.3f} + {cp_B:.4e}*T + {cp_C:.4e}/(T^2))[J/(kg*K)]", "Unit": "J/(kg*K)", "Description": "Intrinsic solid specific heat capacity"},
    {"Name": "Cp_s_eff", "Expression": f"Cp_s * (1 - {phi_eff_val:.4f})", "Unit": "J/(kg*K)", "Description": "LTNE scaled solid specific heat capacity"},
    {"Name": "k_s", "Expression": f"({ks_A:.3f} + {ks_B:.4e}*T + {ks_C:.4e}*(T^2))[W/(m*K)]", "Unit": "W/(m*K)", "Description": "Intrinsic solid thermal conductivity"},
    {"Name": "k_s_eff", "Expression": f"k_s * (1 - {phi_eff_val:.4f})", "Unit": "W/(m*K)", "Description": "LTNE scaled solid thermal conductivity"},
    {"Name": "rho_g", "Expression": f"({rhog_A:.3f} + {rhog_B:.4e}*T + {rhog_C:.4e}*(T^2)) * (p/(101.325[kPa]))[kg/m^3]", "Unit": "kg/m^3", "Description": "Pressure-corrected ideal gas density"},
    {"Name": "mu_g", "Expression": f"({mu_A:.4e} + {mu_B:.4e}*T)[Pa*s]", "Unit": "Pa*s", "Description": "Gas dynamic viscosity"},
    {"Name": "K_perm", "Expression": f"((phi_eff^3) * (dp_eff^2)) / (150 * ((1 - phi_eff)^2))", "Unit": "m^2", "Description": "Intrinsic bed permeability (Ergun)"},
    {"Name": "beta_F", "Expression": f"(1.75 * (1 - phi_eff)) / ((phi_eff^3) * dp_eff)", "Unit": "1/m", "Description": "Forchheimer non-Darcy drag coefficient"},
    {"Name": "a_sf", "Expression": f"(6 * (1 - phi_eff)) / dp_eff", "Unit": "1/m", "Description": "Interphase specific surface area"},
    {"Name": "h_sf", "Expression": f"({h_sf:.2f})[W/(m^2*K)]", "Unit": "W/(m^2*K)", "Description": "Interphase heat transfer coefficient (Wakao-Kaguei)"},
    {"Name": "q_sf", "Expression": f"h_sf * a_sf", "Unit": "W/(m^3*K)", "Description": "Volumetric interphase thermal coupling coefficient"},
    {"Name": "P_tuyere", "Expression": f"{p_tuyere_kPa:.1f}[kPa]", "Unit": "kPa", "Description": "Tuyere blast inlet pressure"},
    {"Name": "P_top", "Expression": f"{p_top_kPa:.1f}[kPa]", "Unit": "kPa", "Description": "Top gas exit pressure"}
]

df_comsol = pd.DataFrame(comsol_data)

# Display COMSOL Table
st.dataframe(df_comsol, use_container_width=True, hide_index=True)

# Generate downloadable CSV formatted for COMSOL Parameter Import
csv_buffer = io.StringIO()
df_comsol.to_csv(csv_buffer, index=False)

st.download_button(
    label="📥 Download COMSOL Parameters File (.csv)",
    data=csv_buffer.getvalue(),
    file_name="comsol_blast_furnace_parameters.csv",
    mime="text/csv"
)

st.code("""
% COMSOL Multiphysics Variable Snippet (Copy-Paste directly into COMSOL Definitions)
phi_eff   = " + f"{phi_eff_val:.4f}" + "
dp_eff    = " + f"{dp_eff_val:.5f}[m]" + "
K_perm    = ((phi_eff^3)*(dp_eff^2))/(150*((1-phi_eff)^2))
beta_F    = (1.75*(1-phi_eff))/((phi_eff^3)*dp_eff)
rho_g     = (" + f"{rhog_A:.3f} + {rhog_B:.4e}*T + {rhog_C:.4e}*T^2" + ")*(p/101325[Pa])
mu_g      = " + f"{mu_A:.4e} + {mu_B:.4e}*T" + "
q_sf      = h_sf * a_sf
""", language="text")
