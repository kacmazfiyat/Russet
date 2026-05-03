# --- PAZARYERİ AYARLARI MENÜSÜ ---
elif menu == "⚙️ Pazaryeri Ayarları":
    st.header("Pazaryeri Yapılandırması")
    
    # 1. Yeni Ekleme Formu (Üst Kısım)
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
    
    # 2. Mevcut Kayıtlar ve Silme Tuşu (Alt Kısım)
    st.subheader("Aktif Pazaryerleri")
    mps = get_all_marketplaces()

    if not mps.empty:
        # Tabloyu göster
        st.dataframe(mps, use_container_width=True)
        
        # SİLME ALANI (Burayı kontrol et, kodda olduğundan emin ol)
        st.write("---")
        st.write("### 🗑️ Kayıt Yönetimi")
        col_del1, col_del2 = st.columns([3, 1])
        
        with col_del1:
            # Seçenekleri hazırla
            options = []
            for _, row in mps.iterrows():
                kdv_tip = "Dahil" if row['kdv_dahil'] == 1 else "Hariç"
                options.append(f"{row['id']} - {row['name']} (KDV {kdv_tip})")
            
            secilen_kayit = st.selectbox("Silinecek pazaryerini seçin:", options, key="delete_box")
            target_id = int(secilen_kayit.split(" - ")[0])
            
        with col_del2:
            st.write(" ") # Dikey hizalama
            st.write(" ") 
            if st.button("Seçiliyi Sil", type="primary", use_container_width=True):
                delete_marketplace(target_id)
                st.toast(f"ID {target_id} silindi!")
                st.rerun()
    else:
        st.info("Henüz tanımlı bir pazaryeri bulunamadı. Lütfen yukarıdan ekleyin.")