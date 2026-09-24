"""Uji asap antarmuka: pastikan halaman benar-benar tampil tanpa galat JS.

Latar belakang: rilis 1.0.3 dan 1.0.4 pernah menampilkan halaman **putih
kosong** karena satu variabel lupa diambil dari hook
(``ReferenceError: teksTombol is not defined``). Galat seperti itu tidak
tertangkap oleh uji Python maupun oleh pembangunan berkas, karena hanya muncul
saat React merender di peramban.

Skrip ini memuat setiap halaman di Chrome sungguhan, menangkap SEMUA galat
konsol, dan memeriksa bahwa isi halaman benar-benar tergambar (bukan kosong).

Pemakaian:
    python scripts/uji_asap_ui.py [url-dasar]
"""

from __future__ import annotations

import asyncio
import json
import pathlib
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

import websockets

CHROME_KANDIDAT = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "google-chrome",
    "chromium",
]

# Halaman yang harus bisa dibuka. `?halaman=` dipakai antarmuka SELA.
HALAMAN = [
    ("beranda", "/"),
    ("beranda eksplisit", "/?halaman=beranda"),
    ("pengaturan", "/?halaman=pengaturan"),
    ("bantuan", "/?halaman=bantuan"),
]

# Galat yang bukan kesalahan aplikasi (mis. lingkungan headless tanpa GPU).
GALAT_DIIZINKAN = (
    "favicon",
    "WebGL",
    "GPU",
    "SwiftShader",
    "Automatic fallback to software WebGL",
    "Failed to load resource: net::ERR_CONNECTION",
    "Environment preset",
    "THREE.WebGLRenderer",
    "Error creating WebGL context",
    "WebGLRenderer:",
    "GroupMarkerNotSet",
    "Fontconfig",
    "net::ERR_BLOCKED_BY_CLIENT",
    "ERR_NAME_NOT_RESOLVED",
    "the server responded with a status of",
)


def cari_chrome() -> str | None:
    for kandidat in CHROME_KANDIDAT:
        if kandidat.startswith("C:"):
            if pathlib.Path(kandidat).is_file():
                return kandidat
        else:
            ada = shutil.which(kandidat)
            if ada:
                return ada
    return None


def port_bebas() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class Sesi:
    """Pembungkus tipis untuk CDP: kirim perintah + kumpulkan galat konsol."""

    def __init__(self, ws):
        self.ws = ws
        self.nomor = 0
        self.galat: list[str] = []

    async def kirim(self, method: str, params: dict | None = None) -> dict:
        self.nomor += 1
        mid = self.nomor
        await self.ws.send(
            json.dumps({"id": mid, "method": method, "params": params or {}})
        )
        while True:
            balas = json.loads(await self.ws.recv())
            m = balas.get("method")
            if m == "Runtime.exceptionThrown":
                d = balas.get("params", {}).get("exceptionDetails", {})
                teks = d.get("exception", {}).get("description") or d.get("text") or ""
                self.galat.append(str(teks).split("\n")[0])
            elif m == "Runtime.consoleAPICalled":
                if balas.get("params", {}).get("type") == "error":
                    isi = " ".join(
                        str(a.get("value", a.get("description", "")))
                        for a in balas.get("params", {}).get("args", [])
                    )
                    if isi:
                        self.galat.append(isi.split("\n")[0])
            elif m == "Log.entryAdded":
                e = balas.get("params", {}).get("entry", {})
                if e.get("level") == "error":
                    self.galat.append(str(e.get("text", ""))[:200])
            if balas.get("id") == mid:
                return balas.get("result", {})

    async def evaluasi(self, ekspresi: str):
        r = await self.kirim(
            "Runtime.evaluate", {"expression": ekspresi, "returnByValue": True}
        )
        return r.get("result", {}).get("value")


def berbahaya(teks: str) -> bool:
    return not any(pola.lower() in teks.lower() for pola in GALAT_DIIZINKAN)


async def tunggu_aplikasi(url_dasar: str, batas_detik: float = 90.0) -> bool:
    """Tunggu aplikasi SELA melayani permintaan.

    Di CI, aplikasi perlu waktu untuk memuat model dan membuka port. Bila
    aplikasi memang tidak bisa jalan di lingkungan itu (mis. runner tanpa
    perangkat audio), pemanggil membedakan lewat kode keluar 2.
    """
    akhir = time.time() + batas_detik
    terakhir = ""
    while time.time() < akhir:
        try:
            with urllib.request.urlopen(url_dasar, timeout=5) as r:
                if r.status < 400:
                    return True
                terakhir = f"HTTP {r.status}"
        except Exception as e:
            terakhir = str(e)
        await asyncio.sleep(2)
    print(f"Aplikasi tidak melayani setelah {batas_detik:.0f} detik ({terakhir}).")
    return False


async def jalankan(url_dasar: str) -> int:
    # Pastikan aplikasi SELA benar-benar melayani. Tanpa ini, Chrome hanya
    # menampilkan halaman galat "connection refused" dan hasil uji menyesatkan.
    if not await tunggu_aplikasi(url_dasar):
        print(
            "Jalankan aplikasi SELA lebih dulu (main.py --skip-activation).",
            file=sys.stderr,
        )
        return 2

    chrome = cari_chrome()
    if not chrome:
        print("Chrome tidak ditemukan.", file=sys.stderr)
        return 2

    port = port_bebas()
    profil = tempfile.mkdtemp(prefix="sela-asap-")
    proses = subprocess.Popen(
        [
            chrome,
            "--headless=new",
            "--disable-gpu",
            "--enable-unsafe-swiftshader",
            "--use-gl=angle",
            "--use-angle=swiftshader",
            "--no-sandbox",
            "--hide-scrollbars",
            "--window-size=1280,900",
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profil}",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    gagal = 0
    try:
        target = None
        for _ in range(80):
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/json/list", timeout=1
                ) as r:
                    daftar = json.load(r)
                target = next((t for t in daftar if t.get("type") == "page"), None)
                if target:
                    break
            except Exception:
                pass
            time.sleep(0.25)
        if not target:
            print("Tidak bisa terhubung ke Chrome.", file=sys.stderr)
            return 2

        async with websockets.connect(
            target["webSocketDebuggerUrl"], max_size=32 * 1024 * 1024
        ) as ws:
            sesi = Sesi(ws)
            await sesi.kirim("Page.enable")
            await sesi.kirim("Runtime.enable")
            await sesi.kirim("Log.enable")

            for nama, jalur in HALAMAN:
                sesi.galat.clear()
                url = url_dasar.rstrip("/") + jalur
                await sesi.kirim("Page.navigate", {"url": url})

                # Tunggu isi benar-benar tergambar (bukan waktu tetap). Aplikasi
                # hasil paket lebih lambat pada pemuatan pertama, sehingga jeda
                # tetap pernah membuat halaman terlihat "kosong" padahal normal.
                d = {"simpul": 0, "teks": 0}
                for _ in range(30):
                    await asyncio.sleep(1)
                    info = await sesi.evaluasi(
                        """(() => {
                          const akar = document.getElementById('root');
                          return JSON.stringify({
                            simpul: akar ? akar.querySelectorAll('*').length : 0,
                            teks: (document.body.innerText || '').trim().length,
                          });
                        })()"""
                    )
                    try:
                        d = json.loads(info)
                    except Exception:
                        continue
                    # Halaman siap bila sudah ada isi, ATAU sudah ada galat
                    # yang perlu dilaporkan (tidak perlu menunggu lama).
                    if d.get("simpul", 0) >= 10 and d.get("teks", 0) >= 20:
                        break
                    if any(berbahaya(g) for g in sesi.galat):
                        break

                penting = [g for g in sesi.galat if berbahaya(g)]
                kosong = d.get("simpul", 0) < 10 or d.get("teks", 0) < 20

                if penting or kosong:
                    gagal += 1
                    tanda = "GAGAL"
                else:
                    tanda = "OK   "
                print(
                    f"  {tanda} {nama:20} simpul={d.get('simpul',0):4} "
                    f"teks={d.get('teks',0):4} galat={len(penting)}"
                )
                for g in penting[:3]:
                    print(f"          -> {g[:150]}")

        print()
        if gagal:
            print(f"HASIL: {gagal} halaman bermasalah - antarmuka TIDAK layak dirilis.")
            return 1
        print("HASIL: seluruh halaman tampil tanpa galat JS.")
        return 0
    finally:
        proses.terminate()
        try:
            proses.wait(timeout=10)
        except Exception:
            proses.kill()


if __name__ == "__main__":
    dasar = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765"
    raise SystemExit(asyncio.run(jalankan(dasar)))
