# Daftar Periksa Pengujian

Lakukan berurutan. Setiap langkah punya **cara memeriksa** dan **yang diharapkan**.

---

## 0. Prasyarat

```bash
python main.py --doctor
```

**Diharapkan:** semua `[ OK ]`. Bila ada `[GAGAL]`, perbaiki dulu — lihat
[`PERBAIKAN.md`](PERBAIKAN.md).

---

## 1. Antarmuka tampil

```bash
python main.py
```

**Diperiksa**
- Peramban terbuka di `http://127.0.0.1:8765/`
- Avatar 3D SELA muncul di tengah
- Bilah atas menampilkan "SELA" dan lencana status
- Panel "SELA ASISTEN UCIC" tampil di kanan (desktop)

**Diharapkan:** tidak ada layar putih, tidak ada galat di konsol peramban (F12).

---

## 2. Tata letak potret

```bash
python main.py --portrait
```

**Diperiksa**
- Jendela berbentuk potret (±480×900)
- Avatar mengisi layar
- Panel percakapan tersembunyi; tombol "Buka Chat" muncul di kanan atas

**Diharapkan:** tidak ada elemen yang terpotong atau saling menumpuk.

---

## 3. Mode kios

```bash
python main.py --portrait --kiosk
```

**Diharapkan:** jendela tanpa bingkai, layar penuh. Untuk keluar: `Alt+F4`
(Windows) atau `Ctrl+C` di terminal.

---

## 4. Tombol mikrofon (alur suara)

1. Pastikan mesin AI sudah tersambung (lencana hijau "Siap")
2. Tekan tombol mikrofon besar di bawah avatar
3. Ucapkan: **"Bagaimana cara mendaftar?"**
4. Tekan tombol sekali lagi (atau tunggu)

**Diperiksa**
- Tombol berubah merah + berdenyut saat mendengarkan
- Status berubah: `Mendengarkan` → `Sedang berpikir` → `SELA sedang bicara`
- Pertanyaan muncul di panel sebagai pesan **Anda**
- Jawaban muncul sebagai pesan **SELA**
- Suara terdengar dari pengeras suara

**Diharapkan:** ada jawaban, dan **mulut avatar bergerak mengikuti suara**.

---

## 5. Lipsync

Saat SELA berbicara, perhatikan mulut avatar.

**Diperiksa**
- Mulut membuka-menutup mengikuti irama suara (bukan acak)
- Saat suara berhenti, mulut menutup
- Bentuk mulut berubah untuk vokal berbeda (a/i/u/e/o)

**Diharapkan:** gerakan halus dan sinkron, tidak kaku.

---

## 6. Kirim teks

1. Ketik "Apa saja program studi yang tersedia?" di kolom panel kanan
2. Tekan Enter atau tombol kirim

**Diharapkan:** sama seperti alur suara, tetapi tanpa rekaman mikrofon.

---

## 7. Pertanyaan populer

Tekan salah satu tombol: **Cara Daftar?**, **Biaya Kuliah**, **Program Studi**,
**Kontak & Lokasi**.

**Diharapkan:** pertanyaan langsung terkirim dan dijawab.

---

## 8. Memotong ucapan SELA

Saat SELA sedang berbicara, tekan tombol mikrofon sekali.

**Diharapkan:** suara berhenti seketika, status kembali ke `Siap mendengarkan`.

---

## 9. Panel percakapan

| Aksi | Diharapkan |
| --- | --- |
| Tombol `>` di panel | Panel menyusut; tombol "Buka Chat" muncul |
| Tombol "Buka Chat" | Panel kembali tampil |
| "+ Sesi Baru" | Percakapan dikosongkan, sesi lama masuk riwayat |
| Gulir ke atas | Tombol gulir-ke-bawah muncul |

---

## 10. Menu samping

1. Tekan ikon hamburger (kiri atas)

**Diperiksa**
- Menu meluncur dari kiri
- "Sesi Baru" berfungsi
- Pencarian menyaring riwayat
- "Pengaturan" dan "Bantuan" membuka halaman masing-masing
- Tombol `Esc` menutup menu

---

## 11. Pengaturan

Buka **Pengaturan**.

**Diperiksa**
- Nilai yang tampil berasal dari mesin AI (bukan nilai palsu)
- Mengganti **Tema** langsung mengubah tampilan
- Dropdown **Mikrofon** / **Pengeras Suara** memuat daftar perangkat nyata
- Mengubah pilihan **tersimpan** (muat ulang halaman, nilainya tetap)

---

## 12. Bantuan

Buka **Bantuan**.

**Diharapkan:** semua bagian terisi, tanpa teks kosong atau placeholder.

---

## 13. Bahasa

**Diperiksa:** telusuri seluruh antarmuka — menu, tombol, status, pengaturan,
bantuan.

**Diharapkan:** **100% Bahasa Indonesia**, tidak ada karakter Tionghoa atau
teks Inggris yang tertinggal.

---

## 14. Build

Ikuti [`BUILD.md`](BUILD.md) untuk platform Anda.

**Diperiksa**
- Skrip selesai tanpa galat
- Berkas hasil ada di `installer/`
- Ukuran wajar (perkiraan: 200-500 MB, karena mesin AI ikut dikemas)

**Uji paket terpasang**
1. Pasang hasil build
2. Jalankan dari Start Menu / launcher aplikasi
3. Ulangi langkah 1, 4, dan 6

---

## 15. Uji di Raspberry Pi (target akhir)

Lakukan di Pi yang sebenarnya, bukan di komputer pengembangan.

```bash
python main.py --doctor
bash run_linux.sh --portrait --kiosk
```

**Diperiksa**
- `--doctor` semua `[ OK ]`
- Antarmuka terbuka dalam waktu wajar (< 30 detik)
- Avatar 3D tampil (bila berat, lihat catatan performa di bawah)
- Alur suara penuh berfungsi
- Suhu CPU wajar saat menganggur

### Bila Pi terasa berat

| Gejala | Saran |
| --- | --- |
| Avatar 3D tersendat | Turunkan kualitas: set `dpr={[1, 1.5]}` di `Avatar3D.jsx` |
| Antarmuka lambat dimuat | Gunakan `--mode cli` bila layar tidak wajib |
| RAM penuh | Tutup peramban lain; gunakan Chromium kiosk yang disediakan peluncur |
| ASR lambat | `export SELA_ASR_THREAD=2` |

---

## 16. Pemeriksaan akhir sebelum dipasang

- [ ] `--doctor` bersih di perangkat target
- [ ] Alur suara penuh berfungsi (tanya → jawab → suara → lipsync)
- [ ] Bahasa Indonesia menyeluruh
- [ ] Tata letak benar di orientasi layar yang dipakai
- [ ] Pengaturan tersimpan dan bertahan setelah muat ulang
- [ ] Aplikasi berjalan otomatis saat boot (bila dipakai sebagai kios)
- [ ] Ada cara keluar/menghentikan aplikasi yang diketahui petugas
