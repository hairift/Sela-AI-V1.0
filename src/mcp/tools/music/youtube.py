"""Penyedia musik YouTube untuk SELA.

Latar belakang
--------------
Pemutar musik bawaan py-xiaozhi mencari lagu lewat **Kuwo** (layanan musik
Tiongkok). Katalognya hampir tidak memuat lagu Indonesia, sehingga permintaan
seperti "putar lagu Sheila On 7" selalu dijawab "tidak menemukan lagu".

Modul ini mencari lewat **YouTube** memakai yt-dlp, yang katalognya global.
Dipakai sebagai CADANGAN: pencarian Kuwo dicoba lebih dulu (cepat, tanpa
unduhan), dan bila tidak ada hasil, YouTube yang dipakai.

Hasil unduhan disimpan di folder cache musik yang sama, sehingga pemutaran
berikutnya tidak perlu mengunduh ulang.
"""

from __future__ import annotations

import asyncio
import pathlib
from dataclasses import dataclass

from src.logging import get_logger

logger = get_logger()

# Batas durasi: hindari mengunduh kompilasi berdurasi berjam-jam.
MAKS_DURASI_DETIK = 900

_OPSI_CARI = {
    "quiet": True,
    "no_warnings": True,
    "extract_flat": True,
    "skip_download": True,
    "noplaylist": True,
}

_OPSI_UNDUH = {
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
    "format": "bestaudio/best",
    "outtmpl": "%(id)s.%(ext)s",
    # Ekstrak audio ke mp3 agar pemutar yang ada bisa langsung memakainya.
    "postprocessors": [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }
    ],
}


@dataclass
class HasilYouTube:
    """Satu lagu yang ditemukan di YouTube."""

    video_id: str
    judul: str
    durasi: int
    url: str


def tersedia() -> bool:
    """Apakah pencarian YouTube bisa dipakai."""
    try:
        import yt_dlp  # noqa: F401
    except Exception:
        return False
    return True


async def cari_lagu(kueri: str, maks: int = 3) -> list[HasilYouTube]:
    """Cari lagu di YouTube. Mengembalikan daftar kosong bila gagal."""
    if not tersedia():
        logger.info("Pencarian YouTube dilewati: yt-dlp tidak terpasang")
        return []

    def _cari() -> list[HasilYouTube]:
        import yt_dlp

        hasil: list[HasilYouTube] = []
        try:
            with yt_dlp.YoutubeDL(_OPSI_CARI) as ydl:
                info = ydl.extract_info(f"ytsearch{maks}:{kueri}", download=False)
        except Exception as e:
            logger.warning(f"Pencarian YouTube gagal: {e}")
            return []

        for entri in (info or {}).get("entries") or []:
            if not entri:
                continue
            durasi = int(entri.get("duration") or 0)
            if durasi and durasi > MAKS_DURASI_DETIK:
                continue
            vid = str(entri.get("id") or "")
            if not vid:
                continue
            hasil.append(
                HasilYouTube(
                    video_id=vid,
                    judul=str(entri.get("title") or ""),
                    durasi=durasi,
                    url=f"https://www.youtube.com/watch?v={vid}",
                )
            )
        return hasil

    return await asyncio.to_thread(_cari)


async def unduh_lagu(lagu: HasilYouTube, folder: pathlib.Path) -> pathlib.Path | None:
    """Unduh satu lagu ke folder cache. Mengembalikan berkasnya bila berhasil."""
    folder.mkdir(parents=True, exist_ok=True)
    # Lewati bila sudah ada (nama berkas memakai id video).
    for ext in ("mp3", "m4a", "webm", "opus"):
        kandidat = folder / f"{lagu.video_id}.{ext}"
        if kandidat.is_file() and kandidat.stat().st_size > 0:
            logger.info(f"Musik YouTube dari cache: {kandidat.name}")
            return kandidat

    def _unduh() -> pathlib.Path | None:
        import yt_dlp

        opsi = dict(_OPSI_UNDUH)
        opsi["outtmpl"] = str(folder / "%(id)s.%(ext)s")
        try:
            with yt_dlp.YoutubeDL(opsi) as ydl:
                ydl.download([lagu.url])
        except Exception as e:
            logger.warning(f"Unduhan YouTube gagal: {e}")
            return None

        for ext in ("mp3", "m4a", "webm", "opus"):
            kandidat = folder / f"{lagu.video_id}.{ext}"
            if kandidat.is_file() and kandidat.stat().st_size > 0:
                return kandidat
        return None

    return await asyncio.to_thread(_unduh)
