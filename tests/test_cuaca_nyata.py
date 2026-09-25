"""Uji tool cuaca nyata (Open-Meteo) - bukan mock.

Pengguna meragukan keakuratan cuaca karena tool bawaan py-xiaozhi masih MOCK
(25 derajat, kondisi "晴朗" Mandarin, hardcoded). Uji ini memastikan:
  * nama tool tidak bentrok dengan "get_weather" milik server AI;
  * argumen dict dari McpServer ditangani dengan benar;
  * pemanggilan jaringan yang gagal menghasilkan pesan Bahasa Indonesia,
    bukan pengecualian;
  * (bila internet tersedia) data yang dikembalikan benar-benar nyata.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from src.mcp.tools.weather import service
from src.mcp.tools.weather.register import register_weather_tools


class _ServerPalsu:
    def __init__(self) -> None:
        self.tools = []

    def add_tool(self, tool) -> None:
        self.tools.append(tool)


def test_nama_tool_tidak_bentrok():
    """Tidak boleh memakai get_weather/get_forecast (bentrok dengan server AI)."""
    server = _ServerPalsu()
    register_weather_tools(server.add_tool)
    nama = {t.name for t in server.tools}
    assert nama == {"cuaca_sekarang", "prakiraan_cuaca"}
    assert "get_weather" not in nama
    assert "get_forecast" not in nama


def test_deskripsi_tool_bahasa_indonesia():
    """Deskripsi harus Bahasa Indonesia dan memuat pemicu 'WAJIB'.

    Deskripsi Mandarin membuat model tidak memanggil tool untuk permintaan
    berbahasa Indonesia.
    """
    server = _ServerPalsu()
    register_weather_tools(server.add_tool)
    for tool in server.tools:
        deskripsi = tool.description or ""
        assert "WAJIB" in deskripsi, f"{tool.name}: deskripsi tanpa pemicu WAJIB"
        # Tidak boleh ada aksara Han di deskripsi.
        assert not any("\u4e00" <= ch <= "\u9fff" for ch in deskripsi), (
            f"{tool.name}: deskripsi masih memuat aksara Mandarin"
        )


def test_ambil_argumen_dari_dict():
    """McpServer mengirim SATU dict parameter, bukan parameter terpisah."""
    assert service._ambil_argumen({"kota": "Cirebon"}, "kota") == "Cirebon"
    assert service._ambil_argumen({"city": "Bandung"}, "kota") == "Bandung"
    assert service._ambil_argumen({}, "kota", "Cirebon") == "Cirebon"
    assert service._ambil_argumen("Surabaya", "kota") == "Surabaya"


def test_kode_cuaca_terjemahan_indonesia():
    """Semua kode WMO yang dipakai punya keterangan Bahasa Indonesia."""
    for kode in (0, 3, 61, 95, 99):
        assert kode in service._KODE_CUACA
        teks = service._KODE_CUACA[kode]
        assert teks and not any("\u4e00" <= ch <= "\u9fff" for ch in teks)


def test_gagal_jaringan_mengembalikan_pesan_indonesia():
    """Bila jaringan gagal, harus ada pesan jelas - bukan pengecualian."""
    with patch.object(service, "_ambil_json", return_value=None):
        hasil = service.cuaca_sekarang({"kota": "Cirebon"})
    assert isinstance(hasil, str)
    assert hasil.strip()
    assert "Maaf" in hasil or "tidak" in hasil.lower()

    with patch.object(service, "_ambil_json", return_value=None):
        hasil2 = service.prakiraan_cuaca({"kota": "Cirebon", "hari": 3})
    assert isinstance(hasil2, str)
    assert hasil2.strip()


def test_kota_tidak_ditemukan_pesan_jelas():
    """Kota tak dikenal -> pesan Bahasa Indonesia yang bisa ditindaklanjuti."""
    with patch.object(service, "_ambil_json", return_value={"results": []}):
        hasil = service.cuaca_sekarang({"kota": "KotaYangTidakAda123"})
    assert "tidak menemukan" in hasil.lower()
    assert "KotaYangTidakAda123" in hasil


def test_prakiraan_memakai_data_dari_api():
    """Prakiraan harus memakai angka dari respons API, bukan nilai hardcoded."""
    palsu = {
        "daily": {
            "time": ["2026-09-25", "2026-09-26"],
            "weather_code": [3, 61],
            "temperature_2m_max": [33.5, 30.1],
            "temperature_2m_min": [24.0, 23.2],
        }
    }
    lokasi = {"nama": "Cirebon", "wilayah": "", "lintang": -6.7, "bujur": 108.5}
    with patch.object(
        service, "_cari_lokasi", return_value=lokasi
    ), patch.object(service, "_ambil_json", return_value=palsu):
        hasil = service.prakiraan_cuaca({"kota": "Cirebon", "hari": 2})

    assert "33.5" in hasil and "30.1" in hasil
    assert service._KODE_CUACA[3] in hasil
    assert service._KODE_CUACA[61] in hasil


def test_cuaca_sekarang_memakai_data_dari_api():
    """Cuaca sekarang harus memakai angka dari respons API."""
    palsu = {
        "current": {
            "temperature_2m": 31.7,
            "relative_humidity_2m": 62,
            "weather_code": 2,
            "wind_speed_10m": 11.4,
        }
    }
    lokasi = {
        "nama": "Cirebon",
        "wilayah": "Jawa Barat",
        "lintang": -6.7,
        "bujur": 108.5,
    }
    with patch.object(
        service, "_cari_lokasi", return_value=lokasi
    ), patch.object(service, "_ambil_json", return_value=palsu):
        hasil = service.cuaca_sekarang({"kota": "Cirebon"})

    assert "31.7" in hasil
    assert "62" in hasil
    assert service._KODE_CUACA[2] in hasil


def test_data_cuaca_nyata_dari_internet():
    """Uji langsung ke Open-Meteo. Dilewati bila tidak ada internet."""
    hasil = service.cuaca_sekarang({"kota": "Cirebon"})
    if "derajat Celsius" not in hasil:
        pytest.skip(f"Tidak ada sambungan internet ke Open-Meteo: {hasil[:80]}")
    assert "Cirebon" in hasil
    assert "Open-Meteo" in hasil
