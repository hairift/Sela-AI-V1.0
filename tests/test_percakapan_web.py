"""Pengujian fitur percakapan web SELA yang baru.

Menguji bagian yang lahir dari permintaan pengguna:

* batas panjang teks pada kolom obrolan (server menolak teks panjang);
* papan langkah alat ("labor illusion") saat mesin AI memanggil alat;
* kotak surat bingkai kamera peramban untuk tool ``take_photo``;
* pemicu kamera dari kalimat pengguna ("tolong foto saya").
"""

import asyncio
import base64
import re
from pathlib import Path

import pytest

from src.core.event_bus import EventBus, Events
from src.ui.web import kamera_peramban
from src.ui.web.bridge import (
    MAKS_PANJANG_TEKS,
    SelaBridge,
    _minta_foto_dari_teks,
    label_alat,
)

AKAR = Path(__file__).resolve().parents[1]


class _FakeWS:
    """WebSocket palsu yang merekam semua pesan yang dikirim."""

    def __init__(self):
        self.terkirim = []

    async def send_json(self, payload):
        self.terkirim.append(payload)

    def tipe(self, nama):
        return [p for p in self.terkirim if p.get("t") == nama]


@pytest.fixture
def bus():
    return EventBus()


@pytest.fixture
def bridge(bus):
    return SelaBridge(bus, task_manager=None)


@pytest.fixture
async def bridge_aktif(bus):
    """Jembatan yang sudah berlangganan EventBus (start() dipanggil)."""
    b = SelaBridge(bus, task_manager=None)
    await b.start()
    try:
        yield b
    finally:
        await b.stop()


@pytest.fixture(autouse=True)
def kamera_kembali_aktif():
    """Pastikan status kamera peramban tidak bocor antar pengujian."""
    kamera_peramban.set_aktif(True)
    kamera_peramban._bingkai_bersih()
    yield
    kamera_peramban.set_aktif(True)
    kamera_peramban._bingkai_bersih()


def _data_url(payload: bytes = b"\xff\xd8\xff\xe0data") -> str:
    return "data:image/jpeg;base64," + base64.b64encode(payload).decode()


# ── Label alat ───────────────────────────────────────────────────────────────


def test_label_alat_untuk_alat_yang_dikenal():
    assert label_alat("cari_info_kampus") == "Membuka data kampus UCIC"
    assert label_alat("take_photo") == "Mengambil gambar dari kamera"
    assert label_alat("cuaca_sekarang") == "Mengambil data cuaca terkini"


def test_label_alat_memakai_bagian_setelah_titik():
    # Alat bawaan py-xiaozhi memakai nama berspasi titik.
    assert label_alat("self.application.launch") == "Membuka aplikasi"
    assert label_alat("self.application.kill") == "Menutup aplikasi"


def test_label_alat_untuk_nama_yang_tidak_dikenal():
    assert label_alat("cetak_dokumen") == "Menjalankan cetak dokumen"
    assert label_alat("cari_sesuatu") == "Mencari informasi"
    assert label_alat("volume_up") == "Mengatur volume suara"


def test_label_alat_aman_untuk_nama_kosong():
    assert label_alat("") == "Menjalankan alat"
    assert label_alat(None) == "Menjalankan alat"


# ── Pemicu kamera dari kalimat pengguna ──────────────────────────────────────


@pytest.mark.parametrize(
    "kalimat",
    [
        "tolong foto saya",
        "lihat saya sekarang",
        "ambil gambar dong",
        "selfie ya",
        "lihat wajah saya",
        "take a photo",
    ],
)
def test_kalimat_minta_foto_dikenali(kalimat):
    assert _minta_foto_dari_teks(kalimat) is True


@pytest.mark.parametrize(
    "kalimat",
    ["berapa biaya kuliah", "cuaca hari ini", "", "program studi apa saja"],
)
def test_kalimat_biasa_tidak_memicu_kamera(kalimat):
    assert _minta_foto_dari_teks(kalimat) is False


# ── Batas panjang teks ───────────────────────────────────────────────────────


def test_batas_panjang_sama_dengan_antarmuka_javascript():
    """Nilai Python dan JavaScript harus sama, kalau tidak batasnya bocor."""
    sumber = (AKAR / "webui" / "src" / "lib" / "percakapan.js").read_text(
        encoding="utf-8"
    )
    cocok = re.search(r"MAKS_PANJANG_TEKS\s*=\s*(\d+)", sumber)
    assert cocok, "MAKS_PANJANG_TEKS tidak ditemukan di percakapan.js"
    assert int(cocok.group(1)) == MAKS_PANJANG_TEKS


@pytest.mark.asyncio
async def test_teks_panjang_dipotong_sebelum_dikirim(bus, bridge):
    ws = _FakeWS()
    await bridge.add_client(ws)
    ws.terkirim.clear()

    diterima = []

    async def tangkap(data=None):
        diterima.append(data)

    bus.on(Events.UI_SEND_TEXT, tangkap)

    panjang = "a" * (MAKS_PANJANG_TEKS + 40)
    await bridge.handle_command({"t": "send_text", "text": panjang})

    assert len(diterima) == 1
    assert len(diterima[0].text) == MAKS_PANJANG_TEKS
    assert len(ws.tipe("user_text")[0]["text"]) == MAKS_PANJANG_TEKS


@pytest.mark.asyncio
async def test_teks_pendek_tidak_dipotong(bus, bridge):
    diterima = []

    async def tangkap(data=None):
        diterima.append(data)

    bus.on(Events.UI_SEND_TEXT, tangkap)
    await bridge.handle_command({"t": "send_text", "text": "halo SELA"})

    assert diterima[0].text == "halo SELA"


@pytest.mark.asyncio
async def test_permintaan_foto_dari_teks_memicu_kamera(bus, bridge):
    ws = _FakeWS()
    await bridge.add_client(ws)
    ws.terkirim.clear()

    await bridge.handle_command({"t": "send_text", "text": "tolong foto saya"})

    minta = ws.tipe("ambil_foto")
    assert len(minta) == 1
    assert minta[0]["source"] == "pengguna"


@pytest.mark.asyncio
async def test_pertanyaan_biasa_tidak_memicu_kamera(bus, bridge):
    ws = _FakeWS()
    await bridge.add_client(ws)
    ws.terkirim.clear()

    await bridge.handle_command({"t": "send_text", "text": "biaya kuliah UCIC?"})

    assert ws.tipe("ambil_foto") == []


# ── Papan langkah alat ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_panggilan_alat_memancarkan_langkah_untuk_antarmuka(bus, bridge_aktif):
    ws = _FakeWS()
    await bridge_aktif.add_client(ws)
    ws.terkirim.clear()

    await bus.emit(
        Events.INCOMING_JSON,
        {
            "type": "mcp",
            "payload": {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "cari_info_kampus", "arguments": {}},
            },
        },
    )

    langkah = ws.tipe("tool")
    assert len(langkah) == 1
    assert langkah[0]["name"] == "cari_info_kampus"
    assert langkah[0]["label"] == "Membuka data kampus UCIC"


@pytest.mark.asyncio
async def test_pesan_mcp_selain_tools_call_diabaikan(bus, bridge_aktif):
    ws = _FakeWS()
    await bridge_aktif.add_client(ws)
    ws.terkirim.clear()

    await bus.emit(
        Events.INCOMING_JSON,
        {"type": "mcp", "payload": {"method": "tools/list", "params": {}}},
    )

    assert ws.tipe("tool") == []


@pytest.mark.asyncio
async def test_alat_kamera_meminta_bingkai_peramban(bus, bridge_aktif):
    ws = _FakeWS()
    await bridge_aktif.add_client(ws)
    ws.terkirim.clear()

    await bus.emit(
        Events.INCOMING_JSON,
        {
            "type": "mcp",
            "payload": {
                "method": "tools/call",
                "params": {"name": "take_photo"},
            },
        },
    )

    assert ws.tipe("tool")[0]["label"] == "Mengambil gambar dari kamera"
    assert ws.tipe("ambil_foto")[0]["source"] == "ai"


# ── Kotak surat bingkai kamera ───────────────────────────────────────────────


def test_bingkai_tersimpan_dan_bisa_diambil():
    isi = b"\xff\xd8\xff\xe0contoh-jpeg"
    assert kamera_peramban.simpan_bingkai(_data_url(isi)) is True
    assert kamera_peramban.ambil_bingkai() == isi
    assert kamera_peramban.ada_bingkai_segar() is True


def test_bingkai_rusak_ditolak():
    assert kamera_peramban.simpan_bingkai("") is False
    assert kamera_peramban.simpan_bingkai("data:image/jpeg;base64,") is False
    assert kamera_peramban.ambil_bingkai() is None


def test_bingkai_kedaluwarsa_tidak_dipakai():
    assert kamera_peramban.simpan_bingkai(_data_url()) is True
    # Batas umur negatif membuat bingkai apa pun dianggap basi.
    assert kamera_peramban.ambil_bingkai(maks_umur_s=-1) is None


def test_saat_nonaktif_bingkai_ditolak_dan_dikosongkan():
    assert kamera_peramban.simpan_bingkai(_data_url()) is True
    kamera_peramban.set_aktif(False)

    assert kamera_peramban.apakah_aktif() is False
    assert kamera_peramban.ambil_bingkai() is None
    assert kamera_peramban.simpan_bingkai(_data_url()) is False


def test_bingkai_terlalu_besar_ditolak():
    besar = b"x" * (kamera_peramban.MAKS_UKURAN_BINGKAI + 1)
    assert kamera_peramban.simpan_bingkai(_data_url(besar)) is False
    assert kamera_peramban.ambil_bingkai() is None


def test_ambil_bingkai_aman_di_thread_lain():
    """Tool kamera berjalan di thread lain; kotak surat harus aman."""
    import threading

    isi = b"\xff\xd8\xff\xe0thread"
    assert kamera_peramban.simpan_bingkai(_data_url(isi)) is True

    hasil = {}

    def baca():
        hasil["bingkai"] = kamera_peramban.ambil_bingkai()

    t = threading.Thread(target=baca)
    t.start()
    t.join(timeout=5)

    assert hasil.get("bingkai") == isi


@pytest.mark.asyncio
async def test_perintah_kamera_bingkai_membalas_kamera_ok(bus, bridge):
    ws = _FakeWS()
    await bridge.add_client(ws)
    ws.terkirim.clear()

    await bridge.handle_command({"t": "kamera_bingkai", "data": _data_url()})

    assert len(ws.tipe("kamera_ok")) == 1
    assert kamera_peramban.ambil_bingkai() is not None


@pytest.mark.asyncio
async def test_perintah_kamera_aktif_mengubah_status(bus, bridge):
    await bridge.handle_command({"t": "kamera_aktif", "aktif": False})
    await asyncio.sleep(0)
    assert kamera_peramban.apakah_aktif() is False

    await bridge.handle_command({"t": "kamera_aktif", "aktif": True})
    await asyncio.sleep(0)
    assert kamera_peramban.apakah_aktif() is True
