import streamlit as st
import pandas as pd
from database import init_db, get_all_marketplaces, save_marketplace, delete_marketplace, clear_all_marketplaces
from excel_reader import process_excel

# Sayfa Yapılandırması
st.set_page_config(page_title="Pro Yönetim v2", layout="wide")
init_db()

# --- SIDEBAR ---
with st.sidebar:
    st.title("💎 Pro Yönetim")
    menu = st.radio("Menü:", ["📊 Analiz", "⚙️ Pazaryeri Ayarları", "📂 Veri Yükleme"])

# --- PAZARYERİ AYARLARI ---
if menu == "⚙️ Pazaryeri Ayarları":
    st.header("Pazaryeri Yapılandırması")
    
    with st.expander("➕ Yeni Pazaryeri Ekle", expanded=True):
        with st.form("yeni_mp"):
            name = st.text_input("Pazaryeri Adı")
            
            # KDV Tipi Seçimi
            kdv_tipi = st.toggle("KDV Satış Fiyatına Dahil mi?", value=True)
            if kdv_tipi:
                st.caption("ℹ️ Bu pazaryerinde fiyatlar KDV dahil hesaplanır.")
            else:
                st.caption("⚠️ Bu pazaryerinde fiyatlar KDV hariç hesaplanır.")

            c1, c2, c3 = st.columns(3)
            komisyon = c1.number_input("Komisyon (%)", value=20.0)
            kargo = c2.number_input("Kargo (TL)", value=85.0)
            kdv = c3.number_input("KDV (%)", value=20.0)
            
            submitted = st.form_submit_button("Kaydet")
            if submitted:
                save_marketplace({
                    "name": name.upper(), "komisyon": komisyon, "kargo": kargo,
                    "kupon": 0, "stopaj": 0, "kdv": kdv, "hizmet": 0, 
                    "ekstra": 0, "varsayilan": 0, "kdv_dahil": 1 if kdv_tipi else 0
                })
                st.rerun()

    st.divider()
    st.subheader("Aktif Pazaryerleri")
    mps = get_all_marketplaces()

    if not mps.empty:
        # Tablo Gösterimi
        st.dataframe(mps, use_container_width=True)
        
        # Seçili Silme Bölümü
        st.write("### 🗑️ Kayıt Yönetimi")
        col_s1, col_s2 = st.columns([3, 1])
        with col_s1:
            mps['label'] = mps['id'].astype(str) + " - " + mps['name'] + (" (Dahil)" if mps['kdv_dahil'].iloc[0] == 1 else " (Hariç)")
            secilen = st.selectbox("Silmek istediğiniz kaydı seçin:", mps['label'].tolist())
            target_id = int(secilen.split(" - ")[0])
        with col_s2:
            st.write(" ") # Boşluk
            if st.button("Seçiliyi Sil", type="primary"):
                delete_marketplace(target_id)
                st.rerun()
    else:
        st.info("Kayıt yok.")

# --- VERİ YÜKLEME ---
elif menu == "📂 Veri Yükleme":
    st.header("Excel Veri Yönetimi")
    file = st.file_uploader("Fiyat Listesi (.xlsx)", type="xlsx")
    if file:
        df = process_excel(file)
        if not df.empty:
            st.success(f"{len(df)} ürün yüklendi.")
            st.dataframe(df)
        else:
            st.error("Excel okunamadı. Başlıkların 3. satırda (MALZEME ADI, BİRİM FİYATI) olduğundan emin olun.")