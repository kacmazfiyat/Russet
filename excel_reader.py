import pandas as pd
import sqlite3
import re

def process_excel(file):
    try:
        # Excel dosyasını tüm sayfalarıyla oku
        xls = pd.ExcelFile(file)
        all_products = []
        
        for sheet_name in xls.sheet_names:
            # Sizin dosyanızda başlıklar 4. satırda (Pandas için index 3)
            # Sayfayı bu satırı başlık kabul ederek oku
            df = pd.read_excel(file, sheet_name=sheet_name, header=3)
            
            # Eğer sayfa boşsa veya beklenen sütun sayısına sahip değilse atla
            if len(df.columns) < 15:
                continue

            # SÜTUNLARI KONUMA GÖRE AL (İsim hatasını önler)
            # 2. Sütun (C): CM. -> 'boyut'
            # 4. Sütun (E): MALZEME ADI -> 'urun_adi'
            # 14. Sütun (O): BİRİM FİYATI -> 'maliyet'
            temp_df = df.iloc[:, [2, 4, 14]].copy()
            temp_df.columns = ['boyut', 'urun_adi', 'maliyet']

            # Ürün adı ve maliyeti boş olan satırları temizle
            temp_df = temp_df.dropna(subset=['urun_adi', 'maliyet'])
            
            # FİYAT TEMİZLEME (TL/Euro yazılarını siler, virgülü noktaya çevirir)
            def clean_price(price):
                try:
                    if pd.isna(price): return 0.0
                    # Rakamlar dışındaki her şeyi temizle (virgül ve nokta hariç)
                    p_str = str(price).replace('.', '').replace(',', '.')
                    res = re.findall(r"[-+]?\d*\.\d+|\d+", p_str)
                    return float(res[0]) if res else 0.0
                except:
                    return 0.0

            temp_df['maliyet'] = temp_df['maliyet'].apply(clean_price)
            
            # Sadece fiyatı 0'dan büyük gerçek ürünleri al
            temp_df = temp_df[temp_df['maliyet'] > 0].copy()
            
            # Ürün ismini boyutla birleştirerek zenginleştir
            temp_df['urun_adi'] = temp_df['urun_adi'].astype(str) + " (" + temp_df['boyut'].astype(str) + " CM)"
            
            all_products.append(temp_df)

        if not all_products:
            return None

        # Tüm sayfaları tek bir tabloda birleştir
        final_df = pd.concat(all_products, ignore_index=True)
        final_df['dosya_adi'] = getattr(file, 'filename', 'Liste.xlsx')
        # Benzersiz Barkod oluştur
        final_df['barkod'] = [f"BRK-{1000 + i}" for i in range(len(final_df))]

        # VERİTABANINA KAYDET (Kalıcı hafıza)
        conn = sqlite3.connect('pazaryeri.db')
        final_df[['barkod', 'urun_adi', 'maliyet', 'dosya_adi']].to_sql('products', conn, if_exists='append', index=False)
        conn.close()
        
        return final_df

    except Exception as e:
        print(f"Excel İşleme Hatası: {e}")
        return None