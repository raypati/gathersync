<<<<<<< HEAD
# GatherSync (TripMate)

Aplikasi desktop untuk mengelola Open Trip dan kas kelompok, dilengkapi manajemen trip,
kas peserta, plotting kursi multi-unit, itinerary, dan laporan PDF.
Dibuat sebagai proyek mata kuliah Rekayasa Perangkat Lunak, Universitas Indraprasta PGRI.

## Anggota Tim
- (nama anggota 1) — feature/menu-dashboard (Menu Dashboard Trip)
- (nama anggota 2) — feature/menu-kas (Menu Registrasi & Kas)
- (nama anggota 3) — feature/menu-plotting (Menu Plotting Kursi)

## Struktur Program

| File | Isi | Branch kerja |
|------|-----|--------------|
| gathersync.py | Program utama: login, kerangka aplikasi, navigasi | chore/setup-repo |
| ui_umum.py | Fungsi gradien tampilan yang dipakai bersama | chore/setup-repo |
| konfigurasi.py | Warna, font, daftar leader, konstanta aturan | feature/database-aturan |
| aturan_bisnis.py | Status pembayaran, armada, risiko H-3, bentrok jadwal | feature/database-aturan |
| database.py | Pembuatan tabel SQLite dan audit log | feature/database-aturan |
| menu_dashboard.py | Menu Dashboard Trip | feature/menu-dashboard |
| menu_kas.py | Menu Registrasi & Kas | feature/menu-kas |
| menu_plotting.py | Menu Plotting Kursi & Multi-Unit | feature/menu-plotting |
| menu_itinerary.py | Menu Itinerary | feature/menu-itinerary |
| menu_manifest.py | Menu Manifest & Audit PDF | feature/menu-manifest |
| test_gathersync.py | Unit test | test/unit-test-logika |
| docs/ | Dokumen SRS, diagram, laporan | docs/srs-uml |

## Cara Menjalankan
1. Clone repository: `git clone <url-repo>`
2. Pasang pustaka: `pip install -r requirements.txt`
3. Jalankan: `python gathersync.py`
4. Login dengan akun awal `admin` / `123` (database dibuat otomatis)

## Menjalankan Pengujian
```
python -m unittest test_gathersync -v
```
=======
# Dokumen
Dokumen tugas Rekayasa Perangkat Lunak untuk proyek GatherSync.
>>>>>>> 642f91f3c1966f8b531c54c843e8215d3733bbad
