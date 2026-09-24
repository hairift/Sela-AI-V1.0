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


def _open_pywebview(url: str, title: str, width: int, height: int, fullscreen: bool) -> bool:
    """Coba buka jendela native via pywebview (opsional)."""
    try:
        import webview  # type: ignore
    except Exception:
        return False

    try:
        webview.create_window(title, url, width=width, height=height, fullscreen=fullscreen)
        webview.start()
        return True
    except Exception as e:
        logger.warning(f"Peluncur: pywebview gagal dibuka: {e}")
        return False


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
        "pywebview" | "chromium" | "browser" | "none"
    """
    # Berguna untuk uji otomatis / server tanpa layar (headless).
    if os.environ.get("SELA_NO_WINDOW") == "1":
        logger.info(f"Peluncur: SELA_NO_WINDOW=1, jendela tidak dibuka. Buka manual: {url}")
        return "none"

    # 1. Jendela native (bila pywebview terpasang dan bukan mode kios).
    if not kiosk and _open_pywebview(url, title, width, height, False):
        return "pywebview"

    # 2. Chromium kiosk (default untuk kios layar sentuh / mode kios).
    if kiosk or os.environ.get("SELA_KIOSK") == "1":
        if _open_chromium_kiosk(url, width, height):
            return "chromium"

    # 3. Peramban bawaan sistem - selalu jadi jalan terakhir.
    if _buka_peramban_bawaan(url):
        return "browser"

    logger.warning(
        f"Peluncur: tidak bisa membuka jendela otomatis. Buka manual di peramban: {url}"
    )
    # Jangan biarkan pengguna menatap layar kosong.
    _beritahu_url_windows(url)
    return "none"
