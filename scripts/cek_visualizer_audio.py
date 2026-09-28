"""Uji visualizer audio pada antarmuka web SELA.

Kenapa berkas ini ada: visualizer di ``Avatar3D.jsx`` dulu memakai animasi CSS
statis (``animate-wave-*``) sehingga tampak bergerak sendiri tanpa hubungan
dengan suara. Uji ini membuktikan tinggi batang BENAR-BENAR berubah mengikuti
data audio (``lip.v``) dari mesin AI.

Yang diperiksa:
1. Tinggi batang saat volume tinggi harus jauh di atas tinggi dasar.
2. Volume berbeda harus menghasilkan tinggi berbeda (bukan konstanta).
3. Semua batang tidak boleh sama tinggi - harus seperti spektrum.
4. Warna batang berubah mengikuti viseme.
5. Batang bergerak walau state perangkat bukan 'speaking' - mesin AI mengayun
   speaking <-> idle di sela kalimat, jadi visualizer tidak boleh ikut mati.
6. Batang mengempis kembali setelah suara hilang.
7. Tidak ada aksara Han pada halaman (harus Indonesia saja).

Bukti diambil dari DOM sungguhan lewat CDP, bukan dari pembacaan berkas sumber.
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
import urllib.request

import websockets

CHROME_KANDIDAT = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

# Rentang kode aksara Han (CJK Unified Ideographs + Extension A).
HAN = __import__("re").compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")


def cari_chrome():
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
        hasil_dalam = hasil.get("result", {})
        if "exceptionDetails" in hasil_dalam:
            raise RuntimeError(f"galat JS: {hasil_dalam['exceptionDetails']}")
        return hasil_dalam.get("result", {}).get("value")


async def jalankan(url: str) -> int:
    chrome = cari_chrome()
    if not chrome:
        print("[LEWAT] Chrome/Edge tidak ditemukan - uji dilewati.")
        return 0

    port = port_bebas()
    profil = tempfile.mkdtemp(prefix="sela-visual-")
    proc = subprocess.Popen(
        [
            chrome,
            "--headless=new",
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profil}",
            "--no-first-run",
            "--disable-gpu",
            "--autoplay-policy=no-user-gesture-required",
            "--window-size=1280,900",
            url,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    galat = []
    try:
        ws_url = await ambil_ws_url(port)
        async with websockets.connect(ws_url, max_size=16 * 1024 * 1024) as ws:
            cdp = CDP(ws)
            await cdp.kirim("Runtime.enable")
            await cdp.kirim("Page.enable")

            # Tunggu sampai React benar-benar merender visualizer. Jendela tetap
            # (mis. 3 detik) rapuh: pada mesin yang lambat - terutama setelah
            # bundel di-*build* ulang sehingga cache kosong - akar React masih
            # kosong saat diperiksa, lalu uji gagal palsu seolah visualizer
            # tidak ada. Jadi tunggu sampai elemennya benar-benar muncul.
            ada = False
            for _ in range(40):
                await asyncio.sleep(0.5)
                ada = await cdp.evaluasi(
                    "!!document.querySelector('[data-visualizer-audio=\"1\"]')"
                )
                if ada:
                    break

            # --- Visualizer ---
            print(f"[visualizer] ada di DOM = {ada}")
            if not ada:
                galat.append("visualizer audio tidak ditemukan di DOM")
            else:

                async def tinggi_batang():
                    return await cdp.evaluasi(
                        "(() => { const w = document.querySelector('[data-visualizer-audio=\"1\"]');"
                        " return Array.from(w.children).map(b => parseInt(b.style.height) || 0); })()"
                    )

                # Tinggi dasar sebelum ada suara sama sekali.
                dasar = await tinggi_batang()
                print(f"[visualizer] tinggi dasar (belum ada suara) = {dasar}")

                # Siarkan volume tinggi melalui kanal yang sama dengan mesin AI.
                async def set_volume(v, viseme="a"):
                    await cdp.evaluasi(
                        "(() => { window.__selaUjiLip && window.__selaUjiLip(%s, '%s'); return 1 })()"
                        % (v, viseme)
                    )

                # Bila jembatan belum membuka kait uji, suntikkan langsung.
                ada_kait = await cdp.evaluasi("typeof window.__selaUjiLip === 'function'")
                print(f"[visualizer] kait uji tersedia = {ada_kait}")
                if not ada_kait:
                    galat.append(
                        "kait uji __selaUjiLip tidak tersedia (uji tidak bisa "
                        "menyuntikkan data audio)"
                    )
                else:
                    # State perangkat sengaja TIDAK dibuat 'speaking': visualizer
                    # harus tetap mengikuti suara murni.
                    print("[visualizer] state perangkat dibiarkan apa adanya")

                    # Volume dinaikkan/ diturunkan perlahan agar peredaman batang
                    # (naik cepat, turun lambat) sempat menyusul nilainya.
                    async def naikkan(v, viseme="a", langkah=0.15, jeda=0.18):
                        sekarang = await cdp.evaluasi(
                            "window.__selaVolumeUji === undefined ? 0 : window.__selaVolumeUji"
                        )
                        sekarang = float(sekarang or 0)
                        arah = 1 if v >= sekarang else -1
                        nilai = sekarang
                        while (nilai < v - 0.03) if arah > 0 else (nilai > v + 0.03):
                            nilai = min(v, nilai + langkah) if arah > 0 else max(v, nilai - langkah)
                            await set_volume(round(nilai, 3), viseme)
                            await cdp.evaluasi(
                                f"window.__selaVolumeUji = {round(nilai, 3)}; 1"
                            )
                            await asyncio.sleep(jeda)
                        await set_volume(v, viseme)
                        await cdp.evaluasi(f"window.__selaVolumeUji = {v}; 1")

                    await naikkan(0.85)
                    await asyncio.sleep(0.5)
                    nyaring = await tinggi_batang()
                    print(f"[visualizer] tinggi saat volume 0.85 = {nyaring}")

                    await naikkan(0.25)
                    await asyncio.sleep(0.5)
                    pelan = await tinggi_batang()
                    print(f"[visualizer] tinggi saat volume 0.25 = {pelan}")

                    rerata = lambda xs: sum(xs) / len(xs) if xs else 0  # noqa: E731
                    r_dasar, r_nyaring, r_pelan = (
                        rerata(dasar),
                        rerata(nyaring),
                        rerata(pelan),
                    )
                    print(
                        f"[visualizer] rerata: dasar={r_dasar:.1f} "
                        f"nyaring={r_nyaring:.1f} pelan={r_pelan:.1f}"
                    )

                    if not (r_nyaring > r_dasar + 6):
                        galat.append(
                            f"volume tinggi tidak menaikkan batang "
                            f"(dasar={r_dasar:.1f} vs nyaring={r_nyaring:.1f})"
                        )
                    if not (r_nyaring > r_pelan + 2):
                        galat.append(
                            f"batang tidak membedakan volume "
                            f"(nyaring={r_nyaring:.1f} vs pelan={r_pelan:.1f})"
                        )
                    if len(set(nyaring)) <= 1:
                        galat.append(
                            "semua batang sama tinggi - bukan spektrum bergelombang"
                        )

                    # Batang tidak boleh melewati batas wadah (tidak "lember").
                    luber = await cdp.evaluasi(
                        "(() => { const w = document.querySelector('[data-visualizer-audio=\"1\"]');"
                        " const wr = w.getBoundingClientRect();"
                        " return Array.from(w.children).some(b => {"
                        "   const r = b.getBoundingClientRect();"
                        "   return r.top < wr.top - 2 || r.bottom > wr.bottom + 2; }); })()"
                    )
                    print(f"[visualizer] ada batang melewati wadah = {luber}")
                    if luber:
                        galat.append("batang keluar dari wadah visualizer")

                    # Warna batang harus ikut berubah mengikuti viseme.
                    await set_volume(0.7, "i")
                    await asyncio.sleep(0.35)
                    warna_i = await cdp.evaluasi(
                        "(() => { const w = document.querySelector('[data-visualizer-audio=\"1\"]');"
                        " return w.children[0] ? w.children[0].style.background : ''; })()"
                    )
                    await set_volume(0.7, "a")
                    await asyncio.sleep(0.35)
                    warna_a = await cdp.evaluasi(
                        "(() => { const w = document.querySelector('[data-visualizer-audio=\"1\"]');"
                        " return w.children[0] ? w.children[0].style.background : ''; })()"
                    )
                    print(f"[visualizer] warna viseme i={warna_i[:40]}...")
                    print(f"[visualizer] warna viseme a={warna_a[:40]}...")
                    if warna_i and warna_a and warna_i == warna_a:
                        galat.append("warna batang tidak berubah mengikuti viseme")

                    # Suara berhenti: batang harus mengempis kembali.
                    await naikkan(0)
                    await asyncio.sleep(1.6)
                    sepi = await tinggi_batang()
                    print(f"[visualizer] tinggi setelah suara hilang = {sepi}")
                    if rerata(sepi) > r_nyaring * 0.6:
                        galat.append(
                            f"batang tidak mengempis setelah suara hilang "
                            f"(nyaring={r_nyaring:.1f} vs sepi={rerata(sepi):.1f})"
                        )

            # Tanpa aksara Han di mana pun pada halaman.
            han_halaman = await cdp.evaluasi(
                "(() => { const t = document.body.innerText || '';"
                " return /[\\u4e00-\\u9fff\\u3400-\\u4dbf]/.test(t); })()"
            )
            print(f"[halaman] ada aksara Han = {han_halaman}")
            if han_halaman:
                galat.append("ada aksara Han pada halaman (harus Indonesia saja)")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        shutil.rmtree(profil, ignore_errors=True)

    print("")
    if galat:
        print("[HASIL] GAGAL:")
        for g in galat:
            print(f"  - {g}")
        return 1
    print("[HASIL] LULUS - visualizer mengikuti audio.")
    return 0


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8765/"
    sys.exit(asyncio.run(jalankan(url)))
