import streamlit as st
import pandas as pd
import math
from io import BytesIO

# --- 1. SaaS UI STYLING (NAVY BLUE & RESPONSIVE) ---
st.set_page_config(page_title="CP CorePlanner", page_icon="🅿️", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    section[data-testid="stSidebar"] { background-color: #004a99; color: white; }
    section[data-testid="stSidebar"] * { color: white !important; }
    
    .metric-card {
        background-color: #ffffff; padding: 15px; border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-left: 5px solid #004a99;
        margin-bottom: 10px;
    }
    .metric-label { font-size: 0.8rem; color: #004a99; font-weight: 700; text-transform: uppercase; }
    .metric-value { font-size: 1.1rem; color: #1e293b; font-weight: 800; }

    .scenario-box {
        background-color: #ffffff; padding: 20px; border-radius: 15px;
        border-top: 5px solid #004a99; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 20px; height: 100%;
    }
    
    div.stButton > button {
        background-color: #004a99 !important; color: white !important;
        border-radius: 8px !important; font-weight: bold !important; width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CORE COMPLIANCE ENGINE ---
class ComplianceEngine:
    def __init__(self, umk):
        self.umk = umk
        self.fixed_overhead = 500000 
        self.bpjs_thr_uuck = 0.0624 + 0.0833 + 0.0833

    def get_cost(self, count, allowance=0):
        if count <= 0: return 0
        gp_plus_tunj = self.umk * (1 + allowance)
        return (gp_plus_tunj * (1 + self.bpjs_thr_uuck) + self.fixed_overhead) * count

    def calculate(self, sys, g_in, g_out, c_mob, c_mot, hours, rev):
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
        
        cost_total = self.get_cost(cashier + ctrl + att, 0) + \
                     self.get_cost(adm, 0.15) + self.get_cost(spv, 0.20) + \
                     self.get_cost(cpm, 0.25)
        
        return {"mpp": cashier+ctrl+att+spv+adm+cpm, "ratio": (cost_total/rev)*100 if rev > 0 else 0, "cost": cost_total}

# --- FUNGSI DOWNLOAD EXCEL ---
def generate_excel(df_comparison, df_shift):
    output = BytesIO()
    # Menggunakan xlsxwriter untuk bisa memanipulasi lebar kolom
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_comparison.to_excel(writer, sheet_name='Perbandingan Skenario', index=False)
        df_shift.to_excel(writer, sheet_name='Jadwal Shift', index=False)
        
        workbook = writer.book
        worksheet1 = writer.sheets['Perbandingan Skenario']
        worksheet2 = writer.sheets['Jadwal Shift']
        
        # Format angka (Accounting/Rupiah)
        money_format = workbook.add_format({'num_format': '#,##0'})
        
        # Autofit Kolom Sheet 1
        for i, col in enumerate(df_comparison.columns):
            column_len = max(df_comparison[col].astype(str).map(len).max(), len(col)) + 2
            # Terapkan format angka jika nama kolom mengandung "Cost" atau "Revenue"
            if "Cost" in col or "Revenue" in col:
                worksheet1.set_column(i, i, column_len, money_format)
            else:
                worksheet1.set_column(i, i, column_len)
                
        # Autofit Kolom Sheet 2
        for i, col in enumerate(df_shift.columns):
            column_len = max(df_shift[col].astype(str).map(len).max(), len(col)) + 2
            worksheet2.set_column(i, i, column_len)
            
    return output.getvalue()

# --- 3. UI DASHBOARD ---
st.title("🛡️ CP CorePlanner v2.5")
st.markdown("Automated Shift Compliance & Rest-Day Logic")

with st.sidebar:
    st.header("📍 Base Configuration")
    umk = st.number_input("Regional UMK (Rp)", value=5729876)
    hours = st.slider("Operating Hours", 16, 24, 24)
    st.divider()
    c_g1, c_g2 = st.columns(2)
    with c_g1:
        g_in = st.number_input("Gate IN", value=3)
        c_mob = st.number_input("Cap Mobil", value=300)
    with c_g2:
        g_out = st.number_input("Gate OUT", value=3)
        c_mot = st.number_input("Cap Motor", value=200)

eng = ComplianceEngine(umk)

# WHAT-IF COMPARISON (Sekarang Reaktif & Langsung Tampil)
st.subheader("💡 What-If Scenario Comparison")
col_a, col_b = st.columns(2)

with col_a:
    st.markdown("<div class='scenario-box'>", unsafe_allow_html=True)
    st.subheader("🅰️ Skenario A")
    sys_a = st.selectbox("Sistem A", ['Manual', 'Semi-Auto', 'Full Manless'], key="sys_a")
    rev_a = st.number_input("Revenue A (Rp)", value=150000000, key="rev_a")
    res_a = eng.calculate(sys_a, g_in, g_out, c_mob, c_mot, hours, rev_a)
    
    st.markdown(f"""
        <div style='display:flex; gap:10px; margin-bottom:15px;'>
            <div class='metric-card' style='flex:1'><div class='metric-label'>MPP</div><div class='metric-value'>{res_a['mpp']} Pax</div></div>
            <div class='metric-card' style='flex:1'><div class='metric-label'>Ratio</div><div class='metric-value'>{res_a['ratio']:.2f}%</div></div>
        </div>
    """, unsafe_allow_html=True)
    st.write(f"**Total Cost: Rp {res_a['cost']:,.0f}**".replace(",","."))
    st.markdown("</div>", unsafe_allow_html=True)

with col_b:
    st.markdown("<div class='scenario-box'>", unsafe_allow_html=True)
    st.subheader("🅱️ Skenario B")
    sys_b = st.selectbox("Sistem B", ['Manual', 'Semi-Auto', 'Full Manless'], index=2, key="sys_b")
    rev_b = st.number_input("Revenue B (Rp)", value=250000000, key="rev_b")
    res_b = eng.calculate(sys_b, g_in, g_out, c_mob, c_mot, hours, rev_b)
    
    st.markdown(f"""
        <div style='display:flex; gap:10px; margin-bottom:15px;'>
            <div class='metric-card' style='flex:1'><div class='metric-label'>MPP</div><div class='metric-value'>{res_b['mpp']} Pax</div></div>
            <div class='metric-card' style='flex:1'><div class='metric-label'>Ratio</div><div class='metric-value'>{res_b['ratio']:.2f}%</div></div>
        </div>
    """, unsafe_allow_html=True)
    st.write(f"**Total Cost: Rp {res_b['cost']:,.0f}**".replace(",","."))
    st.markdown("</div>", unsafe_allow_html=True)

# --- SIAPKAN DATA UNTUK EXCEL ---
df_comparison = pd.DataFrame({
    "Metrik": ["Sistem", "Revenue", "MPP (Pax)", "Ratio Cost/Rev (%)", "Total Cost (Rp)"],
    "Skenario A": [sys_a, rev_a, res_a['mpp'], round(res_a['ratio'], 2), res_a['cost']],
    "Skenario B": [sys_b, rev_b, res_b['mpp'], round(res_b['ratio'], 2), res_b['cost']]
})

shift_logic = pd.DataFrame({
    "Hari": ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"],
    "Shift 1 (Pagi)": ["Grup A", "Grup A", "Grup B", "Grup B", "Grup C", "Grup C", "Grup D"],
    "Shift 2 (Siang)": ["Grup B", "Grup B", "Grup C", "Grup C", "Grup D", "Grup D", "Grup A"],
    "Shift 3 (Malam)": ["Grup C", "Grup C", "Grup D", "Grup D", "Grup A", "Grup A", "Grup B"],
    "OFF (LIBUR)": ["Grup D", "Grup D", "Grup A", "Grup A", "Grup B", "Grup B", "Grup C"]
})

# TOMBOL DOWNLOAD EXCEL
st.divider()
excel_data = generate_excel(df_comparison, shift_logic)
st.download_button(
    label="📥 Download Hasil Analisis (Excel)",
    data=excel_data,
    file_name="Manpower_Planning_Report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# SHIFT SCHEDULING WITH AUTOMATIC OFF DAYS
st.subheader(f"🗓️ Penjadwalan Kerja Mingguan (Rest Day Automator)")
st.info("Pola rotasi ini memastikan setiap karyawan memiliki minimal 1 hari LIBUR (OFF) dalam seminggu sesuai UU Ketenagakerjaan.")
st.dataframe(shift_logic, use_container_width=True, hide_index=True)

# VALIDASI P&L GUARDRAIL
st.divider()
if res_a['ratio'] > 30 or res_b['ratio'] > 30:
    st.warning("⚠️ **Profitability Alert**: Salah satu skenario melebihi ambang batas biaya SDM 30%.")
else:
    st.success("✅ **P&L Secure**: Kedua skenario berada dalam batas biaya SDM yang sehat.")
