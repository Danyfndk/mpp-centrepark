import streamlit as st
import pandas as pd
import math
from io import BytesIO

# --- 1. SaaS UI STYLING ---
st.set_page_config(page_title="CP CorePlanner", page_icon="🅿️", layout="wide")

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
    </style>
    """, unsafe_allow_html=True)

# --- 2. CORE CALCULATION ENGINE (LOCKED LOGIC) ---
class SmartMPP:
    def __init__(self, umk):
        self.umk = umk
        # Konstanta Biaya Centrepark
        self.bpjs_rate, self.thr_rate, self.uuck_rate = 0.0624, 0.0833, 0.0833
        # FIXED OVERHEAD: Rp 200k (Seragam) + Rp 300k (HRIS/Training) = Rp 500k
        self.fixed_overhead = 500000 
        self.complexity = {'Hospitality': 1.15, 'Apartment': 1.10, 'Pasar Modern': 1.10, 'Ruko': 1.0, 'Rukan': 1.0}

    def get_cost(self, count, allowance_rate=0):
        if count <= 0: return 0
        gp_plus_tunj = self.umk * (1 + allowance_rate)
        variable = gp_plus_tunj * (self.bpjs_rate + self.thr_rate + self.uuck_rate)
        # Total All-in Cost per Person
        return (gp_plus_tunj + variable + self.fixed_overhead) * count

    def calculate(self, name, land, sys, g_in, g_out, c_mobil, c_motor, hours, rev):
        # 40 HOURS/WEEK FATIGUE MANAGEMENT LOGIC
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

        # Staffing Logic based on Revenue Thresholds
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
    
    # Gate & Capacity Inputs (Restored)
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        g_in = st.number_input("Gate IN", value=2, min_value=0)
        c_mobil = st.number_input("Cap Mobil", value=500, min_value=0)
    with col_g2:
        g_out = st.number_input("Gate OUT", value=2, min_value=0)
        c_motor = st.number_input("Cap Motor", value=500, min_value=0)
    
    st.divider()
    rev = st.number_input("Est. Monthly Revenue (Rp)", value=150000000, step=1000000)
    umk = st.number_input("Regional UMK (Rp)", value=5100000)
    
    process = st.button("RUN ANALYSIS")

if process:
    engine = SmartMPP(umk)
    res = engine.calculate(name, land, sys, g_in, g_out, c_mobil, c_motor, hours, rev)
    
    # KPI Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Manpower", f"{res['mpp']} Pax")
    m2.metric("Total Labor Cost", f"Rp {res['cost']:,.0f}".replace(",","."))
    
    status_color = "normal" if res['ratio'] <= 30 else "inverse"
    m3.metric("Cost Ratio", f"{res['ratio']:.2f}%", 
              delta=f"{res['ratio']-30:.2f}% Over" if res['ratio'] > 30 else f"{30-res['ratio']:.2f}% Safe", 
              delta_color=status_color)

    st.divider()
    c1, c2 = st.columns([1, 1.5])
    
    with c1:
        st.subheader("📊 Manpower Distribution")
        st.dataframe(res['details'], use_container_width=True, hide_index=True)
        
        # Export logic requires 'xlsxwriter' in requirements.txt
        output = BytesIO()
        try:
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                res['details'].to_excel(writer, index=False)
            st.download_button("📥 EXPORT TO EXCEL", data=output.getvalue(), file_name=f"MPP_{name}.xlsx")
        except:
            st.error("Error: 'xlsxwriter' not found. Please check requirements.txt")

    with c2:
        st.subheader("📈 Visual Analytics")
        st.bar_chart(res['details'].set_index("Category"), color="#004a99")
        
        if res['ratio'] > 30:
            st.error(f"**P&L GUARDRAIL BREACHED**: Labor cost is {res['ratio']:.2f}%.")
        else:
            st.success("**P&L SECURE**: Labor cost is within the 30% threshold.")
