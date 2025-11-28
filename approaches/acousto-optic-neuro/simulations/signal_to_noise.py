"""
Check if modulated signal is detectable above noise.

From previous simulations:
- c4: Shot noise limited phase sensitivity ~ 10^-3 to 10^-4 radians
- c5: Phase modulation depth ~ 2.14e-1 radians (much higher than threshold!)

For detection, we need SNR >> 1, typically SNR > 5 for reliable detection.
"""

import numpy as np

print("Signal-to-Noise Ratio Analysis")
print("=" * 70)

# From previous simulations
phase_modulation = 2.14e-1  # radians (typical case from phase_modulation_depth.py)
shot_noise_low = 1e-4       # radians (best case, 10^8 photons/sec)
shot_noise_mid = 1e-3       # radians (typical, 10^7 photons/sec)
shot_noise_high = 3.2e-3    # radians (worst case, 10^6 photons/sec)

print(f"\nPhase Modulation Signal:")
print(f"  delta_phi = {phase_modulation:.2e} radians")
print()

print(f"Shot Noise Levels (from c4):")
print(f"  Best case (10^8 ph/s):    {shot_noise_low:.2e} radians")
print(f"  Typical (10^7 ph/s):      {shot_noise_mid:.2e} radians")
print(f"  Worst case (10^6 ph/s):   {shot_noise_high:.2e} radians")
print()

# Calculate SNR
print("Signal-to-Noise Ratio (SNR = signal / noise)")
print("-" * 70)

snr_best = phase_modulation / shot_noise_low
snr_typical = phase_modulation / shot_noise_mid
snr_worst = phase_modulation / shot_noise_high

print(f"  Best case:    SNR = {snr_best:.0f}")
print(f"  Typical:      SNR = {snr_typical:.0f}")
print(f"  Worst case:   SNR = {snr_worst:.0f}")
print()

# Check detectability
detection_threshold = 5  # Typical requirement: SNR > 5 for reliable detection

print("=" * 70)
print(f"DETECTABILITY ANALYSIS (threshold: SNR > {detection_threshold})")
print("=" * 70)
print()

all_detectable = True

if snr_best > detection_threshold:
    print(f"✓ Best case: SNR = {snr_best:.0f} > {detection_threshold} - DETECTABLE")
else:
    print(f"✗ Best case: SNR = {snr_best:.0f} < {detection_threshold} - NOT DETECTABLE")
    all_detectable = False

if snr_typical > detection_threshold:
    print(f"✓ Typical: SNR = {snr_typical:.0f} > {detection_threshold} - DETECTABLE")
else:
    print(f"✗ Typical: SNR = {snr_typical:.0f} < {detection_threshold} - NOT DETECTABLE")
    all_detectable = False

if snr_worst > detection_threshold:
    print(f"✓ Worst case: SNR = {snr_worst:.0f} > {detection_threshold} - DETECTABLE")
else:
    print(f"✗ Worst case: SNR = {snr_worst:.0f} < {detection_threshold} - NOT DETECTABLE")
    all_detectable = False

print()

# CRITICAL CAVEAT: Low tagging fraction
print("=" * 70)
print("CRITICAL CAVEAT: Photon Tagging Fraction")
print("=" * 70)
print()

print("From photon_path_length.py simulation:")
print("  - Only ~5-20% of photons pass through ultrasound focal volume")
print("  - This reduces the effective signal amplitude")
print()

tagging_fractions = [0.05, 0.10, 0.20]  # 5%, 10%, 20%

print("Effective SNR with tagging fraction:")
print("-" * 70)

for frac in tagging_fractions:
    snr_eff_typical = snr_typical * frac
    detectable = snr_eff_typical > detection_threshold
    status = "✓ DETECTABLE" if detectable else "✗ NOT DETECTABLE"

    print(f"  Tagging fraction {frac*100:.0f}%: SNR_eff = {snr_eff_typical:.1f}  {status}")

print()

# Most realistic case
frac_realistic = 0.10  # 10% tagging fraction (middle estimate)
snr_realistic = snr_typical * frac_realistic

print(f"Realistic estimate (10% tagging, 10^7 ph/s):")
print(f"  Raw SNR: {snr_typical:.0f}")
print(f"  Effective SNR: {snr_realistic:.1f}")
print(f"  Detectable (SNR > {detection_threshold})? {snr_realistic > detection_threshold}")
print()

# Additional noise sources
print("=" * 70)
print("ADDITIONAL NOISE CONSIDERATIONS")
print("=" * 70)
print()
print("Shot noise is the FUNDAMENTAL limit, but real systems have:")
print("  1. Detector dark noise")
print("  2. Electronics noise")
print("  3. Ambient light (if not well shielded)")
print("  4. Physiological noise (heartbeat, respiration)")
print("  5. Motion artifacts")
print()
print("These typically add ~2-5x additional noise beyond shot noise.")
print()

noise_factor = 3  # Conservative estimate
snr_with_noise = snr_realistic / noise_factor

print(f"With additional noise (3x factor):")
print(f"  Effective SNR: {snr_with_noise:.1f}")
print(f"  Detectable (SNR > {detection_threshold})? {snr_with_noise > detection_threshold}")
print()

# Final conclusion
print("=" * 70)
print("CONCLUSION FOR CLAIM c11")
print("=" * 70)
print()

if snr_with_noise > detection_threshold:
    print("✓ Claim c11 is SUPPORTED")
    print(f"  Even with tagging fraction and additional noise, SNR = {snr_with_noise:.1f} > {detection_threshold}")
elif snr_realistic > detection_threshold:
    print("⚠ Claim c11 is MARGINALLY SUPPORTED")
    print(f"  SNR = {snr_realistic:.1f} > {detection_threshold} with only shot noise")
    print(f"  But SNR = {snr_with_noise:.1f} when including other noise sources")
    print("  Detection may be challenging in practice")
else:
    print("✗ Claim c11 is NOT SUPPORTED")
    print(f"  SNR = {snr_realistic:.1f} < {detection_threshold}")
    print("  Signal is NOT reliably detectable above noise")

print()
print("KEY INSIGHT:")
print("  The phase modulation itself is LARGE (~0.2 rad >> 5×10^-3 rad threshold)")
print("  BUT the low tagging fraction (~10%) significantly reduces effective SNR")
print("  This is a CRITICAL challenge for practical implementation")
