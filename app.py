import streamlit as st
import pandas as pd
import sqlite3
import re
import os

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Pro Yönetim", layout="wide")

# --- VERİTABANI FONKSİYONLARI ---
def get_db_connection():
    conn = sqlite3.connect('pazaryeri.db', check_same_thread=False)
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barkod TEXT,
            urun_adi TEXT,
            maliyet REAL,
            dosya_adi TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- EXCEL İŞLEME MOTORU ---
def process_excel(uploaded_file):
    try:
        xls = pd.ExcelFile(uploaded_file)
        all_data = []
        
        for sheet_name in xls.sheet_names:
            # Sizin Excel'de başlıklar 4. satırda (Pandas index: 3)
            df = pd.read_excel(uploaded_file, sheet_name=sheet_name, header=3)
            
            # Sütun isimlerini temizle (Büyük harf ve boşluk silme)
            df.columns = [str(c).strip().upper() for c in df.columns]

            # Sizin Excel sütunlarını eşleştiriyoruz
            # 'MALZEME ADI' -> urun_adi, 'BİRİM FİYATI' -> maliyet, 'CM.' -> boyut
            mapping = {'MALZEME ADI': 'urun_adi', 'BİRİM FİYATI': 'maliyet', 'CM.': 'boyut'}
            df = df.rename(columns=mapping)

            # Sadece ihtiyacımız olanları al
            needed = [c for c in ['urun_adi', 'maliyet', 'boyut'] if c in df.columns]
            df = df[needed]

            # Boş olanları temizle
            df = df.dropna(subset=['urun_adi', 'maliyet'])

            # Fiyat temizleme (TL, virgül, nokta düzeltme)
            def clean_price(val):
                try:
                    s = str(val).replace('.', '').replace(',', '.')
                    res = re.findall(r"[-+]?\d*\.\d+|\d+", s)
                    return float(res[0]) if res else 0.0
                except: return 0.0

            df['maliyet'] = df['maliyet'].apply(clean_price)
            df = df[df['maliyet'] > 0]

            # İsim ve boyutu birleştir
            if 'boyut' in df.columns:
                df['urun_adi'] = df['urun_adi'].astype(str) + " (" + df['boyut'].astype(str) + " CM)"

            all_data.append(df)

        if not all_data: return None

        final_df = pd.concat(all_data, ignore_index=True)
        final_df['dosya_adi'] = uploaded_file.name
        final_df['barkod'] = [f"BRK-{1000 + i}" for i in range(len(final_df))]
        
        # Veritabanına kaydet
        conn = get_db_connection()
        final_df[['barkod', 'urun_adi', 'maliyet', 'dosya_adi']].to_sql('products', conn, if_exists='append', index=False)
        conn.close()
        
        return len(final_df)
    except Exception as e:
        st.error(f"Hata oluştu: {e}")
        return None

# --- ARAYÜZ (STREAMLIT) ---
st.title("💎 Pro Yönetim - Veri Sistemi")

menu = st.sidebar.radio("Menü Seçiniz:", ["Analiz", "Veri Yükleme"])

if menu == "Veri Yükleme":
    st.subheader("📁 Veri Yönetimi")
    uploaded_file = st.file_uploader("Excel Dosyası Seçin", type=['xlsx'])
    
    if st.button("Excel Yükle"):
        if uploaded_file:
            with st.spinner("Dosya işleniyor..."):
                count = process_excel(uploaded_file)
                if count:
                    st.success(f"Başarılı! {count} ürün sisteme eklendi.")
                else:
                    st.error("Dosya işlenemedi. Sütun isimlerini kontrol edin.")
        else:
            st.warning("Lütfen bir dosya seçin.")

    if st.button("Hafızayı Temizle (Veritabanını Sıfırla)"):
        conn = get_db_connection()
        conn.execute("DELETE FROM products")
        conn.commit()
        conn.close()
        st.info("Tüm veriler temizlendi.")

elif menu == "Analiz":
    st.subheader("📊 Ürün Analizi")
    conn = get_db_connection()
    df_list = pd.read_sql_query("SELECT * FROM products", conn)
    conn.close()

    if not df_list.empty:
        st.dataframe(df_list, use_container_width=True)
        st.write(f"Toplam kayıtlı ürün sayısı: {len(df_list)}")
    else:
        st.info("Henüz veri yüklenmemiş.")