import streamlit as st
import pandas as pd
import sqlite3
import os
import re

# --- DB VE TABLO AYARLARI ---
def get_db_connection():
    return sqlite3.connect('pazaryeri.db', check_same_thread=False)

def init_db():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        urun_adi TEXT, maliyet REAL, doviz TEXT, sayfa_adi TEXT, dosya_adi TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS settings (
        platform TEXT PRIMARY KEY, komisyon REAL, kargo REAL, 
        hizmet_bedeli REAL, kar_orani REAL, kdv_orani REAL, 
        kdv_dahil_mi INTEGER, eur_kuru REAL, usd_kuru REAL)''')
    
    # Sütun kontrolü (Veri silmeden güncelleme)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(products)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'doviz' not in columns:
        conn.execute("ALTER TABLE products ADD COLUMN doviz TEXT DEFAULT 'TL'")
    conn.close()

init_db()

# --- AKILLI EXCEL İŞLEME ---
def process_all_excel(uploaded_file):
    try:
        xls = pd.ExcelFile(uploaded_file)
        all_rows = []
        
        for sheet_name in xls.sheet_names:
            # Sayfayı ham veri olarak oku
            df = pd.read_excel(uploaded_file, sheet_name=sheet_name, header=None)
            
            # 1. Başlık Satırını Bul (Genelde ilk 10 satırda olur)
            price_col = -1
            name_col = -1
            
            for i in range(10): 
                row_vals = [str(val).upper() for val in df.iloc[i].values]
                if "BİRİM FİYATI" in row_vals:
                    price_col = row_vals.index("BİRİM FİYATI")
                if "MALZEME ADI" in row_vals or "ÜRÜN ADI" in row_vals:
                    name_col = row_vals.index(next(x for x in row_vals if x in ["MALZEME ADI", "ÜRÜN ADI"]))
                
                if price_col != -1 and name_col != -1:
                    start_row = i + 1
                    break
            
            if price_col == -1: continue # Başlık bulunamazsa sayfayı atla

            # 2. Verileri Çek
            for index, row in df.iloc[start_row:].iterrows():
                urun_adi = str(row[name_col]).strip() if not pd.isna(row[name_col]) else ""
                
                # Fiyat ve Döviz (Sağındaki sütun)
                fiyat_val = row[price_col]
                doviz_val = str(row[price_col + 1]).strip().upper() if len(row) > price_col + 1 else "TL"

                if urun_adi and urun_adi != "NAN" and not pd.isna(fiyat_val):
                    # Fiyat temizleme
                    try:
                        fiyat_temiz = float(str(fiyat_val).replace('.', '').replace(',', '.'))
                    except:
                        fiyat_temiz = 0.0
                    
                    # Döviz normalizasyonu
                    if any(x in doviz_val for x in ["€", "EUR"]): d_tipi = "EUR"
                    elif any(x in doviz_val for x in ["$", "USD"]): d_tipi = "USD"
                    else: d_tipi = "TL"

                    all_rows.append((urun_adi, fiyat_temiz, d_tipi, sheet_name, uploaded_file.name))

        if all_rows:
            with get_db_connection() as conn:
                conn.executemany("INSERT INTO products (urun_adi, maliyet, doviz, sayfa_adi, dosya_adi) VALUES (?, ?, ?, ?, ?)", all_rows)
            return len(all_rows)
    except Exception as e:
        st.error(f"Hata oluştu: {e}")
        return None

# --- ARAYÜZ (GÜNCELLENDİ) ---
st.title("💎 Dinamik Fiyat Yönetimi")
menu = st.sidebar.radio("Menü", ["🔍 Arama & Düzenle", "⚙️ Ayarlar", "📥 Veri Yükle"])

if menu == "🔍 Arama & Düzenle":
    with get_db_connection() as conn:
        s_df = pd.read_sql_query("SELECT * FROM settings", conn)
    
    if s_df.empty:
        st.warning("Lütfen önce Ayarlar'dan platform kaydedin.")
    else:
        target_plat = st.selectbox("Platform", s_df['platform'])
        s = s_df[s_df['platform'] == target_plat].iloc[0]
        
        search = st.text_input("Ürün Ara...")
        with get_db_connection() as conn:
            df = pd.read_sql_query("SELECT id, urun_adi, maliyet, doviz FROM products WHERE urun_adi LIKE ?", conn, params=(f'%{search}%',))

        if not df.empty:
            def calculate(row):
                m = row['maliyet']
                # Döviz Çevrimi (Ayarlardaki kur ile)
                if row['doviz'] == "EUR": m *= s['eur_kuru']
                elif row['doviz'] == "USD": m *= s['usd_kuru']
                
                m_haric = m / (1 + (s['kdv_orani']/100)) if s['kdv_dahil_mi'] == 1 else m
                gider = m_haric + (s['kargo']/1.2) + (s['hizmet_bedeli']/1.2)
                payda = 1 - ((s['komisyon'] + s['kar_orani'])/100)
                return round((gider/payda)*(1+(s['kdv_orani']/100)), 2) if payda > 0 else 0

            df['Satış Fiyatı'] = df.apply(calculate, axis=1)
            
            # Düzenlenebilir Tablo
            st.data_editor(df, use_container_width=True, hide_index=True,
                column_config={
                    "id": None,
                    "maliyet": st.column_config.NumberColumn("Birim Fiyat", format="%.2f", alignment="center"),
                    "doviz": st.column_config.TextColumn("Kur", alignment="center"),
                    "Satış Fiyatı": st.column_config.NumberColumn("Trendyol Fiyatı", format="%.2f TL", alignment="center")
                }
            )

elif menu == "⚙️ Ayarlar":
    # (V15'teki ayarlar bloğunu buraya aynen ekleyebilirsiniz, kurlar dahil)
    st.info("Kurları ve platform komisyonlarını buradan güncelleyin.")
    # ... Ayarlar Formu ...

elif menu == "📥 Veri Yükle":
    st.subheader("Excel Verisi Yükle")
    f = st.file_uploader("Excel", type=['xlsx'])
    if st.button("Kaydet"):
        if f:
            c = process_all_excel(f)
            if c: st.success(f"{c} ürün başarıyla kaydedildi.")