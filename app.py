import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import re
import requests
import xml.etree.ElementTree as ET

st.set_page_config(page_title="Pazaryeri Fiyat Motoru v62", layout="wide")

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
        return sh.worksheet(sheet_name)
    except: return None

# --- ANA PROGRAM ---
if check_password():
    menu = st.sidebar.radio("Menü", ["🔍 Ürün Analizi", "⚙️ Ayarlar", "📥 Veri Yükle", "🗑️ Veritabanı Yönetimi"])

    # 1. ANALİZ EKRANI
    if menu == "🔍 Ürün Analizi":
        st.subheader("🔍 Ürün Fiyat Analizi")
        ws_set, ws_prod = get_worksheet("Settings"), get_worksheet("Products")
        
        if ws_set and ws_prod:
            s_data = pd.DataFrame(ws_set.get_all_records())
            p_raw = ws_prod.get_all_records()
            
            if not s_data.empty and p_raw:
                p_data = pd.DataFrame(p_raw)
                
                # Sütun Kontrolü
                if 'kod' not in p_data.columns: p_data['kod'] = "-"

                p_list = list(s_data['platform'].unique())
                target = st.selectbox("Hesaplama Yapılacak Platform", p_list)
                search = st.text_input("Kod veya Ürün Adı ile Ara...", placeholder="Örn: 5.1001 veya Döner")
                
                s = s_data[s_data['platform'] == target].iloc[0]
                
                mask = (p_data['kod'].astype(str).str.contains(search, case=False, na=False)) | \
                       (p_data['urun_adi'].astype(str).str.contains(search, case=False, na=False))
                df = p_data[mask].copy()
                
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
                    # Dashboard'da Malzeme Kodu en solda görünecek
                    display_cols = ['kod', 'urun_adi', 'boy', 'maliyet', 'doviz', 'Satış Fiyatı', 'kategori']
                    st.dataframe(df[display_cols].rename(columns={
                        'kod': 'Malzeme Kodu', 
                        'urun_adi': 'Ürün Adı', 
                        'boy': 'Ölçü/CM',
                        'maliyet': 'Birim Maliyet', 
                        'doviz': 'Döviz', 
                        'kategori': 'Kategori'
                    }), use_container_width=True, hide_index=True)

    # 2. AYARLAR
    elif menu == "⚙️ Ayarlar":
        st.subheader("⚙️ Platform ve Kur Ayarları")
        ws_set = get_worksheet("Settings")
        if ws_set:
            settings_df = pd.DataFrame(ws_set.get_all_records())
            platforms = ["Trendyol", "Hepsiburada", "Amazon", "N11"]
            sel_plat = st.selectbox("Platform", platforms)
            dv = settings_df[settings_df['platform'] == sel_plat].iloc[0].to_list() if not settings_df.empty and sel_plat in settings_df['platform'].values else [sel_plat, 20.0, 80.0, 15.0, 30.0, 20.0, 0, 33.50, 36.50]

            if st.button("🔄 Güncel Kurları Getir"):
                k = get_tcmb_kurlar()
                if k:
                    st.session_state["eur_v"], st.session_state["usd_v"] = k["EUR"], k["USD"]
                    st.success(f"Kurlar güncellendi! USD: {k['USD']} - EUR: {k['EUR']}")

            with st.form("set_form"):
                c1, c2, c3 = st.columns(3)
                kom = c1.number_input("Komisyon %", value=float(dv[1]))
                kargo = c2.number_input("Kargo (KDV Hariç)", value=float(dv[2]))
                hizmet = c3.number_input("Hizmet (KDV Hariç)", value=float(dv[3]))
                kar = c1.number_input("Hedef Kâr %", value=float(dv[4]))
                kdv = c2.selectbox("Ürün KDV %", [0, 1, 10, 20], index=3)
                m_tipi = c3.radio("Excel Maliyeti", ["KDV Hariç", "KDV Dahil"], index=int(dv[6]))
                eur_k = st.number_input("Euro Kuru", value=st.session_state.get("eur_v", float(dv[7])))
                usd_k = st.number_input("Dolar Kuru", value=st.session_state.get("usd_v", float(dv[8])))
                
                if st.form_submit_button("Ayarları Güncelle"):
                    new_row = [sel_plat, kom, kargo, hizmet, kar, kdv, (1 if m_tipi=="KDV Dahil" else 0), eur_k, usd_k]
                    try:
                        cell = ws_set.find(sel_plat)
                        ws_set.update(f"A{cell.row}:I{cell.row}", [new_row])
                    except: ws_set.append_row(new_row)
                    st.success("Platform ayarları kaydedildi.")

    # 3. VERİ YÜKLE (MALZEME KODU BAŞLIĞI EŞLEŞTİRİLDİ)
    elif menu == "📥 Veri Yükle":
        st.subheader("📥 Excel'den Malzeme Aktarımı")
        file = st.file_uploader("Ürün Listesi Seçin (xlsx)", type=['xlsx'])
        if st.button("Verileri Buluta İşle") and file:
            xls = pd.ExcelFile(file)
            all_rows = []
            for sheet in xls.sheet_names:
                df = pd.read_excel(file, sheet_name=sheet, header=None).fillna("")
                c_idx, p_idx, n_idx, s_idx = -1, -1, -1, -1
                
                # Sütun başlıklarını tespit etme (İlk 25 satırı tarar)
                for i in range(min(25, len(df))):
                    row = [str(v).upper().strip() for v in df.iloc[i].values]
                    # MALZEME KODU başlıklı sütunu arıyoruz
                    if any(x in row for x in ["MALZEME KODU", "STOK KODU", "KOD"]):
                        c_idx = next(idx for idx,v in enumerate(row) if v in ["MALZEME KODU", "STOK KODU", "KOD"])
                    if "BİRİM FİYATI" in row: p_idx = row.index("BİRİM FİYATI")
                    if any(x in row for x in ["MALZEME ADI", "ÜRÜN ADI"]):
                        n_idx = next(idx for idx,v in enumerate(row) if v in ["MALZEME ADI", "ÜRÜN ADI"])
                    if any(x in row for x in ["CM.", "CM", "BOY"]):
                        s_idx = next(idx for idx,v in enumerate(row) if v in ["CM.", "CM", "BOY"])
                
                # Eğer başlıklar bulunduysa veriyi işle
                if n_idx != -1 and p_idx != -1:
                    for _, row in df.iloc[i+1:].iterrows():
                        # Ürün Adı kontrolü (Merged cell desteği)
                        uname = str(row[n_idx]).strip()
                        if uname == "" and n_idx+1 < len(row): uname = str(row[n_idx+1]).strip()
                        if uname == "" or uname.upper() == "NAN": continue
                        
                        # Malzeme Kodu okuma
                        mkod = str(row[c_idx]).strip() if c_idx != -1 else "-"
                        mboy = str(row[s_idx]).strip() if s_idx != -1 else "-"
                        
                        # Fiyat temizleme
                        try:
                            f_raw = row[p_idx]
                            f_clean = float(str(f_raw).replace('.', '').replace(',', '.'))
                        except: f_clean = 0.0
                        
                        # Döviz (Birim Fiyatının sağındaki kolon)
                        d_raw = str(row[p_idx+1]).strip().upper() if p_idx+1 < len(row) else "TL"
                        d_tipi = "EUR" if "EUR" in d_raw or "€" in d_raw else ("USD" if "USD" in d_raw or "$" in d_raw else "TL")
                        
                        all_rows.append([mkod, uname, mboy, f_clean, d_tipi, sheet])
            
            if all_rows:
                ws_prod = get_worksheet("Products")
                ws_prod.clear() # Temiz bir başlangıç için başlıkları koruyarak siler
                ws_prod.append_row(["kod", "urun_adi", "boy", "maliyet", "doviz", "kategori"])
                ws_prod.append_rows(all_rows)
                st.success(f"✅ {len(all_rows)} ürün başarıyla MALZEME KODU ile birlikte kaydedildi!")

    # 4. TEMİZLEME
    elif menu == "🗑️ Veritabanı Yönetimi":
        st.subheader("🗑️ Tüm Verileri Sil")
        if st.checkbox("Ürün listesini kalıcı olarak silmeyi onaylıyorum") and st.button("Veritabanını Sıfırla"):
            ws_prod = get_worksheet("Products")
            if ws_prod:
                ws_prod.clear()
                ws_prod.append_row(["kod", "urun_adi", "boy", "maliyet", "doviz", "kategori"])
                st.success("Tüm ürün verileri silindi.")