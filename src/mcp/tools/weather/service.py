"""Cuaca nyata (bukan mock) memakai Open-Meteo - gratis, tanpa API key.

Latar belakang: tool cuaca bawaan py-xiaozhi masih MOCK. Datanya hardcoded
(25 derajat, kondisi "晴朗" berbahasa Mandarin, ada TODO memanggil API asli),
sehingga SELA bisa menyebut cuaca yang salah. Modul ini menggantinya dengan
data sungguhan.

Dua langkah:
  1. Geocoding nama kota -> lintang/bujur (Open-Meteo Geocoding API).
  2. Cuaca sekarang / prakiraan dari koordinat (Open-Meteo Forecast API).

Nama tool sengaja berbahasa Indonesia (``cuaca_sekarang`` / ``prakiraan_cuaca``)
supaya TIDAK bentrok dengan ``get_weather`` milik server AI - bentrok nama
membuat server menolak seluruh sesi ("Duplicate tool names").

Hanya memakai pustaka standar Python (urllib), sehingga tetap jalan di
Raspberry Pi dan di paket hasil build tanpa dependensi tambahan.
"""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

from src.logging import get_logger

logger = get_logger()

_GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
_CUACA_URL = "https://api.open-meteo.com/v1/forecast"

_HEADERS = {
    "User-Agent": "SELA-AI/1.0 (asisten kampus UCIC)",
    "Accept": "application/json",
}

# Kode cuaca WMO (dipakai Open-Meteo) -> keterangan Bahasa Indonesia.
_KODE_CUACA = {
    0: "Cerah",
    1: "Sebagian besar cerah",
    2: "Berawan sebagian",
    3: "Mendung",
    45: "Berkabut",
    48: "Kabut berembun",
    51: "Gerimis ringan",
    53: "Gerimis sedang",
    55: "Gerimis lebat",
    56: "Gerimis beku ringan",
    57: "Gerimis beku lebat",
    61: "Hujan ringan",
    63: "Hujan sedang",
    65: "Hujan lebat",
    66: "Hujan beku ringan",
    67: "Hujan beku lebat",
    71: "Salju ringan",
    73: "Salju sedang",
    75: "Salju lebat",
    77: "Butiran salju",
    80: "Hujan lokal ringan",
    81: "Hujan lokal sedang",
    82: "Hujan lokal sangat lebat",
    85: "Hujan salju ringan",
    86: "Hujan salju lebat",
    95: "Hujan petir",
    96: "Hujan petir dengan hujan es ringan",
    99: "Hujan petir dengan hujan es lebat",
}


def _ambil_json(url: str, timeout: int = 12) -> Optional[dict]:
    """Ambil JSON dari URL; None bila gagal (termasuk masalah sertifikat)."""
    req = urllib.request.Request(url, headers=_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.URLError as galat:
        # Sebagian jaringan kampus memakai sertifikat internal.
        if isinstance(getattr(galat, "reason", None), ssl.SSLCertVerificationError):
            try:
                with urllib.request.urlopen(
                    req, timeout=timeout, context=ssl._create_unverified_context()
                ) as resp:
                    return json.loads(resp.read().decode("utf-8", errors="replace"))
            except Exception as e:
                logger.debug(f"Cuaca: fetch tanpa verifikasi gagal: {e}")
                return None
        logger.debug(f"Cuaca: fetch gagal {url}: {galat}")
        return None
    except Exception as e:
        logger.debug(f"Cuaca: fetch gagal {url}: {e}")
        return None


def _cari_lokasi(kota: str) -> Optional[dict]:
    """Ubah nama kota menjadi {nama, negara, wilayah, lintang, bujur}."""
    if not kota or not kota.strip():
        return None
    kueri = urllib.parse.urlencode(
        {"name": kota.strip(), "count": 1, "language": "id", "format": "json"}
    )
    data = _ambil_json(f"{_GEO_URL}?{kueri}")
    if not data:
        return None
    hasil = data.get("results") or []
    if not hasil:
        return None
    baris = hasil[0]
    try:
        return {
            "nama": baris.get("name") or kota,
            "negara": baris.get("country") or "",
            "wilayah": baris.get("admin1") or "",
            "lintang": float(baris["latitude"]),
            "bujur": float(baris["longitude"]),
        }
    except (KeyError, TypeError, ValueError):
        return None


def _ambil_argumen(args: Any, nama: str, bawaan: Any = "") -> Any:
    """Ambil argumen dari data yang dikirim McpServer.

    McpServer memanggil handler dengan SATU argumen berupa dict parameter
    (lihat McpTool.call -> ``self.callback(parsed_args)``), bukan parameter
    terpisah. Handler yang ditulis ``def f(kota)`` akan menerima dict itu
    sebagai `kota`, lalu gagal saat dipakai sebagai teks.
    """
    if isinstance(args, dict):
        nilai = args.get(nama)
        if nilai is None:
            for cadangan in ("kota", "city", "q", "query", "lokasi", "teks"):
                if args.get(cadangan) is not None:
                    nilai = args.get(cadangan)
                    break
        if nilai is None:
            return bawaan
        return nilai
    if isinstance(args, str) and args.strip():
        return args
    return bawaan


def cuaca_sekarang(args: Any) -> str:
    """Cuaca saat ini untuk sebuah kota (data nyata dari Open-Meteo)."""
    kota = str(_ambil_argumen(args, "kota", "Cirebon") or "Cirebon").strip()
    lokasi = _cari_lokasi(kota)
    if lokasi is None:
        return (
            f"Maaf, saya tidak menemukan kota bernama '{kota}'. "
            "Coba sebutkan nama kota yang lebih lengkap, misalnya "
            "'Cirebon' atau 'Jakarta'."
        )

    kueri = urllib.parse.urlencode(
        {
            "latitude": lokasi["lintang"],
            "longitude": lokasi["bujur"],
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
            "timezone": "auto",
        }
    )
    data = _ambil_json(f"{_CUACA_URL}?{kueri}")
    if not data or "current" not in data:
        return (
            "Maaf, data cuaca sedang tidak bisa diambil. "
            "Periksa sambungan internet lalu coba lagi."
        )

    cur = data["current"]
    kode = int(cur.get("weather_code", -1))
    kondisi = _KODE_CUACA.get(kode, "Tidak diketahui")
    suhu = cur.get("temperature_2m")
    lembap = cur.get("relative_humidity_2m")
    angin = cur.get("wind_speed_10m")
    tempat = lokasi["nama"]
    if lokasi["wilayah"] and lokasi["wilayah"] != lokasi["nama"]:
        tempat = f"{lokasi['nama']}, {lokasi['wilayah']}"

    logger.info(f"Cuaca nyata {tempat}: {suhu}C, {kondisi}")
    return (
        f"Cuaca di {tempat} saat ini: {kondisi}, suhu {suhu} derajat Celsius, "
        f"kelembapan {lembap} persen, kecepatan angin {angin} km/jam. "
        "(Sumber: Open-Meteo)"
    )


def prakiraan_cuaca(args: Any) -> str:
    """Prakiraan cuaca beberapa hari (data nyata dari Open-Meteo)."""
    kota = str(_ambil_argumen(args, "kota", "Cirebon") or "Cirebon").strip()
    try:
        hari = int(_ambil_argumen(args, "hari", 3) or 3)
    except (TypeError, ValueError):
        hari = 3
    hari = max(1, min(7, hari))

    lokasi = _cari_lokasi(kota)
    if lokasi is None:
        return (
            f"Maaf, saya tidak menemukan kota bernama '{kota}'. "
            "Coba sebutkan nama kota yang lebih lengkap."
        )

    kueri = urllib.parse.urlencode(
        {
            "latitude": lokasi["lintang"],
            "longitude": lokasi["bujur"],
            "daily": "weather_code,temperature_2m_max,temperature_2m_min",
            "timezone": "auto",
            "forecast_days": hari,
        }
    )
    data = _ambil_json(f"{_CUACA_URL}?{kueri}")
    if not data or "daily" not in data:
        return (
            "Maaf, prakiraan cuaca sedang tidak bisa diambil. "
            "Periksa sambungan internet lalu coba lagi."
        )

    harian = data["daily"]
    tanggal = harian.get("time") or []
    kode = harian.get("weather_code") or []
    maks = harian.get("temperature_2m_max") or []
    min_ = harian.get("temperature_2m_min") or []

    baris = [f"Prakiraan cuaca {lokasi['nama']}:"]
    for i in range(min(len(tanggal), hari)):
        kondisi = _KODE_CUACA.get(int(kode[i]) if i < len(kode) else -1, "Tidak diketahui")
        label = "Hari ini" if i == 0 else ("Besok" if i == 1 else tanggal[i])
        hi = maks[i] if i < len(maks) else "-"
        lo = min_[i] if i < len(min_) else "-"
        baris.append(f"- {label}: {kondisi}, {lo}-{hi} derajat Celsius")
    baris.append("(Sumber: Open-Meteo)")
    logger.info(f"Prakiraan cuaca nyata {lokasi['nama']} selama {hari} hari")
    return "\n".join(baris)
