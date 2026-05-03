import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Pazaryeri Fiyat Motoru v38", layout="wide")

# --- HESAPLAMA MOTORU (SADELEŞTİRİLMİŞ) ---
def calculate_simple_price(maliyet, doviz, s):
    try:
        # 1. Maliyeti TL'ye çevir
        m_tl = float(maliyet)
        if doviz == "EUR": m_tl *= float(s.get('eur', 35))
        elif doviz == "USD": m_tl *= float(s.get('usd', 32))
        
        # 2. KDV Ayarı
        kdv_orani = float(s.get('kdv', 20)) / 100
        # Eğer maliyet KDV dahilse, net maliyeti bul
        m_net = m_tl / (1 + kdv_orani) if s.get('kdv_dahil') == 1 else m_tl
        
        # 3. Giderler (Kargo ve Hizmet netleştirilerek eklenir)
        giderler = m_net + (float(s.get('kargo', 0))/1.2) + (float(s.get('hizmet', 0))/1.2)
        
        # 4. Komisyon ve Kar Paydası
        payda = 1 - ((float(s.get('komisyon', 0)) + float(s.get('kar', 0)))/100)
        
        # 5. Final Satış Fiyatı (KDV geri eklenerek)
        satis_fiyati = (giderler / payda) * (1 + kdv_orani) if payda > 0 else 0
        return round(m_tl, 2), round(satis_fiyati, 2)
    except:
        return 0.0, 0.0

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
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = True

if st.session_state["password_correct"]:
    menu = st.sidebar.radio("Menü", ["🔍 Arama & Düzenle", "⚙️ Ayarlar"])

    if menu == "🔍 Arama & Düzenle":
        st.subheader("🔍 Satış Fiyatı Analizi")
        
        try:
            ws_prod = get_data("Products")
            ws_set = get_data("Settings")
            
            p_df = pd.DataFrame(ws_prod.get_all_records())
            s_df = pd.DataFrame(ws_set.get_all_records())
            
            if not p_df.empty and not s_df.empty:
                target_plat = st.selectbox("Platform", s_df['platform'].unique())
                s = s_df[s_df['platform'] == target_plat].iloc[0].to_dict()
                
                search = st.text_input("Ürün Ara...", "")
                # Filtreleme (İskonto sütununu veri setinden de çıkarıyoruz)
                df = p_df[p_df['urun_adi'].str.contains(search, case=False)].copy()
                if 'iskonto' in df.columns:
                    df = df.drop(columns=['iskonto'])
                
                # Hesaplama
                res = df.apply(lambda x: calculate_simple_price(x['maliyet'], x['doviz'], s), axis=1)
                df['Maliyet (TL)'], df['Satış Fiyatı'] = zip(*res)
                
                st.info(f"📊 **{target_plat}** Ayarları: Komisyon: %{s['komisyon']} | Kâr: %{s['kar']} | Kargo: {s['kargo']} TL")

                # TABLO GÖRÜNÜMÜ
                edited_df = st.data_editor(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "urun_adi": "Ürün Adı",
                        "maliyet": "Liste Fiyatı (Dövizli)",
                        "doviz": "Kur Türü",
                        "Maliyet (TL)": st.column_config.NumberColumn("Maliyet (TL)", format="%.2f ₺"),
                        "Satış Fiyatı": st.column_config.NumberColumn("Satış Fiyatı", format="%.2f ₺"),
                        "boy": "Ölçü",
                        "sayfa_adi": None
                    },
                    disabled=["Maliyet (TL)", "Satış Fiyatı"]
                )
                
                if st.button("Değişiklikleri Kaydet"):
                    # Sadece orijinal sütunları kaydet (Hesaplananları at)
                    cols_to_save = [c for c in p_df.columns if c not in ['İskontolu Maliyet', 'Kdv Dahil Maliyet', 'Satış Fiyatı', 'Maliyet (TL)', 'iskonto']]
                    save_data = edited_df[cols_to_save]
                    ws_prod.update(range_name='A1', values=[save_data.columns.tolist()] + save_data.values.tolist())
                    st.success("Veriler başarıyla güncellendi!")
                    st.rerun()
        except Exception as e:
            st.error(f"Veri çekme hatası: {e}. Lütfen Google Sheets başlıklarını kontrol edin.")

    elif menu == "⚙️ Ayarlar":
        st.subheader("⚙️ Platform Ayarları")
        # Ayarlar kısmını burada kullanmaya devam edebilirsiniz.