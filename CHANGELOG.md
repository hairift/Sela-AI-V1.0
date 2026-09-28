# Riwayat Perubahan SELA AI

Semua perubahan penting pada SELA AI dicatat di berkas ini.

Format mengikuti [Keep a Changelog](https://keepachangelog.com/id/1.1.0/),
dan penomoran versi mengikuti [Semantic Versioning](https://semver.org/lang/id/).

Catatan rilis di GitHub diambil dari bagian versi yang sesuai di berkas ini
(lihat `.github/workflows/release.yml`).

---

## [1.0.14] - 2026-09-28

**Subtitle dihapus total, dan naskah Role Introduction xiaozhi.me kini murni
untuk SELA - tidak lagi menyebut servo atau aturan robot.**

### Tampilan

- **Fitur subtitle dihapus sepenuhnya.** Subtitle yang diperkenalkan di 1.0.13
  (`webui/src/components/SubtitleAI.jsx`) dibuang sampai bersih - berkas
  komponen, pemasangan di `App.jsx`, kait ujinya, dan pemeriksaannya - supaya
  tidak ada sisa kode yang bisa bermasalah di kemudian hari. Visualizer audio
  yang mengikuti suara tetap ada dan tidak berubah.
- Isi gelembung obrolan kini selalu berupa teks jawaban (atau kartu yang
  menyertainya), persis seperti sebelum 1.0.13.

### Dokumentasi

- `docs/KONFIGURASI_XIAOZHI_ROLE.md` - kelompok **ATURAN ROBOT DAN SERVO**
  dihapus. Pemasangan SELA di kampus ini tidak memakai servo maupun aktuator
  robot, jadi aturan itu hanya membuang jatah token dan mengaburkan aturan yang
  benar-benar dipakai. Naskah sekarang terdiri dari 3 kelompok yang semuanya
  berlaku untuk SELA: sumber jawaban, transkrip suara, serta bahasa dan format.
  Aturan yang tersisa diperkuat supaya cukup berdiri sendiri - penolakan di luar
  topik, larangan mengarang, dan format jawaban dijelaskan lebih tegas.

### Perbaikan

- **Kait uji tidak lagi ikut terbit di bundel rilis.** Penjaga kait memakai
  `import.meta.env.PROD && import.meta.env.VITE_SELA_UJI !== '1'`. Di Vite 4,
  `PROD` memang dilipat menjadi literal, tetapi `VITE_SELA_UJI` diganti lewat
  fallback `import.meta.env` menjadi `{}.VITE_SELA_UJI` - bentuk yang tidak bisa
  dilipat, sehingga blok kaitnya TIDAK terbuang sebagai kode mati. Yang terbit
  di bundel adalah `typeof window>"u"||{}.VITE_SELA_UJI==="1"&&(window.__selaUjiLip=...)`.
  Kaitnya tidak pernah aktif (ekspresinya selalu false), jadi tidak berdampak
  saat dipakai - tetapi namanya tetap ikut terbit, sehingga jaminan "bundel
  rilis bersih dari kait uji" tidak benar-benar terpenuhi. Penjaga kini memakai
  `import.meta.env.MODE`, yang diganti langsung dengan literal string oleh Vite
  sehingga esbuild membuang blok kaitnya sepenuhnya. Bundel uji dibangun dengan
  `--mode development`.

- `scripts/cek_bundel_rilis.py` kini memeriksa **teks berkas bundel**, bukan
  hanya `typeof` di peramban. Celah itulah yang membuat cacat di atas lolos:
  `typeof` mengembalikan `undefined` (kait tidak aktif) padahal namanya masih
  ada di berkas. Pemeriksa juga menegaskan visualizer tetap terpasang dan
  penanda subtitle tidak ada.

### Pengujian

- `scripts/cek_visualizer_subtitle.py` menjadi
  `scripts/cek_visualizer_audio.py`; seluruh pemeriksaan subtitle dibuang dan
  pemeriksaan aksara Han tetap dipertahankan. Pemeriksa juga menunggu visualizer
  benar-benar muncul di DOM, bukan memakai jendela waktu tetap - jendela tetap
  pernah membuatnya gagal palsu pada mesin yang lambat.

---

## [1.0.13] - 2026-09-28

**Visualizer kini benar-benar bergerak mengikuti suara SELA dan bubble obrolan
merapikan sendiri daftar poin.**

### Tampilan

- **Visualizer audio akhirnya mengikuti suara.** Batang visualizer dulu
  memakai animasi CSS statis sehingga tampak "nge-fix" - bergerak sendiri
  tanpa hubungan dengan audio. Kini tinggi batang dihitung langsung dari data
  lipsync mesin AI (`lip.v` = volume RMS audio yang benar-benar diputar,
  `lip.viseme` = bentuk mulut). Warna batang ikut berubah mengikuti viseme.
- **Batang tidak lagi mati di sela kalimat.** Mesin AI mengayun status
  `speaking <-> idle` antar kalimat. Visualizer lama hanya hidup saat status
  `speaking`, jadi ia menghilang tepat ketika suara masih keluar. Patokannya
  kini sama dengan gerak mulut avatar: **ada suara bila energi > 0,02**.
- Batang mengempis mulus saat suara berhenti, tidak menyisakan tinggi
  terakhir, dan **tidak melewati wadahnya** - tidak ada lagi batang "lember"
  ke luar area.
### Percakapan

- **Penyusun jawaban dipisah jadi modul sendiri**
  (`webui/src/lib/formatJawaban.js`) supaya bisa diuji. Daftar di dalam satu
  baris kini dipecah dengan benar: `Fasilitas: - A - B - C` menjadi tiga butir,
  bukan satu butir berisi semuanya. Rentang angka (`4 - 5 juta`) dan desimal
  (`250.000`, `1.0.13`) tetap dibiarkan sebagai kalimat biasa.

### Dokumentasi

- `docs/KONFIGURASI_XIAOZHI_ROLE.md` - Role Introduction siap tempel untuk
  xiaozhi.me (14 aturan, ±660-700 token dari batas 2000), termasuk aturan
  baru agar SELA memilih sendiri format jawaban: poin-poin untuk fakta
  setara, bernomor untuk langkah berurutan.

### Pengujian

- `scripts/cek_visualizer_audio.py` - bukti dari DOM sungguhan lewat CDP
  bahwa batang bergerak mengikuti volume, membedakan besar-kecilnya, tidak
  melewati wadah, berubah warna mengikuti viseme, dan mengempis saat sepi.
  Bundel uji dibangun dengan penanda `VITE_SELA_UJI=1` supaya bundel rilis
  tetap bersih dari kait uji.
- `webui/tests/formatJawaban.test.js` - 15 uji untuk penyusun daftar.

---

## [1.0.12] - 2026-09-27

**Kode aktivasi kembali muncul untuk perangkat baru, pengguna tidak lagi
terkunci bila menolak aktivasi, dan teks jawaban tidak bisa lagi tersembunyi
di balik visualizer.**

### Aktivasi

- **Akar masalah "sudah terdaftar" ditemukan.** `config.json` menyimpan
  `SYSTEM_OPTIONS.DEVICE_ID` dari percobaan lama - MAC VirtualBox
  `0a:00:27:...` - dan mesin OTA mengirim nilai itu, bukan MAC fisik, ke
  server. Karena MAC virtual sama di semua komputer, server menjawab "sudah
  terdaftar" sehingga kode aktivasi tidak pernah terbit. `initialize_config()`
  hanya mengisi `DEVICE_ID` bila kosong, jadi nilai yang salah tidak pernah
  diperbaiki. Kini `DEVICE_ID` **diselaraskan dengan identitas fisik setiap
  start** (`src/activation/ota.py`). Ini penting karena `DEVICE_ID` juga
  dipakai untuk autentikasi WebSocket.
- Halaman aktivasi kini punya tombol **"Lewati dulu"** (`POST /lewati`).
  Sebelumnya pengguna yang menolak aktivasi **terkunci total** - hanya ada
  flag CLI `--skip-activation`.

### Percakapan

- **Pengawas visualizer.** Status `speaking` dari mesin AI bisa macet bila
  pemutaran audio tersendat (mis. `output underflow` saat berjalan tanpa
  jendela). Selama visualizer tampil, isi gelembung tidak dirender, sehingga
  teks jawaban dan kartu peta tersembunyi selamanya. Kini visualizer dilepas
  bila tak ada suara nyata selama `BATAS_SEPI_BICARA_MS` (10 detik,
  `webui/src/lib/percakapan.js`), dan penandanya dikunci sampai bicara
  benar-benar berhenti agar tidak berkedip.

### Pengujian

- Pemeriksa kamera kini memakai **klik sungguhan**
  (`Input.dispatchMouseEvent`). `element.click()` tidak memicu `pointerdown`,
  sehingga cacat "bilah geser menyerobot `setPointerCapture`" lolos sebagai
  lulus.
- `cek_percakapan_baru.py` menunggu SELA benar-benar berhenti bicara sebelum
  membaca jawaban, dan menandai pemeriksaan yang bergantung pada aktivasi
  server sebagai **LEWAT** - bukan GAGAL - bila perangkat belum diaktifkan.
- Uji baru untuk tombol lewati aktivasi dan pengawas visualizer.

---

## [1.0.11] - 2026-09-27

**Kata bangun "Hai Hai" akhirnya berfungsi, kamera bisa disembunyikan tanpa
mati, dan perangkat baru kembali punya identitas sendiri.**

### Kamera

- Tombol **tanda silang diganti tombol panah** (chevron) untuk melipat kartu
  kamera, sama seperti panel obrolan.
- **Melipat TIDAK lagi mematikan kamera.** Sebelumnya kartu dilepas dari React
  saat dilipat, sehingga `getUserMedia` berhenti dan SELA tidak bisa lagi
  menjawab "saya lagi ngapain?". Sekarang kartunya tetap terpasang dan hanya
  disembunyikan secara visual (`opacity-0`) - peramban berhenti menghasilkan
  bingkai begitu elemennya tidak digambar lagi.
- Pil kecil pengganti kartu kini **muncul persis di posisi terakhir kartunya**
  dan meniru gaya kartu "Buka Chat", lengkap dengan titik hijau penanda SELA
  masih melihat. Di v1.0.10 ikon pelipat dipaku di `top-24 left-6` (sudut kiri
  atas), sehingga setiap kali lipatan diterapkan ulang - dan itu terjadi tiap
  kali pengguna kembali dari halaman Pengaturan - ikon kamera melompat ke kiri
  layar. Itulah keluhan "tampilannya condong ke kiri".
- Posisi kartu dan pil **dijepit ke dalam jendela**, sehingga jendela yang
  diperkecil atau berpindah ke mode potret tidak meninggalkan kamera di luar
  layar.

### Kata bangun (wake word)

- **Akar masalah ditemukan.** Berkas kata kunci harus memakai penggalan token
  yang **sama persis** dengan tokenizer model. Model `models/en` memakai
  kosakata HURUF BESAR, sehingga baris `▁HA I ▁HA I @Hai Hai` membuat
  sherpa-onnx mencetak `Cannot find ID for token Hai` lalu memanggil
  `exit(-1)` - proses Python mati seketika dan `try/except` tidak bisa
  menahannya. Penggalan yang benar diverifikasi langsung dengan
  `sherpa_onnx.text2token`.
- Tiga kata bangun sekarang **sah dan aktif bersamaan**:
  `Sela`, `HaiHai`, dan `HelloSela`.
- Salinan kata kunci milik pengguna lama ikut diperbarui lewat penggabungan
  berversi (`VERSI_KATA_KUNCI_BAWAAN`). Sebelumnya salinan itu dibuat sekali
  lalu tidak pernah diperbarui, sehingga kata bangun baru tidak pernah sampai
  ke pengguna yang sudah memasang aplikasi.
- **Pengaturan menampilkan kata bangun yang benar-benar aktif**, dibaca dari
  berkas kata kunci mesin pengenal suara. Pemilih kata yang lama menulis
  `WAKE_WORD_OPTIONS.WAKE_WORD` - kunci yang tidak pernah dibaca oleh pengenal
  suara - sehingga memilih "Hai Hai" tidak mengubah apa pun dan terasa rusak.

### Sambungan AI

- **Sambung-ulang otomatis dinyalakan.** Mesin sambung-ulang sudah ada di
  `Protocol` sejak awal, tetapi `enable_auto_reconnect()` tidak pernah
  dipanggil di mana pun, sehingga sambungan yang putus karena jaringan goyang
  tidak pernah dipulihkan sendiri: SELA tetap "Tidak terhubung" sampai
  pengguna menekan tombol mikrofon. Sekarang delapan percobaan dengan mundur
  eksponensial, dan jatahnya pulih setiap sambungan berhasil.
- Antarmuka menampilkan **"Menyambung ulang… (n/m)"** alih-alih diam-diam
  "Terputus". Penutupan normal oleh server (sesi selesai) tetap tidak memicu
  sambung-ulang - itu bukan kerusakan.

### Identitas perangkat & aktivasi

- **Adaptor jaringan fisik didahulukan.** Sebelumnya MAC diambil dari adaptor
  pertama yang bukan loopback. Di komputer yang memasang VirtualBox, adaptor
  pertama justru adaptor virtual dengan MAC `0a:00:27:00:00:10` - nilai yang
  **sama di semua komputer** yang memasang perangkat lunak itu. Akibatnya
  perangkat baru dianggap "sudah terdaftar" oleh server, sehingga halaman kode
  aktivasi tidak pernah muncul, dan banyak pengguna berbagi satu identitas
  perangkat. `efuse.json` yang sudah ada tidak diubah, jadi pemasangan lama
  tidak dipaksa aktivasi ulang.
- Bagian **"Perangkat & Aktivasi"** di Pengaturan menampilkan nomor seri, ID
  perangkat, status aktivasi, tombol **Periksa Ulang**, dan tombol **Buka
  Konsol xiaozhi.me**. Bila server memang mengirim kode aktivasi, kodenya
  ditampilkan besar-besar beserta petunjuk pemakaiannya. Tautan hanya boleh
  menuju host yang dipakai aplikasi ini.
- Pesan status aktivasi **diterjemahkan ke Bahasa Indonesia**. Mesin aktivasi
  berasal dari py-xiaozhi dan mengirim pesan berbahasa Mandarin (`设备已激活`);
  berkas aslinya dipakai bersama jalur QML sehingga dibiarkan utuh, dan
  penerjemahannya dilakukan di perbatasan antarmuka web. Pesan asing yang belum
  dikenal pun tidak akan menampilkan aksara Han ke pengguna.

---

## [1.0.10] - 2026-09-27

**Aplikasi Windows akhirnya benar-benar bisa dibuka.**

Rilis 1.0.9 sudah memperbaiki crash wake word di Linux, tetapi **belum
menuntaskan Windows**. Penelusuran lanjutan menunjukkan akar masalahnya bukan
pada PyInstaller, melainkan pada `pyproject.toml`: dependensi
`sherpa-onnx-core` — paket yang justru **memasok** pustaka asli sherpa-onnx —
diberi penanda `sys_platform != 'win32'`, sehingga tidak pernah dipasang di
Windows. Penanda itu sudah ada sejak v1.0.0.

Wheel `sherpa-onnx` sendiri hanya berisi pembungkus Python. Isi
`sherpa_onnx/lib/` pada wheel Windows-nya cuma satu berkas:

| Wheel | Isi `sherpa_onnx/lib/` |
| --- | --- |
| `sherpa_onnx-1.13.8-cp310-cp310-win_amd64.whl` | hanya `_sherpa_onnx.cp310-win_amd64.pyd` |
| `sherpa_onnx_core-1.13.8-py3-none-win_amd64.whl` | `onnxruntime.dll`, `sherpa-onnx-c-api.dll`, `sherpa-onnx-cxx-api.dll` |

Tanpa ketiga DLL itu, pembuatan `KeywordSpotter` (wake word) menabrak memori →
segfault. Karena aplikasi dibangun `--windowed`, pengguna tidak melihat pesan
apa pun — aplikasinya hanya tampak "tidak mau terbuka". Inilah yang terjadi
pada SELA AI 1.0.8 yang terpasang di komputer pengguna: folder
`sherpa_onnx/lib/` hanya berisi berkas `.pyd`.

Di Linux dan macOS masalah ini tidak terasa karena penanda platform tidak
berlaku di sana, sehingga `sherpa-onnx-core` terpasang seperti biasa.

### Diperbaiki

- **Windows: dependensi `sherpa-onnx-core` kini dipasang di semua platform.**
  Penanda `sys_platform != 'win32'` dihapus. Dengan paket itu terpasang,
  `sherpa_onnx/lib/` berisi ketiga DLL yang dibutuhkan dan hook PyInstaller
  dapat mengemasnya.
- **Verifikasi ulang paket Linux.** Berkas `.deb` 1.0.9 diperiksa isinya untuk
  memastikan perbaikan wake word benar-benar ikut ke paket rilis, bukan hanya
  ada di kode sumber. Hasilnya: `models/en/keywords.txt` berisi tepat
  `▁SE LA @SELA`, dan `sherpa_onnx/lib/` memuat ketiga pustaka pendamping.

### Ditambahkan

- **Pemeriksaan di CI: build digagalkan bila pustaka pendamping tidak
  terbundel.** `.github/workflows/build.yml` kini mencari `*onnxruntime.*`,
  `*sherpa-onnx-c-api.*`, dan `*sherpa-onnx-cxx-api.*` di dalam `dist/` tepat
  setelah tahap build. Sebelumnya tidak ada pemeriksaan apa pun, sehingga paket
  Windows yang rusak bisa lolos ke halaman rilis tanpa satu pun peringatan.
- **`tests/test_dependensi_sherpa.py`** mengunci agar penanda platform tidak
  pernah kembali dipasang pada `sherpa-onnx-core`, dan memastikan
  `pyinstaller_hooks/` serta `build.json` tetap saling cocok.
- **`scripts/cek_paritas_kiblat.py`** membandingkan daftar berkas kiblat
  `py-xiaozhi-main` dengan SELA (`src/`, `models/`, `assets/sounds/`,
  `scripts/`) dan gagal bila ada yang hilang. Ini penjaga otomatis untuk aturan
  tetap proyek: modifikasi SELA harus aditif.

### Diubah

- `.gitignore` juga mengabaikan folder sementara hasil tukar build
  (`dist_siap/`, `build_siap/`, `dist_baru/`, `build_baru/`) dan berkas bantu
  verifikasi.

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
