import pandas as pd
import sqlite3

def process_excel(file):
    try:
        # Tüm sayfaları oku
        xls = pd.ExcelFile(file)
        all_data = []
        
        for sheet_name in xls.sheet_names:
            # Her sayfayı 3. satırı (0-tabanlı) başlık kabul ederek oku
            df = pd.read_excel(file, sheet_name=sheet_name, header=3)
            
            # Gereksiz boşlukları sütun isimlerinden temizle
            df.columns = df.columns.str.strip()
            
            # Sütun isimlerini eşleştir
            mapping = {
                'MALZEME ADI': 'urun_adi',
                'BİRİM FİYATI': 'maliyet',
                'CM.': 'boyut'
            }
            
            # Eğer sayfada 'MALZEME ADI' ve 'BİRİM FİYATI' varsa işleme al
            if 'MALZEME ADI' in df.columns and 'BİRİM FİYATI' in df.columns:
                temp_df = df[['MALZEME ADI', 'BİRİM FİYATI', 'CM.']].copy()
                temp_df.columns = ['urun_adi', 'maliyet', 'boyut']
                
                # Boş olan satırları temizle
                temp_df = temp_df.dropna(subset=['urun_adi', 'maliyet'])
                
                # Boyut bilgisini ürün adına ekle (opsiyonel)
                temp_df['urun_adi'] = temp_df['urun_adi'].astype(str) + " (" + temp_df['boyut'].astype(str) + " cm)"
                
                all_data.append(temp_df)
        
        if not all_data:
            return pd.DataFrame()

        # Tüm sayfaları tek bir tabloda birleştir
        final_df = pd.concat(all_data, ignore_index=True)
        
        # Barkod ve Dosya Adı gibi sistem sütunlarını ekle
        final_df['dosya_adi'] = getattr(file, 'name', 'Excel_Dosyasi')
        final_df['barkod'] = [f"BRK-{1000 + i}" for i in range(len(final_df))]
        
        # Veritabanına kaydet
        conn = sqlite3.connect('pazaryeri.db')
        final_df[['barkod', 'urun_adi', 'maliyet', 'dosya_adi']].to_sql('products', conn, if_exists='append', index=False)
        conn.close()
        
        return final_df

    except Exception as e:
        print(f"Hata: {e}")
        return pd.DataFrame()