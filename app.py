import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import re
import requests
import xml.etree.ElementTree as ET

st.set_page_config(page_title="Pazaryeri Fiyat Motoru v22", layout="wide")

# --- TCMB KUR ÇEKME FONKSİYONU ---
def get_tcmb_kurlar():
    try:
        # TCMB Günlük Kur Verisi
        response = requests.get("https://www.tcmb.gov.tr/kurlar/today.xml", timeout=10)
        tree = ET.fromstring(response.content)
        kurlar = {"USD": 33.0, "EUR": 36.0} # Hata durumunda varsayılan
        
        for currency in tree.findall('Currency'):
            code = currency.get('CurrencyCode')
            if code in ["USD", "EUR"]:
                # ForexSelling = Döviz Satış
                rate = currency.find('ForexSelling').text
                if rate:
                    kurlar[code] = float(rate)
        return kurlar
    except Exception as e:
        st.error(f"Kur çekilirken hata oluştu: {e}")
        return None

# --- GÜVENLİK ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if not st.session_state["password_correct"]:
        st.title("🔐 Pro Yönetim Giriş")
        pwd = st.text_input("Lütfen Giriş Şifresini Giriniz", type="password")
        if st.button("Giriş Yap") or pwd:
            if pwd == st.secrets["access_password"]:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ Hatalı Şifre!")
        return False
    return True

# --- GOOGLE SHEETS BAĞLANTISI ---
@st.cache_resource
def get_gsheet_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    return gspread.authorize(creds)

def get_worksheet(sheet_name):
    client = get_gsheet_client()
    try:
        sh = client.open("Pazaryeri_Veritabani")
    except gspread.exceptions.SpreadsheetNotFound:
        st.error("⚠️ 'Pazaryeri_Veritabani' isimli Google Sheet bulunamadı!")
        return None
    
    try:
        return sh.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        if sheet_name == "Products":
            ws = sh.add_worksheet(title="Products", rows="10000", cols="10")
            ws.append_row(["urun_adi", "boy", "maliyet", "doviz", "sayfa_adi"])
            return ws
        elif sheet_name == "Settings":
            ws = sh.add_worksheet(title="Settings", rows="100", cols="15")
            ws.append_row(["platform", "komisyon", "kargo", "hizmet", "kar", "kdv", "kdv_dahil", "eur", "usd"])
            return ws
    return None

# --- ANA UYGULAMA ---
if check_password():
    st.sidebar.success("Oturum Açıldı")
    menu = st.sidebar.radio("Menü", ["🔍 Arama & Düzenle", "⚙️ Ayarlar", "📥 Veri Yükle"])

    # --- 1. AYARLAR ---
    if menu == "⚙️ Ayarlar":
        st.subheader("⚙️ Platform ve Kur Ayarları")
        
        ws_set = get_worksheet("Settings")
        if ws_set:
            settings_df = pd.DataFrame(ws_set.get_all_records())
            platforms = ["Trendyol", "Hepsiburada", "Amazon", "N11"]
            sel_plat = st.selectbox("Platform Seçin", platforms)
            
            # Google Sheets'ten mevcut ayarları al
            if not settings_df.empty and sel_plat in settings_df['platform'].values:
                dv = settings_df[settings_df['platform'] == sel_plat].iloc[0].to_list()
            else:
                dv = [sel_plat, 20.0, 80.0, 15.0, 30.0, 20.0, 0, 33.50, 36.50]

            # TCMB'den kur çekme butonu
            if st.button("🔄 TCMB'den Güncel Kurları Getir"):
                guncel_kur = get_tcmb_kurlar()
                if guncel_kur:
                    st.session_state["eur_val"] = guncel_kur["EUR"]
                    st.session_state["usd_val"] = guncel_kur["USD"]
                    st.success(f"Merkez Bankası kurları çekildi! (EUR: {guncel_kur['EUR']}, USD: {guncel_kur['USD']})")

            with st.form("set_form"):
                c1, c2, c3 = st.columns(3)
                kom = c1.number_input("Komisyon (%)", value=float(dv[1]))
                kargo = c2.number_input("Kargo (TL/KDV Hariç)", value=float(dv[2]))
                hizmet = c3.number_input("Hizmet (TL/KDV Hariç)", value=float(dv[3]))
                kar = c1.number_input("Kâr (%)", value=float(dv[4]))
                kdv = c2.selectbox("KDV (%)", [0, 1, 10, 20], index=3)
                kdv_d = c3.radio("Maliyet Tipi", ["KDV Hariç", "KDV Dahil"], index=int(dv[6]))
                
                st.divider()
                st.markdown("### 💱 Döviz Kurları")
                # Eğer butonla kur çekildiyse session_state'den al, yoksa Sheets'ten al
                eur_k = st.number_input("EURO Kuru", value=st.session_state.get("eur_val", float(dv[7])))
                usd_k = st.number_input("USD Kuru", value=st.session_state.get("usd_val", float(dv[8])))
                
                if st.form_submit_button("Ayarları Kaydet"):
                    new_row = [sel_plat, kom, kargo, hizmet, kar, kdv, (1 if kdv_d=="KDV Dahil" else 0), eur_k, usd_k]
                    cell = ws_set.find(sel_plat)
                    if cell:
                        ws_set.update(range_name=f"A{cell.row}:I{cell.row}", values=[new_row])
                    else:
                        ws_set.append_row(new_row)
                    st.success("Tüm ayarlar kaydedildi!")

    # --- 2. VERİ YÜKLEME ---
    elif menu == "📥 Veri Yükle":
        st.subheader("📥 Excel'den Buluta Aktar")
        file = st.file_uploader("Excel Dosyası Seçin", type=['xlsx'])
        if st.button("Aktarımı Başlat"):
            if file:
                with st.spinner("İşleniyor..."):
                    try:
                        xls = pd.ExcelFile(file)
                        all_rows = []
                        for sheet_name in xls.sheet_names:
                            df = pd.read_excel(file, sheet_name=sheet_name, header=None).fillna("")
                            
                            price_col, name_col, size_col = -1, -1, -1
                            search_limit = min(15, len(df))
                            for i in range(search_limit):
                                row_vals = [str(val).upper().strip() for val in df.iloc[i].values]
                                if "BİRİM FİYATI" in row_vals: price_col = row_vals.index("BİRİM FİYATI")
                                if any(x in row_vals for x in ["MALZEME ADI", "ÜRÜN ADI"]):
                                    name_col = next(idx for idx, v in enumerate(row_vals) if v in ["MALZEME ADI", "ÜRÜN ADI"])
                                if any(x in row_vals for x in ["BOY", "ÖLÇÜ"]):
                                    size_col = next(idx for idx, v in enumerate(row_vals) if v in ["BOY", "ÖLÇÜ"])
                            
                            if price_col != -1 and name_col != -1:
                                for _, row in df.iloc[i+1:].iterrows():
                                    raw_name = str(row[name_col]).strip()
                                    if not raw_name or raw_name.upper() == "NAN" or raw_name == "": continue
                                    
                                    clean_name = re.sub(r'\d+\s*CM', '', raw_name, flags=re.I).strip()
                                    boy_val = str(row[size_col]).strip() if size_col != -1 else "-"
                                    
                                    try:
                                        f_raw = row[price_col]
                                        f_clean = float(str(f_raw).replace('.', '').replace(',', '.')) if isinstance(f_raw, str) else float(f_raw)
                                    except: f_clean = 0.0

                                    d_raw = str(row[price_col + 1]).strip().upper() if len(row) > price_col + 1 else "TL"
                                    d_tipi = "EUR" if "EUR" in d_raw or "€" in d_raw else ("USD" if "USD" in d_raw or "$" in d_raw else "TL")
                                    
                                    all_rows.append([str(clean_name), str(boy_val), float(f_clean), str(d_tipi), str(sheet_name)])
                        
                        if all_rows:
                            ws_prod = get_worksheet("Products")
                            ws_prod.append_rows(all_rows, value_input_option='RAW')
                            st.success(f"✅ {len(all_rows)} ürün buluta eklendi!")
                    except Exception as e: st.error(f"Hata: {e}")

    # --- 3. ARAMA & HESAPLAMA ---
    elif menu == "🔍 Arama & Düzenle":
        st.subheader("🔍 Ürün Analizi")
        ws_set = get_worksheet("Settings")
        ws_prod = get_worksheet("Products")
        
        if ws_set and ws_prod:
            s_data = pd.DataFrame(ws_set.get_all_records())
            p_data = pd.DataFrame(ws_prod.get_all_records())
            
            if not s_data.empty and not p_data.empty:
                target = st.selectbox("Platform", s_data['platform'])
                s = s_data[s_data['platform'] == target].iloc[0]
                search = st.text_input("Arama yapın...")
                
                df = p_data[p_data['urun_adi'].str.contains(search, case=False) | p_data['boy'].astype(str).str.contains(search, case=False)]
                
                def calc_price(row):
                    m = float(row['maliyet'])
                    if row['doviz'] == "EUR": m *= float(s['eur'])
                    elif row['doviz'] == "USD": m *= float(s['usd'])
                    m_net = m / (1 + (s['kdv']/100)) if s['kdv_dahil'] == 1 else m
                    gider = m_net + (float(s['kargo'])/1.2) + (float(s['hizmet'])/1.2)
                    payda = 1 - ((float(s['komisyon']) + float(s['kar']))/100)
                    return round((gider/payda)*(1+(s['kdv']/100)), 2) if payda > 0 else 0

                if not df.empty:
                    df['Satış Fiyatı'] = df.apply(calc_price, axis=1)
                    st.data_editor(df, use_container_width=True, hide_index=True)