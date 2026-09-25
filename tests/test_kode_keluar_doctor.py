"""Uji penjaga: kode keluar mode --doctor tidak boleh ditimpa.

Latar belakang
--------------
``main.py`` menutup blok utamanya dengan::

    finally:
        sys.exit(exit_code)

Kode di dalam ``finally`` MENIMPA kode keluar apa pun yang sudah ditetapkan di
dalam ``try``. Karena itu, ketika pemeriksaan ``--doctor`` dulu dipanggil dari
DALAM blok ``try``::

    sys.exit(run_diagnostics())

kode keluarnya selalu berubah menjadi ``exit_code`` awal (1) - walaupun seluruh
pemeriksaan lolos. Akibatnya skrip atau CI yang memeriksa ``$?`` tidak bisa
membedakan doctor yang berhasil dari yang gagal, dan doctor yang sukses
terlihat seperti kegagalan.

Berkas ini mengunci perbaikannya: penanganan ``--doctor`` harus berada SEBELUM
blok ``try/finally`` tersebut, sehingga kode keluarnya tidak ditimpa.

Uji ini sengaja memeriksa struktur kode (AST), bukan menjalankan aplikasi,
supaya hasilnya tidak bergantung pada perangkat audio di mesin penguji.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

AKAR = Path(__file__).resolve().parents[1]
BERKAS_MAIN = AKAR / "main.py"


def _pohon() -> ast.Module:
    return ast.parse(BERKAS_MAIN.read_text(encoding="utf-8"))


def _blok_main(pohon: ast.Module) -> ast.If:
    """Temukan `if __name__ == "__main__":`."""
    for simpul in pohon.body:
        if isinstance(simpul, ast.If):
            sumber = ast.unparse(simpul.test)
            if "__name__" in sumber and "__main__" in sumber:
                return simpul
    pytest.fail("Blok `if __name__ == '__main__':` tidak ditemukan di main.py")


def _adalah_cabang_doctor(simpul: ast.stmt) -> bool:
    """Benar bila simpul adalah `if ...doctor...:`."""
    if not isinstance(simpul, ast.If):
        return False
    return "doctor" in ast.unparse(simpul.test)


def test_main_berkas_ada():
    assert BERKAS_MAIN.is_file(), f"main.py tidak ditemukan di {BERKAS_MAIN}"


def test_penanganan_doctor_ada():
    blok = _blok_main(_pohon())
    cabang = [s for s in blok.body if _adalah_cabang_doctor(s)]
    assert cabang, "Penanganan argumen --doctor tidak ditemukan di main.py"


def test_penanganan_doctor_di_luar_blok_try_finally():
    """Penanganan --doctor tidak boleh berada di dalam blok try/finally utama.

    Bila berada di dalamnya, `finally: sys.exit(exit_code)` akan menimpa kode
    keluar hasil pemeriksaan.
    """
    blok = _blok_main(_pohon())

    # Cari blok try yang diakhiri `finally: sys.exit(...)`.
    indeks_try = None
    for i, simpul in enumerate(blok.body):
        if isinstance(simpul, ast.Try) and simpul.finalbody:
            punya_exit = any(
                isinstance(n, ast.Call)
                and isinstance(n.func, ast.Attribute)
                and n.func.attr == "exit"
                for isi in simpul.finalbody
                for n in ast.walk(isi)
            )
            if punya_exit:
                indeks_try = i
                break

    assert indeks_try is not None, (
        "Blok try dengan `finally: sys.exit(...)` tidak ditemukan di main.py - "
        "uji ini perlu diperbarui."
    )

    indeks_doctor = next(
        (i for i, s in enumerate(blok.body) if _adalah_cabang_doctor(s)), None
    )
    assert indeks_doctor is not None, "Penanganan --doctor tidak ditemukan."

    assert indeks_doctor < indeks_try, (
        "Penanganan --doctor berada SETELAH (atau di dalam) blok try/finally. "
        "`finally: sys.exit(exit_code)` akan menimpa kode keluar hasil "
        "pemeriksaan, sehingga --doctor selalu keluar dengan kode 1. "
        "Pindahkan penanganan --doctor ke atas blok try."
    )


def test_dokter_mengembalikan_kode_yang_benar():
    """`run_diagnostics()` harus mengembalikan 0 saat tidak ada kegagalan."""
    from src.utils import diagnostics

    kode = diagnostics.run_diagnostics()
    assert kode in (0, 1), f"Kode keluar doctor tidak wajar: {kode}"
    # Bila doctor melaporkan 0 kegagalan, kode keluarnya wajib 0.
    jumlah_gagal = sum(1 for r in diagnostics._results if r[0] == diagnostics.FAIL)
    if jumlah_gagal == 0:
        assert kode == 0, (
            f"Doctor melaporkan 0 kegagalan tetapi mengembalikan kode {kode}. "
            "Seharusnya 0."
        )
