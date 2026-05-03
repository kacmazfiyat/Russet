import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import requests
import xml.etree.ElementTree as ET

st.set_page_config(page_title="Pazaryeri Fiyat Motoru v35", layout="wide")

# --- HESAPLAMA MOTORU ---
def calculate_final_price(maliyet, doviz, urun_iskonto, s):
    try:
        # 1. Ham Maliyeti Kurla Çarp (TL'ye çevir)
        m_tl = float(maliyet)
        if doviz == "EUR": m_tl *= float(s['eur'])
        elif doviz == "USD": m_tl *= float(s['usd'])
        
        # 2. ÜRÜN MALİYETİ ÜZERİNDEN İSKONTO YAP (Senin İstediğin Kısım)
        # Örn: 100 TL liste fiyatı, %20 iskonto -> 80 TL maliyet
        isk_orani = float(urun_iskonto) if str(urun_iskonto).strip() not in ["", "None"] else 0.0
        net_maliyet = m_tl * (1 - (isk_orani / 100))
        
        # 3. KDV ve Gider Hesaplamaları
        # Eğer maliyet KDV dahilse, içinden KDV'yi çıkar (Giderler KDV'siz eklenir)
        m_kdv_siz = net_maliyet / (1 + (s['kdv']/100)) if s['kdv_dahil'] == 1 else net_maliyet
        
        # Kargo ve Hizmet bedellerinden KDV'yi düş (1.20'ye bölerek net gideri bul)
        giderler = m_kdv_siz + (float(s['kargo'])/1.2) + (float(s['hizmet'])/1.2)
        
        # Komisyon ve Kar paydası
        payda = 1 - ((float(s['komisyon']) + float(s['kar']))/100)
        
        # Final Satış Fiyatı (Üzerine tekrar KDV eklenerek)
        final_price = (giderler / payda) * (1 + (s['kdv']/100)) if payda > 0 else 0
        return round(final_price, 2)
    except:
        return 0.0

# --- GOOGLE SHEETS BAĞLANTISI ---
@st.cache_resource
def get_gsheet_client():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], 
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    return gspread.authorize(creds)

def get_data(sheet_name):
    client = get_gsheet_client()
    sh = client.open("Pazaryeri_Veritabani")
    return sh.worksheet(sheet_name)

# --- ANA EKRAN ---
if True: # Giriş yapılmış varsayıyoruz
    menu = st.sidebar.radio("Menü", ["🔍 Arama & Düzenle", "⚙️ Ayarlar"])

    if menu == "⚙️ Ayarlar":
        st.subheader("⚙️ Platform Ayarları")
        ws_set = get_data("Settings")
        settings_df = pd.DataFrame(ws_set.get_all_records())
        # Ayar kaydetme formunu burada kullanabilirsiniz...

    elif menu == "🔍 Arama & Düzenle":
        st.subheader("🔍 Ürün Analizi ve İskonto Girişi")
        
        ws_prod = get_data("Products")
        ws_set = get_data("Settings")
        
        p_df = pd.DataFrame(ws_prod.get_all_records())
        s_df = pd.DataFrame(ws_set.get_all_records())
        
        if not p_df.empty and not s_df.empty:
            target_plat = st.selectbox("Platform Seçin", s_df['platform'].unique())
            s = s_df[s_df['platform'] == target_plat].iloc[0].to_dict()
            
            search = st.text_input("Ürün veya Boy Ara...", "")
            df = p_df[p_df['urun_adi'].str.contains(search, case=False) | p_df['boy'].astype(str).str.contains(search, case=False)].copy()
            
            if not df.empty:
                # ANLIK HESAPLAMA (Satış Fiyatını iskonto değiştikçe günceller)
                df['Satış Fiyatı'] = df.apply(lambda x: calculate_final_price(x['maliyet'], x['doviz'], x.get('iskonto', 0), s), axis=1)
                
                # TABLO GÖRÜNÜMÜ
                st.write(f"**Mevcut Kur:** EUR: {s['eur']} | USD: {s['usd']} | **Kargo:** {s['kargo']} TL")
                
                edited_df = st.data_editor(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "iskonto": st.column_config.NumberColumn("İskonto %", format="%d", help="Buraya girdiğiniz oran maliyetten düşer."),
                        "maliyet": st.column_config.NumberColumn("Liste Fiyatı", format="%.2f"),
                        "Satış Fiyatı": st.column_config.NumberColumn("Satış Fiyatı", format="%.2f ₺", disabled=True),
                        "urun_adi": "Ürün Adı",
                        "boy": "Boy/Ölçü",
                        "doviz": "Kur",
                        "sayfa_adi": None # Bu sütunu gizler
                    }
                )
                
                if st.button("Tüm Değişiklikleri Kaydet"):
                    p_df.update(edited_df)
                    ws_prod.update(range_name='A1', values=[p_df.columns.tolist()] + p_df.values.tolist())
                    st.success("Veriler başarıyla güncellendi!")
                    st.rerun()