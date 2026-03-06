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

# --- 1. SaaS UI STYLING (PREMIUM & CLEAN) ---
st.set_page_config(page_title="CP CorePlanner", page_icon="🅿️", layout="wide")

st.markdown("""<style>
.main { background-color: #f4f7fa; font-family: 'Segoe UI', sans-serif; }
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

.comp-box { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; font-size: 0.82rem; }
.comp-title { font-weight: 800; color: #1e293b; margin-bottom: 8px; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; text-transform: uppercase; font-size: 0.72rem;}
.comp-row { display: flex; justify-content: space-between; margin-bottom: 4px; color: #475569; }
.comp-val { font-weight: 700; color: #0f172a; }

.total-cost-box { padding: 15px; border-radius: 10px; text-align: center; margin-top: 5px;}
.total-cost-a { background-color: #f0f7ff; border: 2px dashed #93c5fd; }
.total-cost-b { background-color: #fffbeb; border: 2px dashed #fcd34d; }
.total-label { font-size: 0.85rem; font-weight: 700; color: #475569; margin-bottom: 5px; text-transform: uppercase; }

.money-helper-sidebar { font-size: 0.85rem; font-weight: 700; color: #fbbf24; margin-top: -10px; margin-bottom: 15px; }

.info-box-a { background-color: #e0f2fe; padding: 15px; border-radius: 8px; border-left: 5px solid #004a99; margin-bottom: 10px; color: #0f172a;}
.info-box-b { background-color: #fef3c7; padding: 15px; border-radius: 8px; border-left: 5px solid #d97706; margin-bottom: 20px; color: #0f172a;}

div.stDownloadButton > button { background-color: #004a99 !important; color: white !important; border-radius: 8px !important; font-weight: 700 !important; width: 100%; padding: 12px 0 !important; border: none !important; text-transform: uppercase; letter-spacing: 1px;}
div.stDownloadButton > button:hover { background-color: #003366 !important; box-shadow: 0 4px 15px rgba(0,74,153,0.3) !important; }
</style>""", unsafe_allow_html=True)

# --- 2. CORE COMPLIANCE ENGINE (STRICT INDUSTRY LOGIC) ---
class ComplianceEngine:
    def __init__(self, umk, fixed_overhead, bpjs_rate, thr_rate, uuck_rate):
        self.umk = umk
        self.fixed_overhead = fixed_overhead
        self.benefit_rate = bpjs_rate + thr_rate + uuck_rate

    def get_individual_cost(self, allowance_rate=0):
        # Salary/Allowance based on instructions [cite: 2025-09-04]
        salary_and_allowance = self.umk + (self.umk * allowance_rate)
        # Benefits ONLY from basic UMK [cite: 2025-08-05]
        benefit = self.umk * self.benefit_rate
        return salary_and_allowance + benefit + self.fixed_overhead

    def calculate(self, sys, g_in, g_out, c_mob, c_mot, hours, rev, mgt_fee_rate=0.0):
        ff = (hours * 7) / 40 # Standard Labor Law Fatigue Factor [cite: 2025-08-05]
        
        # Mapping Non-Staff (Shift) based on Parking Capacity Fact
        if sys == 'Manual':
            att_base = (c_mob / 250) + (c_mot / 500)
            csr = math.floor((g_in + g_out) * ff)
        elif sys == 'Semi-Auto':
            att_base = (c_mob / 400) + (c_mot / 800)
            csr = math.floor(g_out * ff)
        else: # Full Manless
            att_base = (c_mob / 600) + (c_mot / 1200)
            csr = 0
            
        attd = math.floor(math.ceil(att_base) * ff) if att_base > 0 else 0
        cro = math.floor(1 * ff) if sys != 'Manual' else 0

        # Mapping Staff based on Revenue Tiers [cite: 2025-09-04]
        spv, adm, cpm = (1, 1, 1) if rev >= 500000000 else (1, 1, 0) if rev >= 150000000 else (0, 1, 0)
        
        # Dedicated IT logic [cite: 2025-09-04]
        it = 1 if (sys != 'Manual' and rev >= 150000000) else 0 

        # Allowance Dynamic logic (Highest position gets 30%) [cite: 2025-09-04]
        adm_all, spv_all, cpm_all, it_all = 0.10, 0.20, 0.30, 0.10
        if cpm > 0: pass
        elif spv > 0: spv_all = 0.30
        elif adm > 0: adm_all = 0.30

        shift_mpp = csr + cro + attd
        office_mpp = spv + adm + cpm + it
        
        total_actual_cost = (shift_mpp * self.get_individual_cost(0)) + \
                            (adm * self.get_individual_cost(adm_all)) + \
                            (spv * self.get_individual_cost(spv_all)) + \
                            (cpm * self.get_individual_cost(cpm_all)) + \
                            (it * self.get_individual_cost(it_all))
        
        final_cost = total_actual_cost * (1 + mgt_fee_rate) # Mgt fee on total cost
        
        return {
            "mpp": shift_mpp + office_mpp, "shift_mpp": shift_mpp, "office_mpp": office_mpp,
            "attd": attd, "csr": csr, "cro": cro, "adm": adm, "spv": spv, "cpm": cpm, "it": it,
            "ratio": (final_cost / rev) * 100 if rev > 0 else 0, "cost": final_cost
        }

# --- 3. UI DASHBOARD ---
st.title("🛡️ CP CorePlanner v2.5")
st.markdown("Strict Industry Compliance: Automated Manpower Mapping & P&L Logic")
st.divider()

with st.sidebar:
    st.header("🏢 Project Identity")
    p_name = st.text_input("Project Name", value="EXAMPLE PROJECT").strip().upper()
    property_type = st.selectbox("Property Type", sorted(["APARTMENT", "HOSPITAL", "HOTEL", "MALL", "MODERN MARKET", "OFFICE BUILDING", "SHOPHOUSE", "TRADITIONAL MARKET", "TRANSIT HUB"]) + ["OTHER"])
    
    st.header("📍 Base Configuration")
    umk = st.number_input("Regional UMK", value=5729876, step=100000)
    st.markdown(f"<div class='money-helper-sidebar'>✔️ {format_idr(umk)}</div>", unsafe_allow_html=True)
    hours = st.slider("Operating Hours", 16, 24, 24)
    c1, c2 = st.columns(2)
    with c1: 
        g_in = st.number_input("Gate IN", value=3)
        c_mob = st.number_input("Car Capacity", value=500, step=50)
    with c2: 
        g_out = st.number_input("Gate OUT", value=3)
        c_mot = st.number_input("Motorcycle Capacity", value=200, step=50)
    
    st.header("💰 Financial Variables")
    with st.expander("Adjust Amortization & Benefits"):
        f_ov = st.number_input("Amortized Fixed Cost / Pax", value=500000)
        bpjs = st.number_input("BPJS (%)", value=10.24, step=0.01) / 100
        thr = st.number_input("THR (%)", value=8.33, step=0.01) / 100
        uuck = st.number_input("UUCK (%)", value=8.33, step=0.01) / 100
    
    mgt_fee_check = st.checkbox("Include Management Fee")
    mgt_rate = st.number_input("Fee (%)", value=10.0, step=1.0) / 100 if mgt_fee_check else 0.0

eng = ComplianceEngine(umk, f_ov, bpjs, thr, uuck)
cost_label = "Total Commercial Cost" if mgt_fee_check else "Total Actual Manpower Cost"

# --- SCENARIO RENDERING ---
st.subheader(f"💡 Scenario Analysis: [{property_type}] - {p_name}")
col_a, col_b = st.columns(2)

def render_scen(label, suffix, h_class, cost_class, b_class, def_sys_idx, def_rev):
    st.markdown(f"<div class='{h_class}'><h3 class='header-title'>{label}</h3></div>", unsafe_allow_html=True)
    sys = st.selectbox(f"System {label[-1]}", ['Manual', 'Semi-Auto', 'Full Manless'], index=def_sys_idx, key=f"s_{suffix}")
    rev = st.number_input(f"Revenue {label[-1]}", value=def_rev, step=10000000, key=f"r_{suffix}")
    st.markdown(f"<div style='font-size:0.85rem; font-weight:700; color:{'#004a99' if 'a' in suffix else '#d97706'}; margin-top:-10px; margin-bottom:15px;'>🎯 {format_idr(rev)}</div>", unsafe_allow_html=True)
    res = eng.calculate(sys, g_in, g_out, c_mob, c_mot, hours, rev, mgt_rate)
    
    # SINGLE-LINE HTML TO PREVENT LEAKS
    html = f"<div class='result-card'><div class='metric-row'><div class='metric-card {b_class}'><div class='metric-label'>Total MPP</div><div class='metric-value'>{res['mpp']} Pax</div></div><div class='metric-card {b_class}'><div class='metric-label'>Cost Ratio</div><div class='metric-value'>{res['ratio']:.2f}%</div></div></div><div class='breakdown-bar'><div class='bd-item'><span class='bd-label'>Ops Shift</span><span class='bd-val'>{res['shift_mpp']} Pax</span></div><div class='bd-item bd-border'><span class='bd-label'>Per Group</span><span class='bd-val'>{get_shift_distribution(res['shift_mpp'])}</span></div><div class='bd-item'><span class='bd-label'>Office</span><span class='bd-val'>{res['office_mpp']} Pax</span></div></div><div style='display:flex; gap:10px; margin-bottom:15px;'><div class='comp-box' style='flex:1;'><div class='comp-title'>Non-Staff (Shift)</div><div class='comp-row'><span>ATTD</span><span class='comp-val'>{res['attd']}</span></div><div class='comp-row'><span>CSR</span><span class='comp-val'>{res['csr']}</span></div><div class='comp-row'><span>CRO</span><span class='comp-val'>{res['cro']}</span></div></div><div class='comp-box' style='flex:1;'><div class='comp-title'>Staff (Office)</div><div class='comp-row'><span>ADM</span><span class='comp-val'>{res['adm']}</span></div><div class='comp-row'><span>SPV</span><span class='comp-val'>{res['spv']}</span></div><div class='comp-row'><span>CPM</span><span class='comp-val'>{res['cpm']}</span></div><div class='comp-row'><span>IT</span><span class='comp-val'>{res['it']}</span></div></div></div><div class='total-cost-box {cost_class}'><div class='total-label'>{cost_label}</div><p style='font-size:1.6rem; font-weight:900; color:{'#004a99' if 'a' in suffix else '#d97706'}; margin:0;'>{format_idr(res['cost'])}</p></div></div>"
    st.markdown(html, unsafe_allow_html=True)
    return res

with col_a: res_a = render_scen("🅰️ Scenario A", "a", "header-card-a", "total-cost-a", "metric-card-a", 0, 150000000)
with col_b: res_b = render_scen("🅱️ Scenario B", "b", "header-card-b", "total-cost-b", "metric-card-b", 2, 500000000)

# --- 📥 REPORT & SHIFT (FIXED EXCEL FORMATTING) ---
st.divider()

def get_xls(ra, rb, p_name, p_type, umk, hours, g_in, g_out, c_mob, c_mot, f_ov, bpjs, thr, uuck, mgt_rate):
    out = BytesIO()
    with pd.ExcelWriter(out, engine='xlsxwriter') as wr:
        data = {
            "Category": [
                "PROJECT IDENTITY", "Project Name", "Property Type", "",
                "BASE CONFIGURATION", "Regional UMK", "Operating Hours", "Gate IN", "Gate OUT", "Car Capacity", "Motorcycle Capacity", "",
                "FINANCIAL VARIABLES", "Fixed Cost / Pax", "BPJS (%)", "THR (%)", "UUCK (%)", "Management Fee (%)", "",
                "MANPOWER MAPPING", "System Type", "Total MPP (Pax)", "ATTD (Attendant)", "CSR (Cashier)", "CRO (Control Room)", 
                "ADM (Admin)", "SPV (Supervisor)", "CPM (Manager)", "IT (Technician)", "",
                "SUMMARY", "Cost Ratio (%)", "Total Actual/Comm. Cost"
            ],
            "Scenario A": [
                "", p_name, p_type, "",
                "", umk, hours, g_in, g_out, c_mob, c_mot, "",
                "", f_ov, bpjs*100, thr*100, uuck*100, mgt_rate*100, "",
                "", "Manual", ra['mpp'], ra['attd'], ra['csr'], ra['cro'], ra['adm'], ra['spv'], ra['cpm'], ra['it'], "",
                "", f"{ra['ratio']:.2f}%", ra['cost']
            ],
            "Scenario B": [
                "", p_name, p_type, "",
                "", umk, hours, g_in, g_out, c_mob, c_mot, "",
                "", f_ov, bpjs*100, thr*100, uuck*100, mgt_rate*100, "",
                "", "Full Manless", rb['mpp'], rb['attd'], rb['csr'], rb['cro'], rb['adm'], rb['spv'], rb['cpm'], rb['it'], "",
                "", f"{rb['ratio']:.2f}%", rb['cost']
            ]
        }
        df = pd.DataFrame(data)
        df.to_excel(wr, index=False, sheet_name='MPP Report')
        workbook = wr.book
        worksheet = wr.sheets['MPP Report']
        
        # Neat Formats
        header_f = workbook.add_format({'bold': True, 'bg_color': '#004a99', 'font_color': 'white', 'border': 1, 'align': 'center'})
        border_f = workbook.add_format({'border': 1})
        money_f = workbook.add_format({'num_format': '#,##0', 'border': 1, 'align': 'right'})
        cat_f = workbook.add_format({'bold': True, 'font_color': '#004a99', 'bg_color': '#f8fafc'})

        worksheet.set_column('A:A', 35)
        worksheet.set_column('B:C', 25)

        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_f)
        for row_num in range(len(df)):
            val = df.iloc[row_num, 0]
            if val and val.isupper():
                worksheet.write(row_num + 1, 0, val, cat_f)
            else:
                worksheet.write(row_num + 1, 0, val, border_f)
            
            # Format numbers
            for col_idx in [1, 2]:
                cell_val = df.iloc[row_num, col_idx]
                if any(x in str(val) for x in ["UMK", "Cost", "Fixed"]):
                    worksheet.write(row_num + 1, col_idx, cell_val, money_f)
                else:
                    worksheet.write(row_num + 1, col_idx, cell_val, border_f)
    return out.getvalue()

st.download_button(
    label="📥 DOWNLOAD REPORT (EXCEL)",
    data=get_xls(res_a, res_b, p_name, property_type, umk, hours, g_in, g_out, c_mob, c_mot, f_ov, bpjs, thr, uuck, mgt_rate),
    file_name=f"MPP_REPORT_{p_name}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# --- SHIFT ROTATION ---
st.subheader("🗓️ Shift Rotation (UU No.6/2023 Compliant)")
st.markdown(f"<div class='info-box-a'><strong>🅰️ Scenario A:</strong> Each operational shift manned by <b>{get_shift_distribution(res_a['shift_mpp'])}</b>.</div><div class='info-box-b'><strong>🅱️ Scenario B:</strong> Each operational shift manned by <b>{get_shift_distribution(res_b['shift_mpp'])}</b>.</div>", unsafe_allow_html=True)
shift_df = pd.DataFrame({"Day": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], "Shift 1 (Morning)": ["Group A", "Group A", "Group B", "Group B", "Group C", "Group C", "Group D"], "Shift 2 (Afternoon)": ["Group B", "Group B", "Group C", "Group C", "Group D", "Group D", "Group A"], "Shift 3 (Night)": ["Group C", "Group C", "Group D", "Group D", "Group A", "Group A", "Group B"], "OFF (Rest Day)": ["Group D", "Group D", "Group A", "Group A", "Group B", "Group B", "Group C"]})
st.dataframe(shift_df, use_container_width=True, hide_index=True)
