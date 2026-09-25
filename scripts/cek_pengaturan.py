"""Buka halaman pengaturan (di balik gerbang admin) lalu periksa isinya.

Halaman pengaturan dilindungi kata sandi admin, sehingga uji asap biasa hanya
melihat layar kunci - bukan isi pengaturan. Skrip ini memasukkan kata sandi,
membuka pengaturan, lalu memastikan semua bagian yang diminta pengguna ada:

  Tampilan, Mesin AI, Musik, Suara & Mikrofon, Kamera, Pintasan Papan Tik,
  Alat (MCP), Log Mesin AI, Tentang Aplikasi

Sekaligus mengambil tangkapan layar sebagai bukti visual.

Pemakaian:
    python scripts/cek_pengaturan.py [url-dasar]
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
    "google-chrome",
    "chromium",
]

# Bagian yang HARUS ada di halaman pengaturan (Bahasa Indonesia).
BAGIAN_WAJIB = [
    "Tampilan",
    "Mesin AI",
    "Musik",
    "Suara & Mikrofon",
    "Kamera",
    "Pintasan Papan Tik",
    "Alat (MCP)",
    "Log Mesin AI",
    "Tentang Aplikasi",
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


# Masukkan kata sandi admin, tekan tombol buka, tunggu pengaturan muncul.
SKRIP_BUKA = """
(() => {
  const input = document.querySelector('input[type=password]');
  if (!input) return 'tidak-ada-input';
  const setter = Object.getOwnPropertyDescriptor(
    window.HTMLInputElement.prototype, 'value'
  ).set;
  setter.call(input, 'cirebon250904');
  input.dispatchEvent(new Event('input', { bubbles: true }));
  input.dispatchEvent(new Event('change', { bubbles: true }));
  const tombol = Array.from(document.querySelectorAll('button'))
    .find((b) => /buka pengaturan|buka|masuk/i.test(b.textContent || ''));
  if (!tombol) return 'tidak-ada-tombol';
  tombol.click();
  return 'diklik';
})()
"""

# Baca semua judul bagian (Kartu) yang tampil, beserta jumlah data yang
# benar-benar termuat (pintasan & tool MCP) supaya bisa menunggu pemuatan.
SKRIP_BACA = """
(() => {
  const judul = Array.from(document.querySelectorAll('h2'))
    .map((h) => (h.textContent || '').trim())
    .filter(Boolean);
  const adaInputSandi = !!document.querySelector('input[type=password]');
  const jumlahPintasan = document.querySelectorAll('kbd').length;
  const jumlahSakelar = document.querySelectorAll('button[aria-pressed]').length;
  return {
    judul,
    adaInputSandi,
    jumlahPintasan,
    jumlahSakelar,
    panjang: document.body.innerText.length,
  };
})()
"""


async def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765/"
    chrome = cari_chrome()
    if not chrome:
        print("Chrome/Edge tidak ditemukan - uji dilewati.")
        return 0

    port = port_bebas()
    profil = tempfile.mkdtemp(prefix="sela-set-")
    proc = subprocess.Popen(
        [
            chrome,
            "--headless=new",
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profil}",
            "--no-first-run",
            "--disable-gpu",
            "--window-size=1080,2400",
            f"{url.rstrip('/')}/?halaman=pengaturan",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        ws_url = await ambil_ws_url(port)
        async with websockets.connect(ws_url, max_size=16 * 1024 * 1024) as ws:
            cdp = CDP(ws)
            await cdp.kirim("Runtime.enable")
            print("[CDP] membuka halaman pengaturan")

            for _ in range(40):
                v = await cdp.evaluasi(
                    "!!document.querySelector('input[type=password]')"
                )
                if v:
                    break
                await asyncio.sleep(0.5)

            aksi = await cdp.evaluasi(SKRIP_BUKA)
            print(f"[gerbang admin] {aksi}")

            # Tunggu gerbang hilang, bagian muncul, DAN data termuat
            # (pintasan + tool MCP). Tanpa menunggu data, tangkapan layar bisa
            # memperlihatkan bagian yang masih kosong.
            judul: list[str] = []
            baca: dict = {}
            for _ in range(60):
                await asyncio.sleep(0.5)
                baca = await cdp.evaluasi(SKRIP_BACA) or {}
                judul = baca.get("judul") or []
                if (
                    not baca.get("adaInputSandi")
                    and judul
                    and (baca.get("jumlahPintasan") or 0) > 0
                ):
                    break

            print(f"[bagian ditemukan] {len(judul)}")
            for j in judul:
                print(f"   - {j}")
            print(
                f"[data] pintasan={baca.get('jumlahPintasan')} "
                f"sakelar={baca.get('jumlahSakelar')}"
            )

            hilang = [b for b in BAGIAN_WAJIB if b not in judul]
            if hilang:
                print(f"[HASIL] GAGAL - bagian belum ada: {hilang}")
                kode = 1
            elif (baca.get("jumlahPintasan") or 0) == 0:
                print("[HASIL] GAGAL - daftar pintasan kosong (data tidak termuat)")
                kode = 1
            else:
                print("[HASIL] seluruh bagian pengaturan tersedia (Bahasa Indonesia).")
                kode = 0

            shot = await cdp.kirim(
                "Page.captureScreenshot", {"format": "png", "captureBeyondViewport": True}
            )
            data = shot.get("result", {}).get("data")
            if data:
                out = pathlib.Path(tempfile.gettempdir()) / "sela_pengaturan.png"
                out.write_bytes(base64.b64decode(data))
                print(f"[CDP] tangkapan layar: {out}")
            return kode
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
