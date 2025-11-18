# Acousto-NMR Imaging

## Core Idea

Use focused ultrasound as a spatial encoding mechanism for low-field MRI instead of (or in addition to) traditional magnetic field gradients.

**Mechanism:**
1. Place brain in static magnetic field B₀
2. Apply RF pulse to excite nuclear spins (low-field MR)
3. Shoot focused ultrasound at specific spatial locations
4. Ultrasound causes tissue displacement → moving spins accumulate phase shifts
5. Detect modulation/sidebands in the MR RF signal
6. Spatial specificity comes from ultrasound focus, not field gradients

## Related Work

This concept is related to **MR Elastography (MRE)**, which uses mechanical vibrations with phase-contrast MRI to image tissue mechanical properties. However, our approach differs:
- **MRE goal**: Measure tissue stiffness/elasticity
- **Our goal**: Use ultrasound-induced motion for spatial encoding of neural signals

## Key Physics

### NMR Basics
- Larmor frequency: ω₀ = γB₀
  - γ (proton gyromagnetic ratio) = 42.58 MHz/T
  - For low field (B₀ = 0.1 T): f₀ = 4.26 MHz
- Phase accumulation for moving spin: Δφ = γ·B₀·∫v(t)dt = γ·B₀·Δx

### Ultrasound-Induced Motion
- Focused ultrasound creates localized displacement
- Displacement amplitude depends on: acoustic pressure, tissue compliance, frequency
- Motion creates phase modulation in MR signal → detectable sidebands

### Signal Detection
- MR signal with ultrasound modulation: S(t) ∝ M₀·exp(iγB₀Δx(t))
- For sinusoidal displacement Δx = A·sin(ωᵤₛ·t):
  - S(t) contains sidebands at f₀ ± fᵤₛ
  - Sideband amplitude depends on modulation index β = γB₀A

## Critical Assumptions

### Known (with literature support)
1. **Proton density in brain**: ~80 M (molar concentration of water protons)
   - Source: Standard MRI physics texts
2. **T1/T2 relaxation times at low field** (0.1-0.5 T):
   - Gray matter: T1 ~ 600-800 ms, T2 ~ 80-100 ms
   - White matter: T1 ~ 400-600 ms, T2 ~ 60-80 ms
   - Source: Bottomley et al., Med Phys 1984; low-field MRI literature
3. **Ultrasound focal spot size**: 1-3 mm at typical frequencies (0.5-2 MHz)
   - Source: Focused ultrasound literature
4. **Acoustic pressure limits (safety)**: < 1-2 MPa for brain imaging
   - Source: FDA guidelines for diagnostic ultrasound
5. **Thermal noise in RF coil**: Vₙ = √(4kTRΔf)
   - Source: Fundamental physics

### Partially Known (estimates with uncertainty)
1. **Tissue displacement from ultrasound**:
   - Depends on: acoustic pressure P, tissue Young's modulus E, ultrasound frequency
   - Brain Young's modulus: ~1-10 kPa (highly variable in literature)
   - Estimated displacement: A ~ P/(ω²ρ) or from radiation force
   - **Uncertainty**: ±50% depending on tissue region and measurement method

2. **MR signal strength at low field**:
   - S/N ∝ B₀^(7/4) (approximate scaling)
   - Low field (0.1 T) has ~30-100× lower SNR than 1.5T
   - **Uncertainty**: Coil design and proximity greatly affect sensitivity

3. **Ultrasound heating**:
   - Temperature rise ΔT ∝ α·I·t (α = absorption coefficient)
   - Brain: α ~ 0.5-1.0 dB/cm/MHz
   - **Uncertainty**: Varies with tissue type, perfusion

### Unknown (critical gaps)
1. **What is the achievable displacement amplitude A in brain tissue for safe ultrasound intensities?**
   - Ideas to find out:
     - Review MRE literature for measured displacement amplitudes
     - Look at focused ultrasound neuromodulation studies
     - Finite element modeling of ultrasound-tissue interaction

2. **How does the ultrasound-induced phase modulation compare to thermal/physiological noise?**
   - Phase noise from:
     - Thermal motion of water molecules
     - Blood flow
     - Cardiac/respiratory motion
   - Ideas to find out:
     - Calculate thermal de-phasing time from diffusion
     - Review phase-contrast MRI noise literature
     - Estimate from MRE phase noise measurements

3. **What is the temporal resolution vs spatial resolution tradeoff?**
   - Must scan ultrasound focus across volume
   - Each location requires sufficient MR signal averaging
   - Ideas to find out:
     - Calculate SNR per voxel per unit time
     - Compare to gradient encoding time requirements
     - Consider parallel acquisition schemes (multiple ultrasound foci?)

4. **Does ultrasound disrupt the MR measurement itself?**
   - Mechanical vibration could affect coil coupling
   - Ultrasound transducers could create RF interference
   - Ideas to find out:
     - Review simultaneous ultrasound-MRI literature
     - Consider shielding and timing strategies

5. **What is the off-resonance effect of ultrasound on tissue?**
   - Pressure waves → density modulation → slight B₀ changes?
   - Likely very small but could affect phase
   - Ideas to find out: Literature search, calculate from susceptibility changes

## Implementation Plan

### Phase 1: Basic Signal Model (Current)
- Model MR signal with ultrasound phase modulation
- Include thermal noise
- Calculate modulation index and sideband amplitudes
- Sanity check: Compare to thermal noise floor

### Phase 2: Spatial Encoding
- Model ultrasound focal spot (Gaussian beam approximation)
- Simulate scanning pattern
- Calculate point spread function
- Include off-focus tissue motion

### Phase 3: Realistic Noise Model
- Add physiological noise (cardiac, respiratory, blood flow)
- Model coil sensitivity and geometry
- Include T1/T2 relaxation effects
- Ultrasound heating and its effect on T1/T2

### Phase 4: Feasibility Analysis
- Compare SNR to conventional gradient encoding
- Estimate temporal resolution for neural imaging
- Identify critical parameter regimes
- Determine if approach is viable

## Success Criteria

The simulation should answer:
1. **What SNR can we achieve** for acousto-NMR compared to conventional low-field MRI?
2. **What spatial resolution** is achievable given ultrasound focus and noise?
3. **What temporal resolution** is feasible for neural activity imaging?
4. **What are the critical unknowns** that would need experimental validation?
5. **Is this approach fundamentally feasible** or are there showstopping physics limitations?

## Key Parameters to Explore

- B₀: 0.05 - 0.5 T (low field range)
- Ultrasound frequency: 0.5 - 2 MHz
- Acoustic pressure: 0.1 - 2 MPa
- Tissue displacement amplitude: 0.1 - 10 μm
- Integration time: 10 ms - 1 s
- Voxel size: 1 - 5 mm
