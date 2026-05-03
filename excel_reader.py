import pandas as pd

def process_excel(file):
    try:
        xl = pd.ExcelFile(file)
    except Exception as e:
        return pd.DataFrame()

    all_data = []
    
    for sheet_name in xl.sheet_names:
        try:
            # Sayfayı ham veri olarak oku
            df_raw = pd.read_excel(file, sheet_name=sheet_name, header=None)
            
            # Başlık satırını dinamik olarak bul (Her sayfada farklı satırda olsa bile bulur)
            header_row_index = None
            for i, row in df_raw.iterrows():
                row_str = [str(val).upper() for val in row.values]
                if any('MALZEME ADI' in s for s in row_str) and any('BİRİM FİYATI' in s for s in row_str):
                    header_row_index = i
                    break
            
            if header_row_index is not None:
                # Veriyi bulduğumuz başlık satırından itibaren tekrar oku
                df = pd.read_excel(file, sheet_name=sheet_name, skiprows=header_row_index)
                df.columns = [str(c).strip().upper() for c in df.columns]
                
                col_malzeme = next((c for c in df.columns if 'MALZEME ADI' in c), None)
                col_fiyat = next((c for c in df.columns if 'BİRİM FİYATI' in c), None)
                
                if col_malzeme and col_fiyat:
                    valid_data = df[[col_malzeme, col_fiyat]].copy()
                    valid_data.columns = ['malzeme_adi', 'birim_fiyat']
                    
                    # Fiyatı sayıya çevir, hatalıları temizle
                    valid_data['birim_fiyat'] = pd.to_numeric(valid_data['birim_fiyat'], errors='coerce')
                    valid_data = valid_data.dropna(subset=['birim_fiyat', 'malzeme_adi'])
                    
                    # Sayfa adını kategori olarak ata
                    valid_data['kategori'] = sheet_name.strip()
                    all_data.append(valid_data)
        except:
            continue
            
    if all_data:
        return pd.concat(all_data, ignore_index=True)
    return pd.DataFrame()