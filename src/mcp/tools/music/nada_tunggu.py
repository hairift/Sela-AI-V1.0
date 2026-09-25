"""Nada tunggu saat mesin AI sedang mencari / mengunduh lagu.

Pengguna tidak tahu apakah permintaannya sedang diproses atau macet ketika
meminta lagu, karena pencarian dan pengunduhan bisa memakan beberapa detik.
Modul ini memutar nada lembut berulang selama proses itu berjalan, lalu
berhenti sendiri begitu musik asli mulai diputar (atau proses gagal).

Implementasi sengaja memakai `sounddevice` (sama dengan pemutar verifikasi
aktivasi) dan **bukan** `AudioCodec`, agar:
  * tidak mengganggu aliran Opus ke mesin AI;
  * tidak perlu menunggu codec siap;
  * mudah diuji.

Nada dibaca dari `assets/sounds/<locale>/nada_tunggu.wav`. Bila berkas tidak
ada, modul gagal dengan tenang (hanya mencatat debug) - nada tunggu hanya
pelengkap, tidak boleh menggagalkan pemutaran musik.
"""

from __future__ import annotations

import threading
import wave
from pathlib import Path

from src.logging import get_logger
from src.utils.resource_finder import get_app_root

logger = get_logger()

# Selang antar pemutaran nada (detik). Musik asli biasanya mulai di bawah
# angka ini, sehingga pengguna mendengar satu-dua kali saja.
_JEDA_ANTAR_NADA = 1.1


class NadaTunggu:
    """Pemutar nada tunggu sederhana (thread terpisah, bisa dihentikan)."""

    def __init__(self, locale: str = "id-ID") -> None:
        self._locale = locale
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._kunci = threading.Lock()

    # ------------------------------------------------------------------
    # Berkas nada
    # ------------------------------------------------------------------
    def _berkas_nada(self) -> Path | None:
        dasar = get_app_root() / "assets" / "sounds"
        for locale in (self._locale, "id-ID", "zh-CN"):
            berkas = dasar / locale / "nada_tunggu.wav"
            if berkas.is_file():
                return berkas
        return None

    def tersedia(self) -> bool:
        """True bila berkas nada tunggu ada (untuk uji/diagnosis)."""
        return self._berkas_nada() is not None

    @staticmethod
    def _muat_wav(berkas: Path):
        """Muat WAV menjadi (float32 mono, sample_rate). None bila gagal."""
        try:
            import numpy as np

            with wave.open(str(berkas), "rb") as wf:
                kanal = wf.getnchannels()
                lebar = wf.getsampwidth()
                sr = wf.getframerate()
                mentah = wf.readframes(wf.getnframes())

            if lebar == 2:
                audio = np.frombuffer(mentah, dtype=np.int16).astype(np.float32) / 32768.0
            elif lebar == 4:
                audio = (
                    np.frombuffer(mentah, dtype=np.int32).astype(np.float32)
                    / 2147483648.0
                )
            elif lebar == 1:
                audio = (
                    np.frombuffer(mentah, dtype=np.uint8).astype(np.float32) - 128.0
                ) / 128.0
            else:
                logger.debug(f"Nada tunggu: bit depth {lebar * 8} tidak didukung")
                return None

            if kanal > 1:
                audio = audio.reshape(-1, kanal).mean(axis=1)
            return audio, sr
        except Exception as e:
            logger.debug(f"Nada tunggu: gagal memuat {berkas}: {e}")
            return None

    # ------------------------------------------------------------------
    # Pemutaran
    # ------------------------------------------------------------------
    def _putar_ulang(self, audio, sr: int) -> None:
        import sounddevice as sd

        try:
            while not self._stop.is_set():
                sd.play(audio, sr)
                # Tunggu selama nada berbunyi, dengan jeda pendek agar bisa
                # dihentikan segera saat musik asli mulai.
                akhir = threading.Event()
                durasi = len(audio) / float(sr or 24000)
                if self._stop.wait(max(0.05, durasi)):
                    sd.stop()
                    break
                # Jeda antar nada supaya terdengar lembut, tidak beruntun.
                self._stop.wait(_JEDA_ANTAR_NADA)
                akhir.set()
        except Exception as e:
            logger.debug(f"Nada tunggu: pemutaran berhenti: {e}")
        finally:
            try:
                import sounddevice as sd

                sd.stop()
            except Exception:
                pass

    def mulai(self) -> bool:
        """Mulai memutar nada tunggu. Aman dipanggil berulang.

        Returns:
            True bila putaran nada dimulai, False bila berkas tidak ada.
        """
        with self._kunci:
            if self._thread is not None and self._thread.is_alive():
                return True

            berkas = self._berkas_nada()
            if berkas is None:
                logger.debug("Nada tunggu: berkas tidak ditemukan, dilewati")
                return False

            dimuat = self._muat_wav(berkas)
            if dimuat is None:
                return False
            audio, sr = dimuat

            self._stop.clear()
            self._thread = threading.Thread(
                target=self._putar_ulang,
                args=(audio, sr),
                daemon=True,
                name="NadaTungguMusik",
            )
            self._thread.start()
            logger.debug("Nada tunggu: mulai")
            return True

    def hentikan(self) -> None:
        """Hentikan nada tunggu (aman bila tidak sedang berbunyi)."""
        with self._kunci:
            self._stop.set()
            thread = self._thread
            self._thread = None
        try:
            import sounddevice as sd

            sd.stop()
        except Exception:
            pass
        if thread is not None and thread.is_alive():
            thread.join(timeout=1.0)
