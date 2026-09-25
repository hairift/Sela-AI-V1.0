"""Verifikasi pemutar musik di panel percakapan (end-to-end).

Meminta SELA memutar lagu lewat antarmuka, lalu memeriksa apakah pemutar musik
muncul di panel percakapan: bilah kemajuan, tombol jeda/lanjut, mundur/maju 15
detik, dan hentikan.

Pemakaian:
    python scripts/cek_pemutar_musik.py [url-dasar] [detik]
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

# Judul tombol yang harus ada saat pemutar musik tampil.
TOMBOL_DIHARAPKAN = ["Mundur 15 detik", "Maju 15 detik", "Jeda", "Hentikan"]


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


KIRIM_PERMINTAAN = """
(() => {
  const input = document.querySelector('input[type=text], textarea');
  if (!input) return 'tidak-ada-input';
  const setter = Object.getOwnPropertyDescriptor(
    input.tagName === 'TEXTAREA'
      ? window.HTMLTextAreaElement.prototype
      : window.HTMLInputElement.prototype,
    'value'
  ).set;
  setter.call(input, 'putar lagu Sheila on 7');
  input.dispatchEvent(new Event('input', { bubbles: true }));
  const wadah = input.closest('form') || input.parentElement;
  const tombol = wadah
    ? Array.from(wadah.querySelectorAll('button')).pop()
    : null;
  if (tombol) tombol.click();
  return tombol ? 'dikirim' : 'input-diisi-tanpa-tombol';
})()
"""

# Cari elemen pemutar musik beserta tombol-tombolnya.
# Bilah kemajuan sengaja berupa <div> yang bisa diklik (bukan input range),
# jadi dideteksi lewat penanda "cursor-pointer" + tinggi kecil, bukan tipe input.
BACA_PEMUTAR = """
(() => {
  const tombol = Array.from(document.querySelectorAll('button'))
    .map((b) => (b.getAttribute('aria-label') || b.title || b.textContent || '').trim())
    .filter(Boolean);
  const bilah = Array.from(document.querySelectorAll('div')).filter((d) => {
    const cls = d.className || '';
    return (
      typeof cls === 'string' &&
      cls.includes('cursor-pointer') &&
      cls.includes('rounded-full')
    );
  });
  // Label waktu (m:ss) di bawah bilah kemajuan.
  const waktu = Array.from(document.querySelectorAll('.tabular-nums'))
    .map((e) => (e.textContent || '').trim())
    .filter((x) => /\\d+:\\d\\d/.test(x));
  const judulLagu = Array.from(document.querySelectorAll('p, span, div'))
    .map((e) => (e.textContent || '').trim())
    .filter((t) => /Sedang diputar|Dijeda/i.test(t) && t.length < 40);
  return {
    tombolRelevan: tombol.filter((t) => /mundur|maju|jeda|lanjut|hentikan|musik/i.test(t)),
    adaProgress: bilah.length > 0,
    adaWaktu: waktu.length > 0,
    judulLagu: [...new Set(judulLagu)].slice(0, 2),
  };
})()
"""


async def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765/"
    # Bawaan 120 detik, bukan 45.
    #
    # Alurnya panjang: mesin AI mencari lagu (~5 detik), lalu MEMBACAKAN balasan
    # dengan suara lebih dulu - musik baru diputar setelah TTS selesai ("TTS
    # 进行中，本地音源已就绪，说完再播"). Pada pengujian nyata pemutar baru
    # muncul sekitar 65 detik setelah permintaan dikirim. Batas 45 detik membuat
    # uji ini melaporkan gagal padahal pemutar memang muncul sesaat kemudian.
    tunggu = float(sys.argv[2]) if len(sys.argv) > 2 else 120.0

    chrome = cari_chrome()
    if not chrome:
        print("Chrome/Edge tidak ditemukan - uji dilewati.")
        return 0

    port = port_bebas()
    profil = tempfile.mkdtemp(prefix="sela-musik-")
    proc = subprocess.Popen(
        [
            chrome,
            "--headless=new",
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profil}",
            "--no-first-run",
            "--disable-gpu",
            "--autoplay-policy=no-user-gesture-required",
            "--window-size=1080,620",
            url,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        ws_url = await ambil_ws_url(port)
        async with websockets.connect(ws_url, max_size=16 * 1024 * 1024) as ws:
            cdp = CDP(ws)
            await cdp.kirim("Runtime.enable")
            print("[CDP] membuka antarmuka")

            for _ in range(40):
                v = await cdp.evaluasi("!!document.querySelector('input[type=text], textarea')")
                if v:
                    break
                await asyncio.sleep(0.5)

            aksi = await cdp.evaluasi(KIRIM_PERMINTAAN)
            print(f"[ui] minta putar lagu -> {aksi}")

            hasil: dict = {}
            for i in range(int(tunggu / 2)):
                await asyncio.sleep(2)
                hasil = await cdp.evaluasi(BACA_PEMUTAR) or {}
                if hasil.get("adaProgress") and hasil.get("tombolRelevan"):
                    print(f"[pemutar] muncul setelah ~{(i + 1) * 2} detik")
                    break

            print(f"[pemutar] {json.dumps(hasil, ensure_ascii=False)}")

            tombol = hasil.get("tombolRelevan") or []
            ada = [t for t in TOMBOL_DIHARAPKAN if any(t.lower() in x.lower() for x in tombol)]
            if hasil.get("adaProgress") and hasil.get("adaWaktu") and len(ada) >= 3:
                print(
                    f"[HASIL] pemutar musik tampil lengkap "
                    f"(bilah kemajuan + waktu + tombol: {ada})"
                )
                kode = 0
            else:
                print(
                    "[HASIL] pemutar musik belum terdeteksi lengkap. "
                    f"progress={hasil.get('adaProgress')} "
                    f"waktu={hasil.get('adaWaktu')} tombol={tombol}"
                )
                kode = 1

            shot = await cdp.kirim("Page.captureScreenshot", {"format": "png"})
            data = shot.get("result", {}).get("data")
            if data:
                out = pathlib.Path(tempfile.gettempdir()) / "sela_musik.png"
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
