"""Memastikan tidak ada berkas kiblat yang hilang dari SELA AI.

Kiblat proyek ini adalah `py-xiaozhi-main` (mesin AI asli). Aturan tetap
proyek: modifikasi SELA hanya boleh **aditif** — tidak boleh ada fitur,
modul, model, atau aset suara kiblat yang hilang.

Skrip ini membandingkan daftar berkas kiblat dengan daftar berkas SELA dan
melaporkan apa pun yang ada di kiblat tetapi tidak ada di SELA.

Pemakaian:
    python scripts/cek_paritas_kiblat.py

Keluar dengan kode 1 bila ada berkas yang hilang, 0 bila lengkap (atau bila
kiblat tidak tersedia, misalnya di CI yang hanya memeriksa SELA).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Folder yang dibandingkan, relatif terhadap akar masing-masing proyek.
FOLDER_DIPERIKSA = ("src", "models", "assets/sounds", "scripts")

# Nama folder kiblat di dalam ruang kerja.
NAMA_KIBLAT = Path("py-xiaozhi-main") / "py-xiaozhi-main"


def cari_kiblat(akar_proyek: Path) -> Path | None:
    """Cari folder kiblat di sekitar proyek SELA."""
    kandidat = [
        akar_proyek.parent / NAMA_KIBLAT,
        akar_proyek / NAMA_KIBLAT,
    ]
    for kandidat_path in kandidat:
        if (kandidat_path / "src").is_dir():
            return kandidat_path
    return None


def kumpulkan_berkas(akar: Path, sub: str) -> set[str]:
    """Kumpulkan jalur relatif semua berkas di bawah `akar/sub`."""
    basis = akar / sub.replace("/", os.sep)
    hasil: set[str] = set()
    if not basis.is_dir():
        return hasil
    for dirpath, dirnames, filenames in os.walk(basis):
        # Lewati cache; isinya tidak pernah relevan.
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for nama in filenames:
            if nama.endswith(".pyc"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, nama), akar)
            hasil.add(rel.replace(os.sep, "/"))
    return hasil


def main() -> int:
    akar_proyek = Path(__file__).resolve().parent.parent
    kiblat = cari_kiblat(akar_proyek)

    if kiblat is None:
        print("Kiblat (py-xiaozhi-main) tidak ditemukan; pemeriksaan dilewati.")
        return 0

    print(f"Kiblat : {kiblat}")
    print(f"SELA   : {akar_proyek}")
    print()

    total_hilang = 0
    for sub in FOLDER_DIPERIKSA:
        berkas_kiblat = kumpulkan_berkas(kiblat, sub)
        berkas_sela = kumpulkan_berkas(akar_proyek, sub)
        hilang = sorted(berkas_kiblat - berkas_sela)
        total_hilang += len(hilang)

        tanda = "OK  " if not hilang else "HILANG"
        print(
            f"[{tanda}] {sub:15} kiblat={len(berkas_kiblat):4} "
            f"sela={len(berkas_sela):4} hilang={len(hilang)}"
        )
        for nama in hilang[:20]:
            print(f"          - {nama}")
        if len(hilang) > 20:
            print(f"          ... dan {len(hilang) - 20} berkas lain")

    print()
    if total_hilang:
        print(
            f"GAGAL: {total_hilang} berkas kiblat tidak ada di SELA. "
            "Modifikasi harus aditif; kembalikan berkas tersebut."
        )
        return 1

    print("Semua berkas kiblat masih lengkap di SELA. Tidak ada fitur yang hilang.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
