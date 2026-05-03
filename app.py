import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Pazaryeri Fiyat Motoru v36", layout="wide")

# --- HESAPLAMA MOTORU ---
def calculate_costs_and_price(maliyet, doviz, urun_iskonto, s):
    try:
        # 1. Ham Maliyeti Kurla Çarp (TL Liste Fiyatı)
        m_tl = float(maliyet)
        if doviz == "EUR": m_tl *= float(s['eur'])
        elif doviz == "USD": m_tl *= float(s['usd'])
        
        # 2. İskontolu Maliyet (Net Alış)
        isk_orani = float(urun_iskonto) if str(urun_iskonto).strip() not in ["", "None"] else 0.0
        iskontolu_maliyet = m_tl * (1 - (isk_orani / 100))
        
        # 3. KDV Dahil Maliyet
        # Eğer ayardan "KDV Dahil" seçildiyse zaten dahildir, değilse KDV ekle
        kdv_orani = float(s['kdv']) / 100
        if s['kdv_dahil'] == 1:
            kdv_dahil_maliyet = iskontolu_maliyet
            iskontolu_maliyet_netsiz = iskontolu_maliyet / (1 + kdv_orani)
        else:
            kdv_dahil_maliyet = iskontolu_maliyet * (1 + kdv_orani)
            iskontolu_maliyet_netsiz = iskontolu_maliyet

        # 4. Satış Fiyatı Hesaplama (Giderler eklenerek)
        giderler = iskontolu_maliyet_netsiz + (float(s['kargo'])/1.2) + (float(s['hizmet'])/1.2)
        payda = 1 - ((float(s['komisyon']) + float(s['kar']))/100)
        satis_fiyati = (giderler / payda) * (1 + kdv_orani) if payda > 0 else 0
        
        return round(iskontolu_maliyet, 2), round(kdv_dahil_maliyet, 2), round(satis_fiyati, 2)
    except:
        return 0.0, 0.0, 0.0

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

# --- ANA PROGRAM ---
if True:
    menu = st.sidebar.radio("Menü", ["🔍 Arama & Düzenle", "⚙️ Ayarlar"])

    if menu == "🔍 Arama & Düzenle":
        st.subheader("🔍 Detaylı Maliyet ve Satış Analizi")
        
        ws_prod = get_data("Products")
        ws_set = get_data("Settings")
        
        p_df = pd.DataFrame(ws_prod.get_all_records())
        s_df = pd.DataFrame(ws_set.get_all_records())
        
        if not p_df.empty and not s_df.empty:
            target_plat = st.selectbox("Hesaplama Yapılacak Platform", s_df['platform'].unique())
            s = s_df[s_df['platform'] == target_plat].iloc[0].to_dict()
            
            search = st.text_input("Ürün Ara...", "")
            df = p_df[p_df['urun_adi'].str.contains(search, case=False)].copy()
            
            if not df.empty:
                # ANLIK HESAPLAMA: Üç yeni kolon oluşturuyoruz
                res = df.apply(lambda x: calculate_costs_and_price(x['maliyet'], x['doviz'], x.get('iskonto', 0), s), axis=1)
                df['İskontolu Maliyet'], df['Kdv Dahil Maliyet'], df['Satış Fiyatı'] = zip(*res)
                
                st.info(f"📌 Şu an **{target_plat}** platformu kuralları ve **%{s['varsayilan_iskonto']}** varsayılan iskonto ile hesaplanıyor.")

                # TABLO YAPILANDIRMASI
                edited_df = st.data_editor(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "urun_adi": st.column_config.TextColumn("Ürün Adı", width="large"),
                        "maliyet": st.column_config.NumberColumn("Liste Fiyatı", format="%.2f"),
                        "iskonto": st.column_config.NumberColumn("İskonto", format="%d%%", help="İskonto oranını girin."),
                        "İskontolu Maliyet": st.column_config.NumberColumn("İskontolu Maliyet", format="%.2f ₺"),
                        "Kdv Dahil Maliyet": st.column_config.NumberColumn("Kdv Dahil Maliyet", format="%.2f ₺"),
                        "Satış Fiyatı": st.column_config.NumberColumn("Satış Fiyatı", format="%.2f ₺"),
                        "doviz": "Kur",
                        "boy": "Ölçü",
                        "sayfa_adi": None # Gizli
                    },
                    disabled=["İskontolu Maliyet", "Kdv Dahil Maliyet", "Satış Fiyatı"]
                )
                
                if st.button("Değişiklikleri Buluta İşle"):
                    p_df.update(edited_df)
                    ws_prod.update(range_name='A1', values=[p_df.columns.tolist()] + p_df.values.tolist())
                    st.success("Tüm maliyetler ve fiyatlar güncellendi!")
                    st.rerun()