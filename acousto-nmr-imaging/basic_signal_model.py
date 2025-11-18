"""
Acousto-NMR Imaging: Basic Signal Model

This simulation models the fundamental physics of using focused ultrasound
for spatial encoding in low-field MRI.

Key Question: Can ultrasound-induced phase modulation create detectable
signals above thermal noise?
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import hilbert, welch
from scipy.special import jv  # Bessel function for FM sidebands

# ============================================================================
# PHYSICAL CONSTANTS
# ============================================================================
GAMMA_PROTON = 42.58e6  # Hz/T - proton gyromagnetic ratio
K_BOLTZMANN = 1.380649e-23  # J/K
PROTON_DENSITY = 80e3  # mol/m^3 (80 M water in brain)
AVOGADRO = 6.022e23  # mol^-1

# ============================================================================
# PARAMETERS (with citations/justification in README)
# ============================================================================

class Parameters:
    """Simulation parameters with physical justification"""

    # MRI Parameters
    B0 = 0.1  # Tesla - low field strength
    T1 = 0.7  # seconds - gray matter at low field
    T2 = 0.09  # seconds - gray matter at low field
    voxel_volume = (2e-3)**3  # m^3 - (2mm)^3 voxel

    # Ultrasound Parameters
    us_frequency = 1e6  # Hz - 1 MHz ultrasound
    us_pressure = 0.5e6  # Pa - 0.5 MPa acoustic pressure
    us_focal_diameter = 2e-3  # m - 2 mm focal spot

    # Tissue Properties (UNCERTAIN - see README)
    youngs_modulus = 5e3  # Pa - brain tissue (range: 1-10 kPa in literature)
    tissue_density = 1000  # kg/m^3 - approximately water
    absorption_coeff = 0.05  # Np/m/Hz - ultrasound absorption (α ≈ 0.5 dB/cm/MHz)

    # Detection Parameters
    temperature = 310  # K - body temperature
    coil_resistance = 10  # Ohms - RF coil resistance
    bandwidth = 1000  # Hz - detection bandwidth
    acquisition_time = 0.1  # seconds - signal averaging time

    # Derived quantities
    @property
    def larmor_frequency(self):
        """Larmor frequency in Hz"""
        return GAMMA_PROTON * self.B0

    @property
    def num_spins(self):
        """Number of spins in voxel"""
        return PROTON_DENSITY * self.voxel_volume * AVOGADRO

    @property
    def thermal_noise_voltage(self):
        """RMS thermal noise voltage in coil (Johnson-Nyquist)"""
        return np.sqrt(4 * K_BOLTZMANN * self.temperature *
                      self.coil_resistance * self.bandwidth)


# ============================================================================
# ULTRASOUND-INDUCED DISPLACEMENT
# ============================================================================

def calculate_displacement_amplitude(params):
    """
    Calculate tissue displacement from ultrasound radiation force.

    This is a SIMPLIFIED model. Actual displacement depends on:
    - Tissue viscoelasticity (frequency dependent)
    - Boundary conditions
    - Acoustic streaming effects

    Using simple harmonic oscillator approximation:
    Displacement A = F / (m·ω²) where F is radiation force

    Radiation force: F = 2αI/c where I is intensity, c is speed of sound

    UNCERTAINTY: ±50% or more due to tissue property variability
    """

    # Acoustic intensity (W/m^2)
    c_sound = 1540  # m/s - speed of sound in tissue
    Z = params.tissue_density * c_sound  # acoustic impedance
    intensity = params.us_pressure**2 / (2 * Z)

    # Radiation force per unit volume (N/m^3)
    force_density = 2 * params.absorption_coeff * params.us_frequency * intensity / c_sound

    # Displacement amplitude (m)
    # Using A = F/(m·ω²) = (F/V)/(ρ·ω²) where F/V is force per volume
    omega_us = 2 * np.pi * params.us_frequency
    displacement = force_density / (params.tissue_density * omega_us**2)

    return displacement


def calculate_displacement_alternative(params):
    """
    Alternative estimate using mechanical wave propagation.

    For shear wave: displacement amplitude ≈ pressure / (ρ·c_shear·ω)
    where c_shear = √(G/ρ) and G ≈ E/3 for brain tissue

    This gives another estimate to check order of magnitude.
    """
    # Shear modulus (approximately E/3 for soft tissue)
    shear_modulus = params.youngs_modulus / 3
    c_shear = np.sqrt(shear_modulus / params.tissue_density)
    omega_us = 2 * np.pi * params.us_frequency

    # Displacement from shear wave
    displacement = params.us_pressure / (params.tissue_density * c_shear * omega_us)

    return displacement


# ============================================================================
# MR SIGNAL WITH ULTRASOUND MODULATION
# ============================================================================

def calculate_equilibrium_magnetization(params):
    """
    Equilibrium magnetization M0 (A/m)

    M0 = (N·γ²·ℏ²·I(I+1)·B0) / (3·k·T)

    For protons: I = 1/2, so I(I+1) = 3/4
    Simplified: M0 ≈ (N·γ²·ℏ²·B0) / (4·k·T)
    """
    h_bar = 1.054571817e-34  # J·s
    n_spins = params.num_spins

    M0 = (n_spins * (GAMMA_PROTON * 2 * np.pi)**2 * h_bar**2 * params.B0) / \
         (4 * K_BOLTZMANN * params.temperature * params.voxel_volume)

    return M0


def generate_mr_signal(params, displacement_amplitude, t):
    """
    Generate MR signal with ultrasound phase modulation.

    Signal: S(t) = M0 · sin(θ) · exp(-t/T2) · exp(i·ω0·t) · exp(i·Δφ(t))

    where Δφ(t) = γ·B0·Δx(t) is the phase shift from motion
    and Δx(t) = A·sin(ωus·t) is the ultrasound-induced displacement

    Modulation index: β = γ·B0·A

    The phase modulation creates sidebands at ω0 ± n·ωus
    Sideband amplitudes given by Bessel functions: Jn(β)
    """

    M0 = calculate_equilibrium_magnetization(params)

    # Larmor precession
    omega0 = 2 * np.pi * params.larmor_frequency

    # Ultrasound modulation
    omega_us = 2 * np.pi * params.us_frequency
    displacement = displacement_amplitude * np.sin(omega_us * t)

    # Phase shift from motion
    phase_shift = GAMMA_PROTON * 2 * np.pi * params.B0 * displacement

    # T2 decay
    decay = np.exp(-t / params.T2)

    # Complex MR signal (using small flip angle, so sin(θ) ≈ θ ≈ 0.1 rad)
    flip_angle = 0.1  # radians (about 6 degrees)
    signal = M0 * flip_angle * decay * np.exp(1j * (omega0 * t + phase_shift))

    return signal


def calculate_modulation_index(params, displacement_amplitude):
    """
    Modulation index β = γ·B0·A

    This determines the strength of sidebands:
    - β << 1: weak modulation, first sidebands only
    - β ~ 1: moderate modulation, multiple sidebands
    - β >> 1: strong modulation, many sidebands
    """
    beta = GAMMA_PROTON * 2 * np.pi * params.B0 * displacement_amplitude
    return beta


# ============================================================================
# NOISE MODELING
# ============================================================================

def add_thermal_noise(signal, params):
    """
    Add thermal (Johnson-Nyquist) noise to the signal.

    This is the fundamental noise floor for any resistive detector.

    Vrms = √(4·k·T·R·Δf)

    We model complex noise (I and Q channels) as independent Gaussian.
    """
    n_samples = len(signal)

    # Noise voltage (RMS) per sqrt(Hz)
    noise_spectral_density = np.sqrt(4 * K_BOLTZMANN * params.temperature *
                                    params.coil_resistance)

    # Noise power in our bandwidth
    noise_std = noise_spectral_density * np.sqrt(params.bandwidth)

    # Complex noise (independent I and Q)
    noise_i = np.random.normal(0, noise_std / np.sqrt(2), n_samples)
    noise_q = np.random.normal(0, noise_std / np.sqrt(2), n_samples)
    noise = noise_i + 1j * noise_q

    return signal + noise


# ============================================================================
# SIGNAL ANALYSIS
# ============================================================================

def detect_sidebands(signal, fs, f0, f_us):
    """
    Detect and measure sideband amplitudes using FFT.

    Look for peaks at f0 ± n·fus
    """
    # FFT
    spectrum = np.fft.fft(signal)
    freqs = np.fft.fftfreq(len(signal), 1/fs)

    # Power spectral density
    psd = np.abs(spectrum)**2 / len(signal)

    # Find carrier and sideband frequencies
    def find_peak_power(freq_target, tolerance=100):
        """Find power near target frequency"""
        idx = np.where(np.abs(freqs - freq_target) < tolerance)[0]
        if len(idx) > 0:
            return np.max(psd[idx])
        return 0

    carrier_power = find_peak_power(f0)
    lower_sideband_power = find_peak_power(f0 - f_us)
    upper_sideband_power = find_peak_power(f0 + f_us)

    return {
        'freqs': freqs,
        'psd': psd,
        'carrier_power': carrier_power,
        'lower_sideband_power': lower_sideband_power,
        'upper_sideband_power': upper_sideband_power,
    }


def calculate_snr(signal_power, noise_power):
    """Calculate SNR in dB"""
    return 10 * np.log10(signal_power / noise_power)


# ============================================================================
# SANITY CHECKS
# ============================================================================

def sanity_checks(params, results):
    """
    Perform physical and computational sanity checks.

    Returns dict with check results and warnings.
    """
    checks = {}
    warnings = []

    # 1. Dimensional analysis (spot checks)
    checks['larmor_frequency_units'] = 'Hz'
    checks['larmor_frequency_value'] = params.larmor_frequency
    if not (1e6 < params.larmor_frequency < 100e6):
        warnings.append(f"Larmor frequency {params.larmor_frequency/1e6:.2f} MHz outside typical range")

    # 2. Order of magnitude checks
    displacement = results['displacement_amplitude']
    checks['displacement_nm'] = displacement * 1e9
    if displacement < 0.01e-9 or displacement > 100e-6:
        warnings.append(f"Displacement {displacement*1e9:.2g} nm seems unusual")

    # 3. Modulation index
    beta = results['modulation_index']
    checks['modulation_index'] = beta
    if beta < 1e-6:
        warnings.append(f"Modulation index {beta:.2e} very small - signal may be undetectable")

    # 4. Thermal noise floor
    thermal_voltage = params.thermal_noise_voltage
    checks['thermal_noise_V'] = thermal_voltage
    checks['thermal_noise_dBm'] = 10 * np.log10(thermal_voltage**2 / params.coil_resistance / 1e-3)

    # 5. Check for NaN/Inf
    if np.any(np.isnan(results['signal'])) or np.any(np.isinf(results['signal'])):
        warnings.append("NaN or Inf detected in signal!")

    # 6. SNR reality check
    snr = results['snr_db']
    checks['snr_db'] = snr
    if snr < -20:
        warnings.append(f"SNR {snr:.1f} dB very poor - signal likely undetectable")
    elif snr > 60:
        warnings.append(f"SNR {snr:.1f} dB surprisingly good - check assumptions")

    # 7. Sideband power should be less than carrier
    if results['sideband_analysis']['lower_sideband_power'] > results['sideband_analysis']['carrier_power']:
        warnings.append("Sideband power exceeds carrier - check modulation")

    # 8. Phase shift reasonable
    max_phase = GAMMA_PROTON * 2 * np.pi * params.B0 * displacement
    checks['max_phase_shift_rad'] = max_phase
    checks['max_phase_shift_deg'] = np.degrees(max_phase)

    return checks, warnings


# ============================================================================
# MAIN SIMULATION
# ============================================================================

def run_simulation():
    """
    Main simulation: evaluate feasibility of acousto-NMR imaging.
    """

    print("=" * 70)
    print("ACOUSTO-NMR IMAGING SIMULATION")
    print("=" * 70)
    print()

    # Initialize parameters
    params = Parameters()

    print("PARAMETERS:")
    print(f"  Magnetic field: {params.B0} T")
    print(f"  Larmor frequency: {params.larmor_frequency/1e6:.3f} MHz")
    print(f"  T1: {params.T1*1000:.0f} ms, T2: {params.T2*1000:.1f} ms")
    print(f"  Voxel size: {(params.voxel_volume**(1/3))*1e3:.1f} mm")
    print(f"  US frequency: {params.us_frequency/1e6:.2f} MHz")
    print(f"  US pressure: {params.us_pressure/1e6:.2f} MPa")
    print()

    # Calculate displacement
    displacement_rad_force = calculate_displacement_amplitude(params)
    displacement_shear = calculate_displacement_alternative(params)

    print("DISPLACEMENT ESTIMATES:")
    print(f"  Radiation force model: {displacement_rad_force*1e9:.2f} nm")
    print(f"  Shear wave model: {displacement_shear*1e9:.2f} nm")
    print(f"  Using average: {(displacement_rad_force + displacement_shear)/2*1e9:.2f} nm")
    print(f"  (UNCERTAINTY: ±50% or more - see README)")
    print()

    displacement = (displacement_rad_force + displacement_shear) / 2

    # Modulation index
    beta = calculate_modulation_index(params, displacement)
    print(f"MODULATION INDEX: β = {beta:.4e}")
    print(f"  (β = γ·B0·A)")
    print(f"  First sideband amplitude: J1(β) = {jv(1, beta):.4e}")
    print()

    # Generate time series
    fs = 10 * params.larmor_frequency  # Sample at 10x Larmor frequency
    t = np.arange(0, params.acquisition_time, 1/fs)

    # Generate signal
    signal_clean = generate_mr_signal(params, displacement, t)
    signal_noisy = add_thermal_noise(signal_clean, params)

    # Analyze sidebands
    sideband_clean = detect_sidebands(signal_clean, fs,
                                     params.larmor_frequency,
                                     params.us_frequency)
    sideband_noisy = detect_sidebands(signal_noisy, fs,
                                      params.larmor_frequency,
                                      params.us_frequency)

    # Calculate SNR
    signal_power = sideband_clean['lower_sideband_power'] + sideband_clean['upper_sideband_power']
    noise_power = params.thermal_noise_voltage**2 / params.coil_resistance
    snr = calculate_snr(signal_power, noise_power)

    print("SIGNAL ANALYSIS:")
    print(f"  Carrier power: {sideband_clean['carrier_power']:.3e} W")
    print(f"  Lower sideband: {sideband_clean['lower_sideband_power']:.3e} W")
    print(f"  Upper sideband: {sideband_clean['upper_sideband_power']:.3e} W")
    print(f"  Total sideband power: {signal_power:.3e} W")
    print(f"  Thermal noise power: {noise_power:.3e} W")
    print(f"  SNR: {snr:.1f} dB")
    print()

    # Package results
    results = {
        'params': params,
        'displacement_amplitude': displacement,
        'modulation_index': beta,
        'time': t,
        'signal': signal_noisy,
        'signal_clean': signal_clean,
        'sideband_analysis': sideband_noisy,
        'snr_db': snr,
    }

    # Sanity checks
    print("=" * 70)
    print("SANITY CHECKS")
    print("=" * 70)
    checks, warnings = sanity_checks(params, results)

    for key, value in checks.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.3e}")
        else:
            print(f"  {key}: {value}")

    print()
    if warnings:
        print("WARNINGS:")
        for w in warnings:
            print(f"  ⚠ {w}")
    else:
        print("✓ All sanity checks passed")

    print()

    # Visualization
    plot_results(results)

    return results


def plot_results(results):
    """Visualize simulation results"""

    fig, axes = plt.subplots(3, 2, figsize=(14, 10))
    fig.suptitle('Acousto-NMR Simulation Results', fontsize=14, fontweight='bold')

    params = results['params']
    t = results['time']
    signal = results['signal']
    signal_clean = results['signal_clean']
    sideband = results['sideband_analysis']

    # 1. Time-domain signal (real part)
    ax = axes[0, 0]
    t_ms = t * 1000
    ax.plot(t_ms, np.real(signal_clean), 'b-', linewidth=1, label='Clean', alpha=0.7)
    ax.plot(t_ms, np.real(signal), 'r-', linewidth=0.5, label='With noise', alpha=0.5)
    ax.set_xlabel('Time (ms)')
    ax.set_ylabel('Signal (real part)')
    ax.set_title('MR Signal Time Series')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 2. Time-domain signal (zoomed)
    ax = axes[0, 1]
    n_zoom = int(5 / params.larmor_frequency * params.acquisition_time * len(t) / params.acquisition_time)
    ax.plot(t_ms[:n_zoom], np.real(signal_clean[:n_zoom]), 'b-', linewidth=1, label='Clean')
    ax.plot(t_ms[:n_zoom], np.real(signal[:n_zoom]), 'r-', linewidth=0.5, label='With noise', alpha=0.7)
    ax.set_xlabel('Time (ms)')
    ax.set_ylabel('Signal (real part)')
    ax.set_title('MR Signal (Zoomed - first 5 cycles)')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 3. Frequency spectrum (full)
    ax = axes[1, 0]
    freqs = sideband['freqs']
    psd = sideband['psd']
    ax.semilogy(freqs / 1e6, psd, 'b-', linewidth=0.5)
    ax.set_xlabel('Frequency (MHz)')
    ax.set_ylabel('Power Spectral Density')
    ax.set_title('Frequency Spectrum')
    ax.set_xlim([0, params.larmor_frequency / 1e6 * 2])
    ax.grid(True, alpha=0.3)

    # 4. Frequency spectrum (zoomed around carrier)
    ax = axes[1, 1]
    f0 = params.larmor_frequency
    f_us = params.us_frequency
    idx = np.where((freqs > f0 - 3*f_us) & (freqs < f0 + 3*f_us))[0]
    ax.semilogy(freqs[idx] / 1e6, psd[idx], 'b-', linewidth=1)
    ax.axvline((f0) / 1e6, color='r', linestyle='--', alpha=0.5, label='Carrier')
    ax.axvline((f0 - f_us) / 1e6, color='g', linestyle='--', alpha=0.5, label='Sidebands')
    ax.axvline((f0 + f_us) / 1e6, color='g', linestyle='--', alpha=0.5)
    ax.set_xlabel('Frequency (MHz)')
    ax.set_ylabel('Power Spectral Density')
    ax.set_title('Spectrum Near Carrier (showing sidebands)')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 5. Phase modulation visualization
    ax = axes[2, 0]
    displacement = results['displacement_amplitude'] * np.sin(2 * np.pi * params.us_frequency * t)
    phase_shift = GAMMA_PROTON * 2 * np.pi * params.B0 * displacement
    ax.plot(t_ms, displacement * 1e9, 'b-', linewidth=1, label='Displacement')
    ax.set_xlabel('Time (ms)')
    ax.set_ylabel('Displacement (nm)', color='b')
    ax.tick_params(axis='y', labelcolor='b')
    ax.grid(True, alpha=0.3)

    ax2 = ax.twinx()
    ax2.plot(t_ms, np.degrees(phase_shift), 'r-', linewidth=1, label='Phase shift')
    ax2.set_ylabel('Phase Shift (degrees)', color='r')
    ax2.tick_params(axis='y', labelcolor='r')
    ax.set_title('Ultrasound-Induced Displacement and Phase')

    # 6. Summary statistics
    ax = axes[2, 1]
    ax.axis('off')

    summary_text = f"""
SUMMARY STATISTICS

Displacement: {results['displacement_amplitude']*1e9:.2f} nm
Modulation index β: {results['modulation_index']:.4e}
Max phase shift: {np.degrees(np.max(phase_shift)):.4f}°

SNR: {results['snr_db']:.1f} dB

Carrier power: {sideband['carrier_power']:.2e} W
Sideband power: {sideband['lower_sideband_power']:.2e} W

Thermal noise: {params.thermal_noise_voltage*1e9:.1f} nV/√Hz

FEASIBILITY:
{'✓ Detectable' if results['snr_db'] > 0 else '✗ Below noise floor'}
"""

    ax.text(0.1, 0.5, summary_text, fontsize=10, family='monospace',
            verticalalignment='center', bbox=dict(boxstyle='round',
            facecolor='wheat', alpha=0.3))

    plt.tight_layout()
    plt.savefig('/Users/jbrown/Documents/alegria/ai-simulations/acousto-nmr-imaging/basic_signal_model.png',
                dpi=150, bbox_inches='tight')
    print("Plot saved to: acousto-nmr-imaging/basic_signal_model.png")
    plt.close()


# ============================================================================
# RUN
# ============================================================================

if __name__ == "__main__":
    results = run_simulation()

    print()
    print("=" * 70)
    print("CONCLUSION")
    print("=" * 70)
    print()
    print("This simulation models the BASIC physics of acousto-NMR imaging.")
    print("Key findings will depend on the displacement amplitude achieved,")
    print("which has large uncertainty (±50% or more).")
    print()
    print("Next steps:")
    print("  1. Validate displacement estimates with MRE literature")
    print("  2. Add spatial encoding model (ultrasound scanning)")
    print("  3. Include physiological noise sources")
    print("  4. Compare to conventional gradient encoding")
    print()
    print("See README.md for detailed assumptions and uncertainties.")
