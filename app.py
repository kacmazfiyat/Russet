import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import numpy as np
import time
from datetime import datetime

st.set_page_config(page_title="Pazaryeri Fiyat Motoru v49", layout="wide")

# --- YARDIMCI FONKSİYONLAR ---
def safe_float(value, default=0.0):
    try:
        if value is None or str(value).strip() == "": return default
        val_str = str(value).replace('.', '').replace(',', '.')
        res = float(val_str)
        return default if np.isnan(res) else res
    except: return default

@st.cache_resource
def get_gsheet_client():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], 
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    return gspread.authorize(creds)

# --- ANA VERİ BAĞLANTISI ---
try:
    client = get_gsheet_client()
    sh = client.open("Pazaryeri_Veritabani")
    ws_prod = sh.worksheet("Products")
    ws_set = sh.worksheet("Settings")
    # Backup sayfası yoksa oluştur
    try:
        ws_back = sh.worksheet("Backup")
    except:
        ws_back = sh.add_worksheet(title="Backup", rows="1000", cols="6")
        ws_back.append_row(["Tarih", "urun_adi", "boy", "maliyet", "doviz", "sayfa_adi"])
except Exception as e:
    st.error(f"⚠️ Bağlantı Hatası: {e}")
    st.stop()

menu = st.sidebar.radio("Menü", ["🔍 Arama & Düzenle", "⚙️ Ayarlar", "📥 Veri Yükle & Backup"])

# --- VERİ YÜKLEME & BACKUP SİSTEMİ ---
if menu == "📥 Veri Yükle & Backup":
    st.subheader("📥 Veritabanı Yönetimi & Yedekleme")
    
    # BACKUP GERİ YÜKLEME (Basit Arayüz)
    with st.expander("⏪ Yedekten Geri Dön"):
        back_data = pd.DataFrame(ws_back.get_all_records())
        if not back_data.empty:
            dates = back_data['Tarih'].unique().tolist()
            selected_date = st.selectbox("Geri dönülecek tarih/saat seçin:", dates[::-1])
            if st.button("Seçili Yedeği Geri Yükle"):
                restore_df = back_data[back_data['Tarih'] == selected_date].drop(columns=['Tarih'])
                ws_prod.clear()
                ws_prod.append_row(["urun_adi", "boy", "maliyet", "doviz", "sayfa_adi"])
                ws_prod.append_rows(restore_df.values.tolist())
                st.success(f"✅ {selected_date} tarihli yedeğe dönüldü!")
                time.sleep(2)
                st.rerun()

    st.divider()

    # EXCEL YÜKLEME (Hatalı Eşleşme Düzeltildi)
    file = st.file_uploader("Excel Dosyası (.xlsx)", type=['xlsx'])
    if file and st.button("Yedekle ve Aktarımı Başlat"):
        with st.spinner("Mevcut veri yedekleniyor ve Excel işleniyor..."):
            # 1. MEVCUT VERİYİ YEDEKLE
            current_p = ws_prod.get_all_records()
            if current_p:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                backup_list = [[ts] + list(row.values()) for row in current_p]
                ws_back.append_rows(backup_list)

            # 2. EXCEL OKUMA (Görseldeki kayma hatası düzeltildi)
            xls = pd.ExcelFile(file)
            all_rows = []
            for sheet in xls.sheet_names:
                df = pd.read_excel(file, sheet_name=sheet, header=None)
                
                # Sütun tespiti için daha hassas tarama
                price_col, name_col, size_col = -1, -1, -1
                for i in range(min(20, len(df))):
                    row_vals = [str(v).upper().strip() for v in df.iloc[i].values]
                    # MALZEME ADI tespiti (Ürün adı buraya düşmeli)
                    if any(x in row_vals for x in ["MALZEME ADI", "ÜRÜN ADI", "AÇIKLAMA"]):
                        name_col = next(idx for idx, v in enumerate(row_vals) if v in ["MALZEME ADI", "ÜRÜN ADI", "AÇIKLAMA"])
                    if any(x in row_vals for x in ["BOY", "ÖLÇÜ", "EBAT"]):
                        size_col = next(idx for idx, v in enumerate(row_vals) if v in ["BOY", "ÖLÇÜ", "EBAT"])
                    if "BİRİM FİYATI" in row_vals:
                        price_col = row_vals.index("BİRİM FİYATI")
                
                if name_col != -1 and price_col != -1:
                    for _, row in df.iloc[i+1:].iterrows():
                        u_name = str(row[name_col]).strip()
                        if u_name == "" or u_name.lower() == "nan": continue
                        
                        u_size = str(row[size_col]).strip() if size_col != -1 else "-"
                        u_price = safe_float(row[price_col])
                        
                        # Döviz tespiti
                        cur_raw = str(row[price_col+1]).upper() if len(row) > price_col+1 else "TL"
                        d_tipi = "EUR" if "EUR" in cur_raw or "€" in cur_raw else ("USD" if "USD" in cur_raw or "$" in cur_raw else "TL")
                        
                        all_rows.append([u_name, u_size, u_price, d_tipi, sheet])
            
            if all_rows:
                ws_prod.append_rows(all_rows, value_input_option='RAW')
                st.success(f"✅ {len(all_rows)} Ürün yüklendi. Eski veriler Backup sekmesine kaydedildi.")

# (🔍 Arama & Düzenle menüsü altındaki tablo gösterimini de p_df.head() yerine tam liste olarak güncel tutuyorum)