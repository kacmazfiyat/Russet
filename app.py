if not df.empty:
        def calculate_smart_price(maliyet_ham):
            # 1. Maliyeti KDV'ye göre normalize et
            if s['kdv_dahil_mi'] == 1:
                maliyet_hariç = maliyet_ham / (1 + (s['kdv_orani'] / 100))
            else:
                maliyet_hariç = maliyet_ham
            
            # 2. Giderleri ekle (Kargo ve Hizmet genelde KDV dahil ödenir ama biz matrahı bulalım)
            toplam_gider_hariç = maliyet_hariç + (s['kargo'] / 1.2) + (s['hizmet_bedeli'] / 1.2)
            
            # 3. Satış Matrahını Bul (Komisyon ve Kar Payı Düşülmüş Oran)
            payda = 1 - ((s['komisyon'] + s['kar_orani']) / 100)
            if payda <= 0: return 0
            
            satis_matrahi = toplam_gider_hariç / payda
            
            # 4. En son KDV'yi ekle (Pazaryeri satış fiyatı)
            satis_fiyati_kdv_dahil = satis_matrahi * (1 + (s['kdv_orani'] / 100))
            return round(satis_fiyati_kdv_dahil, 2)

        df['Pazaryeri Satış (KDV Dahil)'] = df['maliyet'].apply(calculate_smart_price)

        # --- GÖRSEL DÜZENLEME (ORTALAMA) ---
        st.dataframe(
            df, 
            use_container_width=True,
            column_config={
                "maliyet": st.column_config.NumberColumn(
                    "Maliyet (Ham)",
                    help="Excel'den gelen ham fiyat",
                    format="%.2f TL",
                    alignment="center" # Yazıyı ortalar
                ),
                "Pazaryeri Satış (KDV Dahil)": st.column_config.NumberColumn(
                    "Pazaryeri Satış",
                    help="Tüm masraflar dahil önerilen fiyat",
                    format="%.2f TL",
                    alignment="center" # Yazıyı ortalar
                ),
                "sayfa_adi": st.column_config.TextColumn(
                    "Kategori",
                    alignment="center"
                )
            },
            hide_index=True # Index numarasını gizleyerek daha temiz görüntü sağlar
        )
    else:
        st.info("Sonuç yok.")