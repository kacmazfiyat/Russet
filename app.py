import streamlit as st
import pandas as pd
import sqlite3
import os

# Sayfa Genişliği
st.set_page_config(page_title="Pro Yönetim v7", layout="wide")

def get_db_connection():
    """SQLite bağlantısı kurar."""
    return sqlite3.connect('pazaryeri.db', check_same_thread=False)

def init_db():
    """Tabloyu en temiz haliyle, id sütunu dahil oluşturur."""
    with get_db_connection() as conn:
        # Tablo yoksa oluştur, varsa dokunma
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

# Uygulama her yüklendiğinde veritabanını kontrol et
init_db()

def process_all_excel(uploaded_file):
    try:
        xls = pd.ExcelFile(uploaded_file)
        all_rows = []
        
        for sheet_name in xls.sheet_names:
            # Sayfayı ham veri olarak oku
            df = pd.read_excel(uploaded_file, sheet_name=sheet_name, header=None)
            df = df.dropna(how='all')

            for _, row in df.iterrows():
                # Excel yapınız: C=2 (Boyut), E=4 (İsim), O=14 (Fiyat)
                urun_adi = str(row[4]) if len(row) > 4 else ""
                fiyat = str(row[14]) if len(row) > 14 else "0"
                boyut = str(row[2]) if len(row) > 2 else ""

                # Başlıkları ve boş satırları ele
                clean_name = urun_adi.strip().upper()
                if clean_name and clean_name not in ["NAN", "MALZEME ADI", "ÜRÜN ADI"]:
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
        st.error(f"Dosya işleme sırasında hata: {e}")
        return None

# --- ARAYÜZ ---
st.title("💎 Pro Ürün Yönetimi")

menu = st.sidebar.radio("Menü", ["🔍 Arama & Liste", "📥 Veri Yükle"])

if menu == "📥 Veri Yükle":
    st.subheader("Excel'den Veri Aktarımı")
    file = st.file_uploader("Dosya Seç (.xlsx)", type=['xlsx'])
    
    if st.button("Verileri Kaydet", use_container_width=True):
        if file:
            with st.spinner("İşleniyor..."):
                count = process_all_excel(file)
                if count:
                    st.success(f"Başarılı! {count} kayıt eklendi.")
                    st.rerun()
        else:
            st.warning("Önce bir dosya yükleyin.")

    st.divider()
    if st.button("⚠️ VERİTABANINI SIFIRLA (Hataları Çözer)"):
        if os.path.exists('pazaryeri.db'):
            os.remove('pazaryeri.db') # Dosyayı fiziksel olarak sil
            init_db() # Yeni ve temiz tablo oluştur
            st.warning("Veritabanı silindi ve yeniden oluşturuldu. Lütfen sayfayı yenileyin.")

elif menu == "🔍 Arama & Liste":
    st.subheader("Ürün Filtreleme")
    search = st.text_input("Ürün adı veya kategori (sayfa) ara...", "")

    with get_db_connection() as conn:
        try:
            if search:
                # 'id' sütunu artık kesinlikle var olduğu için hata almayacağız
                query = "SELECT id, urun_adi, maliyet, sayfa_adi FROM products WHERE urun_adi LIKE ? OR sayfa_adi LIKE ?"
                df_view = pd.read_sql_query(query, conn, params=(f'%{search}%', f'%{search}%'))
            else:
                df_view = pd.read_sql_query("SELECT id, urun_adi, maliyet, sayfa_adi FROM products ORDER BY id DESC LIMIT 100", conn)

            if not df_view.empty:
                st.dataframe(df_view, use_container_width=True)
            else:
                st.info("Kayıtlı veri bulunamadı.")
        except Exception as e:
            st.error(f"Veri çekme hatası: {e}")
            st.info("Eğer hata almaya devam ediyorsanız 'Veri Yükle' sekmesinden veritabanını sıfırlayın.")