import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="Blast Furnace Burden Thermophysical Simulator",
    page_icon="🔥",
    layout="wide"
)

st.title("🔥 Blast Furnace Multi-Zone Thermophysical Simulator")
st.markdown("""
**Model Architecture Updates:** 
* **LTNE Solid Sub-Node:** Utilizes the **True Density ($\rho_s$)** of the solid particles.
* **Manual Solid Matrix:** Utilizes the **Bulk Density ($\rho_{bulk}$)** of the bed.
* **Effective Properties:** $C_{p,eff} = C_{p,s} \cdot (1 - \phi)$ and $k_{eff} = k_s \cdot (1 - \phi)$.
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

# --- Sidebar: Material Properties (Densities, Quantities & Coefficients) ---
st.sidebar.header("🛠️ Material Database & Coefficients")

default_materials = {
    'coke': {'td': 1850.0, 'bd': 480.0, 'mass': 960.0, 'cpa': 860.0, 'cpb': 5.40e-1, 'cpc': -2.75e7, 'ka': 0.28, 'kb': 1.75e-3, 'kc': -3.20e-7},
    'sinter': {'td': 3450.0, 'bd': 1700.0, 'mass': 5950.0, 'cpa': 745.0, 'cpb': 2.60e-1, 'cpc': -1.25e7, 'ka': 0.92, 'kb': 0.48e-3, 'kc': 0.85e-7},
    'pellet': {'td': 3350.0, 'bd': 2050.0, 'mass': 6150.0, 'cpa': 620.5, 'cpb': 6.15e-1, 'cpc': -1.18e7, 'ka': 1.42, 'kb': -0.38e-3, 'kc': 1.15e-7},
    'lump': {'td': 4600.0, 'bd': 2200.0, 'mass': 3300.0, 'cpa': 615.0, 'cpb': 5.85e-1, 'cpc': -1.15e7, 'ka': 2.15, 'kb': -0.65e-3, 'kc': 0.25e-7}
}

active_mats = ['coke', 'sinter', 'pellet', 'lump'] if "Granular" in bf_zone else ['coke']

materials = {}
masses = {}
volumes = {}

for mat in active_mats:
    with st.sidebar.expander(f"{mat.capitalize()} Properties", expanded=(mat == 'coke')):
        td = st.number_input("True Density (kg/m³)", value=default_materials[mat]['td'], step=50.0, key=f"{mat}_td")
        bd = st.number_input("Bulk Density (kg/m³)", value=default_materials[mat]['bd'], step=50.0, key=f"{mat}_bd")
        m = st.number_input("Mass (kg)", value=default_materials[mat]['mass'], step=50.0, key=f"{mat}_m")
        v = m / bd if bd > 0 else 0.0
        st.caption(f"Calculated Bulk Volume: {v:.3f} m³")
            
        masses[mat] = m
        volumes[mat] = v
        
        st.divider()
        st.markdown(f"**$C_p$ Coefficients** ($A + B\\cdot T + C\\cdot T^{{-2}}$)")
        col_cpa, col_cpb, col_cpc = st.columns(3)
        cpa = col_cpa.number_input("A", value=float(default_materials[mat]['cpa']), key=f"{mat}_cpa")
        cpb = col_cpb.number_input("B", value=float(default_materials[mat]['cpb']), key=f"{mat}_cpb")
        cpc = col_cpc.number_input("C", value=float(default_materials[mat]['cpc']), key=f"{mat}_cpc")
        
        st.markdown(f"**$k$ Coefficients** ($A + B\\cdot T + C\\cdot T^2$)")
        col_ka, col_kb, col_kc = st.columns(3)
        ka = col_ka.number_input("A", value=float(default_materials[mat]['ka']), key=f"{mat}_ka")
        kb = col_kb.number_input("B", value=float(default_materials[mat]['kb']), key=f"{mat}_kb")
        kc = col_kc.number_input("C", value=float(default_materials[mat]['kc']), key=f"{mat}_kc")

        materials[mat] = {'true_density': td, 'bulk_density': bd, 'cp_coeffs': (cpa, cpb, cpc), 'k_coeffs': (ka, kb, kc)}

for mat in ['sinter', 'pellet', 'lump']:
    if mat not in active_mats:
        masses[mat] = 0.0
        volumes[mat] = 0.0
        materials[mat] = materials.get(mat, {'true_density': 1.0, 'bulk_density': 1.0, 'cp_coeffs': (0,0,0), 'k_coeffs': (0,0,0)})

# --- Advanced Settings (Gas and Particle Properties) ---
st.sidebar.header("💨 Gas Flow Properties")
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

weighted_void_sum = sum(vol * (1.0 - (materials[mat]['bulk_density'] / materials[mat]['true_density'])) for mat, vol in volumes.items() if materials[mat]['true_density'] > 0)
phi = weighted_void_sum / total_volume

# --- Physics Calculation Engine ---
def calculate_physics(T):
    cp_s, ks_s, rho_s = 0.0, 0.0, 0.0
    rho_bulk_mix = 0.0
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

    # Mixture bulk density based on total mass and total volume
    rho_bulk = total_mass / total_volume if total_volume > 0 else 0.0

    # Effective properties (strictly scalar scaling by [1 - phi])
    cp_s_eff = cp_s * (1.0 - phi)
    ks_s_eff = ks_s * (1.0 - phi)

    # Interphase Heat Transfer (Wakao and Kaguei)
    Re = (rho_g * vg * mean_particle_diameter) / mu_g if mu_g > 0 else 0
    Pr = (cp_g * mu_g) / gas_conductivity if gas_conductivity > 0 else 0
    Nu = 2.0 + 1.1 * (Pr ** (1/3)) * (Re ** 0.6)
    
    h_sf = (Nu * gas_conductivity) / mean_particle_diameter if mean_particle_diameter > 0 else 0
    a_sf = (6.0 * (1.0 - phi)) / mean_particle_diameter if mean_particle_diameter > 0 else 0
    q_sf_coeff = h_sf * a_sf

    coeffs = {'cp': (cp_A, cp_B, cp_C), 'ks': (ks_A, ks_B, ks_C)}
    return (cp_s, ks_s, rho_s, rho_bulk), (cp_s_eff, ks_s_eff), (Re, Pr, Nu, h_sf, a_sf, q_sf_coeff), coeffs

(cp_s, ks_s, rho_s, rho_bulk), (cp_s_eff, ks_s_eff), interphase, coeffs = calculate_physics(temperature_k)
Re, Pr, Nu, h_sf, a_sf, q_sf_coeff = interphase
cp_A, cp_B, cp_C = coeffs['cp']
ks_A, ks_B, ks_C = coeffs['ks']

# --- Display Results ---
st.markdown("---")
st.subheader(f"📊 Computed Properties at $T = {temperature_k:.1f}$ K (Void Fraction $\\phi = {phi:.4f}$)")

tab1, tab2, tab3 = st.tabs([
    "🟢 COMSOL LTNE: Solid Sub-Node", 
    "🟠 COMSOL Heat Transfer in Solids (Manual Matrix)",
    "⚙️ Gas Dynamics & Interphase Coupling ($q_{sf}$)"
])

with tab1:
    st.info("💡 **LTNE Solid Matrix.** Uses True Density and intrinsic solid properties.")
    col1, col2, col3 = st.columns(3)
    col1.metric("True Density (ρ_s)", f"{rho_s:.2f} kg/m³")
    col2.metric("Solid Conductivity (k_s)", f"{ks_s:.3f} W/(m·K)")
    col3.metric("Solid Heat Capacity (Cp_s)", f"{cp_s:.2f} J/(kg·K)")
    
    st.markdown("#### Analytical Functions ($T$)")
    st.latex(rf"C_{{p,s}}(T) = {cp_A:.4f} + ({cp_B:.4e})T + ({cp_C:.4e})T^{{-2}}")
    st.latex(rf"k_s(T) = {ks_A:.4f} + ({ks_B:.4e})T + ({ks_C:.4e})T^2")

with tab2:
    st.info("💡 **Manual Solid Matrix (Heat Transfer in Solids).** Uses Bulk Density and properties scaled strictly by $(1 - \phi)$.")
    col1, col2, col3 = st.columns(3)
    col1.metric("Bulk Density (ρ_bulk)", f"{rho_bulk:.2f} kg/m³")
    col2.metric("Effective Conductivity (k_eff = k_s · [1-φ])", f"{ks_s_eff:.3f} W/(m·K)")
    col3.metric("Effective Heat Capacity (Cp_eff = Cp_s · [1-φ])", f"{cp_s_eff:.2f} J/(kg·K)")
    
    st.markdown("#### Analytical Functions ($T$)")
    st.latex(rf"C_{{p,eff}}(T) = (1 - {phi:.4f}) \cdot C_{{p,s}}(T)")
    st.latex(rf"k_{{eff}}(T) = (1 - {phi:.4f}) \cdot k_s(T)")

with tab3:
    col1, col2, col3 = st.columns(3)
    col1.metric("Reynolds Number (Re)", f"{Re:.1f}")
    col2.metric("Prandtl Number (Pr)", f"{Pr:.3f}")
    col3.metric("Nusselt Number (Nu)", f"{Nu:.2f}")
    
    st.markdown("#### Interphase Heat Exchange Source Term ($q_{sf}$)")
    col4, col5 = st.columns(2)
    col4.metric("Specific Surface Area (a_sf)", f"{a_sf:.1f} m²/m³")
    col5.metric("Interphase HTC (h_sf)", f"{h_sf:.2f} W/(m²·K)")
    st.latex(rf"q_{{sf}}(T_{{fluid}}, T_{{solid}}) = {a_sf:.2f} \cdot {h_sf:.2f} \cdot (T_{{fluid}} - T_{{solid}}) \text{{  [W/m³]}}")

# --- COMSOL Text Export Content Generator ---
comsol_text = f"""====================================================================
BLAST FURNACE DUAL PHYSICS MODEL EXPORT (COMSOL MULTIPHYSICS)
Evaluated at Temp: {temperature_k:.2f} K | Bed Porosity (phi): {phi:.4f}
====================================================================

--------------------------------------------------------------------
1. HEAT TRANSFER IN POROUS MEDIA (LTNE) - SOLID SUB-NODE
--------------------------------------------------------------------
rho_s = {rho_s:.2f} [kg/m^3]  // True density
porosity_phi = {phi:.4f}

[Analytic Function: Solid Heat Capacity Cp_s(T)]
Expression: {cp_A:.6f} + ({cp_B:.6e})*T + ({cp_C:.6e})*T^(-2)

[Analytic Function: Solid Conductivity k_s(T)]
Expression: {ks_A:.6f} + ({ks_B:.6e})*T + ({ks_C:.6e})*T^2

--------------------------------------------------------------------
2. HEAT TRANSFER IN SOLIDS (MANUAL COUPLING SOLID MATRIX)
--------------------------------------------------------------------
rho_bulk = {rho_bulk:.2f} [kg/m^3]  // Bulk density

[Analytic Function: Effective Heat Capacity Cp_eff(T)]
Expression: (1 - {phi:.4f}) * ( {cp_A:.6f} + ({cp_B:.6e})*T + ({cp_C:.6e})*T^(-2) )

[Analytic Function: Effective Conductivity k_eff(T)]
Expression: (1 - {phi:.4f}) * ( {ks_A:.6f} + ({ks_B:.6e})*T + ({ks_C:.6e})*T^2 )

--------------------------------------------------------------------
3. INTERPHASE HEAT TRANSFER COUPLING (FLUID-SOLID)
--------------------------------------------------------------------
a_sf = {a_sf:.6f} [m^2/m^3]
h_sf = {h_sf:.6f} [W/(m^2*K)]
Function q_sf(T_fluid, T_solid) = {q_sf_coeff:.6f} * (T_fluid - T_solid) [W/m^3]

====================================================================
"""

st.download_button(
    label="📥 Download Corrected COMSOL Variables (.txt)",
    data=comsol_text,
    file_name=f"COMSOL_BF_Corrected_Properties.txt",
    mime="text/plain"
)
