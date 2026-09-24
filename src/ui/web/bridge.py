"""Jembatan antara EventBus py-xiaozhi dan antarmuka web SELA.

Modul ini **tidak mengubah** arsitektur inti py-xiaozhi: ia hanya menjadi
pelanggan (subscriber) EventBus yang sudah ada, lalu meneruskan status ke
peramban lewat WebSocket. Perintah dari peramban diterjemahkan kembali menjadi
event UI yang sama dengan yang dipakai antarmuka QML/CLI, sehingga seluruh
fungsi (kirim teks, rekam manual, mode otomatis, batal, keluar, setelan) tetap
utuh dan tidak ada tombol yang hilang.

Arah data:

    Python -> Web : status, teks dialog, emosi, mode, lipsync
    Web -> Python : kirim teks, mulai/hentikan rekam, mode, batal, keluar
"""

from __future__ import annotations

import asyncio
import math
import re
import time
from typing import Any, Optional

import numpy as np

from src.core.event_bus import EventBus, Events
from src.logging import get_logger

logger = get_logger()

# Frekuensi kirim data lipsync (Hz). 30 cukup halus untuk gerak mulut dan
# hemat CPU di Raspberry Pi.
LIP_FPS = 30
LIP_INTERVAL = 1.0 / LIP_FPS

# Ambang RMS minimum agar mulut mulai bergerak (skala float32 -1..1).
LIP_RMS_FLOOR = 0.004
# Pengali RMS -> bukaan mulut. Dikali silang agar cocok untuk suara TTS normal.
LIP_GAIN = 9.0


def _nama_device_state(state: Any) -> str:
    """Ambil nama DeviceState dalam huruf kecil dari berbagai bentuk data.

    EventBus mengirim ``device_state_changed`` dengan data berupa dict
    ``{"old_state": ..., "new_state": ...}``. Bila dict itu langsung diubah
    menjadi string, antarmuka menerima repr Python seperti
    ``"{'old_state': <DeviceState.IDLE: 'idle'>, ...}"`` yang tidak dikenali
    pemetaan state, sehingga avatar selalu dianggap idle dan **mulut tidak
    bergerak saat SELA bicara**.
    """
    nilai = state
    if isinstance(nilai, dict):
        nilai = (
            nilai.get("new_state")
            or nilai.get("state")
            or nilai.get("new")
            or nilai.get("value")
        )
    if nilai is None:
        return "idle"
    nama = getattr(nilai, "name", None) or getattr(nilai, "value", None)
    if nama is None:
        # Cadangan terakhir: ambil kata pertama dari repr, buang sisa sintaks.
        teks = str(nilai)
        potongan = teks.replace("<", " ").replace(">", " ").replace("'", " ").split()
        nama = potongan[0] if potongan else "idle"
    return str(nama).strip().lower()


# Pola teks dari server yang bukan jawaban untuk pengguna, sehingga tidak boleh
# muncul sebagai gelembung obrolan:
#   - nama tool yang dipanggil model, mis. "% cari_info_kampus..."
#   - penanda internal berawalan kurung siku, mis. "[IGNORE_NOISE]"
_POLA_BUKAN_JAWABAN = re.compile(r"^\s*(%|\[IGNORE_NOISE\]|\[Pertanyaan)", re.IGNORECASE)


def _teks_bukan_untuk_ditampilkan(teks: str, teks_pengguna_terakhir: str = "") -> bool:
    """Saring teks yang tidak layak tampil sebagai gelembung obrolan.

    Dua kasus nyata yang pernah muncul di antarmuka:
    1. Pertanyaan pengguna dipantulkan kembali oleh server sehingga muncul
       sebagai jawaban SELA (gelembung ganda).
    2. Nama tool yang dipanggil model ikut terkirim sebagai teks, mis.
       "% cari_info_kampus..." - membingungkan pengguna.
    """
    bersih = (teks or "").strip()
    if not bersih:
        return True
    if _POLA_BUKAN_JAWABAN.match(bersih):
        return True
    # Gema: teks sama persis dengan yang baru saja diketik pengguna.
    if teks_pengguna_terakhir and bersih.casefold() == teks_pengguna_terakhir.strip().casefold():
        return True
    return False


class SelaBridge:
    """Meneruskan status mesin AI ke antarmuka web dan sebaliknya."""

    def __init__(self, event_bus: EventBus, task_manager: Any = None) -> None:
        self._bus = event_bus
        self._tasks = task_manager

        # Klien WebSocket yang sedang terhubung.
        self._clients: set[Any] = set()
        self._clients_lock = asyncio.Lock()

        # Status terakhir: dikirim ulang saat klien baru tersambung.
        self._snapshot: dict[str, Any] = {
            "status": "Siap",
            "connected": False,
            "emotion": "neutral",
            "deviceState": "idle",
            "autoMode": False,
            "buttonText": "",
            "musicLine": "",
        }

        # Slot lipsync (diisi dari thread audio, dibaca dari loop asyncio).
        self._lip_volume = 0.0
        self._lip_viseme = "sil"
        self._lip_at = 0.0

        # Teks terakhir yang dikirim pengguna, untuk menyaring gemanya.
        self._teks_terakhir = ""

        self._lip_task: Optional[asyncio.Task] = None
        self._running = False

    def teks_layak_tampil(self, teks: str) -> bool:
        """Apakah teks dari mesin AI layak muncul sebagai gelembung obrolan.

        Dipakai juga oleh WebViewManager, karena jalur presenter
        (``set_chat_text``) mengirim teks ke antarmuka secara terpisah dari
        jalur EventBus di kelas ini.
        """
        return not _teks_bukan_untuk_ditampilkan(teks, self._teks_terakhir)

    # ------------------------------------------------------------------
    # Siklus hidup
    # ------------------------------------------------------------------
    async def start(self) -> None:
        """Berlangganan EventBus dan mulai pengiriman lipsync berkala."""
        if self._running:
            return
        self._running = True

        self._bus.on(Events.DEVICE_STATE_CHANGED, self._on_device_state)
        self._bus.on(Events.INCOMING_JSON, self._on_incoming_json)
        self._bus.on(Events.NETWORK_ERROR, self._on_network_error)
        self._bus.on(Events.SYSTEM_NOTICE, self._on_system_notice)
        self._bus.on(Events.PROTOCOL_CONNECTED, self._on_protocol_connected)
        self._bus.on(Events.PROTOCOL_DISCONNECTED, self._on_protocol_disconnected)
        self._bus.on(Events.MUSIC_STATE_CHANGED, self._on_music_state)
        self._bus.on(Events.MUSIC_LYRICS_UPDATE, self._on_music_lyrics)

        self._lip_task = asyncio.create_task(self._loop_lipsync(), name="sela:lipsync")
        logger.info("SelaBridge: siap (EventBus terhubung)")

    async def stop(self) -> None:
        self._running = False
        if self._lip_task:
            self._lip_task.cancel()
            try:
                await self._lip_task
            except (asyncio.CancelledError, Exception):
                pass
            self._lip_task = None
        async with self._clients_lock:
            self._clients.clear()
        logger.info("SelaBridge: dihentikan")

    # ------------------------------------------------------------------
    # Manajemen klien
    # ------------------------------------------------------------------
    async def add_client(self, ws: Any) -> None:
        async with self._clients_lock:
            self._clients.add(ws)
        logger.info(f"SelaBridge: antarmuka web tersambung ({len(self._clients)} klien)")
        # Kirim snapshot awal supaya UI langsung sinkron.
        try:
            await ws.send_json({"t": "snapshot", **self._snapshot})
        except Exception as e:  # pragma: no cover - koneksi bisa putus kapan saja
            logger.debug(f"SelaBridge: gagal kirim snapshot: {e}")

    async def remove_client(self, ws: Any) -> None:
        async with self._clients_lock:
            self._clients.discard(ws)
        logger.info(f"SelaBridge: antarmuka web terputus ({len(self._clients)} klien)")

    @property
    def client_count(self) -> int:
        return len(self._clients)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        """Kirim satu paket ke semua klien; klien mati dibersihkan otomatis."""
        if not self._clients:
            return
        async with self._clients_lock:
            targets = list(self._clients)
        dead = []
        for ws in targets:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._clients_lock:
                for ws in dead:
                    self._clients.discard(ws)

    # ------------------------------------------------------------------
    # Perintah dari antarmuka web (Web -> Python)
    # ------------------------------------------------------------------
    async def handle_command(self, msg: dict[str, Any]) -> None:
        """Terjemahkan perintah UI web menjadi event py-xiaozhi."""
        cmd = str(msg.get("t") or msg.get("cmd") or "").strip()
        if not cmd:
            return

        try:
            if cmd == "send_text":
                text = str(msg.get("text") or "").strip()
                if text:
                    from src.ui.shared.events import UISendTextRequest

                    # Simpan agar gema teks yang sama dari server bisa disaring.
                    self._teks_terakhir = text
                    await self._emit(Events.UI_SEND_TEXT, UISendTextRequest(text=text))
                    await self.broadcast({"t": "user_text", "text": text})

            elif cmd == "manual_toggle":
                await self._emit(Events.UI_MANUAL_TOGGLE)

            elif cmd == "button_press":
                await self._emit(Events.UI_BUTTON_PRESS)

            elif cmd == "button_release":
                await self._emit(Events.UI_BUTTON_RELEASE)

            elif cmd == "auto_start":
                await self._emit(Events.UI_AUTO_START)

            elif cmd == "auto_toggle":
                await self._emit(Events.UI_AUTO_TOGGLE)

            elif cmd == "abort":
                await self._emit(Events.UI_ABORT_REQUEST)

            elif cmd == "open_settings":
                await self._emit(Events.UI_OPEN_SETTINGS)

            elif cmd == "quit":
                await self._emit(Events.UI_QUIT_REQUEST)

            elif cmd == "ping":
                await self.broadcast({"t": "pong", "ts": time.time()})

            else:
                logger.debug(f"SelaBridge: perintah tak dikenal {cmd!r}")
        except Exception as e:
            logger.warning(f"SelaBridge: gagal memproses perintah {cmd!r}: {e}", exc_info=True)

    async def _emit(self, event: str, data: Any = None) -> None:
        if self._tasks is not None:
            self._tasks.spawn(self._bus.emit(event, data), name=f"web:{event}")
        else:
            await self._bus.emit(event, data)

    # ------------------------------------------------------------------
    # Handler EventBus (Python -> Web)
    # ------------------------------------------------------------------
    async def _on_device_state(self, state: Any) -> None:
        name = _nama_device_state(state)
        self._snapshot["deviceState"] = name
        await self.broadcast({"t": "state", "state": name})

    async def _on_incoming_json(self, message: Any) -> None:
        if not isinstance(message, dict):
            return
        msg_type = message.get("type")

        if msg_type == "tts":
            text = message.get("text")
            if text and not _teks_bukan_untuk_ditampilkan(text, self._teks_terakhir):
                self._snapshot["lastTts"] = text
                await self.broadcast({"t": "chat", "role": "assistant", "text": text})
        elif msg_type == "stt":
            text = message.get("text")
            if text and not _teks_bukan_untuk_ditampilkan(text, self._teks_terakhir):
                self._snapshot["lastStt"] = text
                await self.broadcast({"t": "chat", "role": "user", "text": text})
        elif msg_type == "llm":
            emotion = message.get("emotion")
            if emotion:
                self._snapshot["emotion"] = emotion
                await self.broadcast({"t": "emotion", "emotion": emotion})

    async def _on_network_error(self, error_message: Any = None) -> None:
        self._snapshot["connected"] = False
        await self.broadcast({"t": "status", "status": "Tidak terhubung", "connected": False})

    async def _on_system_notice(self, message: Any = None) -> None:
        if message:
            await self.broadcast({"t": "notice", "text": str(message)})

    async def _on_protocol_connected(self, data: Any = None) -> None:
        self._snapshot["connected"] = True
        await self.broadcast({"t": "status", "status": "Terhubung", "connected": True})

    async def _on_protocol_disconnected(self, data: Any = None) -> None:
        self._snapshot["connected"] = False
        await self.broadcast({"t": "status", "status": "Terputus", "connected": False})

    async def _on_music_state(self, data: Any) -> None:
        try:
            state = getattr(data, "state", None)
            song = getattr(data, "song", "")
            if state:
                await self.broadcast({"t": "music", "state": state, "song": song})
        except Exception as e:
            logger.debug(f"SelaBridge: music state dilewati: {e}")

    async def _on_music_lyrics(self, data: Any) -> None:
        try:
            text = getattr(data, "text", None)
            if text:
                await self.broadcast({"t": "lyrics", "text": text})
        except Exception as e:
            logger.debug(f"SelaBridge: lyrics dilewati: {e}")

    # ------------------------------------------------------------------
    # Lipsync (dari thread audio, dikirim berkala)
    # ------------------------------------------------------------------
    def feed_output_audio(self, pcm: np.ndarray) -> None:
        """Dipanggil dari callback audio (thread PortAudio).

        Ringan dan tidak memblokir: hanya menghitung RMS + centroid spektral
        lalu menyimpannya. Pengiriman ke peramban dilakukan oleh loop asyncio.
        """
        try:
            if pcm is None or len(pcm) == 0:
                return
            mono = np.asarray(pcm, dtype=np.float32).reshape(-1)
            rms = float(np.sqrt(np.mean(mono * mono)))
            if rms < LIP_RMS_FLOOR:
                self._lip_volume = 0.0
                self._lip_viseme = "sil"
                return

            # Centroid spektral sederhana -> perkiraan bentuk mulut (viseme).
            n = min(len(mono), 1024)
            spectrum = np.abs(np.fft.rfft(mono[:n] * np.hanning(n)))
            freqs = np.fft.rfftfreq(n, d=1.0 / 16000.0)
            total = float(spectrum.sum())
            centroid = float((spectrum * freqs).sum() / total) if total > 0 else 0.0

            if centroid < 450:
                viseme = "o"
            elif centroid < 900:
                viseme = "u"
            elif centroid < 1600:
                viseme = "a"
            elif centroid < 2600:
                viseme = "e"
            else:
                viseme = "i"

            self._lip_volume = min(1.0, rms * LIP_GAIN)
            self._lip_viseme = viseme
            self._lip_at = time.time()
        except Exception:
            # Thread audio: jangan pernah melempar exception ke callback.
            self._lip_volume = 0.0
            self._lip_viseme = "sil"

    async def _loop_lipsync(self) -> None:
        """Kirim data lipsync secara berkala selama ada klien."""
        last_sent = 0.0
        while self._running:
            try:
                await asyncio.sleep(LIP_INTERVAL)
                if not self._clients:
                    continue
                # Audio berhenti >250ms -> mulut menutup.
                if self._lip_volume > 0 and time.time() - self._lip_at > 0.25:
                    self._lip_volume = 0.0
                    self._lip_viseme = "sil"
                # Hindari paket identik beruntun saat hening.
                if self._lip_volume <= 0 and last_sent <= 0:
                    continue
                last_sent = self._lip_volume
                await self.broadcast(
                    {
                        "t": "lip",
                        "v": round(self._lip_volume, 3),
                        "viseme": self._lip_viseme,
                    }
                )
            except asyncio.CancelledError:
                raise
            except Exception as e:  # pragma: no cover
                logger.debug(f"SelaBridge: loop lipsync dilewati: {e}")
                await asyncio.sleep(0.2)
