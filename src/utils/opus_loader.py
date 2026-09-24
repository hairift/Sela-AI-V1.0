"""Pemuat library Opus - memastikan opuslib menemukan pustaka dinamis opus."""

from __future__ import annotations

import ctypes
import ctypes.util
import os
import sys
from pathlib import Path

from src.logging import get_logger
from src.utils.resource_finder import get_lib_path

logger = get_logger()

_opus_loaded = False


def _find_system_opus() -> str | None:
    """Cari pustaka opus yang terpasang di sistem."""
    if sys.platform == "win32":
        return None

    if sys.platform == "darwin":
        candidates = [
            "/opt/homebrew/lib/libopus.dylib",
            "/usr/local/lib/libopus.dylib",
        ]
    else:
        candidates = [
            "/usr/lib/libopus.so.0",
            "/usr/lib/x86_64-linux-gnu/libopus.so.0",
            "/usr/lib/aarch64-linux-gnu/libopus.so.0",
            "/usr/local/lib/libopus.so",
        ]

    for path in candidates:
        if Path(path).exists():
            return path

    return ctypes.util.find_library("opus")


def _try_load(path: str | Path) -> bool:
    """Coba muat pustaka dinamis."""
    try:
        ctypes.CDLL(str(path))
        return True
    except OSError:
        return False


def _patch_find_library(lib_path: str):
    """Tambal ctypes.util.find_library agar opuslib menemukan opus."""
    original = ctypes.util.find_library

    def patched(name: str) -> str | None:
        if name == "opus":
            return lib_path
        return original(name)

    ctypes.util.find_library = patched


def setup_opus() -> bool:
    """Siapkan pustaka opus untuk dipakai opuslib.

    Urutan pencarian:
    1. opus bawaan proyek (libs/libopus/) - versi terkendali, deployment konsisten
    2. opus sistem (brew/apt) - cadangan

    Returns:
        True bila berhasil dimuat
    """
    global _opus_loaded
    if _opus_loaded:
        return True

    # 1. Utamakan opus bawaan
    bundled_path = get_lib_path("libopus")
    if bundled_path and bundled_path.exists():
        if sys.platform == "win32":
            lib_dir = str(bundled_path.parent)
            if hasattr(os, "add_dll_directory"):
                os.add_dll_directory(lib_dir)
            os.environ["PATH"] = lib_dir + os.pathsep + os.environ.get("PATH", "")

        if _try_load(bundled_path):
            logger.debug(f"Memakai opus bawaan: {bundled_path}")
            _patch_find_library(str(bundled_path))
            _opus_loaded = True
            return True

    # 2. Cadangan: opus sistem
    system_path = _find_system_opus()
    if system_path and _try_load(system_path):
        logger.debug(f"Memakai opus sistem: {system_path}")
        _patch_find_library(system_path)
        _opus_loaded = True
        return True

    logger.warning(
        "Pustaka opus tidak ditemukan; audio mungkin tidak berfungsi. "
        "Linux: sudo apt install libopus0  |  macOS: brew install opus"
    )
    return False
