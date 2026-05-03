import streamlit as st
import pandas as pd
from database import init_db, get_all_marketplaces, save_marketplace, delete_marketplace
from excel_reader import process_excel
from profit_calculator import calculate_results

# Sayfa Ayarları
st.set_page_config(page_title="Pro Yönetim", layout="wide")
init_db()

# --- SIDEBAR ---
with st.sidebar:
    st.title("💎 Pro Yönetim")
    menu = st.radio("Menü Seçiniz:", ["📊 Analiz", "⚙️ Pazaryeri Ayarları", "📂 Veri Yükleme"])

# --- 1. ANALİZ SEKİMESİ (Syntax hatası burada giderildi) ---
if menu == "📊 Analiz":
    st.header("📊 Genel Kar-Zarar Analizi")
    mps = get_all_marketplaces()
    
    if not mps.empty:
        col_a, col_b = st.columns(2)
        with col_a:
            sel_mp = st.selectbox("Pazaryeri Seçin:", mps['name'].unique())
            mp_set = mps[mps['name'] == sel_mp].iloc[0].to_dict()
        with col_b:
            maliyet = st.number_input("Maliyet (TL):", value=100.0)

        st.divider()
        c_in, c_out = st.columns([1, 2])
        with c_in:
            fiyat = st.number_input("Satış Fiyatı (TL):", value=250.0)
            kdv_tip = "DAHİL" if mp_set.get('kdv_dahil') == 1 else "HARİÇ"
            st.info(f"📌 {sel_mp} için KDV **{kdv_tip}** hesaplanıyor.")
        
        # Sizin fonksiyonunuzu çağırıyoruz
        res = calculate_results(fiyat, maliyet, mp_set)
        
        with c_out:
            st.subheader("Karlılık Sonucu")
            m1, m2, m3 = st.columns(3)
            kar_renk = "normal" if res['net_kar'] >= 0 else "inverse"
            
            m1.metric("Net Kar", f"{res['net_kar']} TL", f"%{res['kar_marji']}", delta_color=kar_renk)
            m2.metric("Toplam Gider", f"{res['toplam_gider']} TL")
            m3.metric("Tahsilat", f"{res['toplam_tahsilat']} TL")

            with st.expander("Gider Detayları"):
                st.write(f"- Komisyon: {res['komisyon_tutari']} TL")
                st.write(f"- KDV: {res['kdv_tutari']} TL")
                st.write(f"- Diğer Giderler: {round(res['toplam_gider'] - res['komisyon_tutari'] - res['kdv_tutari'], 2)} TL")
    else:
        st.warning("⚠️ Lütfen önce Pazaryeri Ayarları'ndan bir kayıt ekleyin.")

# --- 2. AYARLAR SEKİMESİ ---
elif menu == "⚙️ Pazaryeri Ayarları":
    st.header("⚙️ Pazaryeri Ayarları")
    with st.expander("➕ Yeni Pazaryeri Ekle"):
        with st.form("new_mp"):
            name = st.text_input("Pazaryeri Adı")
            kdv_dahil = st.toggle("KDV Satış Fiyatına Dahil mi?", value=True)
            c1, c2, c3 = st.columns(3)
            kom = c1.number_input("Komisyon %", value=20.0); kar = c2.number_input("Kargo TL", value=80.0); kup = c3.number_input("Kupon TL", value=0.0)
            c4, c5, c6 = st.columns(3)
            kdv = c4.number_input("KDV %", value=20.0); stp = c5.number_input("Stopaj %", value=0.0); hiz = c6.number_input("Hizmet TL", value=0.0)
            eks = st.number_input("Ekstra TL", value=0.0)
            
            if st.form_submit_button("Kaydet"):
                save_marketplace({"name": name.upper(), "komisyon": kom, "kargo": kar, "kupon": kup, "stopaj": stp, "kdv": kdv, "hizmet": hiz, "ekstra": eks, "kdv_dahil": 1 if kdv_dahil else 0})
                st.rerun()

    st.subheader("Mevcut Pazaryerleri")
    mps = get_all_marketplaces()
    if not mps.empty:
        st.dataframe(mps, use_container_width=True)
        sel_del = st.selectbox("Silinecek Kayıt:", [f"{r['id']} - {r['name']}" for _, r in mps.iterrows()])
        if st.button("Seçili Pazaryerini Sil", type="primary"):
            delete_marketplace(int(sel_del.split(" - ")[0]))
            st.rerun()

# --- 3. YÜKLEME SEKİMESİ ---
elif menu == "📂 Veri Yükleme":
    st.header("📂 Excel Veri Yükleme")
    f = st.file_uploader("Dosya Seç", type="xlsx")
    if f:
        df = process_excel(f)
        if not df.empty:
            st.success("Veriler okundu"); st.dataframe(df)