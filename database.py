import sqlite3
import pandas as pd

def create_connection():
    return sqlite3.connect('pazaryeri.db', check_same_thread=False)

def init_db():
    conn = create_connection()
    cur = conn.cursor()
    # kdv_dahil sütunu eklendi (1: Dahil, 0: Hariç)
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
                    varsayilan INTEGER,
                    kdv_dahil INTEGER DEFAULT 1)''')
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
                   (name, komisyon, kargo, kupon, stopaj, kdv, hizmet, ekstra, varsayilan, kdv_dahil)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                (data['name'], data['komisyon'], data['kargo'], data['kupon'],
                 data['stopaj'], data['kdv'], data['hizmet'], data['ekstra'], 
                 data['varsayilan'], data['kdv_dahil']))
    conn.commit()
    conn.close()

def delete_marketplace(mp_id):
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM marketplaces WHERE id=?", (mp_id,))
    conn.commit()
    conn.close()

def clear_all_marketplaces():
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM marketplaces")
    conn.commit()
    conn.close()