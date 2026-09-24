"""ViewPort antarmuka web SELA.

Menggantikan antarmuka QML dengan antarmuka web (React + Three.js) tanpa
mengubah satu pun fungsi mesin AI. Kelas ini mengimplementasikan protokol
:class:`~src.ui.shared.viewport.ViewPort` yang sama dengan GUI/CLI/GPIO,
sehingga seluruh alur data presenter tetap bekerja apa adanya.
"""

from __future__ import annotations

import asyncio
import os
from typing import TYPE_CHECKING, Any, Optional

from src.core.event_bus import EventBus, Events
from src.logging import get_logger
from src.ui.shared.viewport import ViewPort
from src.ui.web.bridge import SelaBridge
from src.ui.web.launcher import open_ui
from src.ui.web.server import SelaWebServer

if TYPE_CHECKING:
    from src.core.task_manager import TaskManager

logger = get_logger()

DEFAULT_PORT = int(os.environ.get("SELA_WEBUI_PORT", "8765"))
# Ukuran jendela bawaan: potret (kios layar sentuh) bila SELA_PORTRAIT=1,
# jika tidak, lanskap desktop.
_IS_PORTRAIT = os.environ.get("SELA_PORTRAIT", "0") == "1"
_WIN_W, _WIN_H = (480, 900) if _IS_PORTRAIT else (1280, 800)


class WebViewManager(ViewPort):
    """Antarmuka web SELA (React) sebagai ViewPort py-xiaozhi."""

    def __init__(
        self,
        event_bus: EventBus,
        task_manager: Optional["TaskManager"] = None,
    ) -> None:
        self._bus = event_bus
        self._tasks = task_manager
        self._running = False
        self._auto_mode = False
        self._codec = None

        self.bridge = SelaBridge(event_bus, task_manager=task_manager)
        self.server = SelaWebServer(
            self.bridge,
            port=DEFAULT_PORT,
            on_config_changed=self._on_config_changed_request,
        )

        # Langganan codec audio dipasang DI SINI, bukan di start().
        # Alasannya penting: AudioPlugin (prioritas 10) memancarkan
        # AUDIO_CODEC_CHANGED saat start_all(), sedangkan UIPlugin (prioritas 60)
        # baru memanggil start() setelahnya. Bila langganan dipasang di start(),
        # peristiwa itu sudah lewat dan lipsync tidak akan pernah terpasang.
        self._bus.on(Events.AUDIO_CODEC_CHANGED, self._on_codec_changed)

    # ------------------------------------------------------------------
    # Siklus hidup
    # ------------------------------------------------------------------
    async def start(self, mode: str = "web") -> None:
        if self._running:
            return
        self._running = True

        try:
            await self.bridge.start()
            await self.server.start()
        except OSError as e:
            # Port terpakai: coba sekali lagi dengan port acak.
            logger.warning(f"WebViewManager: port {self.server.port} gagal ({e}); coba port lain")
            self.server = SelaWebServer(
                self.bridge,
                port=0,
                on_config_changed=self._on_config_changed_request,
            )
            await self.server.start()

        url = self.server.url
        logger.info(f"WebViewManager: antarmuka siap di {url}")

        # Buka jendela di thread terpisah agar tidak memblokir loop asyncio.
        kiosk = os.environ.get("SELA_KIOSK") == "1"
        try:
            await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: open_ui(
                    url,
                    title="SELA AI - Asisten Kampus",
                    width=_WIN_W,
                    height=_WIN_H,
                    kiosk=kiosk,
                ),
            )
        except Exception as e:
            logger.warning(
                f"WebViewManager: jendela tidak bisa dibuka otomatis ({e}). "
                f"Buka manual di peramban: {url}"
            )

    async def close(self) -> None:
        logger.info("WebViewManager: menutup antarmuka web...")
        self._running = False
        try:
            self._bus.off(Events.AUDIO_CODEC_CHANGED, self._on_codec_changed)
        except Exception:
            pass
        self._detach_codec()
        await self.server.stop()
        await self.bridge.stop()
        logger.info("WebViewManager: ditutup")

    # ------------------------------------------------------------------
    # Audio -> lipsync
    # ------------------------------------------------------------------
    async def _on_codec_changed(self, codec: Any = None) -> None:
        """Codec audio diganti (start/stop) -> pasang/lepas pendengar output."""
        self._detach_codec()
        if codec is None:
            return
        try:
            codec.add_output_listener(self.bridge.feed_output_audio)
            self._codec = codec
            logger.info("WebViewManager: pendengar audio output terpasang (lipsync aktif)")
        except Exception as e:
            logger.warning(f"WebViewManager: gagal memasang pendengar audio: {e}")

    def _detach_codec(self) -> None:
        if self._codec is not None:
            try:
                self._codec.remove_output_listener(self.bridge.feed_output_audio)
            except Exception:
                pass
            self._codec = None

    async def _on_config_changed_request(self) -> None:
        """Dipanggil server web setelah config ditulis dari halaman setelan.

        Menerbitkan CONFIG_CHANGED agar AudioPlugin memuat ulang perangkat
        (persis seperti tombol "Terapkan" pada antarmuka QML).
        """
        try:
            await self._bus.emit(Events.CONFIG_CHANGED, None)
            logger.info("WebViewManager: CONFIG_CHANGED dipancarkan (setelan diterapkan)")
        except Exception as e:
            logger.warning(f"WebViewManager: gagal memancarkan CONFIG_CHANGED: {e}")

    # ------------------------------------------------------------------
    # ViewPort
    # ------------------------------------------------------------------
    @property
    def is_running(self) -> bool:
        return self._running

    def _fire(self, payload: dict[str, Any]) -> None:
        """Kirim payload ke peramban tanpa memblokir pemanggil sinkron."""
        if not self._running:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop.create_task(self.bridge.broadcast(payload))

    def set_status(self, status: str, connected: bool = True) -> None:
        self._fire({"t": "status", "status": status, "connected": connected})

    def set_emotion(self, emotion: str) -> None:
        self._fire({"t": "emotion", "emotion": emotion})

    def set_chat_text(self, text: str) -> None:
        self._fire({"t": "chat", "role": "assistant", "text": text})

    def set_music_line(self, text: str) -> None:
        self._fire({"t": "music_line", "text": text})

    def set_button_text(self, text: str) -> None:
        self._fire({"t": "button_text", "text": text})

    def set_auto_mode(self, auto_mode: bool) -> None:
        self._auto_mode = bool(auto_mode)
        self._fire({"t": "auto_mode", "autoMode": bool(auto_mode)})

    def is_auto_mode(self) -> bool:
        return self._auto_mode
