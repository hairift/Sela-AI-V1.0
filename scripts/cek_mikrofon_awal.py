"""Uji: mikrofon TIDAK boleh merekam sendiri saat halaman dibuka/disegarkan.

Latar masalah nyata (laporan pengguna, v1.0.15):

Setiap kali aplikasi dipasang atau halaman disegarkan (Ctrl+Shift+S), tombol
mikrofon sudah berada di posisi "merekam" - berwarna merah, berdenyut, dan
labelnya "Sedang mendengarkan..." - padahal pengguna belum menekan apa pun.

Akibat berantainya lebih buruk lagi: klik mikrofon pertama pengguna justru
menutup sesi dengar hantu itu, sehingga tidak ada audio yang terekam dan
jawaban atas ucapan pengguna tidak pernah muncul.

Penyebabnya ada di sisi mesin AI (lihat tests/test_sesi_dengar.py): protokol
menaikkan status ke LISTENING begitu kanal audio terbuka, dan aplikasi web
menyambung saat start. Perbaikan di antarmuka: rekaman hanya ditandai setelah
pengguna benar-benar menekan tombol.

Yang diperiksa di DOM sungguhan lewat CDP - bukan pembacaan berkas sumber:

1. Saat halaman baru dibuka, tombol mikrofon TIDAK boleh dalam keadaan merekam
   (tidak merah, tidak berdenyut, tidak ada label mendengarkan).
2. Setelah satu klik sungguhan, tombol HARUS masuk keadaan merekam.
3. Setelah klik kedua, tombol kembali tenang.
4. Sepanjang itu tidak boleh ada galat JavaScript.

Klik memakai ``Input.dispatchMouseEvent`` (klik sungguhan), bukan
``element.click()`` - lihat catatan di ``uji_asap_ui.py``: ``.click()`` tidak
memicu ``pointerdown`` sehingga cacat seperti ``setPointerCapture`` lolos
sebagai "lulus".
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


# Ekspresi yang membaca keadaan tombol mikrofon dari DOM.
#
# Tombol "sedang merekam" dikenali dari KELAS yang dipasang komponen
# (VoiceControls.jsx): merah + berdenyut + cincin lebar. Membaca warna hasil
# komputasi lebih tahan banting daripada mencocokkan nama kelas mentah, jadi
# keduanya dipakai - kelas untuk kejelasan, warna untuk memastikan.
EKSPRESI_KEADAAN = """
(() => {
  const btn = document.querySelector('#tombol-suara');
  if (!btn) return { ada: false };
  const kls = btn.className || '';
  const gaya = getComputedStyle(btn);
  const merah = /bg-red-500/.test(kls);
  const denyut = /animate-pulse/.test(kls);
  // Label status ada di <p> setelah tombol.
  const teksSemua = (btn.parentElement?.innerText || '').toLowerCase();
  const menyebutDengar =
    teksSemua.includes('sedang mendengarkan') ||
    teksSemua.includes('mendengarkan...') ||
    teksSemua.includes('merekam');
  return {
    ada: true,
    merah,
    denyut,
    menyebutDengar,
    merekam: merah || denyut || menyebutDengar,
    warna: gaya.backgroundColor,
    teks: teksSemua.slice(0, 120),
  };
})()
"""


async def klik_tombol_mikrofon(cdp: CDP) -> bool:
    """Klik sungguhan di tengah tombol mikrofon."""
    kotak = await cdp.evaluasi(
        """
        (() => {
          const b = document.querySelector('#tombol-suara');
          if (!b) return null;
          const r = b.getBoundingClientRect();
          return { x: r.left + r.width/2, y: r.top + r.height/2 };
        })()
        """
    )
    if not kotak:
        return False
    for tipe in ("mousePressed", "mouseReleased"):
        await cdp.kirim(
            "Input.dispatchMouseEvent",
            {
                "type": tipe,
                "x": kotak["x"],
                "y": kotak["y"],
                "button": "left",
                "clickCount": 1,
            },
        )
    return True


async def jalankan(url: str) -> int:
    chrome = cari_chrome()
    if not chrome:
        print("[LEWAT] Chrome/Edge tidak ditemukan - uji dilewati.")
        return 0

    port = port_bebas()
    profil = tempfile.mkdtemp(prefix="sela-mik-")
    proc = subprocess.Popen(
        [
            chrome,
            "--headless=new",
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profil}",
            "--no-first-run",
            "--disable-gpu",
            "--autoplay-policy=no-user-gesture-required",
            "--use-fake-ui-for-media-stream",
            "--use-fake-device-for-media-stream",
            "--window-size=1280,900",
            url,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    galat: list[str] = []
    try:
        ws_url = await ambil_ws_url(port)
        async with websockets.connect(ws_url, max_size=16 * 1024 * 1024) as ws:
            cdp = CDP(ws)
            await cdp.kirim("Runtime.enable")
            await cdp.kirim("Page.enable")
            await cdp.kirim("Log.enable")

            # Tunggu React selesai merender tombol mikrofon. Jendela tetap
            # rapuh: setelah bundel di-*build* ulang cache kosong dan akar React
            # masih kosong saat diperiksa, lalu uji gagal palsu.
            ada = False
            for _ in range(40):
                await asyncio.sleep(0.5)
                ada = await cdp.evaluasi(
                    "!!document.querySelector('#tombol-suara')"
                )
                if ada:
                    break
            if not ada:
                galat.append("tombol mikrofon (#tombol-suara) tidak muncul di DOM")
            else:
                # Beri waktu sambungan WebSocket + snapshot awal datang, karena
                # di sinilah dulu status LISTENING hantu bocor ke tampilan.
                await asyncio.sleep(3.0)

                awal = await cdp.evaluasi(EKSPRESI_KEADAAN)
                if awal.get("merekam"):
                    galat.append(
                        "tombol mikrofon SUDAH dalam keadaan merekam saat halaman "
                        f"baru dibuka - pengguna belum menekan apa pun. "
                        f"keadaan: {awal}"
                    )
                else:
                    print(
                        "  [OK] saat halaman dibuka: mikrofon tenang "
                        f"(warna={awal.get('warna')!r})"
                    )

                # Klik pertama -> harus mulai merekam.
                if await klik_tombol_mikrofon(cdp):
                    await asyncio.sleep(1.5)
                    setelah = await cdp.evaluasi(EKSPRESI_KEADAAN)
                    if not setelah.get("merekam"):
                        galat.append(
                            "setelah satu klik, tombol mikrofon TIDAK masuk "
                            f"keadaan merekam. keadaan: {setelah}"
                        )
                    else:
                        print("  [OK] setelah klik pertama: mikrofon merekam")

                    # Klik kedua -> kembali tenang.
                    await klik_tombol_mikrofon(cdp)
                    await asyncio.sleep(1.5)
                    akhir = await cdp.evaluasi(EKSPRESI_KEADAAN)
                    if akhir.get("merah"):
                        galat.append(
                            "setelah klik kedua, tombol mikrofon masih merah - "
                            f"rekaman tidak berhenti. keadaan: {akhir}"
                        )
                    else:
                        print("  [OK] setelah klik kedua: mikrofon berhenti")
                else:
                    galat.append("tombol mikrofon tidak bisa diklik (tidak ada kotak)")

            # Galat JavaScript di halaman.
            try:
                entri = await cdp.kirim("Runtime.evaluate", {
                    "expression": "window.__selaGalat || []",
                    "returnByValue": True,
                })
                daftar = entri.get("result", {}).get("result", {}).get("value") or []
                if daftar:
                    galat.append(f"ada galat JavaScript di halaman: {daftar}")
            except Exception:
                pass

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()

    if galat:
        print("\n[GAGAL] masalah berikut ditemukan:")
        for g in galat:
            print(f"  - {g}")
        return 1

    print("\n[LULUS] mikrofon tidak merekam sendiri; klik mengendalikannya.")
    return 0


def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:4173/"
    return asyncio.run(jalankan(url))


if __name__ == "__main__":
    raise SystemExit(main())
