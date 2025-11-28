"""
Calculate shot noise limited phase sensitivity for fNIRS detectors.

Shot noise follows Poisson statistics: delta_N = sqrt(N)
For phase measurements via interferometry/heterodyne detection,
the phase noise is: delta_phi = 1/sqrt(N)

where N is the number of photons detected.
"""

import numpy as np

# Typical fNIRS photon count rates from literature
# CW fNIRS systems typically detect 10^6 to 10^8 photons/sec

photon_rates = [1e6, 1e7, 1e8]  # photons/sec

# Integration times to consider
integration_times = [0.001, 0.01, 0.1, 1.0]  # seconds

print("Shot Noise Limited Phase Sensitivity for fNIRS")
print("=" * 60)
print("\nFor heterodyne/interferometric phase detection:")
print("Phase noise: delta_phi = 1/sqrt(N_photons)")
print()

for rate in photon_rates:
    print(f"\nPhoton rate: {rate:.0e} photons/sec")
    print("-" * 60)
    print(f"{'Integration time (s)':<20} {'N photons':<15} {'Phase noise (rad)':<20}")
    print("-" * 60)

    for t in integration_times:
        N = rate * t
        phase_noise = 1.0 / np.sqrt(N)
        print(f"{t:<20.3f} {N:<15.2e} {phase_noise:<20.2e}")

print("\n" + "=" * 60)
print("SUMMARY FOR TYPICAL fNIRS OPERATION:")
print("=" * 60)

# Most relevant: 10^6 - 10^8 photons/sec with ~0.1-1 sec integration
typical_rates = [1e6, 1e7, 1e8]
typical_integration = 0.1  # 100 ms is typical for fNIRS

print(f"\nIntegration time: {typical_integration} sec")
print(f"{'Photon rate (ph/s)':<25} {'Phase sensitivity (rad)':<25}")
print("-" * 50)

for rate in typical_rates:
    N = rate * typical_integration
    phase_noise = 1.0 / np.sqrt(N)
    print(f"{rate:<25.2e} {phase_noise:<25.2e}")

print("\n" + "=" * 60)
print("CONCLUSION:")
print("=" * 60)
print("For typical fNIRS photon count rates of 10^6 to 10^8 photons/sec")
print("with 0.1 sec integration time:")
print("  - At 10^6 ph/s: N = 10^5 photons -> delta_phi = 3.2e-3 rad")
print("  - At 10^7 ph/s: N = 10^6 photons -> delta_phi = 1.0e-3 rad")
print("  - At 10^8 ph/s: N = 10^7 photons -> delta_phi = 3.2e-4 rad")
print("\nPhase sensitivity range: 3.2e-4 to 3.2e-3 radians")
print("This overlaps with the claimed range of 10^-3 to 10^-4 radians.")
print("\nClaim c4 is SUPPORTED: shot noise limited phase sensitivity")
print("is indeed in the 10^-3 to 10^-4 radian range (and somewhat beyond).")
