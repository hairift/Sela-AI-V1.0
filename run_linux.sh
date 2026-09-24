#!/usr/bin/env bash
# ============================================================
#  Jalankan SELA AI dari sumber (Linux / Raspberry Pi)
# ------------------------------------------------------------
#  Opsi:  --portrait   layar potret (kios 7")
#         --kiosk      layar penuh tanpa bingkai
#         --doctor     periksa lingkungan saja
#
#  Contoh:  bash run_linux.sh --portrait --kiosk
# ============================================================
set -euo pipefail
cd "$(dirname "$0")"

PY_BIN="${PYTHON:-python3}"

if ! command -v "$PY_BIN" >/dev/null 2>&1; then
  echo "[GAGAL] $PY_BIN tidak ditemukan. Pasang python3 + python3-venv."
  exit 1
fi

# Antarmuka web
if [ ! -f webui/dist/index.html ]; then
  if ! command -v npm >/dev/null 2>&1; then
    echo "[GAGAL] Antarmuka web belum dibangun dan npm tidak tersedia."
    echo "        Pasang Node.js, lalu: cd webui && npm install && npm run build"
    exit 1
  fi
  echo "[..] Membangun antarmuka web untuk pertama kali..."
  ( cd webui && { [ -d node_modules ] || npm install --no-audit --no-fund; } && npm run build )
fi

# Lingkungan Python
if [ ! -x .venv/bin/python ]; then
  echo "[..] Membuat virtual environment..."
  "$PY_BIN" -m venv .venv
  echo "[..] Memasang dependensi (sekali saja, perlu beberapa menit)..."
  ./.venv/bin/python -m pip install -r requirements.txt
fi

# Peringatan dini untuk masalah audio yang paling sering di Linux
if ! ldconfig -p 2>/dev/null | grep -q libportaudio; then
  echo "[INFO] libportaudio tidak terdeteksi. Bila suara tidak jalan:"
  echo "       sudo apt install libportaudio2 portaudio19-dev"
fi
if ! ldconfig -p 2>/dev/null | grep -q libopus; then
  echo "[INFO] libopus sistem tidak terdeteksi (SELA memakai libs/libopus/linux bila ada)."
fi

echo
echo "[OK] Menjalankan SELA AI..."
echo "     Antarmuka terbuka di peramban. Tekan Ctrl+C untuk keluar."
echo
exec ./.venv/bin/python main.py "$@"
