import sqlite3

def setup_database():
    conn = sqlite3.connect('pazaryeri.db')
    cursor = conn.cursor()
    # Tabloyu oluştur (barkod, urun_adi, maliyet, dosya_adi)
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
    print("Veritabanı başarıyla hazırlandı.")

if __name__ == "__main__":
    setup_database()