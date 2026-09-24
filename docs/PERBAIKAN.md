# Akar Masalah & Perbaikan (Windows · Linux · macOS)

Dokumen ini mencatat **penyebab sebenarnya** dari dua masalah yang dilaporkan
— Windows tidak bisa membuka aplikasi dan Linux terbuka tetapi suara tidak
merespons — lalu menjelaskan perbaikan yang sudah diterapkan.

---

## Ringkasan

| # | Gejala | Akar masalah | Status |
| --- | --- | --- | --- |
| W1 | Windows: aplikasi tidak terbuka sama sekali | Mode bawaan lama `gui` wajib `PySide6 + qasync`; bila tidak ada → `sys.exit(1)` **tanpa dialog apa pun** | ✅ Diperbaiki |
| W2 | Windows: tidak ada pesan galat | Paket dibuat `windowed=True` (tanpa konsol) sehingga semua traceback hilang | ✅ Diperbaiki |
| W3 | Windows: keluar sendiri setelah beberapa detik | Kegagalan alur **aktivasi** mengembalikan kode 1 → proses berhenti senyap | ✅ Diperbaiki (galat kini terlihat + tercatat) |
| W4 | Semua OS: audio gagal → aplikasi langsung keluar | Plugin `audio` termasuk "plugin kritis"; kegagalan memicu `exit 1` | ✅ Diperbaiki (mode degradasi + pesan jelas) |
| L1 | Linux: terbuka tetapi suara tidak merespons | `libportaudio2` / `portaudio19-dev` belum terpasang → `sounddevice` tidak bisa membuka perangkat | ✅ Dikenali otomatis + panduan perbaikan |
| L2 | Linux: mikrofon tidak terdeteksi | Pengguna tidak ada di grup `audio`, atau PulseAudio/PipeWire tidak berjalan | ✅ Dikenali otomatis |
| L3 | Linux: Opus gagal dimuat | Arsitektur library tidak cocok (mis. `x64` di sistem `arm64`) | ✅ Dikenali otomatis |
| L4 | Linux/macOS: sulit tahu apa yang salah | Tidak ada alat diagnostik | ✅ Ditambah `--doctor` |
| M1 | macOS: belum ada dukungan | Belum ada konfigurasi bundle & DMG | ✅ Ditambah |
| A1 | **Suara kode aktivasi berbahasa Mandarin** | `side_effects.py` mengunci `locale="zh-CN"` | ✅ Diperbaiki → `id-ID` |
| A2 | Teks alur aktivasi berbahasa Mandarin | `cli/activation.py` belum diterjemahkan | ✅ Diperbaiki |
| A3 | Status antarmuka CLI/TUI berbahasa Mandarin | `display.py`, `manager.py`, `app.py`, `settings_data.py` | ✅ Diperbaiki |
| A4 | Aplikasi windowed: log gagal encode karakter non-ASCII | `StreamHandler(None)` → handler cadangan tanpa UTF-8 | ✅ Diperbaiki |

---

## Windows

### W1 — Mode bawaan memaksa PySide6

**Sebelumnya:** `main.py` memakai `--mode gui` sebagai bawaan. Mode itu
memerlukan `PySide6` + `qasync`. Bila keduanya tidak terpasang, program hanya
mencatat error ke log lalu `sys.exit(1)` — dan karena tidak ada konsol, pengguna
melihat "aplikasi tidak mau terbuka".

**Perbaikan:** mode bawaan kini **`web`**, yang **tidak membutuhkan PySide6**.
Antarmuka dibuka di peramban/jendela Chromium. Mode `gui` tetap tersedia bila
PySide6 dipasang (`pip install -e ".[gui]"`).

### W2 — Galat hilang karena tidak ada konsol

**Perbaikan:** fungsi baru `_report_fatal()` di `main.py`:

1. Menulis traceback lengkap ke
   `%LOCALAPPDATA%\sela-ai\logs\crash-<tanggal>.log`
2. Di Windows, menampilkan **kotak dialog** berisi jenis galat dan lokasi log
3. Di Linux/macOS, memastikan pesan muncul di `stderr`

Jadi tidak ada lagi kegagalan yang "senyap".

### W3 — Aktivasi gagal = keluar senyap

Alur aktivasi perangkat butuh koneksi ke layanan OTA. Bila gagal, program
memang harus berhenti — tetapi pengguna harus **tahu mengapa**.

**Perbaikan:** kegagalan kini tercatat dan dilaporkan lewat `_report_fatal()`,
dan `run_windows.bat` menampilkan kode keluar serta menyarankan
`python main.py --doctor`.

### W4 — Kegagalan audio mematikan aplikasi

**Perbaikan:** saat audio gagal tetapi `XIAOZHI_DEGRADED_AUDIO=1`, aplikasi
tetap berjalan dan menampilkan banner peringatan (`SYSTEM_NOTICE`) alih-alih
langsung keluar. Pengguna masih bisa memakai antarmuka dan melihat statusnya.

---

## Linux (termasuk Raspberry Pi)

### L1 / L2 — Perangkat audio tidak siap

Ini penyebab paling umum "suara tidak merespons". Periksa dengan:

```bash
python main.py --doctor
```

Bila muncul `[GAGAL] Perangkat audio`, pasang paket sistem:

```bash
sudo apt update
sudo apt install libportaudio2 portaudio19-dev libopus0
```

Pastikan pengguna punya akses mikrofon:

```bash
sudo usermod -aG audio $USER     # lalu keluar & masuk kembali
```

Dan layanan suara berjalan:

```bash
systemctl --user status pipewire   # atau: pulseaudio --check
```

`run_linux.sh` sekarang memperingatkan lebih awal bila `libportaudio` atau
`libopus` tidak terdeteksi.

### L3 — Arsitektur library Opus

SELA membawa Opus untuk semua kombinasi (`libs/libopus/<platform>/<arch>/`).
Bila library yang terpilih tidak cocok arsitektur, pemuatan gagal. `--doctor`
melaporkan jalur library yang benar-benar dipakai, sehingga ketidakcocokan
langsung terlihat:

```
[ OK ] Library Opus (wajib untuk suara)
        dimuat dari libs/libopus/linux/arm64/libopus.so
```

### Catatan khusus Raspberry Pi

- Bangun paket `.deb` **di Pi itu sendiri** agar arsitekturnya `arm64`.
- Mikrofon USB lebih andal daripada mikrofon bawaan HDMI.
- Untuk layar sentuh 7", jalankan `python main.py --portrait --kiosk`.

---

## macOS

Belum pernah dikonfigurasi sebelumnya. Sekarang tersedia:

- `bundle_identifier`, `minimum_system_version`, kategori aplikasi
- Deskripsi pemakaian **mikrofon**, pengenalan suara, dan kamera (wajib untuk
  aplikasi macOS — tanpa ini macOS akan menolak akses audio)
- Konfigurasi DMG (`volname`, ukuran jendela, ukuran ikon)
- Skrip build: `bash scripts/build_macos.sh`

Prasyarat: `brew install python@3.12 node portaudio opus`.

---

## Cara memverifikasi sendiri

```bash
# 1. Periksa lingkungan
python main.py --doctor

# 2. Jalankan antarmuka web
python main.py
#    Buka http://127.0.0.1:8765/

# 3. Uji antarmuka tanpa perangkat audio (hanya untuk memastikan tampil)
XIAOZHI_DISABLE_AUDIO=1 python main.py      # Windows: set XIAOZHI_DISABLE_AUDIO=1
```

---

## Batas verifikasi

Perbaikan di dokumen ini dibagi menjadi dua tingkat kepercayaan:

| Tingkat | Cakupan |
| --- | --- |
| **Terverifikasi di lingkungan pengembangan** | Antarmuka web dibangun & dirender, server + jembatan WebSocket berjalan, `--doctor` berjalan, sintaks seluruh modul Python valid |
| **Perlu diuji di perangkat Anda** | Perilaku audio nyata (mikrofon → jawaban), aktivasi akun, dan hasil paket `.exe` / `.deb` / `.dmg` pada Windows/Linux/Raspberry Pi/macOS |

Untuk tingkat kedua, jalankan `--doctor` lebih dulu di setiap perangkat —
laporannya akan langsung menunjukkan bagian yang belum siap.
