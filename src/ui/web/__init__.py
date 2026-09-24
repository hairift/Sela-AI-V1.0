"""Antarmuka web SELA (mode UI `web`).

Modul ini menambahkan antarmuka berbasis peramban di atas mesin AI py-xiaozhi
tanpa menyentuh arsitektur intinya. Semua fungsi lama (QML/CLI/TUI/GPIO) tetap
tersedia; mode `web` hanyalah ViewPort tambahan.
"""

from src.ui.web.manager import WebViewManager

__all__ = ["WebViewManager"]
