import pandas as pd
import sqlite3

def process_excel(file):
    try:
        df_raw = pd.read_excel(file, header=None)
        header_row_index = 0
        for i, row in df_raw.iterrows():
            if "MALZEME ADI" in row.values:
                header_row_index = i
                break
        
        df = pd.read_excel(file, header=header_row_index)
        df.columns = [str(col).strip() for col in df.columns]

        mapping = {'MALZEME ADI': 'urun_adi', 'BİRİM FİYATI': 'maliyet', 'CM.': 'boyut'}
        df = df.rename(columns=mapping)

        if 'urun_adi' not in df.columns or 'maliyet' not in df.columns:
            return pd.DataFrame()

        df = df.dropna(subset=['urun_adi', 'maliyet'])
        if 'boyut' in df.columns:
            df['urun_adi'] = df['urun_adi'].astype(str) + " - " + df['boyut'].astype(str) + " CM"

        # Dosya adını da kaydedelim ki neyi sildiğimizi bilelim
        df['dosya_adi'] = file.name 
        df['barkod'] = [f"BRK-{1000 + i}-{file.name[:5]}" for i in range(len(df))]
        df['maliyet'] = pd.to_numeric(df['maliyet'], errors='coerce').fillna(0)

        final_df = df[['barkod', 'urun_adi', 'maliyet', 'dosya_adi']]

        conn = sqlite3.connect('pazaryeri.db')
        # DİKKAT: 'append' yaparak eski veriyi koruyoruz
        final_df.to_sql('products', conn, if_exists='append', index=False)
        conn.close()
        
        return final_df
    except Exception as e:
        return pd.DataFrame()