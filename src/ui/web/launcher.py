"""Pembuka jendela untuk antarmuka web SELA.

Tiga strategi, dipilih otomatis dari yang paling rapi ke paling portabel:

1. **pywebview** - jendela native tanpa bilah peramban (opsional, bila terpasang).
2. **Chromium/Chrome kiosk** - layar penuh tanpa bingkai; mode yang dipakai
   untuk kios Raspberry Pi dengan layar sentuh potret.
3. **Peramban bawaan sistem** - selalu tersedia, jadi aplikasi tidak pernah
   gagal hanya karena jendela tidak bisa dibuka.

Semua strategi dibuat *best-effort*: kegagalan membuka jendela tidak boleh
menghentikan mesin AI yang sudah berjalan.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import webbrowser
from typing import Optional

from src.logging import get_logger

logger = get_logger()

# Peramban berbasis Chromium yang umum ada di Linux/macOS/Windows.
_CHROMIUM_CANDIDATES = (
    "chromium",
    "chromium-browser",
    "google-chrome",
    "google-chrome-stable",
    "microsoft-edge",
    "brave-browser",
    "msedge",
)


def _find_chromium() -> Optional[str]:
    for name in _CHROMIUM_CANDIDATES:
        path = shutil.which(name)
        if path:
            return path
    # Windows: lokasi instalasi umum yang sering tidak ada di PATH.
    if sys.platform == "win32":
        candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c
    return None


def _webview2_tersedia() -> bool:
    """Periksa apakah runtime WebView2 ada (dibutuhkan pywebview di Windows).

    Tanpa runtime ini pywebview tetap membuka jendela tetapi isinya kosong,
    dan prosesnya menggantung — pengguna hanya melihat jendela putih. Lebih
    baik diperiksa lebih dulu lalu memakai jalur cadangan yang pasti tampil.
    """
    if sys.platform != "win32":
        # Linux/macOS memakai GTK/Qt/WebKit; biarkan pywebview mencoba sendiri.
        return True

    # 1. Kunci registry resmi runtime WebView2.
    try:
        import winreg  # type: ignore

        kunci = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"),
        ]
        for sarang, jalur in kunci:
            try:
                with winreg.OpenKey(sarang, jalur) as k:
                    versi = winreg.QueryValueEx(k, "pv")[0]
                    if versi and versi != "0.0.0.0":
                        return True
            except Exception:
                continue
    except Exception:
        pass

    # 2. Folder runtime tetap.
    for folder in (
        r"C:\Program Files (x86)\Microsoft\EdgeWebView\Application",
        r"C:\Program Files\Microsoft\EdgeWebView\Application",
    ):
        try:
            if os.path.isdir(folder) and any(
                os.path.isdir(os.path.join(folder, d)) for d in os.listdir(folder)
            ):
                return True
        except Exception:
            continue
    return False


def _open_pywebview(url: str, title: str, width: int, height: int, fullscreen: bool) -> bool:
    """Buka jendela native pywebview dengan pengawas kesiapan.

    pywebview dijalankan sebagai proses terpisah (``_jendela_native.py``) yang
    menulis berkas penanda begitu jendelanya benar-benar tampil. Bila runtime
    WebView2 rusak, pywebview hanya menggantung dengan jendela kosong dan
    ``webview.start()`` tidak pernah kembali — dahulu ini membuat pengguna
    menatap jendela putih tanpa jalan keluar. Sekarang proses induk menunggu
    paling lama 10 detik; bila penanda tidak muncul, proses dibunuh dan
    launcher memakai jalur cadangan.
    """
    try:
        import webview  # noqa: F401  (hanya memastikan terpasang)
    except Exception:
        logger.info("Peluncur: pywebview tidak terpasang, memakai jalur lain")
        return False

    if not _webview2_tersedia():
        logger.warning(
            "Peluncur: runtime WebView2 tidak ada, pywebview dilewati. "
            "Memakai jalur cadangan."
        )
        return False

    import tempfile

    penanda = os.path.join(tempfile.gettempdir(), f"sela-jendela-{os.getpid()}.txt")
    try:
        os.remove(penanda)
    except Exception:
        pass

    skrip = os.path.join(os.path.dirname(__file__), "_jendela_native.py")
    args = [
        sys.executable,
        skrip,
        url,
        title,
        penanda,
        str(width),
        str(height),
    ]

    try:
        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = 0x00000008  # DETACHED_PROCESS
        else:
            kwargs["start_new_session"] = True
        proses = subprocess.Popen(
            args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs
        )
    except Exception as e:
        logger.warning(f"Peluncur: gagal menjalankan jendela native: {e}")
        return False

    # Tunggu penanda siap/gagal paling lama 10 detik.
    batas = time.time() + 10
    while time.time() < batas:
        if os.path.exists(penanda):
            try:
                with open(penanda, encoding="utf-8") as f:
                    isi = f.read().strip()
            except Exception:
                isi = ""
            if isi == "siap":
                logger.info("Peluncur: jendela native pywebview siap")
                return True
            logger.warning(f"Peluncur: jendela native gagal ({isi or 'tanpa alasan'})")
            _hentikan(proses)
            return False
        if proses.poll() is not None:
            logger.warning("Peluncur: proses jendela native berhenti terlalu cepat")
            return False
        time.sleep(0.15)

    logger.warning(
        "Peluncur: jendela native tidak siap dalam 10 detik "
        "(kemungkinan WebView2 bermasalah). Memakai jalur cadangan."
    )
    _hentikan(proses)
    return False


def _hentikan(proses) -> None:
    """Hentikan proses jendela native dengan sopan."""
    try:
        proses.terminate()
        proses.wait(timeout=5)
    except Exception:
        try:
            proses.kill()
        except Exception:
            pass


def _open_chromium_kiosk(url: str, width: int, height: int) -> bool:
    """Buka Chromium dalam mode app/kiosk (layar penuh tanpa bingkai)."""
    exe = _find_chromium()
    if not exe:
        return False

    profile_dir = os.path.join(
        os.path.expanduser("~"), ".sela-ai", "browser-profile"
    )
    try:
        os.makedirs(profile_dir, exist_ok=True)
    except Exception:
        profile_dir = ""

    args = [
        exe,
        f"--app={url}",
        "--start-fullscreen",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-features=Translate,BackForwardCache",
        # Peramban harus boleh memakai mikrofon tanpa dialog (kios).
        "--use-fake-ui-for-media-stream",
        "--autoplay-policy=no-user-gesture-required",
    ]
    if profile_dir:
        args.append(f"--user-data-dir={profile_dir}")
    if width and height:
        args.append(f"--window-size={width},{height}")

    try:
        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = 0x00000008  # DETACHED_PROCESS
        else:
            kwargs["start_new_session"] = True
        subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs)
        logger.info(f"Peluncur: Chromium kiosk dibuka -> {url}")
        return True
    except Exception as e:
        logger.warning(f"Peluncur: Chromium kiosk gagal: {e}")
        return False


def _open_app_window(url: str, width: int, height: int) -> bool:
    """Buka jendela ala aplikasi desktop memakai Chrome/Edge mode ``--app``.

    Jendela ini **tanpa bilah alamat, tanpa tab, tanpa menu peramban**, punya
    entri tersendiri di taskbar, dan memakai favicon halaman (icon UCIC) sebagai
    icon jendela. Dipakai sebagai jalur cadangan yang andal ketika pywebview
    tidak bisa dipakai (mis. runtime WebView2 tidak terpasang), supaya
    pengguna tetap melihat jendela aplikasi, bukan tab peramban.
    """
    exe = _find_chromium()
    if not exe:
        return False

    profile_dir = os.path.join(os.path.expanduser("~"), ".sela-ai", "window-profile")
    try:
        os.makedirs(profile_dir, exist_ok=True)
    except Exception:
        profile_dir = ""

    args = [
        exe,
        f"--app={url}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-features=Translate,BackForwardCache",
        # Mikrofon harus boleh dipakai tanpa dialog izin.
        "--use-fake-ui-for-media-stream",
        "--autoplay-policy=no-user-gesture-required",
    ]
    if profile_dir:
        args.append(f"--user-data-dir={profile_dir}")
    if width and height:
        args.append(f"--window-size={width},{height}")

    try:
        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = 0x00000008  # DETACHED_PROCESS
        else:
            kwargs["start_new_session"] = True
        subprocess.Popen(
            args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs
        )
        logger.info(f"Peluncur: jendela aplikasi (tanpa bingkai peramban) -> {url}")
        return True
    except Exception as e:
        logger.warning(f"Peluncur: jendela aplikasi gagal: {e}")
        return False


def _buka_peramban_bawaan(url: str) -> bool:
    """Buka peramban bawaan sistem.

    Di Windows, ``os.startfile`` lebih andal daripada ``webbrowser.open``
    (yang kadang mengembalikan True padahal tidak ada jendela terbuka).
    """
    if sys.platform == "win32":
        try:
            os.startfile(url)  # type: ignore[attr-defined]
            logger.info(f"Peluncur: peramban bawaan dibuka -> {url}")
            return True
        except Exception as e:
            logger.warning(f"Peluncur: os.startfile gagal: {e}")
    try:
        if webbrowser.open(url, new=1):
            logger.info(f"Peluncur: peramban bawaan dibuka -> {url}")
            return True
    except Exception as e:
        logger.warning(f"Peluncur: webbrowser.open gagal: {e}")
    return False


def _beritahu_url_windows(url: str) -> None:
    """Tampilkan URL lewat kotak dialog Windows.

    Aplikasi terpaket berjalan tanpa konsol, jadi bila jendela peramban gagal
    dibuka pengguna tidak melihat apa pun dan mengira aplikasi "tidak bisa
    dibuka". Kotak dialog ini memastikan alamatnya selalu terlihat.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes

        teks = (
            "SELA AI sudah berjalan, tetapi jendela peramban tidak dapat "
            "dibuka otomatis.\n\n"
            "Silakan buka alamat berikut di peramban Anda:\n\n"
            f"{url}\n\n"
            "Selama jendela ini terbuka, SELA AI tetap aktif. "
            "Tekan OK lalu tutup jendela ini untuk menghentikan aplikasi."
        )
        ctypes.windll.user32.MessageBoxW(None, teks, "SELA AI", 0x40)
    except Exception as e:
        logger.warning(f"Peluncur: gagal menampilkan kotak dialog: {e}")


def open_ui(
    url: str,
    *,
    title: str = "SELA AI",
    width: int = 1280,
    height: int = 800,
    kiosk: bool = False,
) -> str:
    """Buka antarmuka web. Mengembalikan nama strategi yang berhasil dipakai.

    Returns:
        "pywebview" | "app" | "chromium" | "browser" | "none"
    """
    # Berguna untuk uji otomatis / server tanpa layar (headless).
    if os.environ.get("SELA_NO_WINDOW") == "1":
        logger.info(f"Peluncur: SELA_NO_WINDOW=1, jendela tidak dibuka. Buka manual: {url}")
        return "none"

    # Paksa jalur tertentu bila perlu (untuk diagnosis di perangkat pengguna):
    #   SELA_JENDELA=pywebview | app | kiosk | browser
    paksa = (os.environ.get("SELA_JENDELA") or "").strip().lower()

    # 1. Jendela native (bila pywebview terpasang, WebView2 ada, bukan kios).
    if paksa in ("", "pywebview") and not kiosk:
        if _open_pywebview(url, title, width, height, False):
            return "pywebview"

    # 2. Kios layar penuh (untuk Raspberry Pi / layar sentuh).
    if kiosk or paksa == "kiosk" or os.environ.get("SELA_KIOSK") == "1":
        if _open_chromium_kiosk(url, width, height):
            return "chromium"

    # 3. Jendela ala aplikasi desktop: tanpa bilah alamat, tanpa tab.
    #    Jalur ini yang paling andal di Windows karena hanya butuh Chrome/Edge.
    if paksa in ("", "app"):
        if _open_app_window(url, width, height):
            return "app"

    # 4. Peramban bawaan sistem - jalan terakhir.
    if _buka_peramban_bawaan(url):
        return "browser"

    logger.warning(
        f"Peluncur: tidak bisa membuka jendela otomatis. Buka manual di peramban: {url}"
    )
    # Jangan biarkan pengguna menatap layar kosong.
    _beritahu_url_windows(url)
    return "none"
