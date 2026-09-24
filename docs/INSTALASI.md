# Panduan Instalasi

Pilih bagian sesuai sistem operasi Anda.

---

## Windows 10/11

### Cara cepat (dari sumber)

1. Pasang **Python 3.12** — <https://www.python.org/downloads/>
   Centang **"Add python.exe to PATH"** saat memasang.
2. Pasang **Node.js LTS** — <https://nodejs.org/>
3. Buka folder proyek, klik dua kali **`run_windows.bat`**.

Skrip akan membangun antarmuka web, membuat virtual environment, memasang
dependensi, lalu membuka aplikasi di peramban.

### Cara pakai installer

Bila sudah punya `SELA AI Setup 1.0.0.exe`:

1. Klik dua kali installer, ikuti langkahnya.
2. Jalankan **SELA AI** dari Start Menu / ikon desktop.

> **Catatan:** instalasi dari sumber **tidak** memerlukan PySide6. PySide6 hanya
> dibutuhkan bila Anda ingin memakai antarmuka QML lama (`--mode gui`).

### Bila aplikasi tidak terbuka

```bat
run_windows.bat
```

Skrip ini menampilkan pesan galat di jendela terminal. Untuk pemeriksaan
menyeluruh:

```bat
.venv\Scripts\python.exe main.py --doctor
```

Log galat tersimpan di `%LOCALAPPDATA%\sela-ai\logs\`.

---

## Linux (Debian / Ubuntu)

```bash
sudo apt update
sudo apt install -y python3-venv python3-dev nodejs npm \
    libportaudio2 portaudio19-dev libopus0 libopus-dev libasound2-dev

bash run_linux.sh
```

### Pasang dari paket `.deb`

```bash
sudo apt install ./installer/sela-ai_1.0.0_amd64.deb
sela-ai
```

---

## Raspberry Pi 4B (RAM 2 GB) — target utama

Sistem: **Raspberry Pi OS 64-bit (Bookworm)**.

### 1. Paket sistem

```bash
sudo apt update
sudo apt install -y python3-venv python3-dev nodejs npm \
    libportaudio2 portaudio19-dev libopus0 libopus-dev libasound2-dev \
    chromium-browser
```

> **Penting:** gunakan Raspberry Pi OS **64-bit**. Versi 32-bit tidak didukung
> oleh beberapa paket Python yang dipakai mesin AI.

### 2. Mikrofon

Mikrofon USB lebih andal daripada mikrofon bawaan. Periksa:

```bash
arecord -l          # daftar perangkat input
```

Pastikan pengguna punya akses:

```bash
sudo usermod -aG audio $USER
# lalu keluar dan masuk kembali
```

### 3. Jalankan sebagai kios potret

```bash
bash run_linux.sh --portrait --kiosk
```

`--portrait` memakai tata letak layar potret (avatar penuh + panel bawah),
`--kiosk` membuka Chromium layar penuh tanpa bingkai.

### 4. Jalankan otomatis saat boot (opsional)

Buat berkas `/etc/systemd/system/sela-ai.service`:

```ini
[Unit]
Description=SELA AI - Asisten Kampus
After=graphical.target network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/Sela-AI-V1.0
Environment=DISPLAY=:0
Environment=SELA_PORTRAIT=1
Environment=SELA_KIOSK=1
ExecStart=/home/pi/Sela-AI-V1.0/.venv/bin/python main.py
Restart=on-failure

[Install]
WantedBy=graphical.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now sela-ai
```

### 5. Hemat sumber daya (opsional)

Pada RAM 2 GB, membatasi antarmuka membantu:

```bash
export SELA_WEBUI_PORT=8765
export SELA_ASR_THREAD=2
```

Gunakan `--mode cli` bila layar tidak diperlukan (mis. dipasang sebagai kotak
suara tanpa tampilan).

---

## macOS

```bash
brew install python@3.12 node portaudio opus
bash run_macos.command
```

Pemasangan dari `.dmg`: buka DMG, seret **SELA AI** ke folder Applications.
Saat pertama dijalankan, macOS akan meminta izin **mikrofon** — setujui agar
fitur suara berfungsi.

---

## Setelah terpasang: periksa

```bash
python main.py --doctor
```

Semua item harus `[ OK ]`. Bila ada `[GAGAL]`, pesannya sudah memuat langkah
perbaikan. Lihat juga [`PERBAIKAN.md`](PERBAIKAN.md).
