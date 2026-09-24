@echo off
REM ============================================================
REM  Jalankan SELA AI dari sumber (Windows)
REM ------------------------------------------------------------
REM  Skrip ini menyiapkan semuanya sekali, lalu menjalankan
REM  aplikasi dalam mode antarmuka web (default).
REM
REM  Opsi tambahan yang bisa ditambahkan di belakang:
REM      --portrait      layar potret (kios)
REM      --kiosk         layar penuh tanpa bingkai
REM      --doctor        periksa lingkungan saja
REM      --mode cli      mode terminal
REM
REM  Contoh:  run_windows.bat --portrait --kiosk
REM ============================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

set PY=
where py >nul 2>nul && set PY=py -3
if not defined PY (
  where python >nul 2>nul && set PY=python
)
if not defined PY (
  echo [GAGAL] Python tidak ditemukan. Pasang Python 3.12 lalu coba lagi.
  pause
  exit /b 1
)

REM Siapkan antarmuka web bila belum dibangun.
if not exist "webui\dist\index.html" (
  where npm >nul 2>nul
  if errorlevel 1 (
    echo [GAGAL] Antarmuka web belum dibangun dan npm tidak tersedia.
    echo         Pasang Node.js, lalu jalankan:  cd webui ^&^& npm install ^&^& npm run build
    pause
    exit /b 1
  )
  echo [..] Membangun antarmuka web untuk pertama kali...
  pushd webui
  call npm install --no-audit --no-fund
  call npm run build
  popd
)

REM Siapkan lingkungan Python.
if not exist ".venv\Scripts\python.exe" (
  echo [..] Membuat virtual environment...
  %PY% -m venv .venv
  if errorlevel 1 ( echo [GAGAL] gagal membuat venv & pause & exit /b 1 )
  echo [..] Memasang dependensi (sekali saja, perlu beberapa menit)...
  .venv\Scripts\python.exe -m pip install -r requirements.txt
  if errorlevel 1 ( echo [GAGAL] pip install gagal & pause & exit /b 1 )
)

echo.
echo [OK] Menjalankan SELA AI...
echo      Antarmuka akan terbuka di peramban. Tutup jendela ini untuk keluar.
echo.
.venv\Scripts\python.exe main.py %*
if errorlevel 1 (
  echo.
  echo [INFO] Aplikasi berhenti dengan kode %errorlevel%.
  echo        Jalankan diagnostik:  .venv\Scripts\python.exe main.py --doctor
  pause
)
endlocal
