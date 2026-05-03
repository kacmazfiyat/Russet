import streamlit as st
import pandas as pd
import sqlite3
import re

# Sayfa ayarları
st.set_page_config(page_title="Pro Yönetim v6", layout="wide")

def get_db_connection():
    """Veritabanı bağlantısı kurar."""
    return sqlite3.connect('pazaryeri.db', check_same_thread=False)

def init_db():
    """Tabloyu oluşturur veya eksik sütunları tamamlar."""
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                urun_adi TEXT,
                maliyet TEXT,
                sayfa_adi TEXT,
                dosya_adi TEXT
            )
        ''')
    conn.close()

# Uygulama açılışında veritabanını kontrol et
init_db()

def process_all_excel(uploaded_file):
    try:
        xls = pd.ExcelFile(uploaded_file)
        all_rows = []
        
        for sheet_name in xls.sheet_names:
            # Sayfayı ham oku, başlık aramayı bırak
            df = pd.read_excel(uploaded_file, sheet_name=sheet_name, header=None)
            df = df.dropna(how='all')

            for _, row in df.iterrows():
                # Sizin Excel yapınızda:
                # E sütunu (index 4) -> Ürün Adı
                # O sütunu (index 14) -> Fiyat
                # C sütunu (index 2) -> Boyut
                
                urun_adi = str(row[4]) if len(row) > 4 else ""
                fiyat = str(row[14]) if len(row) > 14 else "0"
                boyut = str(row[2]) if len(row) > 2 else ""

                # Sadece içinde gerçek veri olan satırları al
                if urun_adi.strip() and urun_adi.upper() not in ["NAN", "MALZEME ADI", "ÜRÜN ADI"]:
                    full_name = f"{urun_adi} {boyut}".strip()
                    all_rows.append((full_name, fiyat, sheet_name, uploaded_file.name))

        if not all_rows:
            return None

        with get_db_connection() as db_conn:
            db_conn.executemany(
                "INSERT INTO products (urun_adi, maliyet, sayfa_adi, dosya_adi) VALUES (?, ?, ?, ?)", 
                all_rows
            )
        return len(all_rows)
    except Exception as e:
        st.error(f"Excel işleme hatası: {e}")
        return None

# --- ARAYÜZ ---
st.title("💎 Ürün Yönetim Sistemi")

menu = st.sidebar.radio("Bölüm Seçin", ["🔍 Ürün Arama ve Liste", "📥 Yeni Veri Yükle"])

if menu == "📥 Yeni Veri Yükle":
    st.subheader("Excel Verilerini Sisteme Aktar")
    file = st.file_uploader("Fiyat Listesi Seçin (.xlsx)", type=['xlsx'])
    
    if st.button("Tüm Listeyi Süpür ve Kaydet", use_container_width=True):
        if file:
            with st.spinner("Veriler işleniyor..."):
                count = process_all_excel(file)
                if count:
                    st.success(f"Başarılı! {count} satır sisteme eklendi.")
                else:
                    st.error("Veri ayıklanamadı.")
        else:
            st.warning("Lütfen dosya seçin.")

    if st.button("🗑️ Veritabanını Tamamen Sıfırla"):
        with get_db_connection() as conn:
            conn.execute("DROP TABLE IF EXISTS products")
        init_db() # Tabloyu temiz olarak yeniden kur
        st.warning("Veritabanı sıfırlandı.")

elif menu == "🔍 Ürün Arama ve Liste":
    st.subheader("Kayıtlı Ürünler Arasında Ara")
    
    # Arama kutusu
    search_query = st.text_input("Ürün adı, sayfa veya kelime girin...", "")

    with get_db_connection() as conn:
        try:
            if search_query:
                # SQL injection korumalı güvenli arama
                query = "SELECT * FROM products WHERE urun_adi LIKE ? OR sayfa_adi LIKE ?"
                params = (f'%{search_query}%', f'%{search_query}%')
                df_view = pd.read_sql_query(query, conn, params=params)
            else:
                # Arama yapılmadıysa son 100 kaydı göster
                df_view = pd.read_sql_query("SELECT * FROM products ORDER BY id DESC LIMIT 100", conn)

            if not df_view.empty:
                st.write(f"Bulunan Kayıt: {len(df_view)}")
                st.dataframe(df_view, use_container_width=True)
            else:
                st.info("Henüz veri yüklenmemiş veya sonuç bulunamadı.")
        except Exception as e:
            st.error(f"Arama hatası: {e}")