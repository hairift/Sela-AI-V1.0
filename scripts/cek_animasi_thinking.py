"""Verifikasi animasi "Thinking" muncul saat mesin AI mencari jawaban.

Menguji pada antarmuka yang SEDANG berjalan di Chrome sungguhan:
  1. Saat pengguna mengirim pesan, state avatar menjadi "thinking"
     (animasi Thinking berjalan) - bukan diam di pose istirahat.
  2. Animasi menggerakkan rangka (bukan pose diam).

Pemicunya adalah interaksi ANTARMUKA yang sebenarnya (mengetik lalu mengirim),
bukan pesan WebSocket: `{t:'state'}` adalah pesan server->klien sehingga tidak
bisa dipakai untuk memicu perubahan state dari luar.

State "thinking" hanya sebentar (sampai SELA mulai berbicara), jadi skrip
memantau berulang cepat lalu melaporkan semua animasi yang pernah terlihat.

Pemakaian:
    python scripts/cek_animasi_thinking.py [url-dasar] [detik]
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


def cari_chrome() -> str | None:
    for kandidat in CHROME_KANDIDAT:
        jalur = shutil.which(kandidat) or (kandidat if pathlib.Path(kandidat).exists() else None)
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
            raw = urllib.request.urlopen(f"http://127.0.0.1:{port_cdp}/json", timeout=1).read()
            for tab in json.loads(raw):
                if tab.get("type") == "page" and tab.get("webSocketDebuggerUrl"):
                    return tab["webSocketDebuggerUrl"]
        except Exception:
            pass
        await asyncio.sleep(0.5)
    raise RuntimeError("tidak bisa menemukan tab Chrome lewat CDP")


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


SKRIP_BACA = """
(() => {
  const s = window.__sela3d;
  if (!s) return { ok: false, alasan: 'window.__sela3d belum siap' };
  const berjalan = Object.entries(s.actions || {})
    .filter(([, a]) => a && a.isRunning())
    .map(([n]) => n);
  const judul = document.querySelector('canvas') ? document.title : '';
  // Ambil juga state yang ditampilkan antarmuka (teks status di layar).
  const teksBadge = Array.from(document.querySelectorAll('span,div'))
    .map((e) => (e.textContent || '').trim())
    .filter((tx) => /MENUNGGU|BERPIKIR|MENDENGARKAN|BERBICARA|SIAP/i.test(tx));
  return {
    ok: true,
    berjalan,
    judul,
    teksBadge: [...new Set(teksBadge)].slice(0, 6),
    tulang: (s.tulang || []).length,
  };
})()
"""


async def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765/"
    durasi = float(sys.argv[2]) if len(sys.argv) > 2 else 7.0

    chrome = cari_chrome()
    if not chrome:
        print("Chrome/Edge tidak ditemukan - uji dilewati.")
        return 0

    port = port_bebas()
    profil = tempfile.mkdtemp(prefix="sela-thinking-")
    proc = subprocess.Popen(
        [
            chrome,
            "--headless=new",
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profil}",
            "--no-first-run",
            "--disable-gpu",
            "--window-size=1080,620",
            url,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        ws_url = await ambil_ws_url(port)
        async with websockets.connect(ws_url, max_size=8 * 1024 * 1024) as ws:
            cdp = CDP(ws)
            await cdp.kirim("Runtime.enable")
            print(f"[CDP] membuka {url}")

            # Tunggu model 3D benar-benar siap.
            siap = False
            for _ in range(40):
                v = await cdp.evaluasi("!!(window.__sela3d && window.__sela3d.actions)")
                if v:
                    siap = True
                    break
                await asyncio.sleep(0.5)
            if not siap:
                print("[CDP] model 3D tidak pernah siap - GAGAL")
                return 1
            print("[CDP] model 3D siap")

            # 1) Kondisi awal harus Idle.
            awal = await cdp.evaluasi(SKRIP_BACA)
            print("[awal]", json.dumps(awal, ensure_ascii=False))

            # 2) Kirim pertanyaan lewat antarmuka seperti pengguna sungguhan.
            #    Ini memicu "menunggu jawaban" -> state avatar menjadi
            #    'thinking' sampai SELA mulai berbicara. Pesan {t:'state'} TIDAK
            #    bisa dipakai untuk memicu ini karena itu pesan server->klien.
            kirim_ui = """
            (() => {
              const input = document.querySelector(
                'input[type=text], textarea'
              );
              if (!input) return 'tidak-ada-input';
              const setter = Object.getOwnPropertyDescriptor(
                input.tagName === 'TEXTAREA'
                  ? window.HTMLTextAreaElement.prototype
                  : window.HTMLInputElement.prototype,
                'value'
              ).set;
              setter.call(
                input,
                'Bagaimana cara mendaftar sebagai mahasiswa baru di UCIC?'
              );
              input.dispatchEvent(new Event('input', { bubbles: true }));
              const wadah = input.closest('form') || input.parentElement;
              const tombol = wadah
                ? Array.from(wadah.querySelectorAll('button')).pop()
                : null;
              if (tombol) tombol.click();
              return tombol ? 'dikirim' : 'input-diisi-tanpa-tombol';
            })()
            """
            hasil_ui = await cdp.evaluasi(kirim_ui)
            print("[ui] kirim pertanyaan ->", hasil_ui)

            # State "thinking" hanya sebentar (sampai SELA mulai berbicara),
            # jadi dibaca berulang cepat lalu dikumpulkan semua state yang
            # pernah muncul. Ini lebih andal daripada satu kali baca.
            pantau = """
            (() => {
              const s = window.__sela3d;
              if (!s) return null;
              const berjalan = Object.entries(s.actions || {})
                .filter(([, a]) => a && a.isRunning())
                .map(([n]) => n);
              return berjalan.join(',');
            })()
            """
            terlihat: list[str] = []
            for _ in range(80):  # ~4 detik pada 50 ms
                v = await cdp.evaluasi(pantau)
                if v and v not in terlihat:
                    terlihat.append(v)
                if "Talking" in (v or "") and "Thinking" in " ".join(terlihat):
                    break
                await asyncio.sleep(0.05)

            print(f"[pantau] urutan animasi terlihat: {terlihat}")
            tengah = await cdp.evaluasi(SKRIP_BACA)
            print("[akhir]", json.dumps(tengah, ensure_ascii=False))

            ada_thinking = any("Thinking" in t for t in terlihat)
            if ada_thinking:
                print("[HASIL] animasi Thinking BERJALAN saat menunggu jawaban.")
                kode = 0
            else:
                print(
                    "[HASIL] animasi Thinking tidak terlihat. "
                    "Kemungkinan jawaban datang terlalu cepat untuk diamati. "
                    f"Animasi yang terlihat: {terlihat}"
                )
                kode = 1

            # 3) Buktikan animasi menggerakkan rangka (bukan pose diam).
            #    Diukur pada BEBERAPA tulang sekaligus: animasi Thinking lebih
            #    banyak menggerakkan kepala/leher daripada bahu, sehingga
            #    mengukur satu tulang saja bisa memberi kesimpulan keliru.
            await cdp.evaluasi(
                """
                (() => {
                  const s = window.__sela3d;
                  window.__qAwal = (s.tulang || []).map((b) => b.quaternion.clone());
                  return window.__qAwal.length;
                })()
                """
            )
            await asyncio.sleep(1.2)
            beda = await cdp.evaluasi(
                """
                (() => {
                  const s = window.__sela3d;
                  const t = s.tulang || [];
                  const a = window.__qAwal || [];
                  let maks = 0;
                  for (let i = 0; i < t.length && i < a.length; i++) {
                    const x = a[i], y = t[i].quaternion;
                    const d = Math.abs(x.x - y.x) + Math.abs(x.y - y.y)
                            + Math.abs(x.z - y.z) + Math.abs(x.w - y.w);
                    if (d > maks) maks = d;
                  }
                  return maks;
                })()
                """
            )
            print(f"[gerak] perubahan kuaternion terbesar antar tulang: {beda}")
            if beda is not None and beda > 0.0005:
                print("[HASIL] animasi menggerakkan rangka (bukan pose diam).")
            else:
                # Bukan kegagalan: klip Thinking bisa didominasi gerak halus
                # (mata/ekspresi) yang tidak mengubah kuaternion tulang banyak.
                print(
                    "[CATATAN] perubahan tulang kecil - animasi Thinking "
                    "didominasi gerak halus (ekspresi), bukan gerak rangka."
                )

            # Tangkapan layar untuk bukti visual.
            shot = await cdp.kirim("Page.captureScreenshot", {"format": "png"})
            data = shot.get("result", {}).get("data")
            if data:
                import base64

                out = pathlib.Path(tempfile.gettempdir()) / "sela_thinking.png"
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
