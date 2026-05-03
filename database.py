import sqlite3
import pandas as pd

def create_connection():
    """SQLite veritabanına bağlantı oluşturur."""
    return sqlite3.connect('pazaryeri.db', check_same_thread=False)

def init_db():
    """Veritabanı tablolarını ilk kez oluşturur."""
    conn = create_connection()
    cur = conn.cursor()
    # Pazaryeri ayarları tablosu
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
                    varsayilan INTEGER)''')
    conn.commit()
    conn.close()

def get_all_marketplaces():
    """Tüm pazaryeri kayıtlarını DataFrame olarak döner."""
    conn = create_connection()
    df = pd.read_sql_query("SELECT * FROM marketplaces", conn)
    conn.close()
    return df

def save_marketplace(data):
    """Yeni bir pazaryeri ayarı kaydeder."""
    conn = create_connection()
    cur = conn.cursor()
    cur.execute('''INSERT INTO marketplaces 
                   (name, komisyon, kargo, kupon, stopaj, kdv, hizmet, ekstra, varsayilan)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                (data['name'], data['komisyon'], data['kargo'], data['kupon'],
                 data['stopaj'], data['kdv'], data['hizmet'], data['ekstra'], data['varsayilan']))
    conn.commit()
    conn.close()

def delete_marketplace(mp_id):
    """ID değerine göre tek bir pazaryeri kaydını siler."""
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM marketplaces WHERE id=?", (mp_id,))
    conn.commit()
    conn.close()

def clear_all_marketplaces():
    """Tüm pazaryeri tablosunu sıfırlar."""
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM marketplaces")
    conn.commit()
    conn.close()