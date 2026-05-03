import streamlit as st
import pandas as pd
import plotly.express as px
from database import init_db, create_connection
from excel_reader import process_excel
from profit_calculator import calculate_net_profit, suggest_price

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(
    page_title="Pazaryeri Pro Analiz Dashboard",
    page_icon="📈",
    layout="wide"
)

# Stil Ayarları (CSS)
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# Veritabanı Başlatma
init_db()
conn = create_connection()

# --- SIDEBAR NAVİGASYON ---
st.sidebar.title("💎 Pro Yönetim")
sayfa = st.sidebar.radio(
    "Menü Seçiniz:",
    ["📊 Genel Dashboard", "💡 Akıllı Fiyat Önerici", "⚙️ Pazaryeri Ayarları", "📂 Veri Yükleme"]
)

# --- 1. VERİ YÜKLEME ---
if sayfa == "📂 Veri Yükleme":
    st.header("📂 Veri Yönetimi")
    uploaded_file = st.file_uploader("Fiyat Listesi Seçin (.xlsx)", type="xlsx")
    
    if uploaded_file:
        with st.spinner('Veriler ayıklanıyor...'):
            data = process_excel(uploaded_file)
            if not data.empty:
                st.success(f"Başarılı! {len(data)} ürün bulundu.")
                st.dataframe(data, use_container_width=True)
                if st.button("Veritabanına Aktar", type="primary"):
                    data.to_sql('products', conn, if_exists='replace', index=False)
                    st.toast("Veritabanı güncellendi!")
            else:
                st.error("Excel formatı geçersiz!")

# --- 2. PAZARYERİ AYARLARI ---
elif sayfa == "⚙️ Pazaryeri Ayarları":
    st.header("⚙️ Operasyonel Maliyet Tanımları")
    
    with st.form("new_market_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            name = st.text_input("Pazaryeri Adı")
            kom = st.number_input("Komisyon (%)", 0.0)
            kargo = st.number_input("Kargo (TL)", 0.0)
        with c2:
            kdv = st.number_input("KDV (%)", 20.0)
            stopaj = st.number_input("Stopaj (%)", 0.0)
            hizmet = st.number_input("Hizmet Bedeli (TL)", 0.0)
        with c3:
            kupon = st.number_input("Genel Kupon Payı (TL)", 0.0)
            ekstra = st.number_input("Diğer Giderler (TL)", 0.0)
        
        if st.form_submit_button("Sisteme Tanımla"):
            cursor = conn.cursor()
            cursor.execute("""INSERT INTO marketplaces 
                (name, komisyon, kargo, kupon, stopaj, kdv, hizmet, ekstra, varsayilan) 
                VALUES (?,?,?,?,?,?,?,?,?)""", (name, kom, kargo, kupon, stopaj, kdv, hizmet, ekstra, 0))
            conn.commit()
            st.success("Pazaryeri eklendi!")

    markets_df = pd.read_sql("SELECT * FROM marketplaces", conn)
    if not markets_df.empty:
        st.subheader("Aktif Pazaryerleri")
        st.dataframe(markets_df, use_container_width=True)
        if st.button("Listeyi Sıfırla"):
            conn.cursor().execute("DELETE FROM marketplaces"); conn.commit(); st.rerun()

# --- 3. GENEL DASHBOARD ---
elif sayfa == "📊 Genel Dashboard":
    try:
        prods = pd.read_sql("SELECT * FROM products", conn)
        markets = pd.read_sql("SELECT * FROM marketplaces", conn)
    except:
        st.warning("Önce veri yüklemeli ve pazaryeri eklemelisiniz."); st.stop()

    if not prods.empty and not markets.empty:
        st.title("📊 Karlılık Analiz Paneli")
        
        # Filtreleme Alanı
        col_search, col_mp, col_price = st.columns([2,1,1])
        with col_search:
            secili_urun = st.selectbox("🎯 Ürün Seçimi", prods['malzeme_adi'].unique())
            urun_detay = prods[prods['malzeme_adi'] == secili_urun].iloc[0]
        with col_mp:
            secili_mp = st.selectbox("🏢 Pazaryeri Seçimi", markets['name'].unique())
            mp_detay = markets[markets['name'] == secili_mp].iloc[0]
        with col_price:
            satis = st.number_input("Satış Fiyatı (TL)", value=float(urun_detay['birim_fiyat']*1.5))

        # Hesaplama Motoru
        maliyet = urun_detay['birim_fiyat']
        res = calculate_net_profit(satis, maliyet, mp_detay)

        # Kritik Uyarı Kartları
        if res['kar_marji'] < 10:
            st.error(f"🚨 KRİTİK MARJ: Bu ürünün kâr oranı çok düşük! (%{res['kar_marji']})")
        elif res['kar_marji'] >= 25:
            st.success(f"✅ YÜKSEK VERİM: Bu ürün kâr şampiyonu! (%{res['kar_marji']})")

        # Metrikler
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Birim Maliyet", f"{maliyet} TL")
        m2.metric("Net Kâr", f"{res['net_kar']} TL", f"%{res['kar_marji']} Marj")
        m3.metric("Gider Toplamı", f"{res['toplam_gider']} TL", delta_color="inverse")
        m4.metric("KDV/Stopaj", f"{round(res['detaylar']['KDV'], 2)} TL")

        st.divider()

        # Görsel Analizler
        g1, g2 = st.columns([1, 1])
        
        with g1:
            # Sunburst Gider Analizi
            st.subheader("📉 Gider Kırılım Analizi")
            gider_labels = list(res['detaylar'].keys())
            gider_values = list(res['detaylar'].values())
            fig_sun = px.pie(names=gider_labels, values=gider_values, hole=0.5, 
                             color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig_sun, use_container_width=True)

        with g2:
            st.subheader("🏁 Pazaryeri Kıyaslama")
            kars_list = []
            for _, m in markets.iterrows():
                h = calculate_net_profit(satis, maliyet, m)
                kars_list.append({"Pazaryeri": m['name'], "Net Kâr": h['net_kar'], "Marj %": h['kar_marji']})
            k_df = pd.DataFrame(kars_list).sort_values(by="Net Kâr", ascending=False)
            st.dataframe(k_df, use_container_width=True, hide_index=True)

        # Portföy Marj Grafiği
        st.subheader("🚀 Portföy Karlılık Sıralaması")
        marj_analizi = []
        for _, u in prods.iterrows():
            h = calculate_net_profit(u['birim_fiyat']*1.5, u['birim_fiyat'], mp_detay)
            marj_analizi.append({"Ürün": u['malzeme_adi'], "Marj": h['kar_marji']})
        
        ma_df = pd.DataFrame(marj_analizi).sort_values(by="Marj")
        fig_bar = px.bar(ma_df, x="Marj", y="Ürün", orientation='h', 
                         title="Ürünlerin Mevcut Fiyatlarla Kâr Marjları",
                         color="Marj", color_continuous_scale="RdYlGn")
        st.plotly_chart(fig_bar, use_container_width=True)

# --- 4. AKILLI FİYAT ÖNERİCİ ---
elif sayfa == "💡 Fiyat Önerici":
    st.header("💡 Akıllı Strateji Geliştirici")
    prods = pd.read_sql("SELECT * FROM products", conn)
    markets = pd.read_sql("SELECT * FROM marketplaces", conn)

    if not prods.empty and not markets.empty:
        c_a, c_b = st.columns(2)
        with c_a:
            hedef = st.slider("Hedef Kâr Marjı (%)", 5, 100, 20)
            u_sec = st.selectbox("Hangi Ürün?", prods['malzeme_adi'].unique())
            u_maliyet = prods[prods['malzeme_adi'] == u_sec]['birim_fiyat'].values[0]
        
        st.info(f"Seçilen ürünün maliyeti {u_maliyet} TL. %{hedef} kâr için hesaplanıyor...")
        
        oneri_listesi = []
        for _, mp in markets.iterrows():
            fiyat = suggest_price(u_maliyet, hedef, mp)
            oneri_listesi.append({
                "Pazaryeri": mp['name'],
                "Önerilen Fiyat": f"{fiyat} TL",
                "Tahmini Gider": f"{round(fiyat - u_maliyet - (fiyat*(hedef/100)), 2)} TL"
            })
        st.table(pd.DataFrame(oneri_listesi))
    else:
        st.error("Veri eksik!")

conn.close()