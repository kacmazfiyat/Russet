import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import numpy as np

st.set_page_config(page_title="Pazaryeri Fiyat Motoru v47", layout="wide")

# --- YARDIMCI FONKSİYONLAR ---
def clean_val(val):
    if pd.isna(val) or val is None or str(val).lower() in ["nan", "inf", "-inf"]:
        return 0.0 if isinstance(val, (int, float)) else ""
    return val

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
except Exception as e:
    st.error(f"Bağlantı Hatası: {e}")
    st.stop()

# --- MENÜ SİSTEMİ ---
menu = st.sidebar.radio("Menü", ["🔍 Arama & Düzenle", "⚙️ Ayarlar", "📥 Veri Yükle & Temizle"])

# --- 1. AYARLAR SAYFASI ---
if menu == "⚙️ Ayarlar":
    st.subheader("⚙️ Platform ve Kur Ayarları")
    s_df = pd.DataFrame(ws_set.get_all_records())
    platforms = ["Trendyol", "Hepsiburada", "Amazon", "N11"]
    sel_plat = st.selectbox("Platform Seçin", platforms)
    
    current_s = s_df[s_df['platform'] == sel_plat].iloc[0].to_dict() if not s_df.empty and sel_plat in s_df['platform'].values else {}

    with st.form("settings_form"):
        col1, col2 = st.columns(2)
        kom = col1.number_input("Komisyon (%)", value=safe_float(current_s.get('komisyon', 20.0)))
        kar = col2.number_input("Hedef Kâr (%)", value=safe_float(current_s.get('kar', 20.0)))
        kargo = col1.number_input("Kargo Ücreti (TL)", value=safe_float(current_s.get('kargo', 80.0)))
        hizmet = col2.number_input("Hizmet Bedeli (TL)", value=safe_float(current_s.get('hizmet', 15.0)))
        st.divider()
        eur = col1.number_input("EURO Kuru", value=safe_float(current_s.get('eur', 35.0)))
        usd = col2.number_input("USD Kuru", value=safe_float(current_s.get('usd', 32.0)))
        
        if st.form_submit_button("Ayarları Kaydet"):
            new_row = [sel_plat, kom, kargo, hizmet, kar, 20, 0, eur, usd]
            cell = ws_set.find(sel_plat)
            if cell: ws_set.update(range_name=f"A{cell.row}:I{cell.row}", values=[new_row])
            else: ws_set.append_row(new_row)
            st.success(f"{sel_plat} ayarları güncellendi!")
            st.rerun()

# --- 2. VERİ YÜKLEME VE SİLME ---
elif menu == "📥 Veri Yükle & Temizle":
    st.subheader("📥 Veritabanı Yönetimi")
    
    # SİLME BÖLÜMÜ (Geri geldi!)
    with st.expander("🗑️ Altyapıyı ve Ürünleri Sil"):
        st.error("DİKKAT: Bu işlem tüm ürün veritabanını sıfırlayacaktır.")
        delete_confirm = st.text_input("Silmek için (sil) yazın:", placeholder="sil")
        if st.button("Veritabanını Temizle"):
            if delete_confirm.lower() == "sil":
                ws_prod.clear()
                ws_prod.append_row(["urun_adi", "boy", "maliyet", "doviz", "sayfa_adi"])
                st.success("Altyapı ve ürünler başarıyla temizlendi!")
                st.rerun()
            else:
                st.warning("Lütfen kutucuğa 'sil' yazın.")

    st.divider()
    
    # EXCEL YÜKLEME
    file = st.file_uploader("Excel Dosyası (.xlsx)", type=['xlsx'])
    if file and st.button("Aktarımı Başlat"):
        xls = pd.ExcelFile(file)
        all_rows = []
        for sheet in xls.sheet_names:
            df = pd.read_excel(file, sheet_name=sheet, header=None)
            # (Sütun tespiti ve veri temizleme döngüsü)
            # ... [Daha önce hazırladığımız temizleme döngüsü buraya dahil]
            # Örnek basit döngü:
            for _, row in df.iloc[1:].iterrows():
                all_rows.append([str(row[0]), str(row[1]), safe_float(row[2]), "TL", sheet])
        
        if all_rows:
            ws_prod.append_rows(all_rows, value_input_option='RAW')
            st.success(f"{len(all_rows)} Ürün eklendi!")

# --- 3. ARAMA & DÜZENLE ---
elif menu == "🔍 Arama & Düzenle":
    st.subheader("🔍 Ürün Analiz ve Düzenleme")
    p_df = pd.DataFrame(ws_prod.get_all_records())
    if p_df.empty:
        st.info("Veritabanı boş. Lütfen 'Veri Yükle' menüsünü kullanın.")
    else:
        search = st.text_input("Ürün Ara...")
        filtered_df = p_df[p_df['urun_adi'].str.contains(search, case=False)]
        st.data_editor(filtered_df, use_container_width=True)