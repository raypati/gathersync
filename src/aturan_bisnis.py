# Aturan bisnis: status pembayaran, armada, risiko H-3, bentrok jadwal, hash password
import datetime
import hashlib
from konfigurasi import RULE_DP_MIN_PERSEN, RULE_SELANG_HARI

def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def hitung_rekomendasi_armada(jumlah_peserta):
    if jumlah_peserta <= 9:
        return "Private Car / Transport Kecil (<10 org)"
    elif jumlah_peserta <= 16:
        return "Microbus / HiAce (Kapasitas 16 Kursi)"
    elif jumlah_peserta <= 30:
        return "Medium Bus (Kapasitas 30 Kursi)"
    else:
        jumlah_unit = (jumlah_peserta // 45) + (1 if jumlah_peserta % 45 > 0 else 0)
        return f"Big Bus (Multi-Unit: {jumlah_unit} Unit Kendaraan)"

def hitung_kategori(total, dibayar):
    total = total or 0
    dibayar = dibayar or 0
    persen = (dibayar / total * 100) if total > 0 else 0
    persen = max(0, min(persen, 100))
    if persen <= 0:
        kategori = "Belum Bayar"
    elif persen < RULE_DP_MIN_PERSEN:
        kategori = "DP Diterima"
    elif persen < 100:
        kategori = "Cicilan"
    else:
        kategori = "Lunas"
    return kategori, persen

def hitung_status_risiko(tanggal_keberangkatan_str):
    if not tanggal_keberangkatan_str:
        return None
    try:
        tgl = datetime.datetime.strptime(tanggal_keberangkatan_str, "%Y-%m-%d").date()
    except ValueError:
        return None
    return (tgl - datetime.date.today()).days

def cek_bentrok_jadwal(conn, leader_dipilih, tgl_baru_str, exclude_trip_id=None):
    # bentrok kalau leader yang sama punya trip dengan selisih < RULE_SELANG_HARI hari
    if not tgl_baru_str or not leader_dipilih or leader_dipilih == "Pilih Leader":
        return False, ""
    try:
        tgl_baru = datetime.datetime.strptime(tgl_baru_str, "%Y-%m-%d").date()
    except ValueError:
        return False, ""

    cursor = conn.cursor()
    rows = cursor.execute("SELECT id, nama_trip, leader, tanggal_keberangkatan FROM trip WHERE tanggal_keberangkatan IS NOT NULL").fetchall()
    for t_id, t_nama, t_ldr, t_tgl_str in rows:
        if exclude_trip_id and t_id == exclude_trip_id:
            continue
        if not t_ldr:
            continue
        try:
            tgl_ada = datetime.datetime.strptime(t_tgl_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        selisih = abs((tgl_baru - tgl_ada).days)
        if selisih < RULE_SELANG_HARI and t_ldr == leader_dipilih:
            return True, f"Leader '{leader_dipilih}' sudah bertugas di trip '{t_nama}' pada tanggal {t_tgl_str} (selisih {selisih} hari, minimal {RULE_SELANG_HARI} hari)."
    return False, ""
