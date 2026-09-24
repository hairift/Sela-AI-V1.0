"""Pencari pengetahuan kampus UCIC berbasis BM25 + gerbang cakupan IDF.

Ini adalah mesin pencarian yang membuat SELA bisa menjawab pertanyaan kampus
**tanpa halusinasi**: jawaban hanya diambil dari dokumen resmi yang benar-benar
cocok, dan bila tidak ada yang cocok SELA menjawab jujur bahwa datanya belum
tercatat.

Mengapa BM25 dan bukan sekadar pencocokan teks biasa:

1. **Bobot medan** - judul dan kata kunci berbobot 3x, isi 1x, sehingga dokumen
   yang topiknya persis selalu mengalahkan dokumen yang hanya menyinggung.
2. **Pembobotan IDF** - kata umum seperti "kampus" atau "mahasiswa" tidak
   mendominasi hasil.
3. **Bonus frasa kata kunci** - bila frasa kata kunci muncul utuh di pertanyaan,
   dokumen diberi dorongan kuat.
4. **Gerbang cakupan IDF** - dokumen hanya lolos bila cukup banyak istilah
   penting pertanyaan yang benar-benar tertulis di dokumen. Pertanyaan di luar
   kampus ("resep rendang", "siapa presiden") gagal di gerbang ini, sehingga
   SELA menjawab jujur alih-alih mengarang.
5. **Minimal dua istilah berbeda** harus cocok dalam SATU dokumen, agar
   pertanyaan dua kata tidak lolos hanya karena satu kata kebetulan ada.

Modul ini tidak bergantung pada paket pihak ketiga apa pun - hanya pustaka
standar Python, sehingga ringan untuk Raspberry Pi dan tetap jalan di paket
hasil build.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

# ── Parameter BM25 ────────────────────────────────────────────────────────────
K1 = 1.5
B = 0.75

# Bobot medan: judul & kata kunci jauh lebih menentukan daripada isi panjang.
BOBOT_MEDAN: Dict[str, float] = {
    "judul": 3.0,
    "kata_kunci": 3.0,
    "isi": 1.0,
}

# Ambang cakupan IDF untuk gerbang anti-halusinasi.
# 0,50 berarti separuh bobot istilah penting pertanyaan harus ada di dokumen.
AMBANG_CAKUPAN = 0.50

# Jumlah minimum istilah pertanyaan BERBEDA yang harus cocok di SATU dokumen.
_MIN_COCOK_DISTINCT = 2

# Batas atas IDF untuk istilah yang ada di korpus. Tanpa batas ini, satu kata
# yang sangat langka bisa mendominasi cakupan dan menjatuhkan dokumen yang
# sebenarnya cocok.
_IDF_MAKS = 3.0

# ── Kata umum (tidak dihitung sebagai istilah penting) ────────────────────────
_STOPWORDS = {
    # kata fungsi umum
    "yang", "dan", "atau", "juga", "dengan", "untuk", "pada", "dalam", "oleh",
    "dari", "ke", "di", "ini", "itu", "ada", "adalah", "akan", "sudah", "telah",
    "belum", "masih", "saja", "aja", "pun", "nya", "nih", "deh", "kok",
    "kan", "sih", "ya", "yah", "dong", "lah", "kah", "gitu", "begitu",
    "begini", "sama", "buat", "bisa", "bisakah", "boleh", "tolong", "mohon",
    "silakan", "minta", "coba", "mau", "ingin", "pengen", "butuh", "perlu",
    "tentang", "soal", "mengenai", "seputar", "kasih", "tau", "tahu",
    # kata tanya
    "apa", "apakah", "siapa", "siapakah", "berapa", "berapakah", "kapan",
    "dimana", "kemana", "mana", "bagaimana", "bagaimanakah", "gimana",
    "kenapa", "mengapa", "apaan",
    # penanda / pembatas
    "lain", "lainnya", "semua", "seluruh", "setiap", "para", "suatu", "sebuah",
    "satu", "dua", "nah", "terus", "lewat", "banget",
    "loh", "lho", "mah", "atuh", "euy", "kayak", "kaya", "kek", "tuh", "tu",
    # kata ganti
    "saya", "aku", "kamu", "anda", "kita", "kami", "mereka", "dia", "beliau",
    "kalian", "daku", "diriku",
    # sapaan & kesopanan
    "halo", "hai", "hallo", "hello", "hi", "hei", "selamat", "pagi", "siang",
    "sore", "malam", "terima", "makasih", "thanks", "thank", "you", "kak",
    "min", "mbak", "mas", "pak", "bu", "bang", "bapak", "ibu",
    # negasi ringan
    "tidak", "gak", "ga", "nggak", "engga", "bukan", "jangan", "tanpa",
    # Inggris
    "the", "an", "is", "are", "was", "were", "be", "of", "to", "for",
    "in", "on", "at", "by", "with", "and", "or", "what", "who", "whom",
    "whose", "how", "much", "many", "when", "where", "which", "why", "do",
    "does", "did", "can", "could", "should", "would", "i", "me", "my",
    "your", "we", "our", "they", "their", "there", "here", "please", "tell",
    "about", "give", "get", "want", "need", "any", "some", "this", "that",
}

# ── Sinonim ringan (memperluas daya ingat tanpa merusak gerbang cakupan) ──────
_SINONIM: Dict[str, Sequence[str]] = {
    "biaya": ("ukt", "harga", "tarif", "pembayaran", "bayar", "kuliah"),
    "ukt": ("biaya", "harga", "tarif", "pembayaran"),
    "harga": ("biaya", "tarif", "ukt"),
    "uang": ("biaya", "bayar", "pembayaran", "harga", "tarif"),
    "bayar": ("biaya", "pembayaran", "uang", "transfer"),
    "pembayaran": ("biaya", "bayar", "uang"),
    "masuk": ("pendaftaran", "daftar", "kuliah"),
    "kuliah": ("biaya", "perkuliahan", "kampus"),
    "dosen": ("pengajar", "guru", "staf pengajar"),
    "pengajar": ("dosen", "mengajar", "ajar"),
    "mengajar": ("pengajar", "ajar", "dosen"),
    "jurusan": ("prodi", "program studi"),
    "prodi": ("jurusan", "program studi"),
    "daftar": ("pendaftaran", "registrasi", "mendaftar"),
    "pendaftaran": ("daftar", "mendaftar", "registrasi", "pmb", "admisi"),
    "mendaftar": ("daftar", "pendaftaran", "registrasi"),
    "dibuka": ("pendaftaran", "jadwal", "daftar"),
    "buka": ("pendaftaran", "jadwal", "daftar"),
    "beasiswa": ("kip", "bantuan biaya"),
    "kip": ("beasiswa",),
    "syarat": ("persyaratan", "berkas", "dokumen", "ketentuan"),
    "persyaratan": ("syarat", "berkas", "dokumen"),
    "jadwal": ("waktu", "tanggal", "gelombang"),
    "fasilitas": ("sarana", "prasarana", "gedung", "ruang", "lab", "laboratorium"),
    "lokasi": ("alamat", "tempat", "kampus"),
    "alamat": ("lokasi", "tempat"),
    "kontak": ("telepon", "whatsapp", "email", "hubungi", "nomor"),
    "rektor": ("pimpinan", "ketua"),
    "akreditasi": ("peringkat",),
    "kurikulum": ("mata kuliah", "semester"),
    "kelas": ("perkuliahan", "jadwal kuliah", "kelas karyawan"),
    "alumni": ("lulusan", "tamatan"),
    "lulusan": ("alumni", "tamatan"),
    "kampus": ("ucic", "universitas"),
}

# Awalan & akhiran bahasa Indonesia untuk stemming ringan (menambah varian,
# tidak mengganti token asli sehingga aman).
_AWALAN = (
    "meng", "meny", "mem", "men", "me", "peng", "peny", "pem", "pen", "per",
    "ber", "ter", "ke",
)
_AKHIRAN = ("kannya", "annya", "kan", "an", "nya", "i", "lah", "kah")

_ANGKA = re.compile(r"\d")


def _normalisasi(teks: str) -> str:
    """Huruf kecil, buang aksen, ubah pemisah menjadi spasi."""
    teks = unicodedata.normalize("NFKD", str(teks or ""))
    teks = "".join(c for c in teks if not unicodedata.combining(c))
    teks = teks.lower()
    teks = re.sub(r"[^a-z0-9]+", " ", teks)
    return re.sub(r"\s+", " ", teks).strip()


def _akar(kata: str) -> str:
    """Stemming ringan: buang akhiran lalu awalan yang aman."""
    if len(kata) <= 4:
        return kata
    for akhir in _AKHIRAN:
        if kata.endswith(akhir) and len(kata) - len(akhir) >= 3:
            kata = kata[: -len(akhir)]
            break
    for awal in _AWALAN:
        if kata.startswith(awal) and len(kata) - len(awal) >= 4:
            kata = kata[len(awal):]
            break
    return kata


def _token_dasar(teks: str) -> List[str]:
    """Token bermakna (tanpa kata umum) dari sebuah teks."""
    hasil: List[str] = []
    for t in _normalisasi(teks).split():
        if len(t) < 3 and not _ANGKA.search(t):
            continue
        if t in _STOPWORDS:
            continue
        hasil.append(t)
    return hasil


def _perluas(token: str) -> List[str]:
    """Token + akar + sinonim, untuk memperluas pencocokan BM25."""
    varian = [token]
    akar = _akar(token)
    if akar != token and len(akar) >= 3:
        varian.append(akar)
    for sin in _SINONIM.get(token, ()):
        for bagian in _normalisasi(sin).split():
            if bagian not in _STOPWORDS and len(bagian) >= 3:
                varian.append(bagian)
    terlihat: set[str] = set()
    unik: List[str] = []
    for v in varian:
        if v not in terlihat:
            terlihat.add(v)
            unik.append(v)
    return unik


def _levenshtein_dibatasi(a: str, b: str, batas: int) -> int:
    """Jarak edit dengan pemotongan dini (mengembalikan batas+1 bila jauh)."""
    if abs(len(a) - len(b)) > batas:
        return batas + 1
    sebelumnya = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        sekarang = [i]
        for j, cb in enumerate(b, 1):
            sekarang.append(
                min(
                    sebelumnya[j] + 1,
                    sekarang[j - 1] + 1,
                    sebelumnya[j - 1] + (0 if ca == cb else 1),
                )
            )
        sebelumnya = sekarang
    return sebelumnya[-1]


class LexicalIndex:
    """Indeks BM25 + gerbang cakupan IDF untuk sekumpulan dokumen UCIC."""

    def __init__(self, dokumen: Sequence[Dict[str, Any]]) -> None:
        self.dokumen = list(dokumen)
        self.n = len(self.dokumen)

        self._tf: List[Dict[str, float]] = []  # per dokumen: term -> bobot tf
        self._panjang: List[float] = []        # panjang dokumen (berbobot)
        self._df: Dict[str, int] = {}          # term -> jumlah dokumen
        self._frasa: List[List[str]] = []      # per dokumen: frasa kata kunci
        self._rata_panjang = 1.0
        self._idf_asing = math.log(1.0 + (self.n + 0.5) / 0.5) if self.n else 1.0

        self._bangun()

    # ── Pembangunan indeks ────────────────────────────────────────────────────
    @staticmethod
    def _medan(dok: Dict[str, Any]) -> Dict[str, str]:
        kata_kunci = dok.get("keywords") or dok.get("kata_kunci") or []
        if isinstance(kata_kunci, str):
            kata_kunci = [kata_kunci]
        return {
            "judul": str(dok.get("title") or dok.get("judul") or ""),
            "kata_kunci": " ".join(str(k) for k in kata_kunci),
            "isi": str(dok.get("content") or dok.get("konten") or dok.get("teks") or ""),
        }

    def _bangun(self) -> None:
        for dok in self.dokumen:
            medan = self._medan(dok)
            tf: Dict[str, float] = {}
            panjang = 0.0
            for nama_medan, teks in medan.items():
                bobot = BOBOT_MEDAN.get(nama_medan, 1.0)
                for token in _token_dasar(teks):
                    for varian in _perluas(token):
                        tf[varian] = tf.get(varian, 0.0) + bobot
                        panjang += bobot
            self._tf.append(tf)
            self._panjang.append(max(panjang, 1.0))
            for term in tf:
                self._df[term] = self._df.get(term, 0) + 1

            frasa: List[str] = []
            for kk in (dok.get("keywords") or dok.get("kata_kunci") or []):
                frasa_norm = _normalisasi(kk)
                if len(frasa_norm.split()) >= 2:
                    frasa.append(frasa_norm)
            self._frasa.append(frasa)

        total = sum(self._panjang)
        self._rata_panjang = total / self.n if self.n else 1.0

    # ── IDF ───────────────────────────────────────────────────────────────────
    def _idf(self, term: str) -> float:
        df = self._df.get(term)
        if df is None:
            return self._idf_asing  # istilah di luar korpus -> bobot tertinggi
        return min(math.log(1.0 + (self.n - df + 0.5) / (df + 0.5)), _IDF_MAKS)

    # ── Koreksi salah ketik (OOV) ─────────────────────────────────────────────
    def _koreksi_oov(self, token: str) -> str:
        """Petakan token di luar korpus ke istilah terdekat (jarak edit kecil).

        Menangani salah ketik umum seperti 'persaratan' -> 'persyaratan' agar
        gerbang cakupan tidak menghukum pertanyaan yang sebenarnya valid.
        """
        if token in self._df:
            return token
        batas = 2 if len(token) >= 7 else 1
        terbaik: Optional[str] = None
        jarak_terbaik = batas + 1
        for kandidat in self._df:
            if abs(len(kandidat) - len(token)) > batas:
                continue
            jarak = _levenshtein_dibatasi(token, kandidat, batas)
            if jarak < jarak_terbaik:
                terbaik, jarak_terbaik = kandidat, jarak
                if jarak == 0:
                    break
        return terbaik or token

    # ── Pencarian ─────────────────────────────────────────────────────────────
    def cari(self, kueri: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Kembalikan kandidat terurut yang lolos gerbang cakupan IDF.

        Returns:
            ``[{indeks, skor, cakupan, dokumen, cocok}]``
        """
        if self.n == 0:
            return []
        token_asli = [self._koreksi_oov(t) for t in _token_dasar(kueri)]
        if not token_asli:
            return []

        bobot_asli: Dict[str, float] = {}
        for t in token_asli:
            bobot_asli[t] = bobot_asli.get(t, 0.0) + 1.0
        total_bobot = sum(self._idf(t) * w for t, w in bobot_asli.items())
        if total_bobot <= 0:
            return []

        istilah_bm25: Dict[str, float] = {}
        for t in token_asli:
            istilah_bm25[t] = istilah_bm25.get(t, 0.0) + 1.0
            for v in _perluas(t):
                if v != t:
                    istilah_bm25[v] = max(istilah_bm25.get(v, 0.0), 0.6)

        kueri_norm = _normalisasi(kueri)
        kandidat: List[Dict[str, Any]] = []
        min_cocok = _MIN_COCOK_DISTINCT if len(bobot_asli) >= _MIN_COCOK_DISTINCT else 1

        for i, tf in enumerate(self._tf):
            skor = 0.0
            cocok = 0.0
            jumlah_cocok = 0
            for t, w in bobot_asli.items():
                if tf.get(t, 0.0) > 0 or tf.get(_akar(t), 0.0) > 0:
                    cocok += self._idf(t) * w
                    jumlah_cocok += 1
            cakupan = cocok / total_bobot

            if cakupan < AMBANG_CAKUPAN or jumlah_cocok < min_cocok:
                continue

            for term, qw in istilah_bm25.items():
                f = tf.get(term, 0.0)
                if f <= 0:
                    continue
                idf = self._idf(term)
                penyebut = f + K1 * (1.0 - B + B * self._panjang[i] / self._rata_panjang)
                skor += qw * idf * (f * (K1 + 1.0)) / penyebut

            for frasa in self._frasa[i]:
                if frasa and frasa in kueri_norm:
                    skor += 3.0 * len(frasa.split())

            kandidat.append(
                {
                    "indeks": i,
                    "skor": skor,
                    "cakupan": cakupan,
                    "dokumen": self.dokumen[i],
                    "cocok": [
                        t
                        for t in bobot_asli
                        if tf.get(t, 0.0) > 0 or tf.get(_akar(t), 0.0) > 0
                    ],
                }
            )

        kandidat.sort(key=lambda k: (-k["skor"], -k["cakupan"]))
        return kandidat[:top_k]

    def info(self) -> Dict[str, Any]:
        return {
            "metode": "bm25-lexical",
            "jumlah_dokumen": self.n,
            "jumlah_kosakata": len(self._df),
            "ambang_cakupan": AMBANG_CAKUPAN,
            "min_cocok_distinct": _MIN_COCOK_DISTINCT,
        }


# ── Pemuatan dataset ──────────────────────────────────────────────────────────

_KANDIDAT_JALUR = (
    "src/data/ucic_dataset.json",
    "ai-engine/data/ucic_dataset.json",
    "data/ucic_dataset.json",
)


def temukan_dataset() -> Optional[Path]:
    """Cari berkas dataset kampus, baik saat dijalankan dari sumber maupun terpaket."""
    akar: Optional[Path] = None
    try:
        from src.utils.resource_finder import get_app_root

        akar = Path(get_app_root())
    except Exception:
        akar = Path(__file__).resolve().parents[3]

    for relatif in _KANDIDAT_JALUR:
        kandidat = akar / relatif
        if kandidat.is_file():
            return kandidat

    # Cadangan: telusuri beberapa tingkat ke atas dari modul ini.
    for dasar in (akar, Path(__file__).resolve().parents[3]):
        for pola in ("**/ucic_dataset.json", "**/ucic_knowledge_base*.json"):
            for kandidat in dasar.glob(pola):
                return kandidat
    return None


def muat_dokumen(jalur: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Muat dokumen kampus dari berkas JSON."""
    jalur = jalur or temukan_dataset()
    if not jalur or not jalur.is_file():
        return []
    try:
        data = json.loads(jalur.read_text(encoding="utf-8"))
    except Exception:
        return []

    if isinstance(data, dict):
        for kunci in ("data", "documents", "dokumen", "items"):
            if isinstance(data.get(kunci), list):
                data = data[kunci]
                break
    if not isinstance(data, list):
        return []

    dokumen: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        isi = item.get("content") or item.get("konten") or item.get("teks") or ""
        if not str(isi).strip():
            continue
        # Buang dokumen gabungan raksasa bila ada (bukan satu topik).
        if str(item.get("id") or "") in ("data_lengkap_ucic", "data_lengkap"):
            continue
        dokumen.append(item)
    return dokumen
