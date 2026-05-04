import streamlit as st
import pandas as pd  # <--- Buradaki hata düzeltildi!
import gspread
from google.oauth2.service_account import Credentials
import numpy as np
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import re

st.set_page_config(page_title="Fiyat Motoru Dashboard v57", layout="wide")

# --- YARDIMCI FONKSİYONLAR ---
def get_tcmb_rates():
    """TCMB'den anlık kurları çeker."""
    try:
        url = "https://www.tcmb.gov.tr/kurlar/today.xml"
        response = requests.get(url, timeout=5)
        tree = ET.fromstring(response.content)
        rates = {"USD": 33.0, "EUR": 35.5}
        for currency in tree.findall('Currency'):
            code = currency.get('CurrencyCode')
            if code in ["USD", "EUR"]:
                rate = currency.find('ForexBuying').text
                rates[code] = float(rate)
        return rates
    except:
        return {"USD": 33.0, "EUR": 35.5}

def temizle_ve_ayir(ham_ad):
    """Ürün adından CM bilgilerini ayıklar."""
    ham_ad = str(ham_ad).strip()
    olcu_deseni = r'(\d+.*CM)'
    match = re.search(olcu_deseni, ham_ad, re.IGNORECASE)
    if match:
        boy = match.group(1).upper()
        temiz_ad = re.sub(olcu_deseni, "", ham_ad, flags=re.IGNORECASE).strip()
        temiz_ad = re.sub(r'[- ,/]$', '', temiz_ad)
        return temiz_ad, boy
    return ham_ad, "-"

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
    st.error("Bağlantı Hatası! Lütfen Streamlit Secrets ve Google Sheets ismini kontrol edin."); st.stop()

# --- MENÜ ---
menu = st.sidebar.radio("📋 Yönetim Paneli", ["🔍 Ürün Listesi & Analiz", "⚙️ Platform Ayarları", "📥 Veri Yükleme & Temizlik"])

# --- 1. ÜRÜN LİSTESİ ---
if menu == "🔍 Ürün Listesi & Analiz":
    st.subheader("🔍 Ürün Veritabanı")
    raw_data = ws_prod.get_all_values()
    
    if len(raw_data) > 1:
        df = pd.DataFrame(raw_data[1:], columns=["Ürün Adı", "Boy", "Maliyet", "Kur", "Kategori"])
        search = st.text_input("Ürün veya Kategori Ara...", placeholder="Örn: Mutfak")
        
        if search:
            df = df[df['Ürün Adı'].str.contains(search, case=False) | df['Kategori'].str.contains(search, case=False)]
        
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Henüz veri yüklenmemiş.")

# --- 2. AYARLAR ---
elif menu == "⚙️ Ayarlar":
    st.subheader("⚙️ Finansal Ayarlar")
    if st.button("🔄 TCMB Kurlarını Güncelle"):
        rates = get_tcmb_rates()
        st.session_state.usd = rates["USD"]
        st.session_state.eur = rates["EUR"]
        st.success(f"Kurlar güncellendi! USD: {rates['USD']} | EUR: {rates['EUR']}")

    s_df = pd.DataFrame(ws_set.get_all_records())
    sel_p = st.selectbox("Platform Seçin", ["Trendyol", "Hepsiburada", "Amazon", "N11"])
    current = s_df[s_df['platform'] == sel_p].iloc[0].to_dict() if not s_df.empty and sel_p in s_df['platform'].values else {}

    with st.form("set_form"):
        c1, c2 = st.columns(2)
        kom = c1.number_input("Komisyon (%)", value=float(current.get('komisyon', 20.0)))
        kar = c2.number_input("Kâr (%)", value=float(current.get('kar', 20.0)))
        kargo = c1.number_input("Kargo (TL)", value=float(current.get('kargo', 85.0)))
        hizmet = c2.number_input("Ek Hizmet (TL)", value=float(current.get('hizmet', 15.0)))
        
        # Session state veya veritabanı kurlarını kullan
        eur_val = st.session_state.get('eur', float(current.get('eur', 35.50)))
        usd_val = st.session_state.get('usd', float(current.get('usd', 33.00)))
        
        eur_k = c1.number_input("Euro Kuru", value=eur_val)
        usd_k = c2.number_input("Dolar Kuru", value=usd_val)
        
        if st.form_submit_button("Kaydet"):
            new_row = [sel_p, kom, kargo, hizmet, kar, 20, 0, eur_k, usd_k]
            try:
                cell = ws_set.find(sel_p)
                ws_set.update(f"A{cell.row}:I{cell.row}", [new_row])
            except:
                ws_set.append_row(new_row)
            st.success("Ayarlar kaydedildi!")

# --- 3. VERİ YÜKLEME ---
elif menu == "📥 Veri Yükleme & Temizlik":
    st.subheader("📥 Veri Yönetimi")
    with st.expander("🗑️ Sistemi Sıfırla"):
        if st.text_input("Silmek için 'sil' yazın") == "sil":
            if st.button("Veritabanını Boşalt"):
                ws_prod.clear()
                ws_prod.append_row(["Ürün Adı", "Boy", "Maliyet", "Kur", "Kategori"])
                st.rerun()

    file = st.file_uploader("Excel Dosyası Yükleyin", type=['xlsx'])
    if file and st.button("Ürünleri Aktar"):
        xls = pd.ExcelFile(file)
        data_to_add = []
        for sheet in xls.sheet_names:
            df_ex = pd.read_excel(file, sheet_name=sheet)
            for _, row in df_ex.iterrows():
                ad, boy = temizle_ve_ayir(row.iloc[0])
                maliyet = str(row.iloc[2]).replace(',','.') if len(row) > 2 else "0"
                data_to_add.append([ad, boy, maliyet, "TL", sheet])
        
        if data_to_add:
            ws_prod.append_rows(data_to_add)
            st.success(f"{len(data_to_add)} ürün başarıyla eklendi!")