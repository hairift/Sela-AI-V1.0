#!/usr/bin/env bash
# ============================================================
#  Jalankan SELA AI dari sumber (macOS)
#  Klik dua kali berkas ini dari Finder, atau:
#      bash run_macos.command
# ============================================================
set -euo pipefail
cd "$(dirname "$0")"

PY_BIN="${PYTHON:-python3}"

if ! command -v "$PY_BIN" >/dev/null 2>&1; then
  echo "[GAGAL] python3 tidak ditemukan. Pasang:  brew install python@3.12"
  read -r -p "Tekan Enter untuk menutup..." _
  exit 1
fi

if [ ! -f webui/dist/index.html ]; then
  if ! command -v npm >/dev/null 2>&1; then
    echo "[GAGAL] Antarmuka web belum dibangun dan npm tidak tersedia."
    echo "        Pasang Node.js:  brew install node"
    read -r -p "Tekan Enter untuk menutup..." _
    exit 1
  fi
  echo "[..] Membangun antarmuka web untuk pertama kali..."
  ( cd webui && { [ -d node_modules ] || npm install --no-audit --no-fund; } && npm run build )
fi

if [ ! -x .venv/bin/python ]; then
  echo "[..] Membuat virtual environment..."
  "$PY_BIN" -m venv .venv
  echo "[..] Memasang dependensi (sekali saja)..."
  ./.venv/bin/python -m pip install -r requirements.txt
fi

echo
echo "[OK] Menjalankan SELA AI..."
echo "     Antarmuka terbuka di peramban. Tutup jendela ini untuk keluar."
echo
./.venv/bin/python main.py "$@"
