"""Uji jalur pertanyaan panjang (teks -> suara) dan instruksi Bahasa Indonesia.

Latar belakang: server xiaozhi menolak teks panjang pada jalur listen/detect,
sehingga pertanyaan panjang harus dikirim sebagai SUARA. Bahasa jawaban model
ditentukan prompt di sisi server (bawaan: Mandarin), jadi satu kalimat
instruksi Bahasa Indonesia disertakan pada jalur suara.

Uji ini mengunci perilaku itu beserta sakelar penonaktifannya.
"""

from __future__ import annotations

from src.audio_processing import teks_ke_suara as tts


def test_instruksi_ditambahkan_secara_bawaan():
    hasil = tts.teks_dengan_instruksi("Apa saja jurusan di UCIC?")
    assert hasil.startswith(tts.INSTRUKSI_JAWAB_INDONESIA)
    assert "Apa saja jurusan di UCIC?" in hasil


def test_instruksi_tidak_digandakan():
    sekali = tts.teks_dengan_instruksi("halo")
    dua_kali = tts.teks_dengan_instruksi(sekali)
    assert sekali == dua_kali
    assert dua_kali.count(tts.INSTRUKSI_JAWAB_INDONESIA) == 1


def test_instruksi_bisa_dinonaktifkan(monkeypatch):
    monkeypatch.setenv("SELA_PAKSA_JAWAB_INDONESIA", "0")
    assert tts.teks_dengan_instruksi("halo") == "halo"


def test_teks_kosong_tetap_kosong():
    assert tts.teks_dengan_instruksi("") == ""
    assert tts.teks_dengan_instruksi("   ") == ""
    assert tts.teks_dengan_instruksi(None) == ""


def test_instruksi_bahasa_indonesia_tanpa_aksara_han():
    assert not any("\u4e00" <= ch <= "\u9fff" for ch in tts.INSTRUKSI_JAWAB_INDONESIA)


def test_perlu_jalur_suara_sesuai_ambang():
    """Teks pendek lewat jalur teks; teks panjang lewat jalur suara."""
    pendek = "Cara daftar?"  # 12 karakter
    panjang = "Bagaimana cara mendaftar sebagai mahasiswa baru di UCIC tahun ini?"
    assert len(pendek) <= tts.AMBANG_TEKS_PANJANG
    assert len(panjang) > tts.AMBANG_TEKS_PANJANG
    assert tts.perlu_jalur_suara(panjang) is True
    assert tts.perlu_jalur_suara(pendek) is False
