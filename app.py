import streamlit as st
import pandas as pd
import sqlite3
import re

st.set_page_config(page_title="Pro Yönetim v5", layout="wide")

def get_db_connection():
    return sqlite3.connect('pazaryeri.db', check_same_thread=False)

# Veritabanı (Ürün Adı ve Fiyat odaklı basit yapı)
with get_db_connection() as conn:
    conn.execute('''CREATE TABLE IF NOT EXISTS products 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, urun_adi TEXT, maliyet TEXT, sayfa_adi TEXT)''')

def process_all_excel(uploaded_file):
    try:
        xls = pd.ExcelFile(uploaded_file)
        all_rows = []
        
        for sheet_name in xls.sheet_names:
            # Sayfayı ham veri olarak oku (hiçbir satırı başlık yapma)
            df = pd.read_excel(uploaded_file, sheet_name=sheet_name, header=None)
            
            # Boş satırları temizle
            df = df.dropna(how='all')

            for _, row in df.iterrows():
                # Satırdaki verileri anlamlı hale getir
                # Genelde Ürün İsmi E (4. index), Fiyat O (14. index) sütunundadır.
                # Ama biz garanti olsun diye tüm satırı birleştirip 'arama' için saklayabiliriz.
                
                # Sizin dosya yapınıza göre:
                urun_adi = str(row[4]) if len(row) > 4 else ""
                fiyat = str(row[14]) if len(row) > 14 else "0"
                boyut = str(row[2]) if len(row) > 2 else ""

                if urun_adi.strip() and urun_adi != "nan" and urun_adi != "MALZEME ADI":
                    full_name = f"{urun_adi} {boyut}".strip()
                    all_rows.append((full_name, fiyat, sheet_name))

        if not all_rows: return None

        # Veritabanına toplu kayıt
        with get_db_connection() as db_conn:
            db_conn.executemany("INSERT INTO products (urun_adi, maliyet, sayfa_adi) VALUES (?, ?, ?)", all_rows)
        
        return len(all_rows)
    except Exception as e:
        st.error(f"Sistem Hatası: {str(e)}")
        return None

# --- ARAYÜZ ---
st.title("💎 Ürün Yönetimi ve Arama")

menu = st.sidebar.selectbox("İşlem Seçin", ["🔍 Ürün Ara / Analiz", "📥 Excel Yükle"])

if menu == "📥 Excel Yükle":
    st.subheader("Excel'deki Tüm Ürünleri Sisteme Aktar")
    file = st.file_uploader("Dosyayı buraya bırakın", type=['xlsx'])
    if st.button("Tüm Sayfaları Tara ve Kaydet"):
        if file:
            count = process_all_excel(file)
            if count:
                st.success(f"İşlem Tamam! {count} satır veri sisteme çekildi.")
            else:
                st.error("Veri çekilemedi.")
        
    if st.button("🗑️ Hafızayı Sıfırla"):
        with get_db_connection() as conn:
            conn.execute("DELETE FROM products")
        st.warning("Tüm ürünler silindi.")

elif menu == "🔍 Ürün Ara / Analiz":
    st.subheader("Ürün Arama")
    search_query = st.text_input("Ürün adı, kod veya anahtar kelime yazın:", "")

    with get_db_connection() as conn:
        if search_query:
            # Kullanıcının yazdığı kelimeyi veritabanında ara
            query = f"SELECT * FROM products WHERE urun_adi LIKE '%{search_query}%' OR sayfa_adi LIKE '%{search_query}%'"
            df_view = pd.read_sql_query(query, conn)
        else:
            df_view = pd.read_sql_query("SELECT * FROM products ORDER BY id DESC LIMIT 100", conn)

        if not df_view.empty:
            st.write(f"Bulunan Sonuç: {len(df_view)}")
            st.dataframe(df_view, use_container_width=True)
        else:
            st.info("Sonuç bulunamadı.")