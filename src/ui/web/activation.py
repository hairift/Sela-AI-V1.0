"""Alur aktivasi perangkat untuk mode ``web``.

Mengapa modul ini ada
---------------------
Tahap aktivasi berjalan **sebelum** antarmuka web utama dibuka, jadi halaman
SELA biasa belum tersedia saat kode aktivasi perlu ditampilkan. Sebelumnya
mode ``web`` memakai penangan CLI (:class:`~src.ui.cli.activation.CliActivation`)
yang mencetak kode ke terminal. Pada aplikasi hasil paket, terminal itu tidak
ada (``console=False``) sehingga pengguna baru hanya melihat aplikasi yang
"tidak mau terbuka" tanpa pernah tahu kode aktivasinya.

Modul ini menyalakan server kecil sementara yang menampilkan kode aktivasi di
peramban, lalu mematikan dirinya setelah aktivasi selesai atau gagal. Alur
kodenya tetap sama dengan mode lain: ambil kode → tampilkan → ``activate()``.
"""

from __future__ import annotations

import asyncio
import json
from typing import Optional

from aiohttp import web

from src.constants.system import SystemConstants
from src.logging import get_logger
from src.ui.shared.activation import BaseActivation

logger = get_logger()

# Port yang dicoba berurutan; kalau semuanya terpakai, minta port bebas ke OS.
_PORT_KANDIDAT = tuple(range(8765, 8776))

# Batas waktu menampilkan hasil sebelum jendela ditutup (detik).
_JEDA_TAMPIL_SUKSES = 4
_JEDA_TAMPIL_GAGAL = 8


_HALAMAN = """<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{judul} - Aktivasi</title>
<style>
  :root {{ color-scheme: dark; }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; min-height: 100vh; display: flex; align-items: center;
    justify-content: center; padding: 24px;
    font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    background: radial-gradient(circle at 50% 0%, #14243d 0%, #070d17 60%);
    color: #eaf1ff;
  }}
  .kartu {{
    width: min(560px, 100%); background: rgba(18,28,46,.92);
    border: 1px solid rgba(120,170,255,.22); border-radius: 20px;
    padding: 32px; box-shadow: 0 24px 60px rgba(0,0,0,.55);
  }}
  h1 {{ margin: 0 0 4px; font-size: 22px; letter-spacing: .2px; }}
  .sub {{ margin: 0 0 24px; color: #93a7c4; font-size: 14px; }}
  .label {{ font-size: 12px; text-transform: uppercase; letter-spacing: .12em;
            color: #7f96b8; margin-bottom: 10px; }}
  .kode {{ display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 26px; }}
  .digit {{
    flex: 1 1 0; min-width: 52px; padding: 16px 0; text-align: center;
    font-size: 34px; font-weight: 700; font-variant-numeric: tabular-nums;
    background: linear-gradient(180deg,#1d3252,#152740);
    border: 1px solid rgba(120,170,255,.28); border-radius: 14px;
    color: #cfe4ff;
  }}
  ol {{ margin: 0 0 22px; padding-left: 20px; color: #c3d3e8; font-size: 14px; line-height: 1.85; }}
  ol a {{ color: #6fb3ff; font-weight: 600; }}
  .status {{
    display: flex; align-items: center; gap: 10px; font-size: 14px;
    padding: 13px 16px; border-radius: 12px; border: 1px solid transparent;
  }}
  .menunggu {{ background: rgba(80,140,220,.12); border-color: rgba(90,150,230,.32); color: #b9d4f7; }}
  .sukses   {{ background: rgba(60,190,130,.14); border-color: rgba(70,200,140,.4);  color: #a9f0cd; }}
  .gagal    {{ background: rgba(230,90,90,.14);  border-color: rgba(240,110,110,.4); color: #ffc4c4; }}
  .dilewati {{ background: rgba(210,160,60,.14); border-color: rgba(220,175,80,.4); color: #ffe0a8; }}
  .titik {{
    width: 9px; height: 9px; border-radius: 50%; background: currentColor;
    animation: denyut 1.4s ease-in-out infinite; flex: 0 0 auto;
  }}
  .sukses .titik, .gagal .titik, .dilewati .titik {{ animation: none; }}
  @keyframes denyut {{ 0%,100% {{ opacity:.35 }} 50% {{ opacity:1 }} }}
  .catatan {{ margin: 20px 0 0; font-size: 12px; color: #6f86a6; }}
  .aksi {{ margin-top: 26px; padding-top: 20px; border-top: 1px solid rgba(120,170,255,.16); }}
  .aksi button {{
    width: 100%; padding: 13px 18px; font: inherit; font-size: 14px; font-weight: 600;
    color: #cfe4ff; cursor: pointer;
    background: rgba(40,80,140,.45); border: 1px solid rgba(120,170,255,.32);
    border-radius: 12px; transition: background .15s ease, transform .1s ease;
  }}
  .aksi button:hover:not(:disabled) {{ background: rgba(55,105,175,.6); }}
  .aksi button:active:not(:disabled) {{ transform: scale(.985); }}
  .aksi button:disabled {{ opacity: .45; cursor: default; }}
  .aksi .catatan {{ margin-top: 12px; line-height: 1.7; }}
</style>
</head>
<body>
  <div class="kartu">
    <h1>{judul}</h1>
    <p class="sub">Sambungkan perangkat ini ke akun xiaozhi.me Anda</p>

    <div class="label">Kode aktivasi</div>
    <div class="kode" id="kode"></div>

    <ol>
      <li>Buka <a href="https://xiaozhi.me" target="_blank" rel="noopener">xiaozhi.me</a> di peramban</li>
      <li>Masuk ke akun Anda</li>
      <li>Pilih menu tambah perangkat</li>
      <li>Masukkan kode aktivasi di atas</li>
      <li>Konfirmasi penambahan perangkat</li>
    </ol>

    <div class="status menunggu" id="status">
      <span class="titik"></span><span id="pesan">Menunggu kode dimasukkan...</span>
    </div>

    <p class="catatan">Halaman ini menutup sendiri setelah perangkat aktif.</p>

    <div class="aksi">
      <button type="button" id="lewati">Lewati dulu, pakai aplikasinya</button>
      <p class="catatan">
        Belum sempat mendaftar? Lewati saja - kode ini bisa dilihat lagi kapan
        saja di <strong>Pengaturan &gt; Perangkat &amp; Aktivasi</strong>.
      </p>
    </div>
  </div>
<script>
  var kode = {kode_json};
  var wadah = document.getElementById('kode');
  var digit = kode.split('');
  for (var i = 0; i < digit.length; i++) {{
    var d = document.createElement('div');
    d.className = 'digit';
    d.textContent = digit[i];
    wadah.appendChild(d);
  }}

  var kotakStatus = document.getElementById('status');
  var teksPesan = document.getElementById('pesan');
  var tombolLewati = document.getElementById('lewati');
  var sudahFinal = false;

  tombolLewati.addEventListener('click', function () {{
    tombolLewati.disabled = true;
    teksPesan.textContent = 'Melewati aktivasi...';
    fetch('lewati', {{ method: 'POST' }}).catch(function () {{}});
  }});

  function periksa() {{
    fetch('status', {{ cache: 'no-store' }})
      .then(function (r) {{ return r.json(); }})
      .then(function (d) {{
        kotakStatus.className = 'status ' + d.status;
        teksPesan.textContent = d.pesan;
        if (d.status === 'sukses' || d.status === 'gagal' || d.status === 'dilewati') {{
          sudahFinal = true;
          tombolLewati.disabled = true;
        }}
      }})
      .catch(function () {{}});
  }}
  periksa();
  setInterval(function () {{ if (!sudahFinal) periksa(); }}, 2000);
</script>
</body>
</html>
"""


def _cari_port() -> int:
    """Cari port bebas di 127.0.0.1; 0 = biarkan OS memilih."""
    import socket

    for port in _PORT_KANDIDAT:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return 0


class WebActivation(BaseActivation):
    """Penangan aktivasi perangkat untuk mode web."""

    def __init__(self, activation_service, init_result: dict):
        super().__init__(activation_service, init_result)
        self._runner: Optional[web.AppRunner] = None
        self._port: Optional[int] = None
        self._kode: str = ""
        self._status: str = "menunggu"
        self._pesan: str = "Menunggu kode dimasukkan di xiaozhi.me..."
        self._selesai = asyncio.Event()
        # Dinyalakan tombol "Lewati dulu". Tanpa jalan keluar ini pengguna yang
        # belum siap mendaftarkan perangkat terkunci total: `start_app` keluar
        # dengan kode 1 bila aktivasi gagal.
        self._dilewati = asyncio.Event()

    # ---- Siklus hidup ----

    async def run(self) -> bool:
        if not self.needs_activation():
            logger.info("Perangkat sudah aktif, tahap aktivasi web dilewati")
            return True

        data = self._service.get_activation_data()
        if not data:
            logger.error("Data aktivasi tidak diterima")
            return False

        self._kode = str(data.get("code", ""))
        self._pesan = data.get(
            "message", "Masukkan kode aktivasi di xiaozhi.me lalu konfirmasi"
        )

        await self._mulai_server()
        try:
            self._buka_jendela()
            logger.info(f"Menunggu aktivasi perangkat (kode: {self._kode})")

            # Jalankan penantian aktivasi dan tombol "Lewati dulu" bersamaan;
            # yang lebih dulu selesai itulah keputusannya.
            tugas = asyncio.ensure_future(self._service.activate(data))
            penunggu_lewat = asyncio.ensure_future(self._dilewati.wait())
            try:
                await asyncio.wait(
                    {tugas, penunggu_lewat}, return_when=asyncio.FIRST_COMPLETED
                )
            finally:
                if not penunggu_lewat.done():
                    penunggu_lewat.cancel()

            if self._dilewati.is_set() and not tugas.done():
                tugas.cancel()
                try:
                    await tugas
                except asyncio.CancelledError:
                    pass
                except Exception as e:  # pragma: no cover - jaring pengaman
                    logger.debug(f"Aktivasi dihentikan: {e}")
                self._status = "dilewati"
                self._pesan = (
                    "Aktivasi dilewati. Perangkat belum terdaftar di akun Anda - "
                    "buka Pengaturan > Perangkat & Aktivasi kapan saja untuk "
                    "mendapat kode baru."
                )
                logger.info("Aktivasi dilewati pengguna; aplikasi tetap dijalankan")
                await asyncio.sleep(_JEDA_TAMPIL_SUKSES)
                return True

            sukses = bool(tugas.result())

            if sukses:
                self._status = "sukses"
                self._pesan = (
                    f"Aktivasi berhasil! Menjalankan "
                    f"{SystemConstants.APP_DISPLAY_NAME}..."
                )
            else:
                self._status = "gagal"
                self._pesan = (
                    "Aktivasi gagal. Periksa koneksi jaringan lalu jalankan "
                    "ulang aplikasi untuk mendapat kode baru."
                )

            logger.info(f"Hasil aktivasi: {'berhasil' if sukses else 'gagal'}")
            # Biarkan peramban sempat menampilkan hasil sebelum server ditutup.
            await asyncio.sleep(_JEDA_TAMPIL_SUKSES if sukses else _JEDA_TAMPIL_GAGAL)
            return sukses
        except asyncio.CancelledError:
            logger.info("Aktivasi web dibatalkan")
            raise
        finally:
            await self._hentikan_server()

    async def _lewati(self, request: web.Request) -> web.Response:
        """Tandai aktivasi dilewati supaya aplikasi bisa tetap dibuka."""
        self._dilewati.set()
        return web.json_response({"ok": True})

    async def _mulai_server(self) -> None:
        app = web.Application()
        app.router.add_get("/", self._halaman)
        app.router.add_get("/status", self._status_json)
        app.router.add_post("/lewati", self._lewati)

        self._port = _cari_port()
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, "127.0.0.1", self._port)
        await site.start()

        # Baca port nyata bila OS yang memilih (port 0).
        if self._port == 0:
            try:
                sock = site._server.sockets[0]
                self._port = int(sock.getsockname()[1])
            except Exception:
                pass

        logger.info(f"Server aktivasi web berjalan di {self.url}")

    async def _hentikan_server(self) -> None:
        if self._runner is None:
            return
        try:
            await self._runner.cleanup()
            logger.info("Server aktivasi web dihentikan")
        except Exception as e:
            logger.debug(f"Gagal menghentikan server aktivasi: {e}")
        finally:
            self._runner = None

    # ---- HTTP ----

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self._port}/"

    def _buka_jendela(self) -> None:
        """Buka halaman aktivasi. Kegagalan tidak boleh mematikan aplikasi."""
        try:
            from src.ui.web.launcher import open_ui

            open_ui(
                self.url,
                title=f"{SystemConstants.APP_DISPLAY_NAME} - Aktivasi",
                width=760,
                height=820,
            )
        except Exception as e:
            logger.warning(f"Tidak bisa membuka jendela aktivasi: {e}")
        logger.info(f"Jika jendela tidak terbuka, buka manual: {self.url}")

    async def _halaman(self, request: web.Request) -> web.Response:
        html = _HALAMAN.format(
            judul=SystemConstants.APP_DISPLAY_NAME,
            kode_json=json.dumps(self._kode),
        )
        return web.Response(text=html, content_type="text/html", charset="utf-8")

    async def _status_json(self, request: web.Request) -> web.Response:
        return web.json_response(
            {"status": self._status, "pesan": self._pesan, "kode": self._kode},
            headers={"Cache-Control": "no-store"},
        )
