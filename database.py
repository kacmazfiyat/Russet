import sqlite3
import pandas as pd

def create_connection():
    return sqlite3.connect('pazaryeri.db', check_same_thread=False)

def init_db():
    conn = create_connection()
    cur = conn.cursor()
    # 1. Ana tabloyu oluştur
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
    
    # 2. kdv_dahil sütunu yoksa ekle (Eski ayarları bozmaz, sadece yeni özellik ekler)
    cur.execute("PRAGMA table_info(marketplaces)")
    columns = [column[1] for column in cur.fetchall()]
    if 'kdv_dahil' not in columns:
        cur.execute("ALTER TABLE marketplaces ADD COLUMN kdv_dahil INTEGER DEFAULT 1")
    
    conn.commit()
    conn.close()

def get_all_marketplaces():
    conn = create_connection()
    df = pd.read_sql_query("SELECT * FROM marketplaces", conn)
    conn.close()
    return df

def save_marketplace(data):
    conn = create_connection()
    cur = conn.cursor()
    cur.execute('''INSERT INTO marketplaces 
                   (name, komisyon, kargo, kupon, stopaj, kdv, hizmet, extras, varsayilan, kdv_dahil)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''.replace("extras", "ekstra"), 
                (data['name'], data['komisyon'], data['kargo'], data['kupon'],
                 data['stopaj'], data['kdv'], data['hizmet'], data['ekstra'], 
                 data.get('varsayilan', 0), data.get('kdv_dahil', 1)))
    conn.commit()
    conn.close()

def delete_marketplace(mp_id):
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM marketplaces WHERE id=?", (mp_id,))
    conn.commit()
    conn.close()
def get_all_products():
    conn = create_connection()
    # Excel'den yüklenen ürünlerin 'products' tablosunda olduğunu varsayıyoruz
    df = pd.read_sql_query("SELECT * FROM products", conn)
    conn.close()
    return df