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

# Kata pada judul yang menandakan hasil BUKAN lagu aslinya. Kompilasi remix
# sering muncul lebih dulu di YouTube walau kata kunci penyanyi ada di
# judulnya (mis. "Hitam Putih - REMIX ... Sheila On 7 ..."), sehingga pengguna
# mendengar lagu yang salah.
_KATA_TIDAK_DIINGINKAN = (
    "remix",
    "megamix",
    "mega mix",
    "medley",
    "compilation",
    "kompilasi",
    "karaoke",
    "instrumental",
    "cover",
    "sped up",
    "slowed",
    "reverb",
    "nightcore",
    "tiktok",
    "playlist",
    "full album",
    "nonstop",
    "dj ",
    "mix ",
    "mix)",
    "live",
)

# Kata yang terlalu umum untuk dipakai menilai relevansi.
_KATA_UMUM = {
    "lagu", "musik", "music", "song", "songs", "putar", "putarkan", "nyalakan",
    "mainkan", "dengar", "dengarkan", "the", "play", "feat", "ft", "official",
    "audio", "video", "lyric", "lyrics", "mp3", "and", "dan", "on", "by",
}


def _kata_kunci(kueri: str) -> list[str]:
    """Ambil kata kunci bermakna dari permintaan pengguna."""
    hasil = []
    for k in (kueri or "").split():
        bersih = k.strip(".,!?\"'()[]-").lower()
        if len(bersih) >= 3 and bersih not in _KATA_UMUM:
            hasil.append(bersih)
    return hasil


def skor_relevansi(judul: str, kueri: str, durasi: int = 0) -> float:
    """Nilai kecocokan judul dengan permintaan (makin besar makin cocok).

    Dipakai untuk memilih hasil terbaik dan menolak kompilasi remix/karaoke.
    """
    if not judul:
        return -99.0
    kecil = judul.lower()
    skor = 0.0

    kata = _kata_kunci(kueri)
    if kata:
        cocok = sum(1 for k in kata if k in kecil)
        skor += 2.0 * (cocok / len(kata))
        # Semua kata kunci muncul -> beri bonus.
        if cocok == len(kata):
            skor += 1.5
    else:
        skor += 0.5  # tidak ada kata kunci bermakna; netral saja

    for buruk in _KATA_TIDAK_DIINGINKAN:
        if buruk in kecil:
            skor -= 1.5

    # Judul yang jauh lebih panjang dari permintaan biasanya kompilasi.
    if len(judul) > max(40, len(kueri) * 4):
        skor -= 1.0

    # Durasi wajar untuk satu lagu (60 detik - 10 menit) lebih disukai.
    if durasi:
        if 60 <= durasi <= 600:
            skor += 0.5
        elif durasi > 900:
            skor -= 1.0

    return skor


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
    """Cari lagu di YouTube. Mengembalikan daftar kosong bila gagal.

    Hasil diurutkan berdasarkan relevansi (lihat :func:`skor_relevansi`) supaya
    lagu yang benar-benar diminta muncul lebih dulu, bukan kompilasi remix.
    """
    if not tersedia():
        logger.info("Pencarian YouTube dilewati: yt-dlp tidak terpasang")
        return []

    def _cari() -> list[HasilYouTube]:
        import yt_dlp

        # Ambil lebih banyak kandidat daripada yang dibutuhkan agar bisa
        # dipilih yang paling relevan.
        jumlah = max(maks, 8)
        hasil: list[tuple[float, HasilYouTube]] = []
        try:
            with yt_dlp.YoutubeDL(_OPSI_CARI) as ydl:
                info = ydl.extract_info(f"ytsearch{jumlah}:{kueri}", download=False)
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
            judul = str(entri.get("title") or "")
            lagu = HasilYouTube(
                video_id=vid,
                judul=judul,
                durasi=durasi,
                url=f"https://www.youtube.com/watch?v={vid}",
            )
            hasil.append((skor_relevansi(judul, kueri, durasi), lagu))

        if not hasil:
            return []

        hasil.sort(key=lambda pasangan: pasangan[0], reverse=True)
        teratas = hasil[:maks]
        logger.info(
            "YouTube: kandidat terbaik '%s' (skor %.2f) dari %d hasil",
            teratas[0][1].judul,
            teratas[0][0],
            len(hasil),
        )
        return [lagu for _, lagu in teratas]

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
