"""Registrasi tool MCP pencarian web real-time."""

from __future__ import annotations

from collections.abc import Callable

from src.logging import get_logger
from src.mcp.tooling import McpTool, Property, PropertyList, PropertyType

from .service import cari_web, perlu_cari_web

logger = get_logger()


def register_websearch_tools(add_tool: Callable[[McpTool], None]) -> None:
    """Daftarkan tool pencarian web ke McpServer."""

    tools: list[McpTool] = [
        McpTool(
            "cari_web",
            (
                "Cari informasi TERKINI di internet. Pakai tool ini untuk hal "
                "yang berubah seiring waktu dan tidak ada di data kampus: berita "
                "terbaru, profil atau jabatan tokoh publik, cuaca, harga, kurs, "
                "jadwal, hasil pertandingan, atau peristiwa yang sedang terjadi. "
                "Jangan pakai untuk pertanyaan tentang UCIC - untuk itu gunakan "
                "cari_info_kampus. Parameter: kueri - pertanyaan pengguna apa adanya."
            ),
            PropertyList([Property("kueri", PropertyType.STRING)]),
            cari_web,
        ),
    ]

    for tool in tools:
        add_tool(tool)
    logger.info("Terdaftar %d tool MCP pencarian web", len(tools))
