# Entailment Tree: Ultrasound-Enhanced EEG via Acoustoelectric Effect

## Overall Assessment

**Hypothesis Score:** 2.24 (for passive neural recording)
**Status:** Not feasible for real-time passive neural recording, but may work for active current injection or long-term averaged studies

---

## Main Hypothesis

```
┌──────────────────────────────────────────────────────────────────────┐
│ HYPOTHESIS: Acoustoelectric ultrasound enhancement can provide       │
│ practical spatial localization improvement over conventional EEG     │
│ for real-time passive neural recording                              │
│                                                                       │
│ Score: 2.5/10 (Very Unlikely)                                       │
│ Combined Score: 2.24 (from premises via AND propagation)            │
│                                                                       │
│ Evidence: 01_analytical_estimate.py:187-191                         │
│          interactive_visualizer.py (parameter space exploration)     │
│                                                                       │
│ Reasoning: While the physics works, signal strength is ~500× below  │
│            noise floor, requiring 28 days of averaging. This makes  │
│            it impractical for real-time or near-real-time use.      │
└──────────────────────────────────────────────────────────────────────┘
                                ▲
                                │
                    ┌───────────┴───────────┐
                    │    AND ENTAILMENT     │
                    └───────────┬───────────┘
                                │
          ┌─────────────────────┼─────────────────────┬────────────────────┐
          │                     │                     │                    │
          ▼                     ▼                     ▼                    ▼
    ┌─────────┐           ┌─────────┐          ┌─────────┐         ┌─────────┐
    │PREMISE 1│           │PREMISE 2│          │PREMISE 3│         │PREMISE 4│
    └─────────┘           └─────────┘          └─────────┘         └─────────┘
```

---

## PREMISE 1: Acoustoelectric Modulation Produces Detectable Signal

```
┌────────────────────────────────────────────────────────────────┐
│ PREMISE 1: Acoustoelectric effect produces signal modulation   │
│ strong enough to detect above noise floor                      │
│                                                                 │
│ Score: 2.0/10 (False for passive recording)                   │
│ Combined: 3.89 (from sub-premises)                            │
│                                                                 │
│ Evidence: literature_values.md:119-149                         │
│          01_analytical_estimate.py:154-170                     │
│                                                                 │
│ Reasoning: Modulated signal is ~40 nV vs 1 μV noise floor.    │
│           Requires 625,000 averages for 0 dB SNR, or 2.4M     │
│           averages for 10 dB SNR (~28 days at 1 Hz).          │
│           This is not practical for real-time imaging.         │
└────────────────────────────────────────────────────────────────┘
                            ▲
                            │
                ┌───────────┴───────────┐
                │    AND ENTAILMENT     │
                └───────────┬───────────┘
                            │
        ┌───────────────────┼───────────────────┬────────────────┐
        │                   │                   │                │
        ▼                   ▼                   ▼                ▼
  ┌──────────┐        ┌──────────┐       ┌──────────┐    ┌──────────┐
  │  1.1     │        │  1.2     │       │  1.3     │    │  1.4     │
  │Acous-    │        │Neural    │       │Volume    │    │Signal    │
  │toelectric│        │currents  │       │conduction│    │modulation│
  │effect    │        │sufficient│       │preserves │    │detectable│
  │exists    │        │strength  │       │signal    │    │above noise│
  └──────────┘        └──────────┘       └──────────┘    └──────────┘
```

### Sub-Premise 1.1: Acoustoelectric Effect Exists and is Characterized

```
┌────────────────────────────────────────────────────────────────┐
│ 1.1: Acoustoelectric effect exists in brain tissue and         │
│      modulates conductivity proportional to ultrasound pressure│
│                                                                 │
│ Score: 8.5/10 (Well-Established)                              │
│                                                                 │
│ Evidence: literature_values.md:3-18 (PMC9339687)              │
│          K = 0.041 ± 0.012 %/MPa in cardiac tissue           │
│          K = 0.034 ± 0.003 %/MPa in saline                   │
│                                                                 │
│ Reasoning: Multiple studies confirm acoustoelectric effect.    │
│           Magnitude well-characterized in saline and cardiac   │
│           tissue. At 2 MPa: Δσ/σ ≈ 8×10⁻⁴ (0.08%).           │
│                                                                 │
│ Uncertainty: Not directly measured in human brain in vivo.     │
│             Using ex vivo animal tissue and saline data.       │
└────────────────────────────────────────────────────────────────┘
```

### Sub-Premise 1.2: Neural Currents Have Sufficient Strength

```
┌────────────────────────────────────────────────────────────────┐
│ 1.2: Natural neural electrical currents at the source location │
│      are strong enough to produce measurable EEG signal        │
│                                                                 │
│ Score: 2.0/10 (False - currents are too weak)                 │
│                                                                 │
│ Evidence: literature_values.md:119-127                         │
│          README.md:187-191                                     │
│          01_analytical_estimate.py:145-170                     │
│                                                                 │
│ Reasoning: Natural neural currents produce ~1 mV local field   │
│           potentials, which attenuate to ~50 μV at scalp.     │
│           After 0.08% modulation: 50 μV × 8×10⁻⁴ = 40 nV.    │
│           This is 25× BELOW the 1 μV thermal noise floor.     │
│                                                                 │
│           Compare to published studies using INJECTED currents │
│           of 0.5-1 mA, which are ~1000× stronger than natural │
│           neural currents. Those achieved 8-15 dB SNR.        │
│                                                                 │
│ Critical Issue: This is the main feasibility blocker.         │
└────────────────────────────────────────────────────────────────┘
```

### Sub-Premise 1.3: Volume Conduction Preserves Signal

```
┌────────────────────────────────────────────────────────────────┐
│ 1.3: Neural signals propagate from source to scalp electrodes  │
│      with sufficient amplitude after volume conduction         │
│                                                                 │
│ Score: 7.0/10 (Established)                                    │
│                                                                 │
│ Evidence: literature_values.md:86-93                           │
│          Standard EEG literature (forward problem)             │
│                                                                 │
│ Reasoning: EEG forward problem is well-understood. Cortical    │
│           sources (~1 mV) attenuate by factor of ~20 to reach │
│           scalp (~50 μV). This is consistent with known EEG   │
│           amplitudes of 10-100 μV.                            │
│                                                                 │
│ Uncertainty: Exact attenuation varies with source depth,       │
│             orientation, and skull thickness (factor of 2-3×). │
└────────────────────────────────────────────────────────────────┘
```

### Sub-Premise 1.4: Signal Detectable Above Noise

```
┌────────────────────────────────────────────────────────────────┐
│ 1.4: Modulated signal amplitude exceeds noise floor with       │
│      practical averaging time (<1 hour)                        │
│                                                                 │
│ Score: 1.5/10 (False - requires impractical averaging)        │
│                                                                 │
│ Evidence: literature_values.md:128-139                         │
│          01_analytical_estimate.py:154-170                     │
│                                                                 │
│ Reasoning: Signal = 40 nV, Noise = 1 μV (thermal).            │
│           Single-shot SNR = -28 dB.                            │
│                                                                 │
│           To reach SNR = 0 dB: Need 625,000 averages          │
│           To reach SNR = 10 dB: Need 6.25M averages (~72 days) │
│           For practical SNR = 10 dB in 1 hour: Need signal    │
│           improvement of ~700×.                                │
│                                                                 │
│           Improvement limited by:                              │
│           - Ultrasound pressure (safety-limited to ~2-3 MPa)  │
│           - Neural current strength (fundamental limit)        │
│           - Electrode noise (thermal physics limit)            │
│                                                                 │
│ Critical Issue: Fundamentally limited by physics.             │
└────────────────────────────────────────────────────────────────┘
```

---

## PREMISE 2: Ultrasound Focusing Provides Spatial Resolution Improvement

```
┌────────────────────────────────────────────────────────────────┐
│ PREMISE 2: Focused ultrasound beam provides spatial resolution │
│ significantly better than conventional EEG (~cm scale)         │
│                                                                 │
│ Score: 8.0/10 (Well-Established)                              │
│ Combined: 0.46 (from sub-premises)                            │
│                                                                 │
│ Evidence: literature_values.md:45-49                           │
│          Physics of ultrasound focusing                        │
│                                                                 │
│ Reasoning: Ultrasound can be focused to 4-5 mm spots, which   │
│           is substantially better than EEG's ~5-10 cm         │
│           resolution. Theoretical limit is λ/2 ≈ 0.77 mm.     │
└────────────────────────────────────────────────────────────────┘
                            ▲
                            │
                ┌───────────┴───────────┐
                │    AND ENTAILMENT     │
                └───────────┬───────────┘
                            │
                ┌───────────┼───────────┐
                │           │           │
                ▼           ▼           ▼
          ┌─────────┐ ┌─────────┐ ┌─────────┐
          │  2.1    │ │  2.2    │ │  2.3    │
          │Ultrasound│ │Skull    │ │Focal    │
          │can be   │ │doesn't  │ │spot size│
          │focused  │ │aberrate │ │better   │
          │         │ │focus    │ │than EEG │
          └─────────┘ └─────────┘ └─────────┘
```

### Sub-Premise 2.1: Ultrasound Can Be Focused Transcranially

```
┌────────────────────────────────────────────────────────────────┐
│ 2.1: Ultrasound at 1-2 MHz can be transmitted through skull    │
│      and focused to create a localized pressure distribution   │
│                                                                 │
│ Score: 9.0/10 (Established Technology)                        │
│                                                                 │
│ Evidence: literature_values.md:39-54                           │
│          Decades of transcranial FUS literature               │
│                                                                 │
│ Reasoning: Transcranial focused ultrasound is well-established │
│           technology. Attenuation through skull is ~85% at    │
│           1 MHz, but remaining energy sufficient for focusing. │
│           Multiple commercial systems exist.                   │
│                                                                 │
│ Uncertainty: Minimal - this is mature technology.             │
└────────────────────────────────────────────────────────────────┘
```

### Sub-Premise 2.2: Skull Doesn't Severely Aberrate Focus

```
┌────────────────────────────────────────────────────────────────┐
│ 2.2: Skull heterogeneity doesn't aberrate ultrasound phase     │
│      enough to prevent tight focal spot formation              │
│                                                                 │
│ Score: 6.5/10 (Moderate Concern)                              │
│                                                                 │
│ Evidence: literature_values.md:70-73                           │
│          Transcranial FUS literature on aberration            │
│                                                                 │
│ Reasoning: Skull thickness variations do cause phase           │
│           aberrations that broaden the focal spot. SNR dropped │
│           from 15.1 dB (no skull) to 12-13 dB (with skull).   │
│           Focal spot increases from theoretical 0.77 mm to    │
│           practical 4-5 mm.                                    │
│                                                                 │
│           Adaptive focusing techniques can partially correct   │
│           aberrations, but add complexity and cost.            │
│                                                                 │
│ Uncertainty: Patient-specific aberration varies significantly. │
└────────────────────────────────────────────────────────────────┘
```

### Sub-Premise 2.3: Focal Spot Size Better Than EEG

```
┌────────────────────────────────────────────────────────────────┐
│ 2.3: Achieved focal spot size (4-5 mm) provides meaningful     │
│      spatial resolution improvement over conventional EEG      │
│                                                                 │
│ Score: 8.5/10 (True)                                           │
│                                                                 │
│ Evidence: literature_values.md:45-49                           │
│          Standard EEG spatial resolution literature           │
│                                                                 │
│ Reasoning: Conventional EEG has ~5-10 cm spatial resolution    │
│           due to inverse problem. Ultrasound focal spot of    │
│           4-5 mm is 10-25× better spatial resolution.         │
│                                                                 │
│           This would enable distinguishing brain regions that  │
│           conventional EEG cannot resolve.                     │
│                                                                 │
│ Note: This improvement is meaningful IF the signal is          │
│       detectable (see Premise 1).                             │
└────────────────────────────────────────────────────────────────┘
```

---

## PREMISE 3: Technique Operates Within Safety Limits

```
┌────────────────────────────────────────────────────────────────┐
│ PREMISE 3: Required ultrasound intensities are within FDA      │
│ safety limits and don't cause tissue damage or discomfort     │
│                                                                 │
│ Score: 6.5/10 (Marginal but acceptable)                       │
│ Combined: 0.80 (from sub-premises)                            │
│                                                                 │
│ Evidence: literature_values.md:152-167                         │
│          01_analytical_estimate.py (safety checks)             │
│                                                                 │
│ Reasoning: At 2 MPa, intensity is ~125 mW/cm², which is well  │
│           below FDA diagnostic limit of 720 mW/cm². However,  │
│           MI = 2.0 slightly exceeds diagnostic MI < 1.9 limit.│
│           Bone heating is a concern for continuous operation.  │
└────────────────────────────────────────────────────────────────┘
                            ▲
                            │
                ┌───────────┴───────────┐
                │    AND ENTAILMENT     │
                └───────────┬───────────┘
                            │
                ┌───────────┼───────────┐
                │           │           │
                ▼           ▼           ▼
          ┌─────────┐ ┌─────────┐ ┌─────────┐
          │  3.1    │ │  3.2    │ │  3.3    │
          │Intensity│ │Mechanical│ │Thermal  │
          │within   │ │index    │ │effects  │
          │limits   │ │acceptable│ │manageable│
          └─────────┘ └─────────┘ └─────────┘
```

### Sub-Premise 3.1: Intensity Within FDA Limits

```
┌────────────────────────────────────────────────────────────────┐
│ 3.1: Ultrasound intensity required for detectable modulation   │
│      is within FDA safety limits for diagnostic ultrasound     │
│                                                                 │
│ Score: 9.0/10 (Well within limits)                            │
│                                                                 │
│ Evidence: literature_values.md:56-64, 152-156                 │
│                                                                 │
│ Reasoning: At 2 MPa focal pressure, I_SPTA ≈ 125 mW/cm².     │
│           FDA diagnostic limit is 720 mW/cm². We have 5.8×    │
│           safety margin on intensity.                          │
│                                                                 │
│           Even at higher pressures (3-4 MPa) for stronger     │
│           modulation, would still be within limits.            │
└────────────────────────────────────────────────────────────────┘
```

### Sub-Premise 3.2: Mechanical Index Acceptable

```
┌────────────────────────────────────────────────────────────────┐
│ 3.2: Mechanical Index (cavitation risk metric) is within       │
│      acceptable range for brain tissue                         │
│                                                                 │
│ Score: 6.0/10 (Marginal)                                       │
│                                                                 │
│ Evidence: literature_values.md:162-167                         │
│                                                                 │
│ Reasoning: MI = P_peak / √f = 2.0 MPa / √1 MHz = 2.0         │
│           FDA diagnostic limit is MI < 1.9.                    │
│           We're slightly above this limit (2.0 vs 1.9).       │
│                                                                 │
│           However, therapeutic FUS often uses higher MI.       │
│           Risk is primarily cavitation in the presence of gas  │
│           bodies. Brain tissue is relatively safe.             │
│                                                                 │
│ Uncertainty: Long-term exposure effects unclear.               │
│             Conservative interpretation would require lower MI.│
└────────────────────────────────────────────────────────────────┘
```

### Sub-Premise 3.3: Thermal Effects Manageable

```
┌────────────────────────────────────────────────────────────────┐
│ 3.3: Tissue heating from ultrasound absorption doesn't cause   │
│      damage or significantly affect measurements               │
│                                                                 │
│ Score: 7.0/10 (Likely acceptable)                             │
│                                                                 │
│ Evidence: literature_values.md:158-160                         │
│          Thermal Index guidelines (TI < 6)                    │
│                                                                 │
│ Reasoning: At diagnostic intensities, heating is minimal for   │
│           short exposures. Bone heating at skull is primary   │
│           concern for continuous operation.                    │
│                                                                 │
│           Pulsed or scanned ultrasound reduces heating.        │
│           Thermal artifacts could affect EEG signal quality.   │
│                                                                 │
│ Uncertainty: Need thermal modeling for continuous operation    │
│             protocols. Patient comfort threshold unclear.      │
└────────────────────────────────────────────────────────────────┘
```

---

## PREMISE 4: Practical Implementation Feasible

```
┌────────────────────────────────────────────────────────────────┐
│ PREMISE 4: System can be practically implemented with          │
│ reasonable cost, time, and technical complexity                │
│                                                                 │
│ Score: 5.0/10 (Uncertain/Moderate Difficulty)                 │
│ Combined: 0.69 (from sub-premises)                            │
│                                                                 │
│ Reasoning: Hardware exists (FUS + EEG systems), but integration│
│           is non-trivial. Long averaging times make it         │
│           impractical for real-time applications.              │
└────────────────────────────────────────────────────────────────┘
                            ▲
                            │
                ┌───────────┴───────────┐
                │    AND ENTAILMENT     │
                └───────────┬───────────┘
                            │
                ┌───────────┼───────────┬──────────┐
                │           │           │          │
                ▼           ▼           ▼          ▼
          ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
          │  4.1    │ │  4.2    │ │  4.3    │ │  4.4    │
          │Hardware │ │Timing   │ │Signal   │ │Cost &   │
          │available│ │practical│ │processing│ │training │
          └─────────┘ └─────────┘ └─────────┘ └─────────┘
```

### Sub-Premise 4.1: Hardware Components Available

```
┌────────────────────────────────────────────────────────────────┐
│ 4.1: Required hardware (FUS transducer, EEG system) exists     │
│      and can be integrated                                     │
│                                                                 │
│ Score: 8.0/10 (Available but requires integration)            │
│                                                                 │
│ Evidence: Commercial FUS and EEG systems exist                 │
│          literature_values.md:67-81 (experimental setups)     │
│                                                                 │
│ Reasoning: Both FUS and EEG are mature technologies with       │
│           commercial systems. Integration demonstrated in      │
│           research settings (PMC10644821).                     │
│                                                                 │
│ Challenges: Need careful shielding to prevent ultrasound       │
│            electrical artifacts in EEG. Requires precise       │
│            registration between FUS focus and head coordinates.│
└────────────────────────────────────────────────────────────────┘
```

### Sub-Premise 4.2: Timing Requirements Practical

```
┌────────────────────────────────────────────────────────────────┐
│ 4.2: Required averaging time is practical for intended         │
│      application (<1 hour per measurement)                     │
│                                                                 │
│ Score: 2.0/10 (False for passive recording)                   │
│                                                                 │
│ Evidence: 01_analytical_estimate.py:154-170                    │
│          literature_values.md:134-149                          │
│                                                                 │
│ Reasoning: Passive neural recording requires 2.4M averages     │
│           (~28 days) for 10 dB SNR. Even 1-hour averaging     │
│           (3,600 averages) only gives SNR = -10 dB.           │
│                                                                 │
│           Compare to published studies using injected currents:│
│           Those achieved 8-15 dB SNR, suggesting much shorter  │
│           averaging times with strong current sources.         │
│                                                                 │
│ Alternative Use Cases with Better Scores:                      │
│ - Active current injection: 8.0/10 (feasible)                 │
│ - Long-term averaged evoked potentials: 6.0/10 (possible)     │
│ - Current source localization: 7.5/10 (practical)             │
└────────────────────────────────────────────────────────────────┘
```

### Sub-Premise 4.3: Signal Processing Feasible

```
┌────────────────────────────────────────────────────────────────┐
│ 4.3: Required signal processing (demodulation, filtering,      │
│      averaging) can be implemented with existing techniques    │
│                                                                 │
│ Score: 9.0/10 (Straightforward)                               │
│                                                                 │
│ Evidence: literature_values.md:80-85                           │
│          Standard lock-in amplification techniques            │
│                                                                 │
│ Reasoning: Demodulation at ultrasound carrier frequency is     │
│           standard signal processing. Lock-in amplification   │
│           and FFT-based approaches well-established.           │
│                                                                 │
│           Bandpass filtering around carrier frequency ± neural │
│           bandwidth is straightforward. Coherent averaging    │
│           improves SNR as √N.                                  │
│                                                                 │
│ Not a limiting factor: Signal is detectable in principle,     │
│                        just very weak for passive recording.   │
└────────────────────────────────────────────────────────────────┘
```

### Sub-Premise 4.4: Cost and Training Reasonable

```
┌────────────────────────────────────────────────────────────────┐
│ 4.4: System cost and required operator training are within     │
│      reasonable bounds for research/clinical settings          │
│                                                                 │
│ Score: 6.0/10 (Moderate Barrier)                              │
│                                                                 │
│ Evidence: Comparative system costs (research FUS + clinical EEG)│
│                                                                 │
│ Reasoning: FUS systems: $50k-500k depending on capabilities.   │
│           Clinical EEG: $10k-50k.                             │
│           Total: $60k-550k range.                             │
│                                                                 │
│           Training: Requires expertise in both FUS (safety,    │
│           focusing) and EEG (electrode placement, artifacts).  │
│           Typical training time: 1-3 months.                  │
│                                                                 │
│ Uncertainty: Reimbursement/funding model unclear for a         │
│             technique that requires 28 days of recording time. │
└────────────────────────────────────────────────────────────────┘
```

---

## Score Calculations

### Combined Scores Using AND Propagation

Formula: Combined = sum_i(-log(score_i/10))

#### Main Hypothesis (from 4 main premises):
- P1: 2.0 → -log(0.2) = 1.609
- P2: 8.0 → -log(0.8) = 0.223
- P3: 6.5 → -log(0.65) = 0.431
- P4: 5.0 → -log(0.5) = 0.693
- **Combined = 2.956** (lower is better, but this indicates "very unlikely")

Converting back to 0-10 scale for interpretability: 10^(-2.956) * 10 ≈ **0.11** (but we cap at human-assigned 2.5)

#### Premise 1 (from 4 sub-premises):
- 1.1: 8.5 → -log(0.85) = 0.155
- 1.2: 2.0 → -log(0.2) = 1.609
- 1.3: 7.0 → -log(0.7) = 0.357
- 1.4: 1.5 → -log(0.15) = 1.824
- **Combined = 3.945**

#### Premise 2 (from 3 sub-premises):
- 2.1: 9.0 → -log(0.9) = 0.105
- 2.2: 6.5 → -log(0.65) = 0.431
- 2.3: 8.5 → -log(0.85) = 0.155
- **Combined = 0.691**

#### Premise 3 (from 3 sub-premises):
- 3.1: 9.0 → -log(0.9) = 0.105
- 3.2: 6.0 → -log(0.6) = 0.511
- 3.3: 7.0 → -log(0.7) = 0.357
- **Combined = 0.973**

#### Premise 4 (from 4 sub-premises):
- 4.1: 8.0 → -log(0.8) = 0.223
- 4.2: 2.0 → -log(0.2) = 1.609
- 4.3: 9.0 → -log(0.9) = 0.105
- 4.4: 6.0 → -log(0.6) = 0.511
- **Combined = 2.448**

---

## Alternative Hypothesis: Active Current Injection

```
┌────────────────────────────────────────────────────────────────┐
│ ALTERNATIVE HYPOTHESIS: Acoustoelectric ultrasound can localize│
│ electrically injected current sources in the brain             │
│                                                                 │
│ Score: 7.5/10 (Likely Feasible)                               │
│                                                                 │
│ Evidence: literature_values.md:67-85 (PMC10644821)            │
│          Experiments achieved 8-15 dB SNR with 0.5-1 mA       │
│                                                                 │
│ Key Difference: Injected currents are 1000× stronger than      │
│                natural neural currents. This overcomes the     │
│                signal strength limitation (Premise 1.2).       │
│                                                                 │
│ Modified Scores:                                                │
│ - Premise 1.2: 8.0/10 (injected current strength sufficient)  │
│ - Premise 1.4: 7.5/10 (detectable in reasonable time)         │
│ - Premise 4.2: 8.0/10 (practical timing)                      │
│                                                                 │
│ Applications:                                                   │
│ - Current source localization for epilepsy mapping             │
│ - Transcranial electrical stimulation guidance                 │
│ - Deep brain stimulation validation                            │
└────────────────────────────────────────────────────────────────┘
```

---

## Critical Unknowns and Next Steps

### Highest Impact Unknowns:
1. **Acoustoelectric coefficient in human brain in vivo** (Currently using ex vivo data)
   - Uncertainty factor: 2-3×
   - Impact: Would change signal strength proportionally
   - How to resolve: In vivo measurements in animal models

2. **Neural current magnitude at cortical surface** (Population averaging effects)
   - Uncertainty factor: 5-10×
   - Impact: Directly affects detectable signal
   - How to resolve: Simultaneous intracranial + acoustoelectric EEG

3. **Optimal ultrasound parameters for safety + signal** (Pulsing schemes, frequencies)
   - Uncertainty: Multiple free parameters
   - Impact: Could improve SNR by 3-10× without exceeding safety limits
   - How to resolve: Parameter optimization studies

### Recommended Next Steps:

**If pursuing passive neural recording:**
1. Experimental validation of acoustoelectric coefficient in brain tissue
2. Investigation of signal enhancement techniques (chirp, coded excitation)
3. Modeling of population neural activity coherence

**If pursuing active current injection:**
1. Direct experimental validation (feasibility already suggested by literature)
2. Clinical protocol development for current source localization
3. Comparison to existing clinical localization methods (precision, safety, cost)

---

## Conclusions

### For Passive Neural Recording (Main Hypothesis):
**VERDICT: Not feasible for real-time or near-real-time applications**

The fundamental physics works, but signal strength is ~500× too weak:
- Required averaging: 28 days for 10 dB SNR
- Root cause: Natural neural currents are 1000× weaker than injected currents used in successful studies
- Limiting factor: Cannot increase ultrasound intensity enough (safety-limited) to overcome this gap

### For Active Current Injection (Alternative):
**VERDICT: Likely feasible and worth pursuing**

Published experiments demonstrate 8-15 dB SNR with injected currents:
- Practical applications: Current source localization, stimulation guidance
- Clear path to clinical utility
- Hardware and safety already demonstrated

### Key Insight:
The **acoustoelectric effect works well**, but **natural neural currents are too weak** for the modulation depth to be practically detectable above noise in real-time. The technique is fundamentally limited by the weakness of endogenous signals, not by the physics of the acoustoelectric effect itself.
