import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="Blast Furnace Burden Thermophysical Simulator",
    page_icon="🔥",
    layout="wide"
)

st.title("🔥 Blast Furnace Multi-Zone Thermophysical Simulator (Advanced Gas & Particle Dynamics)")
st.markdown("""
**Model Architecture Updates:** 
* **Effective Sauter Diameter ($d_{p,eff}$):** Automatically computed using the harmonic mean of individual material particle sizes weighted by their solid volume fractions.
* **Temperature-Dependent Gas Properties:** $\mu_g, C_{p,g}, \text{ and } k_g$ are calculated dynamically using user-defined polynomial coefficients ($A + B\cdot T + C\cdot T^2 + D\cdot T^3$).
* **Dual Physics Solid Scaling:** LTNE true density / solid properties and Manual Matrix bulk density / effective properties scaled strictly by $(1 - \phi)$.
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

# --- Sidebar: Material Properties (Densities, Diameters, Quantities & Coefficients) ---
st.sidebar.header("🛠️ Material Database & Particle Sizes")

default_materials = {
    'coke': {'td': 1850.0, 'bd': 480.0, 'mass': 960.0, 'dp': 0.040, 'cpa': 860.0, 'cpb': 5.40e-1, 'cpc': -2.75e7, 'ka': 0.28, 'kb': 1.75e-3, 'kc': -3.20e-7},
    'sinter': {'td': 3450.0, 'bd': 1700.0, 'mass': 5950.0, 'dp': 0.025, 'cpa': 745.0, 'cpb': 2.60e-1, 'cpc': -1.25e7, 'ka': 0.92, 'kb': 0.48e-3, 'kc': 0.85e-7},
    'pellet': {'td': 3350.0, 'bd': 2050.0, 'mass': 6150.0, 'dp': 0.015, 'cpa': 620.5, 'cpb': 6.15e-1, 'cpc': -1.18e7, 'ka': 1.42, 'kb': -0.38e-3, 'kc': 1.15e-7},
    'lump': {'td': 4600.0, 'bd': 2200.0, 'mass': 3300.0, 'dp': 0.030, 'cpa': 615.0, 'cpb': 5.85e-1, 'cpc': -1.15e7, 'ka': 2.15, 'kb': -0.65e-3, 'kc': 0.25e-7}
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
        dp_val = st.number_input("Particle Diameter d_p (m)", value=default_materials[mat]['dp'], step=0.005, format="%.3f", key=f"{mat}_dp")
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

        materials[mat] = {'true_density': td, 'bulk_density': bd, 'dp': dp_val, 'cp_coeffs': (cpa, cpb, cpc), 'k_coeffs': (ka, kb, kc)}

for mat in ['sinter', 'pellet', 'lump']:
    if mat not in active_mats:
        masses[mat] = 0.0
        volumes[mat] = 0.0
        materials[mat] = materials.get(mat, {'true_density': 1.0, 'bulk_density': 1.0, 'dp': 0.02, 'cp_coeffs': (0,0,0), 'k_coeffs': (0,0,0)})

# --- Advanced Settings (Gas Flow & Temperature-Dependent Polynomials) ---
st.sidebar.header("💨 Gas Flow Properties & Polynomials")
temperature_k = paired_input("Bed Temp (K)", 273.15, 2000.0, 1600.0 if "Deadman" in bf_zone else 1000.0, 10.0, "temp_k", fmt="%.1f")
vg = paired_input("Superficial Gas Velocity (m/s)", 0.1, 5.0, 1.5, 0.1, "vg_val")
rho_g = paired_input("Gas Density ρ_g (kg/m³)", 0.1, 2.0, 0.45, 0.05, "rho_g_val")

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
    kg_B = st.number_input("kg_B", value=5.00e-5, format="%.2e", key="kg_b")
    kg_C = st.number_input("kg C", value=0.0, format="%.2e", key="kg_c")
    kg_D = st.number_input("kg D", value=0.0, format="%.2e", key="kg_d")

# --- Void Fraction & Mass Fractions Calculations ---
total_volume = sum(volumes.values()) or 1.0
total_mass = sum(masses.values()) or 1.0
mass_fractions = {mat: m / total_mass for mat, m in masses.items()}

weighted_void_sum = sum(vol * (1.0 - (materials[mat]['bulk_density'] / materials[mat]['true_density'])) for mat, vol in volumes.items() if materials[mat]['true_density'] > 0)
phi = weighted_void_sum / total_volume

# --- Physics Calculation Engine ---
def calculate_physics(T):
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

    # Mixture bulk density
    rho_bulk = total_mass / total_volume if total_volume > 0 else 0.0

    # Effective solid properties (scalar scaling by [1 - phi])
    cp_s_eff = cp_s * (1.0 - phi)
    ks_s_eff = ks_s * (1.0 - phi)

    # Effective Sauter Mean Diameter via Harmonic Mean of solid volume fractions
    inv_dp_sum = sum(vol_fracs[m] / materials[m]['dp'] for m in vol_fracs if materials[m]['dp'] > 0)
    dp_eff = (1.0 / inv_dp_sum) if inv_dp_sum > 0 else 0.025

    # Temperature-Dependent Gas Properties via Polynomial Evaluation
    mu_g = mu_A + mu_B * T + mu_C * (T ** 2) + mu_D * (T ** 3)
    cp_g = cpg_A + cpg_B * T + cpg_C * (T ** 2) + cpg_D * (T ** 3)
    gas_conductivity = kg_A + kg_B * T + kg_C * (T ** 2) + kg_D * (T ** 3)

    # Interphase Heat Transfer (Wakao and Kaguei)
    Re = (rho_g * vg * dp_eff) / mu_g if mu_g > 0 else 0
    Pr = (cp_g * mu_g) / gas_conductivity if gas_conductivity > 0 else 0
    Nu = 2.0 + 1.1 * (Pr ** (1/3)) * (Re ** 0.6)
    
    h_sf = (Nu * gas_conductivity) / dp_eff if dp_eff > 0 else 0
    a_sf = (6.0 * (1.0 - phi)) / dp_eff if dp_eff > 0 else 0
    q_sf_coeff = h_sf * a_sf

    gas_state = {'mu': mu_g, 'cp': cp_g, 'k': gas_conductivity}
    coeffs = {'cp': (cp_A, cp_B, cp_C), 'ks': (ks_A, ks_B, ks_C), 'mu': (mu_A, mu_B, mu_C, mu_D), 'cpg': (cpg_A, cpg_B, cpg_C, cpg_D), 'kg': (kg_A, kg_B, kg_C, kg_D)}
    return (cp_s, ks_s, rho_s, rho_bulk), (cp_s_eff, ks_s_eff), (dp_eff, Re, Pr, Nu, h_sf, a_sf, q_sf_coeff, gas_state), coeffs

(cp_s, ks_s, rho_s, rho_bulk), (cp_s_eff, ks_s_eff), gas_interphase, coeffs = calculate_physics(temperature_k)
dp_eff, Re, Pr, Nu, h_sf, a_sf, q_sf_coeff, gas_state = gas_interphase
cp_A, cp_B, cp_C = coeffs['cp']
ks_A, ks_B, ks_C = coeffs['ks']
mu_A, mu_B, mu_C, mu_D = coeffs['mu']
cpg_A, cpg_B, cpg_C, cpg_D = coeffs['cpg']
kg_A, kg_B, kg_C, kg_D = coeffs['kg']

# --- Display Results ---
st.markdown("---")
st.subheader(f"📊 Computed Properties at $T = {temperature_k:.1f}$ K (Void Fraction $\\phi = {phi:.4f}$ | Effective $d_p = {dp_eff:.4f}$ m)")

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
    st.info(f"💡 **Gas Dynamics evaluated at $T = {temperature_k:.1f}$ K.** Effective Sauter diameter $d_{p,eff} = {dp_eff:.4f}$ m.")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Reynolds Number (Re)", f"{Re:.1f}")
    col2.metric("Prandtl Number (Pr)", f"{Pr:.3f}")
    col3.metric("Nusselt Number (Nu)", f"{Nu:.2f}")
    col4.metric("Effective Particle Diameter (d_p,eff)", f"{dp_eff:.4f} m")
    
    st.markdown("#### Evaluated Gas Properties & Interphase Coupling ($q_{sf}$)")
    gcol1, gcol2, gcol3 = st.columns(3)
    gcol1.metric("Gas Viscosity (μ_g)", f"{gas_state['mu']:.2e} Pa·s")
    gcol2.metric("Gas Specific Heat (Cp_g)", f"{gas_state['cp']:.2f} J/(kg·K)")
    gcol3.metric("Gas Conductivity (k_g)", f"{gas_state['k']:.4f} W/(m·K)")

    col4, col5 = st.columns(2)
    col4.metric("Specific Surface Area (a_sf)", f"{a_sf:.1f} m²/m³")
    col5.metric("Interphase HTC (h_sf)", f"{h_sf:.2f} W/(m²·K)")
    st.latex(rf"q_{{sf}}(T_{{fluid}}, T_{{solid}}) = {a_sf:.2f} \cdot {h_sf:.2f} \cdot (T_{{fluid}} - T_{{solid}}) \text{{  [W/m³]}}")

# --- COMSOL Text Export Content Generator ---
comsol_text = f"""====================================================================
BLAST FURNACE DUAL PHYSICS & GAS DYNAMICS MODEL EXPORT (COMSOL)
Evaluated at Temp: {temperature_k:.2f} K | Bed Porosity (phi): {phi:.4f}
Effective Particle Diameter (d_p,eff): {dp_eff:.6f} m
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
3. TEMPERATURE-DEPENDENT GAS PROPERTIES (FLUID DOMAIN)
--------------------------------------------------------------------
[Analytic Function: Gas Viscosity mu_g(T)]
Expression: {mu_A:.6e} + ({mu_B:.6e})*T + ({mu_C:.6e})*T^2 + ({mu_D:.6e})*T^3

[Analytic Function: Gas Specific Heat Cp_g(T)]
Expression: {cpg_A:.6f} + ({cpg_B:.6e})*T + ({cpg_C:.6e})*T^2 + ({cpg_D:.6e})*T^3

[Analytic Function: Gas Conductivity k_g(T)]
Expression: {kg_A:.6f} + ({kg_B:.6e})*T + ({kg_C:.6e})*T^2 + ({kg_D:.6e})*T^3

--------------------------------------------------------------------
4. INTERPHASE HEAT TRANSFER COUPLING (FLUID-SOLID)
--------------------------------------------------------------------
dp_eff = {dp_eff:.6f} [m]
a_sf = {a_sf:.6f} [m^2/m^3]
h_sf = {h_sf:.6f} [W/(m^2*K)]
Function q_sf(T_fluid, T_solid) = {q_sf_coeff:.6f} * (T_fluid - T_solid) [W/m^3]

====================================================================
"""

st.download_button(
    label="📥 Download Advanced COMSOL Variables (.txt)",
    data=comsol_text,
    file_name=f"COMSOL_BF_Advanced_Properties.txt",
    mime="text/plain"
)
