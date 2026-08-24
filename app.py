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
for a **single solid-phase mixed burden** (Coke, Sinter, Pellet, and Lump Ore) using 
mass-fraction weighting, volume-based solid blending, and the **Yagi-Kunii packed-bed model**.
""")

# --- Sidebar Inputs ---
st.sidebar.header("⚙️ Simulation Parameters")

temperature_k = st.sidebar.slider(
    "Operating Temperature (K)", 
    min_value=298.0, 
    max_value=1500.0, 
    value=1000.0, 
    step=10.0,
    help="Absolute temperature in Kelvin"
)

st.sidebar.subheader("Burden Structure (Mass Percentages)")
coke_p = st.sidebar.slider("Coke (%)", 0.0, 100.0, 20.0, 1.0)
sinter_p = st.sidebar.slider("Sinter (%)", 0.0, 100.0, 35.0, 1.0)
pellet_p = st.sidebar.slider("Pellet (%)", 0.0, 100.0, 30.0, 1.0)
lump_p = st.sidebar.slider("Lump Ore (%)", 0.0, 100.0, 15.0, 1.0)

# Normalize percentages to sum to 1.0
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

if abs(total_p - 100.0) > 0.01:
    st.sidebar.info(f"Normalized from {total_p:.1f}% to 100%. Effective mass breakdown:")
    for mat, w in mass_fractions.items():
        st.sidebar.text(f"- {mat.capitalize()}: {w*100:.1f}%")

with st.sidebar.expander("Advanced Packed-Bed Settings"):
    bed_void_fraction = st.slider("Bed Void Fraction (Porosity φ)", 0.30, 0.50, 0.40, 0.01)
    mean_particle_diameter = st.slider("Mean Particle Diameter (m)", 0.01, 0.05, 0.025, 0.001)
    gas_conductivity = st.slider("Interstitial Gas Conductivity (W/m·K)", 0.02, 0.08, 0.04, 0.005)

# --- Calculation Engine ---
def calculate_single_phase_burden(mass_fractions, T, kg, dp, phi):
    materials = {
        'coke': {
            'true_density': 1850.0, 'bulk_density': 480.0,
            'cp_coeffs': (860.0, 5.40e-1, -2.75e7),
            'k_coeffs': (0.28, 1.75e-3, -3.20e-7)
        },
        'sinter': {
            'true_density': 3450.0, 'bulk_density': 1700.0,
            'cp_coeffs': (745.0, 2.60e-1, -1.25e7),
            'k_coeffs': (0.92, 0.48e-3, 0.85e-7)
        },
        'pellet': {
            'true_density': 3350.0, 'bulk_density': 2050.0,
            'cp_coeffs': (620.5, 6.15e-1, -1.18e7),
            'k_coeffs': (1.42, -0.38e-3, 1.15e-7)
        },
        'lump': {
            'true_density': 4600.0, 'bulk_density': 2200.0,
            'cp_coeffs': (615.0, 5.85e-1, -1.15e7),
            'k_coeffs': (2.15, -0.65e-3, 0.25e-7)
        }
    }
    
    # 1. Effective Specific Heat (Mass-weighted)
    cp_eff = sum(w * (materials[mat]['cp_coeffs'][0] + materials[mat]['cp_coeffs'][1] * T + materials[mat]['cp_coeffs'][2] * (T ** -2)) 
                 for mat, w in mass_fractions.items())
    
    # 2. Volume fractions for solid conductivity blending
    volumes = {mat: w / materials[mat]['true_density'] for mat, w in mass_fractions.items()}
    total_vol = sum(volumes.values())
    vol_fractions = {mat: v / total_vol for mat, v in volumes.items()}
    
    ks_eff = sum(x_v * (materials[mat]['k_coeffs'][0] + materials[mat]['k_coeffs'][1] * T + materials[mat]['k_coeffs'][2] * (T ** 2))
                 for mat, x_v in vol_fractions.items())
    
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
    
    return cp_eff, ks_eff, k_bed_effective, rho_bed_effective, rho_solid_avg

cp_eff, ks_eff, k_bed_effective, rho_bed_effective, rho_solid_avg = calculate_single_phase_burden(
    mass_fractions, temperature_k, gas_conductivity, mean_particle_diameter, bed_void_fraction
)

# --- Display Results ---
st.markdown("---")
st.subheader("📊 Homogenized Single-Phase Output Parameters")

col1, col2 = st.columns(2)

with col1:
    st.metric(label="Effective Specific Heat ($C_p$)", value=f"{cp_eff:.2f} J/(kg·K)")
    st.metric(label="Packed Bed Bulk Density ($\rho_{\text{bed}}$)", value=f"{rho_bed_effective:.2f} kg/m³")
    st.metric(label="Solid Skeleton Density ($\rho_{\text{solid}}$)", value=f"{rho_solid_avg:.2f} kg/m³")

with col2:
    st.metric(label="Packed Bed Effective Conductivity ($k_{\text{eff}}$)", value=f"{k_bed_effective:.3f} W/(m·K)")
    st.metric(label="Equivalent Solid Conductivity ($k_s$)", value=f"{ks_eff:.3f} W/(m·K)")
    st.metric(label="Bed Void Fraction ($\phi$)", value=f"{bed_void_fraction:.2f}")

# Visual Breakdown Chart
st.markdown("---")
st.subheader("📋 Input Burden Structure Summary")
chart_data = {mat.capitalize(): [w * 100] for mat, w in mass_fractions.items()}
st.bar_chart(chart_data)