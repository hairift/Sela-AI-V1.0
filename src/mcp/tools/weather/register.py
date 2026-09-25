"""Registrasi tool cuaca SELA (data nyata Open-Meteo, Bahasa Indonesia).

Catatan penting soal nama tool: versi mock py-xiaozhi memakai nama
``get_weather`` yang BENTROK dengan tool ``get_weather`` milik server AI.
Bentrok nama membuat server menolak SELURUH sesi
("Duplicate tool names: get_weather") sehingga SELA tidak menjawab sama sekali.
Karena itu tool di sini memakai nama berbahasa Indonesia yang unik:
``cuaca_sekarang`` dan ``prakiraan_cuaca``.

Deskripsi wajib Bahasa Indonesia - deskripsi berbahasa Mandarin membuat model
tidak memanggil tool untuk permintaan berbahasa Indonesia.
"""

from __future__ import annotations

from collections.abc import Callable

from src.logging import get_logger
from src.mcp.tooling import McpTool, Property, PropertyList, PropertyType

from .service import cuaca_sekarang, prakiraan_cuaca

logger = get_logger()


def register_weather_tools(add_tool: Callable[[McpTool], None]) -> None:
    """Daftarkan tool cuaca nyata ke McpServer."""

    tools: list[McpTool] = [
        McpTool(
            "cuaca_sekarang",
            (
                "WAJIB dipanggil setiap kali pengguna menanyakan CUACA SAAT INI "
                "di suatu tempat, misalnya 'bagaimana cuaca di Cirebon', "
                "'apakah hari ini hujan', 'berapa suhu sekarang', "
                "'cuaca hari ini di Jakarta'. Jangan mengarang data cuaca - "
                "selalu panggil tool ini karena datanya diambil langsung dari "
                "layanan cuaca resmi (Open-Meteo). "
                "Parameter: kota - nama kota (mis. Cirebon, Jakarta, Bandung)."
            ),
            PropertyList(
                [Property("kota", PropertyType.STRING, default_value="Cirebon")]
            ),
            cuaca_sekarang,
        ),
        McpTool(
            "prakiraan_cuaca",
            (
                "WAJIB dipanggil setiap kali pengguna menanyakan PRAKIRAAN CUACA "
                "BEBERAPA HARI ke depan, misalnya 'prakiraan cuaca besok', "
                "'cuaca seminggu ke depan di Bandung', 'apakah besok hujan'. "
                "Data diambil dari layanan cuaca resmi (Open-Meteo). "
                "Parameter: kota - nama kota, hari - jumlah hari (1-7)."
            ),
            PropertyList(
                [
                    Property("kota", PropertyType.STRING, default_value="Cirebon"),
                    Property(
                        "hari",
                        PropertyType.INTEGER,
                        default_value=3,
                        min_value=1,
                        max_value=7,
                    ),
                ]
            ),
            prakiraan_cuaca,
        ),
    ]

    for tool in tools:
        add_tool(tool)
    logger.info(
        "Terdaftar %d tool cuaca nyata (Open-Meteo, Bahasa Indonesia)",
        len(tools),
    )
