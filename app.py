import streamlit as st
import pandas as pd
import math
from io import BytesIO

# --- 1. CONFIG & RESPONSIVE SaaS STYLING ---
st.set_page_config(page_title="CP CorePlanner", page_icon="🅿️", layout="wide")

st.markdown("""
    <style>
    /* Responsive Container */
    .main { background-color: #f8f9fa; }
    
    /* Metrics Styling - Anti-Cutoff */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        overflow-wrap: break-word;
        white-space: normal;
    }
    
    /* Card Look for SaaS */
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border: 1px solid #eef2f6;
    }
    
    /* Button Professional Look */
    div.stButton > button:first-child {
        background-color: #004a99;
        color: white;
        border-radius: 8px;
        width: 100%;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CORE ENGINE (LOCKED LOGIC CENTREPARK) ---
class SmartMPP:
    def __init__(self, umk):
        self.umk = umk
        self.bpjs_rate, self.thr_rate, self.uuck_rate = 0.0624, 0.0833, 0.0833
        # TETAP: Rp 200k (Seragam) + Rp 300k (HRIS/Training)
        self.fixed_overhead = 500000 
        self.complexity = {'Hospitality': 1.15, 'Apartment': 1.10, 'Pasar Modern': 1.10, 'Ruko': 1.0, 'Rukan': 1.0}

    def get_cost(self, count, allowance_rate=0):
        if count <= 0: return 0
        gp_plus_tunj = self.umk * (1 + allowance_rate)
        variable = gp_plus_tunj * (self.bpjs_rate + self.thr_rate + self.uuck_rate)
        return (gp_plus_tunj + variable + self.fixed_overhead) * count

    def calculate(self, name, land, sys, g_in, g_out, c_mobil, c_motor, hours, rev):
        # TETAP: STANDAR 40 JAM/MINGGU
        ff = (hours * 7) / 40 
        total_g = g_in + g_out
        total_cap = c_mobil + c_motor
        comp = self.complexity.get(land, 1.0)
        
        # Non-Staff Logic with Strict Rounddown
        cashier, ctrl, att = 0, 0, 0
        if sys == 'Manual':
            cashier = total_g * ff
            att = (math.ceil(total_cap / 500)) * ff * comp
        elif sys == 'Semi-Auto':
            ctrl = 1 * ff
            att = (g_out + math.ceil(total_cap / 500)) * ff * comp
        else: # Full Manless
            ctrl = 1 * ff
            att = (math.ceil(total_cap / 1000)) * ff

        f_cashier, f_ctrl, f_att = math.floor(cashier), math.floor(ctrl), math.floor(att)

        # Staffing Logic based on Revenue
        if rev >= 500000000: spv, adm, cpm = 3, 1, 1
        elif rev >= 150000000: spv, adm, cpm = 1, 0, 0
        else: spv, adm, cpm = 0, 0, 0
            
        f_spv, f_adm, f_cpm = math.floor(spv), math.floor(adm), math.floor(cpm)
        total_mpp = f_cashier + f_ctrl + f_att + f_spv + f_adm + f_cpm
        
        cost_total = self.get_cost(f_cashier+f_ctrl+f_att, 0) + \
                     self.get_cost(f_adm, 0.15) + self.get_cost(f_spv, 0.20) + \
                     self.get_cost(f_cpm, 0.25)
        
        avg_cost_pax = cost_total / total_mpp if total_mpp > 0 else 0
        ratio = (cost_total / rev) * 100 if rev > 0 else 0
        
        return {
            "mpp": total_mpp, "ratio": ratio, "cost": cost_total, "avg_pax": avg_cost_pax,
            "details": pd.DataFrame({
                "Category": ["Cashier", "Control Room", "Attendant", "Supervisor", "Admin", "Manager"],
                "Pax": [f_cashier, f_ctrl, f_att, f_spv, f_adm, f_cpm]
            })
        }

# --- 3. DASHBOARD UI ---
st.title("🛡️ CP CorePlanner")
st.markdown("Automated Manpower & Profitability Guardrail for **Centrepark**")

with st.sidebar:
    st.header("⚙️ Project Configuration")
    name = st.text_input("Project Name", "Site Centerpark")
    land = st.selectbox("Landlord Type", ['Hospitality', 'Apartment', 'Pasar Modern', 'Ruko', 'Rukan'])
    sys = st.selectbox("System Type", ['Manual', 'Semi-Auto', 'Full Manless'])
    hours = st.slider("Operating Hours", 16, 24, 24)
    st.divider()
    
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        g_in = st.number_input("Gate IN", value=2)
        c_mobil = st.number_input("Cap Mobil", value=500)
    with col_g2:
        g_out = st.number_input("Gate OUT", value=2)
        c_motor = st.number_input("Cap Motor", value=500)
    
    st.divider()
    rev = st.number_input("Monthly Revenue (Rp)", value=150000000)
    umk = st.number_input("Regional UMK (Rp)", value=5100000)
    process = st.button("RUN ANALYSIS")

if process:
    engine = SmartMPP(umk)
    res = engine.calculate(name, land, sys, g_in, g_out, c_mobil, c_motor, hours, rev)
    
    # KPI Metrics Row (Responsive 4 Columns)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total MPP", f"{res['mpp']} Pax")
    m2.metric("Total Labor Cost", f"Rp {res['cost']:,.0f}".replace(",","."))
    m3.metric("Cost per Pax", f"Rp {res['avg_pax']:,.0f}".replace(",","."))
    
    # Cost Ratio Delta Logic
    diff = res['ratio'] - 30
    m4.metric("Cost Ratio", f"{res['ratio']:.2f}%", 
              delta=f"{diff:.2f}% Over" if diff > 0 else f"{abs(diff):.2f}% Safe", 
              delta_color="inverse" if diff > 0 else "normal")

    st.divider()
    
    # Layout Results
    c1, c2 = st.columns([1, 1.5])
    with c1:
        st.subheader("📊 MPP Distribution")
        st.dataframe(res['details'], use_container_width=True, hide_index=True)
        
        output = BytesIO()
        try:
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                res['details'].to_excel(writer, index=False)
            st.download_button("📥 EXPORT EXCEL", data=output.getvalue(), file_name=f"MPP_{name}.xlsx")
        except:
            st.error("Error: 'xlsxwriter' not found in requirements.txt")

    with c2:
        st.subheader("📈 Visual Analytics")
        st.bar_chart(res['details'].set_index("Category"), color="#004a99")
        
        if res['ratio'] > 30:
            st.error(f"**P&L GUARDRAIL BREACHED**: Labor cost is {res['ratio']:.2f}% (Limit: 30%)")
        else:
            st.success(f"**P&L SECURE**: Labor cost is {res['ratio']:.2f}%")
