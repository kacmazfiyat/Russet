import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import numpy as np
import time
from datetime import datetime

st.set_page_config(page_title="Pazaryeri Fiyat Motoru v51", layout="wide")

# --- KORUMA FONKSİYONLARI ---
def prepare_for_gsheets(value):
    """Veriyi Google Sheets'in reddetmeyeceği hale getirir (NaN ve Karışık Objeler için)."""
    if pd.isna(value) or value is None or str(value).lower() in ["nan", "inf", "-inf"]:
        return ""
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, (int, float)):
        return float(value)
    return str(value).strip()

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

# --- VERİ BAĞLANTISI ---
try:
    client = get_gsheet_client()
    sh = client.open("Pazaryeri_Veritabani")
    ws_prod = sh.worksheet("Products")
    ws_set = sh.worksheet("Settings")
    try:
        ws_back = sh.worksheet("Backup")
    except:
        ws_back = sh.add_worksheet(title="Backup", rows="1000", cols="6")
        ws_back.append_row(["Tarih", "urun_adi", "boy", "maliyet", "doviz", "sayfa_adi"])
except Exception as e:
    st.error(f"Bağlantı Hatası: {e}")
    st.stop()

# --- MENÜ ---
menu = st.sidebar.radio("Menü", ["🔍 Arama & Düzenle", "⚙️ Ayarlar", "📥 Veri Yükle & Temizle & Backup"])

# --- 1. VERİ YÜKLEME, TEMİZLEME VE BACKUP ---
if menu == "📥 Veri Yükle & Temizle & Backup":
    st.subheader("📥 Veritabanı Yönetim Paneli")

    # A) VERİTABANINI SİL (Söz verdiğim gibi buradadır)
    with st.expander("🗑️ Veritabanını Tamamen Sil"):
        st.error("DİKKAT: 'Products' sayfasındaki tüm ürünleri siler.")
        del_confirm = st.text_input("Onaylamak için (sil) yazın:", key="del_final")
        if st.button("Sistemi Sıfırla"):
            if del_confirm.lower() == "sil":
                ws_prod.clear()
                ws_prod.append_row(["urun_adi", "boy", "maliyet", "doviz", "sayfa_adi"])
                st.success("✅ Tüm ürünler silindi. Sistem tertemiz!")
                time.sleep(2)
                st.rerun()
            else:
                st.warning("Lütfen kutucuğa 'sil' yazın.")

    st.divider()

    # B) BACKUP GERİ YÜKLEME
    with st.expander("⏪ Yedekten Geri Dön"):
        back_df = pd.DataFrame(ws_back.get_all_records())
        if not back_df.empty:
            dates = sorted(back_df['Tarih'].unique().tolist(), reverse=True)
            selected_date = st.selectbox("Bir yedek noktası seçin:", dates)
            if st.button("Yedeği Geri Getir"):
                restore_list = back_df[back_df['Tarih'] == selected_date].drop(columns=['Tarih']).values.tolist()
                ws_prod.clear()
                ws_prod.append_row(["urun_adi", "boy", "maliyet", "doviz", "sayfa_adi"])
                ws_prod.append_rows(restore_list)
                st.success(f"✅ {selected_date} tarihli yedeğe geri dönüldü!")
                time.sleep(2)
                st.rerun()

    st.divider()

    # C) EXCEL YÜKLEME
    st.write("### 📤 Yeni Excel Yükle")
    file = st.file_uploader("Dosya Seç", type=['xlsx'])
    if file and st.button("Önce Yedekle Sonra Yükle"):
        with st.spinner("Güvenli aktarım yapılıyor..."):
            # 1. Mevcut olanı yedekle (Hata korumalı)
            current_raw = ws_prod.get_all_records()
            if current_raw:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                clean_backup = [[ts] + [prepare_for_gsheets(v) for v in row.values()] for row in current_raw]
                ws_back.append_rows(clean_backup)

            # 2. Excel'i oku
            xls = pd.ExcelFile(file)
            all_rows = []
            for sheet in xls.sheet_names:
                df = pd.read_excel(file, sheet_name=sheet, header=None)
                p_col, n_col, s_col = -1, -1, -1
                for i in range(min(20, len(df))):
                    row_vals = [str(v).upper().strip() for v in df.iloc[i].values]
                    if any(x in row_vals for x in ["MALZEME ADI", "ÜRÜN ADI", "AÇIKLAMA"]):
                        n_col = next(idx for idx, v in enumerate(row_vals) if v in ["MALZEME ADI", "ÜRÜN ADI", "AÇIKLAMA"])
                    if any(x in row_vals for x in ["BOY", "ÖLÇÜ", "EBAT"]):
                        s_col = next(idx for idx, v in enumerate(row_vals) if v in ["BOY", "ÖLÇÜ", "EBAT"])
                    if "BİRİM FİYATI" in row_vals: p_col = row_vals.index("BİRİM FİYATI")

                if n_col != -1 and p_col != -1:
                    for _, row in df.iloc[i+1:].iterrows():
                        name = prepare_for_gsheets(row[n_col])
                        if not name: continue
                        size = prepare_for_gsheets(row[s_col]) if s_col != -1 else "-"
                        price = safe_float(row[p_col])
                        cur_raw = str(row[p_col+1]).upper() if len(row) > p_col+1 else "TL"
                        d_tipi = "EUR" if "EUR" in cur_raw or "€" in cur_raw else ("USD" if "USD" in cur_raw or "$" in cur_raw else "TL")
                        all_rows.append([name, size, price, d_tipi, sheet])
            
            if all_rows:
                ws_prod.append_rows(all_rows, value_input_option='RAW')
                st.success(f"✅ {len(all_rows)} ürün başarıyla eklendi.")

# --- 2. AYARLAR ---
elif menu == "⚙️ Ayarlar":
    st.subheader("⚙️ Platform Ayarları")
    # (Önceki stabil Ayarlar kodu: Komisyon, Kargo, Kur girişleri)
    # st.form("settings_form") yapısı burada devam eder...

# --- 3. ARAMA ---
elif menu == "🔍 Arama & Düzenle":
    st.subheader("🔍 Ürün Arama")
    p_df = pd.DataFrame(ws_prod.get_all_records())
    if not p_df.empty:
        search = st.text_input("Ürün İsmi Yazın...")
        filtered = p_df[p_df['urun_adi'].astype(str).str.contains(search, case=False)]
        st.dataframe(filtered, use_container_width=True)