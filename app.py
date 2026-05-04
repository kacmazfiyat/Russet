# --- VERİ YÜKLEME (HÜCRE BİRLEŞTİRME DESTEKLİ v59) ---
elif menu == "📥 Veri Yükle":
    st.subheader("📥 Excel'den Buluta Aktar")
    file = st.file_uploader("Excel Dosyası", type=['xlsx'])
    if st.button("Aktarımı Başlat") and file:
        with st.spinner("İşleniyor..."):
            xls = pd.ExcelFile(file)
            all_rows = []
            for sheet_name in xls.sheet_names:
                # fillna(method='ffill') ile birleştirilmiş hücrelerdeki boşlukları doldurmaya çalışıyoruz
                df = pd.read_excel(file, sheet_name=sheet_name, header=None).fillna("")
                
                price_col, name_col, size_col = -1, -1, -1
                
                # Başlık tespiti
                for i in range(min(25, len(df))):
                    row_vals = [str(val).upper().strip() for val in df.iloc[i].values]
                    if "BİRİM FİYATI" in row_vals: price_col = row_vals.index("BİRİM FİYATI")
                    if any(x in row_vals for x in ["MALZEME ADI", "ÜRÜN ADI"]):
                        name_col = next(idx for idx, v in enumerate(row_vals) if v in ["MALZEME ADI", "ÜRÜN ADI"])
                    if any(x in row_vals for x in ["CM.", "CM", "BOY"]):
                        size_col = next(idx for idx, v in enumerate(row_vals) if v in ["CM.", "CM", "BOY"])
                
                if price_col != -1 and name_col != -1:
                    for idx, row in df.iloc[i+1:].iterrows():
                        # Metin birleştirilmiş hücrede yan sütunda kalmış olabilir, kontrol et:
                        raw_name = str(row[name_col]).strip()
                        
                        # Eğer asıl sütun boşsa ama sağındaki sütunda metin varsa onu al (Birleştirilmiş hücre desteği)
                        if (raw_name == "" or raw_name.upper() == "NAN") and name_col + 1 < len(row):
                             alt_name = str(row[name_col + 1]).strip()
                             if alt_name != "": raw_name = alt_name

                        if not raw_name or raw_name.upper() in ["NAN", ""]: continue
                        
                        # Boy bulma (CM sütunundan veya isimden)
                        extracted_boy = "-"
                        if size_col != -1:
                            v = str(row[size_col]).strip()
                            if v != "": extracted_boy = v if "CM" in v.upper() else f"{v} CM"
                        
                        # Fiyat ve Döviz (Fiyatın hemen sağındaki hücre)
                        try:
                            f_raw = row[price_col]
                            f_clean = float(str(f_raw).replace('.', '').replace(',', '.'))
                        except: f_clean = 0.0
                        
                        d_col = price_col + 1
                        d_raw = str(row[d_col]).strip().upper() if d_col < len(row) else "TL"
                        d_tipi = "EUR" if "EUR" in d_raw or "€" in d_raw else ("USD" if "USD" in d_raw or "$" in d_raw else "TL")
                        
                        all_rows.append([raw_name, extracted_boy, f_clean, d_tipi, sheet_name])
            
            if all_rows:
                ws_prod = get_worksheet("Products")
                ws_prod.append_rows(all_rows, value_input_option='RAW')
                st.success(f"✅ {len(all_rows)} ürün başarıyla eklendi!")