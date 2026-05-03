elif menu == "📊 Analiz":
    st.header("📊 Genel Kar-Zarar Analizi")
    
    mps = get_all_marketplaces()
    
    if mps.empty:
        st.warning("⚠️ Lütfen önce 'Pazaryeri Ayarları'ndan bir pazaryeri ekleyin.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            selected_name = st.selectbox("Pazaryeri:", mps['name'].unique())
            mp_data = mps[mps['name'] == selected_name].iloc[0].to_dict()
        with col2:
            maliyet = st.number_input("Ürün Maliyeti (TL):", min_value=0.0, value=100.0)

        st.divider()
        
        c_left, c_right = st.columns([1, 2])
        with c_left:
            satis_fiyati = st.number_input("Satış Fiyatı (TL):", min_value=0.0, value=250.0)
            # Senin fonksiyonun burada devreye giriyor
            res = calculate_results(satis_fiyati, maliyet, mp_data)
            
            kdv_tipi = "DAHİL" if mp_data.get('kdv_dahil') == 1 else "HARİÇ"
            st.info(f"💡 {selected_name} için KDV **{kdv_tipi}** hesaplanıyor.")

        with c_right:
            st.subheader("Hesaplama Sonucu")
            m1, m2, m3 = st.columns(3)
            
            # Kar durumuna göre renk (yeşil/kırmızı)
            delta_color = "normal" if res['net_kar'] >= 0 else "inverse"
            
            m1.metric("Net Kar", f"{res['net_kar']} TL", delta=f"%{res['kar_marji']}", delta_color=delta_color)
            m2.metric("Toplam Gider", f"{res['toplam_gider']} TL")
            m3.metric("Tahsilat", f"{res['toplam_tahsilat']} TL")

            with st.expander("Gider Dağılım Detayı"):
                st.write(f"- Komisyon: {res['komisyon_tutari']} TL")
                st.write(f"- KDV: {res['kdv_tutari']} TL")
                st.write(f"- Kargo: {mp_data['kargo']} TL")
                st.write(f"- Diğer (Kupon/Stopaj/Hizmet): {round(res['toplam_gider'] - res['komisyon_tutari'] - res['kdv_tutari'] - mp_data['kargo'], 2)} TL")