import streamlit as st
import pandas as pd
from database import init_db, get_all_marketplaces, save_marketplace, delete_marketplace
from excel_reader import process_excel

# Sayfa Ayarları
st.set_page_config(page_title="Pro Yönetim v3", layout="wide")
init_db()

# --- SIDEBAR ---
with st.sidebar:
    st.title("💎 Pro Yönetim")
    menu = st.radio("Menü:", ["📊 Analiz", "⚙️ Pazaryeri Ayarları", "📂 Veri Yükleme"])

# --- PAZARYERİ AYARLARI ---
if menu == "⚙️ Pazaryeri Ayarları":
    st.header("Pazaryeri Yapılandırması")
    
    with st.expander("➕ Yeni Pazaryeri Ekle", expanded=True):
        with st.form("yeni_mp_form"):
            name = st.text_input("Pazaryeri Adı (Örn: TRENDYOL)")
            
            # KDV Durumu (En Üstte)
            kdv_dahil_mi = st.toggle("KDV Satış Fiyatına Dahil mi?", value=True)
            st.caption("Açık: Fiyatın içinden KDV düşer. Kapalı: Fiyatın üzerine KDV ekler.")
            
            st.divider()
            
            # Tüm Gider Kalemleri (3'lü kolonlar halinde)
            c1, c2, c3 = st.columns(3)
            komisyon = c1.number_input("Komisyon (%)", min_value=0.0, value=20.0)
            kargo = c2.number_input("Kargo Ücreti (TL)", min_value=0.0, value=85.0)
            kupon = c3.number_input("Kupon/İndirim (TL)", min_value=0.0, value=0.0)
            
            c4, c5, c6 = st.columns(3)
            kdv_orani = c4.number_input("KDV Oranı (%)", min_value=0.0, value=20.0)
            stopaj = c5.number_input("Stopaj (%)", min_value=0.0, value=0.0)
            hizmet = c6.number_input("Hizmet Bedeli (TL)", min_value=0.0, value=0.0)
            
            ekstra = st.number_input("Ekstra Gider (TL)", min_value=0.0, value=0.0)
            
            submitted = st.form_submit_button("Kaydet")
            if submitted:
                save_marketplace({
                    "name": name.upper(), "komisyon": komisyon, "kargo": kargo,
                    "kupon": kupon, "stopaj": stopaj, "kdv": kdv_orani, 
                    "hizmet": hizmet, "ekstra": ekstra, "varsayilan": 0,
                    "kdv_dahil": 1 if kdv_dahil_mi else 0
                })
                st.success(f"{name} kaydedildi!")
                st.rerun()

    st.divider()
    st.subheader("Aktif Pazaryerleri")
    mps = get_all_marketplaces()

    if not mps.empty:
        # Tabloyu tüm sütunlarla göster
        st.dataframe(mps, use_container_width=True)
        
        # SEÇİLİYİ SİLME
        st.write("### 🗑️ Kayıt Yönetimi")
        col_del1, col_del2 = st.columns([3, 1])
        with col_del1:
            # Görseldeki gibi isim karışıklığı olmaması için ID ve KDV bilgisini etikete ekledim
            mps['label'] = (mps['id'].astype(str) + " - " + mps['name'] + 
                           (" (KDV Dahil)" if mps['kdv_dahil'].any() == 1 else " (KDV Hariç)"))
            secilen = st.selectbox("Silmek istediğiniz kaydı seçin:", mps['label'].tolist())
            target_id = int(secilen.split(" - ")[0])
        with col_del2:
            st.write(" ") # Hizalama
            if st.button("Seçili Pazaryerini Sil", type="primary", use_container_width=True):
                delete_marketplace(target_id)
                st.warning("Kayıt veritabanından silindi.")
                st.rerun()
    else:
        st.info("Henüz tanımlı bir pazaryeri yok.")

# --- VERİ YÜKLEME ---
elif menu == "📂 Veri Yükleme":
    st.header("Excel Veri Yönetimi")
    file = st.file_uploader("Fiyat Listesi (.xlsx)", type="xlsx")
    if file:
        df = process_excel(file) # Dinamik başlık bulan fonksiyonu kullanır
        if not df.empty:
            st.success(f"Başarılı! {len(df)} ürün ve kategorileri okundu.")
            st.dataframe(df)
        else:
            st.error("Excel formatı çözülemedi! Başlıkların 'MALZEME ADI' ve 'BİRİM FİYATI' olduğundan emin olun.")