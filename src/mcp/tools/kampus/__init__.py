"""Tool MCP pengetahuan kampus UCIC (RAG anti-halusinasi).

Modul ini membuat SELA dapat menjawab pertanyaan seputar UCIC berdasarkan
dokumen resmi yang tersimpan di ``src/data/ucic_dataset.json``.

- ``register_kampus_tools``: daftarkan tool ke McpServer.
- ``LexicalIndex``: mesin pencarian BM25 + gerbang cakupan IDF.
"""

from .rag import LexicalIndex, muat_dokumen, temukan_dataset
from .register import register_kampus_tools
from .service import KONTAK, cari_info_kampus, info_kampus

__all__ = [
    "LexicalIndex",
    "muat_dokumen",
    "temukan_dataset",
    "register_kampus_tools",
    "cari_info_kampus",
    "info_kampus",
    "KONTAK",
]
