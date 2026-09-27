"""Uji KLIK SUNGGUHAN pada tombol panah kartu kamera.

Kenapa berkas ini ada: ``scripts/cek_kamera_ui.py`` menekan tombol dengan
``element.click()`` - pemanggilan programatik yang TIDAK menghasilkan event
pointer. Akibatnya cacat ini lolos: tombol panah ada di DALAM bilah geser
kartu, sehingga klik sungguhan (pointerdown -> pointerup -> click) memicu
``mulaiSeret`` lebih dulu. Di sana ``setPointerCapture`` dipasang pada bilah
geser, dan sesuai spesifikasi peramban ``click`` lalu diarahkan ke pemegang
capture - BUKAN ke tombolnya. Jadi ``onClick`` tombol panah tidak pernah
berjalan dan kartu tidak pernah terlipat.

Uji ini memakai ``Input.dispatchMouseEvent`` (CDP) yang menghasilkan event
pointer sungguhan, sama seperti pengguna menekan tombol dengan tetikus.
"""

from __future__ import annotations

import asyncio
import base64
import json
import pathlib
import shutil
import socket
import subprocess
import sys
import tempfile
import urllib.request

import websockets

CHROME_KANDIDAT = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def cari_chrome() -> str | None:
    for kandidat in CHROME_KANDIDAT:
        jalur = shutil.which(kandidat) or (
            kandidat if pathlib.Path(kandidat).exists() else None
        )
        if jalur:
            return jalur
    return None


def port_bebas() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


async def ambil_ws_url(port_cdp: int) -> str:
    for _ in range(60):
        try:
            raw = urllib.request.urlopen(
                f"http://127.0.0.1:{port_cdp}/json", timeout=1
            ).read()
            for tab in json.loads(raw):
                if tab.get("type") == "page" and tab.get("webSocketDebuggerUrl"):
                    return tab["webSocketDebuggerUrl"]
        except Exception:
            pass
        await asyncio.sleep(0.5)
    raise RuntimeError("tab Chrome tidak ditemukan lewat CDP")


class CDP:
    def __init__(self, ws) -> None:
        self._ws = ws
        self._id = 0

    async def kirim(self, method: str, params=None) -> dict:
        self._id += 1
        cid = self._id
        await self._ws.send(
            json.dumps({"id": cid, "method": method, "params": params or {}})
        )
        while True:
            pesan = json.loads(await self._ws.recv())
            if pesan.get("id") == cid:
                return pesan

    async def evaluasi(self, ekspresi: str):
        hasil = await self.kirim(
            "Runtime.evaluate",
            {"expression": ekspresi, "returnByValue": True, "awaitPromise": True},
        )
        return hasil.get("result", {}).get("result", {}).get("value")

    async def klik_sungguhan(self, x: float, y: float) -> None:
        """Klik dengan event pointer sungguhan (bukan element.click())."""
        for jenis in ("mousePressed", "mouseReleased"):
            await self.kirim(
                "Input.dispatchMouseEvent",
                {
                    "type": jenis,
                    "x": x,
                    "y": y,
                    "button": "left",
                    "clickCount": 1,
                    "buttons": 1 if jenis == "mousePressed" else 0,
                    "pointerType": "mouse",
                },
            )
            await asyncio.sleep(0.05)


async def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765/"
    chrome = cari_chrome()
    if not chrome:
        print("Chrome/Edge tidak ditemukan - uji dilewati.")
        return 0

    port = port_bebas()
    profil = tempfile.mkdtemp(prefix="sela-klik-")
    proc = subprocess.Popen(
        [
            chrome,
            "--headless=new",
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profil}",
            "--no-first-run",
            "--disable-gpu",
            "--use-fake-ui-for-media-stream",
            "--use-fake-device-for-media-stream",
            "--window-size=1280,900",
            url,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    kode = 0
    try:
        ws_url = await ambil_ws_url(port)
        async with websockets.connect(ws_url, max_size=16 * 1024 * 1024) as ws:
            cdp = CDP(ws)
            await cdp.kirim("Runtime.enable")
            await cdp.kirim("Page.enable")

            # Tunggu kartu kamera muncul dan kamera siap.
            siap = False
            for _ in range(60):
                await asyncio.sleep(0.5)
                v = await cdp.evaluasi(
                    "(() => { const c = document.querySelector('[data-kamera=\"1\"]');"
                    " const v = c && c.querySelector('video');"
                    " return !!(v && v.videoWidth > 0); })()"
                )
                if v:
                    siap = True
                    break
            print(f"[kamera] siap = {siap}")
            if not siap:
                print("[HASIL] GAGAL - kamera tidak pernah terbuka")
                return 1

            # Pastikan kartu sedang terbentang.
            await cdp.evaluasi(
                "(() => { try { localStorage.setItem('sela_kamera_terbuka','1'); }"
                " catch(_) {} return 1 })()"
            )
            await cdp.kirim("Page.reload")
            for _ in range(60):
                await asyncio.sleep(0.5)
                v = await cdp.evaluasi(
                    "(() => { const c = document.querySelector('[data-kamera=\"1\"]');"
                    " return !!(c && c.getAttribute('data-kamera-tersembunyi') === '0'); })()"
                )
                if v:
                    break

            # Titik tengah tombol panah.
            kotak = await cdp.evaluasi(
                "(() => { const b = document.querySelector('[data-kamera-lipat=\"1\"]');"
                " if (!b) return null; const r = b.getBoundingClientRect();"
                " return { x: r.left + r.width/2, y: r.top + r.height/2, w: r.width, h: r.height }; })()"
            )
            print(f"[tombol panah] {kotak}")
            if not kotak:
                print("[HASIL] GAGAL - tombol panah tidak ditemukan")
                return 1

            sebelum = await cdp.evaluasi(
                "document.querySelector('[data-kamera=\"1\"]').getAttribute('data-kamera-tersembunyi')"
            )
            print(f"[sebelum] data-kamera-tersembunyi = {sebelum}")

            # KLIK SUNGGUHAN
            await cdp.klik_sungguhan(kotak["x"], kotak["y"])
            await asyncio.sleep(0.9)

            sesudah = await cdp.evaluasi(
                "document.querySelector('[data-kamera=\"1\"]').getAttribute('data-kamera-tersembunyi')"
            )
            opacity = await cdp.evaluasi(
                "getComputedStyle(document.querySelector('[data-kamera=\"1\"]')).opacity"
            )
            pil = await cdp.evaluasi(
                "!!document.querySelector('[data-kamera-ikon=\"1\"]')"
            )
            print(f"[sesudah] data-kamera-tersembunyi = {sesudah} | opacity = {opacity} | pil = {pil}")

            if sesudah == "1" and pil:
                print("[HASIL] LULUS - klik sungguhan melipat kartu jadi pil kecil.")
            else:
                print(
                    "[HASIL] GAGAL - klik sungguhan TIDAK melipat kartu. "
                    "Kemungkinan setPointerCapture pada bilah geser menelan klik tombol."
                )
                kode = 1

            shot = await cdp.kirim("Page.captureScreenshot", {"format": "png"})
            data = shot.get("result", {}).get("data")
            if data:
                out = pathlib.Path(tempfile.gettempdir()) / "sela_klik_panah.png"
                out.write_bytes(base64.b64decode(data))
                print(f"[CDP] tangkapan layar: {out}")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
    return kode


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
