import sqlite3
import pandas as pd

def create_connection():
    conn = sqlite3.connect('pazaryeri.db', check_same_thread=False)
    return conn

def init_db():
    conn = create_connection()
    cursor = conn.cursor()
    # Pazaryeri tablosu
    cursor.execute('''CREATE TABLE IF NOT EXISTS marketplaces (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, komisyon REAL, kargo REAL, kupon REAL, 
        stopaj REAL, kdv REAL, hizmet REAL, ekstra REAL, varsayilan INTEGER)''')
    # Ürünler tablosu
    cursor.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kategori TEXT, malzeme_adi TEXT, birim_fiyat REAL, sheet_adi TEXT)''')
    conn.commit()
    def delete_marketplace(mp_id):
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM marketplaces WHERE id=?", (mp_id,))
    conn.commit()
    conn.close()