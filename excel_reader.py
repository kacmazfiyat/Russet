import pandas as pd

def process_excel(file):
    """
    Excel dosyasındaki tüm sayfaları tarar, sayfa isimlerini kategori olarak alır
     ve 3. satırdaki (skiprows=2) başlıkları kullanarak verileri ayıklar.
    """
    try:
        xl = pd.ExcelFile(file)
    except Exception as e:
        print(f"Excel dosyası açılırken hata oluştu: {e}")
        return pd.DataFrame()

    all_data = []
    
    for sheet_name in xl.sheet_names:
        # Sayfa ismini kategori adı olarak belirle
        kategori = sheet_name.strip()
        
        try:
            # Dosya yapısına göre ilk 2 satırı atlıyoruz (skiprows=2), 
            # böylece 3. satırdaki 'MALZEME ADI' ve 'BİRİM FİYATI' başlıkları okunur.
            df = pd.read_excel(file, sheet_name=sheet_name, skiprows=2)
            
            # Sütun isimlerindeki boşlukları temizle ve büyük harfe çevir (Eşleşme kolaylığı için)
            df.columns = [str(c).strip().upper() for c in df.columns]
            
            # Dosyandaki tam sütun isimlerini hedef alıyoruz
            col_malzeme = next((c for c in df.columns if 'MALZEME ADI' in c), None)
            col_fiyat = next((c for c in df.columns if 'BİRİM FİYATI' in c), None)
            
            if col_malzeme and col_fiyat:
                # Sadece ilgili sütunları seç ve kopyala
                valid_data = df[[col_malzeme, col_fiyat]].copy()
                valid_data.columns = ['malzeme_adi', 'birim_fiyat']
                
                # 'BİRİM FİYATI' sütununu sayısal değere çevir, sayı olmayanları (TL yazısı vb.) NaN yap
                valid_data['birim_fiyat'] = pd.to_numeric(valid_data['birim_fiyat'], errors='coerce')
                
                # Hem fiyatı hem de adı boş olmayan satırları filtrele
                valid_data = valid_data.dropna(subset=['birim_fiyat', 'malzeme_adi'])
                
                # Veriye kategori ve sayfa bilgisini ekle
                valid_data['kategori'] = kategori
                valid_data['sheet_adi'] = sheet_name
                
                all_data.append(valid_data)
        except Exception as e:
            print(f"{sheet_name} sayfası işlenirken hata oluştu: {e}")
            continue
            
    # Tüm sayfalardan toplanan verileri birleştir
    if all_data:
        final_df = pd.concat(all_data, ignore_index=True)
        # Malzeme adlarındaki gereksiz boşlukları temizle
        final_df['malzeme_adi'] = final_df['malzeme_adi'].astype(str).str.strip()
        return final_df
    
    return pd.DataFrame()