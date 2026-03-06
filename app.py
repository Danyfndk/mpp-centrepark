import streamlit as st
import pandas as pd
import math
from io import BytesIO

# --- 1. SaaS UI STYLING (ULTRA-RESPONSIVE) ---
st.set_page_config(page_title="CP CorePlanner", page_icon="🅿️", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    /* SaaS Card Metrics */
    .metric-card {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border-left: 5px solid #004a99;
        margin-bottom: 10px;
    }
    .metric-label { font-size: 0.85rem; color: #64748b; font-weight: 600; }
    .metric-value { 
        font-size: 1.2rem; 
        color: #1e293b; 
        font-weight: 800; 
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .delta-over { color: #dc2626; font-size: 0.8rem; font-weight: bold; }
    .delta-safe { color: #16a34a; font-size: 0.8rem; font-weight: bold; }
    
    /* Responsive Chart Container */
    .chart-container { background: white; padding: 20px; border-radius: 12px; border: 1px solid #eef2f6; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CORE ENGINE (AUDITED LOGIC) ---
class SmartMPP:
    def __init__(self, umk):
        self.umk = umk
        self.bpjs_rate, self.thr_rate, self.uuck_rate = 0.0624, 0.0833, 0.0833
        # TETAP: Rp 500k (Seragam 200k + HRIS/Training 300k)
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
        
        # MPP Logic (Strict Rounddown)
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
st.markdown("Automated Manpower & Profitability Guardrail for **Centrepark**")

with st.sidebar:
    st.header("⚙️ Configuration")
    name = st.text_input("Project", "Site Centerpark")
    land = st.selectbox("Landlord", ['Hospitality', 'Apartment', 'Pasar Modern', 'Ruko', 'Rukan'])
    sys = st.selectbox("System", ['Manual', 'Semi-Auto', 'Full Manless'])
    hours = st.slider("Ops Hours", 16, 24, 24)
    st.divider()
    c_g1, c_g2 = st.columns(2)
    with c_g1:
        g_in = st.number_input("Gate IN", value=3)
        c_mobil = st.number_input("Cap Mobil", value=300)
    with c_g2:
        g_out = st.number_input("Gate OUT", value=3)
        c_motor = st.number_input("Cap Motor", value=200)
    st.divider()
    rev = st.number_input("Monthly Revenue (Rp)", value=200000000)
    umk = st.number_input("Regional UMK (Rp)", value=5729876)
    process = st.button("RUN ANALYSIS", type="primary", use_container_width=True)

if process:
    eng = SmartMPP(umk)
    res = eng.calculate(name, land, sys, g_in, g_out, c_mobil, c_motor, hours, rev)
    
    # Custom HTML Metric Cards (Anti-Cutoff)
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Total MPP</div><div class='metric-value'>{res['mpp']} Pax</div></div>", unsafe_allow_html=True)
    with m2:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Total Cost</div><div class='metric-value'>Rp {res['cost']:,.0f}</div></div>".replace(",","."), unsafe_allow_html=True)
    with m3:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Cost per Pax</div><div class='metric-value'>Rp {res['avg_pax']:,.0f}</div></div>".replace(",","."), unsafe_allow_html=True)
    with m4:
        diff = res['ratio'] - 30
        delta_html = f"<div class='delta-over'>▲ {diff:.2f}% Over</div>" if diff > 0 else f"<div class='delta-safe'>▼ {abs(diff):.2f}% Safe</div>"
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Cost Ratio</div><div class='metric-value'>{res['ratio']:.2f}%</div>{delta_html}</div>", unsafe_allow_html=True)

    st.divider()
    
    c1, c2 = st.columns([1, 1.5])
    with c1:
        st.subheader("📊 MPP Distribution")
        st.dataframe(res['details'], use_container_width=True, hide_index=True)
        # Export
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            res['details'].to_excel(writer, index=False)
        st.download_button("📥 EXPORT EXCEL", data=output.getvalue(), file_name=f"MPP_{name}.xlsx", use_container_width=True)

    with c2:
        st.subheader("📈 Visual Analytics")
        # Fixed Chart Logic to avoid flickering
        chart_df = res['details'].copy()
        st.bar_chart(chart_df.set_index("Category"), color="#004a99")
        
        if res['ratio'] > 30:
            st.error(f"**P&L GUARDRAIL BREACHED**: Labor cost is {res['ratio']:.2f}% (Target: 30%)")
        else:
            st.success(f"**P&L SECURE**: Labor cost is within threshold.")
