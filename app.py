import os
import re
import sqlite3
import pandas as pd
from flask import Flask, render_template, request, flash, redirect, url_for

app = Flask(__name__)
app.secret_key = "pazaryeri_pro_key_123"

# --- VERİTABANI AYARLARI ---
DB_NAME = 'pazaryeri.db'

def init_db():
    """Veritabanı ve tabloyu oluşturur."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barkod TEXT,
            urun_adi TEXT,
            maliyet REAL,
            dosya_adi TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Uygulama başlarken veritabanını hazırla
init_db()

# --- EXCEL İŞLEME MOTORU ---
def process_excel_logic(file):
    try:
        xls = pd.ExcelFile(file)
        all_products = []
        
        for sheet_name in xls.sheet_names:
            # Excel'in ilk 10 satırını oku (başlığı bulmak için)
            df_header_check = pd.read_excel(file, sheet_name=sheet_name, header=None).head(10)
            
            header_idx = None
            # "MALZEME ADI" yazan satırı dinamik bul
            for i, row in df_header_check.iterrows():
                row_vals = [str(val).strip().upper() for val in row.values if pd.notna(val)]
                if "MALZEME ADI" in row_vals:
                    header_idx = i
                    break
            
            if header_idx is None:
                continue # Başlık bulunamadıysa bu sayfayı atla

            # Sayfayı bulduğumuz satırdan itibaren oku
            df = pd.read_excel(file, sheet_name=sheet_name, header=header_idx)
            
            # Sütun isimlerini temizle
            df.columns = [str(c).strip().upper() for c in df.columns]

            # Sizin Excel yapınızdaki sütunları eşleştir
            # 'MALZEME ADI' -> urun_adi, 'BİRİM FİYATI' -> maliyet, 'CM.' -> boyut
            col_map = {
                'MALZEME ADI': 'urun_adi',
                'BİRİM FİYATI': 'maliyet',
                'CM.': 'boyut'
            }
            df = df.rename(columns=col_map)

            # Sadece ihtiyacımız olan sütunları al (Eğer varsa)
            needed_cols = [c for c in ['urun_adi', 'maliyet', 'boyut'] if c in df.columns]
            df = df[needed_cols]

            # Boş satırları at
            df = df.dropna(subset=['urun_adi', 'maliyet'])
            
            # Sayı temizleme fonksiyonu
            def clean_price(price):
                try:
                    if pd.isna(price): return 0.0
                    p_str = str(price).replace('.', '').replace(',', '.')
                    res = re.findall(r"[-+]?\d*\.\d+|\d+", p_str)
                    return float(res[0]) if res else 0.0
                except:
                    return 0.0

            df['maliyet'] = df['maliyet'].apply(clean_price)
            df = df[df['maliyet'] > 0] # 0 olanları ele

            # Boyut bilgisini isme ekle
            if 'boyut' in df.columns:
                df['urun_adi'] = df['urun_adi'].astype(str) + " (" + df['boyut'].astype(str) + " CM)"

            all_products.append(df)

        if not all_products:
            return None

        final_df = pd.concat(all_products, ignore_index=True)
        final_df['dosya_adi'] = getattr(file, 'filename', 'Excel_Dosyasi')
        final_df['barkod'] = [f"BRK-{1000 + i}" for i in range(len(final_df))]
        
        # Veritabanına Yazma
        conn = sqlite3.connect(DB_NAME)
        final_df[['barkod', 'urun_adi', 'maliyet', 'dosya_adi']].to_sql('products', conn, if_exists='append', index=False)
        conn.close()
        
        return len(final_df)

    except Exception as e:
        print(f"Hata detayı: {e}")
        return None

# --- ROUTE'LAR (SAYFALAR) ---

@app.route('/')
def index():
    return render_template('index.html') # Veya ana sayfanız hangisiyse

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash("Dosya seçilmedi", "danger")
        return redirect(request.referrer)
    
    file = request.files['file']
    if file.filename == '':
        flash("Dosya adı boş", "danger")
        return redirect(request.referrer)

    count = process_excel_logic(file)
    
    if count:
        flash(f"Başarılı! {count} adet ürün veritabanına eklendi.", "success")
    else:
        flash("Dosya işlenemedi. Sütun isimlerini veya formatı kontrol edin.", "danger")
        
    return redirect(request.referrer)

@app.route('/products')
def list_products():
    conn = sqlite3.connect(DB_NAME)
    # Veritabanından çekerek sayfayı yenileseniz de gitmemesini sağlıyoruz
    df = pd.read_sql_query("SELECT * FROM products", conn)
    conn.close()
    products = df.to_dict(orient='records')
    return render_template('analiz.html', products=products)

if __name__ == '__main__':
    app.run(debug=True, port=5000)