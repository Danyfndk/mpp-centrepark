import streamlit as st
import pandas as pd
import math
from io import BytesIO

# --- 1. CONFIG & SaaS STYLING (COMPANY COLORS) ---
st.set_page_config(page_title="CP CorePlanner", page_icon="🅿️", layout="wide")

# Custom CSS for Centre Park Colors
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    
    /* Sidebar Styling (Blue Background) */
    section[data-testid="stSidebar"] {
        background-color: #004a99; /* Navy Blue dari logo */
        color: white;
    }
    section[data-testid="stSidebar"] .stMarkdown h1, 
    section[data-testid="stSidebar"] .stMarkdown h2, 
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown label,
    section[data-testid="stSidebar"] .stNumberInput label,
    section[data-testid="stSidebar"] .stSelectbox label {
        color: white !important;
    }
    section[data-testid="stSidebar"] .stMarkdown hr {
        border-top: 1px solid rgba(255,255,255,0.2) !important;
    }

    /* Metric styling with Blue Labels */
    .metric-card {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border-left: 5px solid #004a99; /* Blue accent bar */
        margin-bottom: 10px;
    }
    .metric-label { font-size: 0.85rem; color: #004a99; font-weight: 600; } /* Blue label */
    .metric-value { 
        font-size: 1.2rem; 
        color: #1e293b; 
        font-weight: 800; 
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    /* Delta metrics remain red/green for P&L readability */
    .delta-over { color: #dc2626; font-size: 0.8rem; font-weight: bold; }
    .delta-safe { color: #16a34a; font-size: 0.8rem; font-weight: bold; }
    
    /* Button Styling (Blue) */
    div.stButton > button:first-child {
        background-color: #004a99;
        color: white;
        border-radius: 8px;
        height: 3em;
        width: 100%;
        font-weight: bold;
    }
    
    /* Input border accent */
    .stNumberInput input, .stSelectbox select {
        border-color: #004a99 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CORE ENGINE (AUDITED LOGIC) ---
class SmartMPP:
    def __init__(self, umk):
        self.umk = umk
        self.bpjs_rate, self.thr_rate, self.uuck_rate = 0.0624, 0.0833, 0.0833
        # TETAP: Rp 500k Overhead (Seragam + HRIS/Training)
        self.fixed_overhead = 500000 
        self.complexity = {'Hospitality': 1.15, 'Apartment': 1.10, 'Pasar Modern': 1.10, 'Ruko': 1.0, 'Rukan': 1.0}

    def get_cost(self, count, allowance_rate=0):
        if count <= 0: return 0
        gp_plus_tunj = self.umk * (1 + allowance_rate)
        variable = gp_plus_tunj * (self.bpjs_rate + self.thr_rate + self.uuck_rate)
        return (gp_plus_tunj + variable + self.fixed_overhead) * count

    def calculate(self, sys, g_in, g_out, c_mobil, c_motor, hours, rev):
        # TETAP: STANDAR 40 JAM/MINGGU
        ff = (hours * 7) / 40 
        total_g = g_in + g_out
        total_cap = c_mobil + c_motor
        comp = self.complexity.get("Ruko", 1.0) # Fixed complex for dashboard demo
        
        # MPP Logic with Strict Rounddown
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
        
        avg_pax = cost_total / total_mpp if total_mpp > 0 else 0
        ratio = (cost_total / rev) * 100 if rev > 0 else 0
        
        return {
            "mpp": total_mpp, "ratio": ratio, "cost": cost_total, "avg_pax": avg_pax,
            "details": pd.DataFrame({
                "Category": ["Cashier", "Control Room", "Attendant", "Supervisor", "Admin", "Manager"],
                "Pax": [f_cashier, f_ctrl, f_att, f_spv, f_adm, f_cpm]
            })
        }

# --- 3. DASHBOARD UI ---
st.title("🛡️ CP CorePlanner")
st.markdown("Automated Manpower & Profitability Guardrail for **Centrepark** [cite: 2025-08-05]")

with st.sidebar:
    st.header("⚙️ Configuration")
    name = st.text_input("Project Name", "Site Centerpark")
    
    # Inputs styled inside sidebar
    sys = st.selectbox("System Type", ['Manual', 'Semi-Auto', 'Full Manless'])
    hours = st.slider("Operating Hours", 16, 24, 24)
    st.divider()
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        g_in = st.number_input("Gate IN", value=3)
        c_mobil = st.number_input("Cap Mobil", value=300)
    with col_g2:
        g_out = st.number_input("Gate OUT", value=3)
        c_motor = st.number_input("Cap Motor", value=200)
    
    st.divider()
    rev = st.number_input("Est. Monthly Revenue (Rp)", value=200000000)
    umk = st.number_input("Regional UMK (Rp)", value=5729876)
    
    process = st.button("RUN ANALYSIS", type="primary")

if process:
    eng = SmartMPP(umk)
    res = eng.calculate(sys, g_in, g_out, c_mobil, c_motor, hours, rev)
    
    # KPI Metrics (Responsive 4 Columns)
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Total MPP</div><div class='metric-value'>{res['mpp']} Pax</div></div>", unsafe_allow_html=True)
    with m2:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Total Labor Cost</div><div class='metric-value'>Rp {res['cost']:,.0f}</div></div>".replace(",","."), unsafe_allow_html=True)
    with m3:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Cost per Pax</div><div class='metric-value'>Rp {res['avg_pax']:,.0f}</div></div>".replace(",","."), unsafe_allow_html=True)
    with m4:
        diff = res['ratio'] - 30
        delta_html = f"<div class='delta-over'>▲ {diff:.2f}% Over</div>" if diff > 0 else f"<div class='delta-safe'>▼ {abs(diff):.2f}% Safe</div>"
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Cost Ratio</div><div class='metric-value'>{res['ratio']:.2f}%</div>{delta_html}</div>", unsafe_allow_html=True)

    st.divider()
    
    c1, c2 = st.columns([1, 1.5])
    with c1:
        st.subheader("📊 Manpower Distribution")
        st.dataframe(res['details'], use_container_width=True, hide_index=True)
        # Export logic
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            res['details'].to_excel(writer, index=False)
        st.download_button("📥 EXPORT TO EXCEL", data=output.getvalue(), file_name=f"MPP_{name}.xlsx", use_container_width=True)

    with c2:
        st.subheader("📈 Visual Analytics")
        st.bar_chart(res['details'].set_index("Category"), color="#004a99") # Navy Blue charts
        
        if res['ratio'] > 30:
            st.error(f"**P&L GUARDRAIL BREACHED**: Labor cost is {res['ratio']:.2f}% (P&L Target: 30%)")
        else:
            st.success("**P&L SECURE**: Labor cost is within the 30% threshold.")
