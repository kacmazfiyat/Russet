import pandas as pd
import sqlite3
import re
import os

def process_excel(file):
    try:
        # Excel dosyasını tüm sayfalarıyla oku
        xls = pd.ExcelFile(file)
        all_products = []
        
        for sheet_name in xls.sheet_names:
            # Sayfayı ham veri olarak oku
            df_raw = pd.read_excel(file, sheet_name=sheet_name, header=None)
            
            # 'MALZEME ADI' hücresinin hangi satırda olduğunu bul
            header_row_index = None
            for i, row in df_raw.iterrows():
                if "MALZEME ADI" in row.values:
                    header_row_index = i
                    break
            
            if header_row_index is None:
                continue # Bu sayfada aranan başlıklar yoksa atla

            # Sayfayı doğru satırdan itibaren tekrar oku
            df = pd.read_excel(file, sheet_name=sheet_name, header=header_row_index)
            
            # Sütun isimlerini temizle
            df.columns = [str(col).strip() for col in df.columns]

            # Sütun eşleştirme
            mapping = {
                'MALZEME ADI': 'urun_adi',
                'BİRİM FİYATI': 'maliyet',
                'CM.': 'boyut'
            }
            df = df.rename(columns=mapping)

            # Gerekli sütunlar kontrolü
            if 'urun_adi' not in df.columns or 'maliyet' not in df.columns:
                continue

            # Veri temizleme
            df = df.dropna(subset=['urun_adi', 'maliyet'])
            
            def clean_price(price):
                if pd.isna(price): return 0
                # Sayı dışındaki her şeyi (nokta ve virgül hariç) temizle
                cleaned = re.sub(r'[^\d.,]', '', str(price))
                cleaned = cleaned.replace(',', '.')
                try:
                    return float(cleaned)
                except:
                    return 0

            df['maliyet'] = df['maliyet'].apply(clean_price)
            
            # Sadece maliyeti 0'dan büyük olanları al (Boş satırları elemek için)
            df = df[df['maliyet'] > 0]

            # Ürün adını boyutla birleştir
            if 'boyut' in df.columns:
                df['urun_adi'] = df['urun_adi'].astype(str) + " - " + df['boyut'].astype(str) + " CM"

            all_products.append(df)

        if not all_products:
            return pd.DataFrame()

        # Tüm sayfaları birleştir
        final_df = pd.concat(all_products, ignore_index=True)
        
        # Dosya ve Barkod bilgileri
        final_df['dosya_adi'] = getattr(file, 'name', 'Excel_Dosyasi')
        final_df['barkod'] = [f"BRK-{1000 + i}" for i in range(len(final_df))]

        # Veritabanına kaydet (Üst üste ekler)
        conn = sqlite3.connect('pazaryeri.db')
        final_df[['barkod', 'urun_adi', 'maliyet', 'dosya_adi']].to_sql('products', conn, if_exists='append', index=False)
        conn.close()
        
        return final_df

    except Exception as e:
        print(f"Hata detayı: {e}")
        return pd.DataFrame()