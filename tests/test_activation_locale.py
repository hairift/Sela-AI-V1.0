"""Pengujian lokalisasi jalur aktivasi.

Aplikasi SELA berbahasa Indonesia, sehingga pengumuman suara kode aktivasi
harus memakai rekaman Indonesia (``assets/sounds/id-ID/``) dan bukan
``zh-CN`` seperti bawaan py-xiaozhi.
"""

import ast
import re
from pathlib import Path

import pytest

from src.constants.system import SystemConstants
from src.utils.activation_announcer import ActivationAnnouncer

HAN = re.compile(r"[\u4e00-\u9fff]")
AKAR = Path(__file__).resolve().parent.parent


def test_locale_bawaan_adalah_indonesia():
    assert SystemConstants.DEFAULT_LOCALE == "id-ID"
    assert SystemConstants.DEFAULT_LANGUAGE == "id"


def test_side_effects_memakai_locale_indonesia():
    from src.activation.side_effects import _locale_aktif

    assert _locale_aktif() == "id-ID"


def test_berkas_suara_indonesia_lengkap():
    """activation.wav + 0..9.wav harus ada untuk id-ID."""
    d = AKAR / "assets" / "sounds" / "id-ID"
    assert d.is_dir(), f"Folder suara Indonesia tidak ada: {d}"

    wajib = ["activation"] + [str(i) for i in range(10)]
    hilang = [f"{n}.wav" for n in wajib if not (d / f"{n}.wav").is_file()]
    assert not hilang, f"Berkas suara hilang: {hilang}"


def test_announcer_menemukan_semua_suara_indonesia():
    a = ActivationAnnouncer("id-ID")
    for n in ["activation"] + [str(i) for i in range(10)]:
        path = a._get_sound_path(n)
        assert path is not None, f"Suara {n} tidak ditemukan"
        assert "id-ID" in str(path), f"Suara {n} tidak berasal dari id-ID: {path}"


def test_suara_indonesia_bukan_rekaman_kosong():
    """Pastikan WAV benar-benar berisi audio (bukan berkas placeholder)."""
    import wave

    d = AKAR / "assets" / "sounds" / "id-ID"
    for n in ["activation", "0", "9"]:
        with wave.open(str(d / f"{n}.wav"), "rb") as w:
            durasi = w.getnframes() / w.getframerate()
        assert durasi > 0.3, f"{n}.wav terlalu pendek ({durasi:.2f}s)"


def _docstring_nodes(tree: ast.AST) -> set[int]:
    """Kumpulkan id() node yang merupakan docstring (bukan string runtime)."""
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", None)
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                ids.add(id(body[0].value))
    return ids


def _string_runtime_berhan(berkas: str) -> list[str]:
    """String yang benar-benar dipakai saat berjalan (bukan docstring) & memuat aksara Han."""
    src = (AKAR / berkas).read_text(encoding="utf-8")
    tree = ast.parse(src)
    docstrings = _docstring_nodes(tree)
    baris = src.splitlines()
    hasil = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstrings
            and HAN.search(node.value)
        ):
            teks = baris[node.lineno - 1].strip() if node.lineno <= len(baris) else node.value
            hasil.append(f"L{node.lineno}: {teks[:110]}")
    return sorted(set(hasil))


def test_pesan_aktivasi_berbahasa_indonesia():
    """Tidak boleh ada aksara Han pada string runtime jalur aktivasi."""
    for fp in [
        "src/ui/cli/activation.py",
        "src/ui/shared/activation.py",
        "src/activation/side_effects.py",
    ]:
        pelanggar = _string_runtime_berhan(fp)
        assert not pelanggar, f"{fp} masih memuat teks Mandarin:\n" + "\n".join(pelanggar)


@pytest.mark.parametrize(
    "berkas",
    [
        "src/ui/cli/display.py",
        "src/ui/cli/manager.py",
        "src/ui/tui/app.py",
        "src/ui/tui/manager.py",
        "src/ui/tui/settings_data.py",
        "src/plugins/ui_presenter.py",
    ],
)
def test_tampilan_tidak_memuat_aksara_han(berkas):
    """String runtime yang tampil di antarmuka CLI/TUI/presenter harus bebas aksara Han."""
    pelanggar = _string_runtime_berhan(berkas)
    assert not pelanggar, f"{berkas} masih memuat teks Mandarin:\n" + "\n".join(pelanggar)
