# --- SADECE VERİ YÜKLEME KISMINI (ELIF MENU == "📥 VERİ YÜKLE") BU ŞEKİLDE GÜNCELLEYİN ---

    elif menu == "📥 Veri Yükle":
        st.subheader("📥 Excel'den Veri Yükleme (Gelişmiş Tarama)")
        file = st.file_uploader("Dosya Seç (xlsx)", type=['xlsx'])
        if st.button("Aktarımı Başlat") and file:
            with st.spinner("Tüm sayfalar taranıyor..."):
                xls = pd.ExcelFile(file)
                all_rows = []
                
                # Tanınacak başlık varyasyonları
                KOD_KEYWORDS = ["MALZEME KODU", "KOD", "STOK KODU", "ÜRÜN KODU", "KODU", "ART.NO"]
                AD_KEYWORDS = ["MALZEME ADI", "ÜRÜN ADI", "AÇIKLAMA", "ÜRÜN", "AD", "ADI"]
                FIYAT_KEYWORDS = ["BİRİM FİYATI", "FİYAT", "B.FİYAT", "FİYATI", "PRICE", "BİRİM"]
                BOY_KEYWORDS = ["CM.", "CM", "BOY", "ÖLÇÜ", "EBAT"]

                for sheet in xls.sheet_names:
                    df = pd.read_excel(file, sheet_name=sheet, header=None).fillna("")
                    c_i, p_i, n_i, s_i = -1, -1, -1, -1
                    
                    # Başlık Satırı Tespiti (İlk 100 satırı tara)
                    header_found_row = -1
                    for i in range(min(100, len(df))):
                        row = [str(v).upper().strip() for v in df.iloc[i].values]
                        
                        if any(x in row for x in KOD_KEYWORDS):
                            c_i = next(idx for idx,v in enumerate(row) if v in KOD_KEYWORDS)
                        if any(x in row for x in FIYAT_KEYWORDS):
                            p_i = next(idx for idx,v in enumerate(row) if v in FIYAT_KEYWORDS)
                        if any(x in row for x in AD_KEYWORDS):
                            n_i = next(idx for idx,v in enumerate(row) if v in AD_KEYWORDS)
                        if any(x in row for x in BOY_KEYWORDS):
                            s_i = next(idx for idx,v in enumerate(row) if v in BOY_KEYWORDS)
                        
                        # Eğer en azından Ad ve Fiyat bulunduysa başlık satırı burasıdır
                        if n_i != -1 and p_i != -1:
                            header_found_row = i
                            break
                    
                    # Veri Çekme İşlemi
                    if header_found_row != -1:
                        for idx, row in df.iloc[header_found_row + 1:].iterrows():
                            # Ürün adı veya koddan biri mutlaka dolu olmalı
                            name = str(row[n_i]).strip() if n_i != -1 else ""
                            mkod = str(row[c_i]).strip() if c_i != -1 else "-"
                            
                            if name == "" and mkod == "-": continue # İkisi de boşsa satırı atla
                            if name.upper() in ["NAN", ""]: continue

                            mboy = str(row[s_i]).strip() if s_i != -1 else "-"
                            
                            # Fiyat Temizleme (Hata payını sıfıra indirir)
                            try:
                                f_raw = str(row[p_i]).replace('.','').replace(',','.')
                                f = float(''.join(c for c in f_raw if c.isdigit() or c=='.'))
                            except: f = 0.0
                            
                            # Döviz tespiti (Fiyat sütununun hemen sağına bak)
                            d_col = p_i + 1
                            d_raw = str(row[d_col]).strip().upper() if d_col < len(row) else "TL"
                            dt = "EUR" if any(x in d_raw for x in ["EUR", "€"]) else ("USD" if any(x in d_raw for x in ["USD", "$"]) else "TL")
                            
                            all_rows.append([mkod, name, mboy, f, dt, sheet])
                
                if all_rows:
                    ws_prod = get_worksheet("Products")
                    ws_prod.clear()
                    ws_prod.append_row(["kod", "urun_adi", "boy", "maliyet", "doviz", "kategori"])
                    ws_prod.append_rows(all_rows)
                    st.success(f"✅ İşlem Tamam! {len(all_rows)} ürün (tüm sayfalardan) başarıyla yüklendi.")
                else:
                    st.error("❌ Hiç ürün bulunamadı! Başlık isimlerini kontrol edin.")