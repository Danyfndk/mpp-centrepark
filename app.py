import streamlit as st
import pandas as pd
import math
from io import BytesIO

# --- HELPER FUNCTIONS ---
def format_idr(amount):
    return f"Rp {amount:,.0f}".replace(",", ".")

def get_shift_distribution(shift_mpp):
    if shift_mpp == 0: return "0 Pax"
    base = shift_mpp // 4
    rem = shift_mpp % 4
    return f"{base} Pax" if rem == 0 else f"{base} - {base+1} Pax"

# --- 1. SaaS UI STYLING (PREMIUM) ---
st.set_page_config(page_title="CP CorePlanner", page_icon="🅿️", layout="wide")

st.markdown("""<style>
.main { background-color: #f4f7fa; font-family: 'Segoe UI', sans-serif; }
section[data-testid="stSidebar"] { background-color: #004a99 !important; }
section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 { color: #ffffff !important; }
section[data-testid="stSidebar"] input { color: #1e293b !important; background-color: #ffffff !important; border-radius: 6px !important; }
section[data-testid="stSidebar"] div[data-baseweb="select"] * { color: #1e293b !important; }

.header-card-a { background-color: #ffffff; padding: 15px 20px; border-radius: 12px; border-top: 6px solid #004a99; box-shadow: 0 4px 10px rgba(0,74,153,0.1); margin-bottom: 15px; }
.header-card-b { background-color: #ffffff; padding: 15px 20px; border-radius: 12px; border-top: 6px solid #d97706; box-shadow: 0 4px 10px rgba(217,119,6,0.1); margin-bottom: 15px; }
.header-title { margin: 0; color: #1e293b; font-weight: 800; font-size: 1.3rem; }

.result-card { background-color: #ffffff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-top: 5px; margin-bottom: 20px; }
.metric-row { display: flex; gap: 15px; margin-bottom: 15px; }
.metric-card { background-color: #f8fafc; padding: 15px; border-radius: 10px; flex: 1; border: 1px solid #e2e8f0; }
.metric-card-a { border-left: 5px solid #004a99; } .metric-card-b { border-left: 5px solid #d97706; }
.metric-label { font-size: 0.8rem; color: #64748b; font-weight: 700; text-transform: uppercase; }
.metric-value { font-size: 1.3rem; color: #1e293b; font-weight: 900; }

.breakdown-bar { display: flex; background-color: #f1f5f9; padding: 12px 10px; border-radius: 10px; margin-bottom: 15px; justify-content: space-between; }
.bd-item { display: flex; flex-direction: column; text-align: center; flex: 1; }
.bd-border { border-left: 1px solid #cbd5e1; border-right: 1px solid #cbd5e1; }
.bd-label { font-size: 0.75rem; color: #64748b; font-weight: 700; }
.bd-val { font-size: 1rem; color: #0f172a; font-weight: 800; }

.comp-box { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; font-size: 0.82rem; }
.comp-title { font-weight: 800; color: #1e293b; margin-bottom: 8px; border-bottom: 1px solid #e2e8f0; text-transform: uppercase; font-size: 0.72rem;}
.comp-row { display: flex; justify-content: space-between; margin-bottom: 4px; color: #475569; }
.comp-val { font-weight: 700; color: #0f172a; }

.total-cost-box { padding: 15px; border-radius: 10px; text-align: center; }
.total-cost-a { background-color: #f0f7ff; border: 2px dashed #93c5fd; }
.total-cost-b { background-color: #fffbeb; border: 2px dashed #fcd34d; }

.info-box-a { background-color: #e0f2fe; padding: 15px; border-radius: 8px; border-left: 5px solid #004a99; margin-bottom: 10px; color: #0f172a;}
.info-box-b { background-color: #fef3c7; padding: 15px; border-radius: 8px; border-left: 5px solid #d97706; margin-bottom: 20px; color: #0f172a;}

div.stDownloadButton > button { background-color: #004a99 !important; color: white !important; border-radius: 8px !important; font-weight: 700 !important; width: 100%; border: none !important; }
</style>""", unsafe_allow_html=True)

# --- 2. CORE COMPLIANCE ENGINE ---
class ComplianceEngine:
    def __init__(self, umk, fixed_overhead, bpjs_rate, thr_rate, uuck_rate):
        self.umk = umk
        self.fixed_overhead = fixed_overhead
        self.benefit_rate = bpjs_rate + thr_rate + uuck_rate

    def get_individual_cost(self, allowance_rate=0):
        salary_and_allowance = self.umk + (self.umk * allowance_rate)
        benefit = self.umk * self.benefit_rate
        return salary_and_allowance + benefit + self.fixed_overhead

    def calculate(self, sys, g_in, g_out, c_mob, c_mot, hours, rev, mgt_fee_rate=0.0):
        ff = (hours * 7) / 40
        
        # Non-Staff Logic
        if sys == 'Manual':
            att_base = (c_mob / 250) + (c_mot / 500)
            cashier = math.floor((g_in + g_out) * ff)
        elif sys == 'Semi-Auto':
            att_base = (c_mob / 400) + (c_mot / 800)
            cashier = math.floor(g_out * ff)
        else:
            att_base = (c_mob / 600) + (c_mot / 1200)
            cashier = 0
            
        att = math.floor(math.ceil(att_base) * ff) if att_base > 0 else 0
        ctrl = math.floor(1 * ff) if sys != 'Manual' else 0

        # Staff & IT Logic
        spv, adm, cpm = (3, 1, 1) if rev >= 500000000 else (1, 1, 0) if rev >= 150000000 else (0, 1, 0)
        it_tech = 1 if (sys != 'Manual' and rev >= 150000000) else 0 

        # Allowance Dynamic logic
        adm_all, spv_all, cpm_all, it_all = 0.10, 0.20, 0.30, 0.10
        if cpm > 0: pass
        elif spv > 0: spv_all = 0.30
        elif adm > 0: adm_all = 0.30

        shift_mpp = cashier + ctrl + att
        office_mpp = spv + adm + cpm + it_tech
        
        total_actual_cost = (shift_mpp * self.get_individual_cost(0)) + \
                            (adm * self.get_individual_cost(adm_all)) + \
                            (spv * self.get_individual_cost(spv_all)) + \
                            (cpm * self.get_individual_cost(cpm_all)) + \
                            (it_tech * self.get_individual_cost(it_all))
        
        final_cost = total_actual_cost * (1 + mgt_fee_rate)
        return {
            "mpp": shift_mpp + office_mpp, "shift_mpp": shift_mpp, "office_mpp": office_mpp,
            "cashier": cashier, "att": att, "ctrl": ctrl, "adm": adm, "spv": spv, "cpm": cpm, "it_tech": it_tech,
            "ratio": (final_cost / rev) * 100 if rev > 0 else 0, "cost": final_cost
        }

# --- 3. UI DASHBOARD ---
st.title("🛡️ CP CorePlanner v2.5")
st.markdown("Strict Compliance: UU Ketenagakerjaan No.6/2023 & Actual P&L Logic")
st.divider()

with st.sidebar:
    st.header("🏢 Project Identity")
    p_name = st.text_input("Project Name", value="EXAMPLE PROJECT").strip().upper()
    property_options = sorted(["APARTMENT", "HOSPITAL", "HOTEL", "MALL", "MODERN MARKET", "OFFICE BUILDING", "SHOPHOUSE", "TRADITIONAL MARKET", "TRANSIT HUB"]) + ["OTHER"]
    p_type = st.selectbox("Property Type", property_options)
    
    st.header("📍 Base Configuration")
    umk = st.number_input("Regional Minimum Wage (UMK)", value=5729876, step=100000)
    st.markdown(f"<div style='color:#fbbf24; font-weight:700; margin-top:-10px;'>✔️ {format_idr(umk)}</div>", unsafe_allow_html=True)
    hours = st.slider("Operating Hours", 16, 24, 24)
    c1, c2 = st.columns(2)
    with c1: 
        g_in = st.number_input("Gate IN", value=3)
        c_mob = st.number_input("Car Capacity", value=500, step=50)
    with c2: 
        g_out = st.number_input("Gate OUT", value=3)
        c_mot = st.number_input("Motorcycle Capacity", value=200, step=50)
    
    st.header("💰 Financial Variables")
    with st.expander("Adjust Variables"):
        f_ov = st.number_input("Amortized Fixed Cost", value=500000)
        bpjs = st.number_input("BPJS (%)", value=10.24) / 100
        thr = st.number_input("THR (%)", value=8.33) / 100
        uuck = st.number_input("UUCK (%)", value=8.33) / 100
    
    mgt_fee_check = st.checkbox("Include Management Fee")
    mgt_rate = st.number_input("Fee (%)", value=10.0) / 100 if mgt_fee_check else 0.0

eng = ComplianceEngine(umk, f_ov, bpjs, thr, uuck)
cost_label = "Total Commercial Cost" if mgt_fee_check else "Total Actual Manpower Cost"

# --- SCENARIOS ---
st.subheader(f"💡 Scenario Analysis: [{p_type}] - {p_name}")
col_a, col_b = st.columns(2)

def render_box(label, suffix, h_class, cost_class, b_class, def_rev, def_sys_idx):
    st.markdown(f"<div class='{h_class}'><h3 class='header-title'>{label}</h3></div>", unsafe_allow_html=True)
    sys = st.selectbox(f"System {label[-1]}", ['Manual', 'Semi-Auto', 'Full Manless'], index=def_sys_idx, key=f"s_{suffix}")
    rev = st.number_input(f"Revenue {label[-1]}", value=def_rev, step=10000000, key=f"r_{suffix}")
    st.markdown(f"<div style='font-size:0.85rem; font-weight:700; color:{'#004a99' if 'a' in suffix else '#d97706'}; margin-top:-10px; margin-bottom:15px;'>🎯 {format_idr(rev)}</div>", unsafe_allow_html=True)
    res = eng.calculate(sys, g_in, g_out, c_mob, c_mot, hours, rev, mgt_rate)
    
    html = f"""<div class='result-card'><div class='metric-row'><div class='metric-card {b_class}'><div class='metric-label'>Total MPP</div><div class='metric-value'>{res['mpp']} Pax</div></div><div class='metric-card {b_class}'><div class='metric-label'>Cost Ratio</div><div class='metric-value'>{res['ratio']:.2f}%</div></div></div><div class='breakdown-bar'><div class='bd-item'><span class='bd-label'>Ops Shift</span><span class='bd-val'>{res['shift_mpp']} Pax</span></div><div class='bd-item bd-border'><span class='bd-label'>Per Group</span><span class='bd-val'>{get_shift_distribution(res['shift_mpp'])}</span></div><div class='bd-item'><span class='bd-label'>Office</span><span class='bd-val'>{res['office_mpp']} Pax</span></div></div><div style='display:flex; gap:10px; margin-bottom:15px;'><div class='comp-box' style='flex:1;'><div class='comp-title'>Non-Staff</div><div class='comp-row'><span>Att</span><span>{res['att']}</span></div><div class='comp-row'><span>Gate</span><span>{res['cashier']}</span></div><div class='comp-row'><span>Ctrl</span><span>{res['ctrl']}</span></div></div><div class='comp-box' style='flex:1;'><div class='comp-title'>Staff</div><div class='comp-row'><span>Adm</span><span>{res['adm']}</span></div><div class='comp-row'><span>SPV</span><span>{res['spv']}</span></div><div class='comp-row'><span>CPM</span><span>{res['cpm']}</span></div><div class='comp-row'><span>IT</span><span>{res['it_tech']}</span></div></div></div><div class='total-cost-box {cost_class}'><div class='total-label'>{cost_label}</div><p style='font-size:1.6rem; font-weight:900; color:{'#004a99' if 'a' in suffix else '#d97706'}; margin:0;'>{format_idr(res['cost'])}</p></div></div>"""
    st.markdown(html, unsafe_allow_html=True)
    return res

with col_a: res_a = render_box("🅰️ Scenario A", "a", "header-card-a", "total-cost-a", "metric-card-a", 150000000, 0)
with col_b: res_b = render_box("🅱️ Scenario B", "b", "header-card-b", "total-cost-b", "metric-card-b", 500000000, 2)

# --- 📥 DOWNLOAD REPORT ---
st.divider()
def get_excel(r_a, r_b):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df = pd.DataFrame({
            "Metric": ["Project", "Property", "System", "Total MPP", "Attendant", "Cashier", "Control Room", "Admin", "Supervisor", "CPM", "IT/Tech", "Cost Ratio (%)", "Total Cost"],
            "Scenario A": [p_name, p_type, "Manual", r_a['mpp'], r_a['att'], r_a['cashier'], r_a['ctrl'], r_a['adm'], r_a['spv'], r_a['cpm'], r_a['it_tech'], round(r_a['ratio'],2), r_a['cost']],
            "Scenario B": [p_name, p_type, "Full Manless", r_b['mpp'], r_b['att'], r_b['cashier'], r_b['ctrl'], r_b['adm'], r_b['spv'], r_b['cpm'], r_b['it_tech'], round(r_b['ratio'],2), r_b['cost']]
        })
        df.to_excel(writer, index=False)
    return output.getvalue()

st.download_button("📥 DOWNLOAD REPORT (EXCEL)", get_excel(res_a, res_b), f"MPP_{p_name}.xlsx")

# --- SHIFT INFO & TABLE ---
st.subheader("🗓️ Shift Rotation (UU No.6/2023 Compliant)")
st.markdown(f"<div class='info-box-a'><strong>🅰️ Scenario A:</strong> Each operational shift will be manned by <b>{get_shift_distribution(res_a['shift_mpp'])}</b> on-site.</div><div class='info-box-b'><strong>🅱️ Scenario B:</strong> Each operational shift will be manned by <b>{get_shift_distribution(res_b['shift_mpp'])}</b> on-site.</div>", unsafe_allow_html=True)

shift_df = pd.DataFrame({"Day": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], "Shift 1 (Morning)": ["Group A", "Group A", "Group B", "Group B", "Group C", "Group C", "Group D"], "Shift 2 (Afternoon)": ["Group B", "Group B", "Group C", "Group C", "Group D", "Group D", "Group A"], "Shift 3 (Night)": ["Group C", "Group C", "Group D", "Group D", "Group A", "Group A", "Group B"], "OFF (Rest Day)": ["Group D", "Group D", "Group A", "Group A", "Group B", "Group B", "Group C"]})
st.dataframe(shift_df, use_container_width=True, hide_index=True)
