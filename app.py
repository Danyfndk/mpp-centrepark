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
    if rem == 0:
        return f"{base} Pax"
    else:
        return f"{base} - {base+1} Pax"

# --- 1. SaaS UI STYLING (PREMIUM & RESPONSIVE) ---
st.set_page_config(page_title="CP CorePlanner", page_icon="🅿️", layout="wide")

st.markdown("""
<style>
.main { background-color: #f4f7fa; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
section[data-testid="stSidebar"] { background-color: #004a99 !important; }
section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 { color: #ffffff !important; }
section[data-testid="stSidebar"] input { color: #1e293b !important; background-color: #ffffff !important; border-radius: 6px !important; border: 1px solid #cbd5e1 !important; }
section[data-testid="stSidebar"] div[data-baseweb="select"] * { color: #1e293b !important; }

.header-card-a { background-color: #ffffff; padding: 15px 20px; border-radius: 12px; border-top: 6px solid #004a99; box-shadow: 0 4px 10px rgba(0,74,153,0.1); margin-bottom: 15px; }
.header-card-b { background-color: #ffffff; padding: 15px 20px; border-radius: 12px; border-top: 6px solid #d97706; box-shadow: 0 4px 10px rgba(217,119,6,0.1); margin-bottom: 15px; }
.header-title { margin: 0; color: #1e293b; font-weight: 800; font-size: 1.3rem; }

.result-card { background-color: #ffffff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-top: 5px; margin-bottom: 20px; }

.metric-row { display: flex; gap: 15px; margin-bottom: 15px; }
.metric-card { background-color: #f8fafc; padding: 15px; border-radius: 10px; flex: 1; border: 1px solid #e2e8f0; }
.metric-card-a { border-left: 5px solid #004a99; } 
.metric-card-b { border-left: 5px solid #d97706; } 
.metric-label { font-size: 0.8rem; color: #64748b; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }
.metric-value { font-size: 1.3rem; color: #1e293b; font-weight: 900; margin-top: 5px;}

.breakdown-bar { display: flex; background-color: #f1f5f9; padding: 12px 10px; border-radius: 10px; margin-bottom: 15px; justify-content: space-between; }
.bd-item { display: flex; flex-direction: column; text-align: center; flex: 1; }
.bd-border { border-left: 1px solid #cbd5e1; border-right: 1px solid #cbd5e1; }
.bd-label { font-size: 0.75rem; color: #64748b; font-weight: 700; text-transform: uppercase; }
.bd-val { font-size: 1rem; color: #0f172a; font-weight: 800; margin-top: 2px;}

.comp-box { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; font-size: 0.85rem; }
.comp-title { font-weight: 800; color: #1e293b; margin-bottom: 8px; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; text-transform: uppercase; font-size: 0.75rem;}
.comp-row { display: flex; justify-content: space-between; margin-bottom: 4px; color: #475569; }
.comp-val { font-weight: 700; color: #0f172a; }

.total-cost-box { padding: 15px; border-radius: 10px; text-align: center; margin-top: 5px;}
.total-cost-a { background-color: #f0f7ff; border: 2px dashed #93c5fd; }
.total-cost-b { background-color: #fffbeb; border: 2px dashed #fcd34d; }
.total-label { font-size: 0.85rem; font-weight: 700; color: #475569; margin-bottom: 5px; text-transform: uppercase; }
.total-value-a { font-size: 1.6rem; font-weight: 900; color: #004a99; margin: 0; }
.total-value-b { font-size: 1.6rem; font-weight: 900; color: #d97706; margin: 0; }

.money-helper-sidebar { font-size: 0.85rem; font-weight: 700; color: #fbbf24; margin-top: -10px; margin-bottom: 15px; }

.info-box-a { background-color: #e0f2fe; padding: 15px; border-radius: 8px; border-left: 5px solid #004a99; margin-bottom: 10px; color: #0f172a;}
.info-box-b { background-color: #fef3c7; padding: 15px; border-radius: 8px; border-left: 5px solid #d97706; margin-bottom: 20px; color: #0f172a;}

div.stButton > button, div.stDownloadButton > button { background-color: #004a99 !important; color: white !important; border-radius: 8px !important; font-weight: 700 !important; width: 100%; padding: 12px 0 !important; border: none !important; text-transform: uppercase; letter-spacing: 1px;}
div.stButton > button:hover, div.stDownloadButton > button:hover { background-color: #003366 !important; box-shadow: 0 4px 15px rgba(0,74,153,0.3) !important; }
</style>
""", unsafe_allow_html=True)

# --- 2. CORE COMPLIANCE ENGINE ---
class ComplianceEngine:
    def __init__(self, umk, fixed_overhead, bpjs_rate, thr_rate, uuck_rate):
        self.umk = umk
        self.fixed_overhead = fixed_overhead 
        self.bpjs_thr_uuck = bpjs_rate + thr_rate + uuck_rate

    def get_cost(self, count, allowance_rate=0):
        if count <= 0: return 0
        base_salary = self.umk
        allowance_amount = self.umk * allowance_rate
        benefit_amount = self.umk * self.bpjs_thr_uuck
        base_cost_per_head = base_salary + allowance_amount + benefit_amount + self.fixed_overhead
        return base_cost_per_head * count

    def calculate(self, sys, g_in, g_out, c_mob, c_mot, hours, rev, mgt_fee_rate=0.0):
        ff = (hours * 7) / 40 
        
        # Industry Standard Logic for Attendants
        if sys == 'Manual':
            att_base = (c_mob / 250) + (c_mot / 500)
            cashier = math.floor((g_in + g_out) * ff)
        elif sys == 'Semi-Auto':
            att_base = (c_mob / 400) + (c_mot / 800)
            cashier = math.floor(g_out * ff)
        else: # Full Manless
            att_base = (c_mob / 600) + (c_mot / 1200)
            cashier = 0
            
        att = math.floor(math.ceil(att_base) * ff) if att_base > 0 else 0
        ctrl = math.floor(1 * ff) if sys != 'Manual' else 0

        # Staff logic
        spv, adm, cpm = (3, 1, 1) if rev >= 500000000 else (1, 0, 0) if rev >= 150000000 else (0, 0, 0)
        
        adm_all, spv_all, cpm_all = 0.10, 0.20, 0.30
        if cpm > 0: pass
        elif spv > 0: spv_all = 0.30
        elif adm > 0: adm_all = 0.30
            
        shift_mpp = cashier + ctrl + att
        office_mpp = spv + adm + cpm
        actual_manpower_cost = self.get_cost(shift_mpp, 0) + self.get_cost(adm, adm_all) + self.get_cost(spv, spv_all) + self.get_cost(cpm, cpm_all)
        final_cost = actual_manpower_cost * (1 + mgt_fee_rate)
        
        return {
            "mpp": shift_mpp + office_mpp, "shift_mpp": shift_mpp, "office_mpp": office_mpp,
            "cashier": cashier, "att": att, "ctrl": ctrl, "adm": adm, "spv": spv, "cpm": cpm,
            "ratio": (final_cost / rev) * 100 if rev > 0 else 0, "cost": final_cost
        }

# --- 3. UI DASHBOARD ---
st.title("🛡️ CP CorePlanner v2.5")
st.markdown("Strict Compliance: UU Ketenagakerjaan No.6/2023 (40 Hrs/Wk & Rest Days) & Actual P&L Logic")
st.divider()

with st.sidebar:
    st.header("🏢 Project Identity") 
    raw_project_name = st.text_input("Project Name", value="EXAMPLE PROJECT")
    project_name = raw_project_name.strip().upper() 
    property_options = ["APARTMENT", "HOSPITAL", "HOTEL", "MALL", "MODERN MARKET", "OFFICE BUILDING", "SHOPHOUSE", "TRADITIONAL MARKET", "TRANSIT HUB", "OTHER"]
    property_type = st.selectbox("Property Type", property_options)
    standard_project_id = f"[{property_type}] - {project_name}"
    
    st.divider()
    st.header("📍 Base Configuration")
    umk = st.number_input("Regional Minimum Wage (UMK)", value=5729876, step=100000)
    st.markdown(f"<div class='money-helper-sidebar'>✔️ {format_idr(umk)}</div>", unsafe_allow_html=True)
    hours = st.slider("Operating Hours / Day", 16, 24, 24)
    
    # RAPIKAN KESEJAJARAN (Menghapus kata 'Bays' agar seimbang)
    c_g1, c_g2 = st.columns(2)
    with c_g1:
        g_in = st.number_input("Gate IN", value=3)
        c_mob = st.number_input("Car Capacity", value=300, step=50)
    with c_g2:
        g_out = st.number_input("Gate OUT", value=3)
        c_mot = st.number_input("Motorcycle Capacity", value=200, step=50)

    st.divider()
    st.header("💰 Actual Cost Variables")
    with st.expander("Adjust Financial Variables", expanded=False):
        fixed_overhead = st.number_input("Amortized Fixed Cost / Pax", value=500000, step=50000)
        st.markdown(f"<div class='money-helper-sidebar'>✔️ {format_idr(fixed_overhead)}</div>", unsafe_allow_html=True)
        bpjs_rate = st.number_input("BPJS Company Portion (%)", value=10.24, step=0.1) / 100
        thr_rate = st.number_input("THR Provision (%)", value=8.33, step=0.1) / 100
        uuck_rate = st.number_input("UUCK/Severance Provision (%)", value=8.33, step=0.1) / 100

    st.divider()
    st.header("📈 Commercial Settings")
    include_mgt_fee = st.checkbox("Include Management Fee")
    mgt_fee_rate = st.number_input("Management Fee (%)", value=10.0, step=1.0) / 100 if include_mgt_fee else 0.0

eng = ComplianceEngine(umk, fixed_overhead, bpjs_rate, thr_rate, uuck_rate)
cost_label = "Total Commercial Cost (incl. Mgt Fee)" if include_mgt_fee else "Total Actual Manpower Cost"

# --- RENDER SCENARIOS ---
st.subheader(f"💡 What-If Scenario Analysis: {standard_project_id}")
col_a, col_b = st.columns(2)

def render_scenario(scenario_label, key_suffix, header_class, cost_class, border_class, default_idx=0, default_rev=150000000):
    st.markdown(f"<div class='{header_class}'><h3 class='header-title'>{scenario_label}</h3></div>", unsafe_allow_html=True)
    sys = st.selectbox(f"System {scenario_label[-1]}", ['Manual', 'Semi-Auto', 'Full Manless'], index=default_idx, key=f"sys_{key_suffix}")
    rev = st.number_input(f"Est. Revenue {scenario_label[-1]}", value=default_rev, step=10000000, key=f"rev_{key_suffix}")
    st.markdown(f"<div style='font-size: 0.85rem; font-weight: 700; color: {'#004a99' if 'a' in key_suffix else '#d97706'}; margin-top: -10px; margin-bottom: 15px;'>🎯 {format_idr(rev)}</div>", unsafe_allow_html=True)
    res = eng.calculate(sys, g_in, g_out, c_mob, c_mot, hours, rev, mgt_fee_rate)
    html = f"<div class='result-card'><div class='metric-row'><div class='metric-card {border_class}'><div class='metric-label'>Total MPP</div><div class='metric-value'>{res['mpp']} Pax</div></div><div class='metric-card {border_class}'><div class='metric-label'>Cost Ratio</div><div class='metric-value'>{res['ratio']:.2f}%</div></div></div><div class='breakdown-bar'><div class='bd-item'><span class='bd-label'>Ops Shift</span><span class='bd-val'>{res['shift_mpp']} Pax</span></div><div class='bd-item bd-border'><span class='bd-label'>Per Regu (Group)</span><span class='bd-val'>{get_shift_distribution(res['shift_mpp'])}</span></div><div class='bd-item'><span class='bd-label'>Back Office</span><span class='bd-val'>{res['office_mpp']} Pax</span></div></div><div style='display:flex; gap:10px; margin-bottom:15px;'><div class='comp-box' style='flex:1;'><div class='comp-title'>Non-Staff (Shift)</div><div class='comp-row'><span>Attendant</span><span class='comp-val'>{res['att']} Pax</span></div><div class='comp-row'><span>Gate/Cashier</span><span class='comp-val'>{res['cashier']} Pax</span></div><div class='comp-row'><span>Control Room</span><span class='comp-val'>{res['ctrl']} Pax</span></div></div><div class='comp-box' style='flex:1;'><div class='comp-title'>Staff (Office)</div><div class='comp-row'><span>Admin</span><span class='comp-val'>{res['adm']} Pax</span></div><div class='comp-row'><span>Supervisor</span><span class='comp-val'>{res['spv']} Pax</span></div><div class='comp-row'><span>Manager (CPM)</span><span class='comp-val'>{res['cpm']} Pax</span></div></div></div><div class='total-cost-box {cost_class}'><div class='total-label'>{cost_label}</div><p style='font-size: 1.6rem; font-weight: 900; color: {'#004a99' if 'a' in key_suffix else '#d97706'}; margin: 0;'>{format_idr(res['cost'])}</p></div></div>"
    st.markdown(html, unsafe_allow_html=True)
    return res

with col_a: res_a = render_scenario("🅰️ Scenario A", "a", "header-card-a", "total-cost-a", "metric-card-a")
with col_b: res_b = render_scenario("🅱️ Scenario B", "b", "header-card-b", "total-cost-b", "metric-card-b", default_idx=2, default_rev=250000000)

# --- SHIFT TABLE & EXCEL ---
st.divider()
shift_logic = pd.DataFrame({"Day": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], "Shift 1 (Morning)": ["Group A", "Group A", "Group B", "Group B", "Group C", "Group C", "Group D"], "Shift 2 (Afternoon)": ["Group B", "Group B", "Group C", "Group C", "Group D", "Group D", "Group A"], "Shift 3 (Night)": ["Group C", "Group C", "Group D", "Group D", "Group A", "Group A", "Group B"], "OFF (Rest Day)": ["Group D", "Group D", "Group A", "Group A", "Group B", "Group B", "Group C"]})
st.subheader(f"🗓️ Shift Rotation (UU No.6/2023 Compliant)")
st.markdown(f"<div class='info-box-a'><strong>🅰️ Scenario A Allocation:</strong> Each shift will be manned by <b>{get_shift_distribution(res_a['shift_mpp'])}</b>.</div><div class='info-box-b'><strong>🅱️ Scenario B Allocation:</strong> Each shift will be manned by <b>{get_shift_distribution(res_b['shift_mpp'])}</b>.</div>", unsafe_allow_html=True)
st.dataframe(shift_logic, use_container_width=True, hide_index=True)

# Profitability Alert
if res_a['ratio'] > 30 or res_b['ratio'] > 30: st.warning("⚠️ **Profitability Alert**: One of the scenarios exceeds the 30% Manpower Cost threshold.")
else: st.success("✅ **P&L Secure**: Both scenarios are within healthy limits.")
