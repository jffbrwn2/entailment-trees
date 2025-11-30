"""
Calculate phase modulation depth from acousto-optic effect.

Using the formula from c16: delta_phi = (2*pi/lambda) * delta_n * L

Given:
- c1: delta_n > 10^-6 (we found ~9e-6 at safe intensities)
- c2: L > 1 mm (we found ~2-5 mm for focal spots)
- c14: lambda ~ 700-900 nm (we confirmed this)

Calculate: delta_phi and check if > 5*10^-3 radians
"""

import numpy as np

print("Phase Modulation Depth Calculation")
print("=" * 70)

# Parameters from previous simulations
lambda_range = [700e-9, 800e-9, 900e-9]  # meters
delta_n_safe = 9.09e-6  # from acousto_optic_coefficient.py at 0.5 W/cm^2
L_range = [2e-3, 3e-3, 5e-3]  # meters (from photon_path_length.py)

print(f"\nInput Parameters:")
print(f"  Wavelength range: {[l*1e9 for l in lambda_range]} nm")
print(f"  Refractive index modulation (delta_n): {delta_n_safe:.2e}")
print(f"  Path length range (L): {[l*1000 for l in L_range]} mm")
print()

# Calculate phase modulation depth
print("Phase Modulation Depth: delta_phi = (2*pi/lambda) * delta_n * L")
print("-" * 70)
print(f"{'lambda (nm)':<15} {'L (mm)':<15} {'delta_phi (rad)':<20} {'delta_phi (sci)':<20}")
print("-" * 70)

all_results = []

for wavelength in lambda_range:
    for L in L_range:
        delta_phi = (2 * np.pi / wavelength) * delta_n_safe * L
        all_results.append((wavelength, L, delta_phi))
        print(f"{wavelength*1e9:<15.0f} {L*1000:<15.1f} {delta_phi:<20.6f} {delta_phi:<20.2e}")

print()

# Check against threshold
threshold = 5e-3  # 5 * 10^-3 radians

print("=" * 70)
print(f"EVALUATION: Is delta_phi > {threshold:.0e} radians?")
print("=" * 70)
print()

meets_threshold_count = 0
total_count = len(all_results)

for wavelength, L, delta_phi in all_results:
    meets = delta_phi > threshold
    status = "✓ YES" if meets else "✗ NO"
    if meets:
        meets_threshold_count += 1

    print(f"λ={wavelength*1e9:.0f}nm, L={L*1000:.1f}mm: δφ={delta_phi:.2e}  {status}")

print()
print("-" * 70)

# Summary with typical case
lambda_typical = 800e-9  # 800 nm (middle of fNIRS range)
L_typical = 3e-3  # 3 mm (middle of focal spot range)
delta_phi_typical = (2 * np.pi / lambda_typical) * delta_n_safe * L_typical

print(f"\nTypical case (λ=800nm, L=3mm):")
print(f"  delta_phi = {delta_phi_typical:.2e} radians")
print(f"  Threshold: {threshold:.0e} radians")
print(f"  Ratio: {delta_phi_typical/threshold:.2f}x threshold")
print()

if meets_threshold_count > 0:
    print(f"✓ {meets_threshold_count}/{total_count} cases meet threshold")
    print()
    print("CONCLUSION:")
    print("  Claim c5 is PARTIALLY SUPPORTED")
    print(f"  At typical wavelengths and path lengths, delta_phi ~ {delta_phi_typical:.2e}")
    if delta_phi_typical > threshold:
        print(f"  This EXCEEDS the threshold of {threshold:.0e} by {delta_phi_typical/threshold:.2f}x")
    else:
        print(f"  This FALLS SHORT of the threshold of {threshold:.0e}")
        print(f"  Would need {threshold/delta_phi_typical:.2f}x improvement")
else:
    print(f"✗ 0/{total_count} cases meet threshold")
    print()
    print("CONCLUSION:")
    print("  Claim c5 is NOT SUPPORTED")

print()
print("=" * 70)
print("CRITICAL ANALYSIS")
print("=" * 70)
print()
print("The phase modulation depth depends on three factors:")
print(f"  1. Refractive index modulation (delta_n = {delta_n_safe:.2e})")
print(f"     - Achieved at safe ultrasound intensity (0.5 W/cm^2)")
print(f"     - Could be increased ~5x to FDA limit (3.6 W/cm^2)")
print()
print(f"  2. Path length through focal volume (L = {L_typical*1000:.1f} mm)")
print(f"     - Limited by focal spot size and diffuse photon paths")
print(f"     - Difficult to increase significantly")
print()
print(f"  3. Wavelength (λ = {lambda_typical*1e9:.0f} nm)")
print(f"     - Fixed by fNIRS requirements (700-900 nm)")
print(f"     - Cannot be changed")
print()

# Calculate what would be needed
if delta_phi_typical < threshold:
    improvement_factor = threshold / delta_phi_typical
    print(f"To achieve threshold of {threshold:.0e} radians:")
    print(f"  - Need {improvement_factor:.2f}x improvement")
    print(f"  - Options:")
    print(f"    1. Increase delta_n by {improvement_factor:.2f}x")
    print(f"       (requires {improvement_factor:.1f}x higher ultrasound intensity)")
    print(f"    2. Increase L by {improvement_factor:.2f}x")
    print(f"       (requires {improvement_factor:.1f}x larger focal spot, defeats purpose)")
    print(f"    3. Combination of both")
else:
    print(f"Current design ACHIEVES the threshold!")
    print(f"  - Phase modulation: {delta_phi_typical:.2e} rad")
    print(f"  - Safety margin: {delta_phi_typical/threshold:.2f}x above threshold")
