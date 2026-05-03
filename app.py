# --- app.py (v37 - KeyError Çözümü) ---

# ... (Üst kısımdaki fonksiyonlar aynı kalacak)

    elif menu == "🔍 Arama & Düzenle":
        st.subheader("🔍 Detaylı Maliyet ve Satış Analizi")
        
        ws_prod = get_data("Products")
        ws_set = get_data("Settings")
        
        # Veriyi çekerken hata riskine karşı kontrol
        p_df = pd.DataFrame(ws_prod.get_all_records())
        s_df = pd.DataFrame(ws_set.get_all_records())
        
        if not p_df.empty and not s_df.empty:
            target_plat = st.selectbox("Hesaplama Yapılacak Platform", s_df['platform'].unique())
            
            # Platform ayarlarını güvenli bir şekilde alalım
            s_row = s_df[s_df['platform'] == target_plat].iloc[0]
            s = s_row.to_dict()
            
            # HATA ALINAN SATIR İÇİN ÖNLEM: 
            # Eğer 'varsayilan_iskonto' yoksa 0 varsayalım
            v_isk = s.get('varsayilan_iskonto', 0)
            if v_isk == "": v_isk = 0

            search = st.text_input("Ürün Ara...", "")
            df = p_df[p_df['urun_adi'].str.contains(search, case=False)].copy()
            
            if not df.empty:
                # ANLIK HESAPLAMA
                # urun_iskonto bilgisini de güvenli çekelim
                res = df.apply(lambda x: calculate_costs_and_price(
                    x['maliyet'], 
                    x['doviz'], 
                    x.get('iskonto', 0), # Eğer üründe iskonto yoksa 0 al
                    s
                ), axis=1)
                
                df['İskontolu Maliyet'], df['Kdv Dahil Maliyet'], df['Satış Fiyatı'] = zip(*res)
                
                # Bilgi kutusundaki hatayı bu şekilde gideriyoruz
                st.info(f"📌 Platform: **{target_plat}** | Varsayılan İskonto: **%{v_isk}**")

                # TABLO YAPILANDIRMASI
                edited_df = st.data_editor(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "urun_adi": st.column_config.TextColumn("Ürün Adı", width="large"),
                        "maliyet": st.column_config.NumberColumn("Liste Fiyatı", format="%.2f"),
                        "iskonto": st.column_config.NumberColumn("İskonto", format="%d", help="İskonto oranını girin."),
                        "İskontolu Maliyet": st.column_config.NumberColumn("İskontolu Maliyet", format="%.2f ₺"),
                        "Kdv Dahil Maliyet": st.column_config.NumberColumn("Kdv Dahil Maliyet", format="%.2f ₺"),
                        "Satış Fiyatı": st.column_config.NumberColumn("Satış Fiyatı", format="%.2f ₺"),
                        "doviz": "Kur",
                        "boy": "Ölçü",
                        "sayfa_adi": None 
                    },
                    disabled=["İskontolu Maliyet", "Kdv Dahil Maliyet", "Satış Fiyatı"]
                )
                
                if st.button("Değişiklikleri Buluta İşle"):
                    # Güncelleme yapmadan önce teknik sütunları temizle ki Sheets'e yazmasın
                    save_df = edited_df.drop(columns=['İskontolu Maliyet', 'Kdv Dahil Maliyet', 'Satış Fiyatı'])
                    # ... (Kayıt kodları)
                    st.success("Güncellendi!")