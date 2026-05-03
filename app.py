import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import re

st.set_page_config(page_title="Pazaryeri Fiyat Motoru v44", layout="wide")

# --- YARDIMCI FONKSİYONLAR ---
def safe_float(value, default=0.0):
    try:
        if value is None or str(value).strip() == "": return default
        return float(str(value).replace('.', '').replace(',', '.'))
    except: return default

@st.cache_resource
def get_gsheet_client():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], 
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    return gspread.authorize(creds)

def get_data(sheet_name):
    try:
        client = get_gsheet_client()
        sh = client.open("Pazaryeri_Veritabani")
        return sh.worksheet(sheet_name)
    except: return None

# --- ANA PROGRAM ---
menu = st.sidebar.radio("Menü", ["🔍 Arama & Düzenle", "⚙️ Ayarlar", "📥 Veri Yükle"])

ws_prod = get_data("Products")
ws_set = get_data("Settings")

if ws_prod is None or ws_set is None:
    st.error("❌ Veritabanı bağlantı hatası!")
else:
    # --- 1. VERİ YÜKLEME VE TEMİZLEME ---
    if menu == "📥 Veri Yükle":
        st.subheader("📥 Veritabanı Yönetimi")
        
        # TEHLİKELİ ALAN: VERİTABANI TEMİZLEME
        with st.expander("⚠️ Tehlikeli Alan: Veritabanını Temizle"):
            st.warning("Bu işlem 'Products' sayfasındaki TÜM ürünleri silecektir!")
            confirm = st.text_input("Silmek için 'SİL' yazın")
            if st.button("Tüm Ürünleri Temizle"):
                if confirm == "SİL":
                    ws_prod.clear()
                    ws_prod.append_row(["urun_adi", "boy", "maliyet", "doviz", "sayfa_adi"])
                    st.success("Veritabanı tamamen temizlendi!")
                    st.rerun()
                else:
                    st.error("Lütfen onay kutusuna SİL yazın.")

        st.divider()

        # EXCEL YÜKLEME
        st.write("### Excel'den Ürün Aktar")
        file = st.file_uploader("Excel Dosyası Seçin (.xlsx)", type=['xlsx'])
        
        if file:
            if st.button("Aktarımı Başlat"):
                with st.spinner("Excel okunuyor ve buluta işleniyor..."):
                    xls = pd.ExcelFile(file)
                    all_rows = []
                    for sheet_name in xls.sheet_names:
                        df = pd.read_excel(file, sheet_name=sheet_name, header=None)
                        # Sütun tespiti (v20 mantığı)
                        price_col, name_col, size_col = -1, -1, -1
                        for i in range(min(15, len(df))):
                            row_vals = [str(val).upper().strip() for val in df.iloc[i].values]
                            if "BİRİM FİYATI" in row_vals: price_col = row_vals.index("BİRİM FİYATI")
                            if any(x in row_vals for x in ["MALZEME ADI", "ÜRÜN ADI"]):
                                name_col = next(idx for idx, v in enumerate(row_vals) if v in ["MALZEME ADI", "ÜRÜN ADI"])
                            if any(x in row_vals for x in ["BOY", "ÖLÇÜ"]):
                                size_col = next(idx for idx, v in enumerate(row_vals) if v in ["BOY", "ÖLÇÜ"])
                        
                        if price_col != -1 and name_col != -1:
                            for _, row in df.iloc[i+1:].iterrows():
                                raw_name = str(row[name_col]).strip()
                                if not raw_name or raw_name.upper() == "NAN": continue
                                
                                # Veriyi temizle ve ekle
                                boy_val = str(row[size_col]).strip() if size_col != -1 else "-"
                                fiyat = safe_float(row[price_col])
                                # Döviz tespiti
                                cur_raw = str(row[price_col+1]).upper() if len(row) > price_col+1 else "TL"
                                d_tipi = "EUR" if "EUR" in cur_raw or "€" in cur_raw else ("USD" if "USD" in cur_raw or "$" in cur_raw else "TL")
                                
                                all_rows.append([raw_name, boy_val, fiyat, d_tipi, sheet_name])
                    
                    if all_rows:
                        ws_prod.append_rows(all_rows)
                        st.success(f"✅ {len(all_rows)} ürün buluta eklendi!")
                        st.rerun()

    # --- 2. AYARLAR ---
    elif menu == "⚙️ Ayarlar":
        # (v43'teki form yapısı buraya gelecek - Submit button dahil)
        st.subheader("⚙️ Platform Ayarları")
        # ... (Önceki stabil form kodu)

    # --- 3. ARAMA & DÜZENLE ---
    elif menu == "🔍 Arama & Düzenle":
        st.subheader("🔍 Ürün Analizi")
        p_data = pd.DataFrame(ws_prod.get_all_records())
        s_data = pd.DataFrame(ws_set.get_all_records())
        
        if p_data.empty:
            st.info("Henüz ürün yüklenmemiş.")
        else:
            # (Filtreleme ve Satış Fiyatı hesaplama motoru buraya gelecek)
            st.dataframe(p_data.head(50)) # Geçici izleme