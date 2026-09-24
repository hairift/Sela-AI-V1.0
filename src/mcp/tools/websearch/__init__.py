"""Tool MCP pencarian web real-time (gratis, tanpa API key).

Menjawab pertanyaan yang jawabannya tidak ada di data kampus dan berubah
seiring waktu: berita terbaru, tokoh publik, cuaca, harga, jadwal.

- ``register_websearch_tools``: daftarkan tool ke McpServer.
- ``cari_web``: gabungan Wikipedia + Wikidata + DuckDuckGo.
"""

from .register import register_websearch_tools
from .service import cari_duckduckgo, cari_jabatan, cari_web, cari_wikipedia, perlu_cari_web

__all__ = [
    "register_websearch_tools",
    "cari_web",
    "cari_wikipedia",
    "cari_jabatan",
    "cari_duckduckgo",
    "perlu_cari_web",
]
