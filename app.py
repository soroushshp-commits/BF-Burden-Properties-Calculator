import streamlit as st
import numpy as np

# Page Configuration
st.set_page_config(
    page_title="Blast Furnace Burden Thermophysical Simulator",
    page_icon="🔥",
    layout="wide"
)

st.title("🔥 Blast Furnace Burden Homogenization Tool")
st.markdown("""
This application calculates the temperature-dependent effective thermophysical properties 
for a **single solid-phase mixed burden** (Coke, Sinter, Pellet, and Lump Ore). You can customize 
individual material properties and coefficients, and view the final analytical functions of temperature below.
""")

# --- Sidebar: Material Property Customization ---
st.sidebar.header("🛠️ Material Database & Coefficients")

# Default values dictionary
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

# --- Sidebar: Simulation Operating Conditions ---
st.sidebar.header("⚙️ Operating Conditions")
temperature_k = st.sidebar.slider(
    "Operating Temperature (K)", 
    min_value=298.0, 
    max_value=1500.0, 
    value=1000.0, 
    step=10.0
)

st.sidebar.subheader("Burden Structure (Mass Percentages)")
coke_p = st.sidebar.slider("Coke (%)", 0.0, 100.0, 20.0, 1.0)
sinter_p = st.sidebar.slider("Sinter (%)", 0.0, 100.0, 35.0, 1.0)
pellet_p = st.sidebar.slider("Pellet (%)", 0.0, 100.0, 30.0, 1.0)
lump_p = st.sidebar.slider("Lump Ore (%)", 0.0, 100.0, 15.0, 1.0)

total_p = coke_p + sinter_p + pellet_p + lump_p
if total_p == 0:
    total_p = 1.0
    coke_p, sinter_p, pellet_p, lump_p = 25.0, 25.0, 25.0, 25.0

mass_fractions = {
    'coke': coke_p / total_p,
    'sinter': sinter_p / total_p,
    'pellet': pellet_p / total_p,
    'lump': lump_p / total_p
}

with st.sidebar.expander("Advanced Packed-Bed Settings"):
    bed_void_fraction = st.slider("Bed Void Fraction (Porosity φ)", 0.30, 0.50, 0.40, 0.01)
    mean_particle_diameter = st.slider("Mean Particle Diameter (m)", 0.01, 0.05, 0.025, 0.001)
    gas_conductivity = st.slider("Interstitial Gas Conductivity (W/m·K)", 0.02, 0.08, 0.04, 0.005)

# --- Calculation Engine ---
def calculate_single_phase_burden(mass_fractions, T, kg, dp, phi, materials):
    # 1. Effective Specific Heat (Mass-weighted) & Aggregate Polynomial Coeffs
    cp_eff = 0.0
    cp_A_eff, cp_B_eff, cp_C_eff = 0.0, 0.0, 0.0
    for mat, w in mass_fractions.items():
        A, B, C = materials[mat]['cp_coeffs']
        cp_A_eff += w * A
        cp_B_eff += w * B
        cp_C_eff += w * C
        cp_eff += w * (A + B * T + C * (T ** -2))
    
    # 2. Volume fractions for solid conductivity blending
    volumes = {mat: w / materials[mat]['true_density'] for mat, w in mass_fractions.items()}
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
    
    # 3. Densities and Porosity
    rho_solid_avg = sum(vol_fractions[mat] * materials[mat]['true_density'] for mat in mass_fractions)
    rho_bed_effective = (1.0 - phi) * rho_solid_avg
    
    # 4. Yagi-Kunii Packed-Bed Effective Thermal Conductivity
    sigma = 5.67e-8
    emissivity = 0.88
    alpha_yk, gamma_yk, beta_yk = 0.8, 0.95, 0.95
    
    conduction_term = kg * (phi + ((1.0 - phi) / ((alpha_yk * (kg / ks_eff)) + gamma_yk)))
    radiation_term = 4.0 * beta_yk * emissivity * sigma * dp * (T ** 3)
    k_bed_effective = conduction_term + radiation_term
    
    formula_coeffs = {
        'cp': (cp_A_eff, cp_B_eff, cp_C_eff),
        'ks': (ks_A_eff, ks_B_eff, ks_C_eff)
    }
    
    return cp_eff, ks_eff, k_bed_effective, rho_bed_effective, rho_solid_avg, formula_coeffs

cp_eff, ks_eff, k_bed_effective, rho_bed_effective, rho_solid_avg, formula_coeffs = calculate_single_phase_burden(
    mass_fractions, temperature_k, gas_conductivity, mean_particle_diameter, bed_void_fraction, materials
)

# --- Display Results ---
st.markdown("---")
st.subheader("📊 Homogenized Single-Phase Output Parameters")

col1, col2 = st.columns(2)

with col1:
    st.metric(label=f"Effective Specific Heat ($C_p$) at {temperature_k} K", value=f"{cp_eff:.2f} J/(kg·K)")
    st.metric(label="Packed Bed Bulk Density ($\rho_{\text{bed}}$)", value=f"{rho_bed_effective:.2f} kg/m³")
    st.metric(label="Solid Skeleton Density ($\rho_{\text{solid}}$)", value=f"{rho_solid_avg:.2f} kg/m³")

with col2:
    st.metric(label=f"Packed Bed Effective Conductivity ($k_{\text{eff}}$) at {temperature_k} K", value=f"{k_bed_effective:.3f} W/(m·K)")
    st.metric(label=f"Equivalent Solid Conductivity ($k_s$) at {temperature_k} K", value=f"{ks_eff:.3f} W/(m·K)")
    st.metric(label="Bed Void Fraction ($\phi$)", value=f"{bed_void_fraction:.2f}")

# --- Analytical Formulas Display ---
st.markdown("---")
st.subheader("📐 Final Analytical Formulas (as a Function of Temperature $T$)")

cp_A, cp_B, cp_C = formula_coeffs['cp']
ks_A, ks_B, ks_C = formula_coeffs['ks']

st.markdown(f"""
Based on your current burden mass fractions and coefficient overrides, the effective properties are governed by the following temperature-dependent expressions ($T$ in Kelvin):

1. **Effective Specific Heat Capacity $C_{{p,\text{{eff}}}}(T)$**:
   $$C_{{p,\text{{eff}}}}(T) = {cp_A:.3f} + ({cp_B:.3e}) \cdot T + ({cp_C:.3e}) \cdot T^{{-2}} \\;\\; \\text{{[J/(kg·K)]}}$$

2. **Equivalent Solid Thermal Conductivity $k_{{s,\text{{eff}}}}(T)$**:
   $$k_{{s,\text{{eff}}}}(T) = {ks_A:.3f} + ({ks_B:.3e}) \cdot T + ({ks_C:.3e}) \cdot T^2 \\;\\; \\text{{[W/(m·K)]}}$$

3. **Effective Packed Bed Bulk Density $\rho_{{\text{{bed}}}}$** (Constant with respect to $T$):
   $$\rho_{{\text{{bed}}}} = {rho_bed_effective:.2f} \\;\\; \\text{{[kg/m³]}}$$

4. **Packed Bed Effective Thermal Conductivity $k_{{\text{{eff}}}}(T)$** (Yagi-Kunii formulation evaluated with current $ks$):
   $$k_{{\text{{eff}}}}(T) = {gas_conductivity} \cdot \left({bed_void_fraction} + \frac{{1 - {bed_void_fraction}}}{{0.8 \cdot \frac{{{gas_conductivity}}}{{{ks_eff:.4f}}} + 0.95}}\right) + (4 \cdot 0.95 \cdot 0.88 \cdot 5.67\times 10^{{-8}} \cdot {mean_particle_diameter}) \cdot T^3$$
""")

# Visual Breakdown Chart
st.markdown("---")
st.subheader("📋 Input Burden Structure Summary")
chart_data = {mat.capitalize(): [w * 100] for mat, w in mass_fractions.items()}
st.bar_chart(chart_data)
