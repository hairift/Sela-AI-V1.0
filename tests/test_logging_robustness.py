"""Pengujian ketahanan sistem log.

Latar belakang: aplikasi yang dikemas dengan PyInstaller mode `windowed` tidak
punya konsol, sehingga `sys.stdout` bernilai None. Sebelumnya handler konsol
tetap dibuat dan logging jatuh ke handler cadangan yang gagal saat meng-encode
karakter non-ASCII (mis. pesan berbahasa Mandarin), sehingga muncul
UnicodeEncodeError pada setiap baris log.
"""

import logging
import sys

import pytest


def _reset_logging():
    """Bersihkan handler agar setup_logging bisa dijalankan ulang."""
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
        try:
            h.close()
        except Exception:
            pass


@pytest.fixture
def tanpa_konsol(monkeypatch):
    """Simulasikan aplikasi windowed: stdout/stderr tidak ada."""
    _reset_logging()
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)
    yield
    monkeypatch.undo()
    _reset_logging()


def test_setup_logging_tidak_gagal_tanpa_konsol(tanpa_konsol):
    import src.logging as sela_logging

    # Tidak boleh melempar exception walau konsol tidak ada.
    sela_logging.setup_logging(enable_console=True)


def test_menulis_log_non_ascii_tanpa_konsol_tidak_error(tanpa_konsol):
    import src.logging as sela_logging

    sela_logging.setup_logging(enable_console=True)
    log = sela_logging.get_logger("uji.tanpa_konsol")

    # Pesan campuran Indonesia + karakter non-ASCII: dulu memicu
    # UnicodeEncodeError di handler cadangan.
    log.info("Memakai opus bawaan: C:\\path\\opus.dll — 你好小智")
    log.warning("Pustaka opus tidak ditemukan; audio mungkin tidak berfungsi.")
    log.error("Galat uji: éàü✓ 中文")


def test_handler_konsol_dilewati_bila_tidak_ada_stdout(tanpa_konsol):
    import src.logging as sela_logging

    sela_logging.setup_logging(enable_console=True)

    root = logging.getLogger()
    handler_stream = [
        getattr(h, "stream", None)
        for h in root.handlers
        if isinstance(h, logging.StreamHandler)
        and not isinstance(h, logging.FileHandler)
    ]
    # Tidak boleh ada handler konsol yang menunjuk ke None.
    assert all(s is not None for s in handler_stream)
