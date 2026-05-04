import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import numpy as np
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import re

st.set_page_config(page_title="Pazaryeri Fiyat Motoru v54", layout="wide")

# --- MERKEZ BANKASI KUR ÇEKME FONKSİYONU ---
def get_tcmb_rates():
    """TCMB'den anlık kurları çeker."""
    try:
        url = "https://www.tcmb.gov.tr/kurlar/today.xml"
        response = requests.get(url, timeout=5)
        tree = ET.fromstring(response.content)
        
        rates = {"USD": 33.0, "EUR": 35.5} # Hata durumunda varsayılan
        
        for currency in tree.findall('Currency'):
            code = currency.get('CurrencyCode')
            if code in ["USD", "EUR"]:
                # ForexBuying (Döviz Alış) değerini alıyoruz
                rate = currency.find('ForexBuying').text
                rates[code] = float(rate)
        return rates
    except Exception as e:
        st.error(f"Kur çekilemedi: {e}")
        return {"USD": 33.0, "EUR": 35.5}

# --- VERİ TEMİZLEME (Regex ile Boy Ayıklama) ---
def split_name_and_size(raw_name):
    """Malzeme adındaki ölçüleri (örn: 120 CM) ayıklar ve temizler."""
    raw_name = str(raw_name)
    # "120 CM", "50X100 CM" gibi kalıpları arar
    match = re.search(r'(\d+.*CM)', raw_name, re.IGNORECASE)
    if match:
        boy = match.group(1).strip()
        # Malzeme adından boy kısmını sil
        clean_name = raw_name.replace(match.group(0), "").strip()
        return clean_name, boy
    return raw_name, "-"

# --- KORUMA VE YARDIMCI FONKSİYONLAR ---
def prepare_for_gsheets(value):
    if pd.isna(value) or value is None or str(value).lower() in ["nan", "inf", "-inf"]:
        return ""
    return str(value).strip()

def safe_float(value, default=0.0):
    try:
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
except Exception as e:
    st.error("Bağlantı Hatası!"); st.stop()

# --- MENÜ ---
menu = st.sidebar.radio("Menü", ["🔍 Arama & Düzenle", "⚙️ Ayarlar", "📥 Veri Yükle & Temizle"])

# --- 1. AYARLAR (TCMB DESTEKLİ) ---
if menu == "⚙️ Ayarlar":
    st.subheader("⚙️ Platform ve Kur Ayarları")
    
    # Manuel Kur Güncelleme Butonu
    if st.button("🔄 Merkez Bankasından Kurları Çek"):
        rates = get_tcmb_rates()
        st.session_state.usd_rate = rates["USD"]
        st.session_state.eur_rate = rates["EUR"]
        st.success(f"Kurlar Güncellendi! USD: {rates['USD']} | EUR: {rates['EUR']}")

    # Veritabanından mevcut ayarları al
    s_df = pd.DataFrame(ws_set.get_all_records())
    plats = ["Trendyol", "Hepsiburada", "Amazon", "N11"]
    sel_p = st.selectbox("Platform Seç", plats)
    
    current = s_df[s_df['platform'] == sel_p].iloc[0].to_dict() if not s_df.empty and sel_p in s_df['platform'].values else {}

    with st.form("settings_form"):
        col1, col2 = st.columns(2)
        kom = col1.number_input("Komisyon (%)", value=safe_float(current.get('komisyon', 20.0)))
        kar = col2.number_input("Hedef Kâr (%)", value=safe_float(current.get('kar', 20.0)))
        kargo = col1.number_input("Kargo (TL)", value=safe_float(current.get('kargo', 85.0)))
        hizmet = col2.number_input("Hizmet (TL)", value=safe_float(current.get('hizmet', 15.0)))
        
        # Eğer session_state'de kur varsa onu kullan, yoksa veritabanındakini
        eur_val = st.session_state.get('eur_rate', safe_float(current.get('eur', 35.50)))
        usd_val = st.session_state.get('usd_rate', safe_float(current.get('usd', 33.00)))
        
        eur_k = col1.number_input("EURO Kuru", value=eur_val)
        usd_k = col2.number_input("USD Kuru", value=usd_val)
        
        if st.form_submit_button("Ayarları Kaydet"):
            new_row = [sel_p, kom, kargo, hizmet, kar, 20, 0, eur_k, usd_k]
            try:
                cell = ws_set.find(sel_p)
                ws_set.update(f"A{cell.row}:I{cell.row}", [new_row])
            except: ws_set.append_row(new_row)
            st.success("Ayarlar başarıyla kaydedildi!")

# --- 2. VERİ YÜKLEME (AKILLI AYIKLAMA) ---
elif menu == "📥 Veri Yükle & Temizle":
    st.subheader("📥 Veritabanı Yönetimi")
    
    with st.expander("🗑️ Veritabanını Temizle"):
        if st.text_input("Silmek için (sil) yazın:") == "sil":
            if st.button("Hepsini Sil"):
                ws_prod.clear(); ws_prod.append_row(["urun_adi", "boy", "maliyet", "doviz", "sayfa_adi"])
                st.rerun()

    file = st.file_uploader("Excel Yükle", type=['xlsx'])
    if file and st.button("Akıllı Ayrıştırma ile Yükle"):
        xls = pd.ExcelFile(file)
        all_rows = []
        for sheet in xls.sheet_names:
            df = pd.read_excel(file, sheet_name=sheet, header=None)
            # ... (Başlık tespit kodları buraya gelecek - n_col, p_col vb.)
            # Örnek döngü içi akıllı ayıklama:
            for _, row in df.iloc[1:].iterrows():
                raw_name = str(row[0])
                # BURASI ÖNEMLİ: Adı ve Boyu ayırıyoruz
                clean_name, extracted_boy = split_name_and_size(raw_name)
                
                all_rows.append([clean_name, extracted_boy, safe_float(row[2]), "TL", sheet])
        
        if all_rows:
            ws_prod.append_rows(all_rows, value_input_option='RAW')
            st.success(f"{len(all_rows)} ürün ayıklanarak yüklendi!")