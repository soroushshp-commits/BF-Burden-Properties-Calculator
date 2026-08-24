import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="Blast Furnace Burden Thermophysical Simulator",
    page_icon="🔥",
    layout="wide"
)

st.title("🔥 Blast Furnace Multi-Zone Thermophysical Simulator (Coke Skeleton + Melts Integration)")
st.markdown("""
**Model Architecture Updates:** 
* **Zone-Aware Phase Split:** Granular zone processes dry multi-component burden. Deadman zone treats the structural skeleton strictly as **coke**, while liquid iron and slag are modeled as interstitial liquid holdups within the pore space.
* **Effective Porosity & Volumetric Blending:** Calculates gas-available porosity ($\phi_{gas}$) and incorporates liquid iron/slag volumetric heat capacity contributions $(\rho C_p)$.
* **Temperature-Dependent Gas & Interphase Dynamics:** Full polynomial functions for gas expansion and heat transfer coefficients.
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

# --- Sidebar: Material Properties (Densities, Diameters, Quantities & Coefficients) ---
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
        cpc = col_cpb.number_input("C", value=float(default_materials[mat]['cpc']), key=f"{mat}_cpc")
        
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

# --- Sidebar: Liquid Melts Holdup (Only active in Deadman Zone) ---
s_iron, rho_iron, cp_iron = 0.0, 7000.0, 800.0
s_slag, rho_slag, cp_slag = 0.0, 2600.0, 1200.0

if is_deadman:
    st.sidebar.header("🧪 Deadman Liquid Melts Holdup")
    with st.sidebar.expander("Liquid Iron & Slag Parameters", expanded=True):
        s_iron = st.slider("Liquid Iron Saturation (s_iron)", 0.0, 0.7, 0.15, 0.01, format="%.2f")
        rho_iron = st.number_input("Liquid Iron Density ρ_iron (kg/m³)", value=7000.0, step=50.0)
        cp_iron = st.number_input("Liquid Iron Specific Heat Cp_iron (J/kg·K)", value=800.0, step=10.0)
        
        st.divider()
        s_slag = st.slider("Liquid Slag Saturation (s_slag)", 0.0, 0.7, 0.10, 0.01, format="%.2f")
        rho_slag = st.number_input("Liquid Slag Density ρ_slag (kg/m³)", value=2600.0, step=50.0)
        cp_slag = st.number_input("Liquid Slag Specific Heat Cp_slag (J/kg·K)", value=1200.0, step=10.0)

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

# Effective porosity available for gas flow when liquid holdup is present
s_liquid_total = s_iron + s_slag
phi_gas = phi * max(0.0, (1.0 - s_liquid_total))

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

    # Liquid melt volumetric heat capacity contributions (for deadman / accumulation zones)
    vol_cp_iron = phi * s_iron * rho_iron * cp_iron
    vol_cp_slag = phi * s_slag * rho_slag * cp_slag

    # Effective Sauter Mean Diameter via Harmonic Mean of solid volume fractions
    inv_dp_sum = sum(vol_fracs[m] / materials[m]['dp'] for m in vol_fracs if materials[m]['dp'] > 0)
    dp_eff = (1.0 / inv_dp_sum) if inv_dp_sum > 0 else 0.025

    # Temperature-Dependent Gas Properties via Polynomial Evaluation
    rho_g = rhog_A + rhog_B * T + rhog_C * (T ** 2) + rhog_D * (T ** 3)
    mu_g = mu_A + mu_B * T + mu_C * (T ** 2) + mu_D * (T ** 3)
    cp_g = cpg_A + cpg_B * T + cpg_C * (T ** 2) + cpg_D * (T ** 3)
    gas_conductivity = kg_A + kg_B * T + kg_C * (T ** 2) + kg_D * (T ** 3)

    # Interphase Heat Transfer (Wakao and Kaguei using gas-available porosity / velocity path)
    Re = (rho_g * vg * dp_eff) / mu_g if mu_g > 0 else 0
    Pr = (cp_g * mu_g) / gas_conductivity if gas_conductivity > 0 else 0
    Nu = 2.0 + 1.1 * (Pr ** (1/3)) * (Re ** 0.6)
    
    h_sf = (Nu * gas_conductivity) / dp_eff if dp_eff > 0 else 0
    a_sf = (6.0 * (1.0 - phi)) / dp_eff if dp_eff > 0 else 0
    q_sf_coeff = h_sf * a_sf

    gas_state = {'rho': rho_g, 'mu': mu_g, 'cp': cp_g, 'k': gas_conductivity}
    coeffs = {
        'cp': (cp_A, cp_B, cp_C), 'ks': (ks_A, ks_B, ks_C), 
        'rhog': (rhog_A, rhog_B, rhog_C, rhog_D),
        'mu': (mu_A, mu_B, mu_C, mu_D), 'cpg': (cpg_A, cpg_B, cpg_C, cpg_D), 'kg': (kg_A, kg_B, kg_C, kg_D)
    }
    return (cp_s, ks_s, rho_s, rho_bulk), (cp_s_eff, ks_s_eff), (vol_cp_iron, vol_cp_slag), (dp_eff, Re, Pr, Nu, h_sf, a_sf, q_sf_coeff, gas_state), coeffs

(cp_s, ks_s, rho_s, rho_bulk), (cp_s_eff, ks_s_eff), (vol_cp_iron, vol_cp_slag), gas_interphase, coeffs = calculate_physics(temperature_k)
dp_eff, Re, Pr, Nu, h_sf, a_sf, q_sf_coeff, gas_state = gas_interphase
cp_A, cp_B, cp_C = coeffs['cp']
ks_A, ks_B, ks_C = coeffs['ks']
rhog_A, rhog_B, rhog_C, rhog_D = coeffs['rhog']
mu_A, mu_B, mu_C, mu_D = coeffs['mu']
cpg_A, cpg_B, cpg_C, cpg_D = coeffs['cpg']
kg_A, kg_B, kg_C, kg_D = coeffs['kg']

# --- Display Results ---
st.markdown("---")
st.subheader(f"📊 Computed Properties at T = {temperature_k:.1f} K (Total Void φ = {phi:.4f} | Gas Porosity φ_gas = {phi_gas:.4f})")

tab1, tab2, tab3 = st.tabs([
    "🟢 COMSOL LTNE: Solid Sub-Node", 
    "🟠 COMSOL Heat Transfer in Solids (Manual Matrix + Melts)",
    "⚙️ Temperature-Dependent Gas Dynamics & Coupling (q_sf)"
])

with tab1:
    st.info("💡 **LTNE Solid Matrix.** Uses True Density and intrinsic solid skeletal properties (Coke skeleton).")
    col1, col2, col3 = st.columns(3)
    col1.metric("True Density (ρ_s)", f"{rho_s:.2f} kg/m³")
    col2.metric("Solid Conductivity (k_s)", f"{ks_s:.3f} W/(m·K)")
    col3.metric("Solid Heat Capacity (Cp_s)", f"{cp_s:.2f} J/(kg·K)")
    
    st.markdown("#### Analytical Functions (T)")
    st.latex(rf"C_{{p,s}}(T) = {cp_A:.4f} + ({cp_B:.4e})T + ({cp_C:.4e})T^{{-2}}")
    st.latex(rf"k_s(T) = {ks_A:.4f} + ({ks_B:.4e})T + ({ks_C:.4e})T^2")

with tab2:
    if is_deadman:
        st.info("💡 **Deadman Zone Effective Matrix.** Includes coke skeleton scaling plus liquid iron and slag volumetric heat capacity contributions.")
        col1, col2, col3 = st.columns(3)
        col1.metric("Bulk Density (ρ_bulk)", f"{rho_bulk:.2f} kg/m³")
        col2.metric("Liquid Iron Holdup Vol. Cp", f"{vol_cp_iron:.1f} J/(m³·K)")
        col3.metric("Liquid Slag Holdup Vol. Cp", f"{vol_cp_slag:.1f} J/(m³·K)")
        
        st.markdown("#### Deadman Effective Volumetric Heat Capacity Formulation")
        st.latex(r"(\rho C_p)_{eff,deadman} = (1 - \phi)\rho_s C_{p,s}(T) + \phi \left[ s_{iron}\rho_{iron}C_{p,iron} + s_{slag}\rho_{slag}C_{p,slag} \right]")
    else:
        st.info("💡 **Manual Solid Matrix (Heat Transfer in Solids).** Uses Bulk Density and properties scaled strictly by (1 - phi).")
        col1, col2, col3 = st.columns(3)
        col1.metric("Bulk Density (ρ_bulk)", f"{rho_bulk:.2f} kg/m³")
        col2.metric("Effective Conductivity (k_eff = k_s · [1-φ])", f"{ks_s_eff:.3f} W/(m·K)")
        col3.metric("Effective Heat Capacity (Cp_eff = Cp_s · [1-φ])", f"{cp_s_eff:.2f} J/(kg·K)")
        
        st.markdown("#### Analytical Functions (T)")
        st.latex(rf"C_{{p,eff}}(T) = (1 - {phi:.4f}) \cdot C_{{p,s}}(T)")
        st.latex(rf"k_{{eff}}(T) = (1 - {phi:.4f}) \cdot k_s(T)")

with tab3:
    st.info(f"💡 **Gas Dynamics & Coupling evaluated as functions of T** (Evaluated at T = {temperature_k:.1f} K).")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Reynolds Number Re(T)", f"{Re:.1f}")
    col2.metric("Prandtl Number Pr(T)", f"{Pr:.3f}")
    col3.metric("Nusselt Number Nu(T)", f"{Nu:.2f}")
    col4.metric("Gas-Available Porosity φ_gas", f"{phi_gas:.4f}")
    
    st.markdown("#### Gas Properties as Functions of Temperature ($T$)")
    gcol1, gcol2, gcol3, gcol4 = st.columns(4)
    gcol1.metric("Gas Density ρ_g(T)", f"{gas_state['rho']:.3f} kg/m³")
    gcol2.metric("Viscosity μ_g(T)", f"{gas_state['mu']:.2e} Pa·s")
    gcol3.metric("Specific Heat Cp_g(T)", f"{gas_state['cp']:.2f} J/(kg·K)")
    gcol4.metric("Conductivity k_g(T)", f"{gas_state['k']:.4f} W/(m·K)")

    st.markdown("#### Interphase Heat Transfer Coefficient & Coupling Terms as Functions of ($T$)")
    col5, col6 = st.columns(2)
    col5.metric("Specific Surface Area a_sf", f"{a_sf:.1f} m²/m³")
    col6.metric("Interphase HTC h_sf(T)", f"{h_sf:.2f} W/(m²·K)")
    
    st.markdown("#### Analytical Temperature-Dependent Formulation")
    st.latex(r"Re(T) = \frac{\rho_g(T) \cdot v_g \cdot d_{p,eff}}{\mu_g(T)}")
    st.latex(r"Pr(T) = \frac{C_{p,g}(T) \cdot \mu_g(T)}{k_g(T)}")
    st.latex(r"Nu(T) = 2.0 + 1.1 \cdot [Pr(T)]^{1/3} \cdot [Re(T)]^{0.6}")
    st.latex(rf"h_{{sf}}(T) = \frac{{Nu(T) \cdot k_g(T)}}{{d_{{p,eff}}}} = {h_sf:.2f} \text{{ [W/(m²·K)] at selected T}}")
    st.latex(rf"q_{{sf}}(T_{{fluid}}, T_{{solid}}, T) = {a_sf:.2f} \cdot h_{{sf}}(T) \cdot (T_{{fluid}} - T_{{solid}}) \text{{ [W/m³]}}")

# --- COMSOL Text Export Content Generator ---
deadman_export_text = f"""
--------------------------------------------------------------------
DEADMAN ZONE LIQUID MELTS HOOK (INTERSTITIAL PHASES)
--------------------------------------------------------------------
Liquid Iron Saturation (s_iron) = {s_iron:.4f}
Liquid Iron Density (rho_iron)   = {rho_iron:.2f} [kg/m^3]
Liquid Iron Specific Heat (Cp_iron) = {cp_iron:.2f} [J/(kg·K)]

Liquid Slag Saturation (s_slag)  = {s_slag:.4f}
Liquid Slag Density (rho_slag)   = {rho_slag:.2f} [kg/m^3]
Liquid Slag Specific Heat (Cp_slag) = {cp_slag:.2f} [J/(kg·K)]

Gas-Available Porosity (phi_gas) = {phi_gas:.4f}
Volumetric Heat Capacity Contribution (Iron) = {vol_cp_iron:.2f} [J/(m^3·K)]
Volumetric Heat Capacity Contribution (Slag) = {vol_cp_slag:.2f} [J/(m^3·K)]
""" if is_deadman else ""

comsol_text = f"""====================================================================
BLAST FURNACE FULL TEMPERATURE-DEPENDENT MODEL EXPORT (COMSOL)
Operating Zone: {bf_zone}
Evaluated at Reference Temp: {temperature_k:.2f} K | Total Porosity (phi): {phi:.4f}
====================================================================

--------------------------------------------------------------------
1. TEMPERATURE-DEPENDENT GAS PROPERTIES (FLUID DOMAIN)
--------------------------------------------------------------------
[Analytic Function: Gas Density rho_g(T)]
Expression: {rhog_A:.6f} + ({rhog_B:.6e})*T + ({rhog_C:.6e})*T^2 + ({rhog_D:.6e})*T^3

[Analytic Function: Gas Viscosity mu_g(T)]
Expression: {mu_A:.6e} + ({mu_B:.6e})*T + ({mu_C:.6e})*T^2 + ({mu_D:.6e})*T^3

[Analytic Function: Gas Specific Heat Cp_g(T)]
Expression: {cpg_A:.6f} + ({cpg_B:.6e})*T + ({cpg_C:.6e})*T^2 + ({cpg_D:.6e})*T^3

[Analytic Function: Gas Conductivity k_g(T)]
Expression: {kg_A:.6f} + ({kg_B:.6e})*T + ({kg_C:.6e})*T^2 + ({kg_D:.6e})*T^3

--------------------------------------------------------------------
2. HEAT TRANSFER IN POROUS MEDIA (LTNE) - SOLID SUB-NODE (Coke Skeleton)
--------------------------------------------------------------------
rho_s = {rho_s:.2f} [kg/m^3]  // True density of coke skeleton
porosity_phi = {phi:.4f}

[Analytic Function: Solid Heat Capacity Cp_s(T)]
Expression: {cp_A:.6f} + ({cp_B:.6e})*T + ({cp_C:.6e})*T^(-2)

[Analytic Function: Solid Conductivity k_s(T)]
Expression: {ks_A:.6f} + ({ks_B:.6e})*T + ({ks_C:.6e})*T^2
{deadman_export_text}
--------------------------------------------------------------------
3. INTERPHASE HEAT TRANSFER COUPLING (FLUID-SOLID) AS FUNCTIONS OF T
--------------------------------------------------------------------
dp_eff = {dp_eff:.6f} [m]
a_sf = {a_sf:.6f} [m^2/m^3]

// Wakao-Kaguei Correlations as Functions of Temperature T:
// Re(T) = (rho_g(T) * vg * dp_eff) / mu_g(T)
// Pr(T) = (cp_g(T) * mu_g(T)) / kg(T)
// Nu(T) = 2.0 + 1.1 * (Pr(T))^(1/3) * (Re(T))^0.6
// h_sf(T) = (Nu(T) * kg(T)) / dp_eff
// q_sf(T_fluid, T_solid, T) = a_sf * h_sf(T) * (T_fluid - T_solid)

====================================================================
"""

st.download_button(
    label="📥 Download Full Temperature-Dependent COMSOL Variables (.txt)",
    data=comsol_text,
    file_name=f"COMSOL_BF_{bf_zone.split()[0]}_Temperature_Functions.txt",
    mime="text/plain"
)
