# Ultrasound-Enhanced EEG via Acoustoelectric Effect

## The Idea

Use focused ultrasound (FUS) to locally modulate the electrical conductivity of brain tissue at a specific spatial location. This modulation "tags" neural electrical activity at that location with the ultrasound frequency. By detecting this frequency-shifted component in the EEG signal, we can achieve better spatial localization than conventional EEG, which suffers from the inverse problem.

**Key Concept:** Acoustoelectric effect causes ultrasound pressure waves to modulate tissue conductivity → neural signals at the ultrasound focus get frequency-shifted → demodulation of EEG signal reveals spatially-specific neural activity.

## Implementation Approach

### Simulation Strategy
Build a 2D model progressing from simple to complex:

1. **2D Head Model**: Simplified circular geometry with tissue layers (brain, CSF, skull, scalp)
2. **Ultrasound Focusing**: Model focused ultrasound beam with realistic focusing parameters
3. **EEG Forward Problem**: Calculate how sources propagate to scalp electrodes
4. **Acoustoelectric Modulation**: Model conductivity modulation and frequency shifting
5. **Noise Integration**: Model ALL relevant noise sources
6. **Parameter Sweeps**: Explore spatial resolution vs SNR trade-offs

### What We're Testing
- **Signal Strength**: Is the acoustoelectric modulation detectable above noise?
- **Spatial Resolution**: Does the ultrasound focal spot size meaningfully improve localization?
- **Practical Feasibility**: Are the required ultrasound intensities safe? Are modulation depths sufficient?

## Assumptions and Unknowns

### KNOWN Parameters (with citations needed)
1. **Ultrasound Properties**
   - Typical frequency: 0.5-2 MHz (from FUS literature)
   - Focal spot size: ~λ/2 ≈ 0.75-3 mm at focus
   - Intensity limits: ISPTA < 720 mW/cm² (FDA guideline)
   - Skull attenuation: ~85% at 1 MHz

2. **Brain Tissue Properties**
   - Conductivity: σ_brain ≈ 0.33 S/m
   - Speed of sound: c ≈ 1540 m/s
   - Density: ρ ≈ 1040 kg/m³

3. **EEG Signal Properties**
   - Typical amplitude: 10-100 μV at scalp
   - Frequency bands: 0.5-100 Hz
   - Electrode impedance: 5-10 kΩ

4. **Noise Sources**
   - Thermal noise: ~4kT·R·Δf
   - 60 Hz powerline interference
   - Physiological noise (EMG, EOG, cardiac)
   - Movement artifacts

### CRITICAL UNKNOWNS (Need to determine or cite)

1. **Acoustoelectric Effect Magnitude**
   - **What we need:** Fractional conductivity change Δσ/σ as function of ultrasound pressure
   - **Status:** ⚠️ UNKNOWN - This is THE critical parameter
   - **Literature search needed:** Look for acoustoelectric measurements in brain tissue or similar biological media
   - **Fallback:** If not found, use measurements from saline or other tissues as order-of-magnitude estimates
   - **Impact:** Directly determines signal strength → May be the feasibility dealbreaker

2. **Acoustoelectric Effect Mechanisms**
   - **Question:** Is the effect primarily from:
     - Pressure-induced conductivity changes?
     - Ion displacement?
     - Electrokinetic streaming currents?
   - **Status:** ⚠️ UNCLEAR - Affects how we model the interaction
   - **Impact:** Determines frequency response and phase relationships

3. **Tissue Nonlinearity and Heating**
   - **Question:** How much does ultrasound heat tissue at required intensities?
   - **Status:** ⚠️ UNKNOWN - Critical for safety assessment
   - **Literature needed:** Thermal models of transcranial ultrasound
   - **Impact:** May limit maximum usable ultrasound intensity

4. **Neural Signal Coherence**
   - **Question:** What spatial scale do we need? Single neurons (50 μm) or populations (1 mm+)?
   - **Status:** Depends on application - affects required spatial resolution
   - **Impact:** Determines if ultrasound focal spot is adequate

5. **Frequency Mixing and Harmonics**
   - **Question:** Does the nonlinear mixing create harmonics that could be used?
   - **Status:** ⚠️ UNKNOWN - Could affect signal processing approach
   - **Impact:** Might enable better detection or create interference

### Assumptions → Implementation Connections

| Assumption | If True | If False | Implementation Impact |
|------------|---------|----------|---------------------|
| Δσ/σ ~ 10⁻³ per MPa | Possibly detectable | Need amplification or different approach | Sets signal amplitude in model |
| Acoustoelectric effect is linear | Simple frequency shift | Complex mixing products | Changes demodulation strategy |
| Skull doesn't distort ultrasound phase | Tight focal spot achievable | Aberrated focus → worse resolution | Affects spatial resolution estimate |
| Brain tissue is homogeneous | Clean focusing | Scattering/multipath | Adds interference terms |
| Safety limits allow needed intensity | Feasible | Need alternative modulation | May require parameter redesign |

## Noise and Interference (CORE FOCUS)

### Primary Noise Sources to Model

1. **Thermal Noise**
   - From electrode-tissue interface: Vnoise = √(4kT·R·Δf)
   - Expect: ~0.5-2 μV in EEG bandwidth

2. **Biological Interference**
   - EMG: 10-100 μV (high frequency, 20-300 Hz)
   - EOG: 50-500 μV (low frequency, < 10 Hz)
   - Cardiac: ~10 μV (1-2 Hz)

3. **Ultrasound-Induced Artifacts**
   - Heating artifacts (slow drift)
   - Mechanical vibrations coupling to electrodes
   - Acoustic streaming effects

4. **Volume Conduction Crosstalk**
   - Signals from non-focused regions still reach all electrodes
   - This is what we're trying to overcome!

### Signal-to-Noise Analysis Strategy

Critical question: **What is the modulated signal amplitude vs noise?**

- Neural signal at source: ~1 mV (intracortical)
- After volume conduction to scalp: ~50 μV
- After acoustoelectric modulation: 50 μV × (Δσ/σ) = ???
- Need this >> thermal noise (~1 μV)

**Feasibility criterion:** SNR > 10 dB after reasonable averaging

## Sanity Checks to Apply

Before accepting results, verify:
1. ✓ Units consistent in all equations
2. ✓ Ultrasound intensity within FDA limits
3. ✓ EEG amplitudes in 10-100 μV range
4. ✓ Thermal noise = √(4kT·R·Δf) ≈ 1 μV
5. ✓ Focal spot size ≥ λ/2
6. ✓ Sample rate ≥ 2× max frequency
7. ✓ Energy conservation in wave propagation
8. ✓ Compare SNR to existing EEG systems
9. ✓ Check if limiting case (no ultrasound) → regular EEG
10. ✓ Check if limiting case (infinite modulation) → perfect localization

## Success Criteria

**The simulation should clearly show:**
1. How acoustoelectric modulation depth affects detectable signal strength
2. How ultrasound focal spot size determines spatial resolution improvement
3. Which noise sources dominate and under what conditions
4. The parameter space where SNR > 10 dB is achievable
5. Whether safety-limited ultrasound intensities provide sufficient modulation

**Questions to answer:**
- Is this fundamentally feasible or limited by physics?
- What are the critical unknowns that need experimental validation?
- What parameter improvements would make it feasible if currently marginal?

## Files in This Directory

- `01_analytical_estimate.py` - Back-of-envelope calculations (complete ✓)
- `01_analytical_feasibility.png` - Visualization of analytical results
- `interactive_visualizer.py` - **Interactive web app for exploring parameters** ⭐
- `literature_values.md` - Collected parameters from literature with citations
- `DEPLOYMENT.md` - Guide for running and deploying the visualizer
- `requirements.txt` - Python dependencies for the visualizer

## Quick Start

### Run the Interactive Visualizer

The interactive visualizer is the best way to explore the parameter space:

```bash
# From the ai-simulations directory
pixi run viz
```

Or see [DEPLOYMENT.md](DEPLOYMENT.md) for other options including cloud deployment.

### Run the Analytical Estimate

For a command-line analysis:

```bash
pixi run python ultrasound_eeg_enhancement/01_analytical_estimate.py
```

## What We've Learned So Far

The analytical model reveals that using acoustoelectric effect for **passive EEG enhancement** faces fundamental challenges:

- **Signal strength:** ~41 nV (500× below noise floor)
- **Required averaging:** 2.4 million averages (~28 days)
- **Main limitation:** Natural neural currents are 1000× weaker than injected currents used in published studies

However, the approach **may work for:**
- Active current source localization (inject known current)
- Transcranial stimulation with acoustoelectric readout
- Long-term averaged studies with strong evoked responses

See the interactive visualizer to explore how different assumptions affect these conclusions!
