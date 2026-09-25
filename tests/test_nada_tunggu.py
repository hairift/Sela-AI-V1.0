"""Uji nada tunggu saat mencari musik.

Pengguna mengeluh tidak tahu apakah permintaan lagunya sedang diproses.
Nada tunggu harus:
  * tersedia sebagai berkas WAV di locale Indonesia;
  * berbunyi selama pencarian/pengunduhan;
  * SELALU berhenti, apa pun hasilnya (berhasil, gagal, dikecualikan).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.mcp.tools.music import nada_tunggu as modul
from src.mcp.tools.music.nada_tunggu import NadaTunggu


def test_berkas_nada_tunggu_ada():
    """Berkas nada tunggu harus ada di assets/sounds/id-ID."""
    from src.utils.resource_finder import get_app_root

    berkas = get_app_root() / "assets" / "sounds" / "id-ID" / "nada_tunggu.wav"
    assert berkas.is_file(), f"berkas nada tunggu tidak ada: {berkas}"
    assert berkas.stat().st_size > 1000, "berkas nada tunggu terlalu kecil"


def test_tersedia_dan_muat_wav():
    nada = NadaTunggu("id-ID")
    assert nada.tersedia() is True

    berkas = nada._berkas_nada()
    assert berkas is not None
    dimuat = NadaTunggu._muat_wav(berkas)
    assert dimuat is not None
    audio, sr = dimuat
    assert sr > 0
    assert len(audio) > 0
    # Harus ada sinyal nyata, bukan berkas kosong.
    assert float(max(abs(audio))) > 0.01


def test_mulai_hentikan_aman_berulang(monkeypatch):
    """mulai/hentikan tidak boleh melempar walau dipanggil berulang."""
    nada = NadaTunggu("id-ID")
    # Jangan benar-benar memutar audio di lingkungan uji.
    diputar = {"jumlah": 0}

    def _putar_palsu(self, audio, sr):  # noqa: ANN001
        diputar["jumlah"] += 1
        self._stop.wait(0.2)

    monkeypatch.setattr(NadaTunggu, "_putar_ulang", _putar_palsu)

    assert nada.mulai() is True
    assert nada.mulai() is True  # idempoten
    nada.hentikan()
    nada.hentikan()  # aman walau tidak berbunyi


def test_hentikan_saat_tidak_berbunyi_tidak_melempar():
    NadaTunggu("id-ID").hentikan()


def test_tanpa_berkas_gagal_dengan_tenang(tmp_path, monkeypatch):
    """Bila berkas tidak ada, mulai() mengembalikan False tanpa melempar."""
    monkeypatch.setattr(modul, "get_app_root", lambda: tmp_path)
    nada = NadaTunggu("id-ID")
    assert nada.tersedia() is False
    assert nada.mulai() is False


@pytest.mark.asyncio
async def test_search_and_play_selalu_hentikan_nada(monkeypatch):
    """Terlepas dari hasilnya, nada tunggu harus dihentikan (lebih utama:
    tidak boleh berbunyi terus ketika pencarian gagal)."""
    from src.mcp.tools.music import music_player as mp

    dipanggil = {"mulai": 0, "hentikan": 0}

    class NadaPalsu:
        def mulai(self):
            dipanggil["mulai"] += 1
            return True

        def hentikan(self):
            dipanggil["hentikan"] += 1

    async def gagal_cari(*_a, **_k):
        raise RuntimeError("mesin pencari mati")

    monkeypatch.setattr(mp, "NadaTunggu", NadaPalsu)
    monkeypatch.setattr(mp, "search_song", gagal_cari)

    player = mp.MusicPlayer()
    player._nada_tunggu = NadaPalsu()

    hasil = await player.search_and_play("lagu uji")
    assert hasil["status"] == "error"
    assert dipanggil["mulai"] == 1, "nada tunggu harus dimulai"
    assert dipanggil["hentikan"] >= 1, "nada tunggu harus dihentikan di akhir"
