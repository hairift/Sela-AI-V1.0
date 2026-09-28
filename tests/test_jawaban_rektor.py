"""Uji jawaban data kampus: rektor pasti, dan pencipta SELA.

Latar masalah nyata (laporan pengguna, v1.0.15):

Pengguna bertanya *"Siapa Rektor Universitas Katur Insan Candikia?"* (nama
kampus salah ketik). Jawaban SELA:

> Di Pedoman Akademik 2020, Rektor UCIC tercatat Dr. Chandra Lukita, MM. Tapi
> data itu dari tahun 2020, jadi jabatan rektor terbaru sebaiknya dikonfirmasi
> langsung ke kampus.

Dua cacat sekaligus:

1. Pertanyaan rektor dijawab dari dokumen **2020** (``pedoman_pimpinan_ucic_2020``)
   yang isinya memuat kalimat "*Posisi pimpinan terbaru perlu dikonfirmasi ke
   kampus.*" - padahal ada dokumen ``rektor`` yang khusus membahas hal itu.
   Penyebabnya: dokumen 2020 itu juga memuat kata "rektor" di kata kuncinya,
   sehingga ikut lolos gerbang cakupan dan isinya yang memuat sanggahan
   "perlu dikonfirmasi" terbawa ke jawaban.
2. Model lalu menambahkan sanggahannya sendiri.

Perbaikan: dokumen ``rektor`` diberi kata kunci yang lebih tegas (termasuk
ejaan lengkap nama universitas), dan ketiga dokumen pimpinan tidak lagi memuat
kalimat "perlu dikonfirmasi". Uji ini mengunci keduanya.
"""

import pytest


@pytest.fixture(scope="module")
def indeks():
    from src.mcp.tools.kampus.rag import LexicalIndex, muat_dokumen

    dokumen = muat_dokumen()
    assert dokumen, "dataset kampus tidak termuat - periksa src/data/ucic_dataset.json"
    return LexicalIndex(dokumen), dokumen


# ---------------------------------------------------------------------------
# 1. Pertanyaan rektor selalu jatuh ke dokumen khusus rektor
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "pertanyaan",
    [
        # Persis pertanyaan pengguna, termasuk dua salah ketik nama kampus.
        "Siapa Rektor Universitas Katur Insan Candikia?",
        "Siapa rektor UCIC?",
        "siapa rektor ucic",
        "rektor ucic siapa",
        "siapa rektor universitas catur insan cendekia",
    ],
)
def test_rektor_menang_di_urutan_pertama(indeks, pertanyaan):
    """Dokumen ``rektor`` harus peringkat 1, bukan dokumen pimpinan 2020."""
    idx, _ = indeks
    hasil = idx.cari(pertanyaan, top_k=3)
    assert hasil, f"tidak ada dokumen cocok untuk {pertanyaan!r}"
    teratas = hasil[0]["dokumen"].get("id")
    assert teratas == "rektor", (
        f"pertanyaan {pertanyaan!r} dijawab dari dokumen {teratas!r}; "
        f"harus dari 'rektor'. Urutan: "
        f"{[h['dokumen'].get('id') for h in hasil]}"
    )


def test_dokumen_2020_tidak_mengalahkan_dokumen_rektor(indeks):
    """Dokumen Pedoman Akademik 2020 harus kalah jelas dari dokumen rektor."""
    idx, _ = indeks
    hasil = idx.cari("Siapa Rektor Universitas Katur Insan Candikia?", top_k=5)
    skor = {h["dokumen"].get("id"): h["skor"] for h in hasil}
    assert "rektor" in skor, f"dokumen rektor tidak muncul; hasil: {list(skor)}"
    if "pedoman_pimpinan_ucic_2020" in skor:
        assert skor["rektor"] > skor["pedoman_pimpinan_ucic_2020"], (
            "dokumen rektor harus lebih tinggi daripada pedoman 2020; "
            f"skor: {skor}"
        )


# ---------------------------------------------------------------------------
# 2. Tidak ada lagi kalimat sanggahan yang terbawa ke jawaban
# ---------------------------------------------------------------------------


def test_dokumen_rektor_tidak_memuat_sanggahan():
    """Isi dokumen rektor harus menyatakan nama beliau tanpa ragu."""
    from src.mcp.tools.kampus.rag import muat_dokumen

    dokumen = {d.get("id"): d for d in muat_dokumen()}
    isi = (dokumen["rektor"].get("content") or "").lower()

    assert "chandra lukita" in isi, "nama rektor hilang dari dokumen"
    for frasa in (
        "perlu dikonfirmasi",
        "dikonfirmasi ke kampus",
        "sebaiknya dikonfirmasi",
        "data itu dari tahun",
        "terbaru perlu",
    ):
        assert frasa not in isi, (
            f"dokumen rektor masih memuat sanggahan {frasa!r} - bila ini "
            "muncul di jawaban, pengguna menganggap SELA tidak yakin"
        )


def test_tidak_ada_dokumen_pimpinan_yang_menyuruh_konfirmasi(indeks):
    """Dokumen apa pun yang membahas rektor tidak boleh menyuruh konfirmasi.

    Kalimat sanggahan hanya boleh muncul pada hal yang memang berubah
    (mis. jadwal seleksi), bukan pada jabatan rektor.
    """
    _, dokumen = indeks
    for d in dokumen:
        kunci = " ".join(d.get("keywords") or []).lower()
        judul = (d.get("title") or "").lower()
        isi = (d.get("content") or "").lower()
        # Dokumen yang memang tentang rektor/pimpinan.
        if not ("rektor" in kunci or "rektor" in judul):
            continue
        for frasa in ("perlu dikonfirmasi ke kampus", "dikonfirmasi ke pihak kampus"):
            assert frasa not in isi, (
                f"dokumen {d.get('id')!r} masih menyuruh konfirmasi: {frasa!r}"
            )


# ---------------------------------------------------------------------------
# 3. Pencipta SELA
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "pertanyaan",
    [
        "siapa yang membuat kamu",
        "siapa penciptamu",
        "siapa pembuat SELA",
        "siapa yang menciptakan kamu",
        "siapa pengembang kamu",
    ],
)
def test_pencipta_ditemukan(indeks, pertanyaan):
    """Pertanyaan tentang pencipta dijawab dari dokumen ``tentang_sela``."""
    idx, _ = indeks
    hasil = idx.cari(pertanyaan, top_k=3)
    assert hasil, f"tidak ada dokumen cocok untuk {pertanyaan!r}"
    assert hasil[0]["dokumen"].get("id") == "tentang_sela", (
        f"pertanyaan {pertanyaan!r} tidak jatuh ke tentang_sela; urutan: "
        f"{[h['dokumen'].get('id') for h in hasil]}"
    )


def test_nama_pencipta_tercatat(indeks):
    """Nama pencipta harus tertulis lengkap di dokumen."""
    _, dokumen = indeks
    isi = next(
        (d.get("content") or "") for d in dokumen if d.get("id") == "tentang_sela"
    )
    assert "Muhammad Arif Triyana" in isi, (
        "nama pencipta 'Muhammad Arif Triyana' tidak ada di dokumen tentang_sela"
    )
    assert "mahasiswa jenius" in isi.lower(), (
        "keterangan 'mahasiswa jenius' tidak ada di dokumen tentang_sela"
    )
