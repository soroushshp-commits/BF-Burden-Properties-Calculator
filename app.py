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
This application computes temperature-dependent effective thermophysical properties for both the 
**Granular Zone (Dry Stack)** and the **Deadman / Lower Coke Zone** of a blast furnace, optimized for 
COMSOL Multiphysics and custom numerical transport models.
""")

# --- Helper Function for Compact Inline Number Input + Slider ---
def paired_input(label, min_val, max_val, default_val, step, key, container=st.sidebar):
    if key not in st.session_state:
        st.session_state[key] = default_val
        
    # Layout: Label + Compact Number Box in the same row, Slider below
    col_label, col_input = container.columns([3, 1.2])
    with col_label:
        container.markdown(f"**{label}**")
    with col_input:
        n_val = container.number_input(
            f"{label} num", 
            min_value=float(min_val), 
            max_value=float(max_val), 
            value=float(st.session_state[key]), 
            step=step, 
            key=f"n_{key}", 
            label_visibility="collapsed"
        )
        
    s_val = container.slider(
        f"{label} slider", 
        min_value=float(min_val), 
        max_value=float(max_val), 
        value=float(n_val), 
        step=step, 
        key=f"s_{key}", 
        label_visibility="collapsed"
    )
    
    # Sync states
    if s_val != st.session_state[key] and s_val != n_val:
        st.session_state[key] = s_val
    elif n_val != st.session_state[key]:
        st.session_state[key] = n_val
    
    return st.session_state[key]

# --- Sidebar: Zone Selection ---
st.sidebar.header("🗺️ Blast Furnace Region")
bf_zone = st.sidebar.radio(
    "Select Operating Zone",
    ["Granular Zone (Dry Burden Mix)", "Deadman / Lower Coke Zone (Coke + Melts)"]
)

# --- Sidebar: Material Property Customization ---
st.sidebar.header("🛠️ Material Database & Coefficients")

default_materials = {
    'coke': {
        'true_density': 1850.0, 'bulk_density': 480.0,
        'cp_a': 860.0, 'cp_b': 5.40e-1, 'cp_c': -2.75e7,
        'k_a': 0.28, 'k_b': 1.75e-3, 'k_c': -3.20e-7
    },
    'sinter': {
        'true_density': 3450.0, 'bulk_density': 1700.0,
        'cp_a': 745.0, 'cp_b': 2.60e-1, 'cp_c': -1.25e7,
        'k_a': 0.92, 'k_b': 0.48e-3, 'k_c': 0.85e-7
    },
    'pellet': {
        'true_density': 3350.0, 'bulk_density': 2050.0,
        'cp_a': 620.5, 'cp_b': 6.15e-1, 'cp_c': -1.18e7,
        'k_a': 1.42, 'k_b': -0.38e-3, 'k_c': 1.15e-7
    },
    'lump': {
        'true_density': 4600.0, 'bulk_density': 2200.0,
        'cp_a': 615.0, 'cp_b': 5.85e-1, 'cp_c': -1.15e7,
        'k_a': 2.15, 'k_b': -0.65e-3, 'k_c': 0.25e-7
    }
}

materials = {}
for mat_name in ['coke', 'sinter', 'pellet', 'lump']:
    with st.sidebar.expander(f"Edit {mat_name.capitalize()} Properties"):
        td = st.number_input(f"{mat_name.capitalize()} True Density (kg/m³)", value=default_materials[mat_name]['true_density'], step=50.0, key=f"{mat_name}_td")
        
        st.text("Cp Coeffs: A + B*T + C*T⁻²")
        cp_a = st.number_input(f"{mat_name} Cp - A", value=default_materials[mat_name]['cp_a'], format="%.2f", key=f"{mat_name}_cp_a")
        cp_b = st.number_input(f"{mat_name} Cp - B", value=default_materials[mat_name]['cp_b'], format="%.2e", key=f"{mat_name}_cp_b")
        cp_c = st.number_input(f"{mat_name} Cp - C", value=default_materials[mat_name]['cp_c'], format="%.2e", key=f"{mat_name}_cp_c")
        
        st.text("Thermal Conductivity Coeffs: A + B*T + C*T²")
        k_a = st.number_input(f"{mat_name} k - A", value=default_materials[mat_name]['k_a'], format="%.3f", key=f"{mat_name}_k_a")
        k_b = st.number_input(f"{mat_name} k - B", value=default_materials[mat_name]['k_b'], format="%.2e", key=f"{mat_name}_k_b")
        k_c = st.number_input(f"{mat_name} k - C", value=default_materials[mat_name]['k_c'], format="%.2e", key=f"{mat_name}_k_c")
        
        materials[mat_name] = {
            'true_density': td,
            'cp_coeffs': (cp_a, cp_b, cp_c),
            'k_coeffs': (k_a, k_b, k_c)
        }

# --- Sidebar: Operating Conditions & Inputs ---
st.sidebar.header("⚙️ Operating Conditions")
temperature_k = paired_input("Operating Temperature (K)", 0.0, 3000.0, 1600.0 if "Deadman" in bf_zone else 1000.0, 10.0, "temp_k")

mass_fractions = {}
if "Granular" in bf_zone:
    st.sidebar.subheader("Granular Burden Structure (%)")
    coke_p = paired_input("Coke (%)", 0.0, 100.0, 20.0, 1.0, "coke_p")
    sinter_p = paired_input("Sinter (%)", 0.0, 100.0, 35.0, 1.0, "sinter_p")
    pellet_p = paired_input("Pellet (%)", 0.0, 100.0, 30.0, 1.0, "pellet_p")
    lump_p = paired_input("Lump Ore (%)", 0.0, 100.0, 15.0, 1.0, "lump_p")
    
    total_p = coke_p + sinter_p + pellet_p + lump_p
    if total_p == 0: total_p = 1.0
    mass_fractions = {
        'coke': coke_p / total_p,
        'sinter': sinter_p / total_p,
        'pellet': pellet_p / total_p,
        'lump': lump_p / total_p
    }
else:
    st.sidebar.info("Deadman Zone consists of 100% packed Coke skeleton saturated with trickling liquid melts.")
    mass_fractions = {'coke': 1.0, 'sinter': 0.0, 'pellet': 0.0, 'lump': 0.0}

with st.sidebar.expander("Advanced Bed & Void Settings") as adv_exp:
    bed_void_fraction = paired_input("Bed Void Fraction (ϕ)", 0.0, 1.0, 0.35 if "Deadman" in bf_zone else 0.40, 0.01, "phi_val", container=adv_exp)
    
    if "Deadman" in bf_zone:
        liquid_holdup = paired_input("Liquid Melt Saturation", 0.0, 1.0, 0.35, 0.01, "liq_hold", container=adv_exp)
    else:
        liquid_holdup = 0.0
        
    mean_particle_diameter = paired_input("Mean Particle Diameter (m)", 0.0, 1.0, 0.04 if "Deadman" in bf_zone else 0.025, 0.001, "dp_val", container=adv_exp)
    gas_conductivity = paired_input("Gas Conductivity (W/m·K)", 0.0, 1.0, 0.04, 0.005, "kg_val", container=adv_exp)

# --- Calculation Engine ---
def calculate_thermophysics(mass_fractions, T, kg, dp, phi, liq_holdup, materials, zone_type):
    cp_eff = 0.0
    cp_A_eff, cp_B_eff, cp_C_eff = 0.0, 0.0, 0.0
    for mat, w in mass_fractions.items():
        if w > 0:
            A, B, C = materials[mat]['cp_coeffs']
            cp_A_eff += w * A
            cp_B_eff += w * B
            cp_C_eff += w * C
            cp_eff += w * (A + B * T + C * (T ** -2))
            
    if "Deadman" in zone_type:
        cp_liquid_avg = 850.0 
        cp_eff = (1.0 - liq_holdup) * cp_eff + liq_holdup * cp_liquid_avg

    active_mats = {mat: w for mat, w in mass_fractions.items() if w > 0}
    volumes = {mat: w / materials[mat]['true_density'] for mat, w in active_mats.items()}
    total_vol = sum(volumes.values())
    vol_fractions = {mat: v / total_vol for mat, v in volumes.items()}
    
    ks_eff = 0.0
    ks_A_eff, ks_B_eff, ks_C_eff = 0.0, 0.0, 0.0
    for mat, x_v in vol_fractions.items():
        A, B, C = materials[mat]['k_coeffs']
        ks_A_eff += x_v * A
        ks_B_eff += x_v * B
        ks_C_eff += x_v * C
        ks_eff += x_v * (A + B * T + C * (T ** 2))
    
    rho_solid_avg = sum(vol_fractions[mat] * materials[mat]['true_density'] for mat in active_mats)
    rho_bed_effective = (1.0 - phi) * rho_solid_avg
    
    if "Deadman" in zone_type:
        rho_liq_avg = 6500.0
        rho_bed_effective = (1.0 - phi) * rho_solid_avg + phi * liq_holdup * rho_liq_avg

    sigma = 5.67e-8
    emissivity = 0.88 if "Deadman" not in zone_type else 0.92
    alpha_yk, gamma_yk, beta_yk = 0.8, 0.95, 0.95
    
    conduction_term = kg * (phi + ((1.0 - phi) / ((alpha_yk * (kg / ks_eff)) + gamma_yk)))
    radiation_term = 4.0 * beta_yk * emissivity * sigma * dp * (T ** 3)
    k_bed_effective = conduction_term + radiation_term
    
    formula_coeffs = {
        'cp': (cp_A_eff, cp_B_eff, cp_C_eff),
        'ks': (ks_A_eff, ks_B_eff, ks_C_eff)
    }
    
    return cp_eff, ks_eff, k_bed_effective, rho_bed_effective, rho_solid_avg, formula_coeffs

cp_eff, ks_eff, k_bed_effective, rho_bed_effective, rho_solid_avg, formula_coeffs = calculate_thermophysics(
    mass_fractions, temperature_k, gas_conductivity, mean_particle_diameter, bed_void_fraction, liquid_holdup, materials, bf_zone
)

# --- Display Results ---
st.markdown("---")
st.subheader(f"📊 Homogenized Parameters for: {bf_zone}")

col1, col2 = st.columns(2)

with col1:
    st.metric(label=f"Effective Specific Heat (Cp) at {temperature_k} K", value=f"{cp_eff:.2f} J/(kg·K)")
    st.metric(label="Effective Bulk Density (ρ_bed)", value=f"{rho_bed_effective:.2f} kg/m³")
    if "Deadman" in bf_zone:
        st.metric(label="Liquid Melt Holdup in Pores", value=f"{liquid_holdup*100:.1f}%")
    else:
        st.metric(label="Solid Skeleton Density (ρ_solid)", value=f"{rho_solid_avg:.2f} kg/m³")

with col2:
    st.metric(label=f"Packed Bed Effective Conductivity (k_eff) at {temperature_k} K", value=f"{k_bed_effective:.3f} W/(m·K)")
    st.metric(label=f"Equivalent Solid Conductivity (ks) at {temperature_k} K", value=f"{ks_eff:.3f} W/(m·K)")
    st.metric(label="Bed Void Fraction (ϕ)", value=f"{bed_void_fraction:.2f}")

# --- Analytical Formulas Display ---
st.markdown("---")
st.subheader("📐 Analytical Equations for COMSOL / Numerical Implementation")

cp_A, cp_B, cp_C = formula_coeffs['cp']
ks_A, ks_B, ks_C = formula_coeffs['ks']

st.markdown(f"""
Based on your region selection (**{bf_zone}**), the active thermophysical functions are:

1. **Effective Specific Heat Capacity $C_{{p,eff}}(T)$**:
   $$C_{{p,eff}}(T) = {cp_A:.3f} + ({cp_B:.3e}) \cdot T + ({cp_C:.3e}) \cdot T^{{-2}} \\;\\; \text{{[J/(kg·K)]}}$$

2. **Equivalent Solid/Skeleton Thermal Conductivity $k_{{s,eff}}(T)$**:
   $$k_{{s,eff}}(T) = {ks_A:.3f} + ({ks_B:.3e}) \cdot T + ({ks_C:.3e}) \cdot T^2 \\;\\; \text{{[W/(m·K)]}}$$

3. **Effective Bulk Density $\\rho_{{bed}}$**:
   $$\\rho_{{bed}} = {rho_bed_effective:.2f} \\;\\; \text{{[kg/m³]}}$$

4. **Packed Bed Effective Thermal Conductivity $k_{{eff}}(T)$**:
   $$k_{{eff}}(T) = {gas_conductivity} \cdot \left({bed_void_fraction} + \frac{{1 - {bed_void_fraction}}}{{0.8 \cdot \frac{{{gas_conductivity}}}{{{ks_eff:.4f}}} + 0.95}}\right) + 4 \cdot 0.95 \cdot \epsilon \cdot \sigma \cdot {mean_particle_diameter} \cdot T^3$$
""")

# Visual Breakdown Chart
st.markdown("---")
st.subheader("📋 Zone Composition Breakdown")
chart_data = {mat.capitalize(): [w * 100] for mat, w in mass_fractions.items()}
st.bar_chart(chart_data)
