import streamlit as st
import pandas as pd
import math
from io import BytesIO

# --- 1. CONFIG & SaaS STYLING ---
st.set_page_config(page_title="CP CorePlanner", page_icon="🅿️", layout="wide")

# Custom CSS for SaaS Look
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #eee;
    }
    div.stButton > button:first-child {
        background-color: #004a99;
        color: white;
        border-radius: 8px;
        height: 3em;
        width: 100%;
        font-weight: bold;
    }
    .reportview-container .main .block-container { padding-top: 2rem; }
    h1 { color: #1e293b; font-weight: 800; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CORE ENGINE ---
class SmartMPP:
    def __init__(self, umk):
        self.umk = umk
        self.complexity = {'Hospitality': 1.15, 'Apartment': 1.10, 'Pasar Modern': 1.10, 'Ruko': 1.0, 'Rukan': 1.0}
        self.bpjs_rate, self.thr_rate, self.uuck_rate = 0.0624, 0.0833, 0.0833
        self.fixed_overhead = 200000 + 300000 # Seragam + HRIS/Training

    def get_cost(self, count, allowance_rate=0):
        if count <= 0: return 0
        gp_plus_tunj = self.umk * (1 + allowance_rate)
        variable = gp_plus_tunj * (self.bpjs_rate + self.thr_rate + self.uuck_rate)
        return (gp_plus_tunj + variable + self.fixed_overhead) * count

    def calculate(self, name, land, sys, g_in, g_out, c_mobil, c_motor, hours, rev):
        ff = (hours * 7) / 40 # 40h/week limit
        total_g = g_in + g_out
        total_cap = c_mobil + c_motor
        comp = self.complexity.get(land, 1.0)
        
        # Non-Staff Logic
        cashier, ctrl, att = 0, 0, 0
        if sys == 'Manual':
            cashier = total_g * ff
            att = (math.ceil(total_cap / 500)) * ff * comp
        elif sys == 'Semi-Auto':
            ctrl = 1 * ff
            att = (g_out + math.ceil(total_cap / 500)) * ff * comp
        else:
            ctrl = 1 * ff
            att = (math.ceil(total_cap / 1000)) * ff

        f_cashier, f_ctrl, f_att = math.floor(cashier), math.floor(ctrl), math.floor(att)

        # Staffing Logic
        if rev >= 500000000: spv, adm, cpm = 3, 1, 1
        elif rev >= 150000000: spv, adm, cpm = 1, 0, 0
        else: spv, adm, cpm = 0, 0, 0
            
        f_spv, f_adm, f_cpm = math.floor(spv), math.floor(adm), math.floor(cpm)
        total_mpp = f_cashier + f_ctrl + f_att + f_spv + f_adm + f_cpm
        
        cost_total = self.get_cost(f_cashier+f_ctrl+f_att, 0) + \
                     self.get_cost(f_adm, 0.15) + self.get_cost(f_spv, 0.20) + \
                     self.get_cost(f_cpm, 0.25)
        
        ratio = (cost_total / rev) * 100 if rev > 0 else 0
        
        return {
            "mpp": total_mpp, "ratio": ratio, "cost": cost_total,
            "details": pd.DataFrame({
                "Category": ["Cashier", "Control Room", "Attendant", "Supervisor", "Admin", "Manager"],
                "Count": [f_cashier, f_ctrl, f_att, f_spv, f_adm, f_cpm]
            }),
            "summary": pd.DataFrame({
                "Parameter": ["Project", "System", "Total MPP", "Cost Ratio"],
                "Value": [name, sys, total_mpp, f"{ratio:.2f}%"]
            })
        }

# --- 3. DASHBOARD UI ---
st.title("🛡️ CP CorePlanner")
st.markdown("Automated Manpower & Profitability Guardrail for **Centrepark**")

# Sidebar for Inputs
with st.sidebar:
    st.header("⚙️ Project Configuration")
    name = st.text_input("Project Name", "Site Centerpark")
    land = st.selectbox("Landlord Type", ['Hospitality', 'Apartment', 'Pasar Modern', 'Ruko', 'Rukan'])
    sys = st.selectbox("System Type", ['Manual', 'Semi-Auto', 'Full Manless'])
    hours = st.slider("Operating Hours", 16, 24, 24)
    st.divider()
    rev = st.number_input("Est. Monthly Revenue (Rp)", value=150000000, step=1000000)
    umk = st.number_input("Regional UMK (Rp)", value=5100000)
    
    process = st.button("RUN ANALYSIS")

if process:
    engine = SmartMPP(umk)
    res = engine.calculate(name, land, sys, g_in=2, g_out=2, c_mobil=500, c_motor=500, hours=hours, rev=rev)
    
    # KPI Metrics Row
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Manpower", f"{res['mpp']} Pax")
    m2.metric("Total Labor Cost", f"Rp {res['cost']:,.0f}".replace(",","."))
    
    # Status Logic for Metric 3
    status = "Normal" if res['ratio'] <= 30 else "Critical"
    m3.metric("Cost Ratio", f"{res['ratio']:.2f}%", delta=f"{res['ratio']-30:.2f}%" if res['ratio']>30 else None, delta_color="inverse")

    st.divider()

    # Main Content Area
    c1, c2 = st.columns([1, 1.5])
    
    with c1:
        st.subheader("📊 Manpower Distribution")
        st.dataframe(res['details'], use_container_width=True, hide_index=True)
        
        # Export SaaS Style
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            res['details'].to_excel(writer, index=False)
        st.download_button("📥 EXPORT TO EXCEL", data=output.getvalue(), file_name=f"MPP_{name}.xlsx")

    with c2:
        st.subheader("📈 Visual Analytics")
        st.bar_chart(res['details'].set_index("Category"), color="#004a99")
        
        # Warning Card
        if res['ratio'] > 30:
            st.error(f"**P&L GUARDRAIL BREACHED**: Labor cost is {res['ratio']:.2f}%. Reduce manpower or switch to Manless.")
        else:
            st.success("**P&L SECURE**: Labor cost is within the 30% profitability threshold.")

else:
    st.info("👈 Please configure the project details in the sidebar and click 'Run Analysis'.")
