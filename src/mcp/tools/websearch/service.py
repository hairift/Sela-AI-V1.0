"""Pencarian web real-time untuk SELA (gratis, tanpa API key).

Dipakai untuk pertanyaan yang jawabannya TIDAK ada di data kampus dan berubah
seiring waktu - berita terbaru, pejabat yang sedang menjabat, cuaca, harga,
jadwal, atau profil tokoh publik.

Tiga sumber digabung menjadi satu konteks untuk model bahasa:

1. **Wikipedia** (id/en) - ringkasan profil tokoh, tempat, organisasi.
2. **Wikidata** - data terstruktur, mis. siapa pemegang jabatan saat ini.
3. **DuckDuckGo** - hasil pencarian web umum dan berita terkini.

Semuanya memakai pustaka standar Python (urllib), sehingga tetap jalan di
Raspberry Pi dan di paket hasil build tanpa dependensi tambahan.
"""

from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from src.logging import get_logger

logger = get_logger()

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
}

# Kata/frasa yang menandakan jawabannya harus dicari ke internet.
_POLA_REALTIME = [
    r"presiden\s+(indonesia|sekarang|saat\s+ini|ke\s+\d+)",
    r"wakil\s+presiden",
    r"menteri\s+\w+",
    r"gubernur\s+\w+",
    r"walikota\s+\w+",
    r"bupati\s+\w+",
    r"berita\s+(terbaru|sekarang|hari\s+ini|terkini)",
    r"kabar\s+(terbaru|terkini|hari\s+ini)",
    r"cuaca\s+\w*",
    r"harga\s+\w+",
    r"jadwal\s+\w+",
    r"hasil\s+(pertandingan|skor|pemilu|pilkada)",
    r"skor\s+\w+",
    r"kurs\s+\w+",
    r"tren(ding)?\s+\w*",
    r"peristiwa\s+(terbaru|terkini)",
    r"apa\s+yang\s+sedang\s+terjadi",
    r"siapa\s+(itu\s+)?[A-Z][a-z]+\s+[A-Z][a-z]+",
]
_KATA_KUNCI_REALTIME = (
    "berita terbaru", "kabar terkini", "hari ini", "saat ini", "sekarang",
    "terkini", "terbaru", "profil", "biografi", "siapa itu",
)

# Kata kunci yang menandakan permintaan berita.
_KATA_BERITA = (
    "berita", "kabar", "terkini", "terbaru", "peristiwa", "headline",
    "news", "update",
)


def _fetch(url: str, timeout: int = 10) -> Optional[str]:
    """Ambil isi URL dengan penanganan sertifikat yang longgar bila perlu."""
    req = urllib.request.Request(url, headers=_HEADERS)
    try:
        try:
            import certifi

            konteks = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            konteks = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=timeout, context=konteks) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as galat:
        # Sebagian lingkungan kampus memakai sertifikat internal; coba sekali lagi
        # tanpa verifikasi agar pencarian tetap berfungsi.
        if isinstance(getattr(galat, "reason", None), ssl.SSLCertVerificationError):
            try:
                with urllib.request.urlopen(
                    req, timeout=timeout, context=ssl._create_unverified_context()
                ) as resp:
                    return resp.read().decode("utf-8", errors="replace")
            except Exception as e:
                logger.debug(f"Pencarian web: fetch gagal (tanpa verifikasi): {e}")
                return None
        logger.debug(f"Pencarian web: fetch gagal {url}: {galat}")
        return None
    except Exception as e:
        logger.debug(f"Pencarian web: fetch gagal {url}: {e}")
        return None


def perlu_cari_web(kueri: str) -> bool:
    """Apakah pertanyaan ini perlu dijawab dengan pencarian internet?"""
    teks = (kueri or "").lower().strip()
    if any(re.search(pola, teks) for pola in _POLA_REALTIME):
        return True
    return any(kk in teks for kk in _KATA_KUNCI_REALTIME)


def _minta_berita(kueri: str) -> bool:
    teks = (kueri or "").lower()
    return any(k in teks for k in _KATA_BERITA)


# ── Wikipedia ────────────────────────────────────────────────────────────────


def cari_wikipedia(kueri: str, bahasa: str = "id") -> Optional[Dict[str, str]]:
    """Ringkasan Wikipedia untuk kueri."""
    lang = "id" if (bahasa or "id").startswith("id") else "en"
    try:
        url_cari = (
            f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search"
            f"&srsearch={urllib.parse.quote(kueri)}&format=json&srlimit=1"
        )
        isi = _fetch(url_cari)
        if not isi:
            return None
        hasil = json.loads(isi).get("query", {}).get("search", [])
        if not hasil:
            return None
        judul = hasil[0]["title"]
        url_ringkas = (
            f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/"
            f"{urllib.parse.quote(judul)}"
        )
        isi = _fetch(url_ringkas)
        if not isi:
            return None
        data = json.loads(isi)
        ringkasan = data.get("extract", "")
        if not ringkasan:
            return None
        return {
            "judul": judul,
            "snippet": ringkasan,
            "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
            "sumber": "Wikipedia",
        }
    except Exception as e:
        logger.debug(f"Pencarian web: Wikipedia gagal: {e}")
        return None


# ── Wikidata: pemegang jabatan terstruktur ───────────────────────────────────

# Jabatan yang datanya tersedia terstruktur di Wikidata.
_JABATAN_WIKIDATA: Dict[str, str] = {
    "presiden indonesia": "Q252",       # Indonesia -> P35 (kepala negara)
    "wakil presiden indonesia": "Q252",
}


def cari_jabatan(kueri: str) -> Optional[Dict[str, str]]:
    """Cari pemegang jabatan saat ini lewat Wikidata (mis. Presiden Indonesia)."""
    teks = (kueri or "").lower()
    entitas = None
    if "presiden" in teks and "indonesia" in teks and "wakil" not in teks:
        entitas = ("Q252", "Presiden Indonesia")
    elif "wakil presiden" in teks and "indonesia" in teks:
        entitas = ("Q252", "Wakil Presiden Indonesia")
    if not entitas:
        return None

    qid, label_jabatan = entitas
    try:
        isi = _fetch(
            "https://www.wikidata.org/w/api.php?action=wbgetentities"
            f"&ids={qid}&props=claims&format=json"
        )
        if not isi:
            return None
        klaim = json.loads(isi)["entities"][qid]["claims"].get("P35", [])
        aktif = next(
            (
                i
                for i in klaim
                if i.get("rank") == "preferred" and "P582" not in i.get("qualifiers", {})
            ),
            None,
        )
        if not aktif:
            return None
        orang = (
            aktif.get("mainsnak", {})
            .get("datavalue", {})
            .get("value", {})
            .get("id")
        )
        if not orang:
            return None
        isi = _fetch(
            "https://www.wikidata.org/w/api.php?action=wbgetentities"
            f"&ids={orang}&props=labels&languages=id,en&format=json"
        )
        if not isi:
            return None
        label = json.loads(isi)["entities"][orang].get("labels", {})
        nama = (label.get("id") or label.get("en") or {}).get("value")
        if not nama:
            return None
        return {
            "judul": f"Data jabatan {label_jabatan}",
            "snippet": f"{label_jabatan} saat ini adalah {nama}.",
            "url": f"https://www.wikidata.org/wiki/{orang}",
            "sumber": "Wikidata",
        }
    except Exception as e:
        logger.debug(f"Pencarian web: Wikidata gagal: {e}")
        return None


# ── DuckDuckGo ───────────────────────────────────────────────────────────────


def cari_duckduckgo(kueri: str, maks: int = 5) -> List[Dict[str, str]]:
    """Pencarian web lewat DuckDuckGo (paket resmi bila ada, scraper bila tidak)."""
    try:
        from duckduckgo_search import DDGS  # type: ignore

        hasil: List[Dict[str, str]] = []
        with DDGS() as ddgs:
            for item in ddgs.text(kueri, region="id-id", max_results=maks):
                hasil.append(
                    {
                        "judul": item.get("title", ""),
                        "url": item.get("href", ""),
                        "snippet": item.get("body", ""),
                    }
                )
        if hasil:
            return hasil
    except Exception as e:
        logger.debug(f"Pencarian web: duckduckgo-search tidak dipakai: {e}")

    # Cadangan: scraper HTML DuckDuckGo (tanpa dependensi).
    hasil = []
    try:
        url = (
            f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(kueri)}&kl=id-id"
        )
        isi = _fetch(url)
        if not isi:
            return hasil
        pola_judul = re.compile(
            r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>', re.DOTALL
        )
        pola_ringkas = re.compile(
            r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>', re.DOTALL
        )
        judul_m = pola_judul.findall(isi)
        ringkas_m = pola_ringkas.findall(isi)
        for i in range(min(len(judul_m), maks)):
            tautan = judul_m[i][0]
            judul = re.sub(r"<[^>]+>", "", judul_m[i][1]).strip()
            ringkas = (
                re.sub(r"<[^>]+>", "", ringkas_m[i]).strip()
                if i < len(ringkas_m)
                else ""
            )
            if "uddg=" in tautan:
                parsed = urllib.parse.parse_qs(urllib.parse.urlparse(tautan).query)
                if "uddg" in parsed:
                    tautan = urllib.parse.unquote(parsed["uddg"][0])
            hasil.append({"judul": judul, "url": tautan, "snippet": ringkas})
    except Exception as e:
        logger.debug(f"Pencarian web: scraper DuckDuckGo gagal: {e}")
    return hasil


# ── Pencarian gabungan ───────────────────────────────────────────────────────


def cari_web(kueri: str, bahasa: str = "id") -> str:
    """Cari jawaban terkini di internet dan kembalikan konteks untuk SELA.

    Args:
        kueri: Pertanyaan pengguna apa adanya.
        bahasa: Kode bahasa untuk Wikipedia ("id" atau "en").

    Returns:
        Konteks berisi kutipan dari Wikipedia/Wikidata/DuckDuckGo, atau pesan
        jujur bila tidak ada hasil.
    """
    kueri = (kueri or "").strip()
    if not kueri:
        return "Pertanyaan kosong; tidak ada yang bisa dicari."

    logger.info(f"Pencarian web: '{kueri}'")

    jabatan = cari_jabatan(kueri)
    wiki = jabatan or cari_wikipedia(kueri, bahasa)

    # Untuk permintaan berita, tambahkan kata "berita" agar hasilnya relevan.
    kueri_ddg = f"{kueri} berita terbaru" if _minta_berita(kueri) else kueri
    ddg = cari_duckduckgo(kueri_ddg, maks=5)

    bagian: List[str] = []
    if wiki:
        bagian.append(
            f"[DARI {wiki.get('sumber', 'WIKIPEDIA').upper()}]\n"
            f"{wiki['snippet']}\nSumber: {wiki.get('url', '')}"
        )
    for h in ddg[:3]:
        if h.get("snippet"):
            bagian.append(
                f"[DARI WEB]\n{h['judul']}\n{h['snippet']}\nSumber: {h.get('url', '')}"
            )

    if not bagian:
        return (
            "Tidak ada hasil pencarian yang bisa dipakai. "
            "Jawab dengan jujur bahwa informasinya belum bisa dipastikan, "
            "jangan mengarang."
        )

    return (
        "Gunakan informasi terkini di bawah ini untuk menjawab. "
        "Sebutkan bahwa sumbernya dari internet bila relevan, dan jangan "
        "menambahkan fakta yang tidak tertulis di sini.\n\n" + "\n\n".join(bagian)
    )
