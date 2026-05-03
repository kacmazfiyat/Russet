import streamlit as st
import pandas as pd
import sqlite3
import os

# --- VERİTABANI ŞEMASI (GÜNCELLENDİ) ---
def get_db_connection():
    return sqlite3.connect('pazaryeri.db', check_same_thread=False)

def init_db():
    conn = get_db_connection()
    # Boy sütunu eklenmiş yeni tablo yapısı
    conn.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        urun_adi TEXT, 
        boy TEXT, 
        maliyet REAL, 
        doviz TEXT, 
        sayfa_adi TEXT, 
        dosya_adi TEXT)''')
    
    conn.execute('''CREATE TABLE IF NOT EXISTS settings (
        platform TEXT PRIMARY KEY, komisyon REAL, kargo REAL, 
        hizmet_bedeli REAL, kar_orani REAL, kdv_orani REAL, 
        kdv_dahil_mi INTEGER, eur_kuru REAL, usd_kuru REAL)''')
    
    # Mevcut veritabanına 'boy' sütunu ekleme kontrolü (Veri kaybını önler)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(products)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'boy' not in columns:
        conn.execute("ALTER TABLE products ADD COLUMN boy TEXT")
    conn.close()

init_db()

# --- GELİŞMİŞ EXCEL İŞLEME ---
def process_all_excel(uploaded_file):
    try:
        xls = pd.ExcelFile(uploaded_file)
        all_rows = []
        
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(uploaded_file, sheet_name=sheet_name, header=None)
            
            # Dinamik Sütun Bulucu
            price_col, name_col, size_col = -1, -1, -1
            start_row = 0
            
            for i in range(min(15, len(df))): 
                row_vals = [str(val).upper().strip() for val in df.iloc[i].values]
                if "BİRİM FİYATI" in row_vals:
                    price_col = row_vals.index("BİRİM FİYATI")
                if "MALZEME ADI" in row_vals or "ÜRÜN ADI" in row_vals:
                    # Hangi terim varsa onun indexini al
                    name_col = next(i for i, v in enumerate(row_vals) if v in ["MALZEME ADI", "ÜRÜN ADI"])
                # Boy sütunu genelde 'C' yani index 2'dir veya 'BOY' başlığı altındadır
                if "BOY" in row_vals or "ÖLÇÜ" in row_vals:
                    size_col = next(i for i, v in enumerate(row_vals) if v in ["BOY", "ÖLÇÜ"])
                elif size_col == -1 and len(row_vals) > 2: # Başlık yoksa C sütununu varsay
                    size_col = 2
                
                if price_col != -1 and name_col != -1:
                    start_row = i + 1
                    break
            
            if price_col == -1: continue 

            for _, row in df.iloc[start_row:].iterrows():
                raw_name = str(row[name_col]).strip()
                # Malzeme adının içindeki CM ibarelerini temizle (Opsiyonel güvenlik)
                clean_name = re.sub(r'\d+\s*CM', '', raw_name, flags=re.I).strip()
                
                boy_bilgisi = str(row[size_col]).strip() if not pd.isna(row[size_col]) else "-"
                fiyat_val = row[price_col]
                doviz_val = str(row[price_col + 1]).strip().upper() if len(row) > price_col + 1 else "TL"

                if clean_name and clean_name.upper() != "NAN" and not pd.isna(fiyat_val):
                    try:
                        f_temiz = float(str(fiyat_val).replace('.', '').replace(',', '.'))
                    except: f_temiz = 0.0
                    
                    if any(x in doviz_val for x in ["€", "EUR"]): d_tipi = "EUR"
                    elif any(x in doviz_val for x in ["$", "USD"]): d_tipi = "USD"
                    else: d_tipi = "TL"

                    all_rows.append((clean_name, boy_bilgisi, f_temiz, d_tipi, sheet_name, uploaded_file.name))

        with get_db_connection() as conn:
            conn.executemany("INSERT INTO products (urun_adi, boy, maliyet, doviz, sayfa_adi, dosya_adi) VALUES (?, ?, ?, ?, ?, ?)", all_rows)
        return len(all_rows)
    except Exception as e:
        st.error(f"Hata: {e}")
        return None

# --- ARAYÜZ ---
st.title("💎 Gelişmiş Ürün Paneli")
menu = st.sidebar.radio("Menü", ["🔍 Arama & Satış Hesapla", "⚙️ Ayarlar", "📥 Veri Yükle"])

if menu == "🔍 Arama & Satış Hesapla":
    with get_db_connection() as conn:
        s_df = pd.read_sql_query("SELECT * FROM settings", conn)
    
    if s_df.empty:
        st.warning("Ayarlar yapılmamış.")
    else:
        target_plat = st.selectbox("Platform", s_df['platform'])
        s = s_df[s_df['platform'] == target_plat].iloc[0]
        
        search = st.text_input("Ürün veya Boyut Ara...")
        with get_db_connection() as conn:
            # Boy sütunu da sorguya eklendi
            df = pd.read_sql_query("SELECT id, urun_adi, boy, maliyet, doviz FROM products WHERE urun_adi LIKE ? OR boy LIKE ?", 
                                   conn, params=(f'%{search}%', f'%{search}%'))

        if not df.empty:
            def calc(row):
                m = row['maliyet']
                if row['doviz'] == "EUR": m *= s['eur_kuru']
                elif row['doviz'] == "USD": m *= s['usd_kuru']
                m_net = m / (1 + (s['kdv_orani']/100)) if s['kdv_dahil_mi'] == 1 else m
                gider = m_net + (s['kargo']/1.2) + (s['hizmet_bedeli']/1.2)
                payda = 1 - ((s['komisyon'] + s['kar_orani'])/100)
                return round((gider/payda)*(1+(s['kdv_orani']/100)), 2) if payda > 0 else 0

            df['Satış Fiyatı'] = df.apply(calc, axis=1)
            
            st.data_editor(df, use_container_width=True, hide_index=True,
                column_config={
                    "id": None,
                    "urun_adi": st.column_config.TextColumn("Malzeme Adı", width="large"),
                    "boy": st.column_config.TextColumn("Boy", width="small"),
                    "maliyet": st.column_config.NumberColumn("Birim Fiyat", format="%.2f", alignment="center"),
                    "doviz": st.column_config.TextColumn("Döviz", alignment="center"),
                    "Satış Fiyatı": st.column_config.NumberColumn("Pazaryeri Fiyatı", format="%.2f TL", alignment="center")
                }
            )

# ... (Ayarlar ve Veri Yükle bölümleri v16 ile benzer kalacak) ...