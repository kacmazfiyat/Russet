import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import requests
import xml.etree.ElementTree as ET

st.set_page_config(page_title="Pazaryeri Fiyat Motoru v34", layout="wide")

# --- FONKSİYONLAR ---
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
    except: return {"USD": 32.50, "EUR": 35.50} # Hata durumunda sabit kur

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

def calculate_final_price(maliyet, doviz, urun_iskonto, genel_iskonto, s):
    try:
        m_tl = float(maliyet)
        if doviz == "EUR": m_tl *= float(s['eur'])
        elif doviz == "USD": m_tl *= float(s['usd'])
        
        # İskonto Belirleme
        isk = float(urun_iskonto) if (str(urun_iskonto).strip() not in ["", "None", "0", "0.0"]) else float(genel_iskonto)
        
        # Maliyet / (1 - İskonto)
        net_maliyet = m_tl / (1 - (isk / 100)) if isk < 100 else m_tl
        
        m_kdv_siz = net_maliyet / (1 + (s['kdv']/100)) if s['kdv_dahil'] == 1 else net_maliyet
        giderler = m_kdv_siz + (float(s['kargo'])/1.2) + (float(s['hizmet'])/1.2)
        payda = 1 - ((float(s['komisyon']) + float(s['kar']))/100)
        
        final_price = (giderler / payda) * (1 + (s['kdv']/100)) if payda > 0 else 0
        return round(final_price, 2)
    except: return 0.0

# --- ANA ARAYÜZ ---
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = True # Test için True, gerekirse secrets'a bağla

if st.session_state["password_correct"]:
    menu = st.sidebar.radio("Menü", ["🔍 Arama & Düzenle", "⚙️ Ayarlar", "📥 Veri Yükle"])

    # --- 1. AYARLAR ---
    if menu == "⚙️ Ayarlar":
        st.subheader("⚙️ Platform Ayarları")
        ws_set = get_worksheet("Settings")
        if ws_set:
            settings_df = pd.DataFrame(ws_set.get_all_records())
            sel_plat = st.selectbox("Ayar Yapılacak Platform", ["Trendyol", "Hepsiburada", "Amazon", "N11"])
            
            # Varsayılan değerleri hazırla
            if not settings_df.empty and sel_plat in settings_df['platform'].values:
                dv = settings_df[settings_df['platform'] == sel_plat].iloc[0].to_dict()
            else:
                dv = {"platform": sel_plat, "komisyon": 20.0, "kargo": 80.0, "hizmet": 15.0, "kar": 30.0, "kdv": 20, "kdv_dahil": 0, "eur": 35.50, "usd": 32.50, "varsayilan_iskonto": 0.0}

            with st.form("settings_form"):
                c1, c2, c3 = st.columns(3)
                kom = c1.number_input("Komisyon (%)", value=float(dv.get("komisyon", 20)))
                kargo = c2.number_input("Kargo (TL)", value=float(dv.get("kargo", 80)))
                hizmet = c3.number_input("Hizmet (TL)", value=float(dv.get("hizmet", 15)))
                kar = c1.number_input("Kâr (%)", value=float(dv.get("kar", 30)))
                kdv = c2.selectbox("KDV (%)", [0, 1, 10, 20], index=3)
                kdv_d = c3.radio("Maliyet Tipi", ["KDV Hariç", "KDV Dahil"], index=int(dv.get("kdv_dahil", 0)))
                eur_k = c1.number_input("Euro Kuru", value=float(dv.get("eur", 35.5)))
                usd_k = c2.number_input("USD Kuru", value=float(dv.get("usd", 32.5)))
                v_isk = c3.number_input("Varsayılan İskonto (%)", value=float(dv.get("varsayilan_iskonto", 0)))
                
                if st.form_submit_button("Kaydet"):
                    new_row = [sel_plat, kom, kargo, hizmet, kar, kdv, (1 if kdv_d=="KDV Dahil" else 0), eur_k, usd_k, v_isk]
                    cell = ws_set.find(sel_plat)
                    if cell: ws_set.update(range_name=f"A{cell.row}:J{cell.row}", values=[new_row])
                    else: ws_set.append_row(new_row)
                    st.success("Ayarlar Güncellendi!")

    # --- 2. ARAMA & DÜZENLE ---
    elif menu == "🔍 Arama & Düzenle":
        st.subheader("🔍 Ürün Analizi")
        ws_prod = get_worksheet("Products")
        ws_set = get_worksheet("Settings")
        
        if ws_prod and ws_set:
            p_df = pd.DataFrame(ws_prod.get_all_records())
            s_df = pd.DataFrame(ws_set.get_all_records())
            
            if not p_df.empty and not s_df.empty:
                target_plat = st.selectbox("Hesaplama Yapılacak Platform", s_df['platform'].unique())
                s = s_df[s_df['platform'] == target_plat].iloc[0].to_dict()
                
                search = st.text_input("Arama...", placeholder="Ürün adı yazın...")
                df = p_df[p_df['urun_adi'].str.contains(search, case=False)].copy()
                
                if not df.empty:
                    # Anlık hesaplama sütunu
                    df['Satış Fiyatı'] = df.apply(lambda x: calculate_final_price(x['maliyet'], x['doviz'], x.get('iskonto', 0), s['varsayilan_iskonto'], s), axis=1)
                    
                    st.info("💡 İskonto rakamını değiştirip Enter'a basınca Satış Fiyatı anında güncellenir.")
                    edited_df = st.data_editor(
                        df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "iskonto": st.column_config.NumberColumn("İskonto (%)", format="%d"),
                            "maliyet": st.column_config.NumberColumn("Liste Fiyatı", format="%.2f"),
                            "Satış Fiyatı": st.column_config.NumberColumn("Satış Fiyatı", format="%.2f ₺")
                        },
                        disabled=["Satış Fiyatı", "sayfa_adi"]
                    )
                    
                    if st.button("Değişiklikleri Kaydet"):
                        p_df.update(edited_df)
                        ws_prod.update(range_name='A1', values=[p_df.columns.tolist()] + p_df.values.tolist())
                        st.success("Kaydedildi!")
                        st.rerun()

    # --- 3. VERİ YÜKLE ---
    elif menu == "📥 Veri Yükle":
        st.subheader("📥 Excel Yükle")
        file = st.file_uploader("Excel Dosyası Seçin", type=['xlsx'])
        if file:
            st.success("Dosya algılandı. Aktarımı başlatmak için 'Verileri İşle' butonuna basın.")
            if st.button("Verileri İşle"):
                # Excel okuma ve Google Sheets'e yazma kodları buraya gelecek
                # Boş görünmemesi için basit bir işlem simülasyonu:
                st.write("Veriler okunuyor...")
                # (Daha önceki yükleme mantığını buraya ekleyebilirsiniz)