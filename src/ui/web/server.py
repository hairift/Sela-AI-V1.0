"""Server lokal untuk antarmuka web SELA.

Menyajikan berkas statis hasil build `webui/dist` dan satu endpoint WebSocket
`/ws` yang dijembatani ke EventBus py-xiaozhi oleh :class:`SelaBridge`.

Server hanya mengikat ke 127.0.0.1 (localhost) sehingga antarmuka tidak
terbuka ke jaringan. Ini juga membuatnya aman dipasang pada kios kampus.
"""

from __future__ import annotations

import asyncio

import json
from pathlib import Path
from typing import Any, Optional

from aiohttp import WSMsgType, web

from src.logging import get_logger
from src.ui.web.bridge import SelaBridge
from src.utils.resource_finder import get_app_root

logger = get_logger()

# Halaman pengganti bila `webui/dist` belum dibangun.
_FALLBACK_HTML = """<!DOCTYPE html>
<html lang="id"><head><meta charset="utf-8">
<title>SELA AI - Antarmuka belum dibangun</title>
<style>
 body{font-family:system-ui,sans-serif;background:#0f172a;color:#e2e8f0;
      display:flex;align-items:center;justify-content:center;height:100vh;margin:0}
 .box{max-width:640px;padding:32px;border-radius:20px;background:#1e293b;
      border:1px solid #334155;line-height:1.6}
 code{background:#0f172a;padding:2px 6px;border-radius:6px;color:#7dd3fc}
 h1{margin-top:0;font-size:20px}
</style></head><body><div class="box">
<h1>Antarmuka SELA belum dibangun</h1>
<p>Folder <code>webui/dist</code> tidak ditemukan. Jalankan langkah berikut
satu kali sebelum menjalankan aplikasi:</p>
<pre><code>cd webui
npm install
npm run build</code></pre>
<p>Setelah selesai, muat ulang halaman ini.</p>
</div></body></html>"""


def _resolve_dist_dir() -> Path:
    """Lokasi hasil build antarmuka web (dev maupun setelah dikemas)."""
    return get_app_root() / "webui" / "dist"


class SelaWebServer:
    """Pembungkus aiohttp untuk antarmuka web SELA."""

    def __init__(
        self,
        bridge: SelaBridge,
        host: str = "127.0.0.1",
        port: int = 8765,
        on_config_changed: Optional[Any] = None,
    ):
        self._bridge = bridge
        self._host = host
        self._port = port
        self._on_config_changed = on_config_changed
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None
        self._app: Optional[web.Application] = None
        self._dist = _resolve_dist_dir()

    @property
    def port(self) -> int:
        return self._port

    @property
    def host(self) -> str:
        return self._host

    @property
    def dist_dir(self) -> Path:
        return self._dist

    @property
    def url(self) -> str:
        return f"http://{self._host}:{self._port}/"

    # ------------------------------------------------------------------
    def build_app(self) -> web.Application:
        app = web.Application()
        app.router.add_get("/ws", self._ws_handler)
        app.router.add_get("/api/status", self._status_handler)
        app.router.add_get("/api/config", self._config_get_handler)
        app.router.add_post("/api/config", self._config_post_handler)
        app.router.add_post("/api/admin/verifikasi", self._admin_verifikasi_handler)
        app.router.add_get("/api/log", self._log_handler)
        app.router.add_get("/api/devices", self._devices_handler)
        app.router.add_get("/api/audio/uji-mikrofon", self._uji_mikrofon_handler)
        app.router.add_get("/", self._index_handler)
        # Aset statis (JS/CSS/model 3D).
        if self._dist.is_dir():
            app.router.add_static("/", self._dist, show_index=False)
        else:
            logger.warning(
                f"SelaWebServer: {self._dist} tidak ada - jalankan 'npm run build' di webui/"
            )
        app.router.add_get("/{tail:.*}", self._spa_fallback)
        self._app = app
        return app

    async def start(self) -> None:
        app = self.build_app()
        self._runner = web.AppRunner(app, access_log=None)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, self._host, self._port)
        await self._site.start()

        # Bila port diminta 0, sistem operasi memilih port bebas. Ambil port
        # NYATA dari soket agar self.url tidak menghasilkan "http://...:0/"
        # yang tidak bisa dibuka peramban.
        try:
            soket = self._site._server.sockets[0]  # type: ignore[union-attr]
            port_nyata = int(soket.getsockname()[1])
            if port_nyata and port_nyata != self._port:
                logger.info(f"SelaWebServer: port {self._port} -> {port_nyata}")
                self._port = port_nyata
        except Exception as e:
            logger.debug(f"SelaWebServer: tidak bisa membaca port nyata: {e}")

        logger.info(f"SelaWebServer: aktif di {self.url}")

    async def stop(self) -> None:
        try:
            if self._runner:
                await self._runner.cleanup()
        except Exception as e:
            logger.debug(f"SelaWebServer: penutupan dilewati: {e}")
        finally:
            self._runner = None
            self._site = None
            logger.info("SelaWebServer: dihentikan")

    # ------------------------------------------------------------------
    # Handler
    # ------------------------------------------------------------------
    async def _index_handler(self, request: web.Request) -> web.StreamResponse:
        index = self._dist / "index.html"
        if index.is_file():
            return web.FileResponse(index)
        return web.Response(text=_FALLBACK_HTML, content_type="text/html")

    async def _spa_fallback(self, request: web.Request) -> web.StreamResponse:
        """Rute tak dikenal -> index.html (aplikasi satu halaman)."""
        rel = request.match_info.get("tail", "")
        candidate = (self._dist / rel).resolve() if rel else None
        # Cegah path traversal keluar dari dist.
        if candidate and self._dist.is_dir():
            try:
                candidate.relative_to(self._dist.resolve())
                if candidate.is_file():
                    return web.FileResponse(candidate)
            except ValueError:
                pass
        return await self._index_handler(request)

    async def _status_handler(self, request: web.Request) -> web.StreamResponse:
        return web.json_response(
            {
                "app": "SELA AI",
                "ui": "web",
                "clients": self._bridge.client_count,
                "dist_ok": self._dist.is_dir(),
            }
        )

    # --- Setelan (membaca & menulis config py-xiaozhi yang sesungguhnya) ---

    # Pemetaan kunci ramah-UI -> jalur config asli.
    _PETA_SETELAN = {
        "wakeWord": "WAKE_WORD_OPTIONS.USE_WAKE_WORD",
        "aec": "AEC_OPTIONS.ENABLED",
        "inputDevice": "AUDIO_DEVICES.input_device_name",
        "outputDevice": "AUDIO_DEVICES.output_device_name",
        "wakeWordText": "WAKE_WORD_OPTIONS.WAKE_WORD",
        "wakeWordThreshold": "WAKE_WORD_OPTIONS.KEYWORDS_THRESHOLD",
        "serverUrl": "SYSTEM_OPTIONS.NETWORK.WEBSOCKET_URL",
        "musicPlatform": "MUSIC.DEFAULT_PLATFORM",
        "musicQuality": "MUSIC.DEFAULT_QUALITY",
    }

    async def _config_get_handler(self, request: web.Request) -> web.StreamResponse:
        try:
            from src.constants.system import SystemConstants
            from src.utils.config_manager import get_config

            cfg = get_config()
            data = {
                "wakeWord": bool(cfg.get_config("WAKE_WORD_OPTIONS.USE_WAKE_WORD", False)),
                "wakeWordText": cfg.get_config("WAKE_WORD_OPTIONS.WAKE_WORD", "") or "",
                "wakeWordThreshold": float(
                    cfg.get_config("WAKE_WORD_OPTIONS.KEYWORDS_THRESHOLD", 0.2) or 0.2
                ),
                "aec": bool(cfg.get_config("AEC_OPTIONS.ENABLED", False)),
                "inputDevice": cfg.get_config("AUDIO_DEVICES.input_device_name", "") or "",
                "outputDevice": cfg.get_config("AUDIO_DEVICES.output_device_name", "") or "",
                "serverUrl": cfg.get_config("SYSTEM_OPTIONS.NETWORK.WEBSOCKET_URL", "") or "",
                "connected": bool(
                    cfg.get_config("SYSTEM_OPTIONS.NETWORK.WEBSOCKET_ACCESS_TOKEN", None)
                ),
                "version": SystemConstants.APP_VERSION,
                "appName": SystemConstants.APP_DISPLAY_NAME,
                "musicPlatform": cfg.get_config("MUSIC.DEFAULT_PLATFORM", "kw") or "kw",
                "musicQuality": cfg.get_config("MUSIC.DEFAULT_QUALITY", "320k") or "320k",
            }
            return web.json_response({"ok": True, "config": data})
        except Exception as e:
            logger.warning(f"SelaWebServer: gagal membaca config: {e}")
            return web.json_response({"ok": False, "error": str(e)}, status=500)

    # Kata sandi admin untuk membuka halaman pengaturan. Nilainya sengaja
    # TIDAK ditanam di kode antarmuka (JavaScript bisa dibaca siapa pun),
    # melainkan diperiksa di sini.
    _SANDI_ADMIN = "cirebon250904"

    async def _admin_verifikasi_handler(self, request: web.Request) -> web.StreamResponse:
        """Periksa kata sandi admin untuk membuka pengaturan."""
        try:
            payload = await request.json()
        except Exception:
            return web.json_response(
                {"ok": False, "error": "Permintaan tidak valid"}, status=400
            )
        sandi = str((payload or {}).get("sandi") or "")
        if sandi == self._SANDI_ADMIN:
            return web.json_response({"ok": True})
        logger.info("SelaWebServer: percobaan buka pengaturan dengan sandi salah")
        return web.json_response(
            {"ok": False, "error": "Kata sandi salah. Coba lagi."}, status=403
        )

    async def _log_handler(self, request: web.Request) -> web.StreamResponse:
        """Kembalikan sejumlah baris terakhir log aplikasi.

        Dipakai halaman pengaturan untuk menampilkan log waktu nyata, supaya
        pengguna bisa melihat sendiri penyebab masalah tanpa membuka berkas
        log secara manual.
        """
        try:
            jumlah = int(request.query.get("baris", "200"))
        except Exception:
            jumlah = 200
        jumlah = max(20, min(1000, jumlah))

        jalur = None
        try:
            from src.utils.resource_finder import get_user_data_dir

            kandidat = get_user_data_dir() / "logs" / "app.log"
            if kandidat.is_file():
                jalur = kandidat
        except Exception:
            jalur = None

        if jalur is None:
            # Cadangan: lokasi standar aplikasi di Windows.
            import pathlib as _pl

            kandidat = _pl.Path.home() / "AppData/Local/sela-ai/sela-ai/logs/app.log"
            jalur = kandidat if kandidat.is_file() else None

        if jalur is None:
            return web.json_response(
                {"ok": False, "error": "Berkas log tidak ditemukan.", "lines": []}
            )

        try:
            import collections

            with open(jalur, "r", encoding="utf-8", errors="replace") as f:
                baris = list(collections.deque(f, maxlen=jumlah))
            return web.json_response(
                {
                    "ok": True,
                    "path": str(jalur),
                    "lines": [b.rstrip("\n") for b in baris],
                }
            )
        except Exception as e:
            logger.warning(f"SelaWebServer: gagal membaca log: {e}")
            return web.json_response(
                {"ok": False, "error": str(e), "lines": []}, status=500
            )

    async def _config_post_handler(self, request: web.Request) -> web.StreamResponse:
        try:
            payload = await request.json()
        except Exception:
            return web.json_response({"ok": False, "error": "JSON tidak valid"}, status=400)

        updates = payload.get("updates") if isinstance(payload, dict) else None
        if not isinstance(updates, dict):
            return web.json_response({"ok": False, "error": "Field 'updates' wajib"}, status=400)

        try:
            from src.utils.config_manager import get_config

            cfg = get_config()
            diterapkan = []
            for kunci, nilai in updates.items():
                path = self._PETA_SETELAN.get(kunci)
                if not path:
                    continue
                cfg.update_config(path, nilai)
                diterapkan.append(kunci)

            # Beri tahu mesin AI agar perangkat audio dimuat ulang.
            if diterapkan and self._on_config_changed:
                await self._on_config_changed()
            return web.json_response({"ok": True, "applied": diterapkan})
        except Exception as e:
            logger.warning(f"SelaWebServer: gagal menulis config: {e}")
            return web.json_response({"ok": False, "error": str(e)}, status=500)

    async def _uji_mikrofon_handler(self, request: web.Request) -> web.StreamResponse:
        """Rekam mikrofon sebentar dan laporkan level suaranya.

        Berguna saat pengguna melaporkan "mikrofon tertekan tetapi suara saya
        tidak menjadi teks". Bila level RMS mendekati nol, masalahnya ada di
        sisi perangkat/izin mikrofon - bukan di mesin AI - sehingga pengguna
        mendapat petunjuk yang tepat alih-alih menebak.
        """
        try:
            detik = float(request.query.get("detik", "3"))
        except Exception:
            detik = 3.0
        detik = max(1.0, min(8.0, detik))

        try:
            import numpy as np
            import sounddevice as sd

            from src.constants.constants import AudioConfig

            laju = AudioConfig.INPUT_SAMPLE_RATE
            rekaman = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: sd.rec(
                    int(laju * detik),
                    samplerate=laju,
                    channels=1,
                    dtype="float32",
                ),
            )
            await asyncio.get_event_loop().run_in_executor(None, sd.wait)
            data = np.asarray(rekaman, dtype=np.float32).reshape(-1)
            if data.size == 0:
                return web.json_response(
                    {"ok": False, "error": "Tidak ada data dari mikrofon."}
                )
            rms = float(np.sqrt(np.mean(data * data)))
            puncak = float(np.max(np.abs(data)))

            if rms < 0.001:
                nilai = "hening"
                saran = (
                    "Mikrofon hampir tidak menangkap suara. Periksa: "
                    "(1) mikrofon tidak diredam (alsamixer -c 0, tekan M bila 'MM'), "
                    "(2) volume rekam dinaikkan, "
                    "(3) perangkat masukan yang dipilih sudah benar, "
                    "(4) pengguna tergabung di grup 'audio'. "
                    "Di Linux, jalankan: arecord -d 3 -f S16_LE -r 16000 tes.wav "
                    "lalu aplay tes.wav untuk memastikan."
                )
            elif rms < 0.01:
                nilai = "pelan"
                saran = (
                    "Suara tertangkap tetapi lemah. Naikkan volume rekam "
                    "(alsamixer) atau dekatkan mikrofon."
                )
            else:
                nilai = "baik"
                saran = "Mikrofon menangkap suara dengan baik."

            logger.info(
                f"Uji mikrofon: rms={rms:.4f} puncak={puncak:.4f} ({nilai})"
            )
            return web.json_response(
                {
                    "ok": True,
                    "rms": round(rms, 5),
                    "puncak": round(puncak, 5),
                    "detik": detik,
                    "nilai": nilai,
                    "saran": saran,
                }
            )
        except Exception as e:
            logger.warning(f"Uji mikrofon gagal: {e}")
            return web.json_response(
                {"ok": False, "error": f"Uji mikrofon gagal: {e}"}, status=500
            )

    async def _devices_handler(self, request: web.Request) -> web.StreamResponse:
        try:
            from src.utils.audio_utils import list_audio_devices

            devices = list_audio_devices(include_virtual=True)
            return web.json_response({"ok": True, "devices": devices})
        except Exception as e:
            logger.warning(f"SelaWebServer: gagal membaca perangkat audio: {e}")
            return web.json_response({"ok": False, "error": str(e)}, status=500)

    async def _ws_handler(self, request: web.Request) -> web.StreamResponse:
        ws = web.WebSocketResponse(heartbeat=30, max_msg_size=4 * 1024 * 1024)
        await ws.prepare(request)
        await self._bridge.add_client(ws)
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        payload = json.loads(msg.data)
                    except (ValueError, TypeError):
                        continue
                    if isinstance(payload, dict):
                        await self._bridge.handle_command(payload)
                elif msg.type == WSMsgType.ERROR:
                    logger.debug(f"SelaWebServer: galat WebSocket: {ws.exception()}")
        finally:
            await self._bridge.remove_client(ws)
        return ws
