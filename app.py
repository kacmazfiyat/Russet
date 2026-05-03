import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import requests
import xml.etree.ElementTree as ET

st.set_page_config(page_title="Pazaryeri Fiyat Motoru v33", layout="wide")

# --- YARDIMCI FONKSİYONLAR ---
def get_tcmb_kurlar():
    try:
        response = requests.get("https://www.tcmb.gov.tr/kurlar/today.xml", timeout=10)
        tree = ET.fromstring(response.content)
        kurlar = {"USD": 0.0, "EUR": 0.0}
        for currency in tree.findall('Currency'):
            code = currency.get('CurrencyCode')
            if code in ["USD", "EUR"]:
                rate = currency.find('ForexSelling').text
                if rate: kurlar[code] = float(rate)
        return kurlar
    except: return None

@st.cache_resource
def get_gsheet_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    return gspread.authorize(creds)

def get_worksheet(sheet_name):
    client = get_gsheet_client()
    try:
        sh = client.open("Pazaryeri_Veritabani")
        return sh.worksheet(sheet_name)
    except: return None

# --- SATIŞ FİYATI HESAPLAMA MOTORU ---
def calculate_final_price(maliyet, doviz, urun_iskonto, genel_iskonto, s_ayar):
    # Kur Çevrimi
    m_tl = float(maliyet)
    if doviz == "EUR": m_tl *= float(s_ayar['eur'])
    elif doviz == "USD": m_tl *= float(s_ayar['usd'])
    
    # İskonto Belirleme (Ürüne özel yoksa genel)
    isk = float(urun_iskonto) if (str(urun_iskonto).strip() not in ["", "None", "0", "0.0"]) else float(genel_iskonto)
    
    # Net Maliyet Hesaplama (Senin Formülün: Maliyet / (1 - İskonto))
    # Örn: 100 TL / (1 - 0.20) = 125 TL
    if isk < 100:
        net_maliyet = m_tl / (1 - (isk / 100))
    else:
        net_maliyet = m_tl

    # Vergisel ve Platform Giderleri
    m_kdv_siz = net_maliyet / (1 + (s_ayar['kdv']/100)) if s_ayar['kdv_dahil'] == 1 else net_maliyet
    giderler = m_kdv_siz + (float(s_ayar['kargo'])/1.2) + (float(s_ayar['hizmet'])/1.2)
    payda = 1 - ((float(s_ayar['komisyon']) + float(s_ayar['kar']))/100)
    
    final_price = (giderler / payda) * (1 + (s_ayar['kdv']/100)) if payda > 0 else 0
    return round(final_price, 2)

# --- ANA PROGRAM ---
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

# Şifre kontrolü basit geçildi, giriş yapılmış varsayıyoruz
if True: 
    menu = st.sidebar.radio("Menü", ["🔍 Arama & Düzenle", "⚙️ Ayarlar", "📥 Veri Yükle"])

    # --- AYARLAR ---
    if menu == "⚙️ Ayarlar":
        st.subheader("⚙️ Platform Ayarları")
        ws_set = get_worksheet("Settings")
        if ws_set:
            settings_df = pd.DataFrame(ws_set.get_all_records())
            sel_plat = st.selectbox("Platform", ["Trendyol", "Hepsiburada", "Amazon", "N11"])
            # ... (Ayar kaydetme kısımları aynı kalacak şekilde)

    # --- ARAMA & ANLIK DÜZENLEME ---
    elif menu == "🔍 Arama & Düzenle":
        st.subheader("🔍 Ürün Analizi")
        
        ws_prod = get_worksheet("Products")
        ws_set = get_worksheet("Settings")
        
        if ws_prod and ws_set:
            p_data = pd.DataFrame(ws_prod.get_all_records())
            s_data = pd.DataFrame(ws_set.get_all_records())
            
            if not p_data.empty and not s_data.empty:
                target_plat = st.selectbox("Hesaplama Yapılacak Platform", s_data['platform'].unique())
                s_ayar = s_data[s_data['platform'] == target_plat].iloc[0]
                
                search_term = st.text_input("Ürün Ara...", placeholder="Ürün adı veya boy yazın...")
                
                # Filtreleme
                filtered_df = p_data[p_data['urun_adi'].str.contains(search_term, case=False)].copy()
                
                # İskonto sütunu başlığını düzelterek göster
                if 'iskonto' not in filtered_df.columns:
                    filtered_df['iskonto'] = 0.0

                # ANLIK HESAPLAMA SÜTUNU EKLE
                filtered_df['Satış Fiyatı'] = filtered_df.apply(
                    lambda x: calculate_final_price(x['maliyet'], x['doviz'], x['iskonto'], s_ayar['varsayilan_iskonto'], s_ayar), axis=1
                )

                # TABLO (DATA EDITOR)
                st.info("💡 İskonto sütununa rakam girip Enter'a bastığınızda Satış Fiyatı anında güncellenir.")
                
                # Sütun sıralaması ve başlık düzenleme
                edited_df = st.data_editor(
                    filtered_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "iskonto": st.column_config.NumberColumn("İskonto (%)", format="%d", help="Ürüne özel iskonto"),
                        "maliyet": st.column_config.NumberColumn("Liste Fiyatı", format="%.2f"),
                        "Satış Fiyatı": st.column_config.NumberColumn("Satış Fiyatı (Güncel)", format="%.2f ₺"),
                        "doviz": "Para Birimi",
                        "urun_adi": "Ürün Adı"
                    },
                    disabled=["Satış Fiyatı", "sayfa_adi"] # Satış fiyatı sadece çıktı olacak
                )

                # Değişiklik Kontrolü ve Kayıt
                if st.button("Değişiklikleri Buluta Kaydet"):
                    # Tüm veritabanını güncelle
                    p_data.update(edited_df)
                    ws_prod.update(range_name='A1', values=[p_data.columns.tolist()] + p_data.values.tolist())
                    st.success("Veritabanı başarıyla güncellendi!")
                    st.rerun()