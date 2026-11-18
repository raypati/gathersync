"""Pengujian GatherSync (blackbox dan whitebox) untuk fungsi logika inti.

Jalankan:  python -m unittest test_gathersync -v
File gathersync.py harus berada di folder yang sama.
"""
import datetime
import os
import tempfile
import unittest

import gathersync as g


class TestStatusPembayaran(unittest.TestCase):
    """Blackbox: equivalence partitioning dan boundary value (total tagihan 100)."""

    CASES = [
        ("BB-01", 0, "Belum Bayar"),
        ("BB-02", 1, "DP Diterima"),
        ("BB-03", 29, "DP Diterima"),
        ("BB-04", 30, "Cicilan"),
        ("BB-05", 99, "Cicilan"),
        ("BB-06", 100, "Lunas"),
        ("BB-07", 150, "Lunas"),   # bayar melebihi tagihan
        ("BB-08", -10, "Belum Bayar"),  # nominal negatif dipotong ke 0%
    ]

    def test_batas_persen(self):
        for kode, bayar, harapan in self.CASES:
            with self.subTest(kode=kode, bayar=bayar):
                kategori, _ = g.hitung_kategori(100, bayar)
                self.assertEqual(kategori, harapan)

    def test_total_nol(self):
        kategori, persen = g.hitung_kategori(0, 50)
        self.assertEqual((kategori, persen), ("Belum Bayar", 0))

    def test_nilai_none(self):
        self.assertEqual(g.hitung_kategori(None, None)[0], "Belum Bayar")


class TestRekomendasiArmada(unittest.TestCase):
    """Blackbox: boundary value jumlah peserta."""

    def test_batas(self):
        kasus = [
            (0, "Private Car"), (1, "Private Car"), (9, "Private Car"),
            (10, "Microbus"), (16, "Microbus"),
            (17, "Medium Bus"), (30, "Medium Bus"),
            (31, "1 Unit"), (45, "1 Unit"), (46, "2 Unit"), (91, "3 Unit"),
        ]
        for n, ciri in kasus:
            with self.subTest(peserta=n):
                self.assertIn(ciri, g.hitung_rekomendasi_armada(n))


class TestRisiko(unittest.TestCase):
    def test_hari_ke_depan(self):
        besok3 = (datetime.date.today() + datetime.timedelta(days=3)).strftime("%Y-%m-%d")
        self.assertEqual(g.hitung_status_risiko(besok3), 3)

    def test_hari_ini(self):
        self.assertEqual(g.hitung_status_risiko(datetime.date.today().strftime("%Y-%m-%d")), 0)

    def test_sudah_lewat(self):
        kemarin = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        self.assertEqual(g.hitung_status_risiko(kemarin), -1)

    def test_kosong_dan_salah_format(self):
        self.assertIsNone(g.hitung_status_risiko(""))
        self.assertIsNone(g.hitung_status_risiko(None))
        self.assertIsNone(g.hitung_status_risiko("14-11-2026"))


class DbTestCase(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)
        self.conn = g.setup_database()

    def tearDown(self):
        self.conn.close()
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def tambah_trip(self, leader, tanggal, nama="Trip Uji"):
        cur = self.conn.cursor()
        cur.execute("INSERT INTO trip (nama_trip, leader, tim, tanggal_keberangkatan, harga_trip) VALUES (?,?,?,?,?)",
                    (nama, leader, "", tanggal, 100000))
        self.conn.commit()
        return cur.lastrowid


class TestBentrokJadwal(DbTestCase):
    """Blackbox: selisih tanggal leader yang sama."""

    def test_selisih(self):
        self.tambah_trip("Budi Santoso", "2026-11-10")
        kasus = [("2026-11-10", True), ("2026-11-11", True), ("2026-11-09", True),
                 ("2026-11-12", False), ("2026-11-08", False)]
        for tgl, bentrok in kasus:
            with self.subTest(tanggal=tgl):
                self.assertEqual(g.cek_bentrok_jadwal(self.conn, "Budi Santoso", tgl)[0], bentrok)

    def test_leader_berbeda(self):
        self.tambah_trip("Budi Santoso", "2026-11-10")
        self.assertFalse(g.cek_bentrok_jadwal(self.conn, "Siti Rahma", "2026-11-10")[0])


class TestBasisPathBentrok(DbTestCase):
    """Whitebox: 8 jalur independen cek_bentrok_jadwal (V(G) = 8)."""

    def test_path_1_input_tidak_valid(self):
        self.assertEqual(g.cek_bentrok_jadwal(self.conn, "Pilih Leader", "2026-11-10"), (False, ""))
        self.assertEqual(g.cek_bentrok_jadwal(self.conn, "Budi Santoso", ""), (False, ""))

    def test_path_2_format_tanggal_baru_salah(self):
        self.assertEqual(g.cek_bentrok_jadwal(self.conn, "Budi Santoso", "10/11/2026"), (False, ""))

    def test_path_3_tidak_ada_trip(self):
        self.assertFalse(g.cek_bentrok_jadwal(self.conn, "Budi Santoso", "2026-11-10")[0])

    def test_path_4_trip_yang_diedit_dilewati(self):
        t_id = self.tambah_trip("Budi Santoso", "2026-11-10")
        self.assertFalse(g.cek_bentrok_jadwal(self.conn, "Budi Santoso", "2026-11-10", exclude_trip_id=t_id)[0])

    def test_path_5_trip_tanpa_leader_dilewati(self):
        self.tambah_trip(None, "2026-11-10")
        self.assertFalse(g.cek_bentrok_jadwal(self.conn, "Budi Santoso", "2026-11-10")[0])

    def test_path_6_tanggal_trip_lama_rusak(self):
        self.tambah_trip("Budi Santoso", "bukan-tanggal")
        self.assertFalse(g.cek_bentrok_jadwal(self.conn, "Budi Santoso", "2026-11-10")[0])

    def test_path_7_tidak_bentrok(self):
        self.tambah_trip("Budi Santoso", "2026-11-20")
        self.assertFalse(g.cek_bentrok_jadwal(self.conn, "Budi Santoso", "2026-11-10")[0])

    def test_path_8_bentrok(self):
        self.tambah_trip("Budi Santoso", "2026-11-10", nama="Open Trip Anyer")
        bentrok, pesan = g.cek_bentrok_jadwal(self.conn, "Budi Santoso", "2026-11-11")
        self.assertTrue(bentrok)
        self.assertIn("Open Trip Anyer", pesan)


class TestLoginDanDatabase(DbTestCase):
    def test_hash_konsisten_dan_64_karakter(self):
        self.assertEqual(g.hash_password("123"), g.hash_password("123"))
        self.assertEqual(len(g.hash_password("123")), 64)
        self.assertNotEqual(g.hash_password("123"), g.hash_password("124"))

    def _login(self, user, pw):
        return self.conn.execute("SELECT id FROM admin WHERE username=? AND password=?",
                                 (user, g.hash_password(pw))).fetchone() is not None

    def test_login_benar_dan_salah(self):
        self.assertTrue(self._login("admin", "123"))
        self.assertFalse(self._login("admin", "salah"))
        self.assertFalse(self._login("bukanadmin", "123"))

    def test_password_tidak_disimpan_polos(self):
        tersimpan = self.conn.execute("SELECT password FROM admin").fetchone()[0]
        self.assertNotEqual(tersimpan, "123")
        self.assertEqual(len(tersimpan), 64)

    def test_migrasi_password_lama(self):
        self.conn.execute("UPDATE admin SET password='abc'")
        self.conn.commit()
        self.conn.close()
        self.conn = g.setup_database()
        tersimpan = self.conn.execute("SELECT password FROM admin").fetchone()[0]
        self.assertEqual(tersimpan, g.hash_password("abc"))

    def test_lima_tabel_terbentuk(self):
        nama = {r[0] for r in self.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for tabel in ("admin", "trip", "peserta", "itinerary", "audit_log"):
            self.assertIn(tabel, nama)

    def test_catat_audit(self):
        g.catat_audit(self.conn, 1, "Andi", "Registrasi", "Bayar awal")
        baris = self.conn.execute("SELECT nama, aksi, keterangan FROM audit_log").fetchall()
        self.assertEqual(baris, [("Andi", "Registrasi", "Bayar awal")])


if __name__ == "__main__":
    unittest.main()
