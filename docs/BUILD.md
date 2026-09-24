# Panduan Build (`.exe` · `.deb` · `.dmg`)

Build memakai **PyInstaller** (mengemas aplikasi) + **unifypy** (menghasilkan
installer tiap platform: Inno Setup / dpkg / hdiutil).

---

## Alur umum

Semua skrip build melakukan hal yang sama:

1. Membangun antarmuka web (`webui/` → `webui/dist/`)
2. Membuat virtual environment & memasang dependensi
3. Memasang `pyinstaller` + `unifypy`
4. Menjalankan `unifypy` dengan `build.json`

Hasilnya ada di folder **`installer/`**.

> **Aturan penting:** build harus dijalankan **di sistem operasi target**.
> Windows hanya bisa menghasilkan `.exe`, Linux `.deb`, macOS `.dmg`.

## Status verifikasi

| Tahap | Status |
| --- | --- |
| Antarmuka web (`npm run build`) | ✅ Terverifikasi |
| PyInstaller (paket aplikasi) | ✅ Terverifikasi di Windows — `dist/sela-ai/sela-ai.exe` berjalan, `--doctor` 11/11 |
| **Installer Windows (.exe)** | ✅ **Terverifikasi** — `installer/sela-ai-1.0.0-x86_64.exe` (122,6 MB) |
| Installer Linux (.deb) | ⏳ Belum dijalankan (butuh `dpkg-dev`, jalankan di Linux/Pi) |
| Installer macOS (.dmg) | ⏳ Belum dijalankan (butuh `hdiutil`, jalankan di macOS) |

---

## Windows → `.exe`

**Prasyarat**

| Perangkat | Sumber |
| --- | --- |
| Python 3.12 | python.org |
| Node.js 18+ | nodejs.org |
| Inno Setup 6 | jrsoftware.org/isdl.php |

**Pasang Inno Setup tanpa admin (opsional).** Installer Inno Setup mendukung
pemasangan per-pengguna, jadi tidak perlu hak administrator:

```bat
innosetup-6.7.3.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CURRENTUSER ^
  /DIR="%USERPROFILE%\SelaBuildTools\InnoSetup6"
```

Skrip `build_windows.bat` otomatis mencari `ISCC.exe` di lokasi ini, jadi tidak
perlu menambah apa pun ke `PATH`.

**Jalankan**

```bat
scripts\build_windows.bat
```

**Hasil:** `installer\sela-ai-1.0.0-x86_64.exe` (±123 MB)

> **Penting:** opsi `--inno-setup-path` milik unifypy harus menunjuk ke
> **berkas `ISCC.exe`**, bukan foldernya. Bila diarahkan ke folder, unifypy
> mencoba menjalankan folder itu sebagai program dan gagal dengan pesan
> menyesatkan `[WinError 5] Access is denied`.
>
> `ISCC.exe` (stub installer) adalah program **32-bit**. Itu normal untuk Inno
> Setup — installer tetap berjalan di Windows 64-bit dan memasang aplikasi
> 64-bit.

### Tentang installer yang dihasilkan

- Dipasang ke **Program Files** (`{autopf}`), jadi **meminta hak administrator**.
  Ini perilaku bawaan template unifypy dan tidak bisa diubah dari `build.json`.
- Membuat ikon desktop dan entri Start Menu.
- Sudah menyertakan uninstaller (muncul di *Apps & features*).

### Alternatif tanpa instalasi (portable)

Folder `dist\sela-ai\` bersifat **mandiri** — seluruh isi aplikasi ada di dalam
`_internal\`. Untuk kios yang tidak ingin memasang apa pun, cukup:

1. Salin folder `dist\sela-ai\` ke flashdisk / perangkat target.
2. Jalankan `sela-ai.exe` langsung dari sana.

Tidak perlu admin, tidak ada entri registry, dan menghapusnya cukup dengan
menghapus foldernya.

---

## Linux → `.deb`

**Prasyarat**

```bash
sudo apt install -y python3-venv python3-dev nodejs npm \
    libportaudio2 portaudio19-dev libopus0 libopus-dev libasound2-dev \
    dpkg-dev fakeroot patchelf
```

**Jalankan**

```bash
bash scripts/build_linux.sh
```

**Hasil:** `installer/sela-ai_1.0.0_amd64.deb`
(di Raspberry Pi: `..._arm64.deb`)

**Pasang**

```bash
sudo apt install ./installer/sela-ai_1.0.0_amd64.deb
```

> **Raspberry Pi:** bangun langsung di Pi. Paket yang dibangun di komputer x64
> tidak akan berjalan di Pi arm64.

---

## macOS → `.dmg`

**Prasyarat**

```bash
brew install python@3.12 node portaudio opus
```

**Jalankan**

```bash
bash scripts/build_macos.sh
```

**Hasil:** `installer/SELA AI-1.0.0.dmg`

Untuk menghasilkan dua arsitektur (Apple Silicon + Intel), jalankan sekali di
masing-masing mesin, atau gunakan alur CI di `.github/workflows/build.yml`.

---

## Konfigurasi build (`build.json`)

| Kunci | Nilai | Keterangan |
| --- | --- | --- |
| `name` | `sela-ai` | Nama paket (ASCII) |
| `display_name` | `SELA AI` | Nama tampilan |
| `pyinstaller.add_data` | `…`, `webui/dist:webui/dist` | **Wajib** — antarmuka web ikut dikemas |
| `platforms.macos.bundle_identifier` | `id.ac.ucic.sela-ai` | ID bundel macOS |
| `platforms.macos.*_usage_description` | … | Alasan akses mikrofon/kamera (wajib di macOS) |
| `platforms.windows.inno_setup` | … | Ikon desktop, Start Menu |
| `platforms.linux.deb` | … | Nama paket, kategori |

---

## Memperbarui versi

Ubah dua tempat agar konsisten:

1. `src/constants/system.py` → `APP_VERSION`
2. `build.json` → `version`

Lalu jalankan ulang skrip build dengan `--app-version` yang sesuai.

---

## Otomatisasi (GitHub Actions)

`.github/workflows/build.yml` sudah disiapkan untuk membangun kelima target
secara otomatis saat tag `v*.*.*` dibuat:

| Runner | Hasil |
| --- | --- |
| `macos-latest` (arm64) | `.dmg` arm64 |
| `macos-latest` (x64) | `.dmg` x64 |
| `windows-latest` | `.exe` |
| `ubuntu-24.04` | `.deb` x64 |
| `ubuntu-24.04-arm` | `.deb` arm64 |

```bash
git tag v1.0.0
git push --tags
```

---

## Pemecahan masalah build

| Gejala | Sebab & solusi |
| --- | --- |
| `webui/dist/index.html` tidak ada | Jalankan `cd webui && npm install && npm run build` |
| Antarmuka tampil "belum dibangun" | `webui/dist` tidak ikut dikemas — periksa `add_data` di `build.json` |
| Inno Setup tidak ditemukan (Windows) | Pasang Inno Setup 6, lalu tambahkan foldernya ke PATH |
| `dpkg-deb` tidak ditemukan | `sudo apt install dpkg-dev` |
| Build macOS gagal menandatangani | Normal untuk build lokal; pengguna dapat membuka via *klik kanan → Open* |
| `.deb` tidak jalan di Raspberry Pi | Paket dibangun untuk arsitektur yang salah — bangun ulang di Pi |
