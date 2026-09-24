#!/usr/bin/env bash
# ============================================================
#  Build paket macOS (.dmg) untuk SELA AI
# ------------------------------------------------------------
#  Menghasilkan:  installer/*.dmg
#
#  Prasyarat:
#     brew install python@3.12 node portaudio opus
#
#  Jalankan:  bash scripts/build_macos.sh
# ============================================================
set -euo pipefail
cd "$(dirname "$0")/.."

echo
echo "============================================================"
echo "  SELA AI - Build Paket macOS (.dmg)"
echo "============================================================"
echo

PY_BIN="${PYTHON:-python3}"

if ! command -v "$PY_BIN" >/dev/null 2>&1; then
  echo "[GAGAL] $PY_BIN tidak ditemukan. Pasang Python 3.12 (brew install python@3.12)."
  exit 1
fi
echo "[OK] Python: $($PY_BIN --version)"

if ! command -v npm >/dev/null 2>&1; then
  echo "[GAGAL] npm tidak ditemukan. Pasang Node.js (brew install node)."
  exit 1
fi

# Opus wajib ada agar suara berfungsi. SELA memakai salinan di libs/libopus
# bila tersedia, jadi langkah ini hanya peringatan.
if ! brew list opus >/dev/null 2>&1; then
  echo "[INFO] Opus Homebrew tidak terdeteksi; SELA akan memakai libs/libopus/mac."
fi

# --- Antarmuka web ------------------------------------------
echo "[..] Membangun antarmuka web..."
cd webui
[ -d node_modules ] || npm install --no-audit --no-fund
npm run build
cd ..
[ -f webui/dist/index.html ] || { echo "[GAGAL] webui/dist tidak terbentuk."; exit 1; }
echo "[OK] Antarmuka web siap."

# --- Lingkungan Python --------------------------------------
if [ ! -d .venv ]; then
  echo "[..] Membuat virtual environment..."
  "$PY_BIN" -m venv .venv
fi
echo "[..] Memasang dependensi..."
./.venv/bin/python -m pip install --upgrade pip >/dev/null
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python -m pip install pyinstaller unifypy
echo "[OK] Dependensi siap."

# --- Build --------------------------------------------------
echo "[..] Menjalankan unifypy (PyInstaller + hdiutil)..."
rm -f *.spec
./.venv/bin/python -m unifypy . --config build.json --app-version 1.0.0 --verbose --clean

echo
echo "============================================================"
echo "  SELESAI"
echo "============================================================"
if ls installer/*.dmg >/dev/null 2>&1; then
  ls -lh installer/*.dmg
else
  echo "[PERINGATAN] Tidak ada .dmg yang dihasilkan - periksa keluaran di atas."
fi
