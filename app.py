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
This application computes temperature-dependent thermophysical properties for both the 
**Granular Zone (Dry Stack)** and the **Deadman / Lower Coke Zone** of a blast furnace. 
Outputs are divided for **COMSOL Porous Media Nodes** (pure solid phase) and **Standard Domains** (homogenized bed).
""")

# --- Helper Function: Synchronized Slider + Number Input via Callbacks ---
def paired_input(label, min_val, max_val, default_val, step, key, container=st.sidebar):
    val_key = f"val_{key}"
    num_key = f"num_{key}"
    slider_key = f"slider_{key}"

    if val_key not in st.session_state:
        st.session_state[val_key] = float(default_val)
    if num_key not in st.session_state:
        st.session_state[num_key] = float(default_val)
    if slider_key not in st.session_state:
        st.session_state[slider_key] = float(default_val)

    def update_from_num():
        st.session_state[slider_key] = st.session_state[num_key]
        st.session_state[val_key] = st.session_state[num_key]

    def update_from_slider():
        st.session_state[num_key] = st.session_state[slider_key]
        st.session_state[val_key] = st.session_state[slider_key]

    col_label, col_input = container.columns([3, 1.2])
    with col_label:
        container.markdown(f"**{label}**")
    with col_input:
        container.number_input(
            f"{label} num", 
            min_value=float(min_val), 
            max_value=float(max_val), 
            step=float(step), 
            key=num_key, 
            on_change=update_from_num,
            label_visibility="collapsed"
        )
        
    container.slider(
        f"{label} slider", 
        min_value=float(min_val), 
        max_value=float(max_val), 
        step=float(step), 
        key=slider_key, 
        on_change=update_from_slider,
        label_visibility="collapsed"
    )
    
    return st.session_state[val_key]

# --- Sidebar: Zone Selection ---
st.sidebar.header("🗺️ Blast Furnace Region")
bf_zone = st.sidebar.radio(
    "Select Operating Zone",
    ["Granular Zone (Dry Burden Mix)", "Deadman / Lower Coke Zone (Coke + Melts)"]
)

# --- Sidebar: Material Property Customization ---
st.sidebar.header("🛠️ Material Database & Densities")

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
        bd = st.number_input(f"{mat_name.capitalize()} Bulk Density (kg/m³)", value=default_materials[mat_name]['bulk_density'], step=50.0, key=f"{mat_name}_bd")
        
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
            'bulk_density': bd,
            'cp_coeffs': (cp_a, cp_b, cp_c),
            'k_coeffs': (k_a, k_b, k_c)
        }

# --- Sidebar: Input Method Selection & Material Inputs ---
st.sidebar.header("⚖️ Burden Material Inputs")

input_method = st.sidebar.radio(
    "Choose Input Method",
    ["Volume-based (m³)", "Mass-based (kg)"]
)

st.sidebar.header("⚙️ Operating Conditions")
temperature_k = paired_input("Operating Temperature (K)", 273.15, 1800.0, 1600.0 if "Deadman" in bf_zone else 1000.0, 10.0, "temp_k")

volumes = {}
masses = {}

if "Granular" in bf_zone:
    st.sidebar.subheader("Granular Burden Proportions")
    if input_method == "Volume-based (m³)":
        coke_v = st.sidebar.number_input("Coke Volume (m³)", min_value=0.0, value=2.0, step=0.1, key="coke_v")
        sinter_v = st.sidebar.number_input("Sinter Volume (m³)", min_value=0.0, value=3.5, step=0.1, key="sinter_v")
        pellet_v = st.sidebar.number_input("Pellet Volume (m³)", min_value=0.0, value=3.0, step=0.1, key="pellet_v")
        lump_v = st.sidebar.number_input("Lump Ore Volume (m³)", min_value=0.0, value=1.5, step=0.1, key="lump_v")
        
        volumes = {'coke': coke_v, 'sinter': sinter_v, 'pellet': pellet_v, 'lump': lump_v}
        for mat, v in volumes.items():
            masses[mat] = v * materials[mat]['bulk_density']
    else:
        coke_m = st.sidebar.number_input("Coke Mass (kg)", min_value=0.0, value=960.0, step=50.0, key="coke_m")
        sinter_m = st.sidebar.number_input("Sinter Mass (kg)", min_value=0.0, value=5950.0, step=50.0, key="sinter_m")
        pellet_m = st.sidebar.number_input("Pellet Mass (kg)", min_value=0.0, value=6150.0, step=50.0, key="pellet_m")
        lump_m = st.sidebar.number_input("Lump Ore Mass (kg)", min_value=0.0, value=3300.0, step=50.0, key="lump_m")
        
        masses = {'coke': coke_m, 'sinter': sinter_m, 'pellet': pellet_m, 'lump': lump_m}
        for mat, m in masses.items():
            bd = materials[mat]['bulk_density']
            volumes[mat] = m / bd if bd > 0 else 0.0
else:
    st.sidebar.subheader("Deadman Coke Quantity")
    if input_method == "Volume-based (m³)":
        coke_v = st.sidebar.number_input("Coke Volume in Deadman (m³)", min_value=0.1, value=10.0, step=0.5, key="coke_deadman_v")
        volumes = {'coke': coke_v, 'sinter': 0.0, 'pellet': 0.0, 'lump': 0.0}
        masses = {'coke': coke_v * materials['coke']['bulk_density'], 'sinter': 0.0, 'pellet': 0.0, 'lump': 0.0}
    else:
        coke_m = st.sidebar.number_input("Coke Mass in Deadman (kg)", min_value=1.0, value=4800.0, step=100.0, key="coke_deadman_m")
        bd = materials['coke']['bulk_density']
        volumes = {'coke': coke_m / bd if bd > 0 else 0.0, 'sinter': 0.0, 'pellet': 0.0, 'lump': 0.0}
        masses = {'coke': coke_m, 'sinter': 0.0, 'pellet': 0.0, 'lump': 0.0}

# --- Void Fraction & Mass Fractions Calculations ---
total_volume = sum(volumes.values())
if total_volume == 0:
    total_volume = 1.0

material_voids = {}
weighted_void_sum = 0.0

for mat, vol in volumes.items():
    td = materials[mat]['true_density']
    bd = materials[mat]['bulk_density']
    mat_void = 1.0 - (bd / td) if td > 0 else 0.0
    material_voids[mat] = mat_void
    weighted_void_sum += vol * mat_void

calculated_bed_void_fraction = weighted_void_sum / total_volume

total_mass = sum(masses.values())
if total_mass == 0:
    total_mass = 1.0
mass_fractions = {mat: m / total_mass for mat, m in masses.items()}

# --- Advanced Settings ---
with st.sidebar.expander("Advanced Bed & Void Settings") as adv_exp:
    st.markdown(f"**Calculated Bed Void Fraction ($\phi$):** `{calculated_bed_void_fraction:.4f}`")
    
    if "Deadman" in bf_zone:
        liquid_holdup = paired_input("Liquid Melt Saturation", 0.0, 1.0, 0.35, 0.01, "liq_hold", container=adv_exp)
    else:
        liquid_holdup = 0.0
        
    mean_particle_diameter = paired_input("Mean Particle Diameter (m)", 0.0, 1.0, 0.04 if "Deadman" in bf_zone else 0.025, 0.001, "dp_val", container=adv_exp)
    gas_conductivity = paired_input("Gas Conductivity (W/m·K)", 0.0, 1.0, 0.04, 0.005, "kg_val", container=adv_exp)

# --- Dual Calculation Engine ---
def calculate_thermophysics(mass_fractions, T, kg, dp, phi, liq_holdup, materials, zone_type):
    # --- 1. Pure Solid Phase Mixture Properties (WITHOUT Void Fraction) ---
    cp_solid_pure = 0.0
    cp_A_eff, cp_B_eff, cp_C_eff = 0.0, 0.0, 0.0
    for mat, w in mass_fractions.items():
        if w > 0:
            A, B, C = materials[mat]['cp_coeffs']
            cp_A_eff += w * A
            cp_B_eff += w * B
            cp_C_eff += w * C
            cp_solid_pure += w * (A + B * T + C * (T ** -2))

    active_mats = {mat: w for mat, w in mass_fractions.items() if w > 0}
    v_solid_terms = {mat: w / materials[mat]['true_density'] for mat, w in active_mats.items()}
    total_v_solid = sum(v_solid_terms.values())
    solid_vol_fractions = {mat: v / total_v_solid for mat, v in v_solid_terms.items()} if total_v_solid > 0 else {}
    
    ks_solid_pure = 0.0
    ks_A_eff, ks_B_eff, ks_C_eff = 0.0, 0.0, 0.0
    for mat, x_v in solid_vol_fractions.items():
        A, B, C = materials[mat]['k_coeffs']
        ks_A_eff += x_v * A
        ks_B_eff += x_v * B
        ks_C_eff += x_v * C
        ks_solid_pure += x_v * (A + B * T + C * (T ** 2))
    
    rho_solid_pure = sum(solid_vol_fractions[mat] * materials[mat]['true_density'] for mat in active_mats) if active_mats else 0.0

    # --- 2. Homogenized Packed Bed Properties (WITH Void Fraction & Radiation) ---
    rho_bed_effective = (1.0 - phi) * rho_solid_pure
    cp_bed_effective = cp_solid_pure

    if "Deadman" in zone_type:
        cp_liquid_avg = 850.0 
        rho_liq_avg = 6500.0
        cp_bed_effective = (1.0 - liq_holdup) * cp_solid_pure + liq_holdup * cp_liquid_avg
        rho_bed_effective = (1.0 - phi) * rho_solid_pure + phi * liq_holdup * rho_liq_avg

    sigma = 5.67e-8
    emissivity = 0.88 if "Deadman" not in zone_type else 0.92
    alpha_yk, gamma_yk, beta_yk = 0.8, 0.95, 0.95
    
    conduction_term = kg * (phi + ((1.0 - phi) / ((alpha_yk * (kg / ks_solid_pure)) + gamma_yk))) if ks_solid_pure > 0 else 0
    radiation_term = 4.0 * beta_yk * emissivity * sigma * dp * (T ** 3)
    k_bed_effective = conduction_term + radiation_term
    
    formula_coeffs = {
        'cp': (cp_A_eff, cp_B_eff, cp_C_eff),
        'ks': (ks_A_eff, ks_B_eff, ks_C_eff)
    }
    
    return (cp_solid_pure, ks_solid_pure, rho_solid_pure), (cp_bed_effective, k_bed_effective, rho_bed_effective), formula_coeffs

(cp_s, ks_s, rho_s), (cp_bed, k_bed, rho_bed), formula_coeffs = calculate_thermophysics(
    mass_fractions, temperature_k, gas_conductivity, mean_particle_diameter, calculated_bed_void_fraction, liquid_holdup, materials, bf_zone
)

# --- Display Results ---
st.markdown("---")
st.subheader(f"📊 Computed Properties at T = {temperature_k:.1f} K ({bf_zone})")

tab_porous, tab_homogenized = st.tabs([
    "🟢 Pure Solid Phase (For COMSOL Porous Media Node)", 
    "🔵 Homogenized Bed Effective (For Standard Domains)"
])

with tab_porous:
    st.info("💡 **Use these values when configuring the Solid Phase sub-node in COMSOL's Porous Media interface.** COMSOL will apply the bed porosity (ϕ) internally.")
    col_p1, col_p2, col_p3 = st.columns(3)
    col_p1.metric(label="Solid Density (ρ_s)", value=f"{rho_s:.2f} kg/m³")
    col_p2.metric(label="Solid Thermal Conductivity (k_s)", value=f"{ks_s:.3f} W/(m·K)")
    col_p3.metric(label="Solid Specific Heat (Cp_s)", value=f"{cp_s:.2f} J/(kg·K)")

with tab_homogenized:
    st.info("💡 **Use these values if modeling the bed as a single equivalent domain** without COMSOL's Porous Media interface.")
    col_h1, col_h2, col_h3 = st.columns(3)
    col_h1.metric(label="Bulk Bed Density (ρ_bed)", value=f"{rho_bed:.2f} kg/m³")
    col_h2.metric(label="Packed Bed Effective Conductivity (k_eff)", value=f"{k_bed:.3f} W/(m·K)")
    col_h3.metric(label="Bed Effective Specific Heat (Cp_eff)", value=f"{cp_bed:.2f} J/(kg·K)")

# --- Analytical Formulas & Export Section ---
st.markdown("---")
st.subheader("📐 Analytical Equations for COMSOL Implementation")

cp_A, cp_B, cp_C = formula_coeffs['cp']
ks_A, ks_B, ks_C = formula_coeffs['ks']
emissivity_val = 0.88 if "Deadman" not in bf_zone else 0.92

st.markdown(rf"""
1. **Pure Solid Phase Specific Heat $C_{{p,s}}(T)$**:
   $$C_{{p,s}}(T) = {cp_A:.3f} + ({cp_B:.3e}) \cdot T + ({cp_C:.3e}) \cdot T^{{-2}} \;\;\text{{[J/(kg·K)]}}$$

2. **Pure Solid Phase Conductivity $k_{{s}}(T)$**:
   $$k_{{s}}(T) = {ks_A:.3f} + ({ks_B:.3e}) \cdot T + ({ks_C:.3e}) \cdot T^2 \;\;\text{{[W/(m·K)]}}$$

3. **Homogenized Bed Conductivity $k_{{eff}}(T)$** *(includes void conduction & radiation)*:
   $$k_{{eff}}(T) = {gas_conductivity} \cdot \left({calculated_bed_void_fraction:.4f} + \frac{{1 - {calculated_bed_void_fraction:.4f}}}{{0.8 \cdot \frac{{{gas_conductivity}}}{{k_s(T)}} + 0.95}}\right) + 4 \cdot 0.95 \cdot {emissivity_val} \cdot \sigma \cdot {mean_particle_diameter} \cdot T^3$$
""")

# --- COMSOL Text Export Content Generator ---
zone_slug = "Granular" if "Granular" in bf_zone else "Deadman"
comsol_text = f"""====================================================================
BLAST FURNACE THERMOPHYSICAL MODEL EXPORT (COMSOL MULTIPHYSICS)
Zone: {bf_zone}
Operating Temperature Reference: {temperature_k:.2f} K
====================================================================

--------------------------------------------------------------------
OPTION 1: FOR COMSOL "HEAT TRANSFER IN POROUS MEDIA" INTERFACE
--------------------------------------------------------------------
[Porous Medium -> Solid Material Inputs]
rho_s = {rho_s:.2f} [kg/m^3]

Analytic Function 1 (Cp_s):
  Name: Cp_s
  Arguments: T
  Expression: {cp_A:.6f} + ({cp_B:.6e})*T + ({cp_C:.6e})*T^(-2)
  Units: J/(kg*K)

Analytic Function 2 (k_s):
  Name: k_s
  Arguments: T
  Expression: {ks_A:.6f} + ({ks_B:.6e})*T + ({ks_C:.6e})*T^2
  Units: W/(m*K)

[Porous Medium -> Porosity Input]
epsilon_p (or phi) = {calculated_bed_void_fraction:.4f}

--------------------------------------------------------------------
OPTION 2: FOR STANDARD SINGLE-PHASE DOMAIN (HOMOGENIZED BED)
--------------------------------------------------------------------
[Global Parameters]
rho_bed = {rho_bed:.2f} [kg/m^3]
phi_bed = {calculated_bed_void_fraction:.4f}

Analytic Function (k_eff):
  Name: k_eff
  Arguments: T
  Expression: {gas_conductivity} * ({calculated_bed_void_fraction:.6f} + (1 - {calculated_bed_void_fraction:.6f}) / (0.8 * ({gas_conductivity} / k_s(T)) + 0.95)) + 4 * 0.95 * {emissivity_val} * 5.67e-8 * {mean_particle_diameter} * T^3
  Units: W/(m*K)

====================================================================
EVALUATED VALUES AT T = {temperature_k:.1f} K:
- Solid Density (rho_s)       : {rho_s:.2f} kg/m^3
- Solid Conductivity (k_s)     : {ks_s:.3f} W/(m*K)
- Solid Heat Capacity (Cp_s)   : {cp_s:.2f} J/(kg*K)
- Bed Bulk Density (rho_bed)   : {rho_bed:.2f} kg/m^3
- Bed Effective k (k_eff)      : {k_bed:.3f} W/(m·K)
- Calculated Porosity (phi)    : {calculated_bed_void_fraction:.4f}
====================================================================
"""

st.download_button(
    label="📥 Download COMSOL Functions (.txt)",
    data=comsol_text,
    file_name=f"COMSOL_BF_{zone_slug}_Properties.txt",
    mime="text/plain"
)

# Visual Breakdown Chart
st.markdown("---")
st.subheader("📋 Zone Composition Breakdown")
col_c1, col_c2 = st.columns(2)
with col_c1:
    st.markdown("**Volume Distribution (m³)**")
    st.bar_chart({mat.capitalize(): [v] for mat, v in volumes.items()})
with col_c2:
    st.markdown("**Mass Distribution (kg)**")
    st.bar_chart({mat.capitalize(): [m] for mat, m in masses.items()})
    
