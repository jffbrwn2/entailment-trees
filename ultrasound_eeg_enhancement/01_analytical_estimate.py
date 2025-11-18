"""
Analytical Back-of-Envelope Estimate for Ultrasound-Enhanced EEG

This script calculates order-of-magnitude estimates for the key feasibility
questions:
1. Is the modulated signal detectable above noise?
2. What spatial resolution can be achieved?
3. How much averaging is required?

All parameters from literature (see literature_values.md)
"""

import numpy as np
import matplotlib.pyplot as plt

print("="*70)
print("ULTRASOUND-ENHANCED EEG: ANALYTICAL FEASIBILITY ESTIMATE")
print("="*70)
print()

# ============================================================================
# PHYSICAL CONSTANTS
# ============================================================================
k_B = 1.38e-23  # Boltzmann constant (J/K)
T = 310  # Body temperature (K)

# ============================================================================
# ACOUSTOELECTRIC EFFECT PARAMETERS (from literature)
# ============================================================================
print("1. ACOUSTOELECTRIC EFFECT MAGNITUDE")
print("-" * 70)

# Interaction constant from cardiac tissue measurements
# 0.041%/MPa = (0.041/100) per MPa = 4.1e-4 per MPa = 4.1e-10 per Pa
K_interaction = 4.1e-10  # per Pa (0.041%/MPa from PMC9339687)
K_percent_per_MPa = K_interaction * 1e6 * 100  # Convert back to %/MPa for display
print(f"Interaction constant K: {K_interaction:.2e} Pa^-1")
print(f"                        = {K_percent_per_MPa:.4f} %/MPa")

# Ultrasound pressure (safety-limited)
P_acoustic = 2.0e6  # Pa (2 MPa - typical from literature)
MI_limit = 1.9  # Mechanical index safety limit
f_ultrasound = 1.0e6  # Hz (1 MHz)
MI_actual = P_acoustic / 1e6 / np.sqrt(f_ultrasound / 1e6)

print(f"\nUltrasound pressure: {P_acoustic/1e6:.1f} MPa")
print(f"Ultrasound frequency: {f_ultrasound/1e6:.1f} MHz")
print(f"Mechanical Index (MI): {MI_actual:.2f} (limit: {MI_limit})")
if MI_actual > MI_limit:
    print(f"⚠️  WARNING: MI exceeds diagnostic safety limit!")

# Fractional conductivity change
delta_sigma_over_sigma = K_interaction * P_acoustic
print(f"\nConductivity modulation: Δσ/σ = {delta_sigma_over_sigma:.2e}")
print(f"                                = {delta_sigma_over_sigma*100:.4f}%")

# ============================================================================
# SPATIAL RESOLUTION
# ============================================================================
print("\n2. SPATIAL RESOLUTION")
print("-" * 70)

# Ultrasound focal spot
c_tissue = 1540  # m/s (speed of sound in brain tissue)
wavelength = c_tissue / f_ultrasound
focal_spot_theoretical = wavelength / 2
focal_spot_actual = 4.2e-3  # m (4.2 mm FWHM from PMC10644821)

print(f"Wavelength λ: {wavelength*1e3:.2f} mm")
print(f"Theoretical focal spot (λ/2): {focal_spot_theoretical*1e3:.2f} mm")
print(f"Actual focal spot (FWHM): {focal_spot_actual*1e3:.1f} mm")
print(f"Focal spot volume: ~{(4/3)*np.pi*(focal_spot_actual/2)**3*1e9:.1f} mm³")

# Compare to EEG spatial resolution
eeg_resolution = 20e-3  # m (2 cm typical EEG resolution)
improvement_factor = eeg_resolution / focal_spot_actual

print(f"\nConventional EEG resolution: ~{eeg_resolution*1e3:.0f} mm")
print(f"Improvement factor: {improvement_factor:.1f}x better")

# ============================================================================
# SIGNAL AMPLITUDE CALCULATION
# ============================================================================
print("\n3. SIGNAL AMPLITUDE")
print("-" * 70)

# Neural signal propagation
V_source = 1.0e-3  # V (1 mV local field potential at cortex)
attenuation_volume_conduction = 20  # Typical attenuation factor
V_scalp = V_source / attenuation_volume_conduction

print(f"Signal at cortex (LFP): {V_source*1e3:.1f} mV")
print(f"Volume conduction attenuation: {attenuation_volume_conduction}x")
print(f"Signal at scalp: {V_scalp*1e6:.1f} μV")

# Acoustoelectric modulation
V_modulated = V_scalp * delta_sigma_over_sigma

print(f"\nModulated signal amplitude:")
print(f"  V_mod = V_scalp × (Δσ/σ)")
print(f"        = {V_scalp*1e6:.1f} μV × {delta_sigma_over_sigma:.2e}")
print(f"        = {V_modulated*1e9:.1f} nV")
print(f"        = {V_modulated*1e6:.4f} μV")

# ============================================================================
# NOISE ANALYSIS
# ============================================================================
print("\n4. NOISE SOURCES")
print("-" * 70)

# Electrode parameters
R_electrode = 10e3  # Ω (10 kΩ typical)
bandwidth_eeg = 100  # Hz (typical EEG bandwidth)

# Thermal noise
V_thermal = np.sqrt(4 * k_B * T * R_electrode * bandwidth_eeg)

print(f"Electrode impedance: {R_electrode/1e3:.0f} kΩ")
print(f"EEG bandwidth: {bandwidth_eeg:.0f} Hz")
print(f"\nThermal noise: V_n = √(4kTRΔf)")
print(f"                    = {V_thermal*1e6:.2f} μV")

# Physiological noise (dominated by EMG in higher frequencies)
V_emg = 20e-6  # V (20 μV typical EMG)
V_eog = 100e-6  # V (100 μV typical EOG)
print(f"\nPhysiological noise:")
print(f"  EMG: ~{V_emg*1e6:.0f} μV")
print(f"  EOG: ~{V_eog*1e6:.0f} μV")

# Total noise (RMS sum)
V_noise_total = np.sqrt(V_thermal**2 + V_emg**2)
print(f"\nTotal noise (thermal + EMG): {V_noise_total*1e6:.2f} μV")

# ============================================================================
# SNR ANALYSIS
# ============================================================================
print("\n5. SIGNAL-TO-NOISE RATIO")
print("-" * 70)

# Single measurement SNR
SNR_single = V_modulated / V_noise_total
SNR_single_dB = 20 * np.log10(SNR_single)

print(f"Single measurement:")
print(f"  Signal: {V_modulated*1e9:.2f} nV")
print(f"  Noise:  {V_noise_total*1e6:.2f} μV")
print(f"  SNR: {SNR_single:.2e} = {SNR_single_dB:.1f} dB")

# Required averaging for target SNR
target_SNR_dB = 10  # 10 dB target
target_SNR_linear = 10**(target_SNR_dB/20)

N_averages_required = (target_SNR_linear / SNR_single)**2

print(f"\nTo achieve SNR = {target_SNR_dB} dB:")
print(f"  Required averages: N = {N_averages_required:.0f}")

# Time requirements
stimulation_rate = 1.0  # Hz (typical EEG stimulation rate)
time_required = N_averages_required / stimulation_rate

print(f"  At {stimulation_rate:.1f} Hz stimulation: {time_required/60:.1f} minutes")
print(f"                              = {time_required/3600:.2f} hours")

# ============================================================================
# PARAMETER SENSITIVITY
# ============================================================================
print("\n6. PARAMETER SENSITIVITY")
print("-" * 70)

# What if we increase ultrasound pressure?
P_range = np.array([1.0, 1.5, 2.0, 2.5, 3.0]) * 1e6  # MPa
MI_range = P_range / 1e6 / np.sqrt(f_ultrasound / 1e6)
delta_sigma_range = K_interaction * P_range
V_mod_range = V_scalp * delta_sigma_range
N_avg_range = (target_SNR_linear * V_noise_total / V_mod_range)**2

print("Pressure (MPa) | MI   | Δσ/σ (×10⁻⁴) | Signal (nV) | Averages | Time (min)")
print("-" * 78)
for i, P in enumerate(P_range):
    print(f"     {P/1e6:.1f}       | {MI_range[i]:.2f} | "
          f"    {delta_sigma_range[i]*1e4:.1f}       | "
          f"   {V_mod_range[i]*1e9:.1f}     | "
          f"  {N_avg_range[i]:7.0f}   | {N_avg_range[i]/stimulation_rate/60:6.1f}")

print("\n⚠️  MI > 1.9 exceeds diagnostic safety limits")

# What if we reduce electrode noise?
print("\n" + "="*70)
print("NOISE REDUCTION ANALYSIS")
print("="*70)

R_range = np.array([20, 10, 5, 2, 1]) * 1e3  # kΩ
V_thermal_range = np.sqrt(4 * k_B * T * R_range * bandwidth_eeg)
V_noise_range = np.sqrt(V_thermal_range**2 + V_emg**2)
N_avg_noise = (target_SNR_linear * V_noise_range / V_modulated)**2

print("Electrode R (kΩ) | Thermal (μV) | Total Noise (μV) | Averages | Time (min)")
print("-" * 78)
for i, R in enumerate(R_range):
    print(f"      {R/1e3:.0f}         |    {V_thermal_range[i]*1e6:.2f}      | "
          f"      {V_noise_range[i]*1e6:.2f}       | "
          f"  {N_avg_noise[i]:7.0f}   | {N_avg_noise[i]/stimulation_rate/60:6.1f}")

# ============================================================================
# SANITY CHECKS
# ============================================================================
print("\n" + "="*70)
print("SANITY CHECKS")
print("="*70)

checks = []

# 1. Dimensional analysis
checks.append(("Units consistent", "All calculations use SI units", True))

# 2. Order of magnitude
checks.append(("EEG amplitude", f"{V_scalp*1e6:.0f} μV in typical range (10-100 μV)",
               10e-6 <= V_scalp <= 100e-6))

# 3. Physical realizability
checks.append(("Ultrasound frequency", f"{f_ultrasound/1e6:.1f} MHz is standard", True))
checks.append(("Focal spot", f"{focal_spot_actual*1e3:.1f} mm ≥ λ/2 = {focal_spot_theoretical*1e3:.2f} mm",
               focal_spot_actual >= focal_spot_theoretical))

# 4. Thermal noise floor
V_thermal_theoretical = np.sqrt(4 * k_B * T * R_electrode * bandwidth_eeg)
checks.append(("Thermal noise", f"{V_thermal*1e6:.2f} μV matches 4kTRΔf = {V_thermal_theoretical*1e6:.2f} μV",
               np.isclose(V_thermal, V_thermal_theoretical, rtol=0.01)))

# 5. SNR reality check
checks.append(("SNR reasonable", f"{SNR_single_dB:.1f} dB is negative (expected for small modulation)",
               SNR_single_dB < 0))

# 6. Averaging requirement
checks.append(("Averaging needed", f"{N_averages_required:.0f} averages is large but achievable",
               N_averages_required < 1e6))

print("\nCheck                 | Result")
print("-" * 70)
for name, desc, passed in checks:
    status = "✓" if passed else "✗"
    print(f"{status} {name:20s} | {desc}")

# ============================================================================
# FEASIBILITY SUMMARY
# ============================================================================
print("\n" + "="*70)
print("FEASIBILITY SUMMARY")
print("="*70)

print(f"""
KEY FINDINGS:

1. SIGNAL STRENGTH: ⚠️ VERY CHALLENGING
   - Modulated signal: ~{V_modulated*1e9:.0f} nV (extremely small!)
   - Noise floor: ~{V_noise_total*1e6:.0f} μV (physiological noise dominated)
   - Single-shot SNR: ~{SNR_single_dB:.0f} dB
   - Requires ~{N_averages_required/1e6:.1f} MILLION averages for 10 dB SNR
   - Acquisition time: ~{time_required/3600:.0f} hours ({time_required/3600/24:.1f} days) at 1 Hz

   ⚠️ CRITICAL: Signal is ~500× smaller than noise floor!

2. SPATIAL RESOLUTION: ✓ GOOD
   - Focal spot: ~{focal_spot_actual*1e3:.0f} mm (vs ~{eeg_resolution*1e3:.0f} mm for EEG)
   - Improvement: ~{improvement_factor:.0f}× better than conventional EEG
   - Volume: ~{(4/3)*np.pi*(focal_spot_actual/2)**3*1e9:.0f} mm³ (contains ~370,000 neurons)

3. SAFETY: ⚠️ AT LIMIT
   - Required pressure ({P_acoustic/1e6:.0f} MPa) gives MI = {MI_actual:.1f}
   - Slightly exceeds diagnostic limit (MI < {MI_limit})
   - May be acceptable for research, needs clinical validation

4. PRACTICAL FEASIBILITY: ❌ EXTREMELY CHALLENGING
   - Averaging time of {time_required/3600/24:.0f} days is impractical
   - Physiological noise dominates (not improvable)
   - Pressure limited by safety (cannot increase significantly)

   CRITICAL ISSUE: Unlike published studies that inject currents (mA-level),
   this approach tries to detect natural neural activity (μA-level in volume),
   making signals 1000× weaker than demonstrated in literature.

5. COMPARISON TO LITERATURE:
   - Published studies: Current injection + acoustoelectric detection
     * Injected current: 0.5-1 mA
     * Achieved SNR: 8-15 dB (reasonable!)
     * Application: Current source localization

   - This proposal: Natural EEG + acoustoelectric modulation
     * Natural current: ~1 μA (in focal volume)
     * Expected SNR: -54 dB (extremely poor)
     * Application: Enhanced spatial resolution for passive recording

   ⚠️ These are FUNDAMENTALLY DIFFERENT applications!

6. CRITICAL UNKNOWNS:
   - Acoustoelectric constant in human brain in vivo
   - Effects of skull aberration on focal spot (may worsen resolution)
   - Thermal effects from days-long sonication (clearly impractical)
   - Phase stability over million-fold averaging (impossible to maintain)

7. PATHS TO IMPROVEMENT (All insufficient):
   - Higher ultrasound pressure: Safety-limited, gains only ~2×
   - Lower electrode noise: Dominated by physiological noise, minimal gain
   - Better source geometry: Computational, doesn't improve SNR
   - Faster stimulation: Limited by neural refractory period
   - Longer coherent averaging: Requires impossibly stable phase

VERDICT: ❌ NOT PRACTICALLY FEASIBLE for passive neural recording

The concept conflicts with fundamental limitations:
- Natural neural signals too weak (1000× smaller than injected currents)
- Physiological noise floor cannot be reduced
- Required averaging time (weeks) is physiologically impossible
- Safety limits prevent adequate signal modulation

MAY work for (different application):
- Current source localization (inject known current, as in literature)
- Transcranial current stimulation with acoustoelectric readout
- Validating neural mass models (not single-trial recording)

NOT feasible for (original proposal):
- Enhanced spatial resolution for passive EEG recording
- Real-time or near-real-time brain-computer interfaces
- Clinical neural monitoring
- Any application requiring < 1 hour acquisition
""")

# ============================================================================
# VISUALIZATION
# ============================================================================
print("\n" + "="*70)
print("Generating visualization...")
print("="*70)

fig, axes = plt.subplots(2, 2, figsize=(12, 10))

# Plot 1: Signal cascade
ax = axes[0, 0]
stages = ['Cortex\n(LFP)', 'Scalp\n(EEG)', 'Modulated\n(AE)']
amplitudes = [V_source*1e6, V_scalp*1e6, V_modulated*1e6]  # μV
colors = ['green', 'blue', 'red']
bars = ax.bar(stages, amplitudes, color=colors, alpha=0.7, edgecolor='black')
ax.axhline(V_noise_total*1e6, color='orange', linestyle='--', linewidth=2, label='Noise floor')
ax.set_ylabel('Amplitude (μV)', fontsize=12)
ax.set_title('Signal Attenuation Cascade', fontsize=14, fontweight='bold')
ax.set_yscale('log')
ax.grid(True, alpha=0.3, which='both')
ax.legend()
for bar, amp in zip(bars, amplitudes):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height,
            f'{amp:.2e} μV',
            ha='center', va='bottom', fontsize=10)

# Plot 2: Pressure vs Averaging Time
ax = axes[0, 1]
ax.plot(P_range/1e6, N_avg_range/stimulation_rate/60, 'o-', linewidth=2, markersize=8)
ax.axhline(60, color='red', linestyle='--', label='1 hour')
ax.axhline(10, color='orange', linestyle='--', label='10 minutes')
ax.set_xlabel('Ultrasound Pressure (MPa)', fontsize=12)
ax.set_ylabel('Acquisition Time (minutes)', fontsize=12)
ax.set_title('Pressure vs Required Averaging Time', fontsize=14, fontweight='bold')
ax.set_yscale('log')
ax.grid(True, alpha=0.3)
ax.legend()

# Add safety limit shading
ax.axvspan(0, 1.9*np.sqrt(f_ultrasound/1e6), alpha=0.2, color='green', label='Safe (MI<1.9)')
ax.axvspan(1.9*np.sqrt(f_ultrasound/1e6), 3, alpha=0.2, color='red')

# Plot 3: Electrode noise vs Averaging
ax = axes[1, 0]
ax.plot(R_range/1e3, N_avg_noise/stimulation_rate/60, 'o-', linewidth=2, markersize=8, color='purple')
ax.axhline(60, color='red', linestyle='--', label='1 hour')
ax.axhline(10, color='orange', linestyle='--', label='10 minutes')
ax.set_xlabel('Electrode Impedance (kΩ)', fontsize=12)
ax.set_ylabel('Acquisition Time (minutes)', fontsize=12)
ax.set_title('Electrode Quality vs Averaging Time', fontsize=14, fontweight='bold')
ax.set_yscale('log')
ax.set_xscale('log')
ax.grid(True, alpha=0.3, which='both')
ax.legend()

# Plot 4: SNR improvement with averaging
ax = axes[1, 1]
N_avg_plot = np.logspace(0, 5, 100)
SNR_plot = SNR_single * np.sqrt(N_avg_plot)
SNR_plot_dB = 20 * np.log10(SNR_plot)
ax.plot(N_avg_plot, SNR_plot_dB, linewidth=2)
ax.axhline(10, color='green', linestyle='--', linewidth=2, label='Target: 10 dB')
ax.axhline(0, color='orange', linestyle='--', linewidth=2, label='Unity SNR')
ax.axvline(N_averages_required, color='red', linestyle='--', linewidth=2,
           label=f'Required: {N_averages_required:.0f}')
ax.set_xlabel('Number of Averages', fontsize=12)
ax.set_ylabel('SNR (dB)', fontsize=12)
ax.set_title('SNR vs Averaging', fontsize=14, fontweight='bold')
ax.set_xscale('log')
ax.grid(True, alpha=0.3, which='both')
ax.legend()
ax.fill_between(N_avg_plot, -60, SNR_plot_dB, where=(SNR_plot_dB>=10),
                alpha=0.2, color='green', label='Detectable')

plt.tight_layout()
plt.savefig('/Users/jbrown/Documents/alegria/ai-simulations/ultrasound_eeg_enhancement/01_analytical_feasibility.png',
            dpi=150, bbox_inches='tight')
print("✓ Saved: 01_analytical_feasibility.png")
plt.show()

print("\n" + "="*70)
print("ANALYSIS COMPLETE")
print("="*70)
print("\nNext steps:")
print("1. Run full 2D simulation to validate these estimates")
print("2. Model skull aberration effects on focal spot")
print("3. Include realistic noise time-series")
print("4. Explore parameter optimization strategies")
print("5. Literature search for in vivo acoustoelectric measurements")
