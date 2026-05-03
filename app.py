import streamlit as st
import pandas as pd
from database import init_db, get_all_marketplaces, save_marketplace, delete_marketplace
from excel_reader import process_excel

# Sayfa Genişliği ve Başlık
st.set_page_config(page_title="Pazaryeri Pro Yönetim", layout="wide")

# Veritabanını Başlat (Sütun hatası alırsan pazaryeri.db dosyasını silmeyi unutma)
init_db()

# --- SIDEBAR NAVİGASYON ---
with st.sidebar:
    st.title("💎 Pro Yönetim")
    # Menü isimlerinin sidebar'daki radio butonlarla tam eşleşmesi gerekir
    menu = st.radio("Menü Seçiniz:", ["📊 Analiz", "⚙️ Pazaryeri Ayarları", "📂 Veri Yükleme"])

# --- 1. ANALİZ / DASHBOARD ---
if menu == "📊 Analiz":
    st.header("Genel Kar-Zarar Analizi")
    st.info("Veri yükledikten sonra analiz burada görünecektir.")

# --- 2. PAZARYERİ AYARLARI (GÜNCELLENMİŞ) ---
elif menu == "⚙️ Pazaryeri Ayarları":
    st.header("Pazaryeri Yapılandırması")
    
    # Yeni Ekleme Formu
    with st.expander("➕ Yeni Pazaryeri Ekle", expanded=False):
        with st.form("yeni_mp_form"):
            name = st.text_input("Pazaryeri Adı (Örn: TRENDYOL)")
            kdv_dahil_mi = st.toggle("KDV Satış Fiyatına Dahil mi?", value=True)
            
            st.divider()
            
            c1, c2, c3 = st.columns(3)
            komisyon = c1.number_input("Komisyon (%)", min_value=0.0, value=20.0)
            kargo = c2.number_input("Kargo Ücreti (TL)", min_value=0.0, value=85.0)
            kupon = c3.number_input("Kupon/İndirim (TL)", min_value=0.0, value=0.0)
            
            c4, c5, c6 = st.columns(3)
            kdv_orani = c4.number_input("KDV Oranı (%)", min_value=0.0, value=20.0)
            stopaj = c5.number_input("Stopaj (%)", min_value=0.0, value=0.0)
            hizmet = c6.number_input("Hizmet Bedeli (TL)", min_value=0.0, value=0.0)
            
            ekstra = st.number_input("Ekstra Gider (TL)", min_value=0.0, value=0.0)
            
            if st.form_submit_button("Kaydet"):
                save_marketplace({
                    "name": name.upper(), "komisyon": komisyon, "kargo": kargo,
                    "kupon": kupon, "stopaj": stopaj, "kdv": kdv_orani, 
                    "hizmet": hizmet, "ekstra": ekstra, "varsayilan": 0,
                    "kdv_dahil": 1 if kdv_dahil_mi else 0
                })
                st.success("Kaydedildi!")
                st.rerun()

    st.divider()
    
    # Mevcut Kayıtlar ve Silme İşlemi
    st.subheader("Aktif Pazaryerleri")
    mps = get_all_marketplaces()

    if not mps.empty:
        st.dataframe(mps, use_container_width=True)
        
        st.write("---")
        st.write("### 🗑️ Kayıt Yönetimi")
        col_del1, col_del2 = st.columns([3, 1])
        
        with col_del1:
            options = []
            for _, row in mps.iterrows():
                kdv_tip = "Dahil" if row.get('kdv_dahil') == 1 else "Hariç"
                options.append(f"{row['id']} - {row['name']} (KDV {kdv_tip})")
            
            secilen_kayit = st.selectbox("Silinecek pazaryerini seçin:", options)
            target_id = int(secilen_kayit.split(" - ")[0])
            
        with col_del2:
            st.write(" ") 
            st.write(" ") 
            if st.button("Seçiliyi Sil", type="primary", use_container_width=True):
                delete_marketplace(target_id)
                st.rerun()
    else:
        st.info("Henüz pazaryeri tanımlanmamış.")

# --- 3. VERİ YÜKLEME ---
elif menu == "📂 Veri Yükleme":
    st.header("Excel Veri Yönetimi")
    file = st.file_uploader("Fiyat Listesi (.xlsx)", type="xlsx")
    if file:
        df = process_excel(file)
        if not df.empty:
            st.success(f"{len(df)} ürün yüklendi.")
            st.dataframe(df)
        else:
            st.error("Excel okunamadı. Sütun başlıklarını kontrol edin.")