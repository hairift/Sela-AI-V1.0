"""Jembatan antara EventBus py-xiaozhi dan antarmuka web SELA.

Modul ini **tidak mengubah** arsitektur inti py-xiaozhi: ia hanya menjadi
pelanggan (subscriber) EventBus yang sudah ada, lalu meneruskan status ke
peramban lewat WebSocket. Perintah dari peramban diterjemahkan kembali menjadi
event UI yang sama dengan yang dipakai antarmuka QML/CLI, sehingga seluruh
fungsi (kirim teks, rekam manual, mode otomatis, batal, keluar, setelan) tetap
utuh dan tidak ada tombol yang hilang.

Arah data:

    Python -> Web : status, teks dialog, emosi, mode, lipsync, langkah alat,
                    permintaan foto
    Web -> Python : kirim teks, mulai/hentikan rekam, mode, batal, keluar,
                    bingkai kamera peramban
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

# Panjang maksimum teks yang boleh dikirim lewat kotak obrolan.
#
# Server xiaozhi menolak teks panjang pada jalur ``listen/detect`` dengan
# jawaban: "Detect is only for wake words, do not send long texts." Akibatnya
# pengguna yang mengetik pertanyaan panjang tidak mendapat jawaban apa pun.
# Antarmuka membatasi kotak teks pada angka ini, dan jembatan ini memotong
# sebagai jaring pengaman bila batas itu dilewati. Pertanyaan sepanjang apa pun
# tetap aman lewat tombol mikrofon karena jalur suara tidak melewati batas ini.
MAKS_PANJANG_TEKS = 24


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


# Nama alat MCP -> kalimat yang ditampilkan saat alat itu dipanggil.
#
# Antarmuka memperlihatkan langkah ini sebagai animasi supaya pengguna melihat
# SELA benar-benar membuka data kampus/pencarian, bukan sekadar diam menunggu.
# Ini murni tampilan: alur pemanggilan alat tetap sepenuhnya milik py-xiaozhi.
LABEL_ALAT = {
    "cari_info_kampus": "Membuka data kampus UCIC",
    "info_kampus": "Memeriksa basis pengetahuan kampus",
    "take_photo": "Mengambil gambar dari kamera",
    "cuaca_sekarang": "Mengambil data cuaca terkini",
    "prakiraan_cuaca": "Menyusun prakiraan cuaca",
    "cari_web": "Menelusuri sumber di internet",
    "cari_berita": "Mencari berita terbaru",
    "take_screenshot": "Mengambil tangkapan layar",
    "self.application.launch": "Membuka aplikasi",
    "self.application.scan_installed": "Mendata aplikasi terpasang",
    "self.application.kill": "Menutup aplikasi",
}

# Pola permintaan difoto/dilihat lewat kamera. Dipakai agar permintaan seperti
# "tolong foto saya" langsung memicu kamera peramban, tanpa bergantung pada
# terjemahan nama alat di model.
_POLA_MINTA_FOTO = re.compile(
    r"(foto|potret|selfie|kamera|ambil gambar|lihat(kan)? saya|lihat muka|"
    r"lihat wajah|wajah saya|muka saya|tengok saya|lihat aku|"
    r"take a photo|take photo)",
    re.IGNORECASE,
)


def _minta_foto_dari_teks(teks: str) -> bool:
    """Apakah pengguna meminta SELA melihat/memotret lewat kamera."""
    return bool(_POLA_MINTA_FOTO.search(teks or ""))


def label_alat(nama: str) -> str:
    """Kalimat Indonesia untuk sebuah nama alat MCP."""
    penuh = (nama or "").strip()
    # Nama beralias titik (mis. "self.application.launch") dicocokkan utuh
    # lebih dulu, karena memotong di titik justru menghilangkan kuncinya.
    if penuh in LABEL_ALAT:
        return LABEL_ALAT[penuh]
    inti = penuh.split(".")[-1].strip()
    if not inti:
        return "Menjalankan alat"
    if inti in LABEL_ALAT:
        return LABEL_ALAT[inti]
    if penuh.startswith("music_player") or inti.startswith("musik"):
        return "Menyiapkan pemutar musik"
    if inti.startswith("cari") or "search" in inti:
        return "Mencari informasi"
    if inti.startswith("volume"):
        return "Mengatur volume suara"
    return f"Menjalankan {inti.replace('_', ' ')}"


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
    # Kamera peramban
    # ------------------------------------------------------------------
    async def minta_foto(self, sumber: str = "ai") -> None:
        """Minta antarmuka mengambil satu gambar dari kamera peramban.

        ``sumber`` hanya untuk keterangan di antarmuka: "ai" (mesin AI memanggil
        alat kamera) atau "pengguna" (pengguna meminta difoto lewat teks).
        """
        await self.broadcast({"t": "ambil_foto", "source": sumber, "ts": time.time()})

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
                # Jaring pengaman: potong bila antarmuka mengirim lebih panjang
                # dari batas server (lihat MAKS_PANJANG_TEKS).
                if len(text) > MAKS_PANJANG_TEKS:
                    logger.info(
                        f"SelaBridge: teks {len(text)} karakter dipotong ke "
                        f"{MAKS_PANJANG_TEKS} agar server mau menjawab"
                    )
                    text = text[:MAKS_PANJANG_TEKS]
                if text:
                    from src.ui.shared.events import UISendTextRequest

                    # Simpan agar gema teks yang sama dari server bisa disaring.
                    self._teks_terakhir = text
                    await self._emit(Events.UI_SEND_TEXT, UISendTextRequest(text=text))
                    await self.broadcast({"t": "user_text", "text": text})
                    # Pengguna minta difoto/dilihat: minta gambar dari kamera
                    # peramban supaya jawabannya benar-benar melihat keadaan
                    # sekarang, bukan mengarang.
                    if _minta_foto_dari_teks(text):
                        await self.minta_foto(sumber="pengguna")

            elif cmd == "kamera_bingkai":
                # Satu bingkai JPEG dari kamera peramban (data URL base64).
                from src.ui.web.kamera_peramban import simpan_bingkai

                if simpan_bingkai(str(msg.get("data") or "")):
                    await self.broadcast({"t": "kamera_ok", "ts": time.time()})

            elif cmd == "kamera_aktif":
                # Menyalakan/mematikan pemakaian kamera peramban dari setelan.
                from src.ui.web.kamera_peramban import set_aktif

                set_aktif(bool(msg.get("aktif")))
                await self.broadcast(
                    {"t": "kamera_status", "aktif": bool(msg.get("aktif"))}
                )

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

            elif cmd == "siap_siaga":
                # Dipancarkan setiap pengguna berpindah halaman agar
                # sambungan dan sesi dengar selalu siap.
                await self._emit(Events.UI_READY_REQUEST)

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
        elif msg_type == "mcp":
            await self._on_mcp_message(message)

    async def _on_mcp_message(self, message: dict) -> None:
        """Catat alat yang sedang dipanggil mesin AI.

        Server mengirim permintaan MCP lewat ``{"type": "mcp", "payload": ...}``
        berisi ``method: "tools/call"`` dan nama alat pada ``params.name``.
        Antarmuka menampilkannya sebagai animasi singkat sehingga pengguna tahu
        SELA sedang membuka data, bukan berhenti. Pemanggilan alatnya sendiri
        tetap dikerjakan py-xiaozhi; di sini hanya diteruskan sebagai tampilan.
        """
        payload = message.get("payload")
        if not isinstance(payload, dict):
            return
        if payload.get("method") != "tools/call":
            return
        params = payload.get("params") or {}
        if not isinstance(params, dict):
            return
        nama = str(params.get("name") or "").strip()
        if not nama:
            return
        await self.broadcast(
            {
                "t": "tool",
                "name": nama,
                "label": label_alat(nama),
                "ts": time.time(),
            }
        )
        # Alat kamera: minta antarmuka mengambil satu gambar sekaligus, supaya
        # bingkai dari kamera peramban siap saat alat itu benar-benar jalan.
        if nama.split(".")[-1] == "take_photo":
            await self.minta_foto(sumber="ai")

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
