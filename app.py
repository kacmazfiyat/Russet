import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Pazaryeri Fiyat Motoru v42", layout="wide")

# --- GOOGLE SHEETS BAĞLANTISI ---
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
    except:
        return None

# --- ANA PROGRAM ---
menu = st.sidebar.radio("Menü", ["🔍 Arama & Düzenle", "⚙️ Ayarlar"])

# 1. VERİLERİ EN BAŞTA ÇEK (HATA KONTROLLÜ)
ws_prod = get_data("Products")
ws_set = get_data("Settings")

if ws_prod is None or ws_set is None:
    st.error("❌ Google Sheets bağlantısı kurulamadı. Lütfen internetinizi ve 'Pazaryeri_Veritabani' dosyasını kontrol edin.")
else:
    # Verileri oku
    p_df = pd.DataFrame(ws_prod.get_all_records())
    s_df = pd.DataFrame(ws_set.get_all_records())

    # --- AYARLAR MENÜSÜ ---
    if menu == "⚙️ Ayarlar":
        st.subheader("⚙️ Platform Ayarları")
        
        if s_df.empty:
            st.warning("Henüz kayıtlı platform yok. Yeni bir tane ekleyelim.")
            platforms = ["Trendyol", "Hepsiburada", "Amazon", "N11"]
        else:
            platforms = s_df['platform'].unique().tolist()
        
        sel_plat = st.selectbox("Düzenlenecek Platform", platforms)
        
        # Seçili platform verisi var mı bak, yoksa boş şablon getir
        if not s_df.empty and sel_plat in s_df['platform'].values:
            current_s = s_df[s_df['platform'] == sel_plat].iloc[0].to_dict()
        else:
            current_s = {"platform": sel_plat, "komisyon": 20, "kar": 20, "kargo": 80, "hizmet": 15, "kdv": 20, "kdv_dahil": 0, "eur": 35, "usd": 32}

        with st.form("settings_form"):
            col1, col2 = st.columns(2)
            kom = col1.number_input("Komisyon (%)", value=float(current_s.get('komisyon', 20)))
            kar = col2.number_input("Hedef Kar (%)", value=float(current_s.get('kar', 20)))
            kargo = col1.number_input("Kargo Ücreti (TL)", value=float(current_s.get('kargo', 80)))
            hizmet = col2.number_input("Hizmet Bedeli (TL)", value=float(current_s.get('hizmet', 15)))
            
            st.divider()
            eur = col1.number_input("EURO Kuru", value=float(current_s.get('eur', 35.0)))
            usd = col2.number_input("USD Kuru", value=float(current_s.get('usd', 32.0)))
            
            if st.form_submit_button("Ayarları Kaydet"):
                # Kaydetme mantığı (v20'deki gibi update/append)
                new_row = [sel_plat, kom, kargo, hizmet, kar, current_s.get('kdv', 20), current_s.get('kdv_dahil', 0), eur, usd]
                cell = ws_set.find(sel_plat)
                if cell:
                    ws_set.update(range_name=f"A{cell.row}:I{cell.row}", values=[new_row])
                else:
                    ws_set.append_row(new_row)
                st.success("Ayarlar Güncellendi!")
                st.rerun()

    # --- ARAMA & DÜZENLE MENÜSÜ ---
    elif menu == "🔍 Arama & Düzenle":
        st.subheader("🔍 Ürün Fiyat Analizi")
        if s_df.empty:
            st.info("Lütfen önce Ayarlar sekmesinden bir platform kaydedin.")
        else:
            # (Burada önceki adımdaki temizleme ve hesaplama kodları çalışacak)
            st.write("Hesaplama motoru hazır...")