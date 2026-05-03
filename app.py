import streamlit as st
import pandas as pd
from database import init_db, get_all_marketplaces, save_marketplace, delete_marketplace
from excel_reader import process_excel
from profit_calculator import calculate_results

# Sayfa Yapılandırması
st.set_page_config(page_title="Pro Yönetim", layout="wide", page_icon="💎")

# Veritabanını Başlat (Eksik sütunları otomatik ekler)
init_db()

# --- SIDEBAR NAVİGASYON ---
with st.sidebar:
    st.title("💎 Pro Yönetim")
    menu = st.radio("Menü Seçiniz:", ["📊 Analiz", "⚙️ Pazaryeri Ayarları", "📂 Veri Yükleme"])

# --- 1. ANALİZ / DASHBOARD SEKİMESİ ---
if menu == "📊 Analiz":
    st.header("📊 Genel Kar-Zarar Analizi")
    
    mps = get_all_marketplaces()
    
    # Ürünleri Veritabanından Çek (Arama için)
    try:
        from database import create_connection
        conn = create_connection()
        # Excel yükleme modülünde tablo adının 'products' olduğunu varsayıyoruz
        products_df = pd.read_sql_query("SELECT * FROM products", conn)
        conn.close()
    except:
        products_df = pd.DataFrame()

    if mps.empty:
        st.warning("⚠️ Lütfen önce 'Pazaryeri Ayarları' menüsünden bir pazaryeri tanımlayın.")
    else:
        # Üst Seçim Paneli: Ürün Arama ve Pazaryeri Seçimi
        col_setup1, col_setup2 = st.columns(2)
        
        with col_setup1:
            if not products_df.empty:
                # Barkod ve Ürün Adını birleştirerek liste oluştur
                product_list = products_df.apply(lambda x: f"{x['barkod']} - {x['urun_adi']}", axis=1).tolist()
                selected_prod = st.selectbox("🔍 Ürün Ara / Seç (Excel'den):", ["Manuel Giriş"] + product_list)
                
                if selected_prod != "Manuel Giriş":
                    # Seçilen ürünün maliyetini otomatik çek
                    barcode = selected_prod.split(" - ")[0]
                    target_row = products_df[products_df['barkod'] == barcode].iloc[0]
                    initial_maliyet = float(target_row['maliyet'])
                else:
                    initial_maliyet = 100.0
            else:
                st.info("ℹ️ Henüz ürün yüklenmemiş. Veri Yükleme sekmesini kullanabilirsiniz.")
                initial_maliyet = 100.0
        
        with col_setup2:
            selected_name = st.selectbox("Satış Yapılacak Pazaryeri:", mps['name'].unique())
            mp_data = mps[mps['name'] == selected_name].iloc[0].to_dict()

        st.divider()

        # Fiyat Girişleri ve Sonuçlar
        col_inputs, col_metrics = st.columns([1, 2])
        
        with col_inputs:
            st.subheader("💰 Fiyatlandırma")
            maliyet = st.number_input("Ürün Alış Maliyeti (TL):", min_value=0.0, value=initial_maliyet)
            satis_fiyati = st.number_input("Planlanan Satış Fiyatı (TL):", min_value=0.0, value=250.0)
            
            kdv_durum = "DAHİL" if mp_data.get('kdv_dahil') == 1 else "HARİÇ"
            st.info(f"📌 {selected_name} için fiyat KDV **{kdv_durum}** kabul edilir.")

        # Senin calculate_results fonksiyonunu çalıştır
        res = calculate_results(satis_fiyati, maliyet, mp_data)

        with col_metrics:
            st.subheader("📈 Karlılık Sonucu")
            
            m1, m2, m3 = st.columns(3)
            # Kar durumuna göre renk (Pozitifse yeşil, negatifse kırmızı)
            status_color = "normal" if res['net_kar'] >= 0 else "inverse"
            
            m1.metric("Net Kar", f"{res['net_kar']} TL", delta=f"%{res['kar_marji']}", delta_color=status_color)
            m2.metric("Toplam Gider", f"{res['toplam_gider']} TL")
            m3.metric("Tahsilat", f"{res['toplam_tahsilat']} TL")

            # Detaylı Gider Tablosu
            with st.expander("🔍 Gider Kalemlerini Gör"):
                gider_ozet = pd.DataFrame({
                    "Kalem": ["Komisyon", "Kargo", "KDV", "Kupon", "Stopaj", "Hizmet/Ekstra"],
                    "Tutar": [
                        f"{res['komisyon_tutari']} TL",
                        f"{mp_data['kargo']} TL",
                        f"{res['kdv_tutari']} TL",
                        f"{mp_data['kupon']} TL",
                        f"{mp_data['stopaj']} TL",
                        f"{mp_data['hizmet'] + mp_data['ekstra']} TL"
                    ]
                })
                st.table(gider_ozet)

# --- 2. PAZARYERİ AYARLARI SEKİMESİ ---
elif menu == "⚙️ Pazaryeri Ayarları":
    st.header("⚙️ Pazaryeri Yapılandırması")
    
    with st.expander("➕ Yeni Pazaryeri Tanımla"):
        with st.form("mp_form"):
            name = st.text_input("Pazaryeri İsmi (Örn: TRENDYOL)")
            kdv_dahil_mi = st.toggle("KDV Satış Fiyatına Dahil mi?", value=True)
            
            c1, c2, c3 = st.columns(3)
            komisyon = c1.number_input("Komisyon (%)", value=20.0)
            kargo = c2.number_input("Kargo (TL)", value=80.0)
            kupon = c3.number_input("Kupon/İndirim (TL)", value=0.0)
            
            c4, c5, c6 = st.columns(3)
            kdv_orani = c4.number_input("KDV (%)", value=20.0)
            stopaj = c5.number_input("Stopaj (%)", value=0.0)
            hizmet = c6.number_input("Hizmet (TL)", value=0.0)
            
            ekstra = st.number_input("Ekstra Gider (TL)", value=0.0)
            
            if st.form_submit_button("Sisteme Kaydet"):
                save_marketplace({
                    "name": name.upper(), "komisyon": komisyon, "kargo": kargo,
                    "kupon": kupon, "stopaj": stopaj, "kdv": kdv_orani,
                    "hizmet": hizmet, "ekstra": ekstra, "varsayilan": 0,
                    "kdv_dahil": 1 if kdv_dahil_mi else 0
                })
                st.success("Pazaryeri başarıyla kaydedildi!")
                st.rerun()

    st.divider()
    st.subheader("📋 Kayıtlı Pazaryerleri")
    mps_list = get_all_marketplaces()
    
    if not mps_list.empty:
        st.dataframe(mps_list, use_container_width=True)
        
        st.write("### 🗑️ Kayıt Sil")
        c_sel, c_btn = st.columns([3, 1])
        with c_sel:
            del_options = [f"{r['id']} - {r['name']}" for _, r in mps_list.iterrows()]
            to_delete = st.selectbox("Silinecek Pazaryeri:", del_options)
        with c_btn:
            st.write(" ") # Hizalama için
            if st.button("Seçiliyi Sil", type="primary"):
                delete_marketplace(int(to_delete.split(" - ")[0]))
                st.rerun()

# --- 3. VERİ YÜKLEME SEKİMESİ ---
elif menu == "📂 Veri Yükleme":
    st.header("📂 Excel Ürün Listesi Yükleme")
    st.info("Not: Excel dosyanızda 'barkod', 'urun_adi' ve 'maliyet' sütunları bulunmalıdır.")
    
    uploaded_file = st.file_uploader("Excel Dosyası Seçin (.xlsx)", type="xlsx")
    if uploaded_file:
        df_excel = process_excel(uploaded_file)
        if not df_excel.empty:
            st.success(f"Başarılı! {len(df_excel)} adet ürün sisteme işlendi.")
            st.dataframe(df_excel, use_container_width=True)
        else:
            st.error("Excel verisi işlenemedi. Sütun isimlerini kontrol edin.")