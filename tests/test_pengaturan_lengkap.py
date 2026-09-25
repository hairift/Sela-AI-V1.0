"""Uji kelengkapan halaman pengaturan (kamera, pintasan, MCP per-tool).

Pengguna meminta halaman pengaturan selengkap py-xiaozhi-main (versi Mandarin),
tetapi 100% Bahasa Indonesia. Tiga bagian yang sebelumnya belum ada:

  * Kamera (CameraTab)
  * Pintasan papan tik (ShortcutsTab)
  * MCP per-tool (McpToolsTab)

Uji ini memastikan data untuk ketiganya benar-benar tersedia di sisi mesin AI
dan bersih dari teks Mandarin.
"""

from __future__ import annotations

from src.mcp.tools.camera.diagnostik import _nama_ramah, uji_kamera
from src.ui.web.server import _daftar_mcp_mati, _ringkas_pintasan

# ---------------------------------------------------------------------------
# Kamera
# ---------------------------------------------------------------------------


def test_nama_kamera_aksara_han_diganti():
    """Nama kamera beraksara Han diganti menjadi 'Kamera <index>'."""
    assert _nama_ramah("摄像头 0", 0, "0") == "Kamera 0"
    assert _nama_ramah("摄像头", 2, "2") == "Kamera 2"


def test_nama_kamera_normal_dipertahankan():
    assert _nama_ramah("HD Webcam C270", 1, "1") == "HD Webcam C270"


def test_nama_kamera_kosong_diberi_nama():
    assert _nama_ramah("", 0, "0") == "Kamera 0"
    assert _nama_ramah("   ", None, "3") == "Kamera 3"


def test_uji_kamera_mengembalikan_dict_aman():
    """Uji kamera tidak boleh melempar walau tidak ada kamera."""
    from src.utils.config_manager import initialize_config, reset_config

    reset_config()
    initialize_config()
    hasil = uji_kamera()
    assert isinstance(hasil, dict)
    assert "ok" in hasil
    if not hasil["ok"]:
        assert "error" in hasil
        # Pesan harus Bahasa Indonesia, bukan aksara Han (mis. bocoran dari
        # pengecualian internal ConfigManager/OpenCV).
        assert not any("\u4e00" <= ch <= "\u9fff" for ch in hasil["error"]), hasil[
            "error"
        ]


# ---------------------------------------------------------------------------
# Pintasan papan tik
# ---------------------------------------------------------------------------


class _ConfigPalsu:
    def __init__(self, data: dict) -> None:
        self._data = data

    def get_config(self, path: str, default=None):
        if path == "SHORTCUTS":
            return self._data
        return default


def test_pintasan_diterjemahkan_ke_indonesia():
    """Keterangan pintasan berbahasa Mandarin diganti Bahasa Indonesia."""
    cfg = _ConfigPalsu(
        {
            "ENABLED": True,
            "MANUAL_PRESS": {
                "modifier": "ctrl",
                "key": "j",
                "description": "按住说话",
            },
            "ABORT": {"modifier": "ctrl", "key": "q", "description": "中断对话"},
        }
    )
    hasil = _ringkas_pintasan(cfg)
    assert len(hasil) == 2
    for baris in hasil:
        assert not any("\u4e00" <= ch <= "\u9fff" for ch in baris["keterangan"]), (
            f"keterangan masih Mandarin: {baris}"
        )
    nama = {b["nama"]: b for b in hasil}
    assert nama["MANUAL_PRESS"]["keterangan"] == "Tahan untuk bicara"
    assert nama["ABORT"]["keterangan"] == "Hentikan percakapan"
    assert nama["MANUAL_PRESS"]["key"] == "j"


def test_pintasan_tanpa_data_aman():
    """Config tanpa SHORTCUTS tidak boleh melempar."""
    assert _ringkas_pintasan(_ConfigPalsu({})) == []
    assert _ringkas_pintasan(_ConfigPalsu({"ENABLED": True})) == []


# ---------------------------------------------------------------------------
# MCP per-tool
# ---------------------------------------------------------------------------


def test_daftar_mcp_mati_membaca_config():
    cfg = _ConfigPalsu({})
    cfg._data = []  # tidak dipakai untuk jalur ini

    class Cfg:
        def get_config(self, path, default=None):
            if path == "MCP_TOOLS.DISABLED":
                return ["music_player.stop", "music_player.stop", " take_photo "]
            return default

    hasil = _daftar_mcp_mati(Cfg())
    # Duplikat dibuang, spasi dipangkas.
    assert hasil == ["music_player.stop", "take_photo"]


def test_katalog_mcp_memuat_kelompok_yang_diharapkan():
    """Katalog tool MCP harus memuat kelompok inti yang ditampilkan di UI."""
    from src.mcp.tool_catalog import builtin_catalog_rows

    baris = builtin_catalog_rows()
    kelompok = {r["group"] for r in baris}
    for wajib in ("kampus", "music", "camera", "weather", "websearch"):
        assert wajib in kelompok, f"kelompok MCP '{wajib}' tidak ada di katalog"

    # Setiap baris punya nama dan label agar bisa ditampilkan.
    for r in baris:
        assert r.get("name")
        assert r.get("label") or r.get("name")


def test_label_kelompok_ui_mencakup_katalog():
    """Setiap kelompok di katalog sebaiknya punya label Indonesia di UI."""
    import json
    import re
    from pathlib import Path

    from src.mcp.tool_catalog import builtin_catalog_rows

    sumber = Path("webui/src/components/Settings.jsx").read_text(encoding="utf-8")
    m = re.search(r"LABEL_KELOMPOK_MCP = \{(.*?)\n\}", sumber, re.S)
    assert m, "LABEL_KELOMPOK_MCP tidak ditemukan di Settings.jsx"
    kunci = set(re.findall(r"(\w+):\s*'", m.group(1)))
    kelompok = {r["group"] for r in builtin_catalog_rows()}
    hilang = kelompok - kunci
    assert not hilang, f"kelompok tanpa label Indonesia: {sorted(hilang)}"
    assert json is not None
