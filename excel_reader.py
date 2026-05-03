import pandas as pd
import sqlite3

def process_excel(file):
    try:
        # Excel dosyasını oku
        df = pd.read_excel(file)
        
        # Sütun isimlerindeki boşlukları temizleyelim (Hata payını azaltmak için)
        df.columns = [str(col).strip() for col in df.columns]

        # Sizin Excel sütunlarınız ile sistemin eşleşmesi
        # CM. sütununu da ürün adına ekleyebilir veya ayrı tutabiliriz
        mapping = {
            'MALZEME ADI': 'urun_adi',
            'BİRİM FİYATI': 'maliyet',
            'CM.': 'boyut'
        }
        
        # Bulunan sütunları yeniden adlandır
        df = df.rename(columns=mapping)

        # Eğer MALZEME ADI ve CM. varsa, ürün adını daha açıklayıcı yapalım (Örn: "Bıçak - 20 CM")
        if 'urun_adi' in df.columns and 'boyut' in df.columns:
            df['urun_adi'] = df['urun_adi'].astype(str) + " - " + df['boyut'].astype(str) + " CM"

        # Barkod sende yoksa, her satıra benzersiz bir ID (Barkod) atayalım
        if 'barkod' not in df.columns:
            df['barkod'] = [f"BRK-{1000 + i}" for i in range(len(df))]

        # Sadece gerekli sütunları temiz bir şekilde alalım
        # Maliyet sütunundaki sayısal olmayan verileri (TL ibaresi vb.) temizleyelim
        df['maliyet'] = pd.to_numeric(df['maliyet'], errors='coerce').fillna(0)

        final_df = df[['barkod', 'urun_adi', 'maliyet']]

        # Veritabanına Yazma
        conn = sqlite3.connect('pazaryeri.db')
        # 'products' tablosunu yenisiyle değiştirir
        final_df.to_sql('products', conn, if_exists='replace', index=False)
        conn.close()
        
        return final_df

    except Exception as e:
        print(f"Excel işleme hatası: {e}")
        return pd.DataFrame()