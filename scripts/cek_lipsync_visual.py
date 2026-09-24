"""Bukti visual lipsync: avatar harus membuka mulut saat SELA bicara.

Membuka antarmuka lewat Chrome sungguhan (CDP), mengirim pertanyaan, lalu
mengambil beberapa tangkapan layar berurutan sambil MEMBACA bobot morph mulut
langsung dari scene 3D. Bila bobot mulut pernah > 0, lipsync bekerja.

Pemakaian:
    python scripts/cek_lipsync_visual.py [url] ["pertanyaan"]
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

# Membaca bobot morph mulut (a, i, u, e, o) dari scene yang dipaparkan
# aplikasi lewat window.__sela3d.
SKRIP_BACA_MULUT = """
(() => {
  const s = window.__sela3d;
  if (!s) return JSON.stringify({ siap: false });
  let maks = 0;
  const detail = {};
  s.scene.traverse((o) => {
    if (!o.morphTargetDictionary || !o.morphTargetInfluences) return;
    for (const k of ['a', 'i', 'u', 'e', 'o']) {
      const i = o.morphTargetDictionary[k];
      if (i == null) continue;
      const v = o.morphTargetInfluences[i] || 0;
      detail[k] = Math.max(detail[k] || 0, Number(v.toFixed(3)));
      maks = Math.max(maks, v);
    }
  });
  return JSON.stringify({ siap: true, maks: Number(maks.toFixed(3)), detail });
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
    p = s.getsockname()[1]
    s.close()
    return p


async def jalankan(url: str, pertanyaan: str) -> int:
    chrome = cari_chrome()
    if not chrome:
        print("Chrome tidak ditemukan.", file=sys.stderr)
        return 2

    port = port_bebas()
    profil = tempfile.mkdtemp(prefix="sela-lip-")
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

            async def evaluasi(ekspresi: str) -> str:
                r = await kirim(
                    "Runtime.evaluate",
                    {"expression": ekspresi, "returnByValue": True},
                )
                return r.get("result", {}).get("value")

            await kirim("Page.enable")
            await kirim("Runtime.enable")
            await kirim("Page.navigate", {"url": url})
            print(f"[CDP] membuka {url}")

            # Tunggu model + kait diagnostik siap.
            for _ in range(40):
                await asyncio.sleep(2)
                siap = await evaluasi(
                    "Boolean(window.__sela3d && window.__selaKirim)"
                )
                if siap:
                    break
            print(f"[CDP] siap: {bool(siap)}")
            if not siap:
                return 1

            print(f"[CDP] kirim: {pertanyaan!r}")
            await evaluasi(
                f"window.__selaKirim({json.dumps(pertanyaan)}), 'ok'"
            )

            maks_global = 0.0
            terbaik = None
            for i in range(90):
                await asyncio.sleep(0.12)
                mentah = await evaluasi(SKRIP_BACA_MULUT)
                try:
                    info = json.loads(mentah)
                except Exception:
                    continue
                if not info.get("siap"):
                    continue
                m = float(info.get("maks") or 0)
                if m > maks_global:
                    maks_global = m
                # Simpan tangkapan layar saat mulut paling terbuka.
                if m > 0.15 and (terbaik is None or m > terbaik[0]):
                    tangkap = await kirim("Page.captureScreenshot", {"format": "png"})
                    data = tangkap.get("data")
                    if data:
                        p = pathlib.Path("C:/tmp/lipsync_bicara.png")
                        p.write_bytes(base64.b64decode(data))
                        terbaik = (m, p)
                if m > 0.02 or i % 10 == 0:
                    print(f"   [{i}] bukaan mulut maks={m:.3f}")

            print()
            print(f"bukaan mulut tertinggi: {maks_global:.3f}")
            if terbaik:
                print(f"tangkapan layar saat bicara: {terbaik[1]} (maks {terbaik[0]:.3f})")
            if maks_global > 0.15:
                print("\nHASIL: LIPSYNC BERFUNGSI - mulut avatar membuka saat bicara.")
                return 0
            print("\nHASIL: mulut tidak membuka - lipsync gagal.")
            return 1
    finally:
        proses.terminate()
        try:
            proses.wait(timeout=10)
        except Exception:
            proses.kill()


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765/"
    tanya = sys.argv[2] if len(sys.argv) > 2 else "halo sela apa kabar"
    raise SystemExit(asyncio.run(jalankan(url, tanya)))
