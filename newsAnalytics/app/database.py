import sqlite3
import os

# Set ke False karena kita murni menggunakan file SQLite lokal
IS_POSTGRES = False 

# Mendapatkan jalur direktori dasar proyek secara absolut dan mengarah tepat ke google_news.db
# Ini menjamin skrip Scraper dan skrip Dashboard membaca dan menulis pada file fisik yang SAMA.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "google_news.db")

def dapatkan_koneksi_db():
    """Membuka file SQLite menggunakan jalur absolut, tanpa password, aman, dan anti-mismatch."""
    try:
        # Langsung membuka koneksi standar bawaan Python ke berkas database yang sama
        conn = sqlite3.connect(DB_PATH)
        return conn
    except Exception as e:
        raise Exception(f"Gagal membuka file database SQLite di {DB_PATH}: {str(e)}")

# Fungsi pembantu tambahan dari ui_backup.py Anda (jika ada yang membutuhkannya di modul lain)
def ambil_data_dari_db(query, params=()):
    try:
        conn = dapatkan_koneksi_db()
        cursor = conn.cursor()
        cursor.execute(query, params)
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        return data
    except Exception as e:
        print(f"Error ambil data: {str(e)}")
        return []