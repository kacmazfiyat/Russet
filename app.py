import streamlit as st
import pandas as pd
import sqlite3
from database import init_db, get_all_marketplaces, save_marketplace, delete_marketplace
from excel_reader import process_excel
from profit_calculator import calculate_results

st.set_page_config(page_title="Pro Yönetim", layout="wide", page_icon="💎")
init_db()

# Yardımcı Fonksiyon: Ürün Silme
def delete_product(barcode):
    conn = sqlite3.connect('pazaryeri.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE barkod = ?", (barcode,))
    conn.commit()
    conn.close()

with st.sidebar:
    st.title("💎 Pro Yönetim")
    menu = st.radio("Menü Seçiniz:", ["📊 Analiz", "⚙️ Pazaryeri Ayarları", "📂 Veri Yükleme"])

# --- 1. ANALİZ SEKİMESİ --- (Aynı mantıkla devam eder)
if menu == "📊 Analiz":
    st.header("📊 Genel Kar-Zarar Analizi")
    mps = get_all_marketplaces()
    
    conn = sqlite3.connect('pazaryeri.db')
    try:
        products_df = pd.read_sql_query("SELECT * FROM products", conn)
    except:
        products_df = pd.DataFrame()
    conn.close()

    if mps.empty:
        st.warning("⚠️ Önce Pazaryeri Ayarları yapın.")
    else:
        col_setup1, col_setup2 = st.columns(2)
        with col_setup1:
            if not products_df.empty:
                product_list = products_df.apply(lambda x: f"{x['barkod']} | {x['urun_adi']}", axis=1).tolist()
                selected_prod = st.selectbox("🔍 Ürün Ara (Hafızadan):", ["Manuel Giriş"] + product_list)
                
                if selected_prod != "Manuel Giriş":
                    barcode = selected_prod.split(" | ")[0]
                    target_row = products_df[products_df['barkod'] == barcode].iloc[0]
                    initial_maliyet = float(target_row['maliyet'])
                else: initial_maliyet = 100.0
            else:
                st.info("ℹ️ Hafıza boş.")
                initial_maliyet = 100.0
        
        with col_setup2:
            selected_name = st.selectbox("Pazaryeri:", mps['name'].unique())
            mp_data = mps[mps['name'] == selected_name].iloc[0].to_dict()

        st.divider()
        col_inputs, col_metrics = st.columns([1, 2])
        with col_inputs:
            maliyet = st.number_input("Maliyet (TL):", min_value=0.0, value=initial_maliyet)
            target_margin = st.number_input("🎯 Hedef Kar (%)", value=20.0)
            
            # Ters Hesaplama
            kom, stp, kdv = mp_data['komisyon']/100, mp_data['stopaj']/100, mp_data['kdv']/100
            sabit = mp_data['kargo'] + mp_data['hizmet'] + mp_data['ekstra'] + mp_data['kupon']
            kdv_e = (kdv / (1 + kdv)) if mp_data['kdv_dahil'] == 1 else 0
            payda = 1 - (kom + stp + (target_margin/100) + kdv_e)
            
            satis_fiyati_onerisi = (maliyet + sabit) / payda if payda > 0 else 0
            st.success(f"💡 Öneri: **{round(satis_fiyati_onerisi, 2)} TL**")
            satis_fiyati = st.number_input("Satış Fiyatı (TL):", value=round(satis_fiyati_onerisi, 2))

        res = calculate_results(satis_fiyati, maliyet, mp_data)
        with col_metrics:
            m1, m2, m3 = st.columns(3)
            m1.metric("Net Kar", f"{res['net_kar']} TL", f"%{res['kar_marji']}")
            m2.metric("Gider", f"{res['toplam_gider']} TL")
            m3.metric("Tahsilat", f"{res['tahsilat']} TL")

# --- 2. PAZARYERI AYARLARI (Kısa geçildi) ---
elif menu == "⚙️ Pazaryeri Ayarları":
    st.header("⚙️ Pazaryeri Ayarları")
    # (Önceki kodun aynısı burada kalacak)

# --- 3. VERİ YÜKLEME VE HAFIZA YÖNETİMİ ---
elif menu == "📂 Veri Yükleme":
    st.header("📂 Veri Yükleme ve Hafıza Yönetimi")
    
    tab1, tab2 = st.tabs(["📤 Yeni Dosya Ekle", "🗑️ Hafızayı Yönet (Sil)"])
    
    with tab1:
        uploaded_file = st.file_uploader("Excel Yükle (Üst üste eklenir)", type="xlsx")
        if uploaded_file:
            df_excel = process_excel(uploaded_file)
            if not df_excel.empty:
                st.success(f"Hafızaya eklendi! Toplam {len(df_excel)} ürün.")
                st.rerun()

    with tab2:
        conn = sqlite3.connect('pazaryeri.db')
        current_products = pd.read_sql_query("SELECT * FROM products", conn)
        conn.close()
        
        if not current_products.empty:
            st.write(f"Hafızada toplam **{len(current_products)}** ürün var.")
            
            # Silme işlemi için arayüz
            col_sel, col_btn = st.columns([3,1])
            with col_sel:
                to_delete = st.selectbox("Silinecek Ürünü Seçin:", current_products.apply(lambda x: f"{x['barkod']} - {x['urun_adi']}", axis=1))
            with col_btn:
                st.write(" ") # Hizalama
                if st.button("Seçileni Sil", type="primary"):
                    barcode_to_del = to_delete.split(" - ")[0]
                    delete_product(barcode_to_del)
                    st.success("Ürün silindi.")
                    st.rerun()
            
            st.divider()
            if st.button("⚠️ Tüm Hafızayı Temizle"):
                conn = sqlite3.connect('pazaryeri.db')
                conn.execute("DELETE FROM products")
                conn.commit()
                conn.close()
                st.warning("Tüm veriler silindi.")
                st.rerun()
                
            st.dataframe(current_products, use_container_width=True)
        else:
            st.info("Hafıza şu an boş.")