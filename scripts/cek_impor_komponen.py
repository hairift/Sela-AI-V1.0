"""Cari komponen JSX yang DIPAKAI tetapi TIDAK diimpor.

Kelas galat ini sudah dua kali menyebabkan halaman putih kosong di rilis SELA:
  * v1.0.3/1.0.4 - ``ReferenceError: teksTombol is not defined``
  * v1.0.6       - ``ReferenceError: PemutarMusik is not defined``

Galat seperti ini TIDAK tertangkap oleh ``pytest``, ``vite build``, maupun
ESLint (yang dibatasi hanya pada kesalahan nyata) karena baru muncul saat React
merender di peramban. Skrip ini memeriksa berkas sumber secara statis sehingga
masalahnya ketahuan sebelum pengemasan.

Pemakaian:
    python scripts/cek_impor_komponen.py        # 0 = bersih, 1 = ada masalah
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent / "webui" / "src"


def definisi_komponen() -> dict[str, str]:
    """Peta nama komponen -> berkas tempat ia didefinisikan."""
    peta: dict[str, str] = {}
    for f in ROOT.rglob("*.jsx"):
        try:
            src = f.read_text(encoding="utf-8")
        except Exception:
            continue
        for pola in (
            r"(?:export\s+default\s+function|function|const)\s+([A-Z][A-Za-z0-9_]*)\s*\(",
            r"export\s+default\s+([A-Z][A-Za-z0-9_]*)\b",
        ):
            for m in re.finditer(pola, src):
                peta.setdefault(m.group(1), str(f.relative_to(ROOT)))
    return peta


def nama_diimpor(src: str) -> set[str]:
    """Semua nama yang diimpor di satu berkas (default maupun bernama)."""
    hasil: set[str] = set()
    for m in re.finditer(r"import\s+([A-Za-z0-9_$]+)\s*(?:,\s*\{[^}]*\})?\s*from", src):
        hasil.add(m.group(1))
    for m in re.finditer(r"import\s*\{([^}]*)\}", src):
        for bagian in m.group(1).split(","):
            nama = bagian.strip().split(" as ")[-1].strip()
            if nama:
                hasil.add(nama)
    return hasil


def periksa() -> list[str]:
    peta = definisi_komponen()
    masalah: list[str] = []
    for f in sorted(ROOT.rglob("*.jsx")):
        rel = str(f.relative_to(ROOT))
        src = f.read_text(encoding="utf-8")
        diimpor = nama_diimpor(src)
        dipakai = set(re.findall(r"<([A-Z][A-Za-z0-9_]*)[\s/>]", src))
        for nama in sorted(dipakai):
            if nama in diimpor:
                continue
            asal = peta.get(nama)
            if asal is None:
                continue  # komponen pustaka (mis. Suspense) - bukan urusan kita
            if asal == rel:
                continue  # didefinisikan di berkas yang sama
            masalah.append(f"{rel}: <{nama}> dipakai tetapi TIDAK diimpor (asal: {asal})")
    return masalah


def berkas_tak_terpakai() -> list[str]:
    """Berkas komponen yang ekspor bawaannya tidak diimpor berkas lain.

    Kelas masalah ini sudah terjadi dua kali di SELA:
      * ``PemutarMusik`` ditulis tetapi tidak diimpor ChatPanel -> halaman putih.
      * ``TeksKaya`` ditulis tetapi tidak dipakai sama sekali -> teks kaya
        (tebal/miring/daftar) tidak pernah aktif.

    Pemeriksaan dilakukan per BERKAS (bukan per nama fungsi) supaya komponen
    pembantu yang dipakai di dalam berkasnya sendiri (mis. ``Kartu`` di
    Settings.jsx) tidak salah dianggap kode mati.
    """
    masalah: list[str] = []
    berkas = [f for f in sorted(ROOT.rglob("*.jsx"))]
    isi = {f: f.read_text(encoding="utf-8") for f in berkas}

    for f in berkas:
        rel = str(f.relative_to(ROOT))
        # Titik masuk aplikasi memang tidak diimpor siapa pun.
        if rel.replace("\\", "/").endswith(("App.jsx", "main.jsx")):
            continue

        src = isi[f]
        m = re.search(r"export\s+default\s+(?:function\s+)?([A-Za-z0-9_]+)", src)
        if not m:
            continue
        nama = m.group(1)

        diimpor = False
        for lain, isi_lain in isi.items():
            if lain == f:
                continue
            if re.search(rf"import[^\n]*\b{re.escape(nama)}\b[^\n]*from", isi_lain):
                diimpor = True
                break
        if not diimpor:
            masalah.append(f"{rel}: komponen '{nama}' tidak diimpor berkas mana pun")
    return masalah


def main() -> int:
    masalah = periksa()
    mati = berkas_tak_terpakai()
    if masalah:
        print("GAGAL - komponen JSX tanpa impor (akan menyebabkan halaman putih):")
        for baris in masalah:
            print(f"  - {baris}")
    if mati:
        print("PERINGATAN - berkas komponen tidak terpakai (kode mati):")
        for baris in mati:
            print(f"  - {baris}")
    if masalah or mati:
        return 1
    print("OK - semua komponen JSX sudah diimpor dan terpakai.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
