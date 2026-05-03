import pandas as pd
import sqlite3
import re

def process_excel(file):
    try:
        xls = pd.ExcelFile(file)
        all_products = []
        
        for sheet_name in xls.sheet_names:
            # Sayfayı 3. satırı atlayarak oku (4. satır başlık olsun diye)
            df = pd.read_excel(file, sheet_name=sheet_name, header=3)
            
            # Sütunları isim yerine sıraya göre alalım (Sizin Excel yapınıza göre)
            # 1. Sütun (B): MALZEME KODU
            # 2. Sütun (C): BOYUT (CM.)
            # 4. Sütun (E): MALZEME ADI
            # 14. Sütun (O): BİRİM FİYATI
            
            # DataFrame'in sütun sayısı yeterli mi kontrol et
            if len(df.columns) < 15:
                continue

            # Sütunları manuel seçip isimlendiriyoruz
            # iloc[:, [1, 2, 4, 14]] -> 2, 3, 5 ve 15. sütunları al (0'dan başladığı için)
            temp_df = df.iloc[:, [2, 4, 14]].copy()
            temp_df.columns = ['boyut', 'urun_adi', 'maliyet']

            # Boş satırları temizle
            temp_df = temp_df.dropna(subset=['urun_adi', 'maliyet'])
            
            # Sayı temizleme (TL yazısını ve virgülü temizle)
            def clean_price(price):
                try:
                    if pd.isna(price): return 0.0
                    p_str = str(price).replace('.', '').replace(',', '.')
                    res = re.findall(r"[-+]?\d*\.\d+|\d+", p_str)
                    return float(res[0]) if res else 0.0
                except:
                    return 0.0

            temp_df['maliyet'] = temp_df['maliyet'].apply(clean_price)
            
            # Fiyatı 0'dan büyük olanları al ve isme boyutu ekle
            temp_df = temp_df[temp_df['maliyet'] > 0].copy()
            temp_df['urun_adi'] = temp_df['urun_adi'].astype(str) + " (" + temp_df['boyut'].astype(str) + " CM)"
            
            all_products.append(temp_df)

        if not all_products:
            return pd.DataFrame()

        final_df = pd.concat(all_products, ignore_index=True)
        final_df['dosya_adi'] = getattr(file, 'name', 'Excel_Dosyasi')
        final_df['barkod'] = [f"BRK-{1000 + i}" for i in range(len(final_df))]

        # Veritabanına Yaz
        conn = sqlite3.connect('pazaryeri.db')
        final_df[['barkod', 'urun_adi', 'maliyet', 'dosya_adi']].to_sql('products', conn, if_exists='append', index=False)
        conn.close()
        
        return final_df

    except Exception as e:
        print(f"Hata detayı: {e}")
        return pd.DataFrame()