"""Pengujian penyaring berkas kata kunci (``keywords.txt``) wake word.

Latar belakang: ``sherpa_onnx.KeywordSpotter`` memvalidasi isi berkas kata
kunci di dalam kode C++ dan memanggil ``exit(-1)`` bila ada baris yang tidak
valid. Proses Python mati seketika sehingga ``try/except`` tidak menolong —
inilah yang dulu membuat aplikasi Linux tertutup sendiri saat start.

Berkas ini mengunci tiga hal:
1. aturan validasi (label terakhir, tanpa spasi, semua token dikenal);
2. perilaku penyaring saat disuapkan berkas nyata milik proyek;
3. pemenggalan token harus SAMA dengan tokenizer model — pemenggalan yang
   "kelihatan benar" tapi berbeda membuat kata kunci tidak pernah cocok
   (wake word tampak tidak berfungsi tanpa pesan apa pun).
"""

from pathlib import Path

import pytest

from src.audio_processing.kata_kunci import (
    HasilSaring,
    muat_token,
    periksa_baris,
    saring_kata_kunci,
)

AKAR = Path(__file__).resolve().parents[1]
MODEL_EN = AKAR / "models" / "en"

TOKENS = muat_token((MODEL_EN / "tokens.txt").read_text(encoding="utf-8"))

# Kata kunci bawaan SELA beserta pemenggalan yang benar dari modelnya.
# Diverifikasi dengan ``sherpa_onnx.text2token`` (lihat uji di bawah).
KATA_KUNCI_BAWAAN = [
    "\u2581SE LA @Sela",
    "\u2581HA I \u2581HA I @HaiHai",
    "\u2581HE LL O \u2581SE LA @HelloSela",
]


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
    def test_keywords_model_en_memuat_tiga_kata_kunci(self):
        baris = [
            b.strip()
            for b in (MODEL_EN / "keywords.txt").read_text(encoding="utf-8").splitlines()
            if b.strip()
        ]
        assert baris == KATA_KUNCI_BAWAAN

    def test_setiap_kata_kunci_bawaan_lolos_penyaring(self):
        for baris in KATA_KUNCI_BAWAAN:
            sah, alasan = periksa_baris(baris, TOKENS)
            assert sah, f"kata kunci bawaan ditolak [{alasan}]: {baris!r}"

    def test_label_kata_kunci_bawaan_tanpa_spasi(self):
        # Label berspasi membuat sherpa-onnx memanggil exit(-1).
        for baris in KATA_KUNCI_BAWAAN:
            label = baris[baris.rindex("@") + 1 :]
            assert " " not in label, f"label memuat spasi: {label!r}"

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


def test_pemenggalan_kata_kunci_sesuai_tokenizer_model():
    """Pemenggalan token harus persis sama dengan tokenizer model.

    Pemenggalan yang "kelihatan benar" tetapi berbeda dari model membuat kata
    kunci tidak pernah cocok — wake word tampak tidak berfungsi tanpa pesan
    apa pun. Contoh nyata: model memenggal "HELLO" menjadi ``▁HE LL O``,
    bukan ``▁HE LO``.

    Uji ini dilewati bila ``sentencepiece`` (dipakai ``text2token``) tidak
    terpasang; daftar di ``KATA_KUNCI_BAWAAN`` tetap mengunci hasilnya.
    """
    sherpa_onnx = pytest.importorskip("sherpa_onnx")
    pytest.importorskip("sentencepiece")

    teks_per_label = {
        "Sela": "SELA",
        "HaiHai": "HAI HAI",
        "HelloSela": "HELLO SELA",
    }

    for baris in KATA_KUNCI_BAWAAN:
        label = baris[baris.rindex("@") + 1 :]
        token_baris = baris[: baris.rindex("@")].strip()
        asli = sherpa_onnx.text2token(
            [teks_per_label[label]],
            str(MODEL_EN / "tokens.txt"),
            "bpe",
            bpe_model=str(MODEL_EN / "bpe.model"),
        )[0]
        assert " ".join(asli) == token_baris, (
            f"pemenggalan '{label}' tidak sama dengan model: "
            f"model={' '.join(asli)!r} berkas={token_baris!r}"
        )


class TestGabungKataKunciBawaan:
    """Kata kunci baru harus sampai ke pengguna lama.

    Berkas kata kunci pengguna dibuat SEKALI saat pemasangan pertama dan tidak
    pernah diperbarui, sehingga tanpa penggabungan ini pengguna lama selamanya
    hanya punya kata kunci dari versi pertama yang mereka pasang.
    """

    @staticmethod
    def _siapkan(tmp_path, monkeypatch, isi: str):
        monkeypatch.setenv("XIAOZHI_KEYWORDS_DIR", str(tmp_path))
        from src.utils import resource_finder as rf

        berkas = tmp_path / "en_keywords.txt"
        berkas.write_text(isi, encoding="utf-8")
        return rf, berkas

    def test_pengguna_lama_mendapat_kata_kunci_baru(self, tmp_path, monkeypatch):
        rf, berkas = self._siapkan(tmp_path, monkeypatch, "\u2581SE LA @SELA\n")
        rf.get_user_keywords_path("en")
        isi = berkas.read_text(encoding="utf-8")
        for baris in KATA_KUNCI_BAWAAN:
            label = baris[baris.rindex("@") + 1 :].lower()
            assert f"@{label}" in isi.lower(), f"{label} tidak sampai ke pengguna lama"

    def test_tidak_menggandakan_kata_kunci_yang_sudah_ada(self, tmp_path, monkeypatch):
        rf, berkas = self._siapkan(tmp_path, monkeypatch, "\u2581SE LA @SELA\n")
        rf.get_user_keywords_path("en")
        isi = berkas.read_text(encoding="utf-8").lower()
        assert isi.count("@sela") == 1, "kata kunci SELA tergandakan"

    def test_kata_kunci_buatan_pengguna_tidak_dihapus(self, tmp_path, monkeypatch):
        rf, berkas = self._siapkan(
            tmp_path, monkeypatch, "\u2581SE LA @SELA\n\u2581HA LO @HaloSela\n"
        )
        rf.get_user_keywords_path("en")
        assert "@HaloSela" in berkas.read_text(encoding="utf-8")

    def test_idempoten(self, tmp_path, monkeypatch):
        rf, berkas = self._siapkan(tmp_path, monkeypatch, "\u2581SE LA @SELA\n")
        rf.get_user_keywords_path("en")
        sekali = berkas.read_text(encoding="utf-8")
        rf.get_user_keywords_path("en")
        assert berkas.read_text(encoding="utf-8") == sekali

    def test_hasil_gabungan_tetap_lolos_penyaring(self, tmp_path, monkeypatch):
        rf, berkas = self._siapkan(tmp_path, monkeypatch, "\u2581SE LA @SELA\n")
        rf.get_user_keywords_path("en")
        hasil = saring_kata_kunci(
            berkas.read_text(encoding="utf-8"),
            (MODEL_EN / "tokens.txt").read_text(encoding="utf-8"),
        )
        assert hasil.bersih, f"baris rusak setelah digabung: {hasil.baris_rusak}"

    def test_pengguna_baru_mendapat_seluruh_daftar(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XIAOZHI_KEYWORDS_DIR", str(tmp_path))
        from src.utils import resource_finder as rf

        berkas = rf.get_user_keywords_path("en")
        assert berkas.exists()
        baris = [b.strip() for b in berkas.read_text(encoding="utf-8").splitlines() if b.strip()]
        assert baris == KATA_KUNCI_BAWAAN
