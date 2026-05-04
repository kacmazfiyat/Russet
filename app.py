import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import requests
import xml.etree.ElementTree as ET

# Sayfa Ayarları
st.set_page_config(page_title="Pazaryeri Fiyat Motoru v66", layout="wide")

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
    except: return None

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
                # Eksik sütun koruması
                for c in ['kod', 'urun_adi', 'boy', 'maliyet', 'doviz', 'kategori']:
                    if c not in p_data.columns: p_data[c] = "-"
                
                target = st.selectbox("Platform Seçin", list(s_data['platform'].unique()))
                search = st.text_input("Arama (Kod, Ürün Adı veya Kategori)...", placeholder="Örn: Ayna, 5.100, Döner")
                
                s = s_data[s_data['platform'] == target].iloc[0]
                
                # Güçlendirilmiş Arama Maskesi
                mask = (p_data['kod'].astype(str).str.contains(search, case=False, na=False)) | \
                       (p_data['urun_adi'].astype(str).str.contains(search, case=False, na=False)) | \
                       (p_data['kategori'].astype(str).str.contains(search, case=False, na=False))
                
                df = p_data[mask].copy()

                def calc_price(row):
                    try:
                        m = float(row['maliyet'])
                        if row['doviz'] == "EUR": m *= float(s['eur'])
                        elif row['doviz'] == "USD": m *= float(s['usd'])
                        m_n = m / (1 + (s['kdv']/100)) if s['kdv_dahil'] == 1 else m
                        g = m_n + (float(s['kargo'])/1.2) + (float(s['hizmet'])/1.2)
                        p = 1 - ((float(s['komisyon']) + float(s['kar']))/100)
                        return round((g/p)*(1+(s['kdv']/100)), 2) if p > 0 else 0
                    except: return 0

                if not df.empty:
                    df['Satış Fiyatı'] = df.apply(calc_price, axis=1)
                    show_cols = ['kod','urun_adi','boy','maliyet','doviz','Satış Fiyatı','kategori']
                    st.dataframe(df[show_cols].rename(columns={
                        'kod':'Malzeme Kodu','urun_adi':'Ürün Adı','boy':'Ölçü',
                        'maliyet':'Maliyet','doviz':'Kur','kategori':'Kategori'
                    }), use_container_width=True, hide_index=True)
                else: st.warning("Aranan kriterlere uygun ürün bulunamadı.")
            else: st.info("Sistemde ürün veya ayar kaydı bulunamadı.")

    # 2. AYARLAR
    elif menu == "⚙️ Ayarlar":
        st.subheader("⚙️ Platform Ayarları")
        ws_set = get_worksheet("Settings")
        if ws_set:
            s_df = pd.DataFrame(ws_set.get_all_records())
            sel_plat = st.selectbox("Platform", ["Trendyol", "Hepsiburada", "Amazon", "N11"])
            dv = s_df[s_df['platform'] == sel_plat].iloc[0].to_list() if not s_df.empty and sel_plat in s_df['platform'].values else [sel_plat, 20, 80, 15, 30, 20, 0, 35, 33]
            
            if st.button("🔄 TCMB Kurlarını Getir"):
                k = get_tcmb_kurlar()
                if k: st.session_state.update({"ev": k["EUR"], "uv": k["USD"]}); st.success("Kurlar çekildi.")

            with st.form("sf"):
                c1, c2, c3 = st.columns(3)
                kom = c1.number_input("Komisyon %", value=float(dv[1]))
                kargo = c2.number_input("Kargo TL", value=float(dv[2]))
                hizmet = c3.number_input("Hizmet TL", value=float(dv[3]))
                kar = c1.number_input("Hedef Kâr %", value=float(dv[4]))
                kdv = c2.selectbox("Ürün KDV %", [0, 1, 10, 20], index=3)
                mt = c3.radio("Maliyet Tipi", ["KDV Hariç", "KDV Dahil"], index=int(dv[6]))
                ek = st.number_input("Euro Kuru", value=st.session_state.get("ev", float(dv[7])))
                uk = st.number_input("USD Kuru", value=st.session_state.get("uv", float(dv[8])))
                if st.form_submit_button("Ayarları Kaydet"):
                    row = [sel_plat, kom, kargo, hizmet, kar, kdv, (1 if mt=="KDV Dahil" else 0), ek, uk]
                    try: 
                        cell = ws_set.find(sel_plat)
                        ws_set.update(f"A{cell.row}:I{cell.row}", [row])
                    except: ws_set.append_row(row)
                    st.success("Platform ayarları güncellendi.")

    # 3. VERİ YÜKLE
    elif menu == "📥 Veri Yükle":
        st.subheader("📥 Excel'den Veri Yükleme")
        file = st.file_uploader("Dosya Seç (xlsx)", type=['xlsx'])
        if st.button("Aktarımı Başlat") and file:
            xls = pd.ExcelFile(file)
            all_rows = []
            for sheet in xls.sheet_names:
                df = pd.read_excel(file, sheet_name=sheet, header=None).fillna("")
                c_i, p_i, n_i, s_i = -1, -1, -1, -1
                
                # Başlık Tespiti (Genişletilmiş Tarama)
                for i in range(min(30, len(df))):
                    row = [str(v).upper().strip() for v in df.iloc[i].values]
                    if any(x in row for x in ["MALZEME KODU", "KOD", "STOK KODU"]): 
                        c_i = next(idx for idx,v in enumerate(row) if v in ["MALZEME KODU", "KOD", "STOK KODU"])
                    if "BİRİM FİYATI" in row: p_i = row.index("BİRİM FİYATI")
                    if any(x in row for x in ["MALZEME ADI", "ÜRÜN ADI"]): 
                        n_i = next(idx for idx,v in enumerate(row) if v in ["MALZEME ADI", "ÜRÜN ADI"])
                    if any(x in row for x in ["CM.", "CM", "BOY"]): 
                        s_i = next(idx for idx,v in enumerate(row) if v in ["CM.", "CM", "BOY"])
                
                if n_i != -1 and p_i != -1:
                    for _, row in df.iloc[i+1:].iterrows():
                        name = str(row[n_i]).strip()
                        # Merged cell (Hücre Birleştirme) Koruması: Boşsa sağa bak
                        if name == "" and n_i+1 < len(row): name = str(row[n_i+1]).strip()
                        if name == "" or name.upper() == "NAN": continue
                        
                        mkod = str(row[c_i]).strip() if c_i != -1 else "-"
                        mboy = str(row[s_i]).strip() if s_i != -1 else "-"
                        try: f = float(str(row[p_i]).replace('.','').replace(',','.'))
                        except: f = 0.0
                        
                        d_r = str(row[p_i+1]).strip().upper() if p_i+1 < len(row) else "TL"
                        dt = "EUR" if "EUR" in d_r or "€" in d_r else ("USD" if "USD" in d_r or "$" in d_r else "TL")
                        
                        all_rows.append([mkod, name, mboy, f, dt, sheet])
            
            if all_rows:
                ws_prod = get_worksheet("Products")
                ws_prod.clear()
                ws_prod.append_row(["kod", "urun_adi", "boy", "maliyet", "doviz", "kategori"])
                ws_prod.append_rows(all_rows)
                st.success(f"✅ {len(all_rows)} ürün başarıyla sisteme yüklendi!")

    # 4. TEMİZLEME
    elif menu == "🗑️ Veritabanı Yönetimi":
        st.subheader("🗑️ Veritabanı Sıfırlama")
        st.warning("Bu işlem kayıtlı tüm ürünleri siler.")
        if st.checkbox("Verileri silmeyi onaylıyorum") and st.button("Sistemi Sıfırla"):
            ws_p = get_worksheet("Products")
            if ws_p:
                ws_p.clear()
                ws_p.append_row(["kod", "urun_adi", "boy", "maliyet", "doviz", "kategori"])
                st.success("Tüm ürün verileri temizlendi.")