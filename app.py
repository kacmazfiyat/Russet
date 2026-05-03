import streamlit as st
import pandas as pd
import sqlite3
import os

st.set_page_config(page_title="Pro Yönetim v10", layout="wide")

# --- DB BAĞLANTISI ---
def get_db_connection():
    return sqlite3.connect('pazaryeri.db', check_same_thread=False)

def init_db():
    with get_db_connection() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            urun_adi TEXT, maliyet REAL, sayfa_adi TEXT, dosya_adi TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS settings (
            platform TEXT PRIMARY KEY, komisyon REAL, kargo REAL, 
            hizmet_bedeli REAL, kar_orani REAL, kdv_orani REAL, kdv_dahil_mi INTEGER)''')
    conn.close()

init_db()

# --- GÜNCELLEME FONKSİYONU ---
def update_product_in_db(df_changes):
    """Tabloda yapılan değişiklikleri DB'ye yazar."""
    with get_db_connection() as conn:
        for row_id, changes in df_changes.items():
            for col_name, new_val in changes.items():
                # Sütun isimlerini DB isimleriyle eşleştir
                db_col = "maliyet" if col_name == "Maliyet (Ham)" else col_name
                db_col = "urun_adi" if col_name == "Ürün Adı" else db_col
                
                if db_col in ["maliyet", "urun_adi"]:
                    conn.execute(f"UPDATE products SET {db_col} = ? WHERE id = ?", (new_val, row_id))
        conn.commit()

# --- ARAYÜZ ---
st.title("💎 Pro Ürün Düzenleme Paneli")
menu = st.sidebar.radio("Menü", ["🔍 Arama & Düzenle", "⚙️ Pazaryeri Ayarları", "📥 Veri Yükle"])

if menu == "🔍 Arama & Düzenle":
    st.subheader("Ürün Bilgilerini Güncelle")
    st.info("💡 Tablodaki hücrelere çift tıklayarak fiyatı veya ismi değiştirebilirsiniz. Değişiklikler anında kaydedilir.")

    # Platform Ayarlarını Çek
    with get_db_connection() as conn:
        platforms_saved = pd.read_sql_query("SELECT platform FROM settings", conn)
    
    if not platforms_saved.empty:
        target_plat = st.selectbox("Hesaplama Platformu", platforms_saved['platform'])
        with get_db_connection() as conn:
            s = pd.read_sql_query("SELECT * FROM settings WHERE platform = ?", conn, params=(target_plat,)).iloc[0]
    else:
        st.warning("Lütfen önce Ayarlar sekmesinden platform kurun!")
        st.stop()

    search = st.text_input("Ürün Ara...")
    
    with get_db_connection() as conn:
        # id sütununu mutlaka çekmeliyiz ki güncellemeyi yapabilelim
        df = pd.read_sql_query("SELECT id, urun_adi, maliyet, sayfa_adi FROM products WHERE urun_adi LIKE ?", conn, params=(f'%{search}%',))

    if not df.empty:
        # Fiyat Hesaplama Fonksiyonu
        def calculate_smart_price(maliyet_ham):
            if s['kdv_dahil_mi'] == 1:
                m_haric = maliyet_ham / (1 + (s['kdv_orani'] / 100))
            else:
                m_haric = maliyet_ham
            toplam_gider = m_haric + (s['kargo'] / 1.2) + (s['hizmet_bedeli'] / 1.2)
            payda = 1 - ((s['komisyon'] + s['kar_orani']) / 100)
            if payda <= 0: return 0
            res = (toplam_gider / payda) * (1 + (s['kdv_orani'] / 100))
            return round(res, 2)

        # Tabloyu hazırlarken sütun isimlerini şıklaştıralım
        df.rename(columns={'urun_adi': 'Ürün Adı', 'maliyet': 'Maliyet (Ham)', 'sayfa_adi': 'Kategori'}, inplace=True)
        df['Pazaryeri Satış'] = df['Maliyet (Ham)'].apply(calculate_smart_price)

        # --- DÜZENLENEBİLİR TABLO (st.data_editor) ---
        edited_df = st.data_editor(
            df,
            key="product_editor",
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": None, # ID'yi gizle ama arka planda tut
                "Maliyet (Ham)": st.column_config.NumberColumn(format="%.2f TL", alignment="center"),
                "Pazaryeri Satış": st.column_config.NumberColumn(format="%.2f TL", alignment="center", disabled=True), # Otomatik hesaplandığı için elle değiştirilemez
                "Kategori": st.column_config.TextColumn(alignment="center", disabled=True),
                "Ürün Adı": st.column_config.TextColumn(width="large")
            },
        )

        # Değişiklikleri Veritabanına Kaydetme Kontrolü
        if st.session_state.get("product_editor") and st.session_state.product_editor["edited_rows"]:
            update_product_in_db(st.session_state.product_editor["edited_rows"])
            st.success("Değişiklikler kaydedildi! Hesaplama güncellendi.")
            st.rerun() # Fiyat hesaplamasının yenilenmesi için sayfayı tazele

    else:
        st.info("Sonuç yok.")

# Ayarlar ve Veri Yükleme bölümleri bir önceki (v9) kod ile aynı kalsın...
# (Okunabilirlik için buraya tekrar eklemiyorum ama v9'daki o blokları altına eklemeyi unutma)