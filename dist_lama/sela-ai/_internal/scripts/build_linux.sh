#!/usr/bin/env bash
# ============================================================
#  Build paket Linux (.deb) untuk SELA AI
# ------------------------------------------------------------
#  Menghasilkan:  installer/*.deb
#
#  Prasyarat (Debian/Ubuntu/Raspberry Pi OS):
#     sudo apt install python3-venv python3-dev nodejs npm \
#         libportaudio2 portaudio19-dev libopus0 libopus-dev \
#         libasound2-dev dpkg-dev fakeroot patchelf
#
#  Jalankan:  bash scripts/build_linux.sh
# ============================================================
set -euo pipefail
cd "$(dirname "$0")/.."

echo
echo "============================================================"
echo "  SELA AI - Build Paket Linux (.deb)"
echo "============================================================"
echo

PY_BIN="${PYTHON:-python3}"

# --- 1. Cek prasyarat ---------------------------------------
if ! command -v "$PY_BIN" >/dev/null 2>&1; then
  echo "[GAGAL] $PY_BIN tidak ditemukan. Pasang python3 + python3-venv."
  exit 1
fi
echo "[OK] Python: $($PY_BIN --version)"

if ! command -v npm >/dev/null 2>&1; then
  echo "[GAGAL] npm tidak ditemukan. Pasang Node.js (sudo apt install nodejs npm)."
  exit 1
fi

if ! command -v dpkg-deb >/dev/null 2>&1; then
  echo "[GAGAL] dpkg-deb tidak ditemukan (sudo apt install dpkg-dev)."
  exit 1
fi

# --- 2. Bangun antarmuka web --------------------------------
echo "[..] Membangun antarmuka web..."
cd webui
[ -d node_modules ] || npm install --no-audit --no-fund
npm run build
cd ..
[ -f webui/dist/index.html ] || { echo "[GAGAL] webui/dist tidak terbentuk."; exit 1; }
echo "[OK] Antarmuka web siap."

# --- 3. Lingkungan Python -----------------------------------
if [ ! -d .venv ]; then
  echo "[..] Membuat virtual environment..."
  "$PY_BIN" -m venv .venv
fi
echo "[..] Memasang dependensi..."
./.venv/bin/python -m pip install --upgrade pip >/dev/null
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python -m pip install pyinstaller unifypy
echo "[OK] Dependensi siap."

# --- 4. Build ----------------------------------------------
echo "[..] Menjalankan unifypy (PyInstaller + dpkg)..."
rm -f *.spec
./.venv/bin/python -m unifypy . --config build.json --app-version 1.0.0 --verbose --clean

echo
echo "============================================================"
echo "  SELESAI"
echo "============================================================"
if ls installer/*.deb >/dev/null 2>&1; then
  ls -lh installer/*.deb
  echo
  echo "Pasang dengan:  sudo apt install ./installer/<nama>.deb"
else
  echo "[PERINGATAN] Tidak ada .deb yang dihasilkan - periksa keluaran di atas."
fi
