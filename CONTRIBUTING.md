# Panduan Kolaborasi

## Alur kerja
<<<<<<< HEAD
1. Ambil satu issue dari daftar tugas.
2. Pindah ke `main` dan ambil versi terbaru: `git checkout main` lalu `git pull`.
3. Buat branch sesuai tugas: `git checkout -b feature/menu-kas`.
4. Kerjakan di file milik tugasmu, lalu commit dengan pesan yang jelas.
5. Push branch: `git push origin feature/menu-kas`.
6. Buat Pull Request ke `main` di GitHub dan minta review anggota lain.
7. Setelah disetujui, merge. Selesaikan conflict bila ada.
=======

1. Ambil atau buat **issue** untuk pekerjaan yang akan dikerjakan.
2. Buat branch dari `develop` dengan nama sesuai jenis pekerjaan.
3. Commit perubahan kecil dan sering dengan pesan yang jelas.
4. Push branch, lalu buat **pull request** ke `develop`.
5. Minimal satu anggota lain mereview. Perbaiki bila ada catatan.
6. Setelah disetujui dan test lulus, merge, lalu hapus branch.
7. Saat milestone selesai, `develop` digabung ke `main`.
>>>>>>> 642f91f3c1966f8b531c54c843e8215d3733bbad

Jangan commit langsung ke `main`.

## Nama branch
<<<<<<< HEAD
- `feature/<nama>` untuk fitur atau menu
- `fix/<nama>` untuk perbaikan bug
- `docs/<nama>` untuk dokumen
- `test/<nama>` untuk pengujian

## Pesan commit
Tulis kalimat yang menjelaskan apa yang berubah.

| Kurang baik | Lebih baik |
|-------------|------------|
| update | Menambahkan validasi pembayaran yang melebihi total tagihan |
| fix bug | Memperbaiki sisa tagihan yang bernilai negatif pada menu kas |
| perubahan | Menambahkan konfirmasi sebelum menghapus kegiatan itinerary |

## Sebelum membuat Pull Request
- Jalankan `python gathersync.py` dan coba bagian yang kamu ubah.
- Jalankan `python -m unittest test_gathersync -v`.
=======

| Jenis | Format | Contoh |
|-------|--------|--------|
| Fitur | `feature/<nama-singkat>` | `feature/validasi-bentrok-jadwal` |
| Perbaikan | `fix/<nama-singkat>` | `fix/sisa-tagihan-negatif` |
| Dokumen | `docs/<nama-singkat>` | `docs/srs-revisi` |
| Test | `test/<nama-singkat>` | `test/basis-path-bentrok` |

## Pesan commit

Format: `jenis: ringkasan singkat`

- `feat:` fitur baru
- `fix:` perbaikan bug
- `docs:` dokumen
- `test:` pengujian
- `refactor:` merapikan kode tanpa mengubah perilaku

Contoh: `fix: tolak pembayaran melebihi total tagihan`

## Sebelum membuat pull request

- Jalankan `python -m unittest test_gathersync -v` dan pastikan lulus.
- Jalankan aplikasi dan coba bagian yang diubah.
>>>>>>> 642f91f3c1966f8b531c54c843e8215d3733bbad
- Jangan commit `gathersync.db` atau file PDF laporan.
