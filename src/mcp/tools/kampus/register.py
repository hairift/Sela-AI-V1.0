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
                "Cari informasi resmi tentang Universitas Catur Insan Cendekia "
                "(UCIC): biaya kuliah, program studi, pendaftaran, syarat masuk, "
                "beasiswa, dosen, fasilitas, jadwal, akreditasi, dan kontak. "
                "Panggil tool ini SETIAP KALI pengguna bertanya tentang UCIC agar "
                "jawaban berasal dari dokumen resmi dan tidak mengarang. "
                "Parameter: pertanyaan - pertanyaan pengguna apa adanya."
            ),
            PropertyList([Property("pertanyaan", PropertyType.STRING)]),
            cari_info_kampus,
        ),
        McpTool(
            "info_kampus",
            (
                "Tampilkan ringkasan basis pengetahuan kampus: jumlah dokumen dan "
                "kategori yang tersedia. Berguna untuk memastikan data kampus siap."
            ),
            PropertyList([]),
            info_kampus,
        ),
    ]

    for tool in tools:
        add_tool(tool)
    logger.info("Terdaftar %d tool MCP pengetahuan kampus UCIC", len(tools))
