import pandas as pd
import sqlite3
import re
import os

def process_excel(file):
    try:
        xls = pd.ExcelFile(file)
        all_products = []
        
        for sheet_name in xls.sheet_names:
            # 1. Sayfayı ham veri olarak oku
            df_raw = pd.read_excel(file, sheet_name=sheet_name, header=None)
            
            # 2. Satır satır tara: İçinde hem 'MALZEME ADI' hem 'FİYAT' geçen satırı bul
            header_row_index = None
            for i, row in df_raw.iterrows():
                row_str = " ".join([str(x).upper() for x in row.values if pd.notna(x)])
                if "MALZEME ADI" in row_str or "BİRİM FİYATI" in row_str:
                    header_row_index = i
                    break
            
            if header_row_index is None:
                continue

            # 3. Veriyi o satırdan itibaren al
            df = pd.read_excel(file, sheet_name=sheet_name, skiprows=header_row_index)
            
            # 4. SÜTUN İSİMLERİNİ TEMİZLE (Kritik Nokta)
            # Birleşmiş hücrelerden dolayı oluşan 'Unnamed' sütunları temizle
            df.columns = [str(c).strip().upper() for c in df.columns]
            
            # 5. Sütunları Manuel Eşleştir (İsim tam tutmasa da konumdan bulur)
            # Eğer isimle bulamazsa, içinde 'MALZEME ADI' geçen sütunu yakala
            col_map = {}
            for col in df.columns:
                if "MALZEME ADI" in col: col_map[col] = "urun_adi"
                if "BİRİM FİYATI" in col: col_map[col] = "maliyet"
                if "CM." in col or "BOYUT" in col: col_map[col] = "boyut"
            
            df = df.rename(columns=col_map)

            # 6. Kontrol ve Temizlik
            if 'urun_adi' not in df.columns or 'maliyet' not in df.columns:
                continue

            df = df.dropna(subset=['urun_adi', 'maliyet'])
            
            # Sayı temizleme (TL, Euro, Nokta, Virgül karmaşasını çözer)
            def clean_price(price):
                if pd.isna(price): return 0.0
                val = str(price).replace('.', '').replace(',', '.') # Binlik ayırıcıyı sil, kuruşu noktaya çevir
                res = re.findall(r"[-+]?\d*\.\d+|\d+", val)
                return float(res[0]) if res else 0.0

            df['maliyet'] = df['maliyet'].apply(clean_price)
            df = df[df['maliyet'] > 0]

            # Ürün ismine boyut ekle
            if 'boyut' in df.columns:
                df['urun_adi'] = df['urun_adi'].astype(str) + " - " + df['boyut'].astype(str)

            all_products.append(df)

        if not all_products:
            return pd.DataFrame()

        final_df = pd.concat(all_products, ignore_index=True)
        final_df['dosya_adi'] = getattr(file, 'name', 'Excel_Dosyasi')
        final_df['barkod'] = [f"BRK-{1000 + i}" for i in range(len(final_df))]

        # Veritabanı Kayıt
        conn = sqlite3.connect('pazaryeri.db')
        final_df[['barkod', 'urun_adi', 'maliyet', 'dosya_adi']].to_sql('products', conn, if_exists='append', index=False)
        conn.close()
        
        return final_df

    except Exception as e:
        print(f"Hata detayı: {e}")
        return pd.DataFrame()