"""Tool MCP: pengetahuan kampus UCIC (RAG anti-halusinasi).

Membuat SELA dapat menjawab pertanyaan seputar UCIC (biaya, jurusan, pendaftaran,
dosen, fasilitas, jadwal, beasiswa) **berdasarkan dokumen resmi** yang tersimpan
di ``src/data/ucic_dataset.json`` - bukan dari karangan model bahasa.

Bila dokumen tidak memuat jawabannya, tool mengembalikan pesan jujur beserta
kontak yang bisa dihubungi, sehingga SELA tidak berhalusinasi.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.logging import get_logger

from .rag import LexicalIndex, muat_dokumen

logger = get_logger()

# Kontak resmi yang diberikan bila informasi tidak ditemukan di dokumen.
KONTAK = "Admin PMB UCIC (WhatsApp 0812 1670 0519) atau pmb.cic.ac.id"


def _ambil_argumen(args: Any, nama: str) -> str:
    """Ambil satu argumen teks dari data yang dikirim McpServer.

    McpServer memanggil handler dengan SATU argumen berupa dict parameter
    (lihat McpTool.call -> ``self.callback(parsed_args)``), bukan dengan
    parameter terpisah. Handler yang ditulis sebagai ``def f(pertanyaan)``
    akan menerima dict itu sebagai `pertanyaan`, lalu gagal saat di-``strip``.
    Fungsi ini menormalkan kedua bentuk agar aman.
    """
    if isinstance(args, dict):
        nilai = args.get(nama)
        if nilai is None:
            # Terima juga nama lain yang lazim dipakai model.
            for cadangan in ("q", "query", "text", "teks", "pertanyaan"):
                if args.get(cadangan) is not None:
                    nilai = args[cadangan]
                    break
        return str(nilai or "").strip()
    return str(args or "").strip()

_index: Optional[LexicalIndex] = None
_dokumen: List[Dict[str, Any]] = []


def _pastikan_index() -> Optional[LexicalIndex]:
    """Bangun indeks sekali saja, lalu pakai ulang (singleton)."""
    global _index, _dokumen
    if _index is not None:
        return _index

    _dokumen = muat_dokumen()
    if not _dokumen:
        logger.warning("Tool kampus: dataset tidak ditemukan atau kosong")
        return None

    try:
        _index = LexicalIndex(_dokumen)
        logger.info(
            "Tool kampus: indeks siap - %d dokumen, %d kosakata",
            _index.n,
            len(_index._df),
        )
    except Exception as e:
        logger.error(f"Tool kampus: gagal membangun indeks: {e}", exc_info=True)
        _index = None
    return _index


def _format_konteks(kandidat: List[Dict[str, Any]]) -> str:
    """Susun konteks untuk dibaca model, satu dokumen per blok."""
    bagian: List[str] = []
    for i, k in enumerate(kandidat, 1):
        dok = k["dokumen"]
        judul = dok.get("title") or dok.get("judul") or dok.get("id") or "Informasi UCIC"
        kategori = dok.get("category") or dok.get("kategori") or ""
        isi = dok.get("content") or dok.get("konten") or dok.get("teks") or ""
        kepala = f"[DOKUMEN {i}] {judul}"
        if kategori:
            kepala += f" (Kategori: {kategori})"
        bagian.append(f"{kepala}\n{isi}")
    return "\n\n".join(bagian)


def cari_info_kampus(args: Any = None) -> str:
    """Cari informasi kampus UCIC dari basis pengetahuan resmi.

    Args:
        args: Dict parameter dari McpServer, berisi ``pertanyaan``.

    Returns:
        Konteks dokumen resmi untuk dijawab SELA, atau pesan jujur bila tidak ada
        dokumen yang benar-benar cocok.
    """
    pertanyaan = _ambil_argumen(args, "pertanyaan")
    if not pertanyaan:
        return (
            "Pertanyaan kosong. Mintalah pengguna menyebutkan topik kampus yang "
            "ingin ditanyakan."
        )

    index = _pastikan_index()
    if index is None:
        return (
            "Basis pengetahuan kampus belum tersedia. "
            f"Arahkan pengguna menghubungi {KONTAK}."
        )

    try:
        kandidat = index.cari(pertanyaan, top_k=4)
    except Exception as e:
        logger.error(f"Tool kampus: pencarian gagal: {e}", exc_info=True)
        kandidat = []

    if not kandidat:
        return (
            "Informasi itu belum tercatat di basis pengetahuan resmi UCIC. "
            "Jawab dengan jujur bahwa datanya belum tersedia, jangan menebak, "
            f"lalu arahkan pengguna menghubungi {KONTAK}."
        )

    konteks = _format_konteks(kandidat)
    return (
        "Jawab HANYA berdasarkan dokumen resmi UCIC di bawah ini. "
        "Jangan menambah fakta yang tidak tertulis di sana.\n\n"
        f"{konteks}"
    )


def info_kampus(args: Any = None) -> str:
    """Ringkasan basis pengetahuan kampus (jumlah dokumen & kategori)."""
    index = _pastikan_index()
    if index is None:
        return "Basis pengetahuan kampus belum tersedia."

    kategori: Dict[str, int] = {}
    for dok in _dokumen:
        nama = (dok.get("category") or dok.get("kategori") or "lainnya").strip()
        kategori[nama] = kategori.get(nama, 0) + 1

    rincian = ", ".join(f"{k} ({v})" for k, v in sorted(kategori.items()))
    return (
        f"Basis pengetahuan UCIC memuat {index.n} dokumen resmi. "
        f"Kategori: {rincian}."
    )
