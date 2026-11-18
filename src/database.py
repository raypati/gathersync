# Database SQLite dan pencatatan audit log
import datetime
import sqlite3
from aturan_bisnis import hash_password

def setup_database():
    conn = sqlite3.connect("gathersync.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS admin (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, password TEXT)''')
    cursor.execute("SELECT COUNT(*) FROM admin")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO admin (username, password) VALUES (?, ?)", ("admin", hash_password("123")))
    else:
        # password lama (teks biasa) diubah jadi hash
        for a_id, a_pass in cursor.execute("SELECT id, password FROM admin").fetchall():
            if a_pass is not None and len(a_pass) != 64:
                cursor.execute("UPDATE admin SET password=? WHERE id=?", (hash_password(a_pass), a_id))

    cursor.execute('''CREATE TABLE IF NOT EXISTS trip (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nama_trip TEXT, leader TEXT, tim TEXT,
                        tanggal_keberangkatan TEXT, harga_trip REAL DEFAULT 0)''')

    try:
        cursor.execute("ALTER TABLE trip ADD COLUMN harga_trip REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    cursor.execute('''CREATE TABLE IF NOT EXISTS peserta (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, id_trip INTEGER,
                        nama TEXT, total_tagihan REAL, nominal_bayar REAL,
                        sisa_tagihan REAL, status TEXT, kursi_bus TEXT, unit_bus TEXT DEFAULT 'Unit 1')''')

    try:
        cursor.execute("ALTER TABLE peserta ADD COLUMN unit_bus TEXT DEFAULT 'Unit 1'")
    except sqlite3.OperationalError:
        pass

    cursor.execute('''CREATE TABLE IF NOT EXISTS itinerary (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, id_trip INTEGER,
                        hari TEXT, jam TEXT, kegiatan TEXT,
                        titik_kumpul TEXT, dresscode TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS audit_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, id_trip INTEGER,
                        nama TEXT, aksi TEXT, keterangan TEXT, waktu TEXT)''')
    conn.commit()
    return conn

def catat_audit(conn, id_trip, nama, aksi, keterangan):
    waktu = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.cursor().execute("INSERT INTO audit_log (id_trip, nama, aksi, keterangan, waktu) VALUES (?, ?, ?, ?, ?)", (id_trip, nama, aksi, keterangan, waktu))
    conn.commit()
