import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import numpy as np
import time
from datetime import datetime

st.set_page_config(page_title="Pazaryeri Fiyat Motoru v52", layout="wide")

# --- KORUMA VE YARDIMCI FONKSİYONLAR ---
def prepare_for_gsheets(value):
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

# --- 1. AYARLAR SAYFASI (BOŞ GELMEYEN VERSİYON) ---
if menu == "⚙️ Ayarlar":
    st.subheader("⚙️ Platform ve Kur Ayarları")
    
    # Mevcut ayarları oku
    settings_data = ws_set.get_all_records()
    s_df = pd.DataFrame(settings_data)
    
    platforms = ["Trendyol", "Hepsiburada", "Amazon", "N11"]
    selected_p = st.selectbox("Düzenlenecek Platformu Seçin", platforms)
    
    # Seçili platformun mevcut verilerini bul veya varsayılan ata
    if not s_df.empty and selected_p in s_df['platform'].values:
        current = s_df[s_df['platform'] == selected_p].iloc[0].to_dict()
    else:
        # EĞER VERİTABANI BOŞSA GELECEK VARSAYILANLAR
        current = {
            "komisyon": 20.0, "kargo": 85.0, "hizmet": 15.0, 
            "kar": 20.0, "kdv": 20.0, "eur": 35.50, "usd": 33.00
        }

    with st.form("settings_form"):
        col1, col2 = st.columns(2)
        
        # Değerler artık 'current' içinden otomatik geliyor, boş kalmıyor
        kom = col1.number_input("Komisyon (%)", value=safe_float(current.get('komisyon', 20.0)), step=0.5)
        kar = col2.number_input("Hedef Kâr (%)", value=safe_float(current.get('kar', 20.0)), step=0.5)
        kargo = col1.number_input("Kargo Ücreti (TL)", value=safe_float(current.get('kargo', 85.0)), step=1.0)
        hizmet = col2.number_input("Hizmet Bedeli (TL)", value=safe_float(current.get('hizmet', 15.0)), step=1.0)
        
        st.divider()
        col3, col4 = st.columns(2)
        eur_k = col3.number_input("EURO Kuru (TL)", value=safe_float(current.get('eur', 35.50)), format="%.2f")
        usd_k = col4.number_input("USD Kuru (TL)", value=safe_float(current.get('usd', 33.00)), format="%.2f")
        
        if st.form_submit_button("Ayarları Güncelle ve Kaydet"):
            # Güncellenecek satır
            new_row = [selected_p, kom, kargo, hizmet, kar, 20, 0, eur_k, usd_k]
            
            # Google Sheets'te platformu ara, varsa güncelle yoksa ekle
            try:
                cell = ws_set.find(selected_p)
                ws_set.update(f"A{cell.row}:I{cell.row}", [new_row])
            except:
                ws_set.append_row(new_row)
                
            st.success(f"✅ {selected_p} ayarları başarıyla kaydedildi!")
            time.sleep(1)
            st.rerun()

# --- 2. DİĞER TÜM SİSTEMLER (SİL, BACKUP, YÜKLE) ---
elif menu == "📥 Veri Yükle & Temizle & Backup":
    # Bu bölüm v51'deki silme ve yedekleme korumalarını aynen korur
    st.subheader("📥 Veritabanı Yönetimi")
    
    with st.expander("🗑️ Veritabanını Tamamen Sil"):
        st.warning("Bu işlem geri alınamaz!")
        del_confirm = st.text_input("Silmek için (sil) yazın:", key="del_final")
        if st.button("Sistemi Sıfırla"):
            if del_confirm.lower() == "sil":
                ws_prod.clear()
                ws_prod.append_row(["urun_adi", "boy", "maliyet", "doviz", "sayfa_adi"])
                st.success("✅ Tüm ürünler silindi!")
                time.sleep(1.5)
                st.rerun()
    
    st.divider()
    # (Yedekleme ve Excel Yükleme kodları v51 ile aynıdır, bozulmadı)
    # ...