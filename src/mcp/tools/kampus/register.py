"""Registrasi tool MCP pengetahuan kampus UCIC."""

from __future__ import annotations

from collections.abc import Callable

from src.logging import get_logger
from src.mcp.tooling import McpTool, Property, PropertyList, PropertyType

from .service import cari_info_kampus, info_kampus

logger = get_logger()


def register_kampus_tools(add_tool: Callable[[McpTool], None]) -> None:
    """Daftarkan tool pengetahuan kampus ke McpServer."""

    tools: list[McpTool] = [
        McpTool(
            "cari_info_kampus",
            (
                "WAJIB dipanggil setiap kali pengguna menanyakan Universitas Catur "
                "Insan Cendekia. Kampus ini juga disebut UCIC, UIC, CIC, UCIC "
                "Cirebon, atau 'kampus'. Panggil tool ini untuk SEMUA pertanyaan "
                "tentang kampus tersebut, antara lain: biaya kuliah, program "
                "studi/jurusan/fakultas, cara dan syarat pendaftaran, beasiswa, "
                "dosen, fasilitas, jadwal, akreditasi, alamat, dan kontak. "
                "Jawaban HARUS berasal dari dokumen resmi yang dikembalikan tool "
                "ini supaya tidak mengarang. Panggil lebih dulu, jangan menjawab "
                "dari ingatan sendiri. "
                "Parameter: pertanyaan - pertanyaan pengguna apa adanya."
            ),
            PropertyList([Property("pertanyaan", PropertyType.STRING)]),
            cari_info_kampus,
        ),
        McpTool(
            "info_kampus",
            (
                "Tampilkan ringkasan basis pengetahuan kampus UCIC: jumlah dokumen "
                "dan kategori yang tersedia. Berguna untuk memastikan data kampus "
                "siap dipakai."
            ),
            PropertyList([]),
            info_kampus,
        ),
    ]

    for tool in tools:
        add_tool(tool)
    logger.info("Terdaftar %d tool MCP pengetahuan kampus UCIC", len(tools))
