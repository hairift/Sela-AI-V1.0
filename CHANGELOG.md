# Riwayat Perubahan SELA AI

Semua perubahan penting pada SELA AI dicatat di berkas ini.

Format mengikuti [Keep a Changelog](https://keepachangelog.com/id/1.1.0/),
dan penomoran versi mengikuti [Semantic Versioning](https://semver.org/lang/id/).

Catatan rilis di GitHub diambil dari bagian versi yang sesuai di berkas ini
(lihat `.github/workflows/release.yml`).

---

## [1.0.7] - 2026-09-25

Rilis ini melengkapi halaman pengaturan agar setara dengan versi QML
py-xiaozhi, memperbaiki beberapa bug yang membuat fitur tidak berjalan,
dan mengganti data tiruan dengan data sungguhan.

### Ditambahkan

- **Nada tunggu saat mencari musik.** Selagi SELA mencari lagu, aplikasi
  memutar nada lembut singkat sehingga pengguna tahu aplikasi sedang bekerja
  dan tidak terasa menggantung.
- **Tool cuaca sungguhan.** Tool cuaca kini mengambil data nyata dari
  Open-Meteo (prakiraan dan cuaca saat ini) beserta pemetaan kode cuaca WMO
  ke Bahasa Indonesia. Sebelumnya tool ini masih data tiruan.
- **Pengaturan: bagian Kamera.** Memilih perangkat kamera, memilih mesin
  kamera (backend OpenCV), dan tombol **Uji Kamera** yang benar-benar
  membuka kamera dan mengambil satu bingkai.
- **Pengaturan: bagian Pintasan Papan Tik.** Menyalakan/mematikan pintasan
  beserta daftar tombolnya, dengan keterangan Bahasa Indonesia.
- **Pengaturan: bagian Tool MCP.** Sakelar aktif/nonaktif untuk setiap tool
  MCP (dikelompokkan per kategori, dilengkapi kotak pencarian). Tool yang
  dimatikan tidak lagi ditawarkan ke mesin AI.
- **Skrip pemeriksa.** `cek_impor_komponen.py` (mendeteksi kode mati),
  `cek_animasi_thinking.py`, `cek_pengaturan.py`, dan `cek_pemutar_musik.py`
  untuk memverifikasi antarmuka memakai Chrome sungguhan.
- **Uji otomatis baru.** 45 uji tambahan untuk nada tunggu, cuaca nyata,
  kelengkapan pengaturan, jalur suara panjang, relevansi musik, dan kode
  keluar `--doctor`.

### Diperbaiki

- **Animasi "Thinking" tidak pernah tampil.** Saat pengguna selesai
  berbicara, mesin AI mengembalikan state ke `listening` selagi memproses
  jawaban. Kondisi lama mengecualikan state `listening`, sehingga animasi
  berpikir tidak pernah berjalan pada momen yang paling penting. Kini
  animasi berpikir berjalan sebagaimana mestinya.
- **Halaman putih kosong pada panel percakapan.** Komponen `PemutarMusik`
  dipakai di JSX tetapi tidak pernah diimpor, sehingga React berhenti
  merender (galat `ReferenceError`). Sama seperti penyebab halaman putih
  pada rilis 1.0.3 dan 1.0.4, dan kini ikut dicegah oleh pemeriksa kode mati.
- **Pencarian musik memilih kompilasi remix.** Pencarian Kuwo (jalur
  pertama) selalu mengambil hasil paling atas, sehingga permintaan
  "putar lagu Sheila on 7" bisa memutar kompilasi remix yang hanya
  menyebut nama penyanyinya di judul. Kini seluruh kandidat dinilai dan
  yang paling relevan yang dipilih — terverifikasi memilih
  "Sederhana - Sheila On 7", bukan kompilasi remix.
- **`--doctor` selalu keluar dengan kode 1.** Blok `finally:
  sys.exit(exit_code)` di `main.py` menimpa kode keluar hasil pemeriksaan,
  sehingga pemeriksaan yang LOLOS pun terlihat gagal bagi skrip atau CI.
  Penanganan `--doctor` dipindahkan ke luar blok tersebut.
- **Langkah lint CI tidak pernah memeriksa berkas tampilan.** Perintah
  `eslint src/` pada ESLint 8 hanya memeriksa berkas `.js` dan MELEWATI
  seluruh berkas `.jsx` — padahal justru di sanalah galat halaman putih
  berada. Kini memakai `--ext .js,.jsx` dan seluruh berkas tampilan bersih.
- **Teks miring tidak dirender.** Gelembung jawaban kini mengenali penanda
  miring (`*teks*`) di samping tebal, daftar, dan kode QR.
- **Pencarian musik YouTube lebih relevan.** Kandidat diambil lebih banyak
  lalu diberi skor, sehingga kompilasi remix dan hasil yang tidak
  berhubungan tidak lagi terpilih.
- **Kebocoran aksara Mandarin.** Nama kamera ("摄像头 0") dan pesan galat
  internal ("ConfigManager 未初始化") tidak lagi tampil ke pengguna.
- **Deskripsi pintasan papan tik** kini sepenuhnya Bahasa Indonesia.
- **Jawaban panjang lewat suara** memakai instruksi Bahasa Indonesia agar
  jawaban konsisten berbahasa Indonesia.

### Diubah

- **Tool cuaca bawaan tidak lagi dilewati.** Karena tool tiruan sudah
  diganti tool sungguhan dan namanya tidak lagi bentrok dengan tool server
  AI, sesi tidak lagi ditolak akibat "Duplicate tool names".

### Dihapus

- Komponen mati `TeksKaya.jsx` dan `LiveCaption.jsx` (tidak dipakai di mana
  pun; fungsinya sudah ditangani `ChatBubble.jsx`).

---

## [1.0.6] - 2026-09-25

### Diperbaiki

- Musik Indonesia bisa diputar lewat cadangan YouTube ketika platform
  utama tidak menemukan lagunya.

---

## [1.0.5] - 2026-09-24

### Diperbaiki

- Urutan langkah lint pada CI diperbaiki (ESLint dijalankan setelah
  `npm install`).
- Batas panjang pesan, tombol cepat, kunci admin, dan log waktu nyata.
- Menambahkan uji mikrofon di halaman pengaturan untuk membantu masalah
  suara di Linux.
- Dokumentasi tangkapan layar kunci admin.

---

## [1.0.2] - 2026-09-24

### Diubah

- Icon UCIC dipakai di installer, dan lisensi tampil saat pemasangan.

---

## [1.0.1] - 2026-09-24

### Diperbaiki

- Build macOS Intel: membatasi `cryptography < 45` karena versi 45+ tidak
  menyediakan wheel untuk macOS Intel.

---

## [1.0.0] - 2026-09-24

Rilis pertama.

### Ditambahkan

- **SELA AI** — asisten kampus UCIC berbasis suara, dibangun di atas mesin
  py-xiaozhi.
- Antarmuka web bergaya kios (potret dan desktop) berbahasa Indonesia,
  disajikan server lokal pada `127.0.0.1:8765`.
- Avatar 3D dengan animasi dan lipsync yang dihitung dari keluaran audio
  nyata.
- Kata bangun (wake word) "SELA".
- Tool pengetahuan kampus, pencarian web, berita, musik, cuaca, kamera,
  tangkapan layar, volume, dan peluncur aplikasi.
- Halaman pengaturan dengan kunci admin.
- Paket instalasi Windows (.exe), Linux (.deb), dan macOS (.dmg).
