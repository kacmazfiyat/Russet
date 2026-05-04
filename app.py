import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import re
import requests
import xml.etree.ElementTree as ET

st.set_page_config(page_title="Pazaryeri Fiyat Motoru v58", layout="wide")

# --- TCMB KUR ÇEKME ---
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

# --- GÜVENLİK ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if not st.session_state["password_correct"]:
        st.title("🔐 Pro Yönetim Giriş")
        pwd = st.text_input("Şifre", type="password")
        if st.button("Giriş Yap") or pwd:
            if pwd == st.secrets["access_password"]:
                st.session_state["password_correct"] = True
                st.rerun()
            else: st.error("❌ Hatalı Şifre!")
        return False
    return True

# --- GOOGLE SHEETS ---
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

# --- ANA UYGULAMA ---
if check_password():
    menu = st.sidebar.radio("Menü", ["🔍 Arama & Düzenle", "⚙️ Ayarlar", "📥 Veri Yükle", "🗑️ Veritabanı Yönetimi"])

    # --- AYARLAR ---
    if menu == "⚙️ Ayarlar":
        st.subheader("⚙️ Platform ve Kur Ayarları")
        ws_set = get_worksheet("Settings")
        if ws_set:
            settings_df = pd.DataFrame(ws_set.get_all_records())
            platforms = ["Trendyol", "Hepsiburada", "Amazon", "N11"]
            sel_plat = st.selectbox("Ayar Yapılacak Platform", platforms)
            dv = settings_df[settings_df['platform'] == sel_plat].iloc[0].to_list() if not settings_df.empty and sel_plat in settings_df['platform'].values else [sel_plat, 20.0, 80.0, 15.0, 30.0, 20.0, 0, 33.50, 36.50]

            if st.button("🔄 TCMB'den Güncel Kurları Getir"):
                g_kur = get_tcmb_kurlar()
                if g_kur:
                    st.session_state["eur_val"], st.session_state["usd_val"] = g_kur["EUR"], g_kur["USD"]
                    st.success("Kurlar çekildi!")

            with st.form("set_form"):
                c1, c2, c3 = st.columns(3)
                kom = c1.number_input("Komisyon (%)", value=float(dv[1]))
                kargo = c2.number_input("Kargo (TL)", value=float(dv[2]))
                hizmet = c3.number_input("Hizmet (TL)", value=float(dv[3]))
                kar = c1.number_input("Kâr (%)", value=float(dv[4]))
                kdv = c2.selectbox("KDV (%)", [0, 1, 10, 20], index=3)
                kdv_d = c3.radio("Maliyet Tipi", ["KDV Hariç", "KDV Dahil"], index=int(dv[6]))
                eur_k = st.number_input("EURO Kuru", value=st.session_state.get("eur_val", float(dv[7])))
                usd_k = st.number_input("USD Kuru", value=st.session_state.get("usd_val", float(dv[8])))
                if st.form_submit_button("Ayarları Kaydet"):
                    new_row = [sel_plat, kom, kargo, hizmet, kar, kdv, (1 if kdv_d=="KDV Dahil" else 0), eur_k, usd_k]
                    cell = ws_set.find(sel_plat)
                    if cell: ws_set.update(range_name=f"A{cell.row}:I{cell.row}", values=[new_row])
                    else: ws_set.append_row(new_row)
                    st.success("Kaydedildi!")

    # --- VERİ YÜKLEME ---
    elif menu == "📥 Veri Yükle":
        st.subheader("📥 Excel'den Buluta Aktar")
        file = st.file_uploader("Excel Dosyası", type=['xlsx'])
        if st.button("Aktarımı Başlat") and file:
            with st.spinner("İşleniyor..."):
                xls = pd.ExcelFile(file)
                all_rows = []
                for sheet_name in xls.sheet_names:
                    df = pd.read_excel(file, sheet_name=sheet_name, header=None).fillna("")
                    price_col, name_col, size_col = -1, -1, -1
                    
                    # Başlık Satırını ve Sütunları Tespit Et
                    for i in range(min(20, len(df))):
                        row_vals = [str(val).upper().strip() for val in df.iloc[i].values]
                        if "BİRİM FİYATI" in row_vals: 
                            price_col = row_vals.index("BİRİM FİYATI")
                        if any(x in row_vals for x in ["MALZEME ADI", "ÜRÜN ADI"]):
                            name_col = next(idx for idx, v in enumerate(row_vals) if v in ["MALZEME ADI", "ÜRÜN ADI"])
                        if any(x in row_vals for x in ["CM.", "CM", "BOY", "ÖLÇÜ"]):
                            size_col = next(idx for idx, v in enumerate(row_vals) if v in ["CM.", "CM", "BOY", "ÖLÇÜ"])
                    
                    if price_col != -1 and name_col != -1:
                        for _, row in df.iloc[i+1:].iterrows():
                            raw_name = str(row[name_col]).strip()
                            if not raw_name or raw_name.upper() in ["NAN", ""]: continue
                            
                            # BOY BULMA STRATEJİSİ
                            extracted_boy = "-"
                            if size_col != -1 and str(row[size_col]).strip() != "":
                                val = str(row[size_col]).strip()
                                extracted_boy = val if "CM" in val.upper() else f"{val} CM"
                            elif re.search(r'(\d+)\s*CM', raw_name, flags=re.I):
                                match = re.search(r'(\d+)\s*CM', raw_name, flags=re.I)
                                extracted_boy = match.group(0).upper()
                                raw_name = raw_name.replace(match.group(0), "").strip()

                            # FİYAT TEMİZLEME
                            try:
                                f_raw = row[price_col]
                                f_clean = float(str(f_raw).replace('.', '').replace(',', '.')) if isinstance(f_raw, str) else float(f_raw)
                            except: f_clean = 0.0

                            # DÖVİZ TESPİTİ (Fiyatın bir sağındaki kolon)
                            # Sizin isteğiniz doğrultusunda revize edilen kısım burasıdır
                            d_col_idx = price_col + 1
                            d_raw = "TL"
                            if d_col_idx < len(row):
                                d_raw = str(row[d_col_idx]).strip().upper()
                            
                            # Döviz tipini normalize et
                            if any(x in d_raw for x in ["EUR", "€", "EURO"]): d_tipi = "EUR"
                            elif any(x in d_raw for x in ["USD", "$", "DOLAR"]): d_tipi = "USD"
                            else: d_tipi = "TL"
                            
                            all_rows.append([raw_name, extracted_boy, f_clean, d_tipi, sheet_name])
                
                if all_rows:
                    get_worksheet("Products").append_rows(all_rows, value_input_option='RAW')
                    st.success(f"✅ {len(all_rows)} ürün eklendi!")

    # --- ARAMA ---
    elif menu == "🔍 Arama & Düzenle":
        st.subheader("🔍 Ürün Analizi")
        ws_set, ws_prod = get_worksheet("Settings"), get_worksheet("Products")
        if ws_set and ws_prod:
            s_data, p_data = pd.DataFrame(ws_set.get_all_records()), pd.DataFrame(ws_prod.get_all_records())
            if not s_data.empty and not p_data.empty:
                p_list = list(s_data['platform'].unique())
                target = st.selectbox("Hesaplama Yapılacak Platform", p_list)
                search = st.text_input("Arama yapın...", placeholder="Ürün adı veya boy...")
                
                s = s_data[s_data['platform'] == target].iloc[0]
                df = p_data[p_data['urun_adi'].str.contains(search, case=False) | p_data['boy'].astype(str).str.contains(search, case=False)].copy()
                
                def calc_price(row):
                    try:
                        m = float(row['maliyet'])
                        if row['doviz'] == "EUR": m *= float(s['eur'])
                        elif row['doviz'] == "USD": m *= float(s['usd'])
                        
                        m_net = m / (1 + (s['kdv']/100)) if s['kdv_dahil'] == 1 else m
                        gider = m_net + (float(s['kargo'])/1.2) + (float(s['hizmet'])/1.2)
                        payda = 1 - ((float(s['komisyon']) + float(s['kar']))/100)
                        
                        return round((gider/payda)*(1+(s['kdv']/100)), 2) if payda > 0 else 0
                    except: return 0

                if not df.empty:
                    df['Satış Fiyatı'] = df.apply(calc_price, axis=1)
                    # Sütunları daha okunabilir isimlerle gösterelim
                    display_df = df.rename(columns={
                        'urun_adi': 'Ürün Adı',
                        'boy': 'Boy/Ölçü',
                        'maliyet': 'Maliyet',
                        'doviz': 'Kur',
                        'kategori': 'Kategori'
                    })
                    st.data_editor(display_df, use_container_width=True, hide_index=True)

    # --- TEMİZLE ---
    elif menu == "🗑️ Veritabanı Yönetimi":
        st.subheader("🗑️ Veritabanını Temizle")
        st.warning("Bu işlem geri alınamaz!")
        if st.checkbox("Ürün listesini tamamen silmeyi onaylıyorum") and st.button("Tümünü Sil"):
            ws_prod = get_worksheet("Products")
            if ws_prod:
                ws_prod.batch_clear(["A2:E10000"])
                st.success("Veritabanı başarıyla temizlendi!")