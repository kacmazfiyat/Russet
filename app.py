import streamlit as st
import pandas as pd
import sqlite3
from database import init_db, get_all_marketplaces, save_marketplace, delete_marketplace
from excel_reader import process_excel
from profit_calculator import calculate_results

# Sayfa Ayarları
st.set_page_config(page_title="Pro Yönetim", layout="wide", page_icon="💎")

# Veritabanını Başlat
init_db()

# --- YARDIMCI FONKSİYONLAR ---
def delete_product_from_db(barcode):
    conn = sqlite3.connect('pazaryeri.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE barkod = ?", (barcode,))
    conn.commit()
    conn.close()

# --- SIDEBAR NAVİGASYON ---
with st.sidebar:
    st.title("💎 Pro Yönetim")
    menu = st.radio("Menü Seçiniz:", ["📊 Analiz", "⚙️ Pazaryeri Ayarları", "📂 Veri Yükleme"])

# --- 1. ANALİZ / DASHBOARD SEKİMESİ ---
if menu == "📊 Analiz":
    st.header("📊 Genel Kar-Zarar Analizi")
    
    mps = get_all_marketplaces()
    
    # Ürünleri Veritabanından Çek
    conn = sqlite3.connect('pazaryeri.db')
    try:
        products_df = pd.read_sql_query("SELECT * FROM products", conn)
    except:
        products_df = pd.DataFrame()
    conn.close()

    if mps.empty:
        st.warning("⚠️ Lütfen önce 'Pazaryeri Ayarları' menüsünden bir pazaryeri tanımlayın.")
    else:
        # Üst Seçim Paneli
        col_setup1, col_setup2 = st.columns(2)
        
        with col_setup1:
            if not products_df.empty:
                product_list = products_df.apply(lambda x: f"{x['barkod']} | {x['urun_adi']}", axis=1).tolist()
                selected_prod = st.selectbox("🔍 Ürün Ara (Yüklü Ürünler):", ["Manuel Giriş"] + product_list)
                
                if selected_prod != "Manuel Giriş":
                    barcode = selected_prod.split(" | ")[0]
                    target_row = products_df[products_df['barkod'] == barcode].iloc[0]
                    initial_maliyet = float(target_row['maliyet'])
                else:
                    initial_maliyet = 100.0
            else:
                st.info("ℹ️ Ürün hafızası boş. Veri Yükleme sekmesinden Excel ekleyebilirsiniz.")
                initial_maliyet = 100.0
        
        with col_setup2:
            selected_name = st.selectbox("Satış Yapılacak Pazaryeri:", mps['name'].unique())
            mp_data = mps[mps['name'] == selected_name].iloc[0].to_dict()

        st.divider()

        # Fiyat Girişleri ve Ters Hesaplama
        col_inputs, col_metrics = st.columns([1, 2])
        
        with col_inputs:
            st.subheader("💰 Fiyatlandırma")
            maliyet = st.number_input("Ürün Alış Maliyeti (TL):", min_value=0.0, value=initial_maliyet)
            
            st.write("---")
            target_margin = st.number_input("🎯 Hedef Kar Marjı (%)", value=20.0)
            
            kom = mp_data.get('komisyon', 0) / 100
            stp = mp_data.get('stopaj', 0) / 100
            kdv = mp_data.get('kdv', 20) / 100
            hedef = target_margin / 100
            sabit = (mp_data.get('kargo', 0) + mp_data.get('hizmet', 0) + 
                     mp_data.get('ekstra', 0) + mp_data.get('kupon', 0))
            
            kdv_e = (kdv / (1 + kdv)) if mp_data.get('kdv_dahil') == 1 else 0
            payda = 1 - (kom + stp + hedef + kdv_e)
            
            if payda <= 0:
                st.error("⚠️ Hedef kar ulaşılamaz!")
                satis_fiyati_onerisi = 0.0
            else:
                satis_fiyati_onerisi = (maliyet + sabit) / payda
            
            st.success(f"💡 Önerilen Satış Fiyatı: **{round(satis_fiyati_onerisi, 2)} TL**")
            satis_fiyati = st.number_input("Planlanan Satış Fiyatı (TL):", min_value=0.0, value=round(satis_fiyati_onerisi, 2))

        # Kar Hesapla
        res = calculate_results(satis_fiyati, maliyet, mp_data)

        with col_metrics:
            st.subheader("📈 Karlılık Sonucu")
            m1, m2 = st.columns(2) # Tahsilat kaldırıldı, 2 sütuna düşürüldü
            status_color = "normal" if res['net_kar'] >= 0 else "inverse"
            m1.metric("Net Kar", f"{res['net_kar']} TL", delta=f"%{res['kar_marji']}", delta_color=status_color)
            m2.metric("Toplam Gider", f"{res['toplam_gider']} TL")

            with st.expander("🔍 Gider Detayları"):
                st.table(pd.DataFrame({
                    "Kalem": ["Komisyon", "Kargo", "KDV", "Kupon", "Stopaj", "Ekstra"],
                    "Tutar": [f"{res['komisyon_tutari']} TL", f"{mp_data['kargo']} TL", f"{res['kdv_tutari']} TL", 
                              f"{mp_data['kupon']} TL", f"{mp_data['stopaj']} TL", f"{mp_data['hizmet'] + mp_data['ekstra']} TL"]
                }))

# --- 2. PAZARYERİ AYARLARI ---
elif menu == "⚙️ Pazaryeri Ayarları":
    st.header("⚙️ Pazaryeri Yapılandırması")
    with st.expander("➕ Yeni Pazaryeri Tanımla"):
        with st.form("mp_form"):
            name = st.text_input("Pazaryeri İsmi")
            kdv_dahil_mi = st.toggle("KDV Satış Fiyatına Dahil mi?", value=True)
            c1, c2, c3 = st.columns(3)
            kom = c1.number_input("Komisyon (%)", value=20.0); kar = c2.number_input("Kargo (TL)", value=80.0); kup = c3.number_input("Kupon (TL)", value=0.0)
            c4, c5, c6 = st.columns(3)
            kdv = c4.number_input("KDV (%)", value=20.0); stp = c5.number_input("Stopaj (%)", value=0.0); hiz = c6.number_input("Hizmet (TL)", value=0.0)
            eks = st.number_input("Ekstra Gider (TL)", value=0.0)
            if st.form_submit_button("Sisteme Kaydet"):
                save_marketplace({"name": name.upper(), "komisyon": kom, "kargo": kar, "kupon": kup, "stopaj": stp, "kdv": kdv, "hizmet": hiz, "ekstra": eks, "kdv_dahil": 1 if kdv_dahil_mi else 0})
                st.rerun()

    st.subheader("📋 Kayıtlı Pazaryerleri")
    mps_list = get_all_marketplaces()
    if not mps_list.empty:
        st.dataframe(mps_list, use_container_width=True)
        sel_mp = st.selectbox("Silinecek Pazaryeri:", mps_list['name'].unique())
        if st.button("Seçili Pazaryerini Sil", type="primary"):
            delete_marketplace(int(mps_list[mps_list['name'] == sel_mp]['id'].values[0]))
            st.rerun()

# --- 3. VERİ YÜKLEME VE HAFIZA ---
elif menu == "📂 Veri Yükleme":
    st.header("📂 Veri Yönetimi")
    tab1, tab2 = st.tabs(["📤 Ürün Ekle", "🗑️ Hafızayı Yönet"])
    
    with tab1:
        uploaded_file = st.file_uploader("Excel Seçin (Üst üste eklenir)", type="xlsx")
        if uploaded_file:
            df_excel = process_excel(uploaded_file)
            if not df_excel.empty:
                st.success("Hafızaya eklendi!"); st.rerun()

    with tab2:
        conn = sqlite3.connect('pazaryeri.db')
        all_prods = pd.read_sql_query("SELECT * FROM products", conn)
        conn.close()
        if not all_prods.empty:
            sel_prod = st.selectbox("Silinecek Ürün:", all_prods.apply(lambda x: f"{x['barkod']} - {x['urun_adi']}", axis=1))
            if st.button("Seçileni Sil", type="primary"):
                delete_product_from_db(sel_prod.split(" - ")[0]); st.rerun()
            if st.button("🚨 TÜMÜNÜ SİL"):
                conn = sqlite3.connect('pazaryeri.db'); conn.execute("DELETE FROM products"); conn.commit(); conn.close()
                st.rerun()
            st.dataframe(all_prods)