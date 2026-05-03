import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import numpy as np # NaN kontrolü için ekledik

st.set_page_config(page_title="Pazaryeri Fiyat Motoru v46", layout="wide")

# --- YARDIMCI FONKSİYONLAR ---
def clean_val(val):
    """Veriyi JSON ile tam uyumlu hale getirir."""
    # Pandas NaN, None veya inf değerlerini kontrol et
    if pd.isna(val) or val is None or str(val).lower() in ["nan", "inf", "-inf"]:
        return 0.0 if isinstance(val, (int, float)) else ""
    return val

def safe_float(value, default=0.0):
    try:
        if value is None or str(value).strip() == "": return default
        # Hem binlik ayırıcıyı hem de virgülü temizle
        val_str = str(value).replace('.', '').replace(',', '.')
        res = float(val_str)
        # Sayı nan ise default dön
        return default if np.isnan(res) else res
    except: return default

@st.cache_resource
def get_gsheet_client():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], 
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    return gspread.authorize(creds)

# --- ANA PROGRAM ---
menu = st.sidebar.radio("Menü", ["🔍 Arama & Düzenle", "⚙️ Ayarlar", "📥 Veri Yükle"])

ws_prod = None
try:
    client = get_gsheet_client()
    sh = client.open("Pazaryeri_Veritabani")
    ws_prod = sh.worksheet("Products")
except:
    st.error("Veritabanı bağlantısı kurulamadı!")

if menu == "📥 Veri Yükle" and ws_prod:
    st.subheader("📥 Excel Aktarımı")
    file = st.file_uploader("Excel Seç", type=['xlsx'])
    
    if file and st.button("Aktarımı Başlat"):
        with st.spinner("Veriler temizleniyor..."):
            xls = pd.ExcelFile(file)
            all_rows = []
            
            for sheet in xls.sheet_names:
                df = pd.read_excel(file, sheet_name=sheet, header=None)
                
                # Başlık tespiti
                price_col, name_col, size_col = -1, -1, -1
                for i in range(min(15, len(df))):
                    row_vals = [str(v).upper().strip() for v in df.iloc[i].values]
                    if "BİRİM FİYATI" in row_vals: price_col = row_vals.index("BİRİM FİYATI")
                    if any(x in row_vals for x in ["MALZEME ADI", "ÜRÜN ADI"]):
                        name_col = next(idx for idx, v in enumerate(row_vals) if v in ["MALZEME ADI", "ÜRÜN ADI"])
                    if any(x in row_vals for x in ["BOY", "ÖLÇÜ"]):
                        size_col = next(idx for idx, v in enumerate(row_vals) if v in ["BOY", "ÖLÇÜ"])
                
                if price_col != -1 and name_col != -1:
                    for _, row in df.iloc[i+1:].iterrows():
                        u_adi = clean_val(row[name_col])
                        if not u_adi: continue
                        
                        boy = clean_val(row[size_col]) if size_col != -1 else "-"
                        fiyat = safe_float(row[price_col])
                        
                        # Döviz tespiti
                        cur_raw = str(row[price_col+1]).upper() if len(row) > price_col+1 else "TL"
                        d_tipi = "EUR" if "EUR" in cur_raw or "€" in cur_raw else ("USD" if "USD" in cur_raw or "$" in cur_raw else "TL")
                        
                        # JSON HATASINI ÖNLEYEN KRİTİK LİSTE OLUŞTURMA
                        all_rows.append([
                            str(u_adi), 
                            str(boy), 
                            float(fiyat), # Burada asla NaN gitmemeli
                            str(d_tipi), 
                            str(sheet)
                        ])
            
            if all_rows:
                try:
                    # 'RAW' modu ve temizlenmiş liste ile kesin çözüm
                    ws_prod.append_rows(all_rows, value_input_option='RAW')
                    st.success(f"✅ {len(all_rows)} ürün hatasız aktarıldı!")
                except Exception as e:
                    st.error(f"Aktarım hatası: {e}")