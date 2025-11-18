"""
Interactive Visualizer for Ultrasound-Enhanced EEG Feasibility

This Streamlit app allows interactive exploration of all parameters and assumptions
to understand feasibility and parameter sensitivity.

To run: streamlit run interactive_visualizer.py
"""

import streamlit as st
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Page config
st.set_page_config(
    page_title="Ultrasound-Enhanced EEG Explorer",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
k_B = 1.38e-23  # Boltzmann constant (J/K)
T = 310  # Body temperature (K)

# Custom CSS
st.markdown("""
<style>
.big-font {
    font-size:20px !important;
    font-weight: bold;
}
.warning-box {
    padding: 10px;
    background-color: #fff3cd;
    border-left: 5px solid #ffc107;
    margin: 10px 0;
}
.danger-box {
    padding: 10px;
    background-color: #f8d7da;
    border-left: 5px solid #dc3545;
    margin: 10px 0;
}
.success-box {
    padding: 10px;
    background-color: #d4edda;
    border-left: 5px solid #28a745;
    margin: 10px 0;
}
.info-box {
    padding: 10px;
    background-color: #d1ecf1;
    border-left: 5px solid #17a2b8;
    margin: 10px 0;
}
</style>
""", unsafe_allow_html=True)

# Title
st.title("🧠 Ultrasound-Enhanced EEG Feasibility Explorer")
st.markdown("""
Explore how acoustoelectric effect parameters affect the feasibility of using
focused ultrasound to improve EEG spatial resolution. Adjust parameters to see
real-time updates of signal strength, noise, and required averaging.
""")

# Sidebar - Parameter Inputs
st.sidebar.header("📊 Parameters")

st.sidebar.markdown("---")
st.sidebar.subheader("🔊 Acoustoelectric Effect")
st.sidebar.markdown("*Source: Cardiac tissue measurements (PMC9339687)*")

K_percent_per_MPa = st.sidebar.slider(
    "K: Interaction constant (%/MPa)",
    min_value=0.01,
    max_value=0.15,
    value=0.041,
    step=0.001,
    help="Literature: 0.041±0.012 %/MPa in cardiac tissue"
)
K_interaction = K_percent_per_MPa / 100 / 1e6  # Convert to per Pa

st.sidebar.markdown("---")
st.sidebar.subheader("🌊 Ultrasound Parameters")
st.sidebar.markdown("*Source: Typical FUS literature*")

P_acoustic_MPa = st.sidebar.slider(
    "Pressure (MPa)",
    min_value=0.5,
    max_value=3.0,
    value=2.0,
    step=0.1,
    help="Safety limit: MI < 1.9 (depends on frequency)"
)
P_acoustic = P_acoustic_MPa * 1e6  # Convert to Pa

f_ultrasound_MHz = st.sidebar.slider(
    "Frequency (MHz)",
    min_value=0.5,
    max_value=3.0,
    value=1.0,
    step=0.1,
    help="Typical: 0.5-2 MHz for transcranial applications"
)
f_ultrasound = f_ultrasound_MHz * 1e6  # Convert to Hz

focal_spot_mm = st.sidebar.slider(
    "Focal spot FWHM (mm)",
    min_value=1.0,
    max_value=10.0,
    value=4.2,
    step=0.1,
    help="Literature: 4.2 mm at 1 MHz. Theoretical minimum: λ/2"
)
focal_spot = focal_spot_mm / 1000  # Convert to m

st.sidebar.markdown("---")
st.sidebar.subheader("🧠 Neural Signal")
st.sidebar.markdown("*Source: Typical cortical measurements*")

V_source_mV = st.sidebar.slider(
    "Cortical LFP amplitude (mV)",
    min_value=0.1,
    max_value=5.0,
    value=1.0,
    step=0.1,
    help="Local field potential amplitude at cortex"
)
V_source = V_source_mV / 1000  # Convert to V

attenuation_factor = st.sidebar.slider(
    "Volume conduction attenuation",
    min_value=5,
    max_value=50,
    value=20,
    step=1,
    help="How much signal attenuates from cortex to scalp"
)

st.sidebar.markdown("---")
st.sidebar.subheader("📡 Electrode & Noise")
st.sidebar.markdown("*Source: Typical EEG system*")

R_electrode_kohm = st.sidebar.slider(
    "Electrode impedance (kΩ)",
    min_value=1,
    max_value=20,
    value=10,
    step=1,
    help="Typical: 5-10 kΩ for good EEG electrodes"
)
R_electrode = R_electrode_kohm * 1000  # Convert to Ω

bandwidth_eeg = st.sidebar.slider(
    "EEG bandwidth (Hz)",
    min_value=50,
    max_value=200,
    value=100,
    step=10,
    help="Typical EEG recording bandwidth"
)

V_emg_uV = st.sidebar.slider(
    "EMG noise (μV)",
    min_value=5,
    max_value=100,
    value=20,
    step=5,
    help="Physiological muscle artifact noise"
)
V_emg = V_emg_uV / 1e6  # Convert to V

stimulation_rate_Hz = st.sidebar.slider(
    "Stimulation rate (Hz)",
    min_value=0.1,
    max_value=10.0,
    value=1.0,
    step=0.1,
    help="How often neural events occur for averaging"
)

target_SNR_dB = st.sidebar.slider(
    "Target SNR (dB)",
    min_value=5,
    max_value=20,
    value=10,
    step=1,
    help="Desired signal-to-noise ratio"
)

# ============================================================================
# CALCULATIONS
# ============================================================================

# Tissue properties
c_tissue = 1540  # m/s
rho_tissue = 1040  # kg/m³

# Wavelength and theoretical focal spot
wavelength = c_tissue / f_ultrasound
focal_spot_theoretical = wavelength / 2

# Mechanical Index (safety)
MI_actual = P_acoustic_MPa / np.sqrt(f_ultrasound_MHz)
MI_limit = 1.9

# Intensity
I_spta = P_acoustic**2 / (2 * rho_tissue * c_tissue)  # W/m²
I_spta_mW_cm2 = I_spta / 10  # mW/cm²

# Acoustoelectric modulation
delta_sigma_over_sigma = K_interaction * P_acoustic

# Signal cascade
V_scalp = V_source / attenuation_factor
V_modulated = V_scalp * delta_sigma_over_sigma

# Noise
V_thermal = np.sqrt(4 * k_B * T * R_electrode * bandwidth_eeg)
V_noise_total = np.sqrt(V_thermal**2 + V_emg**2)

# SNR
SNR_single = V_modulated / V_noise_total
SNR_single_dB = 20 * np.log10(SNR_single) if SNR_single > 0 else -100

# Averaging requirements
target_SNR_linear = 10**(target_SNR_dB/20)
N_averages_required = max(1, (target_SNR_linear / SNR_single)**2)
time_required_sec = N_averages_required / stimulation_rate_Hz

# Spatial resolution
eeg_resolution = 20e-3  # m
improvement_factor = eeg_resolution / focal_spot

# ============================================================================
# DISPLAY RESULTS
# ============================================================================

# Top metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Modulated Signal",
        f"{V_modulated*1e9:.1f} nV",
        help="Signal amplitude after acoustoelectric modulation"
    )

with col2:
    st.metric(
        "Total Noise",
        f"{V_noise_total*1e6:.1f} μV",
        help="Thermal + physiological noise"
    )

with col3:
    snr_color = "normal" if SNR_single_dB > 0 else "inverse"
    st.metric(
        "Single-Shot SNR",
        f"{SNR_single_dB:.1f} dB",
        help="Signal-to-noise ratio without averaging"
    )

with col4:
    if time_required_sec < 60:
        time_str = f"{time_required_sec:.1f} sec"
    elif time_required_sec < 3600:
        time_str = f"{time_required_sec/60:.1f} min"
    elif time_required_sec < 86400:
        time_str = f"{time_required_sec/3600:.1f} hr"
    else:
        time_str = f"{time_required_sec/86400:.1f} days"

    st.metric(
        f"Time for {target_SNR_dB} dB SNR",
        time_str,
        help=f"Requires {N_averages_required:.0f} averages"
    )

# Safety warnings
st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    if MI_actual > MI_limit:
        st.markdown(f"""
        <div class="danger-box">
        ⚠️ <b>Safety Warning</b><br>
        MI = {MI_actual:.2f} exceeds limit ({MI_limit})
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="success-box">
        ✓ <b>MI Within Limits</b><br>
        MI = {MI_actual:.2f} (limit: {MI_limit})
        </div>
        """, unsafe_allow_html=True)

with col2:
    if I_spta_mW_cm2 > 720:
        st.markdown(f"""
        <div class="danger-box">
        ⚠️ <b>Intensity Warning</b><br>
        {I_spta_mW_cm2:.0f} mW/cm² exceeds FDA limit (720)
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="success-box">
        ✓ <b>Intensity OK</b><br>
        {I_spta_mW_cm2:.0f} mW/cm² (limit: 720)
        </div>
        """, unsafe_allow_html=True)

with col3:
    if focal_spot < focal_spot_theoretical:
        st.markdown(f"""
        <div class="danger-box">
        ⚠️ <b>Focal Spot Too Small</b><br>
        Cannot be smaller than λ/2 = {focal_spot_theoretical*1000:.2f} mm
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="info-box">
        ℹ️ <b>Spatial Resolution</b><br>
        {improvement_factor:.1f}× better than EEG
        </div>
        """, unsafe_allow_html=True)

# ============================================================================
# VISUALIZATIONS
# ============================================================================

st.markdown("---")
st.header("📈 Interactive Visualizations")

# Create tabs for different views
tab1, tab2, tab3, tab4 = st.tabs([
    "Signal Cascade",
    "Parameter Sensitivity",
    "Trade-off Analysis",
    "Assumptions & Sources"
])

with tab1:
    st.subheader("Signal Attenuation Cascade")

    # Signal cascade waterfall
    fig = go.Figure()

    stages = ['Cortex<br>(LFP)', 'Scalp<br>(EEG)', 'Modulated<br>(AE)']
    amplitudes_uV = [V_source*1e6, V_scalp*1e6, V_modulated*1e6]
    colors = ['#2ecc71', '#3498db', '#e74c3c']

    fig.add_trace(go.Bar(
        x=stages,
        y=amplitudes_uV,
        marker_color=colors,
        text=[f"{a:.2e} μV" for a in amplitudes_uV],
        textposition='outside',
        name='Signal'
    ))

    fig.add_hline(
        y=V_noise_total*1e6,
        line_dash="dash",
        line_color="orange",
        annotation_text=f"Noise floor: {V_noise_total*1e6:.2f} μV",
        annotation_position="right"
    )

    fig.update_layout(
        yaxis_type="log",
        yaxis_title="Amplitude (μV)",
        height=400,
        showlegend=False,
        hovermode='x unified'
    )

    st.plotly_chart(fig, use_container_width=True)

    # Breakdown table
    st.markdown("**Detailed Breakdown:**")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"""
        **Signals:**
        - Cortical LFP: {V_source*1e3:.2f} mV
        - After volume conduction (÷{attenuation_factor}): {V_scalp*1e6:.2f} μV
        - After AE modulation (×{delta_sigma_over_sigma:.2e}): {V_modulated*1e9:.2f} nV
        - **Signal/Noise ratio: {V_modulated/V_noise_total:.2e}** ({SNR_single_dB:.1f} dB)
        """)

    with col2:
        st.markdown(f"""
        **Noise Sources:**
        - Thermal noise: {V_thermal*1e6:.3f} μV
        - EMG noise: {V_emg*1e6:.1f} μV
        - **Total (RMS): {V_noise_total*1e6:.2f} μV**

        **Modulation:**
        - Δσ/σ = {delta_sigma_over_sigma*100:.4f}% = {delta_sigma_over_sigma:.2e}
        """)

with tab2:
    st.subheader("Parameter Sensitivity Analysis")

    # Create parameter sweep plots
    col1, col2 = st.columns(2)

    with col1:
        # Pressure vs time
        P_range = np.linspace(0.5, 3.0, 50) * 1e6
        delta_sigma_range = K_interaction * P_range
        V_mod_range = V_scalp * delta_sigma_range
        SNR_range = V_mod_range / V_noise_total
        N_avg_range = (target_SNR_linear / SNR_range)**2
        time_range = N_avg_range / stimulation_rate_Hz / 60  # minutes
        MI_range = P_range/1e6 / np.sqrt(f_ultrasound_MHz)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=P_range/1e6,
            y=time_range,
            mode='lines',
            line=dict(color='blue', width=3),
            name='Acquisition time'
        ))

        # Color regions by safety
        fig.add_vrect(
            x0=0, x1=MI_limit*np.sqrt(f_ultrasound_MHz),
            fillcolor="green", opacity=0.1,
            annotation_text="Safe", annotation_position="top left"
        )
        fig.add_vrect(
            x0=MI_limit*np.sqrt(f_ultrasound_MHz), x1=3.0,
            fillcolor="red", opacity=0.1,
            annotation_text="MI > 1.9", annotation_position="top right"
        )

        # Add reference lines
        fig.add_hline(y=1, line_dash="dash", line_color="orange",
                     annotation_text="1 min")
        fig.add_hline(y=60, line_dash="dash", line_color="red",
                     annotation_text="1 hour")

        # Mark current point
        fig.add_trace(go.Scatter(
            x=[P_acoustic_MPa],
            y=[time_required_sec/60],
            mode='markers',
            marker=dict(size=15, color='red', symbol='star'),
            name='Current'
        ))

        fig.update_layout(
            xaxis_title="Ultrasound Pressure (MPa)",
            yaxis_title="Acquisition Time (minutes)",
            yaxis_type="log",
            height=400,
            hovermode='x unified'
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # K constant vs time
        K_range = np.linspace(0.01, 0.15, 50) / 100 / 1e6  # per Pa
        delta_sigma_K = K_range * P_acoustic
        V_mod_K = V_scalp * delta_sigma_K
        SNR_K = V_mod_K / V_noise_total
        N_avg_K = (target_SNR_linear / SNR_K)**2
        time_K = N_avg_K / stimulation_rate_Hz / 60  # minutes

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=K_range*1e6*100,  # Convert to %/MPa
            y=time_K,
            mode='lines',
            line=dict(color='purple', width=3),
            name='Acquisition time'
        ))

        # Add literature value range
        fig.add_vrect(
            x0=0.029, x1=0.053,
            fillcolor="green", opacity=0.2,
            annotation_text="Literature<br>range",
            annotation_position="top left"
        )

        # Mark current point
        fig.add_trace(go.Scatter(
            x=[K_percent_per_MPa],
            y=[time_required_sec/60],
            mode='markers',
            marker=dict(size=15, color='red', symbol='star'),
            name='Current'
        ))

        fig.add_hline(y=1, line_dash="dash", line_color="orange")
        fig.add_hline(y=60, line_dash="dash", line_color="red")

        fig.update_layout(
            xaxis_title="Interaction Constant K (%/MPa)",
            yaxis_title="Acquisition Time (minutes)",
            yaxis_type="log",
            height=400,
            hovermode='x unified'
        )

        st.plotly_chart(fig, use_container_width=True)

    # SNR improvement with averaging
    st.markdown("**SNR Improvement with Averaging:**")
    N_avg_plot = np.logspace(0, 7, 100)
    SNR_plot = SNR_single * np.sqrt(N_avg_plot)
    SNR_plot_dB = 20 * np.log10(SNR_plot)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=N_avg_plot,
        y=SNR_plot_dB,
        mode='lines',
        line=dict(color='blue', width=3),
        name='SNR'
    ))

    fig.add_hline(y=target_SNR_dB, line_dash="dash", line_color="green",
                 annotation_text=f"Target: {target_SNR_dB} dB")
    fig.add_hline(y=0, line_dash="dash", line_color="orange",
                 annotation_text="Unity SNR")
    fig.add_vline(x=N_averages_required, line_dash="dash", line_color="red",
                 annotation_text=f"Required: {N_averages_required:.0e}")

    fig.update_layout(
        xaxis_title="Number of Averages",
        yaxis_title="SNR (dB)",
        xaxis_type="log",
        height=400,
        hovermode='x unified'
    )

    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("Trade-off Analysis")

    st.markdown("""
    Explore fundamental trade-offs between spatial resolution, signal strength,
    safety, and acquisition time.
    """)

    # 2D heatmap: Pressure vs Frequency -> Time required
    P_2d = np.linspace(0.5, 3.0, 30)
    f_2d = np.linspace(0.5, 3.0, 30)
    P_grid, f_grid = np.meshgrid(P_2d, f_2d)

    # Calculate time required for each combination
    delta_sigma_2d = K_interaction * P_grid * 1e6
    V_mod_2d = V_scalp * delta_sigma_2d
    SNR_2d = V_mod_2d / V_noise_total
    N_avg_2d = (target_SNR_linear / SNR_2d)**2
    time_2d = N_avg_2d / stimulation_rate_Hz / 3600  # hours

    # Calculate MI for each combination
    MI_2d = P_grid / np.sqrt(f_grid)

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Acquisition Time (hours)", "Mechanical Index (MI)")
    )

    # Time heatmap
    fig.add_trace(
        go.Contour(
            x=P_2d, y=f_2d, z=np.log10(time_2d),
            colorscale='Viridis',
            colorbar=dict(
                title="log₁₀(hours)",
                x=0.45
            ),
            contours=dict(
                showlabels=True,
                labelfont=dict(size=10)
            )
        ),
        row=1, col=1
    )

    # MI heatmap with safety contour
    fig.add_trace(
        go.Contour(
            x=P_2d, y=f_2d, z=MI_2d,
            colorscale='RdYlGn_r',
            colorbar=dict(
                title="MI",
                x=1.05
            ),
            contours=dict(
                showlabels=True,
                start=0.5,
                end=3.0,
                size=0.5
            )
        ),
        row=1, col=2
    )

    # Add safety contour at MI = 1.9
    fig.add_trace(
        go.Contour(
            x=P_2d, y=f_2d, z=MI_2d,
            contours=dict(
                start=1.9,
                end=1.9,
                size=1,
                coloring='lines',
                showlabels=True,
                labelfont=dict(color='red', size=14)
            ),
            line=dict(color='red', width=3),
            showscale=False,
            name='MI=1.9 (limit)'
        ),
        row=1, col=2
    )

    # Mark current point on both
    for col in [1, 2]:
        fig.add_trace(
            go.Scatter(
                x=[P_acoustic_MPa],
                y=[f_ultrasound_MHz],
                mode='markers',
                marker=dict(size=15, color='red', symbol='star',
                           line=dict(color='white', width=2)),
                showlegend=False,
                name='Current'
            ),
            row=1, col=col
        )

    fig.update_xaxes(title_text="Pressure (MPa)", row=1, col=1)
    fig.update_xaxes(title_text="Pressure (MPa)", row=1, col=2)
    fig.update_yaxes(title_text="Frequency (MHz)", row=1, col=1)
    fig.update_yaxes(title_text="Frequency (MHz)", row=1, col=2)

    fig.update_layout(height=500)

    st.plotly_chart(fig, use_container_width=True)

    # Summary statistics
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
        **Current Configuration:**
        - Pressure: {P_acoustic_MPa:.1f} MPa
        - Frequency: {f_ultrasound_MHz:.1f} MHz
        - Time: {time_required_sec/3600:.1f} hr
        - MI: {MI_actual:.2f}
        """)

    with col2:
        # Find minimum time configuration (that's safe)
        safe_mask = MI_2d <= MI_limit
        if np.any(safe_mask):
            min_time_idx = np.where(safe_mask, time_2d, np.inf).argmin()
            min_P, min_f = P_grid.flat[min_time_idx], f_grid.flat[min_time_idx]
            min_time = time_2d.flat[min_time_idx]
            min_MI = MI_2d.flat[min_time_idx]

            st.markdown(f"""
            **Best Safe Configuration:**
            - Pressure: {min_P:.1f} MPa
            - Frequency: {min_f:.1f} MHz
            - Time: {min_time:.1f} hr
            - MI: {min_MI:.2f}
            """)
        else:
            st.markdown("**No safe configuration found**")

    with col3:
        # Find configuration for 1-hour acquisition
        time_target_idx = np.abs(time_2d - 1.0).argmin()
        target_P, target_f = P_grid.flat[time_target_idx], f_grid.flat[time_target_idx]
        target_MI = MI_2d.flat[time_target_idx]

        st.markdown(f"""
        **For 1-Hour Acquisition:**
        - Pressure: {target_P:.1f} MPa
        - Frequency: {target_f:.1f} MHz
        - MI: {target_MI:.2f}
        - {'⚠️ Unsafe!' if target_MI > MI_limit else '✓ Safe'}
        """)

with tab4:
    st.subheader("Assumptions & Data Sources")

    st.markdown("""
    This analysis relies on a combination of literature values, measured parameters,
    and assumptions. Understanding the source and confidence of each parameter is
    critical for interpreting the results.
    """)

    # Create a table of all parameters
    assumptions_data = {
        "Parameter": [
            "Acoustoelectric constant (K)",
            "Ultrasound frequency",
            "Ultrasound pressure",
            "Focal spot size",
            "Cortical LFP amplitude",
            "Volume conduction attenuation",
            "Electrode impedance",
            "EEG bandwidth",
            "EMG noise",
            "MI safety limit",
            "Thermal noise formula",
            "Speed of sound (tissue)",
            "Tissue density"
        ],
        "Value": [
            f"{K_percent_per_MPa:.3f} %/MPa",
            f"{f_ultrasound_MHz:.1f} MHz",
            f"{P_acoustic_MPa:.1f} MPa",
            f"{focal_spot_mm:.1f} mm",
            f"{V_source_mV:.1f} mV",
            f"{attenuation_factor}×",
            f"{R_electrode_kohm} kΩ",
            f"{bandwidth_eeg} Hz",
            f"{V_emg_uV} μV",
            "1.9",
            "√(4kTRΔf)",
            "1540 m/s",
            "1040 kg/m³"
        ],
        "Source": [
            "PMC9339687: Cardiac tissue",
            "Literature range",
            "Typical FUS",
            "PMC10644821: Brain imaging",
            "Typical cortical measurements",
            "⚠️ ESTIMATE (high uncertainty)",
            "Typical EEG systems",
            "Standard EEG",
            "Typical EMG interference",
            "FDA diagnostic limit",
            "Thermal noise theory",
            "Brain tissue literature",
            "Brain tissue literature"
        ],
        "Confidence": [
            "🟡 Medium",
            "🟢 High",
            "🟢 High",
            "🟢 High",
            "🟡 Medium",
            "🔴 Low",
            "🟢 High",
            "🟢 High",
            "🟡 Medium",
            "🟢 High",
            "🟢 High",
            "🟢 High",
            "🟢 High"
        ],
        "Impact": [
            "CRITICAL",
            "Medium",
            "CRITICAL",
            "High",
            "High",
            "CRITICAL",
            "Low",
            "Low",
            "Medium",
            "High",
            "Low",
            "Low",
            "Low"
        ]
    }

    import pandas as pd
    df = pd.DataFrame(assumptions_data)

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        ### 🔴 Critical Unknowns

        These parameters have the highest impact on feasibility but lowest confidence:

        1. **Acoustoelectric constant in human brain**
           - Current value from cardiac tissue (ex vivo)
           - May differ in living brain tissue
           - Could be 2-5× different

        2. **Volume conduction attenuation**
           - Highly geometry-dependent
           - Depends on source depth and orientation
           - Uncertainty: ±10× (factor of 5-50)

        3. **Ultrasound pressure achievable in vivo**
           - Skull aberration effects
           - Thermal constraints
           - May reduce effective pressure by 50%+
        """)

    with col2:
        st.markdown("""
        ### ✓ Well-Established Parameters

        These are well-characterized in literature:

        1. **Ultrasound physics**
           - Wavelength, focal spot, propagation
           - Safety limits (MI, intensity)
           - High confidence

        2. **Electrode thermal noise**
           - Fundamental physics (Johnson noise)
           - Verified experimentally
           - Cannot be reduced below this limit

        3. **Tissue properties**
           - Speed of sound, density, conductivity
           - Well-measured across studies
           - Variations <20%
        """)

    st.markdown("---")
    st.markdown("""
    ### 🎯 Key Insights from This Analysis

    **The fundamental challenge:** Natural neural currents (~1 μA in the focal volume)
    are ~1000× weaker than the injected currents (0.5-1 mA) used in published
    acoustoelectric brain imaging studies. This explains the dramatic difference in
    achieved SNR:

    - **Literature (current injection):** 8-15 dB SNR ✓ Feasible
    - **This proposal (passive recording):** -54 dB SNR ✗ Extremely challenging

    **What could change the conclusion:**
    1. If K is 10× larger than measured (very unlikely given multiple studies)
    2. If volume conduction is 10× better than estimated (unlikely)
    3. If you can inject current rather than record passive signals (changes application)
    4. If you average for weeks (impractical but technically possible)

    **Bottom line:** The physics is sound, but the application (passive EEG enhancement)
    appears impractical with current parameters. A different application (active current
    source localization) would be much more feasible.
    """)

# ============================================================================
# SIDEBAR - QUICK PRESETS
# ============================================================================

st.sidebar.markdown("---")
st.sidebar.subheader("🎛️ Quick Presets")

if st.sidebar.button("📚 Literature Baseline"):
    st.query_params.update(preset="literature")
    st.rerun()

if st.sidebar.button("🎯 Optimistic Scenario"):
    st.query_params.update(preset="optimistic")
    st.rerun()

if st.sidebar.button("⚠️ Conservative Estimate"):
    st.query_params.update(preset="conservative")
    st.rerun()

if st.sidebar.button("🔬 Published Study (Current Injection)"):
    st.query_params.update(preset="published")
    st.rerun()

# Handle presets
if "preset" in st.query_params:
    preset = st.query_params["preset"]
    st.sidebar.info(f"Loaded preset: {preset}")
    # Note: In practice, this would reload with different default values
    # For now, user can manually adjust after seeing the info

st.sidebar.markdown("---")
st.sidebar.markdown("""
### About
This interactive tool explores the feasibility of using focused ultrasound
to enhance EEG spatial resolution via the acoustoelectric effect.

**Created for:** ai-simulations project
**Based on:** Literature review and analytical modeling
**Last updated:** 2025-01-13
""")
