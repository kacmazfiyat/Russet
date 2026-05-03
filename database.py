import sqlite3
import pandas as pd

def create_connection():
    """SQLite veritabanına güvenli bağlantı oluşturur."""
    return sqlite3.connect('pazaryeri.db', check_same_thread=False)

def init_db():
    """Tabloyu oluşturur ve eksik sütun varsa (kdv_dahil gibi) otomatik ekler."""
    conn = create_connection()
    cur = conn.cursor()
    
    # 1. Temel tabloyu oluştur (Eğer hiç yoksa)
    cur.execute('''CREATE TABLE IF NOT EXISTS marketplaces (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT, 
                    komisyon REAL, 
                    kargo REAL, 
                    kupon REAL,
                    stopaj REAL, 
                    kdv REAL, 
                    hizmet REAL, 
                    ekstra REAL, 
                    varsayilan INTEGER DEFAULT 0)''')
    
    # 2. Sütun Kontrolü: kdv_dahil sütunu yoksa ekle (OperationalError çözümü)
    cur.execute("PRAGMA table_info(marketplaces)")
    columns = [column[1] for column in cur.fetchall()]
    
    if 'kdv_dahil' not in columns:
        try:
            cur.execute("ALTER TABLE marketplaces ADD COLUMN kdv_dahil INTEGER DEFAULT 1")
            print("Sistem Güncelleme: kdv_dahil sütunu başarıyla eklendi.")
        except Exception as e:
            print(f"Sütun eklenirken hata oluştu: {e}")

    conn.commit()
    conn.close()

def get_all_marketplaces():
    """Tüm pazaryeri ayarlarını DataFrame olarak döndürür."""
    conn = create_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM marketplaces", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df

def save_marketplace(data):
    """Yeni pazaryeri ayarlarını kaydeder."""
    conn = create_connection()
    cur = conn.cursor()
    query = '''INSERT INTO marketplaces 
               (name, komisyon, kargo, kupon, stopaj, kdv, hizmet, ekstra, varsayilan, kdv_dahil)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''
    
    values = (
        data['name'], data['komisyon'], data['kargo'], data['kupon'],
        data['stopaj'], data['kdv'], data['hizmet'], data['ekstra'], 
        data.get('varsayilan', 0), data.get('kdv_dahil', 1)
    )
    
    cur.execute(query, values)
    conn.commit()
    conn.close()

def delete_marketplace(mp_id):
    """Belirtilen ID'ye sahip pazaryerini veritabanından siler."""
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM marketplaces WHERE id=?", (mp_id,))
    conn.commit()
    conn.close()

def clear_all_marketplaces():
    """Tablodaki tüm verileri temizler."""
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM marketplaces")
    conn.commit()
    conn.close()