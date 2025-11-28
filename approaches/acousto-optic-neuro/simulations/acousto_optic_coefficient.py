"""
Calculate refractive index modulation by ultrasound in brain tissue.

The acousto-optic effect relates pressure to refractive index change through strain:
    delta_n = n^3/2 * p * S

where strain S = P / K (pressure / bulk modulus)

So: delta_n = (n^3 / 2) * p * (P / K)

where:
    n = baseline refractive index
    p = photoelastic coefficient (dimensionless, ~0.3 for water/tissue)
    P = acoustic pressure amplitude (Pa)
    K = bulk modulus (Pa) ~ 2.2 GPa for water/soft tissue

Key question: What pressure can we achieve at cortex depth (2.5 cm)?
"""

import numpy as np

print("Acousto-Optic Coefficient in Brain Tissue")
print("=" * 70)

# Material properties for brain tissue
n_tissue = 1.37  # refractive index at NIR wavelengths
p_photoelastic = 0.31  # photoelastic coefficient (dimensionless, similar to water)
K_bulk = 2.2e9  # Pa (bulk modulus, similar to water ~2.2 GPa)

print(f"\nMaterial Properties (Brain Tissue at NIR):")
print(f"  Refractive index: {n_tissue}")
print(f"  Photoelastic coefficient: {p_photoelastic}")
print(f"  Bulk modulus: {K_bulk/1e9:.1f} GPa")
print()

# Calculate acousto-optic coefficient
# delta_n = (n^3 / 2) * p * (P / K)
ao_coefficient = (n_tissue**3 / 2) * p_photoelastic / K_bulk
print(f"Acousto-optic coefficient: {ao_coefficient:.4e} Pa^-1")
print(f"  This gives: delta_n = {ao_coefficient:.4e} * P (where P is in Pa)")
print()

# Ultrasound pressure achievable at depth
print("Ultrasound Pressure at Cortex Depth")
print("-" * 70)

# Typical ultrasound transducer parameters
I_spta = [0.1, 0.5, 1.0, 3.0, 5.0]  # W/cm^2 (spatial peak temporal average)
# FDA limit for diagnostic ultrasound: 720 mW/cm^2 = 0.72 W/cm^2 (Ispta)
# For brain imaging, typically use lower values: 0.1-1 W/cm^2

c_tissue = 1540  # m/s
rho_tissue = 1050  # kg/m^3
Z = rho_tissue * c_tissue  # acoustic impedance

print(f"Speed of sound: {c_tissue} m/s")
print(f"Tissue density: {rho_tissue} kg/m^3")
print(f"Acoustic impedance: {Z:.0f} kg/(m^2·s)")
print()

# Attenuation at cortex depth (2.5 cm)
frequency = 1.0e6  # 1 MHz
skull_thickness = 0.007  # 7 mm
skull_attenuation_coeff = 10  # dB/cm/MHz
tissue_attenuation_coeff = 0.6  # dB/cm/MHz
tissue_path = 0.018  # 1.8 cm

skull_loss_dB = skull_attenuation_coeff * (skull_thickness * 100) * (frequency / 1e6)
tissue_loss_dB = tissue_attenuation_coeff * (tissue_path * 100) * (frequency / 1e6)
total_loss_dB = skull_loss_dB + tissue_loss_dB

print(f"Attenuation at 1 MHz to cortex (2.5 cm depth):")
print(f"  Skull loss: {skull_loss_dB:.1f} dB")
print(f"  Tissue loss: {tissue_loss_dB:.1f} dB")
print(f"  Total loss: {total_loss_dB:.1f} dB")
print()

attenuation_factor = 10**(-total_loss_dB / 10)
print(f"Intensity reduction factor: {attenuation_factor:.4f} ({attenuation_factor*100:.2f}%)")
print()

# Calculate pressure amplitude at cortex for various input intensities
print("Pressure Amplitude at Cortex vs Input Intensity")
print("-" * 70)
print(f"{'Input I (W/cm^2)':<20} {'I at cortex':<20} {'Pressure (Pa)':<20} {'Pressure (MPa)':<20}")
print("-" * 70)

pressures_at_cortex = []
for I_in in I_spta:
    I_in_SI = I_in * 1e4  # convert W/cm^2 to W/m^2
    I_cortex = I_in_SI * attenuation_factor  # W/m^2

    # Relation: I = P^2 / (2 * Z)
    P_cortex = np.sqrt(2 * Z * I_cortex)  # Pa

    pressures_at_cortex.append(P_cortex)

    print(f"{I_in:<20.1f} {I_cortex/1e4:<20.4f} {P_cortex:<20.0f} {P_cortex/1e6:<20.4f}")

print()

# Calculate refractive index modulation
print("Refractive Index Modulation at Cortex")
print("-" * 70)
print(f"{'Input I (W/cm^2)':<20} {'Pressure (Pa)':<20} {'delta_n':<20} {'delta_n (sci)':<20}")
print("-" * 70)

for i, I_in in enumerate(I_spta):
    P = pressures_at_cortex[i]
    delta_n = ao_coefficient * P
    print(f"{I_in:<20.1f} {P:<20.0f} {delta_n:<20.10f} {delta_n:<20.2e}")

print()

# Check claim: delta_n > 10^-6
print("=" * 70)
print("EVALUATION OF CLAIM c1: delta_n > 10^-6")
print("=" * 70)

threshold = 1e-6
print(f"\nThreshold: delta_n > {threshold:.0e}")
print()

for i, I_in in enumerate(I_spta):
    P = pressures_at_cortex[i]
    delta_n = ao_coefficient * P
    meets_threshold = delta_n > threshold

    status = "✓ YES" if meets_threshold else "✗ NO"
    print(f"At I = {I_in:.1f} W/cm^2: delta_n = {delta_n:.2e}  {status}")

print()
print("ANALYSIS:")
print("-" * 70)

# Find minimum intensity needed
P_needed = threshold / ao_coefficient
I_needed_cortex = P_needed**2 / (2 * Z)  # W/m^2
I_needed_surface = I_needed_cortex / attenuation_factor  # W/m^2
I_needed_surface_wcm2 = I_needed_surface / 1e4  # W/cm^2

print(f"To achieve delta_n = 10^-6:")
print(f"  Required pressure at cortex: {P_needed:.0f} Pa = {P_needed/1e6:.4f} MPa")
print(f"  Required intensity at cortex: {I_needed_cortex:.2f} W/m^2")
print(f"  Required intensity at surface: {I_needed_surface:.2f} W/m^2 = {I_needed_surface_wcm2:.3f} W/cm^2")
print()

FDA_limit = 0.72  # W/cm^2 (Ispta for diagnostic ultrasound)
print(f"FDA diagnostic ultrasound limit: {FDA_limit} W/cm^2 (Ispta)")
print()

if I_needed_surface_wcm2 < FDA_limit:
    print(f"✓ ACHIEVABLE: Required intensity ({I_needed_surface_wcm2:.3f} W/cm^2) is below FDA limit")
    print(f"  Safety margin: {FDA_limit/I_needed_surface_wcm2:.1f}x")
else:
    print(f"✗ CHALLENGING: Required intensity ({I_needed_surface_wcm2:.3f} W/cm^2) exceeds FDA limit")
    print(f"  Would need: {I_needed_surface_wcm2/FDA_limit:.1f}x FDA limit")

print()

# Test with realistic safe intensity
safe_intensity = 0.5  # W/cm^2 (conservative, below FDA limit)
I_safe_SI = safe_intensity * 1e4
I_safe_cortex = I_safe_SI * attenuation_factor
P_safe_cortex = np.sqrt(2 * Z * I_safe_cortex)
delta_n_safe = ao_coefficient * P_safe_cortex

print(f"At safe operating intensity ({safe_intensity} W/cm^2):")
print(f"  Pressure at cortex: {P_safe_cortex:.0f} Pa")
print(f"  delta_n: {delta_n_safe:.2e}")
print(f"  Meets threshold (>10^-6)? {delta_n_safe > threshold}")
print()

print("=" * 70)
print("CONCLUSION:")
print("=" * 70)
if delta_n_safe > threshold:
    print(f"✓ Claim c1 is SUPPORTED")
    print(f"  At safe intensities (0.5 W/cm^2), delta_n = {delta_n_safe:.2e} > 10^-6")
else:
    print(f"✗ Claim c1 is NOT SUPPORTED")
    print(f"  At safe intensities (0.5 W/cm^2), delta_n = {delta_n_safe:.2e} < 10^-6")
    print(f"  Would need {threshold/delta_n_safe:.1f}x higher intensity")
