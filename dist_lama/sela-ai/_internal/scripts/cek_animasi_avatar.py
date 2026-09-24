"""Periksa animasi avatar 3D memakai Chrome sungguhan lewat CDP.

`--virtual-time-budget` tidak bisa dipakai untuk menguji animasi: ia
mempercepat timer sehingga tidak ada waktu nyata yang berjalan dan rangka
tidak pernah bergerak. Skrip ini menjalankan Chrome headless, menunggu
beberapa detik NYATA, lalu membaca posisi tulang dan mengambil tangkapan layar.

Pemakaian:
    python scripts/cek_animasi_avatar.py [url] [detik]
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

# Membaca rotasi tulang pada dua waktu berbeda, langsung di dalam halaman.
# Scene dipaparkan aplikasi lewat window.__sela3d (lihat Avatar3D.jsx).
SKRIP_PERIKSA = """
(() => {
  const s = window.__sela3d;
  if (!s) return JSON.stringify({ ok: false, alasan: 'window.__sela3d belum ada (model 3D belum siap)' });
  const tulang = s.tulang || [];
  if (!tulang.length) return JSON.stringify({ ok: false, alasan: 'tidak ada tulang' });
  const bahu = tulang.find((b) => /shoulder|upperarm|arm/i.test(b.name)) || tulang[0];
  const aksi = Object.entries(s.actions || {}).find(([, a]) => a && a.isRunning());
  window.__selaUji = {
    bahu,
    awal: bahu.quaternion.clone(),
    jumlahTulang: tulang.length,
    aksiBerjalan: aksi ? aksi[0] : null,
    waktuAksi: aksi ? aksi[1].time : null,
  };
  return JSON.stringify({
    ok: true,
    namaTulang: bahu.name,
    jumlahTulang: tulang.length,
    klip: Object.keys(s.actions || {}),
    aksiBerjalan: aksi ? aksi[0] : null,
  });
})()
"""

SKRIP_HASIL = """
(() => {
  const u = window.__selaUji;
  if (!u) return JSON.stringify({ ok: false });
  const delta = u.awal.angleTo(u.bahu.quaternion);
  const aksi = Object.entries(window.__sela3d.actions || {}).find(([, a]) => a && a.isRunning());
  return JSON.stringify({
    ok: true,
    namaTulang: u.bahu.name,
    jumlahTulang: u.jumlahTulang,
    perubahanRad: Number(delta.toFixed(5)),
    bergerak: delta > 0.001,
    aksiBerjalan: aksi ? aksi[0] : null,
    waktuAksi: aksi ? Number(aksi[1].time.toFixed(3)) : null,
    bobotAksi: aksi ? Number(aksi[1].getEffectiveWeight().toFixed(3)) : null,
  });
})()
"""


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
    port = s.getsockname()[1]
    s.close()
    return port


async def jalankan(url: str, detik: float) -> int:
    chrome = cari_chrome()
    if not chrome:
        print("Chrome/Chromium tidak ditemukan.", file=sys.stderr)
        return 2

    port = port_bebas()
    profil = tempfile.mkdtemp(prefix="sela-cdp-")
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
            "--window-size=1280,800",
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profil}",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        # Tunggu endpoint debug siap.
        target = None
        for _ in range(60):
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/json/list", timeout=1
                ) as r:
                    daftar = json.load(r)
                target = next(
                    (t for t in daftar if t.get("type") == "page"), None
                )
                if target:
                    break
            except Exception:
                pass
            time.sleep(0.25)

        if not target:
            print("Tidak bisa terhubung ke Chrome (CDP).", file=sys.stderr)
            return 2

        async with websockets.connect(
            target["webSocketDebuggerUrl"], max_size=32 * 1024 * 1024
        ) as ws:
            nomor = {"n": 0}

            async def kirim(method: str, params: dict | None = None) -> dict:
                nomor["n"] += 1
                mid = nomor["n"]
                await ws.send(
                    json.dumps({"id": mid, "method": method, "params": params or {}})
                )
                while True:
                    balas = json.loads(await ws.recv())
                    if balas.get("id") == mid:
                        return balas.get("result", {})

            await kirim("Page.enable")
            await kirim("Runtime.enable")
            await kirim("Page.navigate", {"url": url})
            print(f"[CDP] membuka {url}")

            # Tunggu sampai model 3D benar-benar siap (window.__sela3d terisi).
            # Memuat model 12 MB + lingkungan HDR bisa butuh beberapa detik.
            siap = False
            batas = time.monotonic() + 60
            while time.monotonic() < batas:
                await asyncio.sleep(2.0)
                cek = await kirim(
                    "Runtime.evaluate",
                    {
                        "expression": "Boolean(window.__sela3d && window.__sela3d.tulang && window.__sela3d.tulang.length)",
                        "returnByValue": True,
                    },
                )
                if cek.get("result", {}).get("value"):
                    siap = True
                    break
            print(f"[CDP] model 3D siap: {siap}")

            hasil = await kirim(
                "Runtime.evaluate",
                {"expression": SKRIP_PERIKSA, "returnByValue": True},
            )
            nilai = hasil.get("result", {}).get("value")
            print("[CDP] pemeriksaan awal:", nilai)

            # Tunggu lagi, lalu bandingkan rotasi tulang.
            await asyncio.sleep(max(2.0, detik / 2))

            hasil = await kirim(
                "Runtime.evaluate",
                {"expression": SKRIP_PERIKSA, "returnByValue": True},
            )
            nilai = hasil.get("result", {}).get("value")
            print("[CDP] pemeriksaan awal:", nilai)

            # Tunggu lagi, lalu bandingkan rotasi tulang.
            await asyncio.sleep(max(1.5, detik / 3))

            hasil2 = await kirim(
                "Runtime.evaluate",
                {"expression": SKRIP_HASIL, "returnByValue": True},
            )
            nilai2 = hasil2.get("result", {}).get("value")
            print("[CDP] hasil:", nilai2)

            # Tangkapan layar
            tangkap = await kirim("Page.captureScreenshot", {"format": "png"})
            data = tangkap.get("data")
            if data:
                keluaran = pathlib.Path("C:/tmp/avatar_cdp.png")
                keluaran.write_bytes(base64.b64decode(data))
                print(f"[CDP] tangkapan layar: {keluaran}")

            if not nilai2:
                return 1
            info = json.loads(nilai2)
            if not info.get("ok"):
                return 1
            if info.get("bergerak"):
                print(
                    f"\nHASIL: rangka BERGERAK "
                    f"({info['perubahanRad']} rad pada {info['namaTulang']}) "
                    f"- animasi avatar berfungsi."
                )
                return 0
            print(
                f"\nHASIL: rangka DIAM (perubahan {info['perubahanRad']} rad) "
                "- animasi tidak menggerakkan avatar."
            )
            return 1
    finally:
        proses.terminate()
        try:
            proses.wait(timeout=10)
        except Exception:
            proses.kill()


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765/"
    detik = float(sys.argv[2]) if len(sys.argv) > 2 else 6.0
    raise SystemExit(asyncio.run(jalankan(url, detik)))
