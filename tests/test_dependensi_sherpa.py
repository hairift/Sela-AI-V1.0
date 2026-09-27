"""Pengujian dependensi sherpa-onnx.

Latar belakang: aplikasi hasil paket **tidak bisa dibuka di Windows** karena
``sherpa_onnx/lib/`` hanya berisi ``_sherpa_onnx.*.pyd`` tanpa satu pun DLL
pendamping (``onnxruntime.dll``, ``sherpa-onnx-c-api.dll``,
``sherpa-onnx-cxx-api.dll``). Tanpa DLL itu pembuatan ``KeywordSpotter``
(wake word) menabrak memori → segfault, dan karena aplikasi dibangun
``--windowed`` pengguna tidak melihat pesan apa pun.

Akar masalahnya bukan PyInstaller, melainkan ``pyproject.toml``: dependensi
``sherpa-onnx-core`` — paket yang justru **memasok** ketiga DLL tersebut ke
``sherpa_onnx/lib/`` — diberi penanda ``sys_platform != 'win32'`` sehingga
tidak pernah dipasang di Windows. Wheel ``sherpa-onnx`` sendiri hanya berisi
pembungkus Python.

Berkas ini mengunci agar penanda platform itu tidak pernah kembali.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

AKAR = Path(__file__).resolve().parents[1]
PYPROJECT = AKAR / "pyproject.toml"
HOOK = AKAR / "pyinstaller_hooks" / "hook-sherpa_onnx.py"


def _dependensi() -> list[str]:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    proyek = data.get("project", {})
    daftar = list(proyek.get("dependencies", []))
    for nilai in (proyek.get("optional-dependencies") or {}).values():
        daftar.extend(nilai)
    return daftar


def _cari(nama: str) -> list[str]:
    pola = re.compile(rf"^{re.escape(nama)}\b")
    return [d for d in _dependensi() if pola.match(d.strip())]


def test_sherpa_onnx_dideklarasikan():
    assert _cari("sherpa-onnx"), "sherpa-onnx harus ada di dependensi"


def test_sherpa_onnx_core_dideklarasikan():
    assert _cari("sherpa-onnx-core"), (
        "sherpa-onnx-core harus ada di dependensi: paket itulah yang memasok "
        "DLL pendamping ke sherpa_onnx/lib/"
    )


def test_sherpa_onnx_core_tanpa_penanda_platform():
    """Inti penguncian: sherpa-onnx-core WAJIB berlaku di semua platform.

    Penanda ``sys_platform != 'win32'`` pernah membuat Windows kehilangan
    seluruh DLL pendamping dan aplikasinya tidak mau terbuka.
    """
    baris = _cari("sherpa-onnx-core")
    assert baris, "sherpa-onnx-core tidak ditemukan"
    for d in baris:
        assert "sys_platform" not in d, (
            "sherpa-onnx-core tidak boleh diberi penanda platform; "
            f"ketemu: {d!r}"
        )
        assert "platform_system" not in d, (
            "sherpa-onnx-core tidak boleh diberi penanda platform; "
            f"ketemu: {d!r}"
        )
        assert "win32" not in d, (
            f"sherpa-onnx-core tidak boleh mengecualikan Windows; ketemu: {d!r}"
        )


def test_sherpa_onnx_juga_tanpa_penanda_platform():
    for d in _cari("sherpa-onnx"):
        assert "sys_platform" not in d, (
            f"sherpa-onnx harus berlaku di semua platform; ketemu: {d!r}"
        )


def test_hook_pyinstaller_sherpa_tersedia():
    """Tanpa hook ini DLL yang sudah ada di disk tetap tidak ikut terbundel."""
    assert HOOK.is_file(), f"hook PyInstaller hilang: {HOOK}"
    isi = HOOK.read_text(encoding="utf-8")
    assert "collect_dynamic_libs" in isi
    assert "sherpa_onnx" in isi


def test_build_json_menunjuk_direktori_hook():
    """build.json adalah sumber kebenaran build, bukan sela-ai.spec."""
    import json

    cfg = json.loads((AKAR / "build.json").read_text(encoding="utf-8"))
    py = cfg.get("pyinstaller", {})
    assert "pyinstaller_hooks" in (py.get("additional_hooks_dir") or []), (
        "build.json harus memasang additional_hooks_dir = ['pyinstaller_hooks']"
    )
    assert "sherpa_onnx" in (py.get("hidden_import") or []), (
        "sherpa_onnx harus ada di hidden_import build.json"
    )
