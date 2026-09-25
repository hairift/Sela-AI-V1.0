"""Uji pemilihan lagu yang relevan (bukan kompilasi remix).

Pengguna mengeluh lagu yang diputar tidak sesuai permintaan. Penyebabnya:
hasil pencarian mengembalikan kompilasi remix lebih dulu walau nama penyanyi
ada di judulnya (mis. "Hitam Putih - REMIX ... Sheila On 7 ...").

Diuji dua jalur:
  1. Jalur YouTube  -> skor_relevansi (fungsi penilaian).
  2. Jalur Kuwo     -> _pilih_terbaik (pemilihan kandidat), karena jalur ini
     yang dipakai lebih dulu dan dulu selalu mengambil hasil PERTAMA.
"""

from __future__ import annotations

from src.mcp.tools.music.online_search import _judul_lengkap, _pilih_terbaik
from src.mcp.tools.music.youtube import skor_relevansi


def test_lagu_asli_lebih_tinggi_daripada_kompilasi_remix():
    kueri = "Sheila on 7"
    asli = skor_relevansi("Sheila On 7 - Dan", kueri, 260)
    remix = skor_relevansi(
        "Hitam Putih - REMIX MUSIC&Aulora Band&Sheila On 7&ST12 (Hitam Putih)",
        kueri,
        300,
    )
    assert asli > remix, f"lagu asli ({asli}) harus mengalahkan remix ({remix})"


def test_karaoke_dan_cover_dihukum():
    kueri = "Sheila on 7"
    asli = skor_relevansi("Sheila On 7 - Bila Kau Tak Disampingku", kueri, 257)
    karaoke = skor_relevansi(
        "Sheila On 7 - Bila Kau Tak Disampingku (Karaoke Version)", kueri, 257
    )
    cover = skor_relevansi("Sheila On 7 - Dan (Cover by Someone)", kueri, 250)
    assert asli > karaoke
    assert asli > cover


def test_judul_tanpa_kata_kunci_dihukum():
    kueri = "Sheila on 7"
    cocok = skor_relevansi("Sheila On 7 - Dan", kueri, 260)
    tak_cocok = skor_relevansi("Lagu Mandarin Populer 2024", kueri, 260)
    assert cocok > tak_cocok


def test_judul_kosong_skor_sangat_rendah():
    assert skor_relevansi("", "Sheila on 7") < -50


def test_kompilasi_sangat_panjang_dihukum():
    kueri = "Sheila on 7"
    panjang = skor_relevansi(
        "Kumpulan Lagu Sheila On 7 Full Album Terbaik Sepanjang Masa Nonstop "
        "Tanpa Iklan Untuk Perjalanan Jauh",
        kueri,
        300,
    )
    pendek = skor_relevansi("Sheila On 7 - Dan", kueri, 260)
    assert pendek > panjang


def test_durasi_tidak_wajar_dihukum():
    kueri = "Sheila on 7"
    wajar = skor_relevansi("Sheila On 7 - Dan", kueri, 260)
    sangat_panjang = skor_relevansi("Sheila On 7 - Dan", kueri, 3600)
    assert wajar > sangat_panjang


def test_kueri_tanpa_kata_kunci_bermakna_tetap_memberi_skor():
    """Kueri seperti 'lagu' saja tidak boleh membuat semua hasil dihukum berat."""
    skor = skor_relevansi("Beberapa Lagu Bagus", "lagu", 200)
    assert skor > 0


# --------------------------------------------------------------------------
# Jalur Kuwo (dipakai lebih dulu sebelum YouTube)
# --------------------------------------------------------------------------


def _kuwo_remix_dulu() -> list[dict]:
    """Hasil Kuwo tiruan: kompilasi remix di urutan pertama."""
    return [
        {
            "MUSICRID": "MUSIC_1",
            "SONGNAME": (
                "Hitam Putih - REMIX MUSIC&Aulora Band&Sheila On 7&ST12"
                "&Zaski Gotik&Cita Citata (Hitam Putih)"
            ),
            "ARTIST": "Various Artists",
            "ALBUM": "Hitam Putih",
            "DURATION": "245",
        },
        {
            "MUSICRID": "MUSIC_2",
            "SONGNAME": "Dan",
            "ARTIST": "Sheila On 7",
            "ALBUM": "Sheila On 7",
            "DURATION": "260",
        },
    ]


def test_kuwo_memilih_lagu_asli_bukan_hasil_pertama():
    """Dulu `results[0]` dipakai apa adanya; kini kandidat terbaik dipilih."""
    hasil = _kuwo_remix_dulu()
    pilih = _pilih_terbaik(hasil, "putar lagu Sheila on 7")
    assert pilih is not None
    assert pilih["MUSICRID"] == "MUSIC_2", (
        "Kuwo harus memilih lagu asli, bukan kompilasi remix di urutan pertama"
    )


def test_kuwo_melewati_hasil_tanpa_musicrid():
    """Hasil tanpa MUSICRID tidak bisa diputar, jadi harus dilewati."""
    hasil = [
        {"MUSICRID": "", "SONGNAME": "Dan", "ARTIST": "Sheila On 7"},
        {"MUSICRID": "MUSIC_9", "SONGNAME": "Dan", "ARTIST": "Sheila On 7",
         "DURATION": "260"},
    ]
    pilih = _pilih_terbaik(hasil, "Sheila on 7")
    assert pilih is not None
    assert pilih["MUSICRID"] == "MUSIC_9"


def test_kuwo_kembalikan_none_bila_tidak_ada_kandidat_layak():
    assert _pilih_terbaik([], "Sheila on 7") is None
    assert _pilih_terbaik([{"SONGNAME": "x"}], "Sheila on 7") is None


def test_judul_lengkap_menggabungkan_artis_dan_album():
    assert (
        _judul_lengkap(
            {"SONGNAME": "Dan", "ARTIST": "Sheila On 7", "ALBUM": "Sheila On 7"}
        )
        == "Dan - Sheila On 7 (Sheila On 7)"
    )
    # Tanpa artis maupun album -> hanya judul.
    assert _judul_lengkap({"SONGNAME": "Dan"}) == "Dan"
    # Artis saja tetap dipakai.
    assert _judul_lengkap({"ARTIST": "Sheila On 7"}) == "Sheila On 7"
    assert _judul_lengkap({}) == ""


def test_kuwo_hasil_bukan_dict_tidak_membuat_gagal():
    """Bentuk hasil yang aneh (bukan dict) harus dilewati, bukan melempar."""
    hasil = ["bukan dict", None, {"MUSICRID": "MUSIC_3", "SONGNAME": "Dan",
                                  "ARTIST": "Sheila On 7", "DURATION": "260"}]
    pilih = _pilih_terbaik(hasil, "Sheila on 7")
    assert pilih is not None
    assert pilih["MUSICRID"] == "MUSIC_3"
