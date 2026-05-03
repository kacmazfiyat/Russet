import pandas as pd
import sqlite3
import re
import os

def process_excel(file):
    try:
        # Excel dosyasını tüm sayfalarıyla (sheets) oku
        xls = pd.ExcelFile(file)
        all_products = []
        
        for sheet_name in xls.sheet_names:
            # Sayfayı ham veri olarak oku (İlk 20 satırı kontrol etmek yeterli)
            df_raw = pd.read_excel(file, sheet_name=sheet_name, header=None).head(20)
            
            # 'MALZEME ADI' hücresinin hangi satırda olduğunu tespit et
            header_row_index = None
            for i, row in df_raw.iterrows():
                # Satırdaki tüm değerleri stringe çevir ve "MALZEME ADI" ifadesini ara
                row_values = [str(val).strip().upper() for val in row.values if pd.notna(val)]
                if "MALZEME ADI" in row_values:
                    header_row_index = i
                    break
            
            if header_row_index is None:
                continue # Bu sayfada başlık bulunamadıysa pas geç

            # Sayfayı tespit edilen başlık satırından itibaren tekrar oku
            df = pd.read_excel(file, sheet_name=sheet_name, header=header_row_index)
            
            # Sütun isimlerini temizle (boşlukları sil ve büyük harf yap)
            df.columns = [str(col).strip().upper() for col in df.columns]

            # Sütunları bizim veritabanı yapımıza eşleştir
            # Excel'deki tam karşılıkları: 'MALZEME ADI', 'BİRİM FİYATI', 'CM.'
            mapping = {
                'MALZEME ADI': 'urun_adi',
                'BİRİM FİYATI': 'maliyet',
                'CM.': 'boyut'
            }
            
            # Sütunları yeniden adlandır (Sadece var olanları)
            df = df.rename(columns=mapping)

            # Gerekli ana sütunlar var mı kontrol et
            if 'urun_adi' not in df.columns or 'maliyet' not in df.columns:
                continue

            # Verisiz satırları temizle
            df = df.dropna(subset=['urun_adi', 'maliyet'])
            
            # Fiyat temizleme fonksiyonu (Metin içindeki sayıları ayıklar)
            def clean_price(price):
                if pd.isna(price): return 0.0
                # "210 TL" veya "450 Euro" gibi ifadelerden sadece rakam ve virgül/nokta kısmını al
                cleaned = re.sub(r'[^\d.,]', '', str(price))
                cleaned = cleaned.replace(',', '.') # Virgülü noktaya çevir
                try:
                    return float(cleaned)
                except:
                    return 0.0

            df['maliyet'] = df['maliyet'].apply(clean_price)
            
            # Sadece fiyatı 0'dan büyük olanları ürün kabul et
            df = df[df['maliyet'] > 0]

            # Ürün adını boyutla (CM) birleştirerek daha spesifik yap
            if 'boyut' in df.columns:
                df['urun_adi'] = df['urun_adi'].astype(str) + " (" + df['boyut'].astype(str) + " CM)"

            all_products.append(df)

        if not all_products:
            return pd.DataFrame()

        # Tüm sayfaları birleştir
        final_df = pd.concat(all_products, ignore_index=True)
        
        # Ek bilgiler
        final_df['dosya_adi'] = getattr(file, 'name', 'Excel_Dosyasi')
        final_df['barkod'] = [f"BRK-{1000 + i}" for i in range(len(final_df))]

        # --- VERİTABANINA KAYDET ---
        conn = sqlite3.connect('pazaryeri.db')
        # if_exists='append' -> Mevcut verilerin üzerine ekle
        final_df[['barkod', 'urun_adi', 'maliyet', 'dosya_adi']].to_sql('products', conn, if_exists='append', index=False)
        conn.close()
        
        return final_df

    except Exception as e:
        print(f"Hata detayı: {e}")
        return pd.DataFrame()