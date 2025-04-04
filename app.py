import numpy as np
import matplotlib.pyplot as plt
import streamlit as st

# Constants with hematocrit factors
METHODS = {
    'Whole Blood': {
        'efficiency': 0.25,
        'volume_factor': 1.0,
        'hct_impact': 0.2,  # 20% hematocrit sensitivity
        'rbc_contam': 50.0,  # RBC contamination (×10⁹ per L)
        'cd3_estimate': lambda tlc, lymph: 60 + 10*(tlc/15) + 5*(lymph/50),  # CD3% estimation function
        'params': {}
    },
    'Haemonetics': {
        'efficiency': 0.85,
        'volume_factor': 0.3,
        'hct_impact': 0.6,  # 60% hematocrit sensitivity
        'rbc_contam': 15.0,  # Higher RBC contamination
        'cd3_estimate': lambda tlc, lymph: 70 + 15*(tlc/15) + 10*(lymph/50),  # Better CD3+ selection
        'params': {
            'flow_rate': (40, 60),
            'acd_ratio': (11, 13),
            'plasma_removal': (5, 15)
        }
    },
    'Spectra Optia': {
        'efficiency': 0.95,
        'volume_factor': 0.2,
        'hct_impact': 0.4,  # 40% hematocrit sensitivity
        'rbc_contam': 10.0,  # Lower RBC contamination
        'cd3_estimate': lambda tlc, lymph: 75 + 20*(tlc/15) + 15*(lymph/50),  # Best CD3+ selection
        'params': {
            'flow_rate': (50, 70),
            'acd_ratio': (12, 14),
            'plasma_removal': (5, 10)
        }
    }
}

RECOMMENDED_DOSES = {
    'Matched Sibling': 10,  # 1×10⁷ CD3+/kg
    'Haploidentical': 1     # 1×10⁶ CD3+/kg (1 log lower)
}

def calculate_dli(dose, recipient_weight, donor_tlc, lymph_percent, donor_hct, method):
    """Calculate required collection volume and optimal parameters for DLI with hematocrit adjustment"""
    method_data = METHODS[method]
    
    # Estimate CD3% based on method, TLC and lymphocyte %
    cd3_percent = method_data['cd3_estimate'](donor_tlc, lymph_percent)
    cd3_percent = min(max(cd3_percent, 50), 95)  # Keep within reasonable bounds
    
    required_cd3 = dose * recipient_weight
    cd3_conc = donor_tlc * 1e3 * (lymph_percent/100) * (cd3_percent/100)
    
    # Hematocrit efficiency correction (normalized to 40% Hct)
    hct_efficiency = 1 - method_data['hct_impact'] * (donor_hct - 40)/40
    
    # Adjusted volume calculation with Hct impact
    volume = (required_cd3 / (cd3_conc * method_data['efficiency'] * hct_efficiency)) * method_data['volume_factor'] / 1e3
    
    # RBC contamination calculation
    rbc_contamination = method_data['rbc_contam'] * (donor_hct/40) * (volume/0.5)  # Normalized to 0.5L
    
    params = {}
    if method != 'Whole Blood':
        # Adjust flow rate based on Hct
        base_flow = METHODS[method]['params']['flow_rate'][0] + (METHODS[method]['params']['flow_rate'][1]-METHODS[method]['params']['flow_rate'][0])*(lymph_percent/100)
        flow_rate = base_flow * (1 - 0.2*(donor_hct-40)/40)  # Reduce flow for high Hct
        flow_rate = max(METHODS[method]['params']['flow_rate'][0], min(METHODS[method]['params']['flow_rate'][1], flow_rate))
        
        params = {
            'Flow Rate': f"{flow_rate:.1f} mL/min",
            'ACD Ratio': f"1:{int((METHODS[method]['params']['acd_ratio'][0] + METHODS[method]['params']['acd_ratio'][1])/2 + (1 if donor_hct > 45 else 0))}",
            'Plasma Removal': f"{METHODS[method]['params']['plasma_removal'][0] + (5 if donor_hct > 45 else 0)} mL",
            'Hct Efficiency': f"{hct_efficiency:.2f}",
            'Estimated CD3%': f"{cd3_percent:.1f}%"
        }
    return volume, rbc_contamination, params, cd3_percent

def main():
    st.set_page_config(page_title="DLI Calculator", layout="wide")
    st.title("Donor Lymphocyte Infusion (DLI) Calculator")
    
    # Display recommended doses information at the top
    st.markdown("""
    ### Recommended Doses:
    - **Matched Sibling Donor:** 10 ×10⁶ CD3+ cells/kg (1×10⁷ cells/kg)
    - **Haploidentical Donor:** 1 ×10⁶ CD3+ cells/kg (1 log lower)
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        donor_type = st.selectbox("Donor Type", list(RECOMMENDED_DOSES.keys()))
        # Show recommended dose next to the slider
        recommended_dose = RECOMMENDED_DOSES[donor_type]
        dose = st.slider(
            f"Dose (×10⁶ CD3+ cells/kg) [Recommended: {recommended_dose}]", 
            0.1, 20.0, float(recommended_dose), 0.1
        )
        recipient_weight = st.number_input("Recipient Weight (kg)", min_value=30, max_value=120, value=70)
        method = st.selectbox("Collection Method", list(METHODS.keys()))
        
    with col2:
        donor_tlc = st.slider("Donor TLC (×10³/μL)", min_value=2.0, max_value=30.0, value=8.0, step=0.5)
        lymph_percent = st.slider("Lymphocyte %", min_value=10, max_value=90, value=30)
        donor_hct = st.slider("Donor Hematocrit (%)", min_value=30.0, max_value=60.0, value=40.0, step=0.1,
                            help="Critical for collection efficiency and RBC contamination")
    
    # Calculate
    dose_cells = dose * 1e6
    volume, rbc_contamination, params, cd3_percent = calculate_dli(
        dose_cells, recipient_weight, donor_tlc, lymph_percent, donor_hct, method
    )
    
    # Display results with highlighted recommended dose
    st.subheader("Results")
    st.write(f"**Donor Type:** {donor_type} [Recommended dose: {RECOMMENDED_DOSES[donor_type]} ×10⁶ CD3+ cells/kg]")
    st.write(f"**Selected Dose:** {dose} ×10⁶ CD3+ cells/kg")
    st.write(f"**Required CD3+ cells:** {dose * recipient_weight:.1f} ×10⁶ cells")
    st.write(f"**Estimated CD3+ %:** {cd3_percent:.1f}%")
    st.write(f"**Effective CD3+ concentration:** {(donor_tlc * 1e3 * (lymph_percent/100) * (cd3_percent/100)):.1f} cells/μL")
    st.write(f"**Required volume:** {volume:.1f} mL")
    st.write(f"**Estimated RBC contamination:** {rbc_contamination:.1f} ×10⁹")
    
    if method != 'Whole Blood':
        st.subheader("Recommended Parameters")
        for param, value in params.items():
            st.write(f"**{param}:** {value}")
        
        # Show HCT warning if needed
        if donor_hct > 45:
            st.warning(f"High donor hematocrit ({donor_hct}%) - consider:")
            st.markdown("""
            - Reducing flow rate by 10-20%
            - Increasing ACD ratio by 1-2 points
            - Increasing plasma removal by 5-10 mL
            """)
    
    # Plot with recommended dose marker
    st.subheader("Dose-Volume Relationship")
    fig, ax1 = plt.subplots(figsize=(10, 6))
    
    # Generate points for the curve
    doses = np.linspace(0.5e6, 2e7, 50)
    volumes = []
    for d in doses:
        v, _, _, _ = calculate_dli(d, recipient_weight, donor_tlc, lymph_percent, donor_hct, method)
        volumes.append(v)
    
    # Main volume curve
    ax1.plot(doses/1e6, volumes, 'b-', linewidth=2, label='Volume Curve')
    
    # Current dose marker
    ax1.scatter([dose], [volume], color='red', s=200, label='Selected Dose')
    
    # Recommended dose marker
    recommended_vol, _, _, _ = calculate_dli(
        RECOMMENDED_DOSES[donor_type] * 1e6,
        recipient_weight,
        donor_tlc,
        lymph_percent,
        donor_hct,
        method
    )
    ax1.scatter([RECOMMENDED_DOSES[donor_type]], [recommended_vol], 
                color='green', s=200, marker='D', label='Recommended Dose')
    
    ax1.set_xlabel('DLI Dose (×10⁶ CD3+ cells/kg)')
    ax1.set_ylabel('Required Volume (mL)', color='b')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Secondary axis for total cells
    ax2 = ax1.twinx()
    ax2.plot(doses/1e6, np.array(doses)*recipient_weight/1e8, 'g--', alpha=0.5)
    ax2.set_ylabel('Total CD3+ Cells (×10⁸)', color='g')
    
    st.pyplot(fig)

if __name__ == "__main__":
    main()
