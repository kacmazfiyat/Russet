import streamlit as st
import pandas as pd
import sqlite3
import re

st.set_page_config(page_title="Pro Yönetim", layout="wide")

def get_db_connection():
    return sqlite3.connect('pazaryeri.db', check_same_thread=False)

# Veritabanı başlangıç ayarı
conn = get_db_connection()
conn.execute('''CREATE TABLE IF NOT EXISTS products 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, barkod TEXT, urun_adi TEXT, maliyet REAL, dosya_adi TEXT)''')
conn.close()

def process_excel(uploaded_file):
    try:
        xls = pd.ExcelFile(uploaded_file)
        all_data = []
        
        for sheet_name in xls.sheet_names:
            # Sayfayı ham oku
            df_raw = pd.read_excel(uploaded_file, sheet_name=sheet_name, header=None)
            
            # Başlık satırını bul (İçinde "MALZEME ADI" veya "FİYAT" geçen ilk satırı arar)
            header_idx = None
            for i, row in df_raw.iterrows():
                row_str = " ".join([str(val).upper() for val in row.values if pd.notna(val)])
                if "MALZEME ADI" in row_str or "BİRİM FİYATI" in row_str:
                    header_idx = i
                    break
            
            if header_idx is None:
                continue

            # Sayfayı o satırdan itibaren başlık kabul ederek tekrar oku
            df = pd.read_excel(uploaded_file, sheet_name=sheet_name, header=header_idx)
            
            # Sütun isimlerini temizle (Büyük harf ve boşlukları at)
            df.columns = [str(c).strip().upper() for c in df.columns]

            # DİNAMİK İSİM BULUCU (İçerik taraması yapar)
            col_map = {}
            for col in df.columns:
                if "MALZEME ADI" in col or "ÜRÜN ADI" in col:
                    col_map[col] = "urun_adi"
                elif "FİYAT" in col or "MALİYET" in col:
                    col_map[col] = "maliyet"
                elif "CM" in col or "BOYUT" in col:
                    col_map[col] = "boyut"

            df = df.rename(columns=col_map)

            # Sadece eşleşen sütunları al
            found_cols = [c for c in ["urun_adi", "maliyet", "boyut"] if c in df.columns]
            if "urun_adi" not in df.columns or "maliyet" not in df.columns:
                continue # Kritik sütunlar yoksa atla
                
            df = df[found_cols].copy()
            df = df.dropna(subset=['urun_adi', 'maliyet'])

            # Fiyat temizleme
            def clean_price(val):
                try:
                    s = str(val).replace('.', '').replace(',', '.')
                    res = re.findall(r"[-+]?\d*\.\d+|\d+", s)
                    return float(res[0]) if res else 0.0
                except: return 0.0

            df['maliyet'] = df['maliyet'].apply(clean_price)
            df = df[df['maliyet'] > 0]

            # Boyutu isme ekle (Eğer varsa)
            if 'boyut' in df.columns:
                df['urun_adi'] = df['urun_adi'].astype(str) + " (" + df['boyut'].astype(str) + " CM)"

            all_data.append(df)

        if not all_data: return None

        final_df = pd.concat(all_data, ignore_index=True)
        final_df['dosya_adi'] = uploaded_file.name
        final_df['barkod'] = [f"BRK-{3000 + i}" for i in range(len(final_df))]
        
        db_conn = get_db_connection()
        final_df[['barkod', 'urun_adi', 'maliyet', 'dosya_adi']].to_sql('products', db_conn, if_exists='append', index=False)
        db_conn.close()
        
        return len(final_df)
    except Exception as e:
        st.error(f"Teknik bir hata oluştu: {e}")
        return None

# --- ARAYÜZ ---
st.title("💎 Pro Yönetim")
tab1, tab2 = st.tabs(["📊 Analiz", "📁 Veri Yükleme"])

with tab2:
    st.info("Sistem sütunları isme göre bulur: 'MALZEME ADI', 'BİRİM FİYATI' ve 'CM.' başlıklarını arar.")
    uploaded_file = st.file_uploader("Excel Dosyası Seçin", type=['xlsx'])
    if st.button("Hafızaya Al"):
        if uploaded_file:
            count = process_excel(uploaded_file)
            if count:
                st.success(f"{count} adet ürün başarıyla listeye eklendi!")
            else:
                st.error("Dosyada 'MALZEME ADI' veya 'BİRİM FİYATI' başlıkları bulunamadı.")
        else:
            st.warning("Dosya seçmediniz.")

with tab1:
    db_conn = get_db_connection()
    df_list = pd.read_sql_query("SELECT * FROM products", db_conn)
    db_conn.close()
    if not df_list.empty:
        st.dataframe(df_list, use_container_width=True)
    else:
        st.info("Gösterilecek veri yok. Önce 'Veri Yükleme' yapın.")