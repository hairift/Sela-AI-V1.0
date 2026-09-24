@echo off
REM ============================================================
REM  Build installer Windows (.exe) untuk SELA AI
REM ------------------------------------------------------------
REM  Menghasilkan:  installer\SELA AI Setup <versi>.exe
REM
REM  Prasyarat:
REM    1. Python 3.10-3.12 terpasang (py launcher tersedia)
REM    2. Node.js 18+ terpasang (untuk membangun antarmuka web)
REM    3. Inno Setup 6 terpasang (https://jrsoftware.org/isdl.php)
REM
REM  Jalankan dengan klik dua kali, atau dari terminal:
REM       scripts\build_windows.bat
REM ============================================================
setlocal enabledelayedexpansion
cd /d "%~dp0\.."

echo.
echo ============================================================
echo   SELA AI - Build Installer Windows
echo ============================================================
echo.

REM --- 1. Cek Python -----------------------------------------
set PY=
where py >nul 2>nul && set PY=py -3
if not defined PY (
  where python >nul 2>nul && set PY=python
)
if not defined PY (
  echo [GAGAL] Python tidak ditemukan di PATH.
  echo         Pasang Python 3.12 dari https://www.python.org/downloads/
  exit /b 1
)
echo [OK] Python: !PY!

REM --- 2. Bangun antarmuka web --------------------------------
where npm >nul 2>nul
if errorlevel 1 (
  echo [GAGAL] Node.js/npm tidak ditemukan di PATH.
  echo         Pasang Node.js LTS dari https://nodejs.org/
  exit /b 1
)
echo [..] Membangun antarmuka web...
pushd webui
if not exist node_modules (
  call npm install --no-audit --no-fund || (echo [GAGAL] npm install gagal & popd & exit /b 1)
)
call npm run build || (echo [GAGAL] npm run build gagal & popd & exit /b 1)
popd
if not exist "webui\dist\index.html" (
  echo [GAGAL] webui\dist\index.html tidak terbentuk.
  exit /b 1
)
echo [OK] Antarmuka web siap.

REM --- 3. Cari Inno Setup (ISCC.exe) ---------------------------
REM  unifypy butuh JALUR BERKAS ISCC.exe, bukan foldernya.
REM  Kalau salah, errornya menyesatkan: "[WinError 5] Access is denied".
set ISCC=
for %%P in (
  "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
  "%ProgramFiles%\Inno Setup 6\ISCC.exe"
  "%USERPROFILE%\SelaBuildTools\InnoSetup6\ISCC.exe"
  "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
) do (
  if not defined ISCC if exist %%P set ISCC=%%~fP
)
if not defined ISCC (
  where ISCC.exe >nul 2>nul && set ISCC=ISCC.exe
)
if not defined ISCC (
  echo [GAGAL] Inno Setup 6 tidak ditemukan.
  echo         Pasang dari https://jrsoftware.org/isdl.php
  echo         atau letakkan ISCC.exe di %%USERPROFILE%%\SelaBuildTools\InnoSetup6\
  exit /b 1
)
echo [OK] Inno Setup: !ISCC!

REM --- 4. Siapkan lingkungan Python ---------------------------
if not exist .venv (
  echo [..] Membuat virtual environment...
  %PY% -m venv .venv || (echo [GAGAL] gagal membuat venv & exit /b 1)
)
echo [..] Memasang dependensi (butuh waktu pada percobaan pertama)...
.venv\Scripts\python.exe -m pip install -r requirements.txt || (echo [GAGAL] pip install gagal & exit /b 1)
.venv\Scripts\python.exe -m pip install pyinstaller unifypy || (echo [GAGAL] pip install unifypy gagal & exit /b 1)
echo [OK] Dependensi siap.

REM --- 5. Bangun installer ------------------------------------
echo [..] Menjalankan unifypy (PyInstaller + Inno Setup)...
.venv\Scripts\python.exe -m unifypy . --config build.json --app-version 1.0.0 --inno-setup-path "!ISCC!" --verbose

echo.
echo ============================================================
echo   SELESAI
echo ============================================================
if exist installer (
  echo Hasil ada di folder: installer\
  dir /b installer\*.exe 2>nul
) else (
  echo [PERINGATAN] Folder installer tidak ditemukan - periksa keluaran di atas.
)
echo.
endlocal
