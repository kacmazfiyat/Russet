import streamlit as st
import pandas as pd
import sqlite3
import os
import re

st.set_page_config(page_title="Pro Yönetim v17", layout="wide")

# --- VERİTABANI AYARLARI ---
def get_db_connection():
    return sqlite3.connect('pazaryeri.db', check_same_thread=False)

def init_db():
    with get_db_connection() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            urun_adi TEXT, boy TEXT, maliyet REAL, doviz TEXT, sayfa_adi TEXT, dosya_adi TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS settings (
            platform TEXT PRIMARY KEY, komisyon REAL, kargo REAL, 
            hizmet_bedeli REAL, kar_orani REAL, kdv_orani REAL, 
            kdv_dahil_mi INTEGER, eur_kuru REAL, usd_kuru REAL)''')
        
        # Eksik sütun kontrolü (Veri silmeden güncelleme)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(products)")
        cols = [c[1] for c in cursor.fetchall()]
        if 'boy' not in cols: conn.execute("ALTER TABLE products ADD COLUMN boy TEXT")
        if 'doviz' not in cols: conn.execute("ALTER TABLE products ADD COLUMN doviz TEXT DEFAULT 'TL'")
    conn.close()

init_db()

# --- EXCEL İŞLEME FONKSİYONU ---
def process_all_excel(uploaded_file):
    try:
        xls = pd.ExcelFile(uploaded_file)
        all_rows = []
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(uploaded_file, sheet_name=sheet_name, header=None)
            price_col, name_col, size_col = -1, -1, -1
            start_row = 0
            
            # Başlık Tarama
            for i in range(min(15, len(df))):
                row_vals = [str(val).upper().strip() for val in df.iloc[i].values]
                if "BİRİM FİYATI" in row_vals: price_col = row_vals.index("BİRİM FİYATI")
                if any(x in row_vals for x in ["MALZEME ADI", "ÜRÜN ADI"]):
                    name_col = next(idx for idx, v in enumerate(row_vals) if v in ["MALZEME ADI", "ÜRÜN ADI"])
                if any(x in row_vals for x in ["BOY", "ÖLÇÜ"]):
                    size_col = next(idx for idx, v in enumerate(row_vals) if v in ["BOY", "ÖLÇÜ"])
                elif size_col == -1 and len(row_vals) > 2: size_col = 2 # Varsayılan C sütunu

                if price_col != -1 and name_col != -1:
                    start_row = i + 1
                    break
            
            if price_col == -1: continue

            for _, row in df.iloc[start_row:].iterrows():
                raw_name = str(row[name_col]).strip()
                if not raw_name or raw_name.upper() == "NAN": continue
                
                # Temizleme: İsimden CM bilgilerini çıkar, boy sütununa yaz
                clean_name = re.sub(r'\d+\s*CM', '', raw_name, flags=re.I).strip()
                boy_val = str(row[size_col]).strip() if size_col != -1 else "-"
                
                # Fiyat ve Döviz (Sağdaki P sütunu)
                fiyat_raw = row[price_col]
                doviz_raw = str(row[price_col + 1]).strip().upper() if len(row) > price_col + 1 else "TL"
                
                # Döviz Tespiti
                if any(x in doviz_raw for x in ["€", "EUR"]): d_tipi = "EUR"
                elif any(x in doviz_raw for x in ["$", "USD"]): d_tipi = "USD"
                else: d_tipi = "TL"

                try:
                    f_clean = float(str(fiyat_raw).replace('.', '').replace(',', '.'))
                    all_rows.append((clean_name, boy_val, f_clean, d_tipi, sheet_name, uploaded_file.name))
                except: continue

        with get_db_connection() as conn:
            conn.executemany("INSERT INTO products (urun_adi, boy, maliyet, doviz, sayfa_adi, dosya_adi) VALUES (?, ?, ?, ?, ?, ?)", all_rows)
        return len(all_rows)
    except Exception as e:
        st.error(f"Hata: {e}")
        return None

# --- ARAYÜZ ---
menu = st.sidebar.radio("Menü", ["🔍 Arama & Düzenle", "⚙️ Ayarlar", "📥 Veri Yükle"])

# --- 1. ARAMA ---
if menu == "🔍 Arama & Düzenle":
    st.subheader("🔍 Ürün Analizi")
    with get_db_connection() as conn:
        s_df = pd.read_sql_query("SELECT * FROM settings", conn)
    
    if s_df.empty:
        st.info("Lütfen önce Ayarlar'dan platform kaydedin.")
    else:
        target = st.selectbox("Hesaplama Yapılacak Platform", s_df['platform'])
        s = s_df[s_df['platform'] == target].iloc[0]
        search = st.text_input("Ürün veya Boyut Ara...")
        
        with get_db_connection() as conn:
            df = pd.read_sql_query("SELECT id, urun_adi, boy, maliyet, doviz FROM products WHERE urun_adi LIKE ? OR boy LIKE ?", 
                                   conn, params=(f'%{search}%', f'%{search}%'))
        
        if not df.empty:
            def calc_price(row):
                m = row['maliyet']
                if row['doviz'] == "EUR": m *= s['eur_kuru']
                elif row['doviz'] == "USD": m *= s['usd_kuru']
                m_net = m / (1 + (s['kdv_orani']/100)) if s['kdv_dahil_mi'] == 1 else m
                gider = m_net + (s['kargo']/1.2) + (s['hizmet_bedeli']/1.2)
                payda = 1 - ((s['komisyon'] + s['kar_orani'])/100)
                return round((gider/payda)*(1+(s['kdv_orani']/100)), 2) if payda > 0 else 0

            df['Satış Fiyatı'] = df.apply(calc_price, axis=1)
            st.data_editor(df, use_container_width=True, hide_index=True,
                column_config={
                    "id": None, "maliyet": st.column_config.NumberColumn("Birim", format="%.2f"),
                    "doviz": st.column_config.TextColumn("Kur", alignment="center"),
                    "Satış Fiyatı": st.column_config.NumberColumn("Pazaryeri Satış", format="%.2f TL")
                })

# --- 2. AYARLAR ---
elif menu == "⚙️ Ayarlar":
    st.subheader("⚙️ Platform ve Kur Ayarları")
    platforms = ["Trendyol", "Hepsiburada", "Amazon", "N11"]
    sel_plat = st.selectbox("Platform", platforms)
    
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM settings WHERE platform = ?", (sel_plat,)).fetchone()
    
    dv = row if row else (sel_plat, 20.0, 80.0, 15.0, 30.0, 20.0, 0, 36.50, 33.50)
    
    with st.form("settings_form"):
        c1, c2, c3 = st.columns(3)
        kom = c1.number_input("Komisyon (%)", value=dv[1])
        kargo = c2.number_input("Kargo (TL)", value=dv[2])
        hizmet = c3.number_input("Hizmet (TL)", value=dv[3])
        kar = c1.number_input("Kâr (%)", value=dv[4])
        kdv = c2.selectbox("KDV (%)", [0, 1, 10, 20], index=3)
        kdv_d = c3.radio("Maliyet Tipi", ["KDV Hariç", "KDV Dahil"], index=dv[6])
        
        st.divider()
        st.markdown("### 💱 Güncel Döviz Kurları")
        cur1, cur2 = st.columns(2)
        e_k = cur1.number_input("EURO Kuru", value=dv[7])
        u_k = cur2.number_input("USD Kuru", value=dv[8])
        
        if st.form_submit_button("Ayarları Kaydet"):
            with get_db_connection() as conn:
                conn.execute("INSERT OR REPLACE INTO settings VALUES (?,?,?,?,?,?,?,?,?)", 
                             (sel_plat, kom, kargo, hizmet, kar, kdv, (1 if kdv_d=="KDV Dahil" else 0), e_k, u_k))
            st.success("Ayarlar güncellendi.")

# --- 3. VERİ YÜKLEME ---
elif menu == "📥 Veri Yükle":
    st.subheader("📥 Excel Veri Yükleme")
    file = st.file_uploader("Excel Dosyası Seçin", type=['xlsx'])
    
    if st.button("Verileri Sisteme Aktar"):
        if file:
            with st.spinner("Yükleniyor..."):
                count = process_all_excel(file)
                if count: st.success(f"{count} ürün başarıyla yüklendi.")
        else:
            st.warning("Lütfen bir dosya seçin.")
    
    st.divider()
    st.markdown("### 🛠️ Veritabanı Bakımı")
    if st.button("🔴 TÜM VERİLERİ SİL"):
        if os.path.exists('pazaryeri.db'):
            os.remove('pazaryeri.db')
            init_db()
            st.rerun()