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
            # Sayfayı ham veri olarak oku (başlık yokmuş gibi)
            df_raw = pd.read_excel(uploaded_file, sheet_name=sheet_name, header=None)
            
            # 1. ADIM: Başlık satırını tespit et
            header_idx = None
            for i, row in df_raw.iterrows():
                # Satırdaki tüm hücreleri yanyana koy ve içinde kritik kelimeleri ara
                row_text = " ".join([str(val).upper() for val in row.values if pd.notna(val)])
                if "MALZEME ADI" in row_text or "BİRİM FİYAT" in row_text:
                    header_idx = i
                    break
            
            if header_idx is None:
                continue

            # 2. ADIM: Sayfayı o satırdan itibaren oku
            df = pd.read_excel(uploaded_file, sheet_name=sheet_name, header=header_idx)
            
            # Sütun isimlerini temizle (Sadece string olanları büyük harfe çevir)
            df.columns = [str(c).strip().upper() for c in df.columns]

            # 3. ADIM: Esnek Sütun Eşleştirme (İsmin İÇİNDE geçiyor mu?)
            col_map = {}
            for col in df.columns:
                # "MALZEME ADI " veya "MALZEME ADI.1" gibi durumları yakalar
                if "MALZEME ADI" in col or "URUN ADI" in col or "ÜRÜN ADI" in col:
                    col_map[col] = "urun_adi"
                elif "BİRİM FİYAT" in col or "BIRIM FIYAT" in col or "MALİYET" in col:
                    col_map[col] = "maliyet"
                elif "CM" in col or "BOYUT" in col:
                    col_map[col] = "boyut"

            df = df.rename(columns=col_map)

            # 4. ADIM: Kontrol ve Temizlik
            # En azından isim ve fiyat sütununu bulmuş olmalıyız
            if "urun_adi" not in df.columns or "maliyet" not in df.columns:
                continue
                
            # Sadece ihtiyacımız olan sütunları seç (boyut opsiyonel)
            cols_to_keep = [c for c in ["urun_adi", "maliyet", "boyut"] if c in df.columns]
            df = df[cols_to_keep].copy()
            
            # İsim veya fiyatı boş olan satırları at
            df = df.dropna(subset=['urun_adi', 'maliyet'])

            # 5. ADIM: Fiyat Temizleme
            def clean_price(val):
                try:
                    if pd.isna(val): return 0.0
                    # Rakam, nokta ve virgül dışındaki her şeyi (TL vb.) sil
                    s = str(val).replace('.', '').replace(',', '.')
                    res = re.findall(r"[-+]?\d*\.\d+|\d+", s)
                    return float(res[0]) if res else 0.0
                except: return 0.0

            df['maliyet'] = df['maliyet'].apply(clean_price)
            df = df[df['maliyet'] > 0] # 0 olanları ele

            # Boyutu isme ekle
            if 'boyut' in df.columns:
                df['urun_adi'] = df['urun_adi'].astype(str) + " (" + df['boyut'].astype(str) + " CM)"

            all_data.append(df)

        if not all_data: return None

        final_df = pd.concat(all_data, ignore_index=True)
        final_df['dosya_adi'] = uploaded_file.name
        # Benzersiz barkod (yükleme zamanına göre)
        import time
        ts = int(time.time())
        final_df['barkod'] = [f"BRK-{ts}-{i}" for i in range(len(final_df))]
        
        # Veritabanına Yazma
        db_conn = get_db_connection()
        final_df[['barkod', 'urun_adi', 'maliyet', 'dosya_adi']].to_sql('products', db_conn, if_exists='append', index=False)
        db_conn.close()
        
        return len(final_df)
    except Exception as e:
        # Hata detayını Streamlit üzerinde göster
        st.error(f"Teknik bir hata oluştu: {str(e)}")
        return None

# --- STREAMLIT ARAYÜZÜ ---
st.title("💎 Pro Yönetim v2")
tab1, tab2 = st.tabs(["📊 Analiz", "📁 Veri Yükleme"])

with tab2:
    st.markdown("### Excel Veri Yükleme")
    st.info("Sistem; 'MALZEME ADI' ve 'BİRİM FİYATI' içeren sütunları otomatik bulur.")
    
    uploaded_file = st.file_uploader("Fiyat Listesi Seçin (.xlsx)", type=['xlsx'])
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Verileri Kaydet", use_container_width=True):
            if uploaded_file:
                with st.spinner("İşleniyor..."):
                    count = process_excel(uploaded_file)
                    if count:
                        st.success(f"Başarılı! {count} ürün sisteme eklendi.")
                    else:
                        st.error("Hata: Gerekli sütun başlıkları bulunamadı.")
            else:
                st.warning("Lütfen bir dosya yükleyin.")
    
    with col2:
        if st.button("⚠️ Veritabanını Sıfırla", use_container_width=True):
            db_conn = get_db_connection()
            db_conn.execute("DELETE FROM products")
            db_conn.commit()
            db_conn.close()
            st.warning("Tüm veriler silindi.")

with tab1:
    st.markdown("### Kayıtlı Ürünler")
    db_conn = get_db_connection()
    try:
        df_list = pd.read_sql_query("SELECT * FROM products ORDER BY id DESC", db_conn)
        if not df_list.empty:
            st.dataframe(df_list, use_container_width=True)
        else:
            st.info("Veritabanı şu an boş.")
    except:
        st.error("Veritabanı hatası!")
    finally:
        db_conn.close()