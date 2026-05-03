import streamlit as st
import pandas as pd
import sqlite3
import re
import os

st.set_page_config(page_title="Pro Yönetim v3", layout="wide")

def get_db_connection():
    return sqlite3.connect('pazaryeri.db', check_same_thread=False)

# Veritabanını sessizce hazırla
with get_db_connection() as conn:
    conn.execute('''CREATE TABLE IF NOT EXISTS products 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, barkod TEXT, urun_adi TEXT, maliyet REAL, dosya_adi TEXT)''')

def process_excel(uploaded_file):
    try:
        xls = pd.ExcelFile(uploaded_file)
        all_data = []
        
        for sheet_name in xls.sheet_names:
            # Sayfayı ham veri olarak oku (hiçbir şeyi başlık kabul etme)
            df_raw = pd.read_excel(uploaded_file, sheet_name=sheet_name, header=None)
            
            # 1. BAŞLIK SATIRINI BUL (Dinamik Tarama)
            header_idx = None
            for i, row in df_raw.iterrows():
                row_str = " ".join([str(val).upper() for val in row.values if pd.notna(val)])
                if "MALZEME ADI" in row_str or "BİRİM FİYAT" in row_str or "FİYAT" in row_str:
                    header_idx = i
                    break
            
            # Eğer başlık satırı bulunamazsa zorla 3. satırı (index 3) dene
            if header_idx is None:
                header_idx = 3 

            # Veriyi o satırdan itibaren al
            df = pd.read_excel(uploaded_file, sheet_name=sheet_name, header=header_idx)
            
            # Sütun isimlerini normalize et
            df.columns = [str(c).strip().upper() for c in df.columns]

            # 2. ESNEK EŞLEŞTİRME
            col_map = {}
            for col in df.columns:
                if any(x in col for x in ["MALZEME ADI", "ÜRÜN", "URUN", "AD"]):
                    col_map[col] = "urun_adi"
                elif any(x in col for x in ["FİYAT", "FIYAT", "MALİYET", "BİRİM"]):
                    col_map[col] = "maliyet"
                elif any(x in col for x in ["CM", "BOYUT"]):
                    col_map[col] = "boyut"

            df = df.rename(columns=col_map)

            # 3. BAŞARISIZ OLURSA SÜTUN SIRASINA GÜVEN (A=0, B=1...)
            if "urun_adi" not in df.columns and df.shape[1] >= 5:
                df.rename(columns={df.columns[4]: "urun_adi"}, inplace=True) # E Sütunu
            if "maliyet" not in df.columns and df.shape[1] >= 15:
                df.rename(columns={df.columns[14]: "maliyet"}, inplace=True) # O Sütunu

            # Temel sütunlar hala yoksa bu sayfayı pas geç
            if "urun_adi" not in df.columns or "maliyet" not in df.columns:
                continue

            # Veri Temizliği
            df = df.dropna(subset=['urun_adi', 'maliyet']).copy()
            
            def clean_price(val):
                try:
                    s = str(val).replace('.', '').replace(',', '.')
                    res = re.findall(r"[-+]?\d*\.\d+|\d+", s)
                    return float(res[0]) if res else 0.0
                except: return 0.0

            df['maliyet'] = df['maliyet'].apply(clean_price)
            df = df[df['maliyet'] > 0]

            # Boyut ekleme
            if 'boyut' in df.columns:
                df['urun_adi'] = df['urun_adi'].astype(str) + " (" + df['boyut'].astype(str) + " CM)"

            all_data.append(df[['urun_adi', 'maliyet']])

        if not all_data: return None

        final_df = pd.concat(all_data, ignore_index=True)
        final_df['dosya_adi'] = uploaded_file.name
        final_df['barkod'] = [f"BRK-{i+1000}" for i in range(len(final_df))]
        
        with get_db_connection() as db_conn:
            final_df[['barkod', 'urun_adi', 'maliyet', 'dosya_adi']].to_sql('products', db_conn, if_exists='append', index=False)
        
        return len(final_df)
    except Exception as e:
        st.error(f"Sistem Hatası: {str(e)}")
        return None

# --- ARAYÜZ ---
st.title("💎 Pro Yönetim Arayüzü")

tab_analiz, tab_yukle = st.tabs(["📊 Analiz", "📁 Veri Yükleme"])

with tab_yukle:
    st.info("İpucu: Excel dosyanızda 'MALZEME ADI' ve 'BİRİM FİYATI' başlıklarının olduğundan emin olun.")
    file = st.file_uploader("Excel Yükle", type=['xlsx'])
    if st.button("Veritabanına İşle", use_container_width=True):
        if file:
            count = process_excel(file)
            if count:
                st.success(f"İşlem Başarılı: {count} ürün eklendi.")
                st.rerun()
            else:
                st.error("Hata: Sütunlar otomatik eşleştirilemedi. Lütfen başlıkları kontrol edin.")
        else:
            st.warning("Dosya seçilmedi.")

    if st.button("🗑️ Tüm Verileri Sıfırla"):
        with get_db_connection() as conn:
            conn.execute("DELETE FROM products")
        st.warning("Veritabanı boşaltıldı.")

with tab_analiz:
    with get_db_connection() as conn:
        try:
            df_view = pd.read_sql_query("SELECT * FROM products ORDER BY id DESC", conn)
            if not df_view.empty:
                st.dataframe(df_view, use_container_width=True)
            else:
                st.write("Henüz veri yüklenmemiş.")
        except:
            st.write("Veritabanı henüz hazır değil.")