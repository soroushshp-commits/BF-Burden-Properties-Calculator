import streamlit as st
import pandas as pd
import plotly.express as px

# Page Configuration
st.set_page_config(
    page_title="Blast Furnace Burden Thermophysical Simulator",
    page_icon="🔥",
    layout="wide"
)

st.title("🔥 Blast Furnace Multi-Zone Thermophysical Simulator")
st.markdown("""
**Model Architecture Updates:** 
* **Zone-Aware Fluid Mechanics:** Granular Zone strictly operates as single-phase gas ($s_{gas} = 1.0$); Deadman Zone models dynamic multiphase pore flow (Gas + Iron + Slag).
* **Solid Matrix Scaling:** $C_{p,s}$ and $k_s$ are multiplied strictly by $(1 - \phi)$ without density ($\rho$) coupling.
* **Burden Visualization:** Interactive Mass vs. Volume distribution charts.
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

# --- Sidebar: Material Properties ---
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

# --- Sidebar: Liquid Melts Holdup & Temperature Coefficients ---
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
else:
    # Strictly zero out liquid melts in dry granular zone
    s_iron, mu_iron = 0.0, 0.005
    rho_iron_A, rho_iron_B = 7000.0, -0.5
    cp_iron_A, cp_iron_B = 800.0, 0.05
    k_iron_A, k_iron_B = 30.0, 0.0

    s_slag, mu_slag = 0.0, 0.05
    rho_slag_A, rho_slag_B = 2600.0, -0.2
    cp_slag_A, cp_slag_B = 1200.0, 0.1
    k_slag_A, k_slag_B = 3.5, 0.0

# --- Advanced Settings (Gas Flow & Temperature-Dependent Polynomials) ---
st.sidebar.header("💨 Gas Flow Properties & Polynomials")
temperature_k = paired_input("Bed Temp (K)", 273.15, 2000.0, 1600.0 if is_deadman else 1000.0, 10.0, "temp_k", fmt="%.1f")
vg = paired_input("Superficial Gas Velocity (m/s)", 0.1, 5.0, 1.5, 0.1, "vg_val")

with st.sidebar.expander("Gas Density ρ_g ($A + BT + CT^2 + DT^3$)", expanded=False):
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

# --- Void Fraction & Mass Fractions Calculations ---
total_volume = sum(volumes.values()) or 1.0
total_mass = sum(masses.values()) or 1.0
mass_fractions = {mat: m / total_mass for mat, m in masses.items()}

weighted_void_sum = sum(vol * (1.0 - (materials[mat]['bulk_density'] / materials[mat]['true_density'])) for mat, vol in volumes.items() if materials[mat]['true_density'] > 0)
phi = weighted_void_sum / total_volume

# Pore phase saturations
if is_deadman:
    s_liquid_total = s_iron + s_slag
    s_gas = max(0.0, 1.0 - s_liquid_total)
else:
    s_gas = 1.0
    s_iron = 0.0
    s_slag = 0.0

# --- Burden Visualization ---
st.markdown("---")
st.subheader("🧱 Burden Composition (Solid Matrix)")

df_burden = pd.DataFrame({
    "Material": [m.capitalize() for m in active_mats],
    "Mass (kg)": [masses[m] for m in active_mats],
    "Volume (m³)": [volumes[m] for m in active_mats]
})

col_mass, col_vol = st.columns(2)
color_map = {"Coke": "#4A4A4A", "Sinter": "#D2691E", "Pellet": "#A0522D", "Lump": "#8B4513"}

with col_mass:
    fig_mass = px.pie(
        df_burden, values='Mass (kg)', names='Material', 
        title="Mass Distribution", hole=0.4,
        color='Material', color_discrete_map=color_map
    )
    fig_mass.update_layout(margin=dict(t=40, b=0, l=0, r=0))
    st.plotly_chart(fig_mass, use_container_width=True)

with col_vol:
    fig_vol = px.pie(
        df_burden, values='Volume (m³)', names='Material', 
        title="Volume Distribution", hole=0.4,
        color='Material', color_discrete_map=color_map
    )
    fig_vol.update_layout(margin=dict(t=40, b=0, l=0, r=0))
    st.plotly_chart(fig_vol, use_container_width=True)

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

    rho_bulk = total_mass / total_volume if total_volume > 0 else 0.0

    cp_s_eff = cp_s * (1.0 - phi)
    ks_s_eff = ks_s * (1.0 - phi)

    inv_dp_sum = sum(vol_fracs[m] / materials[m]['dp'] for m in vol_fracs if materials[m]['dp'] > 0)
    dp_eff = (1.0 / inv_dp_sum) if inv_dp_sum > 0 else 0.025

    rho_g = rhog_A + rhog_B * T + rhog_C * (T ** 2) + rhog_D * (T ** 3)
    mu_g = mu_A + mu_B * T + mu_C * (T ** 2) + mu_D * (T ** 3)
    cp_g = cpg_A + cpg_B * T + cpg_C * (T ** 2) + cpg_D * (T ** 3)
    kg = kg_A + kg_B * T + kg_C * (T ** 2) + kg_D * (T ** 3)

    rho_iron = rho_iron_A + rho_iron_B * T
    cp_iron = cp_iron_A + cp_iron_B * T
    k_iron = k_iron_A + k_iron_B * T

    rho_slag = rho_slag_A + rho_slag_B * T
    cp_slag = cp_slag_A + cp_slag_B * T
    k_slag = k_slag_A + k_slag_B * T

    if is_deadman:
        rho_fluid = (s_gas * rho_g) + (s_iron * rho_iron) + (s_slag * rho_slag)
        cp_fluid = (s_gas * cp_g) + (s_iron * cp_iron) + (s_slag * cp_slag)
        k_fluid = (s_gas * kg) + (s_iron * k_iron) + (s_slag * k_slag)
        mu_fluid = (s_gas * mu_g) + (s_iron * mu_iron) + (s_slag * mu_slag)
    else:
        rho_fluid = rho_g
        cp_fluid = cp_g
        k_fluid = kg
        mu_fluid = mu_g

    Re = (rho_fluid * vg * dp_eff) / mu_fluid if mu_fluid > 0 else 0
    Pr = (cp_fluid * mu_fluid) / k_fluid if k_fluid > 0 else 0
    Nu = 2.0 + 1.1 * (Pr ** (1/3)) * (Re ** 0.6)
    
    h_sf = (Nu * k_fluid) / dp_eff if dp_eff > 0 else 0
    a_sf = (6.0 * (1.0 - phi)) / dp_eff if dp_eff > 0 else 0
    q_sf_coeff = h_sf * a_sf

    fluid_state = {'rho': rho_fluid, 'cp': cp_fluid, 'k': k_fluid, 'mu': mu_fluid, 'rhog': rho_g, 'cpg': cp_g, 'kg': kg, 'mug': mu_g}
    coeffs = {
        'cp': (cp_A, cp_B, cp_C), 'ks': (ks_A, ks_B, ks_C), 
        'rhog': (rhog_A, rhog_B, rhog_C, rhog_D),
        'mu': (mu_A, mu_B, mu_C, mu_D), 'cpg': (cpg_A, cpg_B, cpg_C, cpg_D), 'kg': (kg_A, kg_B, kg_C, kg_D),
        'rho_iron': (rho_iron_A, rho_iron_B), 'cp_iron': (cp_iron_A, cp_iron_B), 'k_iron': (k_iron_A, k_iron_B),
        'rho_slag': (rho_slag_A, rho_slag_B), 'cp_slag': (cp_slag_A, cp_slag_B), 'k_slag': (k_slag_A, k_slag_B)
    }
    return (cp_s, ks_s, rho_s, rho_bulk), (cp_s_eff, ks_s_eff), (dp_eff, Re, Pr, Nu, h_sf, a_sf, q_sf_coeff, fluid_state), coeffs

(cp_s, ks_s, rho_s, rho_bulk), (cp_s_eff, ks_s_eff), fluid_interphase, coeffs = calculate_physics(temperature_k)
dp_eff, Re, Pr, Nu, h_sf, a_sf, q_sf_coeff, fluid_state = fluid_interphase
cp_A, cp_B, cp_C = coeffs['cp']
ks_A, ks_B, ks_C = coeffs['ks']
rhog_A, rhog_B, rhog_C, rhog_D = coeffs['rhog']
mu_A, mu_B, mu_C, mu_D = coeffs['mu']
cpg_A, cpg_B, cpg_C, cpg_D = coeffs['cpg']
kg_A, kg_B, kg_C, kg_D = coeffs['kg']

# --- Display Results ---
st.markdown("---")
st.subheader(f"📊 Computed Properties at T = {temperature_k:.1f} K")

tab3_label = "⚙️ Multiphase Pore Fluid (Gas + Melts)" if is_deadman else "💨 Gas Phase Pore Fluid"

tab1, tab2, tab3 = st.tabs([
    "🟢 COMSOL LTNE: Solid Sub-Node", 
    "🟠 COMSOL Solid Matrix (Scaled by [1-φ])",
    tab3_label
])

with tab1:
    st.info("💡 **LTNE Solid Matrix (Intrinsic).** Uses True Density and pure skeletal properties.")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Void Fraction (Porosity φ)", f"{phi:.4f}")
    col2.metric("True Density (ρ_s)", f"{rho_s:.2f} kg/m³")
    col3.metric("Solid Conductivity (k_s)", f"{ks_s:.3f} W/(m·K)")
    col4.metric("Solid Heat Capacity (Cp_s)", f"{cp_s:.2f} J/(kg·K)")
    
    st.markdown("#### Analytical Functions (T)")
    st.latex(rf"C_{{p,s}}(T) = {cp_A:.4f} + ({cp_B:.4e})T + ({cp_C:.4e})T^{{-2}}")
    st.latex(rf"k_s(T) = {ks_A:.4f} + ({ks_B:.4e})T + ({ks_C:.4e})T^2")

with tab2:
    st.info("💡 **Scaled Solid Matrix.** $C_p$ and $k$ multiplied by $(1-\phi)$ without density.")
    col1, col2, col3 = st.columns(3)
    col1.metric("Bulk Density (ρ_bulk)", f"{rho_bulk:.2f} kg/m³")
    col2.metric("Effective Conductivity (k_eff = k_s · [1-φ])", f"{ks_s_eff:.3f} W/(m·K)")
    col3.metric("Effective Specific Heat (Cp_eff = Cp_s · [1-φ])", f"{cp_s_eff:.2f} J/(kg·K)")
    
    st.markdown("#### Analytical Functions (T)")
    st.latex(rf"C_{{p,eff}}(T) = (1 - {phi:.4f}) \cdot C_{{p,s}}(T)")
    st.latex(rf"k_{{eff}}(T) = (1 - {phi:.4f}) \cdot k_s(T)")

with tab3:
    if is_deadman:
        st.info(f"💡 **Multiphase Pore Fluid Mixture evaluated at T = {temperature_k:.1f} K** (Gas + Liquid Iron + Liquid Slag).")
    else:
        st.info(f"💡 **Gas Phase Pore Fluid evaluated at T = {temperature_k:.1f} K** (Single-Phase Gas Flow in Granular Bed).")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Fluid Density ρ_fluid(T)", f"{fluid_state['rho']:.3f} kg/m³")
    col2.metric("Fluid Specific Heat Cp_fluid(T)", f"{fluid_state['cp']:.2f} J/(kg·K)")
    col3.metric("Fluid Conductivity k_fluid(T)", f"{fluid_state['k']:.4f} W/(m·K)")
    col4.metric("Fluid Viscosity μ_fluid(T)", f"{fluid_state['mu']:.4f} Pa·s")

    st.markdown("#### Dimensionless Numbers & Interphase Coupling")
    dcol1, dcol2, dcol3 = st.columns(3)
    dcol1.metric("Reynolds Number Re(T)", f"{Re:.1f}")
    dcol2.metric("Prandtl Number Pr(T)", f"{Pr:.3f}")
    dcol3.metric("Nusselt Number Nu(T)", f"{Nu:.2f}")

    st.markdown("#### Analytical Formulations in Pores")
    if is_deadman:
        st.latex(r"\rho_{fluid}(T) = s_{gas}\rho_g(T) + s_{iron}\rho_{iron}(T) + s_{slag}\rho_{slag}(T)")
        st.latex(r"C_{p,fluid}(T) = s_{gas}C_{p,g}(T) + s_{iron}C_{p,iron}(T) + s_{slag}C_{p,slag}(T)")
        st.latex(r"k_{fluid}(T) = s_{gas}k_g(T) + s_{iron}k_{iron}(T) + s_{slag}k_{slag}(T)")
    else:
        st.latex(r"\rho_{fluid}(T) = \rho_g(T) = A + B\cdot T + C\cdot T^2 + D\cdot T^3")
        st.latex(r"C_{p,fluid}(T) = C_{p,g}(T) = A + B\cdot T + C\cdot T^2 + D\cdot T^3")
        st.latex(r"k_{fluid}(T) = k_g(T) = A + B\cdot T + C\cdot T^2 + D\cdot T^3")

# --- COMSOL Text Export Content Generator ---
scale_fac = 1.0 - phi

if is_deadman:
    fluid_export_text = (
        "--------------------------------------------------------------------\n"
        "2. DEADMAN ZONE MULTIPHASE PORE FLUID MIXTURE (COMSOL)\n"
        "--------------------------------------------------------------------\n"
        f"Gas Saturation (s_gas)   = {s_gas:.4f}\n"
        f"Iron Saturation (s_iron) = {s_iron:.4f}\n"
        f"Slag Saturation (s_slag) = {s_slag:.4f}\n\n"
        "[Mixture Fluid Property Expressions in Pores]\n"
        f"rho_fluid(T) = {s_gas:.4f}*rho_g(T) + {s_iron:.4f}*rho_iron(T) + {s_slag:.4f}*rho_slag(T)\n"
        f"Cp_fluid(T)  = {s_gas:.4f}*Cp_g(T) + {s_iron:.4f}*Cp_iron(T) + {s_slag:.4f}*Cp_slag(T)\n"
        f"k_fluid(T)   = {s_gas:.4f}*k_g(T) + {s_iron:.4f}*k_iron(T) + {s_slag:.4f}*k_slag(T)\n"
        f"mu_fluid(T)  = {s_gas:.4f}*mu_g(T) + {s_iron:.4f}*{mu_iron:.4f} + {s_slag:.4f}*{mu_slag:.4f}"
    )
else:
    fluid_export_text = (
        "--------------------------------------------------------------------\n"
        "2. GRANULAR ZONE PORE FLUID PROPERTIES (COMSOL - PURE GAS PHASE)\n"
        "--------------------------------------------------------------------\n"
        "Gas Saturation (s_gas)   = 1.0000 (No Liquid Melts Present)\n\n"
        "[Pure Gas Property Expressions in Pores]\n"
        "rho_fluid(T) = rho_g(T)\n"
        "Cp_fluid(T)  = Cp_g(T)\n"
        "k_fluid(T)   = k_g(T)\n"
        "mu_fluid(T)  = mu_g(T)"
    )

zone_prefix = "Deadman" if is_deadman else "Granular"

comsol_text = (
    "====================================================================\n"
    "BLAST FURNACE MULTIPHASE MODEL EXPORT (COMSOL)\n"
    f"Operating Zone: {bf_zone}\n"
    f"Evaluate
