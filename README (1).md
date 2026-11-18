# GatherSync (TripMate)

Aplikasi desktop untuk mengelola Open Trip dan kas kelompok. Dibuat sebagai proyek mata kuliah
Rekayasa Perangkat Lunak, Universitas Indraprasta PGRI (Unindra).

## Fitur

- Login admin (password disimpan sebagai hash SHA-256)
- Manajemen trip: leader, tim otomatis, harga flat, validasi bentrok jadwal leader
- Registrasi dan kas peserta dengan status otomatis (Belum Bayar, DP Diterima, Cicilan, Lunas)
- Rekomendasi armada dan plotting kursi multi-unit (sopir di kanan depan)
- Itinerary kegiatan
- Manifest, log audit otomatis, dan ekspor PDF

## Teknologi

Python 3, customtkinter, tkcalendar, SQLite (sqlite3), reportlab.

## Cara menjalankan

```bash
git clone https://github.com/<username>/gathersync.git
cd gathersync
pip install -r requirements.txt
python gathersync.py
```

Akun awal: `admin` / `123`. File `gathersync.db` dibuat otomatis saat pertama dijalankan.

## Menjalankan pengujian

```bash
python -m unittest test_gathersync -v
```

## Struktur repositori

```
gathersync.py          program utama
test_gathersync.py     unit test (blackbox dan whitebox)
requirements.txt       daftar pustaka
docs/                  dokumen tugas (SRS, diagram, laporan)
.github/               template issue dan pull request
```

## Tim

| Nama | NPM | Peran | GitHub |
|------|-----|-------|--------|
| Rai Putra | 202343501243 | (isi) | (isi) |
| (isi) | (isi) | (isi) | (isi) |

## Berkontribusi

Baca [CONTRIBUTING.md](CONTRIBUTING.md) sebelum membuat branch atau pull request.
