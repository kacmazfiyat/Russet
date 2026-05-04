# ... (Önceki kısımlar aynı, Veri Yükle kısmındaki başlık yakalama güncellendi)

    elif menu == "📥 Veri Yükle":
        st.subheader("📥 Excel'den Malzeme Kodu ile Aktarım")
        file = st.file_uploader("Dosya Seçin (xlsx)", type=['xlsx'])
        if st.button("Sisteme Yükle") and file:
            with st.spinner("Veriler işleniyor, lütfen bekleyin..."):
                xls = pd.ExcelFile(file)
                all_rows = []
                for sheet in xls.sheet_names:
                    df = pd.read_excel(file, sheet_name=sheet, header=None).fillna("")
                    c_idx, p_idx, n_idx, s_idx = -1, -1, -1, -1
                    
                    # Başlık Satırını ve Sütunları Bulma
                    for i in range(min(30, len(df))):
                        row = [str(v).upper().strip() for v in df.iloc[i].values]
                        if "MALZEME KODU" in row: c_idx = row.index("MALZEME KODU")
                        elif "STOK KODU" in row: c_idx = row.index("STOK KODU")
                        elif "KOD" in row: c_idx = row.index("KOD")
                        
                        if "BİRİM FİYATI" in row: p_idx = row.index("BİRİM FİYATI")
                        if any(x in row for x in ["MALZEME ADI", "ÜRÜN ADI"]):
                            n_idx = next(idx for idx,v in enumerate(row) if v in ["MALZEME ADI", "ÜRÜN ADI"])
                        if any(x in row for x in ["CM.", "CM", "BOY"]):
                            s_idx = next(idx for idx,v in enumerate(row) if v in ["CM.", "CM", "BOY"])
                    
                    # Verileri Çekme
                    if n_idx != -1 and p_idx != -1:
                        for _, row in df.iloc[i+1:].iterrows():
                            uname = str(row[n_idx]).strip()
                            if uname == "" and n_idx+1 < len(row): uname = str(row[n_idx+1]).strip()
                            if uname == "" or uname.upper() in ["NAN", ""]: continue
                            
                            # Malzeme Kodunu Çek
                            mkod = str(row[c_idx]).strip() if c_idx != -1 else "-"
                            mboy = str(row[s_idx]).strip() if s_idx != -1 else "-"
                            
                            try:
                                f_raw = row[p_idx]
                                f_clean = float(str(f_raw).replace('.', '').replace(',', '.'))
                            except: f_clean = 0.0
                            
                            d_col = p_idx + 1
                            d_raw = str(row[d_col]).strip().upper() if d_col < len(row) else "TL"
                            d_tipi = "EUR" if "EUR" in d_raw or "€" in d_raw else ("USD" if "USD" in d_raw or "$" in d_raw else "TL")
                            
                            all_rows.append([mkod, uname, mboy, f_clean, d_tipi, sheet])
                
                if all_rows:
                    ws_prod = get_worksheet("Products")
                    ws_prod.clear() # Mevcut her şeyi siler
                    # Temiz başlıkları yaz
                    ws_prod.append_row(["kod", "urun_adi", "boy", "maliyet", "doviz", "kategori"])
                    # Verileri toplu yükle
                    ws_prod.append_rows(all_rows)
                    st.success(f"✅ İşlem Tamam! {len(all_rows)} ürün Malzeme Kodlarıyla yüklendi.")