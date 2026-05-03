import pandas as pd

def process_excel(file):
    xl = pd.ExcelFile(file)
    all_data = []
    
    for sheet_name in xl.sheet_names:
        # 3. satırı (index 2) kategori adı olarak al
        temp_df = pd.read_excel(file, sheet_name=sheet_name, header=None, nrows=5)
        kategori = str(temp_df.iloc[2, 0]) if not temp_df.empty else "Genel"
        
        # Veriyi oku
        df = pd.read_excel(file, sheet_name=sheet_name)
        
        # Sütunları temizle ve bul
        df.columns = [str(c).strip().upper() for c in df.columns]
        
        # Dinamik sütun eşleştirme
        col_map = {
            'malzeme_adi': next((c for c in df.columns if 'MALZEME ADI' in c), None),
            'birim_fiyat': next((c for c in df.columns if 'BİRİM FİYATI' in c or 'FİYAT' in c), None)
        }
        
        if col_map['malzeme_adi'] and col_map['birim_fiyat']:
            valid_data = df[[col_map['malzeme_adi'], col_map['birim_fiyat']]].copy()
            valid_data.columns = ['malzeme_adi', 'birim_fiyat']
            valid_data['kategori'] = kategori
            valid_data['sheet_adi'] = sheet_name
            all_data.append(valid_data)
            
    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()