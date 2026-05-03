import pandas as pd
import sqlite3

def process_excel(file):
    try:
        # header=None ile okuyup başlıkların olduğu satırı dinamik bulacağız
        df_raw = pd.read_excel(file, header=None)
        
        # 'MALZEME ADI' ifadesinin geçtiği satırı bul
        header_row_index = 0
        for i, row in df_raw.iterrows():
            if "MALZEME ADI" in row.values:
                header_row_index = i
                break
        
        # Dosyayı bulduğumuz başlık satırından itibaren tekrar oku
        df = pd.read_excel(file, header=header_row_index)
        
        # Sütun isimlerini temizle
        df.columns = [str(col).strip() for col in df.columns]

        # Sizin sütunlarınızla eşleme
        mapping = {
            'MALZEME ADI': 'urun_adi',
            'BİRİM FİYATI': 'maliyet',
            'CM.': 'boyut'
        }
        
        df = df.rename(columns=mapping)

        # Gerekli sütunlar var mı kontrol et
        if 'urun_adi' not in df.columns or 'maliyet' not in df.columns:
            return pd.DataFrame()

        # Boş satırları (NaN) temizle
        df = df.dropna(subset=['urun_adi', 'maliyet'])

        # Ürün adını boyutla birleştir (Örn: "Kasap Bıçağı - 15 CM")
        if 'boyut' in df.columns:
            df['urun_adi'] = df['urun_adi'].astype(str) + " - " + df['boyut'].astype(str) + " CM"

        # Barkod üret
        df['barkod'] = [f"BRK-{1000 + i}" for i in range(len(df))]
        
        # Maliyeti sayıya çevir
        df['maliyet'] = pd.to_numeric(df['maliyet'], errors='coerce').fillna(0)

        final_df = df[['barkod', 'urun_adi', 'maliyet']]

        # Veritabanına kaydet
        conn = sqlite3.connect('pazaryeri.db')
        final_df.to_sql('products', conn, if_exists='replace', index=False)
        conn.close()
        
        return final_df

    except Exception as e:
        print(f"Hata: {e}")
        return pd.DataFrame()