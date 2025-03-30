import numpy as np
import matplotlib.pyplot as plt
import streamlit as st

# Constants
METHODS = {
    'Whole Blood': {
        'efficiency': 0.25,
        'volume_factor': 1.0,
        'params': {}
    },
    'Haemonetics': {
        'efficiency': 0.85,
        'volume_factor': 0.3,
        'params': {
            'interface_position': (0.5, 1.5),
            'flow_rate': (40, 60),
            'acd_ratio': (11, 13),
            'plasma_removal': (5, 15)
        }
    },
    'Spectra Optia': {
        'efficiency': 0.95,
        'volume_factor': 0.2,
        'params': {
            'interface_position': (0.5, 1.5),
            'flow_rate': (50, 70),
            'acd_ratio': (12, 14),
            'plasma_removal': (5, 10)
        }
    }
}

RECOMMENDED_DOSES = {
    'Matched Sibling': 10,
    'Haploidentical': 1
}

def calculate_dli(dose, recipient_weight, donor_tlc, lymph_percent, cd3_percent, method):
    required_cd3 = dose * recipient_weight
    cd3_conc = donor_tlc * 1e3 * (lymph_percent/100) * (cd3_percent/100)
    method_data = METHODS[method]
    volume = (required_cd3 / (cd3_conc * method_data['efficiency'])) * method_data['volume_factor'] / 1e3
    
    params = {}
    if method != 'Whole Blood':
        interface_pos = 1.0 - 0.5*(donor_tlc/15) + 0.25*(lymph_percent/50)
        interface_pos = max(METHODS[method]['params']['interface_position'][0], 
                          min(METHODS[method]['params']['interface_position'][1], interface_pos))
        params = {
            'Interface Position': f"{interface_pos:.2f}",
            'Flow Rate': f"{METHODS[method]['params']['flow_rate'][0] + (METHODS[method]['params']['flow_rate'][1]-METHODS[method]['params']['flow_rate'][0])*(lymph_percent/100):.1f} mL/min",
            'ACD Ratio': f"1:{int((METHODS[method]['params']['acd_ratio'][0] + METHODS[method]['params']['acd_ratio'][1])/2)}",
            'Plasma Removal': f"{METHODS[method]['params']['plasma_removal'][0]} mL"
        }
    return volume, params

def main():
    st.set_page_config(page_title="DLI Calculator", layout="wide")
    st.title("Donor Lymphocyte Infusion (DLI) Calculator")
    
    col1, col2 = st.columns(2)
    
    with col1:
        donor_type = st.selectbox("Donor Type", ['Matched Sibling', 'Haploidentical'])
        dose = st.slider("Dose (×10⁶ CD3+ cells/kg)", 0.1, 20.0, float(RECOMMENDED_DOSES[donor_type]), 0.1)
        recipient_weight = st.slider("Recipient Weight (kg)", 30, 120, 70)
        method = st.selectbox("Collection Method", list(METHODS.keys()))
        
    with col2:
        donor_tlc = st.slider("Donor TLC (×10³/μL)", 2.0, 30.0, 8.0, 0.5)
        lymph_percent = st.slider("Lymphocyte %", 10, 90, 30)
        cd3_percent = st.slider("CD3+ %", 10, 100, 70)
    
    # Calculate
    dose_cells = dose * 1e6
    volume, params = calculate_dli(dose_cells, recipient_weight, donor_tlc, lymph_percent, cd3_percent, method)
    
    # Display results
    st.subheader("Results")
    st.write(f"**Required CD3+ cells:** {dose * recipient_weight:.1f} ×10⁶ cells")
    st.write(f"**Effective CD3+ concentration:** {(donor_tlc * 1e3 * (lymph_percent/100) * (cd3_percent/100):.1f} cells/μL")
    st.write(f"**Required volume:** {volume:.1f} mL")
    
    if method != 'Whole Blood':
        st.subheader("Recommended Parameters")
        for param, value in params.items():
            st.write(f"**{param}:** {value}")
    
    # Plot
    doses = np.linspace(0.5e6, 2e7, 50)
    volumes = [calculate_dli(d, recipient_weight, donor_tlc, lymph_percent, cd3_percent, method)[0] 
               for d in doses]
    
    fig, ax1 = plt.subplots(figsize=(10, 6))
    ax1.plot(doses/1e6, volumes, 'b-', linewidth=2, label='Volume Curve')
    ax1.scatter([dose], [volume], color='red', s=200, label=f'Current Dose')
    ax1.set_xlabel('DLI Dose (×10⁶ CD3+ cells/kg)')
    ax1.set_ylabel('Required Volume (mL)', color='b')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    ax2 = ax1.twinx()
    ax2.plot(doses/1e6, np.array(doses)*recipient_weight/1e8, 'g--', alpha=0.5)
    ax2.set_ylabel('Total CD3+ Cells (×10⁸)', color='g')
    
    st.pyplot(fig)

if __name__ == "__main__":
    main()
