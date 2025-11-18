# Literature Values for Acoustoelectric Brain Imaging

## Acoustoelectric Effect Magnitude

### Interaction Constant (K_I)
**Source:** Systematic review (PMC9339687)

- **In saline (0.9% NaCl)**: K_I ≈ 10⁻⁹ Pa⁻¹
- **In cardiac tissue**: K = 0.041 ± 0.012 %/MPa
- **In saline (comparison)**: K = 0.034 ± 0.003 %/MPa

**Key equation:** Δρ/ρ₀ = K_I × ΔP

For conductivity (σ = 1/ρ): **Δσ/σ ≈ -Δρ/ρ₀**

**Practical values:**
- At 1 MPa: Δσ/σ ≈ 4 × 10⁻⁴ (0.04%)
- At 2 MPa: Δσ/σ ≈ 8 × 10⁻⁴ (0.08%)

## Brain Tissue Properties

**Source:** Acoustoelectric brain imaging study (PMC10644821) - Pig brain tissue

### Conductivities
- **Gray matter**: σ_gray = 0.2917 S/m
- **White matter**: σ_white = 0.1585 S/m
- **Cerebrospinal fluid (CSF)**: σ_csf = 2.002 S/m
- **Skull**: σ_skull = 0.04282 S/m (15-27% of brain tissue)

### General properties
- **Speed of sound**: c ≈ 1540 m/s
- **Density**: ρ ≈ 1040 kg/m³
- **Acoustic impedance**: Z ≈ 1.6 × 10⁶ kg/(m²·s)

## Ultrasound Parameters

**Source:** Multiple studies from review

### Frequencies Used
- **Typical range**: 0.5 - 8 MHz
- **Cardiac imaging**: 0.5 - 1 MHz
- **Transcranial applications**: 2 - 2.5 MHz (better penetration)
- **Brain imaging experiments**: 1.0 MHz

### Focal Parameters (1 MHz transducer)
- **Focal length**: 20 mm
- **Focal spot diameter (FWHM)**: 4.1 - 4.4 mm
- **Theoretical minimum**: λ/2 ≈ 0.77 mm (for 1 MHz in tissue)
- **Achieved spatial resolution**: Millimeter-level

### Acoustic Pressures
- **Typical focal pressure**: 2.04 MPa
- **FDA safety limit (diagnostic)**: I_SPTA < 720 mW/cm²
- **Therapeutic FUS**: Can reach higher intensities for neural modulation

### Pressure-Intensity Relationship
I = P²/(2ρc) where:
- P = pressure amplitude (Pa)
- ρ = density (kg/m³)
- c = speed of sound (m/s)

For 2 MPa in brain tissue:
I = (2×10⁶)²/(2 × 1040 × 1540) ≈ 1250 W/m² = 125 mW/cm²

## Signal Characteristics

**Source:** Brain imaging experiments (PMC10644821)

### Achieved Performance
- **SNR (FFT-based)**: 8.1 - 15.1 dB depending on tissue configuration
  - Fat tissue: ~8.1 dB
  - Brain tissue: ~12-13 dB
  - Without skull: ~15.1 dB
- **Correlation with source**: r = 0.28 - 0.61

### Experimental Setup
- **Stimulation current**: 0.5 - 1.0 mA sinusoidal at 13 Hz
- **Scanning resolution**: 1 mm steps
- **Sample rate**: 20 kHz (downsampled to 5 kHz)
- **Filter**: PRF ± 50 Hz bandpass

### Signal Sensitivity
- **Cardiac tissue**: 3.2 μV/mA (standard pulses)
- **With chirp excitation**: 3.5 μV/mA (improved by >10 dB vs square pulses)

## EEG Signal Properties

### Typical Amplitudes (at scalp)
- **Overall range**: 10 - 100 μV
- **Alpha (8-13 Hz)**: ~30 μV
- **Beta (13-30 Hz)**: ~10-20 μV
- **Gamma (30-100 Hz)**: ~5-10 μV

### Electrode Properties
- **Impedance**: 5 - 10 kΩ typical
- **Noise floor**: ~1 μV (thermal noise limited)

## Noise Sources

### Thermal (Johnson) Noise
V_n = √(4kTRΔf) where:
- k = 1.38 × 10⁻²³ J/K
- T = 310 K (body temperature)
- R = 5-10 kΩ (electrode impedance)
- Δf = bandwidth

**For EEG (100 Hz bandwidth, 10 kΩ):** V_n ≈ 1.3 μV

### Physiological Noise
- **EMG (muscle)**: 10-100 μV, 20-300 Hz
- **EOG (eye movement)**: 50-500 μV, <10 Hz
- **Cardiac**: ~10 μV, 1-2 Hz
- **Powerline**: 60 Hz (or 50 Hz), can be large without shielding

## Modulation Detection

### Expected Modulated Signal Amplitude

For neural signal S_neural at depth propagating to scalp:

1. **At source (cortex)**: ~1 mV (local field potential)
2. **At scalp (volume conduction)**: ~50 μV (attenuation factor ~20×)
3. **After acoustoelectric modulation**: S_mod = S_scalp × (Δσ/σ)

With Δσ/σ = 8×10⁻⁴ at 2 MPa:
**S_mod ≈ 50 μV × 8×10⁻⁴ = 0.04 μV = 40 nV**

### Detectability Analysis

**Signal:** 40 nV (single measurement)
**Noise:** ~1 μV (thermal)
**SNR:** -28 dB (single measurement)

**Required averaging:** N = (1 μV / 40 nV)² ≈ 625 averages to reach SNR = 0 dB

For SNR = 10 dB: N ≈ 6,250 averages

**Time required** (at 1 Hz stimulation): ~1-2 hours of averaging

### Implications

1. **Feasibility**: Detectable with significant averaging
2. **Real-time limitation**: Not suitable for real-time imaging without improvement
3. **Improvement paths**:
   - Higher ultrasound pressure (safety-limited)
   - Longer averaging (time-limited)
   - Better electrodes (limited by physics)
   - Source localization (computational)

## Safety Considerations

### Ultrasound Safety Limits (FDA)
- **Diagnostic**: I_SPTA < 720 mW/cm²
- **Ophthalmic**: I_SPTA < 50 mW/cm²
- **Fetal**: I_SPTA < 94 mW/cm²

### Thermal Index (TI)
- TI < 6 generally considered safe for neuro applications
- Bone heating is primary concern for transcranial ultrasound

### Mechanical Index (MI)
- MI = P_neg / √f (MPa/√MHz)
- MI < 1.9 for general diagnostic imaging
- Cavitation risk at high MI

**For 1 MHz, 2 MPa:** MI = 2.0 / √1 = 2.0 (slightly above diagnostic limit)

## Key References

1. PMC9339687: "Biological current source imaging method based on acoustoelectric effect: A systematic review" (2022)
2. PMC10644821: "Acoustoelectric brain imaging with different conductivities and acoustic distributions" (2023)
3. Various: Cardiac tissue AE measurements, transcranial ultrasound parameters

## Critical Parameters Summary

| Parameter | Value | Uncertainty | Impact |
|-----------|-------|-------------|--------|
| K (modulation constant) | 0.04 %/MPa | ±0.012 | HIGH - determines signal strength |
| Focal spot size | 4-5 mm | ±0.5 mm | HIGH - determines spatial resolution |
| Safe ultrasound pressure | ~2 MPa | MI-limited | HIGH - limits modulation depth |
| EEG signal amplitude | 50 μV | Factor of 2-5× | MEDIUM - varies with source |
| Electrode noise | 1-2 μV | Factor of 2× | MEDIUM - affects required averaging |

**CRITICAL UNKNOWN:** Acoustoelectric effect in human brain in vivo - all data from ex vivo animal tissue or saline!
