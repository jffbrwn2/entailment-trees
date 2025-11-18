# Claude Guidelines for AI Simulations Project

## Purpose
This project tests Claude's ability to generate simulations of potential neural recording devices to evaluate their feasibility from first principles.

## Core Principles

### 1. Clarity and Truth
These are the most important values for all work in this project.

**Documentation Requirements:**
- Every simulation must have a document describing:
  - The implementation idea
  - ALL assumptions made
  - How assumptions connect to implementation details
  - Things I do not know, with ideas for how to obtain that information if possible

**Central Focus: Noise and Interference**
- Understanding how noise and the interference of many factors together is the CORE of whether ideas work
- Incorporating noise and interference into simulations is THE central goal
- Every simulation must rigorously model these real-world complexities

**Sanity Checks:**
Before accepting any simulation result, verify the following. When a check fails → investigate before proceeding.

*Physical Sanity:*
1. **Dimensional Analysis** - All equations must have consistent units. Check every term.
2. **Order of Magnitude** - Results within ~10x of related systems or literature values
3. **Limiting Cases** - Model behaves correctly when parameters → 0 or → ∞
4. **Physical Realizability** - All parameters within achievable ranges (cite safety limits, tech limits)
5. **Conservation Laws** - Energy/charge/mass conserved unless explicitly dissipated
6. **Sign Checks** - Are positive/negative values physically meaningful? (e.g., PSD cannot be negative)
7. **Noise Floors** - Compare signals to fundamental limits (thermal noise: ~4kT·R·Δf, shot noise)

*Computational Sanity:*
8. **Numerical Stability** - No NaN/Inf in results; check filter stability (poles inside unit circle)
9. **Sampling Theorem** - Sample rate ≥ 2× highest frequency of interest (avoid aliasing)
10. **Resolution vs Precision** - Is numerical precision sufficient for the signal levels involved?

*Model Validity:*
11. **Assumption Traceability** - Every assumption traces to literature citation OR marked "Unknown"
12. **Parameter Ranges** - All inputs physically/practically achievable with citations
13. **Symmetry Checks** - Model respects physical symmetries (time-reversal, spatial)
14. **Back-of-Envelope** - Can you estimate the answer within an order of magnitude with simple math?

*Results Interpretation:*
15. **SNR Reality Check** - Compare SNR to what's achievable in similar measurement systems
16. **Plausibility Testing** - If this worked easily, why hasn't it been done? What barriers exist?
17. **Error Propagation** - If key parameter has ±X% uncertainty, how does it affect conclusions?

Document any assumptions that cannot be validated. Clearly mark critical unknowns.

### 2. Organization
Critical for understanding and maintaining the work.

**Code Quality:**
- All code must be well-written
- Always follow the KISS principle (Keep It Simple, Stupid)
- Prefer clarity over cleverness

**Project Structure:**
- Each sufficiently distinct approach goes in a separate folder
- Each folder must contain a README describing:
  - The idea
  - My interpretation of the implementation
- Within each folder:
  - Simulations of varying resolution in separate scripts OR
  - Distinct cells in Jupyter notebooks

### 3. Responsibility
Given the latitude provided in this project:

**Safety First:**
- Never do anything to harm the computer or the user
- Keep every additional thing within the environment we create
- No external dependencies or actions that could compromise system integrity



## Workflow
1. Understand the neural recording concept
2. Document assumptions and unknowns
3. Design simulation with noise/interference as primary consideration
4. Implement following organizational structure
5. Test and validate
6. Document results and learnings

IMPORTANT! At the end, I want a simulation that clearly establishes how the different parameters and assumptions interact to determine the feasibility of the idea.
