import streamlit as st
import pandas as pd
import sqlite3
import os
import re

st.set_page_config(page_title="Pro Yönetim v12", layout="wide")

# --- DB BAĞLANTISI ---
def get_db_connection():
    return sqlite3.connect('pazaryeri.db', check_same_thread=False)

def init_db():
    with get_db_connection() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            urun_adi TEXT, maliyet REAL, doviz TEXT, sayfa_adi TEXT, dosya_adi TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS settings (
            platform TEXT PRIMARY KEY, komisyon REAL, kargo REAL, 
            hizmet_bedeli REAL, kar_orani REAL, kdv_orani REAL, 
            kdv_dahil_mi INTEGER, eur_kuru REAL, usd_kuru REAL)''')
    conn.close()

init_db()

# --- EXCEL İŞLEME (P SÜTUNU DÖVİZ KONTROLLÜ) ---
def process_all_excel(uploaded_file):
    try:
        xls = pd.ExcelFile(uploaded_file)
        all_rows = []
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(uploaded_file, sheet_name=sheet_name, header=None)
            df = df.dropna(how='all')
            
            for _, row in df.iterrows():
                # E (4) = İsim, O (14) = Fiyat, P (15) = Döviz Türü, C (2) = Boyut
                urun_adi = str(row[4]) if len(row) > 4 else ""
                fiyat_ham = str(row[14]) if len(row) > 14 else "0"
                doviz_ham = str(row[15]).strip().upper() if len(row) > 15 else "TL"
                boyut = str(row[2]) if len(row) > 2 else ""

                # Döviz türünü normalize et
                if any(x in doviz_ham for x in ["€", "EUR", "EURO"]): doviz = "EUR"
                elif any(x in doviz_ham for x in ["$", "USD", "DOLAR"]): doviz = "USD"
                else: doviz = "TL"

                try:
                    fiyat = float(str(fiyat_ham).replace('.', '').replace(',', '.'))
                except: fiyat = 0.0

                if urun_adi.strip().upper() not in ["NAN", "MALZEME ADI", "ÜRÜN ADI"] and urun_adi.strip():
                    full_name = f"{urun_adi} {boyut}".strip()
                    all_rows.append((full_name, fiyat, doviz, sheet_name, uploaded_file.name))

        if all_rows:
            with get_db_connection() as db_conn:
                db_conn.executemany("INSERT INTO products (urun_adi, maliyet, doviz, sayfa_adi, dosya_adi) VALUES (?, ?, ?, ?, ?)", all_rows)
            return len(all_rows)
    except Exception as e:
        st.error(f"Hata: {e}")
        return None

# --- ARAYÜZ ---
st.title("💎 Pro Dövizli Yönetim Paneli")
menu = st.sidebar.radio("Menü", ["🔍 Arama & Düzenle", "⚙️ Ayarlar (Kur/Komisyon)", "📥 Veri Yükle"])

# --- 1. AYARLAR (DÖVİZ KURLARI DAHİL) ---
if menu == "⚙️ Ayarlar (Kur/Komisyon)":
    st.subheader("Platform ve Döviz Ayarları")
    platforms = ["Trendyol", "Hepsiburada", "Amazon", "N11"]
    selected_plat = st.selectbox("Platform Seçin", platforms)
    
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM settings WHERE platform = ?", (selected_plat,)).fetchone()
    
    # Varsayılanlar: [plat, kom, kargo, hiz, kar, kdv, kdv_dahil, eur, usd]
    dv = row if row else (selected_plat, 20.0, 80.0, 15.0, 30.0, 20.0, 0, 36.50, 33.50)

    with st.form("settings_form"):
        col1, col2, col3 = st.columns(3)
        kom = col1.number_input("Komisyon (%)", value=dv[1])
        kargo = col2.number_input("Kargo (TL)", value=dv[2])
        hizmet = col3.number_input("Hizmet (TL)", value=dv[3])
        kar = col1.number_input("Kâr (%)", value=dv[4])
        kdv = col2.selectbox("KDV (%)", [0, 1, 10, 20], index=3 if dv[5]==20 else 0)
        kdv_secim = col3.radio("Maliyet Durumu", ["KDV Hariç", "KDV Dahil"], index=dv[6])
        
        st.divider()
        st.markdown("### 💱 Güncel Döviz Kurları")
        c1, c2 = st.columns(2)
        eur_kur = c1.number_input("1 Euro (€) Kaç TL?", value=dv[7])
        usd_kur = c2.number_input("1 Dolar ($) Kaç TL?", value=dv[8])
        
        if st.form_submit_button("Tüm Ayarları Kaydet"):
            with get_db_connection() as conn:
                conn.execute('''INSERT OR REPLACE INTO settings VALUES (?,?,?,?,?,?,?,?,?)''', 
                             (selected_plat, kom, kargo, hizmet, kar, kdv, (1 if kdv_secim=="KDV Dahil" else 0), eur_kur, usd_kur))
            st.success("Ayarlar ve kurlar güncellendi!")

# --- 2. ARAMA & DÜZENLEME ---
elif menu == "🔍 Arama & Düzenle":
    with get_db_connection() as conn:
        s_df = pd.read_sql_query("SELECT * FROM settings", conn)
    
    if s_df.empty:
        st.warning("Önce ayarlar sekmesinden platform ve kurları kaydedin!")
        st.stop()
    
    target_plat = st.selectbox("Platform", s_df['platform'])
    s = s_df[s_df['platform'] == target_plat].iloc[0]

    search = st.text_input("Ürün Ara...")
    with get_db_connection() as conn:
        df = pd.read_sql_query("SELECT id, urun_adi, maliyet, doviz, sayfa_adi FROM products WHERE urun_adi LIKE ?", conn, params=(f'%{search}%',))

    if not df.empty:
        def calculate_price(row):
            # Döviz Çevrimi
            m_ham = row['maliyet']
            if row['doviz'] == "EUR": m_ham *= s['eur_kuru']
            elif row['doviz'] == "USD": m_ham *= s['usd_kuru']
            
            # KDV Normalizasyonu
            m_haric = m_ham / (1 + (s['kdv_orani']/100)) if s['kdv_dahil_mi'] == 1 else m_ham
            
            # Giderler ve Kâr
            toplam = m_haric + (s['kargo']/1.2) + (s['hizmet_bedeli']/1.2)
            payda = 1 - ((s['komisyon'] + s['kar_orani'])/100)
            return round((toplam / payda) * (1 + (s['kdv_orani']/100)), 2) if payda > 0 else 0

        df['Pazaryeri Satış'] = df.apply(calculate_price, axis=1)
        
        # Tabloyu göster ve düzenlemeye aç
        st.data_editor(
            df, use_container_width=True, hide_index=True,
            column_config={
                "id": None,
                "maliyet": st.column_config.NumberColumn("Maliyet (Ham)", alignment="center"),
                "doviz": st.column_config.TextColumn("Döviz", alignment="center"),
                "Pazaryeri Satış": st.column_config.NumberColumn("Pazaryeri Satış", format="%.2f TL", alignment="center", disabled=True)
            }
        )
# ... Veri Yükleme kısmı v9 ile aynı ...