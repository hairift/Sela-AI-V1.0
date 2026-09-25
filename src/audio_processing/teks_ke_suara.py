"""Ubah teks menjadi suara agar pertanyaan panjang bisa dikirim ke mesin AI.

Latar belakang
--------------
Server xiaozhi menolak teks panjang pada jalur ``listen/detect``:

    {"type": "alert", "message": "Detect is only for wake words, do not send long texts."}

Jalur itu memang hanya untuk kata bangun, sehingga tombol pertanyaan cepat dan
ketikan panjang selalu gagal. Percobaan terhadap beberapa bentuk pesan lain
(``type=text``, ``type=message``, ``listen/start`` lalu teks) tidak menghasilkan
tanggapan apa pun dari server — satu-satunya jalur yang menerima pertanyaan
panjang adalah **suara**.

Modul ini menyintesis teks menjadi PCM 16 kHz mono memakai Edge TTS (gratis,
tanpa kunci API, suara Indonesia ``id-ID-GadisNeural`` / ``id-ID-ArdiNeural``),
lalu hasilnya dikirim lewat jalur suara biasa. Dengan begitu panjang pertanyaan
tidak lagi dibatasi dan mesin AI menerimanya persis seperti orang berbicara.
"""

from __future__ import annotations

import asyncio
import os
import pathlib
import shutil
import subprocess
import tempfile

import numpy as np

from src.logging import get_logger

logger = get_logger()

# Suara Indonesia yang dipakai. Gadis terdengar ramah dan jelas untuk asisten.
SUARA_DEFAULT = "id-ID-GadisNeural"
SUARA_CADANGAN = "id-ID-ArdiNeural"

# Teks di atas ambang ini dikirim sebagai suara; di bawahnya jalur teks biasa
# dipakai karena lebih cepat dan tidak perlu sintesis.
AMBANG_TEKS_PANJANG = 24

# Batas aman panjang teks yang disintesis (menghindari audio sangat panjang).
MAKS_KARAKTER = 600

# Instruksi singkat yang diucapkan sebelum pertanyaan panjang.
#
# Bahasa jawaban model ditentukan oleh prompt agent di sisi server, bukan oleh
# aplikasi. Pada akun bawaan, prompt-nya berbahasa Mandarin sehingga SELA
# kadang menjawab dalam Bahasa Mandarin walau pertanyaannya Bahasa Indonesia.
# Prompt LLM tidak bisa diubah dari sisi klien, tetapi karena pertanyaan panjang
# dikirim sebagai SUARA (lalu ditranskrip server), menambahkan satu kalimat
# instruksi Bahasa Indonesia di depan pertanyaan membuat model menjawab dalam
# Bahasa Indonesia.
#
# Nonaktifkan dengan SELA_PAKSA_JAWAB_INDONESIA=0 bila prompt server sudah
# diatur sendiri.
INSTRUKSI_JAWAB_INDONESIA = "Tolong jawab dengan Bahasa Indonesia."


def _paksa_indonesia_aktif() -> bool:
    return os.environ.get("SELA_PAKSA_JAWAB_INDONESIA", "1") != "0"


def teks_dengan_instruksi(teks: str) -> str:
    """Tambahkan instruksi Bahasa Indonesia di depan pertanyaan (bila aktif).

    Hanya dipakai pada jalur suara; pertanyaan pendek (yang lewat jalur teks
    dengan batas ~24 karakter) tidak disentuh karena akan melebihi batas.
    """
    teks = (teks or "").strip()
    if not teks or not _paksa_indonesia_aktif():
        return teks
    if teks.startswith(INSTRUKSI_JAWAB_INDONESIA):
        return teks
    return f"{INSTRUKSI_JAWAB_INDONESIA} {teks}"


class TeksKeSuaraError(RuntimeError):
    """Gagal mengubah teks menjadi suara."""


def cari_ffmpeg() -> str | None:
    """Temukan ffmpeg: yang dibundel dulu, lalu yang ada di PATH."""
    kandidat = [
        pathlib.Path("libs/ffmpeg/ffmpeg.exe"),
        pathlib.Path("libs/ffmpeg.exe"),
        pathlib.Path("libs/ffmpeg/bin/ffmpeg.exe"),
        pathlib.Path("libs/ffmpeg/ffmpeg"),
    ]
    for c in kandidat:
        if c.is_file():
            return str(c)
    return shutil.which("ffmpeg")


def _tambal_parsing_tanggal_edge_tts() -> None:
    """Buat penguraian tanggal Edge TTS tidak bergantung pada locale proses.

    Edge TTS memakai ``datetime.strptime(date, "%a, %d %b %Y %H:%M:%S %Z")``
    untuk menyelaraskan jam dengan server. Direktif ``%a`` dan ``%b``
    bergantung pada locale proses: pada sistem berlokal Indonesia (atau lokal
    non-Inggris lain), nama hari/bulan berbahasa Inggris seperti "Fri" dan
    "Sep" **gagal diurai**, sehingga sintesis selalu berhenti dengan
    "Failed to parse server date".

    Tambalan ini menggantinya dengan pengurai yang tidak bergantung locale.
    """
    try:
        from email.utils import parsedate_to_datetime

        from edge_tts import drm as drm_mod
    except Exception:
        return

    def parse_tanggal(tanggal: str) -> float | None:
        if not isinstance(tanggal, str):
            return None
        try:
            return parsedate_to_datetime(tanggal).timestamp()
        except Exception:
            pass
        # Cadangan terakhir: buang nama hari/bulan lalu hitung manual.
        try:
            import re as _re
            from datetime import datetime as _dt, timezone as _tz

            bersih = _re.sub(r"^[A-Za-z]{3},\s*", "", tanggal.strip())
            bersih = _re.sub(r"\s+[A-Za-z]{2,4}$", "", bersih)  # buang zona waktu
            for pola in ("%d %b %Y %H:%M:%S", "%d %B %Y %H:%M:%S"):
                try:
                    return _dt.strptime(bersih, pola).replace(tzinfo=_tz.utc).timestamp()
                except ValueError:
                    continue
        except Exception:
            pass
        return None

    try:
        drm_mod.DRM.parse_rfc2616_date = staticmethod(parse_tanggal)
        logger.debug("Tambalan parsing tanggal Edge TTS dipasang")
    except Exception as e:
        logger.debug(f"Tambalan parsing tanggal Edge TTS dilewati: {e}")


def tersedia() -> tuple[bool, str]:
    """Periksa apakah TTS bisa dipakai. Mengembalikan (siap, alasan)."""
    try:
        import edge_tts  # noqa: F401
    except Exception as e:
        return False, f"pustaka edge-tts tidak terpasang ({e})"
    if cari_ffmpeg() is None:
        return False, "ffmpeg tidak ditemukan (dibutuhkan untuk mengubah audio)"
    return True, "siap"


async def teks_ke_pcm(teks: str, suara: str = SUARA_DEFAULT) -> np.ndarray:
    """Sintesis teks menjadi PCM mono float32 16 kHz.

    Args:
        teks: Teks yang akan diucapkan.
        suara: Nama suara Edge TTS.

    Returns:
        Larik float32 ternormalisasi pada 16 kHz.

    Raises:
        TeksKeSuaraError: Bila sintesis atau konversi gagal.
    """
    bersih = (teks or "").strip()
    if not bersih:
        raise TeksKeSuaraError("Teks kosong.")
    if len(bersih) > MAKS_KARAKTER:
        bersih = bersih[:MAKS_KARAKTER]

    ffmpeg = cari_ffmpeg()
    if ffmpeg is None:
        raise TeksKeSuaraError("ffmpeg tidak ditemukan.")

    try:
        import edge_tts
    except Exception as e:
        raise TeksKeSuaraError(f"pustaka edge-tts tidak terpasang: {e}") from e

    # Wajib sebelum sintesis: perbaiki penguraian tanggal yang bergantung locale.
    _tambal_parsing_tanggal_edge_tts()

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="sela-tts-"))
    mp3 = tmp / "ucap.mp3"
    pcm = tmp / "ucap.pcm"

    try:
        try:
            komunikasi = edge_tts.Communicate(bersih, suara)
            await komunikasi.save(str(mp3))
        except Exception as e:
            # Suara utama gagal (mis. nama suara berubah) -> coba cadangan.
            logger.warning(f"TTS suara {suara} gagal ({e}), mencoba cadangan")
            komunikasi = edge_tts.Communicate(bersih, SUARA_CADANGAN)
            await komunikasi.save(str(mp3))

        if not mp3.is_file() or mp3.stat().st_size == 0:
            raise TeksKeSuaraError("Edge TTS tidak menghasilkan audio.")

        proses = await asyncio.create_subprocess_exec(
            ffmpeg, "-y", "-i", str(mp3),
            "-f", "s16le", "-acodec", "pcm_s16le",
            "-ar", "16000", "-ac", "1", str(pcm),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, galat = await proses.communicate()
        if proses.returncode != 0 or not pcm.is_file():
            raise TeksKeSuaraError(
                f"ffmpeg gagal: {galat.decode(errors='replace')[-200:]}"
            )

        mentah = np.frombuffer(pcm.read_bytes(), dtype=np.int16)
        if mentah.size == 0:
            raise TeksKeSuaraError("Audio hasil konversi kosong.")
        return (mentah.astype(np.float32) / 32768.0).copy()
    finally:
        # Bersihkan berkas sementara; kegagalan menghapus tidak penting.
        try:
            shutil.rmtree(tmp, ignore_errors=True)
        except Exception:
            pass


def perlu_jalur_suara(teks: str) -> bool:
    """Apakah teks harus dikirim sebagai suara alih-alih jalur teks biasa."""
    return len((teks or "").strip()) > AMBANG_TEKS_PANJANG


def _aktifkan() -> bool:
    """Jalur suara bisa dimatikan lewat lingkungan (untuk uji/CI)."""
    return os.environ.get("SELA_TANPA_TTS") != "1"
