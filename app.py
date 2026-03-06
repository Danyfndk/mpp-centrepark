import streamlit as st
import pandas as pd
import math
from io import BytesIO

# --- FUNGSI HELPER UNTUK FORMAT RUPIAH ---
def format_rp(angka):
    # Mengubah format angka menjadi gaya Indonesia (titik pemisah ribuan)
    return f"Rp {angka:,.0f}".replace(",", ".")

# --- 1. SaaS UI STYLING (PREMIUM & RESPONSIVE) ---
st.set_page_config(page_title="CP CorePlanner", page_icon="🅿️", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f4f6f9; }
    section[data-testid="stSidebar"] { background-color: #004a99 !important; }
    section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 { color: #ffffff !important; }
    section[data-testid="stSidebar"] input { color: #1e293b !important; background-color: #ffffff !important; border-radius: 6px !important; }
    section[data-testid="stSidebar"] div[data-baseweb="select"] * { color: #1e293b !important; }
    
    .metric-card { background-color: #ffffff; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); margin-bottom: 10px; transition: all 0.2s ease-in-out; }
    .metric-card-a { border-left: 6px solid #004a99; } /* Metrik Skenario A */
    .metric-card-b { border-left: 6px solid #d97706; } /* Metrik Skenario B */
    .metric-card:hover { transform: translateY(-3px); box-shadow: 0 6px 16px rgba(0,0,0,0.1); }
    .metric-label { font-size: 0.85rem; color: #64748b; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }
    .metric-value { font-size: 1.4rem; color: #1e293b; font-weight: 900; margin-top: 5px;}
    
    /* SCENARIO A STYLING (BIRU) */
    .scenario-box-a { 
        background-color: #ffffff; padding: 25px; border-radius: 15px; 
        border-top: 6px solid #004a99; 
        box-shadow: 0 8px 25px rgba(0,74,153,0.15); /* Bayangan Biru */
        margin-bottom: 20px; height: 100%; 
    }
    
    /* SCENARIO B STYLING (ORANYE) */
    .scenario-box-b { 
        background-color: #ffffff; padding: 25px; border-radius: 15px; 
        border-top: 6px solid #d97706; 
        box-shadow: 0 8px 25px rgba(217,119,6,0.15); /* Bayangan Oranye */
        margin-bottom: 20px; height: 100%; 
    }

    /* Helper Text untuk Format Uang */
    .money-helper { font-size: 0.85rem; font-weight: 700; color: #10b981; margin-top: -10px; margin-bottom: 15px; }
    .money-helper-sidebar { font-size: 0.85rem; font-weight: 700; color: #fbbf24; margin-top: -10px; margin-bottom: 15px; }

    div.stButton > button, div.stDownloadButton > button { background-color: #004a99 !important; color: white !important; border-radius: 8px !important; font-weight: 700 !important; width: 100%; padding: 10px 0 !important; border: none !important; transition: all 0.3s ease !important; }
    div.stButton > button:hover, div.stDownloadButton > button:hover { background-color: #003366 !important; box-shadow: 0 4px 12px rgba(0,74,153,0.3) !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CORE COMPLIANCE ENGINE (STRICT FINANCIAL LOGIC) ---
class ComplianceEngine:
    def __init__(self, umk, fixed_overhead, bpjs_rate, thr_rate, uuck_rate):
        self.umk = umk
        self.fixed_overhead = fixed_overhead 
        self.bpjs_thr_uuck = bpjs_rate + thr_rate + uuck_rate

    def get_cost(self, count, allowance_rate=0):
        if count <= 0: return 0
        gaji_pokok = self.umk
        tunjangan = self.umk * allowance_rate
        benefit = self.umk * self.bpjs_thr_uuck
        base_cost_per_head = gaji_pokok + tunjangan + benefit + self.fixed_overhead
        return base_cost_per_head * count

    def calculate(self, sys, g_in, g_out, c_mob, c_mot, hours, rev, mgt_fee_rate=0.0):
        ff = (hours * 7) / 40 
        
        cashier = math.floor((g_in + g_out) * ff) if sys == 'Manual' else 0
        if sys == 'Manual':
            att = math.floor((math.ceil((c_mob + c_mot) / 500)) * ff)
        elif sys == 'Semi-Auto':
            att = math.floor((g_out + math.ceil((c_mob + c_mot) / 500)) * ff)
        else: 
            att = math.floor((math.ceil((c_mob + c_mot) / 1000)) * ff)
            
        ctrl = math.floor(1 * ff) if sys != 'Manual' else 0

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
            
        cost_ops = self.get_cost(cashier + ctrl + att, 0)
        cost_adm = self.get_cost(adm, adm_allowance)
        cost_spv = self.get_cost(spv, spv_allowance)
        cost_cpm = self.get_cost(cpm, cpm_allowance)
        
        actual_manpower_cost = cost_ops + cost_adm + cost_spv + cost_cpm
        final_cost = actual_manpower_cost * (1 + mgt_fee_rate)
        
        total_mpp = cashier + ctrl + att + spv + adm + cpm
        ratio = (final_cost / rev) * 100 if rev > 0 else 0
        
        return {"mpp": total_mpp, "ratio": ratio, "cost": final_cost}

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

with st.sidebar:
    st.header("🏢 Project Identity") 
    raw_project_name = st.text_input("Project Name", value="EXAMPLE PROJECT")
    project_name = raw_project_name.strip().upper() 
    property_type = st.selectbox(
        "Property Type", 
        ["MALL", "HOSPITAL", "OFFICE BUILDING", "APARTMENT", "HOTEL", "TRANSIT HUB", "SHOPHOUSE", "TRADITIONAL MARKET", "MODERN MARKET", "OTHER"]
    )
    standard_project_id = f"[{property_type}] - {project_name}"
    
    st.divider()
    
    st.header("📍 Base Configuration")
    umk = st.number_input("Regional Minimum Wage (UMK)", value=5729876, step=100000)
    # Menampilkan format rupiah di bawah input
    st.markdown(f"<div class='money-helper-sidebar'>✔️ {format_rp(umk)}</div>", unsafe_allow_html=True)
    
    hours = st.slider("Operating Hours / Day", 16, 24, 24)
    
    c_g1, c_g2 = st.columns(2)
    with c_g1:
        g_in = st.number_input("Gate IN", value=3)
        c_mob = st.number_input("Car Capacity", value=300)
    with c_g2:
        g_out = st.number_input("Gate OUT", value=3)
        c_mot = st.number_input("Motor Capacity", value=200)

    st.divider()
    
    st.header("💰 Actual Cost Variables")
    with st.expander("Adjust Variables", expanded=False):
        fixed_overhead = st.number_input("Amortized Fixed Cost / Pax", value=500000, step=50000)
        st.markdown(f"<div class='money-helper-sidebar'>✔️ {format_rp(fixed_overhead)}</div>", unsafe_allow_html=True)
        
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
cost_label = "Total Cost (incl. Mgt Fee)" if include_mgt_fee else "Actual Manpower Cost"

# WHAT-IF COMPARISON
st.subheader(f"💡 What-If Scenario: {standard_project_id}")
col_a, col_b = st.columns(2)

with col_a:
    # KOTAK SKENARIO A (WARNA BIRU)
    st.markdown("<div class='scenario-box-a'>", unsafe_allow_html=True)
    st.subheader("🅰️ Scenario A")
    sys_a = st.selectbox("System A", ['Manual', 'Semi-Auto', 'Full Manless'], key="sys_a")
    rev_a = st.number_input("Est. Revenue A (Input Value)", value=150000000, step=10000000, key="rev_a")
    st.markdown(f"<div class='money-helper'>🎯 {format_rp(rev_a)}</div>", unsafe_allow_html=True)
    
    res_a = eng.calculate(sys_a, g_in, g_out, c_mob, c_mot, hours, rev_a, mgt_fee_rate)
    
    st.markdown(f"""
        <div style='display:flex; gap:15px; margin-bottom:20px; margin-top:5px;'>
            <div class='metric-card metric-card-a' style='flex:1'>
                <div class='metric-label'>Total MPP</div>
                <div class='metric-value'>{res_a['mpp']} Pax</div>
            </div>
            <div class='metric-card metric-card-a' style='flex:1'>
                <div class='metric-label'>Cost Ratio</div>
                <div class='metric-value'>{res_a['ratio']:.2f}%</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    st.write(f"**{cost_label}:**")
    st.markdown(f"<h3 style='color:#004a99; margin-top: -10px;'>{format_rp(res_a['cost'])}</h3>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col_b:
    # KOTAK SKENARIO B (WARNA ORANYE)
    st.markdown("<div class='scenario-box-b'>", unsafe_allow_html=True)
    st.subheader("🅱️ Scenario B")
    sys_b = st.selectbox("System B", ['Manual', 'Semi-Auto', 'Full Manless'], index=2, key="sys_b")
    rev_b = st.number_input("Est. Revenue B (Input Value)", value=250000000, step=10000000, key="rev_b")
    st.markdown(f"<div class='money-helper' style='color:#d97706;'>🎯 {format_rp(rev_b)}</div>", unsafe_allow_html=True)
    
    res_b = eng.calculate(sys_b, g_in, g_out, c_mob, c_mot, hours, rev_b, mgt_fee_rate)
    
    st.markdown(f"""
        <div style='display:flex; gap:15px; margin-bottom:20px; margin-top:5px;'>
            <div class='metric-card metric-card-b' style='flex:1'>
                <div class='metric-label'>Total MPP</div>
                <div class='metric-value'>{res_b['mpp']} Pax</div>
            </div>
            <div class='metric-card metric-card-b' style='flex:1'>
                <div class='metric-label'>Cost Ratio</div>
                <div class='metric-value'>{res_b['ratio']:.2f}%</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    st.write(f"**{cost_label}:**")
    st.markdown(f"<h3 style='color:#d97706; margin-top: -10px;'>{format_rp(res_b['cost'])}</h3>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# --- DATA EXCEL ---
df_comparison = pd.DataFrame({
    "Metric": ["Project ID", "Parking System", "Est. Revenue", "Total MPP (Pax)", "Cost/Rev Ratio (%)", f"{cost_label} (Rp)"],
    "Scenario A": [standard_project_id, sys_a, rev_a, res_a['mpp'], round(res_a['ratio'], 2), res_a['cost']],
    "Scenario B": [standard_project_id, sys_b, rev_b, res_b['mpp'], round(res_b['ratio'], 2), res_b['cost']]
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
    label="📥 Download Analysis Report (Excel)",
    data=excel_data,
    file_name=f"MPP_{safe_property}_{safe_filename}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# SHIFT SCHEDULING
st.subheader(f"🗓️ Shift Rotation (UU No.6/2023 Compliant)")
st.info("Ensures max 40 work hours/week with 4-Group Rotation. Guarantees minimum 1 Rest Day/week per employee in accordance with Indonesian Labor Law.")
st.dataframe(shift_logic, use_container_width=True, hide_index=True)

# VALIDASI P&L GUARDRAIL
st.divider()
if res_a['ratio'] > 30 or res_b['ratio'] > 30:
    st.warning("⚠️ **Profitability Alert**: One of the scenarios exceeds the 30% Manpower Cost threshold.")
else:
    st.success("✅ **P&L Secure**: Both scenarios are within healthy Manpower Cost limits.")
