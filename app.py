import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import numpy as np
import time
from datetime import datetime

st.set_page_config(page_title="Pazaryeri Fiyat Motoru v53", layout="wide")

# --- KORUMA VE YARDIMCI FONKSİYONLAR ---
def prepare_for_gsheets(value):
    """NaN ve geçersiz JSON değerlerini temizler."""
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

# --- MENÜ SİSTEMİ ---
menu = st.sidebar.radio("Menü", ["🔍 Arama & Düzenle", "⚙️ Ayarlar", "📥 Veri Yükle & Temizle & Backup"])

# --- 1. VERİ YÜKLEME, TEMİZLEME VE BACKUP ---
if menu == "📥 Veri Yükle & Temizle & Backup":
    st.subheader("📥 Veritabanı Yönetim Merkezi")

    # A) UPLOAD (YÜKLEME) BÖLÜMÜ - GERİ GELDİ
    st.write("### 📤 Excel'den Ürün Yükle")
    file = st.file_uploader("Excel Dosyası Seçin (.xlsx)", type=['xlsx'])
    
    if file and st.button("Yedekle ve Aktarımı Başlat"):
        with st.spinner("Önce mevcut veriler yedekleniyor, sonra aktarılıyor..."):
            # Mevcut olanı yedekle
            current_raw = ws_prod.get_all_records()
            if current_raw:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                clean_backup = [[ts] + [prepare_for_gsheets(v) for v in row.values()] for row in current_raw]
                ws_back.append_rows(clean_backup)

            # Excel'i işle
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
                st.success(f"✅ {len(all_rows)} ürün yüklendi ve eski veriler yedeklendi!")

    st.divider()

    # B) SİL (TEMİZLEME) BÖLÜMÜ
    with st.expander("🗑️ Veritabanını Temizle"):
        st.error("Bu işlem tüm ürün listesini sıfırlar.")
        del_confirm = st.text_input("Onay için (sil) yazın:", key="del_final")
        if st.button("Hepsini Sil"):
            if del_confirm.lower() == "sil":
                ws_prod.clear()
                ws_prod.append_row(["urun_adi", "boy", "maliyet", "doviz", "sayfa_adi"])
                st.success("✅ Veritabanı sıfırlandı!")
                time.sleep(1.5)
                st.rerun()

    st.divider()

    # C) BACKUP (YEDEK) GERİ YÜKLEME
    with st.expander("⏪ Yedekten Geri Dön"):
        back_df = pd.DataFrame(ws_back.get_all_records())
        if not back_df.empty:
            dates = sorted(back_df['Tarih'].unique().tolist(), reverse=True)
            sel_date = st.selectbox("Yedek Tarihi Seçin:", dates)
            if st.button("Geri Yüklemeyi Başlat"):
                res_list = back_df[back_df['Tarih'] == sel_date].drop(columns=['Tarih']).values.tolist()
                ws_prod.clear()
                ws_prod.append_row(["urun_adi", "boy", "maliyet", "doviz", "sayfa_adi"])
                ws_prod.append_rows(res_list)
                st.success(f"✅ {sel_date} tarihli yedeğe dönüldü!")
                time.sleep(1.5)
                st.rerun()

# --- 2. AYARLAR (BOŞ GELMEYEN) ---
elif menu == "⚙️ Ayarlar":
    st.subheader("⚙️ Platform Ayarları")
    s_df = pd.DataFrame(ws_set.get_all_records())
    plats = ["Trendyol", "Hepsiburada", "Amazon", "N11"]
    sel_p = st.selectbox("Platform Seç", plats)
    
    current = s_df[s_df['platform'] == sel_p].iloc[0].to_dict() if not s_df.empty and sel_p in s_df['platform'].values else {"komisyon": 20.0, "kargo": 85.0, "hizmet": 15.0, "kar": 20.0, "eur": 35.5, "usd": 33.0}

    with st.form("set_form"):
        c1, c2 = st.columns(2)
        kom = c1.number_input("Komisyon (%)", value=safe_float(current.get('komisyon')))
        kar = c2.number_input("Kâr (%)", value=safe_float(current.get('kar')))
        kargo = c1.number_input("Kargo (TL)", value=safe_float(current.get('kargo')))
        hizmet = c2.number_input("Hizmet (TL)", value=safe_float(current.get('hizmet')))
        eur = c1.number_input("Euro Kuru", value=safe_float(current.get('eur')))
        usd = c2.number_input("Dolar Kuru", value=safe_float(current.get('usd')))
        
        if st.form_submit_button("Ayarları Kaydet"):
            row = [sel_p, kom, kargo, hizmet, kar, 20, 0, eur, usd]
            try:
                cell = ws_set.find(sel_p)
                ws_set.update(f"A{cell.row}:I{cell.row}", [row])
            except:
                ws_set.append_row(row)
            st.success("Ayarlar güncellendi!")

# --- 3. ARAMA & DÜZENLE ---
elif menu == "🔍 Arama & Düzenle":
    st.subheader("🔍 Ürün Arama")
    p_df = pd.DataFrame(ws_prod.get_all_records())
    if not p_df.empty:
        search = st.text_input("Ürün Ara...")
        filtered = p_df[p_df['urun_adi'].astype(str).str.contains(search, case=False)]
        st.dataframe(filtered, use_container_width=True)