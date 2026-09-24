"""Pengujian antarmuka web SELA (jembatan EventBus ↔ WebSocket).

Menguji bagian yang menghubungkan antarmuka web dengan mesin AI py-xiaozhi:
pemetaan perintah, penyiaran status, dan perhitungan data lipsync.
"""

import asyncio
import json

import numpy as np
import pytest

from src.core.event_bus import EventBus, Events
from src.ui.web.bridge import SelaBridge


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


# ── Perintah antarmuka -> EventBus ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_kirim_teks_memancarkan_event_ui_send_text(bus, bridge):
    diterima = []

    async def tangkap(data=None):
        diterima.append(data)

    bus.on(Events.UI_SEND_TEXT, tangkap)
    await bridge.handle_command({"t": "send_text", "text": "halo SELA"})

    assert len(diterima) == 1
    assert diterima[0].text == "halo SELA"


@pytest.mark.asyncio
async def test_teks_kosong_tidak_memancarkan_event(bus, bridge):
    dipanggil = []

    async def tangkap(data=None):
        dipanggil.append(data)

    bus.on(Events.UI_SEND_TEXT, tangkap)
    await bridge.handle_command({"t": "send_text", "text": "   "})

    assert dipanggil == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("perintah", "event"),
    [
        ("manual_toggle", Events.UI_MANUAL_TOGGLE),
        ("auto_start", Events.UI_AUTO_START),
        ("auto_toggle", Events.UI_AUTO_TOGGLE),
        ("abort", Events.UI_ABORT_REQUEST),
        ("open_settings", Events.UI_OPEN_SETTINGS),
        ("quit", Events.UI_QUIT_REQUEST),
    ],
)
async def test_perintah_tombol_dipetakan_ke_event_yang_benar(bus, bridge, perintah, event):
    """Setiap tombol antarmuka harus memakai event yang sama dengan QML/CLI."""
    dipanggil = []

    async def tangkap(data=None):
        dipanggil.append(data)

    bus.on(event, tangkap)
    await bridge.handle_command({"t": perintah})

    assert len(dipanggil) == 1


@pytest.mark.asyncio
async def test_perintah_tak_dikenal_tidak_error(bridge):
    # Tidak boleh melempar exception.
    await bridge.handle_command({"t": "perintah_aneh"})
    await bridge.handle_command({})


# ── EventBus -> antarmuka ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tts_diteruskan_sebagai_pesan_asisten(bus, bridge_aktif):
    ws = _FakeWS()
    await bridge_aktif.add_client(ws)
    ws.terkirim.clear()

    await bus.emit(Events.INCOMING_JSON, {"type": "tts", "text": "Selamat pagi"})

    pesan = ws.tipe("chat")
    assert len(pesan) == 1
    assert pesan[0]["role"] == "assistant"
    assert pesan[0]["text"] == "Selamat pagi"


@pytest.mark.asyncio
async def test_stt_diteruskan_sebagai_pesan_pengguna(bus, bridge_aktif):
    ws = _FakeWS()
    await bridge_aktif.add_client(ws)
    ws.terkirim.clear()

    await bus.emit(Events.INCOMING_JSON, {"type": "stt", "text": "berapa biaya"})

    pesan = ws.tipe("chat")
    assert len(pesan) == 1
    assert pesan[0]["role"] == "user"


@pytest.mark.asyncio
async def test_emosi_diteruskan(bus, bridge_aktif):
    ws = _FakeWS()
    await bridge_aktif.add_client(ws)
    ws.terkirim.clear()

    await bus.emit(Events.INCOMING_JSON, {"type": "llm", "emotion": "happy"})

    assert ws.tipe("emotion")[0]["emotion"] == "happy"


@pytest.mark.asyncio
async def test_klien_baru_langsung_menerima_snapshot(bridge):
    ws = _FakeWS()
    await bridge.add_client(ws)

    snapshot = ws.tipe("snapshot")
    assert len(snapshot) == 1
    assert "status" in snapshot[0]


@pytest.mark.asyncio
async def test_klien_terputus_tidak_mengganggu_penyiaran(bus, bridge):
    hidup = _FakeWS()
    await bridge.add_client(hidup)

    class _Mati:
        async def send_json(self, payload):
            raise ConnectionResetError("klien hilang")

    await bridge.add_client(_Mati())
    # Tidak boleh melempar meski salah satu klien mati.
    await bridge.broadcast({"t": "uji"})

    assert len(hidup.terkirim) > 0


# ── Lipsync ──────────────────────────────────────────────────────────────────


def test_lipsync_hening_membuat_mulut_tertutup(bridge):
    bridge.feed_output_audio(np.zeros(512, dtype=np.float32))
    assert bridge._lip_volume == 0.0
    assert bridge._lip_viseme == "sil"


def test_lipsync_suara_nyaring_membuat_mulut_terbuka(bridge):
    t = np.linspace(0, 0.02, 512, endpoint=False)
    sinyal = (0.5 * np.sin(2 * np.pi * 200 * t)).astype(np.float32)

    bridge.feed_output_audio(sinyal)

    assert bridge._lip_volume > 0.2
    assert bridge._lip_viseme in {"a", "e", "i", "o", "u"}


def test_lipsync_vokal_berbeda_memberi_viseme_berbeda(bridge):
    t = np.linspace(0, 0.02, 512, endpoint=False)

    bridge.feed_output_audio((0.5 * np.sin(2 * np.pi * 200 * t)).astype(np.float32))
    rendah = bridge._lip_viseme

    bridge.feed_output_audio((0.5 * np.sin(2 * np.pi * 4000 * t)).astype(np.float32))
    tinggi = bridge._lip_viseme

    assert rendah != tinggi


def test_lipsync_tidak_pernah_melempar_pada_masukan_aneh(bridge):
    # Callback audio tidak boleh melempar exception apa pun.
    bridge.feed_output_audio(np.array([], dtype=np.float32))
    bridge.feed_output_audio(None)


@pytest.mark.asyncio
async def test_lipsync_dikirim_berkala_ke_klien(bridge):
    ws = _FakeWS()
    await bridge.start()
    await bridge.add_client(ws)

    t = np.linspace(0, 0.02, 512, endpoint=False)
    bridge.feed_output_audio((0.6 * np.sin(2 * np.pi * 300 * t)).astype(np.float32))

    await asyncio.sleep(0.2)
    await bridge.stop()

    assert len(ws.tipe("lip")) >= 1
