import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Pazaryeri Fiyat Motoru v43", layout="wide")

# --- GÜVENLİ SAYI ÇEVİRİCİ ---
def safe_float(value, default=0.0):
    """Veriyi güvenli bir şekilde float'a çevirir, hata alırsa default döner."""
    try:
        if value is None or str(value).strip() == "":
            return default
        return float(str(value).replace(',', '.'))
    except:
        return default

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

ws_prod = get_data("Products")
ws_set = get_data("Settings")

if ws_prod is None or ws_set is None:
    st.error("❌ Veritabanına ulaşılamıyor. Sheets ismini ve yetkileri kontrol edin.")
else:
    # Verileri oku
    p_df = pd.DataFrame(ws_prod.get_all_records())
    s_df = pd.DataFrame(ws_set.get_all_records())

    if menu == "⚙️ Ayarlar":
        st.subheader("⚙️ Platform Ayarları")
        
        platforms = ["Trendyol", "Hepsiburada", "Amazon", "N11"]
        sel_plat = st.selectbox("Düzenlenecek Platform", platforms)
        
        # Mevcut veriyi çek veya boş şablon oluştur
        current_s = {}
        if not s_df.empty and sel_plat in s_df['platform'].values:
            current_s = s_df[s_df['platform'] == sel_plat].iloc[0].to_dict()
        
        # FORM BAŞLANGICI
        with st.form("settings_form"):
            col1, col2 = st.columns(2)
            
            # safe_float kullanarak ValueError hatasını engelliyoruz
            kom = col1.number_input("Komisyon (%)", value=safe_float(current_s.get('komisyon'), 20.0))
            kar = col2.number_input("Hedef Kar (%)", value=safe_float(current_s.get('kar'), 20.0))
            kargo = col1.number_input("Kargo Ücreti (TL)", value=safe_float(current_s.get('kargo'), 80.0))
            hizmet = col2.number_input("Hizmet Bedeli (TL)", value=safe_float(current_s.get('hizmet', 15.0)))
            
            st.divider()
            eur = col1.number_input("EURO Kuru", value=safe_float(current_s.get('eur'), 35.0))
            usd = col2.number_input("USD Kuru", value=safe_float(current_s.get('usd'), 32.0))
            
            # FORMUN MUTLAKA İÇİNDE OLMASI GEREKEN BUTON
            submit = st.form_submit_button("Ayarları Kaydet")
            
            if submit:
                new_row = [sel_plat, kom, kargo, hizmet, kar, 20, 0, eur, usd]
                try:
                    cell = ws_set.find(sel_plat)
                    if cell:
                        ws_set.update(range_name=f"A{cell.row}:I{cell.row}", values=[new_row])
                    else:
                        ws_set.append_row(new_row)
                    st.success("Başarıyla kaydedildi!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Kayıt sırasında hata: {e}")

    elif menu == "🔍 Arama & Düzenle":
        st.subheader("🔍 Ürün Fiyat Analizi")
        # ... (Arama ve Tablo Kodları)
        st.info("Ayarlar tamamlandıktan sonra burada analiz yapabilirsiniz.")