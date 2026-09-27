"""Pengujian penyaring berkas kata kunci (``keywords.txt``) wake word.

Latar belakang: ``sherpa_onnx.KeywordSpotter`` memvalidasi isi berkas kata
kunci di dalam kode C++ dan memanggil ``exit(-1)`` bila ada baris yang tidak
valid. Proses Python mati seketika sehingga ``try/except`` tidak menolong —
inilah yang dulu membuat aplikasi Linux tertutup sendiri saat start.

Berkas ini mengunci dua hal:
1. aturan validasi (label terakhir, tanpa spasi, semua token dikenal);
2. perilaku penyaring saat disuapkan berkas nyata milik proyek.
"""

from pathlib import Path

from src.audio_processing.kata_kunci import (
    HasilSaring,
    muat_token,
    periksa_baris,
    saring_kata_kunci,
)

AKAR = Path(__file__).resolve().parents[1]
MODEL_EN = AKAR / "models" / "en"

TOKENS = muat_token((MODEL_EN / "tokens.txt").read_text(encoding="utf-8"))


def test_token_dimuat():
    assert len(TOKENS) > 100
    # token BPE yang memang dipakai kata kunci SELA
    for t in ("\u2581SE", "LA"):
        assert t in TOKENS


class TestPeriksaBaris:
    def test_baris_sah_kiblat(self):
        assert periksa_baris("\u2581MO S S @MOSS", TOKENS) == (True, "")

    def test_baris_sah_sela(self):
        assert periksa_baris("\u2581SE LA @SELA", TOKENS) == (True, "")

    def test_label_berisi_spasi_ditolak(self):
        # inilah baris yang dulu mematikan aplikasi Linux
        sah, alasan = periksa_baris("\u2581HA I \u2581HA I @Hai Hai", TOKENS)
        assert sah is False
        assert "label" in alasan

    def test_label_spasi_pada_kata_umum_ditolak(self):
        sah, _ = periksa_baris("\u2581SE LA @SELA AI", TOKENS)
        assert sah is False

    def test_token_tidak_dikenal_ditolak(self):
        sah, alasan = periksa_baris("\u2581SE XX @SELA", TOKENS)
        assert sah is False
        assert "XX" in alasan

    def test_label_dua_kata_tanpa_spasi_sah(self):
        assert periksa_baris("\u2581HA I @HaiHai", TOKENS)[0] is True

    def test_baris_kosong_dan_komentar_ditolak(self):
        assert periksa_baris("", TOKENS)[0] is False
        assert periksa_baris("   ", TOKENS)[0] is False
        assert periksa_baris("# catatan", TOKENS)[0] is False

    def test_tanpa_label_ditolak(self):
        assert periksa_baris("\u2581SE LA", TOKENS)[0] is False

    def test_label_kosong_ditolak(self):
        assert periksa_baris("\u2581SE LA @", TOKENS)[0] is False

    def test_label_di_tengah_ditolak(self):
        assert periksa_baris("@SELA \u2581SE LA", TOKENS)[0] is False


class TestSaringKataKunci:
    def test_berkas_kiblat_bersih(self):
        teks = (MODEL_EN / "keywords.txt").read_text(encoding="utf-8")
        hasil = saring_kata_kunci(teks, "\n".join(TOKENS))
        assert isinstance(hasil, HasilSaring)
        assert hasil.bersih
        assert hasil.ada_baris_valid

    def test_baris_rusak_dibuang_tapi_valid_dipertahankan(self):
        teks = "\u2581SE LA @SELA\n\u2581HA I \u2581HA I @Hai Hai\n"
        hasil = saring_kata_kunci(teks, (MODEL_EN / "tokens.txt").read_text(encoding="utf-8"))
        assert hasil.baris_valid == ["\u2581SE LA @SELA"]
        assert len(hasil.baris_rusak) == 1
        assert hasil.bersih is False
        assert hasil.teks_bersih == "\u2581SE LA @SELA\n"

    def test_semua_baris_rusak(self):
        teks = "\u2581HA I \u2581HA I @Hai Hai\n\u2581SE XX @SELA\n"
        hasil = saring_kata_kunci(teks, (MODEL_EN / "tokens.txt").read_text(encoding="utf-8"))
        assert hasil.ada_baris_valid is False
        assert hasil.teks_bersih == ""

    def test_baris_kosong_diabaikan_tanpa_dihitung_rusak(self):
        teks = "\u2581SE LA @SELA\n\n   \n"
        hasil = saring_kata_kunci(teks, (MODEL_EN / "tokens.txt").read_text(encoding="utf-8"))
        assert hasil.bersih is True
        assert hasil.baris_valid == ["\u2581SE LA @SELA"]


class TestBerkasModelNyata:
    def test_keywords_model_en_hanya_sela(self):
        baris = [
            b.strip()
            for b in (MODEL_EN / "keywords.txt").read_text(encoding="utf-8").splitlines()
            if b.strip()
        ]
        assert baris == ["\u2581SE LA @SELA"]

    def test_tidak_ada_berkas_bak_tertinggal(self):
        assert not (MODEL_EN / "keywords.txt.bak").exists()

    def test_berkas_kata_kunci_kiblat_juga_lolos_penyaring(self):
        kiblat = AKAR.parent / "py-xiaozhi-main" / "py-xiaozhi-main" / "models" / "en"
        if not kiblat.exists():  # pragma: no cover - kiblat tidak tersedia
            return
        teks = (kiblat / "keywords.txt").read_text(encoding="utf-8")
        token = muat_token((kiblat / "tokens.txt").read_text(encoding="utf-8"))
        hasil = saring_kata_kunci(teks, "\n".join(token))
        assert hasil.ada_baris_valid
