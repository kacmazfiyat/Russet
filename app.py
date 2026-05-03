import streamlit as st
import pandas as pd
import sqlite3
from database import init_db, get_all_marketplaces, save_marketplace, delete_marketplace
from excel_reader import process_excel
from profit_calculator import calculate_results

st.set_page_config(page_title="Pro Yönetim", layout="wide", page_icon="💎")
init_db()

def delete_product_from_db(barcode):
    conn = sqlite3.connect('pazaryeri.db')
    conn.execute("DELETE FROM products WHERE barkod = ?", (barcode,))
    conn.commit()
    conn.close()

with st.sidebar:
    st.title("💎 Pro Yönetim")
    menu = st.radio("Menü Seçiniz:", ["📊 Analiz", "⚙️ Pazaryeri Ayarları", "📂 Veri Yükleme"])

# --- 1. ANALİZ ---
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
                selected_prod = st.selectbox("🔍 Ürün Ara:", ["Manuel Giriş"] + product_list)
                if selected_prod != "Manuel Giriş":
                    barcode = selected_prod.split(" | ")[0]
                    target_row = products_df[products_df['barkod'] == barcode].iloc[0]
                    initial_maliyet = float(target_row['maliyet'])
                else: initial_maliyet = 100.0
            else:
                st.info("ℹ️ Ürün hafızası boş.")
                initial_maliyet = 100.0
        
        with col_setup2:
            sel_mp = st.selectbox("Pazaryeri:", mps['name'].unique())
            mp_data = mps[mps['name'] == sel_mp].iloc[0].to_dict()

        st.divider()
        c_in, c_res = st.columns([1, 2])
        with c_in:
            maliyet = st.number_input("Alış Maliyeti:", value=initial_maliyet)
            target_margin = st.number_input("🎯 Hedef Kar Marjı (%)", value=20.0)
            
            kom, stp, kdv = mp_data['komisyon']/100, mp_data['stopaj']/100, mp_data['kdv']/100
            sabit = mp_data['kargo'] + mp_data['hizmet'] + mp_data['ekstra'] + mp_data['kupon']
            kdv_e = (kdv / (1 + kdv)) if mp_data['kdv_dahil'] == 1 else 0
            payda = 1 - (kom + stp + (target_margin/100) + kdv_e)
            
            onerilen = (maliyet + sabit) / payda if payda > 0 else 0
            st.success(f"💡 Öneri: **{round(onerilen, 2)} TL**")
            satis_fiyati = st.number_input("Satış Fiyatı (TL):", value=round(onerilen, 2))

        res = calculate_results(satis_fiyati, maliyet, mp_data)
        with c_res:
            st.subheader("📈 Karlılık Sonucu")
            m1, m2 = st.columns(2)
            m1.metric("Net Kar", f"{res['net_kar']} TL", f"%{res['kar_marji']}")
            m2.metric("Toplam Gider", f"{res['toplam_gider']} TL")
            with st.expander("🔍 Gider Detayı"):
                st.table(pd.DataFrame({"Kalem": ["Komisyon", "Kargo", "KDV", "Diger"], 
                                      "Tutar": [f"{res['komisyon_tutari']} TL", f"{mp_data['kargo']} TL", 
                                                f"{res['kdv_tutari']} TL", f"{mp_data['hizmet']+mp_data['ekstra']} TL"]}))

# --- 2. AYARLAR ---
elif menu == "⚙️ Pazaryeri Ayarları":
    st.header("⚙️ Pazaryeri Yapılandırması")
    with st.expander("➕ Yeni Ekle"):
        with st.form("mp_form"):
            name = st.text_input("İsim"); kdv_d = st.toggle("KDV Dahil", value=True)
            c1, c2, c3 = st.columns(3); kom = c1.number_input("Komisyon (%)"); kar = c2.number_input("Kargo"); kup = c3.number_input("Kupon")
            c4, c5, c6 = st.columns(3); kdv = c4.number_input("KDV (%)"); stp = c5.number_input("Stopaj"); hiz = c6.number_input("Hizmet")
            eks = st.number_input("Ekstra")
            if st.form_submit_button("Kaydet"):
                save_marketplace({"name": name.upper(), "komisyon": kom, "kargo": kar, "kupon": kup, "stopaj": stp, "kdv": kdv, "hizmet": hiz, "ekstra": eks, "kdv_dahil": 1 if kdv_d else 0})
                st.rerun()
    mps_list = get_all_marketplaces()
    if not mps_list.empty:
        st.dataframe(mps_list)
        sel = st.selectbox("Sil:", mps_list['name'].unique())
        if st.button("Sil"):
            delete_marketplace(int(mps_list[mps_list['name']==sel]['id'].values[0])); st.rerun()

# --- 3. VERİ YÜKLEME ---
elif menu == "📂 Veri Yükleme":
    st.header("📂 Veri Yönetimi")
    t1, t2 = st.tabs(["📤 Excel Yükle", "🗑️ Hafızayı Yönet"])
    
    with t1:
        st.info("Not: Excel dosyanızda 'MALZEME ADI', 'BİRİM FİYATI' ve 'CM.' sütunları bulunmalıdır.")
        uploaded_file = st.file_uploader("Excel Dosyası Seçin", type="xlsx")
        if uploaded_file:
            df_excel = process_excel(uploaded_file)
            if not df_excel.empty:
                # GÖRSELDEKİ INFO KISMI (image_e2e114.png)
                st.success(f"✅ Başarılı! {len(df_excel)} adet ürün sisteme işlendi.")
                st.write("### Yüklenen Veri Özeti")
                st.dataframe(df_excel, use_container_width=True)
                st.balloons()
            else:
                st.error("❌ Dosya işlenemedi. Sütun isimlerini kontrol edin.")

    with t2:
        conn = sqlite3.connect('pazaryeri.db')
        all_p = pd.read_sql_query("SELECT * FROM products", conn)
        conn.close()
        if not all_p.empty:
            st.write(f"Hafızada **{len(all_p)}** ürün kayıtlı.")
            sel_p = st.selectbox("Ürün Sil:", all_p.apply(lambda x: f"{x['barkod']} - {x['urun_adi']}", axis=1))
            if st.button("Seçileni Sil"):
                delete_product_from_db(sel_p.split(" - ")[0]); st.rerun()
            if st.button("🚨 TÜM HAFIZAYI TEMİZLE"):
                conn = sqlite3.connect('pazaryeri.db'); conn.execute("DELETE FROM products"); conn.commit(); conn.close()
                st.rerun()
            st.dataframe(all_p)