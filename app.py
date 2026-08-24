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
This application computes temperature-dependent thermophysical properties. 
**Upgrades:** Features customizable polynomial coefficients, true gas-solid mixture effective heat capacity ($C_{p,eff}$), and explicit temperature-dependent COMSOL functions.
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

# --- Sidebar: Zone & Input Method Selection ---
st.sidebar.header("🗺️ Blast Furnace Region")
bf_zone = st.sidebar.radio("Select Operating Zone", ["Granular Zone (Dry Burden Mix)", "Deadman / Lower Coke Zone (Coke + Melts)"])

st.sidebar.header("⚖️ Input Method")
input_method = st.sidebar.radio("Choose Primary Input", ["Mass-based (kg)", "Volume-based (m³)"])

# --- Sidebar: Material Properties (Densities, Quantities & Coefficients) ---
st.sidebar.header("🛠️ Material Database & Coefficients")

default_materials = {
    'coke': {'td': 1850.0, 'bd': 480.0, 'mass': 960.0, 'vol': 2.0, 'cpa': 860.0, 'cpb': 5.40e-1, 'cpc': -2.75e7, 'ka': 0.28, 'kb': 1.75e-3, 'kc': -3.20e-7},
    'sinter': {'td': 3450.0, 'bd': 1700.0, 'mass': 5950.0, 'vol': 3.5, 'cpa': 745.0, 'cpb': 2.60e-1, 'cpc': -1.25e7, 'ka': 0.92, 'kb': 0.48e-3, 'kc': 0.85e-7},
    'pellet': {'td': 3350.0, 'bd': 2050.0, 'mass': 6150.0, 'vol': 3.0, 'cpa': 620.5, 'cpb': 6.15e-1, 'cpc': -1.18e7, 'ka': 1.42, 'kb': -0.38e-3, 'kc': 1.15e-7},
    'lump': {'td': 4600.0, 'bd': 2200.0, 'mass': 3300.0, 'vol': 1.5, 'cpa': 615.0, 'cpb': 5.85e-1, 'cpc': -1.15e7, 'ka': 2.15, 'kb': -0.65e-3, 'kc': 0.25e-7}
}

active_mats = ['coke', 'sinter', 'pellet', 'lump'] if "Granular" in bf_zone else ['coke']

materials = {}
masses = {}
volumes = {}

for mat in active_mats:
    with st.sidebar.expander(f"{mat.capitalize()} Configuration", expanded=(mat == 'coke')):
        st.markdown("**Densities & Quantities**")
        td = st.number_input(f"True Density (kg/m³)", value=default_materials[mat]['td'], step=50.0, key=f"{mat}_td")
        bd = st.number_input(f"Bulk Density (kg/m³)", value=default_materials[mat]['bd'], step=50.0, key=f"{mat}_bd")
        
        if input_method == "Mass-based (kg)":
            m = st.number_input(f"Mass (kg)", value=default_materials[mat]['mass'], step=50.0, key=f"{mat}_m")
            v = m / bd if bd > 0 else 0.0
            st.caption(f"Calculated Bulk Volume: {v:.2f} m³")
        else:
            v = st.number_input(f"Bulk Volume (m³)", value=default_materials[mat]['vol'], step=0.1, key=f"{mat}_v")
            m = v * bd
            st.caption(f"Calculated Mass: {m:.2f} kg")
            
        masses[mat] = m
        volumes[mat] = v
        
        st.markdown("**Cp Polynomial (A + B*T + C*T⁻²)**")
        c1, c2, c3 = st.columns(3)
        cpa = c1.number_input("A", value=default_materials[mat]['cpa'], format="%.1f", key=f"{mat}_cpa")
        cpb = c2.number_input("B", value=default_materials[mat]['cpb'], format="%.3e", key=f"{mat}_cpb")
        cpc = c3.number_input("C", value=default_materials[mat]['cpc'], format="%.3e", key=f"{mat}_cpc")
        
        st.markdown("**k Polynomial (A + B*T + C*T²)**")
        k1, k2, k3 = st.columns(3)
        ka = k1.number_input("A", value=default_materials[mat]['ka'], format="%.2f", key=f"{mat}_ka")
        kb = k2.number_input("B", value=default_materials[mat]['kb'], format="%.3e", key=f"{mat}_kb")
        kc = k3.number_input("C", value=default_materials[mat]['kc'], format="%.3e", key=f"{mat}_kc")

        materials[mat] = {'true_density': td, 'bulk_density': bd, 'cp_coeffs': (cpa, cpb, cpc), 'k_coeffs': (ka, kb, kc)}

for mat in ['sinter', 'pellet', 'lump']:
    if mat not in active_mats:
        masses[mat] = 0.0
        volumes[mat] = 0.0
        materials[mat] = {'true_density': 1.0, 'bulk_density': 1.0, 'cp_coeffs': (0,0,0), 'k_coeffs': (0,0,0)}

# --- Advanced Settings (Gas and Particle Properties) ---
st.sidebar.header("💨 Gas Flow & LTNE Properties")
temperature_k = paired_input("Bed Temp Evaluation (K)", 273.15, 2000.0, 1000.0, 10.0, "temp_k", fmt="%.1f")
vg = paired_input("Superficial Gas Velocity (m/s)", 0.1, 5.0, 1.5, 0.1, "vg_val")
rho_g = paired_input("Gas Density (kg/m³)", 0.1, 2.0, 0.45, 0.05, "rho_g_val")
mu_g = paired_input("Gas Viscosity (x10⁻⁵ Pa·s)", 1.0, 10.0, 4.5, 0.1, "mu_g_val") * 1e-5
cp_g = paired_input("Gas Specific Heat (J/kg·K)", 500.0, 2500.0, 1150.0, 10.0, "cp_g_val")
gas_conductivity = paired_input("Gas Conductivity (W/m·K)", 0.01, 0.2, 0.04, 0.005, "kg_val")
mean_particle_diameter = paired_input("Particle Diameter (m)", 0.01, 0.1, 0.04 if "Deadman" in bf_zone else 0.025, 0.001, "dp_val")

# --- Calculations ---
total_volume = sum(volumes.values()) or 1.0
total_mass = sum(masses.values()) or 1.0
mass_fractions = {mat: m / total_mass for mat, m in masses.items()}

weighted_void_sum = sum(vol * (1.0 - (materials[mat]['bulk_density'] / materials[mat]['true_density'])) for mat, vol in volumes.items() if materials[mat]['true_density'] > 0)
phi = weighted_void_sum / total_volume

def calculate_physics(T):
    # 1. Pure Solid Property Blending
    cp_A, cp_B, cp_C = 0.0, 0.0, 0.0
    ks_A, ks_B, ks_C = 0.0, 0.0, 0.0
    rho_s = 0.0
    
    active = {m: w for m, w in mass_fractions.items() if w > 0}
    v_solid = {m: w / materials[m]['true_density'] for m, w in active.items()}
    v_tot = sum(v_solid.values())
    vol_fracs = {m: v / v_tot for m, v in v_solid.items()} if v_tot > 0 else {}
    
    for m, w in active.items():
        A, B, C = materials[m]['cp_coeffs']
        cp_A += w * A; cp_B += w * B; cp_C += w * C
        
    for m, x in vol_fracs.items():
        A, B, C = materials[m]['k_coeffs']
        ks_A += x * A; ks_B += x * B; ks_C += x * C
        rho_s += x * materials[m]['true_density']

    # Evaluate pure solid at evaluation temp
    cp_s = cp_A + cp_B * T + cp_C * (T ** -2) if T > 0 else 0
    ks_s = ks_A + ks_B * T + ks_C * (T ** 2)

    # 2. Homogenized Bed Properties (True Mixture)
    rho_bed = (1.0 - phi) * rho_s + phi * rho_g
    
    # Scale solid and gas contributions for true Cp_eff polynomial
    M_s = ((1.0 - phi) * rho_s) / rho_bed if rho_bed > 0 else 0
    M_g = (phi * rho_g) / rho_bed if rho_bed > 0 else 0
    
    cpeff_A = M_s * cp_A + M_g * cp_g
    cpeff_B = M_s * cp_B
    cpeff_C = M_s * cp_C
    cp_bed = cpeff_A + cpeff_B * T + cpeff_C * (T ** -2) if T > 0 else 0
    
    emissivity = 0.92 if "Deadman" in bf_zone else 0.88
    sigma = 5.67e-8
    
    # Bounded Radiation Model evaluation
    k_rad = 4.0 * emissivity * sigma * mean_particle_diameter * (T ** 3)
    k_gap = gas_conductivity + k_rad 
    k_series = (1.0 - phi) / ((1.0 / ks_s) + (1.0 / k_gap)) if (ks_s > 0 and k_gap > 0) else 0.0
    k_parallel = phi * gas_conductivity
    k_bed = k_series + k_parallel

    # 3. Interphase Heat Transfer
    Re = (rho_g * vg * mean_particle_diameter) / mu_g if mu_g > 0 else 0
    Pr = (cp_g * mu_g) / gas_conductivity if gas_conductivity > 0 else 0
    Nu = 2.0 + 1.1 * (Pr ** (1/3)) * (Re ** 0.6)
    
    h_sf = (Nu * gas_conductivity) / mean_particle_diameter if mean_particle_diameter > 0 else 0
    a_sf = (6.0 * (1.0 - phi)) / mean_particle_diameter if mean_particle_diameter > 0 else 0
    q_sf_coeff = h_sf * a_sf

    coeffs = {
        'cp_s': (cp_A, cp_B, cp_C), 
        'ks': (ks_A, ks_B, ks_C), 
        'cp_eff': (cpeff_A, cpeff_B, cpeff_C)
    }
    return (cp_s, ks_s, rho_s), (cp_bed, k_bed, rho_bed), (Re, Pr, Nu, h_sf, a_sf, q_sf_coeff), coeffs, emissivity

(cp_s, ks_s, rho_s), (cp_bed, k_bed, rho_bed), interphase, coeffs, emissivity_val = calculate_physics(temperature_k)
Re, Pr, Nu, h_sf, a_sf, q_sf_coeff = interphase

# --- Display Results ---
st.markdown("---")
st.subheader(f"📊 Evaluated Output at Reference T = {temperature_k:.1f} K (ϕ = {phi:.4f})")

tab1, tab2, tab3 = st.tabs([
    "🟢 COMSOL LTNE: Solid Domain", 
    "🔵 COMSOL Standard: True Homogenized Mixture",
    "⚙️ Interphase & Fluid Dynamics"
])

with tab1:
    st.info("Uses **True Solid** values. Independent of void fraction scaling.")
    st.metric("Solid Matrix Density (ρ_s)", f"{rho_s:.2f} kg/m³")
    
    st.markdown("#### Temperature-Dependent Functions")
    st.latex(rf"Cp_s(T) = {coeffs['cp_s'][0]:.2f} + ({coeffs['cp_s'][1]:.2e}) \cdot T + ({coeffs['cp_s'][2]:.2e}) \cdot T^{{-2}}")
    st.latex(rf"k_s(T) = {coeffs['ks'][0]:.3f} + ({coeffs['ks'][1]:.2e}) \cdot T + ({coeffs['ks'][2]:.2e}) \cdot T^2")

with tab2:
    st.info("Uses **True Mixture** values. Accounts for total domain mass ($M_s + M_g$) and structural thermal bottlenecks.")
    st.metric("Mixture Effective Density (ρ_bed)", f"{rho_bed:.2f} kg/m³")
    
    st.markdown("#### True Effective Heat Capacity Function")
    st.latex(rf"Cp_{{eff}}(T) = {coeffs['cp_eff'][0]:.2f} + ({coeffs['cp_eff'][1]:.2e}) \cdot T + ({coeffs['cp_eff'][2]:.2e}) \cdot T^{{-2}}")
    
    st.markdown("#### Bounded Effective Conductivity Function")
    st.latex(rf"k_{{gap}}(T) = {gas_conductivity} + 4(0.88)\sigma d_p T^3")
    st.latex(rf"k_{{eff}}(T) = \frac{{{1.0 - phi:.4f}}}{{\frac{{1}}{{k_s(T)}} + \frac{{1}}{{k_{{gap}}(T)}}}} + {phi * gas_conductivity:.4f}")

with tab3:
    col1, col2, col3 = st.columns(3)
    col1.metric("Reynolds Number (Re)", f"{Re:.1f}")
    col2.metric("Prandtl Number (Pr)", f"{Pr:.3f}")
    col3.metric("Nusselt Number (Nu)", f"{Nu:.2f}")
    
    st.markdown("#### Interphase Coupling Function")
    st.latex(rf"q_{{sf}}(T_f, T_s) = a_{{sf}} h_{{sf}} (T_f - T_s)")
    st.latex(rf"q_{{sf}}(T_f, T_s) = {q_sf_coeff:.2f} \cdot (T_f - T_s)")

# --- COMSOL Text Export Content Generator ---
comsol_text = f"""====================================================================
BLAST FURNACE THERMOPHYSICAL MODEL EXPORT (COMSOL MULTIPHYSICS)
Bed Porosity (phi): {phi:.4f}
====================================================================

--------------------------------------------------------------------
1. HEAT TRANSFER IN POROUS MEDIA (LTNE)
--------------------------------------------------------------------
[Solid Matrix Properties]
rho_s = {rho_s:.2f} [kg/m^3]

[Analytic Function: Cp_s(T)]
Expression: {coeffs['cp_s'][0]:.6f} + ({coeffs['cp_s'][1]:.6e})*T + ({coeffs['cp_s'][2]:.6e})*T^(-2)

[Analytic Function: k_s(T)]
Expression: {coeffs['ks'][0]:.6f} + ({coeffs['ks'][1]:.6e})*T + ({coeffs['ks'][2]:.6e})*T^2

[Interphase Heat Transfer Coupling]
a_sf = {a_sf:.2f} [m^2/m^3]
h_sf = {h_sf:.2f} [W/(m^2*K)]
Function q_sf(T_f, T_s) = {q_sf_coeff:.2f} * (T_f - T_s) [W/m^3]

--------------------------------------------------------------------
2. HOMOGENIZED BED MODEL (SINGLE DOMAIN)
--------------------------------------------------------------------
[Global Parameters]
rho_bed = {rho_bed:.2f} [kg/m^3]

[Analytic Function: Cp_eff(T)]
Expression: {coeffs['cp_eff'][0]:.6f} + ({coeffs['cp_eff'][1]:.6e})*T + ({coeffs['cp_eff'][2]:.6e})*T^(-2)

[Analytic Function: k_eff(T) - Bounded Series-Parallel Model]
Variables to define in COMSOL:
  k_gap(T) = {gas_conductivity} + 4*{emissivity_val}*5.67e-8*{mean_particle_diameter}*T^3
Expression: 
  ((1 - {phi:.4f}) / (1/k_s(T) + 1/k_gap(T))) + ({phi:.4f} * {gas_conductivity})

====================================================================
"""

st.download_button(
    label="📥 Download Updated COMSOL Variables (.txt)",
    data=comsol_text,
    file_name=f"COMSOL_BF_Properties_Corrected.txt",
    mime="text/plain"
)
