# Riwayat Perubahan SELA AI

Semua perubahan penting pada SELA AI dicatat di berkas ini.

Format mengikuti [Keep a Changelog](https://keepachangelog.com/id/1.1.0/),
dan penomoran versi mengikuti [Semantic Versioning](https://semver.org/lang/id/).

Catatan rilis di GitHub diambil dari bagian versi yang sesuai di berkas ini
(lihat `.github/workflows/release.yml`).

---

## [1.0.9] - 2026-09-27

Rilis ini memperbaiki **dua penyebab aplikasi tidak bisa dibuka** — satu di
Linux, satu di Windows — yang keduanya membuat aplikasi mati tanpa pesan apa
pun. Selain itu, pengguna baru kini benar-benar melihat kode aktivasi di
peramban, suara kode aktivasi sepenuhnya Bahasa Indonesia, dan fitur kamera
mengikuti kemauan pengguna: bisa dilipat jadi ikon kecil, dan foto tidak lagi
langsung masuk ke percakapan.

### Diperbaiki

- **Linux: aplikasi tertutup sendiri saat start (wake word).** Berkas
  `models/en/keywords.txt` memuat baris rusak
  `▁HA I ▁HA I @Hai Hai`. Label kata kunci tidak boleh memuat spasi —
  sherpa-onnx memperlakukan kata setelah spasi sebagai token, tidak
  menemukannya, lalu **memanggil `exit()` dari dalam kode C++**. Proses Python
  mati seketika sehingga `try/except` tidak sempat menolong dan tidak ada
  jejaknya di log. Baris rusak itu dibuang dan berkas kini hanya memuat
  `▁SE LA @SELA`.
- **Baris kata kunci rusak tidak lagi bisa mematikan aplikasi.** Berkas kata
  kunci disaring lebih dulu di Python (`src/audio_processing/kata_kunci.py`)
  sebelum diserahkan ke sherpa-onnx. Baris tidak valid dibuang dengan
  peringatan yang jelas, berkas pengguna ditulis ulang supaya pulih sendiri,
  dan bila tidak ada satu pun baris yang sah, fitur wake word dimatikan
  dengan rapi sementara aplikasi tetap berjalan.
- **Salinan kata kunci milik pengguna kini ikut diperbarui.** Sebelumnya
  `get_user_keywords_path()` hanya menyalin berkas bawaan saat berkas pengguna
  belum ada, sehingga salinan lama yang rusak terus dipakai. Sekarang salinan
  itu diperiksa dan dibersihkan setiap kali model dimuat.
- **Windows: aplikasi tidak mau terbuka (tidak ada reaksi sama sekali).**
  Build lama hanya mengemas `_sherpa_onnx.pyd` tanpa pustaka pendampingnya —
  `onnxruntime.dll`, `sherpa-onnx-c-api.dll`, dan `sherpa-onnx-cxx-api.dll`
  tidak ikut terbundel (tidak ada hook PyInstaller untuk paket ini). Saat wake
  word dimuat, aplikasi menabrak memori (segfault) dan karena dibangun
  `--windowed` tanpa konsol, tidak ada satu pun pesan yang terlihat. Pustaka
  asli itu kini dikumpulkan lewat `pyinstaller_hooks/hook-sherpa_onnx.py`.
- **`pynput` dan `python-xlib` ikut didaftarkan** sebagai modul tersembunyi
  sehingga pintasan papan tik tidak lagi mati pada build Linux.
- **Pembuat kata kunci menolak menulis baris yang berbahaya.**
  `scripts/keyword_generator.py` dulu hanya memberi peringatan lalu tetap
  menulis baris dengan label berspasi — baris itulah yang mematikan aplikasi.
  Sekarang baris seperti itu ditolak.
- **Suara kode aktivasi tidak lagi jatuh ke Bahasa Mandarin.**
  `ActivationAnnouncer` bawaannya `zh-CN` dan masih punya cadangan ke
  rekaman Mandarin. Kini bawaannya mengikuti `SystemConstants.DEFAULT_LOCALE`
  (`id-ID`) dan cadangannya pun Indonesia.

### Ditambahkan

- **Halaman aktivasi di peramban.** Sebelumnya tahap aktivasi selalu memakai
  penangan CLI, padahal aplikasi hasil paket berjalan tanpa konsol — pengguna
  baru tidak pernah melihat kodenya dan aplikasi tampak menggantung. Mode
  `web` kini menyalakan server kecil sementara
  (`src/ui/web/activation.py`) yang menampilkan kode aktivasi besar-besar,
  langkah menghubungkan perangkat ke xiaozhi.me, dan status yang diperbarui
  otomatis; halaman itu menutup sendiri setelah perangkat aktif.
- **Kamera bisa dilipat jadi ikon kecil.** Tombol silang pada kartu kamera
  kini hanya menyembunyikan kartunya dan menyisakan ikon kamera kecil di
  sudut layar — sama seperti panel obrolan. Saklar induk di Pengaturan tetap
  satu-satunya cara mematikan kamera sepenuhnya.
- **SELA bisa "melihat" tanpa difoto.** Kartu kamera mengirim bingkai hidup
  setiap 5 detik ke mesin AI, jadi pertanyaan seperti "saya lagi ngapain?"
  atau "gender saya apa?" bisa dijawab dari kamera walau pengguna tidak
  menekan tombol foto.

### Diubah

- **Foto tidak lagi langsung masuk ke percakapan.** Menekan "Ambil Foto"
  menaruh foto sebagai lampiran di kotak teks, sehingga pengguna bisa
  mengetik pertanyaannya lebih dulu ("saya lagi ngapain?") dan foto itu ikut
  terkirim bersama pertanyaannya. Permintaan foto yang datang dari mesin AI
  sendiri tidak mengotori kotak teks.

---

## [1.0.8] - 2026-09-26

Rilis ini mengembalikan mesin AI ke bentuk asli py-xiaozhi (seluruh fitur
musik buatan SELA dihapus), lalu membangun ulang percakapan web agar terasa
seperti asisten sungguhan: satu gelembung per jawaban, visualizer suara,
efek mengetik, papan langkah alat, peta kampus, dan kartu kamera melayang.

### Ditambahkan

- **Visualizer audio di gelembung jawaban.** Selagi SELA berbicara, gelembung
  menampilkan batang suara yang bergerak mengikuti level audio nyata (bukan
  animasi palsu), sehingga pengguna tahu SELA sedang bersuara walau teksnya
  belum muncul.
- **Efek mengetik setelah suara selesai.** Teks jawaban muncul bertahap
  hanya setelah SELA selesai berbicara, dan melanjutkan dari posisi terakhir
  bila potongan teks berikutnya menyusul.
- **Avatar pengguna dan SELA di setiap gelembung** (`user.png`, `sela.png`).
- **Papan langkah alat.** Saat mesin AI memanggil alat data (kampus, cuaca,
  pencarian, kamera), antarmuka menampilkan langkah kerja singkat beranimasi
  sehingga pengguna melihat SELA benar-benar membuka data, bukan diam.
- **Baris tanya lanjut di bawah setiap jawaban.** Tiga tombol pertanyaan
  lanjutan yang mengikuti topik jawaban (kampus, cuaca, waktu, umum) dan
  tidak mengulang pilihan yang sudah pernah tampil.
- **Peta kampus di dalam gelembung.** Jawaban yang menyebut alamat kampus
  menampilkan peta OpenStreetMap (tanpa kunci API) beserta tombol "Buka
  Rute" dan "Lihat Peta".
- **Kartu kamera melayang.** Kartu yang bisa digeser-geser untuk merekam
  pengguna, bisa dinyalakan/dimatikan dari halaman Pengaturan. Permintaan
  seperti "tolong foto saya" membuat SELA mengambil gambar dari kamera
  peramban dan menampilkannya di gelembung jawaban.
- **Batas panjang kolom obrolan (24 karakter)** beserta penghitung sisa
  karakter. Server menolak teks panjang pada jalur `listen/detect`, jadi
  pertanyaan panjang diarahkan ke tombol mikrofon (jalur suara tidak
  dibatasi).
- **Uji otomatis baru.** 24 uji Node (`npm test`) untuk aturan percakapan dan
  perapi teks, serta 30 uji Python untuk batas teks, label alat, papan langkah
  alat, dan kotak surat kamera peramban.
- **Pemeriksa antarmuka `scripts/cek_percakapan_baru.py`** yang memeriksa
  perilaku percakapan di Chrome sungguhan (13 pemeriksaan).

### Diperbaiki

- **Jawaban terpecah menjadi banyak gelembung.** Mesin AI mengirim jawaban
  sepotong-sepotong (jalur suara dan jalur presenter), dan jeda antar potongan
  bisa puluhan detik karena kalimatnya dibacakan lebih dulu. Penggabungan
  tidak lagi memakai batas waktu, melainkan berhenti saat pengguna bicara
  lagi, sehingga satu jawaban tampil sebagai SATU gelembung.
- **Blok kalimat yang tercetak dua kali.** Bila mesin AI menggabungkan dua
  hasil alat data yang isinya mirip, blok kalimat yang sama muncul dua kali
  ("... Cirebon. ... Cirebon."). Blok ganda kini diruntuhkan saat pesan
  digabung, termasuk untuk jawaban beraksara Han.
- **Baris tanya lanjut tidak muncul.** Syarat tampilnya ikut menunggu
  visualizer berhenti, padahal visualizer bisa tetap tampil setelah teks
  selesai. Kini baris itu muncul begitu teks jawaban selesai ditampilkan.
- **Gulir otomatis melawan pengguna.** Gulir mengikuti teks yang sedang
  muncul, tetapi langsung berhenti bila pengguna menggeser ke atas, dan
  tombol "ke bawah" muncul untuk kembali mengikuti.
- **Avatar tidak ter-decode.** Avatar memakai `loading="lazy"` sehingga
  avatar pada gelembung lama tidak pernah dimuat.
- **Label alat bernama beralias titik** (mis. `self.application.launch`)
  selalu jatuh ke "Menjalankan launch" karena namanya dipotong di titik
  sebelum dicocokkan.

### Diubah

- **Halaman Pengaturan: bagian Musik dihapus** (platform musik dan kualitas
  audio), tersisa delapan bagian yang semuanya berfungsi.

### Dihapus

- **Seluruh fitur musik buatan SELA**: pemutar musik web, nada tunggu,
  pencarian YouTube, tool musik tambahan, dan setelan musik. Berkas mesin
  musik dikembalikan byte-identik ke py-xiaozhi.
- **Edge TTS** (`src/audio_processing/teks_ke_suara.py`) beserta event
  `UI_SEND_LONG_TEXT` dan `MUSIC_CONTROL_REQUEST`. Aplikasi kini sepenuhnya
  memakai arsitektur suara py-xiaozhi.

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
