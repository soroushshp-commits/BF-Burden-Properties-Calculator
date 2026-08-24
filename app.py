import streamlit as st
import numpy as np

# Page Configuration
st.set_page_config(
    page_title="Blast Furnace Burden & Deadman Thermophysical Simulator",
    page_icon="🔥",
    layout="wide"
)

st.title("🔥 Blast Furnace Multi-Zone Thermophysical Simulator")
st.markdown("""
This application computes temperature-dependent thermophysical properties for the blast furnace. 
**Correction Applied:** The effective thermal conductivity ($k_{eff}$) now uses a strictly bounded series-parallel resistance model to ensure it cannot physically exceed the solid conductivity ($k_s$). 
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

# --- Sidebar: Material Property Customization ---
st.sidebar.header("🛠️ Solid Material Database")
default_materials = {
    'coke': {'td': 1850.0, 'bd': 480.0, 'cpa': 860.0, 'cpb': 5.40e-1, 'cpc': -2.75e7, 'ka': 0.28, 'kb': 1.75e-3, 'kc': -3.20e-7},
    'sinter': {'td': 3450.0, 'bd': 1700.0, 'cpa': 745.0, 'cpb': 2.60e-1, 'cpc': -1.25e7, 'ka': 0.92, 'kb': 0.48e-3, 'kc': 0.85e-7},
    'pellet': {'td': 3350.0, 'bd': 2050.0, 'cpa': 620.5, 'cpb': 6.15e-1, 'cpc': -1.18e7, 'ka': 1.42, 'kb': -0.38e-3, 'kc': 1.15e-7},
    'lump': {'td': 4600.0, 'bd': 2200.0, 'cpa': 615.0, 'cpb': 5.85e-1, 'cpc': -1.15e7, 'ka': 2.15, 'kb': -0.65e-3, 'kc': 0.25e-7}
}

materials = {}
for mat in ['coke', 'sinter', 'pellet', 'lump']:
    td, bd = default_materials[mat]['td'], default_materials[mat]['bd']
    cpa, cpb, cpc = default_materials[mat]['cpa'], default_materials[mat]['cpb'], default_materials[mat]['cpc']
    ka, kb, kc = default_materials[mat]['ka'], default_materials[mat]['kb'], default_materials[mat]['kc']
    materials[mat] = {'true_density': td, 'bulk_density': bd, 'cp_coeffs': (cpa, cpb, cpc), 'k_coeffs': (ka, kb, kc)}

# --- Sidebar: Input Method Selection & Material Inputs ---
st.sidebar.header("⚖️ Burden Proportions")
coke_m = st.sidebar.number_input("Coke Mass (kg)", value=960.0, step=50.0)
sinter_m = st.sidebar.number_input("Sinter Mass (kg)", value=5950.0 if "Granular" in bf_zone else 0.0, step=50.0)
pellet_m = st.sidebar.number_input("Pellet Mass (kg)", value=6150.0 if "Granular" in bf_zone else 0.0, step=50.0)
lump_m = st.sidebar.number_input("Lump Ore Mass (kg)", value=3300.0 if "Granular" in bf_zone else 0.0, step=50.0)

masses = {'coke': coke_m, 'sinter': sinter_m, 'pellet': pellet_m, 'lump': lump_m}
volumes = {mat: m / materials[mat]['bulk_density'] if materials[mat]['bulk_density'] > 0 else 0 for mat, m in masses.items()}

# --- Advanced Settings (Gas and Particle Properties) ---
st.sidebar.header("💨 Gas Flow & LTNE Properties")
temperature_k = paired_input("Bed Temp (K)", 273.15, 2000.0, 1600.0 if "Deadman" in bf_zone else 1000.0, 10.0, "temp_k", fmt="%.1f")
vg = paired_input("Superficial Gas Velocity (m/s)", 0.1, 5.0, 1.5, 0.1, "vg_val")
rho_g = paired_input("Gas Density (kg/m³)", 0.1, 2.0, 0.45, 0.05, "rho_g_val")
mu_g = paired_input("Gas Viscosity (x10⁻⁵ Pa·s)", 1.0, 10.0, 4.5, 0.1, "mu_g_val") * 1e-5
cp_g = paired_input("Gas Specific Heat (J/kg·K)", 500.0, 2500.0, 1150.0, 10.0, "cp_g_val")
gas_conductivity = paired_input("Gas Conductivity (W/m·K)", 0.01, 0.2, 0.04, 0.005, "kg_val")
mean_particle_diameter = paired_input("Particle Diameter (m)", 0.01, 0.1, 0.04 if "Deadman" in bf_zone else 0.025, 0.001, "dp_val")

# --- Void Fraction & Mass Fractions Calculations ---
total_volume = sum(volumes.values()) or 1.0
total_mass = sum(masses.values()) or 1.0
mass_fractions = {mat: m / total_mass for mat, m in masses.items()}

weighted_void_sum = sum(vol * (1.0 - (materials[mat]['bulk_density'] / materials[mat]['true_density'])) for mat, vol in volumes.items())
phi = weighted_void_sum / total_volume

# --- Physics Calculation Engine ---
def calculate_physics(T):
    # 1. Pure Solid Properties
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

    # 2. Homogenized Bed Properties & Bounded Conductivity
    rho_bed = (1.0 - phi) * rho_s
    cp_bed = cp_s # Mass basis equality
    
    emissivity = 0.92 if "Deadman" in bf_zone else 0.88
    sigma = 5.67e-8
    
    # BOUNDED RADIATION MODEL
    k_rad = 4.0 * emissivity * sigma * mean_particle_diameter * (T ** 3)
    k_gap = gas_conductivity + k_rad 
    
    # Series path: Heat must travel through the solid and the gap sequentially
    if ks_s > 0 and k_gap > 0:
        k_series = (1.0 - phi) / ((1.0 / ks_s) + (1.0 / k_gap))
    else:
        k_series = 0.0
        
    # Parallel path: Gas conduction only (radiation is blocked by staggering)
    k_parallel = phi * gas_conductivity
    k_bed = k_series + k_parallel

    # 3. Interphase Heat Transfer (Wakao and Kaguei)
    Re = (rho_g * vg * mean_particle_diameter) / mu_g if mu_g > 0 else 0
    Pr = (cp_g * mu_g) / gas_conductivity if gas_conductivity > 0 else 0
    Nu = 2.0 + 1.1 * (Pr ** (1/3)) * (Re ** 0.6)
    
    h_sf = (Nu * gas_conductivity) / mean_particle_diameter if mean_particle_diameter > 0 else 0
    a_sf = (6.0 * (1.0 - phi)) / mean_particle_diameter if mean_particle_diameter > 0 else 0
    q_sf_coeff = h_sf * a_sf

    coeffs = {'cp': (cp_A, cp_B, cp_C), 'ks': (ks_A, ks_B, ks_C)}
    return (cp_s, ks_s, rho_s), (cp_bed, k_bed, rho_bed), (Re, Pr, Nu, h_sf, a_sf, q_sf_coeff), coeffs

(cp_s, ks_s, rho_s), (cp_bed, k_bed, rho_bed), interphase, coeffs = calculate_physics(temperature_k)
Re, Pr, Nu, h_sf, a_sf, q_sf_coeff = interphase
cp_A, cp_B, cp_C = coeffs['cp']
ks_A, ks_B, ks_C = coeffs['ks']

# --- Display Results ---
st.markdown("---")
st.subheader(f"📊 Computed Properties at T = {temperature_k:.1f} K (ϕ = {phi:.4f})")

tab1, tab2, tab3 = st.tabs([
    "🟢 COMSOL LTNE: Solid & Interphase", 
    "🔵 COMSOL Standard: Homogenized Bed",
    "⚙️ Fluid Dynamics (Dimensionless)"
])

with tab1:
    st.info("💡 **For Heat Transfer in Porous Media (LTNE).** Notice how $k_s$ remains the strict upper bound.")
    col1, col2, col3 = st.columns(3)
    col1.metric("Solid Density (ρ_s)", f"{rho_s:.2f} kg/m³")
    col2.metric("Solid Conductivity (k_s)", f"{ks_s:.3f} W/(m·K)")
    col3.metric("Solid Heat Capacity (Cp_s)", f"{cp_s:.2f} J/(kg·K)")
    
    st.markdown("#### Interphase Coupling (Gas-Solid)")
    col4, col5, col6 = st.columns(3)
    col4.metric("Specific Surface Area (a_sf)", f"{a_sf:.1f} m²/m³")
    col5.metric("Interphase HTC (h_sf)", f"{h_sf:.2f} W/(m²·K)")
    col6.metric("Volumetric Transfer Coeff (a·h)", f"{q_sf_coeff:.1f} W/(m³·K)")

with tab2:
    st.info("💡 **For standard Single-Phase Heat Transfer.** Bounded Series-Parallel formulation applied.")
    col1, col2, col3 = st.columns(3)
    col1.metric("Bulk Bed Density (ρ_bed)", f"{rho_bed:.2f} kg/m³")
    col2.metric("Bed Effective Conductivity (k_eff)", f"{k_bed:.3f} W/(m·K)")
    col3.metric("Bed Heat Capacity (Cp_bed)", f"{cp_bed:.2f} J/(kg·K)")

with tab3:
    col1, col2, col3 = st.columns(3)
    col1.metric("Reynolds Number (Re)", f"{Re:.1f}")
    col2.metric("Prandtl Number (Pr)", f"{Pr:.3f}")
    col3.metric("Nusselt Number (Nu)", f"{Nu:.2f}")

# --- COMSOL Text Export Content Generator ---
emissivity_val = 0.92 if "Deadman" in bf_zone else 0.88
comsol_text = f"""====================================================================
BLAST FURNACE THERMOPHYSICAL MODEL EXPORT (COMSOL MULTIPHYSICS)
Operating Temperature: {temperature_k:.2f} K | Porosity: {phi:.4f}
====================================================================

--------------------------------------------------------------------
1. HEAT TRANSFER IN POROUS MEDIA (LTNE)
--------------------------------------------------------------------
[Solid Properties]
rho_s = {rho_s:.2f} [kg/m^3]

Analytic Function (Cp_s):
  Expression: {cp_A:.6f} + ({cp_B:.6e})*T + ({cp_C:.6e})*T^(-2)

Analytic Function (k_s):
  Expression: {ks_A:.6f} + ({ks_B:.6e})*T + ({ks_C:.6e})*T^2

[Interphase Heat Transfer Coupling]
a_sf = {a_sf:.2f} [m^2/m^3]
h_sf = {h_sf:.2f} [W/(m^2*K)]
Volumetric Coupling (q_sf) = {q_sf_coeff:.2f} * (T_fluid - T_solid) [W/m^3]

--------------------------------------------------------------------
2. HOMOGENIZED BED MODEL (SINGLE DOMAIN)
--------------------------------------------------------------------
[Global Parameters]
rho_bed = {rho_bed:.2f} [kg/m^3]

Analytic Function (k_eff - Bounded Series-Parallel Model):
  Variables: 
    k_gap = {gas_conductivity} + 4*{emissivity_val}*5.67e-8*{mean_particle_diameter}*T^3
  Expression: 
    ((1 - {phi:.4f}) / (1/k_s(T) + 1/k_gap)) + ({phi:.4f} * {gas_conductivity})

====================================================================
"""

st.download_button(
    label="📥 Download Updated COMSOL Variables (.txt)",
    data=comsol_text,
    file_name=f"COMSOL_BF_Properties_Corrected.txt",
    mime="text/plain"
)
