import streamlit as st
import pandas as pd
import numpy as np

# Page Configuration
st.set_page_config(page_title="BF Burden Properties Calculator", layout="wide")

st.title("Blast Furnace Burden Properties Calculator")
st.markdown("Calculate effective packed bed properties (Porosity, Density, Fractions) for COMSOL Multiphysics.")

# Define the burden materials
materials = ["Coke", "Iron Ore Pellets", "Sinter", "Lump Ore"]

# Default values based on typical blast furnace ranges
defaults = {
    "Coke": {"mass": 500.0, "rho_bulk": 500.0, "rho_true": 1850.0},
    "Iron Ore Pellets": {"mass": 1000.0, "rho_bulk": 2100.0, "rho_true": 4000.0},
    "Sinter": {"mass": 1500.0, "rho_bulk": 1800.0, "rho_true": 3800.0},
    "Lump Ore": {"mass": 500.0, "rho_bulk": 2000.0, "rho_true": 4200.0},
}

st.header("1. Burden Material Inputs")
st.markdown("Enter the **Mass**, **Bulk Density**, and **True Density**. The app will automatically calculate both **Bulk Volume** and **True Volume** for the mixture mechanics.")

inputs = {}
cols = st.columns(4)

for i, mat in enumerate(materials):
    with cols[i]:
        st.subheader(mat)
        
        # Dual inputs: handling standard numerical inputs as requested
        mass = st.number_input(f"Mass (kg) - {mat}", value=defaults[mat]["mass"], step=10.0, min_value=0.0)
        rho_bulk = st.number_input(f"Bulk Density (kg/m³) - {mat}", value=defaults[mat]["rho_bulk"], step=10.0, min_value=1.0)
        rho_true = st.number_input(f"True Density (kg/m³) - {mat}", value=defaults[mat]["rho_true"], step=10.0, min_value=1.0)
        
        # Calculate the volumes based on mass and density
        vol_bulk = mass / rho_bulk if rho_bulk > 0 else 0
        vol_true = mass / rho_true if rho_true > 0 else 0
        
        # Individual Porosity: eps = 1 - (rho_bulk / rho_true)
        porosity = 1.0 - (rho_bulk / rho_true) if rho_true > 0 else 0
        
        inputs[mat] = {
            "Mass [kg]": mass,
            "Bulk Density [kg/m³]": rho_bulk,
            "True Density [kg/m³]": rho_true,
            "Bulk Volume [m³]": vol_bulk,
            "True Volume [m³]": vol_true,
            "Porosity [-]": porosity
        }

# Create a DataFrame for the raw properties and calculated volumes
df_individual = pd.DataFrame(inputs).T

st.header("2. Individual Component Properties & Volumes")
st.dataframe(df_individual.style.format("{:.4f}"), use_container_width=True)

# ---------------------------------------------------------
# Mixture & Effective Property Calculations
# ---------------------------------------------------------
total_mass = df_individual["Mass [kg]"].sum()
total_bulk_vol = df_individual["Bulk Volume [m³]"].sum()
total_true_vol = df_individual["True Volume [m³]"].sum()

# Calculate Fractions (Mass and Volume)
df_individual["Mass Fraction (x_i)"] = df_individual["Mass [kg]"] / total_mass if total_mass > 0 else 0
df_individual["Bulk Vol Fraction (v_bulk_i)"] = df_individual["Bulk Volume [m³]"] / total_bulk_vol if total_bulk_vol > 0 else 0
df_individual["True Vol Fraction (v_true_i)"] = df_individual["True Volume [m³]"] / total_true_vol if total_true_vol > 0 else 0

st.header("3. Mixture Fractions")
st.dataframe(df_individual[["Mass Fraction (x_i)", "Bulk Vol Fraction (v_bulk_i)", "True Vol Fraction (v_true_i)"]].style.format("{:.4f}"), use_container_width=True)

# Effective Properties for the Packed Bed
eff_bulk_density = total_mass / total_bulk_vol if total_bulk_vol > 0 else 0
eff_true_density = total_mass / total_true_vol if total_true_vol > 0 else 0
eff_porosity = 1.0 - (eff_bulk_density / eff_true_density) if eff_true_density > 0 else 0

st.header("4. Effective Packed Bed Properties (COMSOL Inputs)")
col1, col2, col3 = st.columns(3)
col1.metric("Effective Bulk Density", f"{eff_bulk_density:.2f} kg/m³")
col2.metric("Effective True Density", f"{eff_true_density:.2f} kg/m³")
col3.metric("Effective Bed Porosity", f"{eff_porosity:.4f}")

# LaTeX Explanations with f-string fixes (using double braces {{ }})
st.markdown("### Governing Equations")
st.latex(rf"\rho_{{bulk, eff}} = \frac{{\sum m_i}}{{\sum V_{{bulk, i}}}} = \frac{{{total_mass:.2f}}}{{{total_bulk_vol:.2f}}} = {eff_bulk_density:.2f} \text{{ kg/m}}^3")
st.latex(rf"\rho_{{true, eff}} = \frac{{\sum m_i}}{{\sum V_{{true, i}}}} = \frac{{{total_mass:.2f}}}{{{total_true_vol:.2f}}} = {eff_true_density:.2f} \text{{ kg/m}}^3")
st.latex(rf"\epsilon_{{eff}} = 1 - \frac{{\rho_{{bulk, eff}}}}{{\rho_{{true, eff}}}} = 1 - \frac{{{eff_bulk_density:.2f}}}{{{eff_true_density:.2f}}} = {eff_porosity:.4f}")

# ---------------------------------------------------------
# COMSOL Variables Export
# ---------------------------------------------------------
st.header("5. COMSOL Parameters Export")
st.markdown("Copy these calculated parameters directly into your COMSOL **Parameters** or **Variables** node for the Brinkman equations / LTNE interfaces.")

comsol_code = f"""// Blast Furnace Burden - Effective Bed Properties
rho_bulk_eff = {eff_bulk_density:.2f} [kg/m^3];  // Effective Bulk Density
rho_true_eff = {eff_true_density:.2f} [kg/m^3];  // Effective True Density
eps_eff = {eff_porosity:.4f};                  // Effective Bed Porosity

// Component Mass Fractions
x_coke = {df_individual.loc["Coke", "Mass Fraction (x_i)"]:.4f};
x_pellets = {df_individual.loc["Iron Ore Pellets", "Mass Fraction (x_i)"]:.4f};
x_sinter = {df_individual.loc["Sinter", "Mass Fraction (x_i)"]:.4f};
x_lump = {df_individual.loc["Lump Ore", "Mass Fraction (x_i)"]:.4f};
"""

st.code(comsol_code, language="c")
