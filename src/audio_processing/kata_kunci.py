"""Penyaring berkas kata kunci (keywords.txt) untuk sherpa-onnx.

Masalah yang diselesaikan
-------------------------
`sherpa_onnx.KeywordSpotter(...)` memvalidasi isi berkas kata kunci di dalam
kode C++. Bila ada satu baris yang tidak valid, sherpa-onnx memanggil
``exit(-1)`` — proses Python **langsung mati**, tanpa exception yang bisa
ditangkap ``try/except`` dan tanpa jejak di log selain pesan C++ mentah.

Bentuk baris yang benar::

    <token1> <token2> ... <tokenN> @<label>

* ``<label>`` wajib elemen **terakhir**, diawali ``@``, dan **tidak boleh
  mengandung spasi** (kalau ada spasi, kata setelahnya dianggap token).
* Setiap token sebelum label harus ada di ``tokens.txt``.

Modul ini memeriksa berkas sebelum diserahkan ke sherpa-onnx sehingga baris
rusak bisa dibuang, bukan mematikan aplikasi.
"""

from __future__ import annotations

from typing import Iterable, List, Tuple

__all__ = [
    "muat_token",
    "periksa_baris",
    "saring_kata_kunci",
    "HasilSaring",
]


class HasilSaring:
    """Hasil penyaringan berkas kata kunci."""

    __slots__ = ("baris_valid", "baris_rusak")

    def __init__(self, baris_valid: List[str], baris_rusak: List[Tuple[str, str]]):
        self.baris_valid = baris_valid
        # (baris asli, alasan) untuk setiap baris yang dibuang
        self.baris_rusak = baris_rusak

    @property
    def ada_baris_valid(self) -> bool:
        return bool(self.baris_valid)

    @property
    def bersih(self) -> bool:
        return not self.baris_rusak

    @property
    def teks_bersih(self) -> str:
        return "".join(baris + "\n" for baris in self.baris_valid)


def muat_token(tokens_text: str) -> set:
    """Kumpulkan semua token dari isi ``tokens.txt``.

    Format ``tokens.txt``: ``<token> <id>`` per baris (id boleh tidak ada).
    """
    token = set()
    for baris in tokens_text.splitlines():
        bagian = baris.split()
        if bagian:
            token.add(bagian[0])
    return token


def periksa_baris(baris: str, token: Iterable[str]) -> Tuple[bool, str]:
    """Periksa satu baris kata kunci.

    Kembalikan ``(valid, alasan)``. ``alasan`` kosong bila valid.
    """
    teks = baris.strip()
    if not teks:
        return False, "baris kosong"

    if teks.startswith("#"):
        return False, "komentar"

    token = token if isinstance(token, (set, frozenset)) else set(token)
    bagian = teks.split()
    if len(bagian) < 2:
        return False, "perlu minimal satu token dan satu label '@...'"

    label = bagian[-1]
    if not label.startswith("@"):
        return False, "elemen terakhir harus label '@...'"
    if len(label) == 1:
        return False, "label '@' kosong"

    for satuan in bagian[:-1]:
        if satuan.startswith("@"):
            return False, f"label '@...' harus di akhir baris (ditemukan {satuan!r})"
        if satuan not in token:
            return False, f"token {satuan!r} tidak ada di tokens.txt"

    return True, ""


def saring_kata_kunci(keywords_text: str, tokens_text: str) -> HasilSaring:
    """Saring isi berkas kata kunci terhadap ``tokens.txt``."""
    token = muat_token(tokens_text)
    valid: List[str] = []
    rusak: List[Tuple[str, str]] = []

    for baris in keywords_text.splitlines():
        if not baris.strip():
            continue
        ok, alasan = periksa_baris(baris, token)
        if ok:
            valid.append(baris.strip())
        else:
            rusak.append((baris, alasan))

    return HasilSaring(valid, rusak)
