import streamlit as st
import pandas as pd
from database import init_db, get_all_marketplaces, save_marketplace, delete_marketplace, clear_all_marketplaces
from excel_reader import process_excel
from profit_calculator import calculate_net_profit, suggest_price

# Sayfa Genişliği ve Başlık
st.set_page_config(page_title="Pazaryeri Pro Yönetim", layout="wide")

# Veritabanını Başlat
init_db()

# --- SIDEBAR NAVİGASYON ---
with st.sidebar:
    st.title("💎 Pro Yönetim")
    menu = st.radio("Menü Seçiniz:", ["📊 Genel Dashboard", "💡 Akıllı Fiyat Önerici", "⚙️ Pazaryeri Ayarları", "📂 Veri Yükleme"])

# --- 1. GENEL DASHBOARD ---
if menu == "📊 Genel Dashboard":
    st.header("Genel Kar-Zarar Analizi")
    # Dashboard kodların buraya gelecek...
    st.info("Lütfen önce veri yükleyin ve pazaryeri ayarlarını yapın.")

# --- 2. AKILLI FİYAT ÖNERİCİ ---
elif menu == "💡 Akıllı Fiyat Önerici":
    st.header("Hedef Kâr Marjı Analizi")
    # Fiyat önerici kodların buraya gelecek...

# --- 3. PAZARYERİ AYARLARI (GÜNCELLENMİŞ SİLME ÖZELLİKLİ) ---
elif menu == "⚙️ Pazaryeri Ayarları":
    st.header("Pazaryeri Komisyon ve Gider Ayarları")
    
    with st.expander("➕ Yeni Pazaryeri Ekle", expanded=True):
        with st.form("mp_form"):
            name = st.text_input("Pazaryeri Adı (Örn: TRENDYOL)")
            col1, col2, col3 = st.columns(3)
            komisyon = col1.number_input("Komisyon (%)", min_value=0.0, value=20.0)
            kargo = col2.number_input("Kargo Ücreti (TL)", min_value=0.0, value=80.0)
            kupon = col3.number_input("Kupon/İndirim (TL)", min_value=0.0, value=0.0)
            
            col4, col5, col6 = st.columns(3)
            stopaj = col4.number_input("Stopaj (%)", min_value=0.0, value=0.0)
            kdv = col5.number_input("KDV (%)", min_value=0.0, value=20.0)
            hizmet = col6.number_input("Hizmet Bedeli (TL)", min_value=0.0, value=0.0)
            
            ekstra = st.number_input("Ekstra Gider (TL)", min_value=0.0, value=0.0)
            submitted = st.form_submit_button("Kaydet")
            
            if submitted:
                save_marketplace({
                    "name": name.upper(), "komisyon": komisyon, "kargo": kargo,
                    "kupon": kupon, "stopaj": stopaj, "kdv": kdv,
                    "hizmet": hizmet, "ekstra": ekstra, "varsayilan": 0
                })
                st.success(f"{name} eklendi!")
                st.rerun()

    st.divider()
    st.subheader("Aktif Pazaryerleri")
    mps = get_all_marketplaces()

    if not mps.empty:
        # Tabloyu göster
        st.dataframe(mps, use_container_width=True)
        
        # --- SEÇİLİYİ SİLME ALANI ---
        st.write("🗑️ **Kayıt Yönetimi**")
        col_del1, col_del2 = st.columns([3, 1])
        
        with col_del1:
            # ID ve İsim birleştirerek seçenek oluştur (Mükerrer isimleri ayırt etmek için)
            mps['choice'] = mps['id'].astype(str) + " - " + mps['name']
            to_delete = st.selectbox("Silinecek kaydı seçin:", mps['choice'].tolist())
            target_id = int(to_delete.split(" - ")[0])
            
        with col_del2:
            st.write(" ") # Hizalama için
            if st.button("Seçiliyi Sil", type="primary", use_container_width=True):
                delete_marketplace(target_id)
                st.warning("Kayıt silindi.")
                st.rerun()
        
        if st.button("Tüm Listeyi Sıfırla"):
            clear_all_marketplaces()
            st.rerun()
    else:
        st.info("Kayıtlı pazaryeri bulunamadı.")

# --- 4. VERİ YÜKLEME ---
elif menu == "📂 Veri Yükleme":
    st.header("Excel Veri Yönetimi")
    uploaded_file = st.file_uploader("Fiyat Listesi Seçin (.xlsx)", type="xlsx")
    
    if uploaded_file:
        df_excel = process_excel(uploaded_file)
        if not df_excel.empty:
            st.success(f"{len(df_excel)} adet ürün başarıyla okundu.")
            st.dataframe(df_excel.head(20))
            # Veritabanına kaydetme işlemi buraya eklenebilir
        else:
            st.error("Excel formatı geçersiz veya okunacak veri bulunamadı!")