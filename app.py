import streamlit as st
import pandas as pd
import sqlite3
import os

st.set_page_config(page_title="Pro Yönetim v9", layout="wide")

# --- VERİTABANI FONKSİYONLARI ---
def get_db_connection():
    return sqlite3.connect('pazaryeri.db', check_same_thread=False)

def init_db():
    with get_db_connection() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            urun_adi TEXT, maliyet REAL, sayfa_adi TEXT, dosya_adi TEXT)''')
        # KDV ve KDV Durumu sütunları eklendi
        conn.execute('''CREATE TABLE IF NOT EXISTS settings (
            platform TEXT PRIMARY KEY, komisyon REAL, kargo REAL, 
            hizmet_bedeli REAL, kar_orani REAL, kdv_orani REAL, kdv_dahil_mi INTEGER)''')
    conn.close()

init_db()

# --- EXCEL İŞLEME ---
def process_all_excel(uploaded_file):
    try:
        xls = pd.ExcelFile(uploaded_file)
        all_rows = []
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(uploaded_file, sheet_name=sheet_name, header=None)
            df = df.dropna(how='all')
            for _, row in df.iterrows():
                urun_adi = str(row[4]) if len(row) > 4 else ""
                fiyat_ham = str(row[14]) if len(row) > 14 else "0"
                boyut = str(row[2]) if len(row) > 2 else ""
                
                try:
                    fiyat = float(str(fiyat_ham).replace('.', '').replace(',', '.'))
                except: fiyat = 0.0

                if urun_adi.strip().upper() not in ["NAN", "MALZEME ADI", "ÜRÜN ADI"] and urun_adi.strip():
                    full_name = f"{urun_adi} {boyut}".strip()
                    all_rows.append((full_name, fiyat, sheet_name, uploaded_file.name))

        if all_rows:
            with get_db_connection() as db_conn:
                db_conn.executemany("INSERT INTO products (urun_adi, maliyet, sayfa_adi, dosya_adi) VALUES (?, ?, ?, ?)", all_rows)
            return len(all_rows)
        return None
    except Exception as e:
        st.error(f"Hata: {e}")
        return None

# --- ARAYÜZ ---
st.title("💎 Pazaryeri Fiyatlandırma v9")
menu = st.sidebar.radio("Menü", ["🔍 Arama & Akıllı Fiyat", "⚙️ Pazaryeri & KDV Ayarları", "📥 Veri Yükle"])

# --- 1. AYARLAR VE KDV BÖLÜMÜ ---
if menu == "⚙️ Pazaryeri & KDV Ayarları":
    st.subheader("Platform ve KDV Parametreleri")
    platforms = ["Trendyol", "Hepsiburada", "Amazon", "N11", "Diğer"]
    selected_plat = st.selectbox("Platform Seçin", platforms)
    
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM settings WHERE platform = ?", (selected_plat,))
        row = cur.fetchone()
    
    # Varsayılan değerler (Eski ayar yoksa bunlar gelir)
    # row düzeni: [platform, komisyon, kargo, hizmet, kar, kdv_orani, kdv_dahil_mi]
    def_val = row if row else (selected_plat, 20.0, 80.0, 15.0, 30.0, 20.0, 0)

    with st.form(f"form_{selected_plat}"):
        col1, col2 = st.columns(2)
        kom = col1.number_input("Komisyon Oranı (%)", value=def_val[1])
        kargo = col2.number_input("Sabit Kargo Ücreti (TL)", value=def_val[2])
        hizmet = col1.number_input("Hizmet Bedeli (TL)", value=def_val[3])
        kar = col2.number_input("Hedef Kâr Oranı (%)", value=def_val[4])
        
        st.divider()
        st.markdown("**KDV Ayarları**")
        col3, col4 = st.columns(2)
        kdv = col3.selectbox("Ürün KDV Oranı (%)", [0, 1, 10, 20], index=3 if def_val[5]==20 else 0)
        
        # KDV Dahil/Hariç Butonu (Radio Button olarak daha net anlaşılır)
        kdv_durumu = col4.radio(
            "Excel'deki Alış Fiyatı (Maliyet):",
            ["KDV Hariç", "KDV Dahil"],
            index=def_val[6]
        )
        kdv_dahil_mi = 1 if kdv_durumu == "KDV Dahil" else 0
        
        if st.form_submit_button("Ayarları ve KDV'yi Kaydet"):
            with get_db_connection() as conn:
                conn.execute('''INSERT OR REPLACE INTO settings 
                             (platform, komisyon, kargo, hizmet_bedeli, kar_orani, kdv_orani, kdv_dahil_mi) 
                             VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                             (selected_plat, kom, kargo, hizmet, kar, kdv, kdv_dahil_mi))
            st.success(f"{selected_plat} için tüm maliyet ve KDV ayarları kaydedildi!")

# --- 2. ANALİZ VE HESAPLAMA ---
elif menu == "🔍 Arama & Akıllı Fiyat":
    st.subheader("Net Maliyet ve Satış Analizi")
    
    with get_db_connection() as conn:
        platforms_saved = pd.read_sql_query("SELECT platform FROM settings", conn)
    
    if not platforms_saved.empty:
        target_plat = st.selectbox("Hesaplama Platformu", platforms_saved['platform'])
        with get_db_connection() as conn:
            s = pd.read_sql_query("SELECT * FROM settings WHERE platform = ?", conn, params=(target_plat,)).iloc[0]
    else:
        st.warning("Lütfen önce Ayarlar sekmesinden platform kurun!")
        st.stop()

    search = st.text_input("Ürün Ara (İsim veya Sayfa)")
    
    with get_db_connection() as conn:
        df = pd.read_sql_query("SELECT urun_adi, maliyet, sayfa_adi FROM products WHERE urun_adi LIKE ?", conn, params=(f'%{search}%',))
    
    if not df.empty:
        def calculate_smart_price(maliyet_ham):
            # 1. Maliyeti KDV'ye göre normalize et (Her zaman Hariç üzerinden giderleri ekleyelim)
            if s['kdv_dahil_mi'] == 1:
                maliyet_hariç = maliyet_ham / (1 + (s['kdv_orani'] / 100))
            else:
                maliyet_hariç = maliyet_ham
            
            # 2. Giderleri ekle (Kargo ve Hizmet genelde KDV dahil ödenir ama biz matrahı bulalım)
            toplam_gider_hariç = maliyet_hariç + (s['kargo'] / 1.2) + (s['hizmet_bedeli'] / 1.2)
            
            # 3. Satış Matrahını Bul (Komisyon ve Kar Payı Düşülmüş Oran)
            payda = 1 - ((s['komisyon'] + s['kar_orani']) / 100)
            if payda <= 0: return 0
            
            satis_matrahi = toplam_gider_hariç / payda
            
            # 4. En son KDV'yi ekle (Pazaryeri satış fiyatı)
            satis_fiyati_kdv_dahil = satis_matrahi * (1 + (s['kdv_orani'] / 100))
            return round(satis_fiyati_kdv_dahil, 2)

        df['Pazaryeri Satış (KDV Dahil)'] = df['maliyet'].apply(calculate_smart_price)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Sonuç yok.")

# --- 3. VERİ YÜKLEME ---
elif menu == "📥 Veri Yükle":
    st.subheader("Hafıza Yönetimi")
    file = st.file_uploader("Excel (.xlsx)", type=['xlsx'])
    if st.button("Sisteme Aktar"):
        if file:
            count = process_all_excel(file)
            if count: st.success(f"{count} ürün listelendi.")
    
    st.divider()
    if st.button("⚠️ VERİTABANINI TEMİZLE"):
        if os.path.exists('pazaryeri.db'):
            os.remove('pazaryeri.db')
            init_db()
            st.rerun()