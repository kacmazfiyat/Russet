import streamlit as st
import pandas as pd
import sqlite3
import os
import re

st.set_page_config(page_title="Pro Yönetim v15", layout="wide")

# --- VERİTABANI GÜNCELLEME (VERİ SİLMEYEN SİSTEM) ---
def get_db_connection():
    return sqlite3.connect('pazaryeri.db', check_same_thread=False)

def init_db():
    conn = get_db_connection()
    # Mevcut tabloları oluştur (yoksa)
    conn.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        urun_adi TEXT, maliyet REAL, sayfa_adi TEXT, dosya_adi TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS settings (
        platform TEXT PRIMARY KEY, komisyon REAL, kargo REAL, 
        hizmet_bedeli REAL, kar_orani REAL, kdv_orani REAL, kdv_dahil_mi INTEGER)''')
    
    # --- EKSİK SÜTUNLARI EKLE (ALTER TABLE) ---
    # Bu kısım verileri silmeden yeni özellikleri ekler
    cursor = conn.cursor()
    
    # Products tablosuna 'doviz' ekle
    cursor.execute("PRAGMA table_info(products)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'doviz' not in columns:
        conn.execute("ALTER TABLE products ADD COLUMN doviz TEXT DEFAULT 'TL'")
    
    # Settings tablosuna kur sütunlarını ekle
    cursor.execute("PRAGMA table_info(settings)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'eur_kuru' not in columns:
        conn.execute("ALTER TABLE settings ADD COLUMN eur_kuru REAL DEFAULT 36.50")
    if 'usd_kuru' not in columns:
        conn.execute("ALTER TABLE settings ADD COLUMN usd_kuru REAL DEFAULT 33.50")
    
    conn.commit()
    conn.close()

init_db()

# --- EXCEL İŞLEME (DÖVİZ SÜTUNU: P / INDEX: 15) ---
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
                # Sağındaki sütun (P) döviz türü
                doviz_ham = str(row[15]).strip().upper() if len(row) > 15 else "TL"
                boyut = str(row[2]) if len(row) > 2 else ""

                if any(x in doviz_ham for x in ["€", "EUR", "EURO"]): d_tipi = "EUR"
                elif any(x in doviz_ham for x in ["$", "USD", "DOLAR"]): d_tipi = "USD"
                else: d_tipi = "TL"

                try:
                    f = float(str(fiyat_ham).replace('.', '').replace(',', '.'))
                except: f = 0.0

                if urun_adi.strip().upper() not in ["NAN", "MALZEME ADI"] and urun_adi.strip():
                    full_name = f"{urun_adi} {boyut}".strip()
                    all_rows.append((full_name, f, d_tipi, sheet_name, uploaded_file.name))

        with get_db_connection() as db:
            db.executemany("INSERT INTO products (urun_adi, maliyet, doviz, sayfa_adi, dosya_adi) VALUES (?, ?, ?, ?, ?)", all_rows)
        return len(all_rows)
    except Exception as e:
        st.error(f"Hata: {e}")
        return None

# --- MENÜ ---
menu = st.sidebar.radio("Menü", ["🔍 Arama & Düzenle", "⚙️ Ayarlar (Kur/Komisyon)", "📥 Veri Yükle"])

# --- 1. AYARLAR (KUR EKLEMELİ) ---
if menu == "⚙️ Ayarlar (Kur/Komisyon)":
    st.subheader("Platform ve Döviz Ayarları")
    platforms = ["Trendyol", "Hepsiburada", "Amazon", "N11"]
    selected_plat = st.selectbox("Platform Seçin", platforms)
    
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM settings WHERE platform = ?", (selected_plat,)).fetchone()
    
    # Eski ayarları koru, kur yoksa varsayılan ata
    dv = row if row else (selected_plat, 20.0, 80.0, 15.0, 30.0, 20.0, 0, 36.50, 33.50)
    
    with st.form("settings_form"):
        col1, col2, col3 = st.columns(3)
        kom = col1.number_input("Komisyon (%)", value=dv[1])
        kargo = col2.number_input("Kargo (TL)", value=dv[2])
        hizmet = col3.number_input("Hizmet (TL)", value=dv[3])
        kar = col1.number_input("Kâr (%)", value=dv[4])
        kdv = col2.selectbox("KDV (%)", [0, 1, 10, 20], index=3)
        kdv_dahil = col3.radio("Alış Fiyatı", ["KDV Hariç", "KDV Dahil"], index=dv[6])
        
        st.divider()
        st.markdown("### 💱 Güncel Döviz Kurları")
        c1, c2 = st.columns(2)
        eur_kur = c1.number_input("EURO Kuru", value=dv[7] if len(dv)>7 else 36.50)
        usd_kur = c2.number_input("USD Kuru", value=dv[8] if len(dv)>8 else 33.50)
        
        if st.form_submit_button("Ayarları Güncelle"):
            with get_db_connection() as conn:
                conn.execute("INSERT OR REPLACE INTO settings VALUES (?,?,?,?,?,?,?,?,?)", 
                             (selected_plat, kom, kargo, hizmet, kar, kdv, (1 if kdv_dahil=="KDV Dahil" else 0), eur_kur, usd_kur))
            st.success("Ayarlar kaydedildi.")

# --- 2. ANALİZ & DÜZENLEME ---
elif menu == "🔍 Arama & Düzenle":
    st.subheader("Ürün Analiz ve Fiyatlandırma")
    with get_db_connection() as conn:
        s_df = pd.read_sql_query("SELECT * FROM settings", conn)
    
    if s_df.empty:
        st.info("Lütfen önce Ayarlar sekmesinden bir platform kurun.")
    else:
        target_plat = st.selectbox("Platform", s_df['platform'])
        s = s_df[s_df['platform'] == target_plat].iloc[0]
        search = st.text_input("Ürün ara...")
        
        with get_db_connection() as conn:
            df = pd.read_sql_query("SELECT id, urun_adi, maliyet, doviz, sayfa_adi FROM products WHERE urun_adi LIKE ?", conn, params=(f'%{search}%',))

        if not df.empty:
            def calc(row):
                m = row['maliyet']
                if row['doviz'] == "EUR": m *= s['eur_kuru']
                elif row['doviz'] == "USD": m *= s['usd_kuru']
                m_net = m / (1 + (s['kdv_orani']/100)) if s['kdv_dahil_mi'] == 1 else m
                gider = m_net + (s['kargo']/1.2) + (s['hizmet_bedeli']/1.2)
                payda = 1 - ((s['komisyon'] + s['kar_orani'])/100)
                return round((gider/payda)*(1+(s['kdv_orani']/100)), 2) if payda > 0 else 0

            df['Pazaryeri Satış'] = df.apply(calc, axis=1)
            st.data_editor(df, use_container_width=True, hide_index=True,
                           column_config={
                               "id": None,
                               "maliyet": st.column_config.NumberColumn("Alış", alignment="center"),
                               "doviz": st.column_config.TextColumn("Döviz", alignment="center"),
                               "Pazaryeri Satış": st.column_config.NumberColumn("Satış", format="%.2f TL", alignment="center")
                           })

# --- 3. VERİ YÜKLEME ---
elif menu == "📥 Veri Yükle":
    st.subheader("📦 Veri Yönetimi")
    f = st.file_uploader("Excel Yükle", type=['xlsx'])
    if st.button("Sisteme Aktar"):
        if f:
            count = process_all_excel(f)
            if count: st.success(f"{count} ürün başarıyla eklendi.")
    
    st.divider()
    if st.button("⚠️ Veritabanını Onar (Sütun Hataları İçin)"):
        init_db()
        st.success("Tablo yapısı güncellendi, veriler korundu.")