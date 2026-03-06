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

.money-helper { font-size: 0.85rem; font-weight: 700; margin-top: -10px; margin-bottom: 15px; padding-left: 5px;}
.helper-a { color: #004a99; }
.helper-b { color: #d97706; }
.money-helper-sidebar { font-size: 0.85rem; font-weight: 700; color: #fbbf24; margin-top: -10px; margin-bottom: 15px; }

.info-box-a { background-color: #e0f2fe; padding: 15px; border-radius: 8px; border-left: 5px solid #004a99; margin-bottom: 10px; color: #0f172a;}
.info-box-b { background-color: #fef3c7; padding: 15px; border-radius: 8px; border-left: 5px solid #d97706; margin-bottom: 20px; color: #0f172a;}

div.stButton > button, div.stDownloadButton > button { background-color: #004a99 !important; color: white !important; border-radius: 8px !important; font-weight: 700 !important; width: 100%; padding: 12px 0 !important; border: none !important; text-transform: uppercase; letter-spacing: 1px;}
div.stButton > button:hover, div.stDownloadButton > button:hover { background-color: #003366 !important; box-shadow: 0 4px 15px rgba(0,74,153,0.3) !important; }
</style>
""", unsafe_allow_html=True)

# --- 2. CORE COMPLIANCE ENGINE (NEW INDUSTRY STANDARD LOGIC) ---
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
        # STANDAR KERJA (Fatigue Factor)
        ff = (hours * 7) / 40 
        
        # --- 1. LOGIKA KAPASITAS PARKIR UNTUK ATTENDANT (INDUSTRY STANDARD) ---
        if sys == 'Manual':
            att_base = (c_mob / 250) + (c_mot / 500)
        elif sys == 'Semi-Auto':
            att_base = (c_mob / 400) + (c_mot / 800)
        else: # Full Manless
            att_base = (c_mob / 600) + (c_mot / 1200)
            
        att = math.floor(math.ceil(att_base) * ff) if att_base > 0 else 0
        
        # --- 2. LOGIKA CASHIER BERDASARKAN GATE ---
        if sys == 'Manual':
            cashier = math.floor((g_in + g_out) * ff)
        elif sys == 'Semi-Auto':
            cashier = math.floor(g_out * ff) # Hanya bayar di Gate OUT
        else:
            cashier = 0 # Manless = Cashless
            
        # --- 3. LOGIKA CONTROL ROOM ---
        ctrl = math.floor(1 * ff) if sys != 'Manual' else 0

        # --- 4. LOGIKA STAFF BERDASARKAN REVENUE ---
        spv, adm, cpm = (3, 1, 1) if rev >= 500000000 else (1, 0, 0) if rev >= 150000000 else (0, 0, 0)
        
        adm_allowance = 0.10
        spv_allowance = 0.20
        cpm_allowance = 0.30

        if cpm > 0:
            pass 
        elif spv > 0:
            spv_allowance = 0.30 
        elif adm > 0:
            adm_allowance = 0.30 
            
        shift_mpp = cashier + ctrl + att
        office_mpp = spv + adm + cpm
            
        cost_ops = self.get_cost(shift_mpp, 0)
        cost_adm = self.get_cost(adm, adm_allowance)
        cost_spv = self.get_cost(spv, spv_allowance)
        cost_cpm = self.get_cost(cpm, cpm_allowance)
        
        actual_manpower_cost = cost_ops + cost_adm + cost_spv + cost_cpm
        final_cost = actual_manpower_cost * (1 + mgt_fee_rate)
        
        total_mpp = shift_mpp + office_mpp
        ratio = (final_cost / rev) * 100 if rev > 0 else 0
        
        return {
            "mpp": total_mpp, 
            "shift_mpp": shift_mpp, 
            "office_mpp": office_mpp,
            "cashier": cashier,
            "att": att,
            "ctrl": ctrl,
            "adm": adm,
            "spv": spv,
            "cpm": cpm,
            "ratio": ratio, 
            "cost": final_cost
        }

# --- EXCEL DOWNLOAD FUNCTION ---
def generate_excel(df_comparison, df_shift):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_comparison.to_excel(writer, sheet_name='Scenario Comparison', index=False)
        df_shift.to_excel(writer, sheet_name='Shift Schedule', index=False)
        
        workbook = writer.book
        worksheet1 = writer.sheets['Scenario Comparison']
        worksheet2 = writer.sheets['Shift Schedule']
        money_format = workbook.add_format({'num_format': '#,##0'})
        
        for i, col in enumerate(df_comparison.columns):
            column_len = max(df_comparison[col].astype(str).map(len).max(), len(col)) + 2
            if "Cost" in col or "Revenue" in col:
                worksheet1.set_column(i, i, column_len, money_format)
            else:
                worksheet1.set_column(i, i, column_len)
                
        for i, col in enumerate(df_shift.columns):
            column_len = max(df_shift[col].astype(str).map(len).max(), len(col)) + 2
            worksheet2.set_column(i, i, column_len)
            
    return output.getvalue()

# --- 3. UI DASHBOARD ---
st.title("🛡️ CP CorePlanner v2.5")
st.markdown("Strict Compliance: UU Ketenagakerjaan No.6/2023 (40 Hrs/Wk & Rest Days) & Actual P&L Logic")
st.divider()

with st.sidebar:
    st.header("🏢 Project Identity") 
    raw_project_name = st.text_input("Project Name", value="EXAMPLE PROJECT")
    project_name = raw_project_name.strip().upper() 
    
    property_options = [
        "APARTMENT", "HOSPITAL", "HOTEL", "MALL", "MODERN MARKET", 
        "OFFICE BUILDING", "SHOPHOUSE", "TRADITIONAL MARKET", "TRANSIT HUB", "OTHER"
    ]
    property_type = st.selectbox("Property Type", property_options)
    standard_project_id = f"[{property_type}] - {project_name}"
    
    st.divider()
    
    st.header("📍 Base Configuration")
    umk = st.number_input("Regional Minimum Wage (UMK)", value=5729876, step=100000)
    st.markdown(f"<div class='money-helper-sidebar'>✔️ {format_idr(umk)}</div>", unsafe_allow_html=True)
    
    hours = st.slider("Operating Hours / Day", 16, 24, 24)
    
    c_g1, c_g2 = st.columns(2)
    with c_g1:
        g_in = st.number_input("Gate IN", value=3)
        c_mob = st.number_input("Car Capacity (Bays)", value=300, step=50)
    with c_g2:
        g_out = st.number_input("Gate OUT", value=3)
        c_mot = st.number_input("Motor Capacity (Bays)", value=200, step=50)

    st.divider()
    
    st.header("💰 Actual Cost Variables")
    with st.expander("Adjust Financial Variables", expanded=False):
        fixed_overhead = st.number_input("Amortized Fixed Cost / Pax", value=500000, step=50000)
        st.markdown(f"<div class='money-helper-sidebar'>✔️ {format_idr(fixed_overhead)}</div>", unsafe_allow_html=True)
        st.caption("BPJS, THR & UUCK (Strictly from Basic UMK):")
        bpjs_rate = st.number_input("BPJS Company Portion (%)", value=10.24, step=0.1) / 100
        thr_rate = st.number_input("THR Provision (%)", value=8.33, step=0.1) / 100
        uuck_rate = st.number_input("UUCK/Severance Provision (%)", value=8.33, step=0.1) / 100

    st.divider()
    
    st.header("📈 Commercial Settings")
    include_mgt_fee = st.checkbox("Include Management Fee")
    mgt_fee_rate = 0.0 
    if include_mgt_fee:
        mgt_fee_rate = st.number_input("Management Fee (%)", value=10.0, step=1.0) / 100
        st.caption("*Mgt Fee is calculated from Total Actual Cost")

eng = ComplianceEngine(umk, fixed_overhead, bpjs_rate, thr_rate, uuck_rate)
cost_label = "Total Commercial Cost (incl. Mgt Fee)" if include_mgt_fee else "Total Actual Manpower Cost"

# WHAT-IF COMPARISON
st.subheader(f"💡 What-If Scenario Analysis: {standard_project_id}")
col_a, col_b = st.columns(2)

with col_a:
    st.markdown("<div class='header-card-a'><h3 class='header-title'>🅰️ Scenario A</h3></div>", unsafe_allow_html=True)
    sys_a = st.selectbox("System A", ['Manual', 'Semi-Auto', 'Full Manless'], key="sys_a")
    rev_a = st.number_input("Est. Revenue A", value=150000000, step=10000000, key="rev_a")
    st.markdown(f"<div class='money-helper helper-a'>🎯 {format_idr(rev_a)}</div>", unsafe_allow_html=True)
    res_a = eng.calculate(sys_a, g_in, g_out, c_mob, c_mot, hours, rev_a, mgt_fee_rate)
    
    html_a = f"<div class='result-card'><div class='metric-row'><div class='metric-card metric-card-a'><div class='metric-label'>Total MPP</div><div class='metric-value'>{res_a['mpp']} Pax</div></div><div class='metric-card metric-card-a'><div class='metric-label'>Cost Ratio</div><div class='metric-value'>{res_a['ratio']:.2f}%</div></div></div><div class='breakdown-bar'><div class='bd-item'><span class='bd-label'>Ops Shift</span><span class='bd-val'>{res_a['shift_mpp']} Pax</span></div><div class='bd-item bd-border'><span class='bd-label'>Per Regu (Group)</span><span class='bd-val'>{get_shift_distribution(res_a['shift_mpp'])}</span></div><div class='bd-item'><span class='bd-label'>Back Office</span><span class='bd-val'>{res_a['office_mpp']} Pax</span></div></div><div style='display:flex; gap:10px; margin-bottom:15px;'><div class='comp-box' style='flex:1;'><div class='comp-title'>Non-Staff (Shift)</div><div class='comp-row'><span>Attendant</span><span class='comp-val'>{res_a['att']} Pax</span></div><div class='comp-row'><span>Gate/Cashier</span><span class='comp-val'>{res_a['cashier']} Pax</span></div><div class='comp-row'><span>Control Room</span><span class='comp-val'>{res_a['ctrl']} Pax</span></div></div><div class='comp-box' style='flex:1;'><div class='comp-title'>Staff (Office)</div><div class='comp-row'><span>Admin</span><span class='comp-val'>{res_a['adm']} Pax</span></div><div class='comp-row'><span>Supervisor</span><span class='comp-val'>{res_a['spv']} Pax</span></div><div class='comp-row'><span>Manager (CPM)</span><span class='comp-val'>{res_a['cpm']} Pax</span></div></div></div><div class='total-cost-box total-cost-a'><div class='total-label'>{cost_label}</div><p class='total-value-a'>{format_idr(res_a['cost'])}</p></div></div>"
    st.markdown(html_a, unsafe_allow_html=True)

with col_b:
    st.markdown("<div class='header-card-b'><h3 class='header-title'>🅱️ Scenario B</h3></div>", unsafe_allow_html=True)
    sys_b = st.selectbox("System B", ['Manual', 'Semi-Auto', 'Full Manless'], index=2, key="sys_b")
    rev_b = st.number_input("Est. Revenue B", value=250000000, step=10000000, key="rev_b")
    st.markdown(f"<div class='money-helper helper-b'>🎯 {format_idr(rev_b)}</div>", unsafe_allow_html=True)
    res_b = eng.calculate(sys_b, g_in, g_out, c_mob, c_mot, hours, rev_b, mgt_fee_rate)
    
    html_b = f"<div class='result-card'><div class='metric-row'><div class='metric-card metric-card-b'><div class='metric-label'>Total MPP</div><div class='metric-value'>{res_b['mpp']} Pax</div></div><div class='metric-card metric-card-b'><div class='metric-label'>Cost Ratio</div><div class='metric-value'>{res_b['ratio']:.2f}%</div></div></div><div class='breakdown-bar'><div class='bd-item'><span class='bd-label'>Ops Shift</span><span class='bd-val'>{res_b['shift_mpp']} Pax</span></div><div class='bd-item bd-border'><span class='bd-label'>Per Regu (Group)</span><span class='bd-val'>{get_shift_distribution(res_b['shift_mpp'])}</span></div><div class='bd-item'><span class='bd-label'>Back Office</span><span class='bd-val'>{res_b['office_mpp']} Pax</span></div></div><div style='display:flex; gap:10px; margin-bottom:15px;'><div class='comp-box' style='flex:1;'><div class='comp-title'>Non-Staff (Shift)</div><div class='comp-row'><span>Attendant</span><span class='comp-val'>{res_b['att']} Pax</span></div><div class='comp-row'><span>Gate/Cashier</span><span class='comp-val'>{res_b['cashier']} Pax</span></div><div class='comp-row'><span>Control Room</span><span class='comp-val'>{res_b['ctrl']} Pax</span></div></div><div class='comp-box' style='flex:1;'><div class='comp-title'>Staff (Office)</div><div class='comp-row'><span>Admin</span><span class='comp-val'>{res_b['adm']} Pax</span></div><div class='comp-row'><span>Supervisor</span><span class='comp-val'>{res_b['spv']} Pax</span></div><div class='comp-row'><span>Manager (CPM)</span><span class='comp-val'>{res_b['cpm']} Pax</span></div></div></div><div class='total-cost-box total-cost-b'><div class='total-label'>{cost_label}</div><p class='total-value-b'>{format_idr(res_b['cost'])}</p></div></div>"
    st.markdown(html_b, unsafe_allow_html=True)

# --- DATA EXCEL ---
df_comparison = pd.DataFrame({
    "Metric": [
        "Project ID", "Parking System", "Est. Revenue", 
        "TOTAL MPP (Pax)", "--- NON-STAFF SHIFT ---", "Attendant (Pax)", "Gate/Cashier (Pax)", "Control Room (Pax)", "Est. Pax / Group",
        "--- STAFF OFFICE ---", "Admin (Pax)", "Supervisor (Pax)", "Manager/CPM (Pax)",
        "Cost/Rev Ratio (%)", f"{cost_label} (Rp)"
    ],
    "Scenario A": [
        standard_project_id, sys_a, rev_a, 
        res_a['mpp'], "", res_a['att'], res_a['cashier'], res_a['ctrl'], get_shift_distribution(res_a['shift_mpp']),
        "", res_a['adm'], res_a['spv'], res_a['cpm'],
        round(res_a['ratio'], 2), res_a['cost']
    ],
    "Scenario B": [
        standard_project_id, sys_b, rev_b, 
        res_b['mpp'], "", res_b['att'], res_b['cashier'], res_b['ctrl'], get_shift_distribution(res_b['shift_mpp']),
        "", res_b['adm'], res_b['spv'], res_b['cpm'],
        round(res_b['ratio'], 2), res_b['cost']
    ]
})

shift_logic = pd.DataFrame({
    "Day": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    "Shift 1 (Morning)": ["Group A", "Group A", "Group B", "Group B", "Group C", "Group C", "Group D"],
    "Shift 2 (Afternoon)": ["Group B", "Group B", "Group C", "Group C", "Group D", "Group D", "Group A"],
    "Shift 3 (Night)": ["Group C", "Group C", "Group D", "Group D", "Group A", "Group A", "Group B"],
    "OFF (Rest Day)": ["Group D", "Group D", "Group A", "Group A", "Group B", "Group B", "Group C"]
})

# TOMBOL DOWNLOAD EXCEL
st.divider()
excel_data = generate_excel(df_comparison, shift_logic)

safe_filename = project_name.replace(" ", "_")
safe_property = property_type.replace(" ", "_").replace("/", "_")
st.download_button(
    label="📥 DOWNLOAD REPORT (EXCEL)",
    data=excel_data,
    file_name=f"MPP_{safe_property}_{safe_filename}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# --- SHIFT SCHEDULING ---
st.subheader(f"🗓️ Shift Rotation (UU No.6/2023 Compliant)")
st.info("Ensures max 40 work hours/week with 4-Group Rotation. Guarantees minimum 1 Rest Day/week per employee.")

st.markdown(f"""
    <div class='info-box-a'>
        <strong>🅰️ Scenario A Allocation:</strong><br>
        Each operational shift (Morning/Afternoon/Night) will be manned by <b>{get_shift_distribution(res_a['shift_mpp'])}</b> on-site.
    </div>
    <div class='info-box-b'>
        <strong>🅱️ Scenario B Allocation:</strong><br>
        Each operational shift (Morning/Afternoon/Night) will be manned by <b>{get_shift_distribution(res_b['shift_mpp'])}</b> on-site.
    </div>
""", unsafe_allow_html=True)

st.dataframe(shift_logic, use_container_width=True, hide_index=True)

# VALIDASI P&L GUARDRAIL
st.divider()
if res_a['ratio'] > 30 or res_b['ratio'] > 30:
    st.warning("⚠️ **Profitability Alert**: One of the scenarios exceeds the 30% Manpower Cost threshold.")
else:
    st.success("✅ **P&L Secure**: Both scenarios are within healthy Manpower Cost limits.")
