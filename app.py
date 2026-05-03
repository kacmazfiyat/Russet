import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import re
import json

st.set_page_config(page_title="Pazaryeri Fiyat Motoru v45", layout="wide")

# --- YARDIMCI FONKSİYONLAR ---
def clean_for_json(val):
    """Veriyi Google Sheets'in kabul edeceği temiz bir formata sokar."""
    if pd.isna(val) or str(val).lower() == "nan":
        return ""
    # Eğer veri bir tarih ise stringe çevir
    if hasattr(val, 'isoformat'):
        return val.isoformat()
    return val

def safe_float(value, default=0.0):
    try:
        if value is None or str(value).strip() == "": return default
        # Virgüllü sayıları noktaya çevirerek temizle
        val_str = str(value).replace('.', '').replace(',', '.')
        return float(val_str)
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
    if menu == "📥 Veri Yükle":
        st.subheader("📥 Veri Yükleme")
        
        file = st.file_uploader("Excel Dosyası Seçin (.xlsx)", type=['xlsx'])
        
        if file:
            if st.button("Aktarımı Başlat"):
                with st.spinner("Veriler JSON uyumlu hale getiriliyor ve aktarılıyor..."):
                    xls = pd.ExcelFile(file)
                    all_rows = []
                    for sheet_name in xls.sheet_names:
                        df = pd.read_excel(file, sheet_name=sheet_name, header=None)
                        
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
                                raw_name = clean_for_json(row[name_col])
                                if not raw_name or str(raw_name).upper() == "NAN": continue
                                
                                boy_val = clean_for_json(row[size_col]) if size_col != -1 else "-"
                                fiyat = safe_float(row[price_col])
                                
                                cur_raw = str(row[price_col+1]).upper() if len(row) > price_col+1 else "TL"
                                d_tipi = "EUR" if "EUR" in cur_raw or "€" in cur_raw else ("USD" if "USD" in cur_raw or "$" in cur_raw else "TL")
                                
                                # KRİTİK: Her bir hücreyi JSON dostu hale getiriyoruz
                                row_to_append = [
                                    str(raw_name), 
                                    str(boy_val), 
                                    fiyat, 
                                    str(d_tipi), 
                                    str(sheet_name)
                                ]
                                all_rows.append(row_to_append)
                    
                    if all_rows:
                        try:
                            # Hata veren kısım burasıydı, artık temizlenmiş liste gönderiliyor
                            ws_prod.append_rows(all_rows, value_input_option='RAW')
                            st.success(f"✅ {len(all_rows)} ürün başarıyla aktarıldı!")
                        except Exception as upload_error:
                            st.error(f"Aktarım sırasında hata: {upload_error}")