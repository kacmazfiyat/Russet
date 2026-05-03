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
            # Sayfayı ham veri olarak oku (İlk 10 satırı kontrol etmek için)
            df_raw = pd.read_excel(file, sheet_name=sheet_name, header=None).head(10)
            
            # 'MALZEME ADI' hücresinin hangi satırda olduğunu bul (Genelde 3. veya 4. satır)
            header_row_index = None
            for i, row in df_raw.iterrows():
                if "MALZEME ADI" in row.values:
                    header_row_index = i
                    break
            
            if header_row_index is None:
                continue # Bu sayfada aranan başlıklar yoksa bir sonraki sayfaya geç

            # Sayfayı doğru satırdan itibaren (başlığın olduğu yer) tekrar oku
            df = pd.read_excel(file, sheet_name=sheet_name, header=header_row_index)
            
            # Sütun isimlerini temizle (Başındaki/sonundaki görünmez boşlukları sil)
            df.columns = [str(col).strip() for col in df.columns]

            # Sütun isimlerini bizim sisteme uygun hale getir
            mapping = {
                'MALZEME ADI': 'urun_adi',
                'BİRİM FİYATI': 'maliyet',
                'CM.': 'boyut'
            }
            df = df.rename(columns=mapping)

            # Gerekli sütunlar bu sayfada var mı kontrol et
            if 'urun_adi' not in df.columns or 'maliyet' not in df.columns:
                continue

            # Verisi boş olan (NaN) satırları temizle
            df = df.dropna(subset=['urun_adi', 'maliyet'])
            
            # --- FİYAT TEMİZLEME ---
            # "210 TL" gibi metinlerden "TL"yi silip sayıya çevirir
            def clean_price(price):
                if pd.isna(price): return 0
                cleaned = re.sub(r'[^\d.,]', '', str(price)) # Sadece rakam, nokta ve virgül kalsın
                cleaned = cleaned.replace(',', '.') # Virgülü noktaya çevir
                try:
                    return float(cleaned)
                except:
                    return 0

            df['maliyet'] = df['maliyet'].apply(clean_price)
            
            # Sadece maliyeti 0'dan büyük olan gerçek ürünleri al
            df = df[df['maliyet'] > 0]

            # Ürün adını boyutla birleştir (Örn: Kasap Bıçağı - 13 CM)
            if 'boyut' in df.columns:
                df['urun_adi'] = df['urun_adi'].astype(str) + " - " + df['boyut'].astype(str) + " CM"

            all_products.append(df)

        if not all_products:
            return pd.DataFrame()

        # Tüm sayfaları tek bir listede birleştir
        final_df = pd.concat(all_products, ignore_index=True)
        
        # Dosya adı ve otomatik Barkod ata
        final_df['dosya_adi'] = getattr(file, 'name', 'Fiyat_Listesi.xlsx')
        final_df['barkod'] = [f"BRK-{1000 + i}" for i in range(len(final_df))]

        # --- VERİTABANINA KAYDET (Kalıcı Hafıza) ---
        conn = sqlite3.connect('pazaryeri.db')
        # if_exists='append' sayesinde her yeni dosyada eskilerin üstüne ekler
        final_df[['barkod', 'urun_adi', 'maliyet', 'dosya_adi']].to_sql('products', conn, if_exists='append', index=False)
        conn.close()
        
        return final_df

    except Exception as e:
        print(f"Hata detayı: {e}")
        return pd.DataFrame()