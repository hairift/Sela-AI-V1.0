"""Bingkai kamera dari peramban untuk tool kamera py-xiaozhi.

Latar belakang
--------------
Tool ``take_photo`` milik py-xiaozhi membuka kamera lewat OpenCV/picamera2 di
sisi Python. Pada kios SELA, kamera yang paling mudah dipakai adalah **kamera
peramban** (``getUserMedia``) karena pengguna sudah melihat pratinjaunya dan
tidak ada perangkat yang direbut dua aplikasi sekaligus.

Modul ini menjadi kotak surat satu arah:

    peramban --(WebSocket)--> SelaBridge --simpan--> slot bingkai
                                                          |
                                   tool take_photo <------+

``base_camera.capture_frame`` mengambil bingkai peramban bila ada dan masih
segar; bila tidak ada, jalur kamera asli py-xiaozhi tetap dipakai apa adanya.
Dengan begitu arsitektur kiblat tidak berubah, hanya mendapat sumber gambar
tambahan yang bisa dimatikan kapan saja.
"""

from __future__ import annotations

import base64
import binascii
import os
import threading
import time

from src.logging import get_logger

logger = get_logger()

# Bingkai dianggap masih mewakili keadaan sekarang selama ini. Setelah lewat,
# jalur kamera asli dipakai lagi supaya SELA tidak "melihat" gambar basi.
MAKS_UMUR_BINGKAI_S = 12.0

# Batas ukuran bingkai yang diterima (byte JPEG). Lebih besar dari ini ditolak
# agar tidak membebani Raspberry Pi 2 GB.
MAKS_UKURAN_BINGKAI = 4 * 1024 * 1024

# Nama berkas pratinjau terakhir; berguna saat memeriksa manual.
NAMA_BERKAS_PRATINJAU = "bingkai_peramban.jpg"

_lock = threading.Lock()
_bingkai: bytes | None = None
_bingkai_pada: float = 0.0
_aktif = True


def _jalur_pratinjau() -> str:
    """Lokasi berkas pratinjau di dalam folder cache aplikasi."""
    try:
        from src.utils.resource_finder import get_app_root

        dasar = get_app_root() / "cache"
    except Exception:  # pragma: no cover - sangat jarang
        dasar = None
    if dasar is None:
        import tempfile

        return os.path.join(tempfile.gettempdir(), NAMA_BERKAS_PRATINJAU)
    try:
        dasar.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return str(dasar / NAMA_BERKAS_PRATINJAU)


def set_aktif(aktif: bool) -> None:
    """Nyalakan/matikan pemakaian bingkai peramban (dari pengaturan)."""
    global _aktif
    with _lock:
        _aktif = bool(aktif)
        if not _aktif:
            _bingkai_bersih()
    logger.info(f"Kamera peramban: {'aktif' if _aktif else 'nonaktif'}")


def apakah_aktif() -> bool:
    with _lock:
        return _aktif


def _bingkai_bersih() -> None:
    """Kosongkan slot (pemanggil harus memegang kunci)."""
    global _bingkai, _bingkai_pada
    _bingkai = None
    _bingkai_pada = 0.0


def _urai_data_url(data_url: str) -> bytes | None:
    """Ubah data URL (``data:image/jpeg;base64,...``) menjadi byte JPEG."""
    teks = (data_url or "").strip()
    if not teks:
        return None
    if teks.startswith("data:"):
        koma = teks.find(",")
        if koma < 0:
            return None
        teks = teks[koma + 1 :]
    try:
        data = base64.b64decode(teks, validate=False)
    except (binascii.Error, ValueError) as e:
        logger.debug(f"Bingkai peramban tidak bisa diurai: {e}")
        return None
    if not data or len(data) > MAKS_UKURAN_BINGKAI:
        logger.debug(f"Bingkai peramban ditolak (ukuran {len(data)} byte)")
        return None
    return data


def simpan_bingkai(data_url: str) -> bool:
    """Terima satu bingkai dari peramban. True bila tersimpan."""
    data = _urai_data_url(data_url)
    if data is None:
        return False
    global _bingkai, _bingkai_pada
    with _lock:
        if not _aktif:
            return False
        _bingkai = data
        _bingkai_pada = time.time()
    try:
        with open(_jalur_pratinjau(), "wb") as f:
            f.write(data)
    except Exception as e:
        logger.debug(f"Gagal menulis pratinjau bingkai: {e}")
    logger.info(f"Kamera peramban: bingkai diterima ({len(data)} byte)")
    return True


def ambil_bingkai(maks_umur_s: float = MAKS_UMUR_BINGKAI_S) -> bytes | None:
    """Ambil bingkai peramban bila ada dan masih segar, jika tidak None."""
    with _lock:
        if not _aktif or _bingkai is None:
            return None
        umur = time.time() - _bingkai_pada
        if umur > maks_umur_s:
            logger.debug(f"Bingkai peramban kedaluwarsa ({umur:.1f} detik)")
            return None
        return _bingkai


def ada_bingkai_segar() -> bool:
    return ambil_bingkai() is not None
