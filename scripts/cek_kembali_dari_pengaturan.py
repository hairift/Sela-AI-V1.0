"""Periksa tata letak setelah kembali dari halaman Pengaturan.

Laporan pengguna: "masuk ke setting terus close lagi ada bug malah tampilannya
condong ke kiri". Tata letak halaman beranda harus kembali PERSIS seperti
sebelum Pengaturan dibuka.

Skrip ini merekam geometri elemen penting pada beranda, membuka Pengaturan
lewat menu (sama seperti pengguna), menekan tombol kembali, lalu membandingkan
geometrinya lagi. Perbedaannya harus nol (toleransi 2 px untuk pembulatan).

Pemakaian:
    python scripts/cek_kembali_dari_pengaturan.py [url-dasar]
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import tempfile
import time
import urllib.request

import websockets

from uji_asap_ui import Sesi, cari_chrome, port_bebas

TOLERANSI_PX = 2

# Elemen yang diukur. Kunci -> ekspresi JS yang mengembalikan elemen.
ELEMEN = {
    "kerangka": "document.querySelector('div.fixed.inset-0')",
    "navbar": "document.querySelector('header')",
    "utama": "document.querySelector('main')",
    "kanvas_avatar": "document.querySelector('canvas')",
    "kolom_teks": "document.getElementById('kolom-pesan')",
    "kartu_kamera": "document.querySelector('[data-kamera=\"1\"]')",
    "tombol_menu": "document.getElementById('hamburger-btn')",
}

# Nilai ukur yang diambil dari halaman.
SKRIP_UKUR = """
(() => {
  const hasil = {};
  const ambil = (nama, expr) => {
    let el = null;
    try { el = eval(expr); } catch (e) { el = null; }
    if (!el) { hasil[nama] = null; return; }
    const r = el.getBoundingClientRect();
    hasil[nama] = {
      x: Math.round(r.x), y: Math.round(r.y),
      w: Math.round(r.width), h: Math.round(r.height),
    };
  };
  %s
  hasil.__viewport = {
    lebar: window.innerWidth,
    tinggi: window.innerHeight,
    gulirX: Math.round(window.scrollX),
    gulirY: Math.round(window.scrollY),
    lebarDokumen: document.documentElement.scrollWidth,
  };
  return hasil;
})()
""" % "\n".join(
    f"  ambil({json.dumps(nama)}, {json.dumps(expr)});" for nama, expr in ELEMEN.items()
)


async def tunggu_aplikasi(url_dasar: str, batas_detik: float = 60.0) -> bool:
    akhir = time.time() + batas_detik
    while time.time() < akhir:
        try:
            with urllib.request.urlopen(url_dasar, timeout=5) as r:
                if r.status < 400:
                    return True
        except Exception:
            pass
        await asyncio.sleep(2)
    return False


async def tunggu_beranda(sesi: Sesi) -> bool:
    for _ in range(40):
        await asyncio.sleep(0.5)
        siap = await sesi.evaluasi(
            "!!document.getElementById('kolom-pesan') && !!document.querySelector('canvas')"
        )
        if siap:
            return True
    return False


# Klik tombol menu, lalu entri "Pengaturan" di dalamnya.
SKRIP_BUKA_MENU = """
(() => {
  const menu = document.getElementById('hamburger-btn');
  if (!menu) return 'tidak-ada-tombol-menu';
  menu.click();
  return 'diklik';
})()
"""

SKRIP_PILIH_PENGATURAN = """
(() => {
  const tombol = Array.from(document.querySelectorAll('button'))
    .find((b) => /pengaturan/i.test(b.textContent || ''));
  if (!tombol) return 'tidak-ada-entri-pengaturan';
  tombol.click();
  return 'diklik';
})()
"""

SKRIP_LEWATI_GERBANG = """
(() => {
  const input = document.querySelector('input[type=password]');
  if (!input) return 'sudah-terbuka';
  const setter = Object.getOwnPropertyDescriptor(
    window.HTMLInputElement.prototype, 'value'
  ).set;
  setter.call(input, 'cirebon250904');
  input.dispatchEvent(new Event('input', { bubbles: true }));
  input.dispatchEvent(new Event('change', { bubbles: true }));
  const tombol = Array.from(document.querySelectorAll('button'))
    .find((b) => /buka|masuk/i.test(b.textContent || ''));
  if (!tombol) return 'tidak-ada-tombol-buka';
  tombol.click();
  return 'diklik';
})()
"""

SKRIP_KEMBALI = """
(() => {
  const tombol = document.querySelector('button[aria-label="Kembali"]')
    || Array.from(document.querySelectorAll('button'))
      .find((b) => /kembali/i.test(b.getAttribute('aria-label') || ''));
  if (!tombol) return 'tidak-ada-tombol-kembali';
  tombol.click();
  return 'diklik';
})()
"""


def bandingkan(sebelum: dict, sesudah: dict) -> list[str]:
    """Kembalikan daftar perbedaan yang melewati toleransi."""
    beda: list[str] = []
    for nama in list(ELEMEN) + ["__viewport"]:
        a = sebelum.get(nama)
        b = sesudah.get(nama)
        if a is None and b is None:
            continue
        if a is None or b is None:
            beda.append(f"{nama}: ada={a is not None} -> ada={b is not None}")
            continue
        for kunci in a:
            if abs(a[kunci] - b[kunci]) > TOLERANSI_PX:
                beda.append(f"{nama}.{kunci}: {a[kunci]} -> {b[kunci]}")
    return beda


async def jalankan(url_dasar: str) -> int:
    if not await tunggu_aplikasi(url_dasar):
        print(
            "Aplikasi SELA belum melayani. Jalankan main.py --skip-activation.",
            file=sys.stderr,
        )
        return 2

    chrome = cari_chrome()
    if not chrome:
        print("Chrome tidak ditemukan - uji dilewati.", file=sys.stderr)
        return 0

    port = port_bebas()
    profil = tempfile.mkdtemp(prefix="sela-layout-")
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
            await sesi.kirim(
                "Emulation.setDeviceMetricsOverride",
                {"width": 1280, "height": 900, "deviceScaleFactor": 1, "mobile": False},
            )

            await sesi.kirim("Page.navigate", {"url": url_dasar.rstrip("/") + "/"})
            if not await tunggu_beranda(sesi):
                print("Antarmuka SELA tidak selesai dimuat.", file=sys.stderr)
                return 2
            # Beri waktu avatar 3D dan tata letak stabil.
            await asyncio.sleep(2.5)

            sebelum = await sesi.evaluasi(SKRIP_UKUR)
            print("[sebelum] ")
            for nama, nilai in (sebelum or {}).items():
                print(f"   {nama:16s} {nilai}")

            # ---- Buka Pengaturan seperti pengguna ----
            print(f"[menu] {await sesi.evaluasi(SKRIP_BUKA_MENU)}")
            await asyncio.sleep(0.8)
            print(f"[pilih pengaturan] {await sesi.evaluasi(SKRIP_PILIH_PENGATURAN)}")
            await asyncio.sleep(1.2)
            print(f"[gerbang admin] {await sesi.evaluasi(SKRIP_LEWATI_GERBANG)}")

            # Tunggu isi pengaturan benar-benar muncul.
            terbuka = False
            for _ in range(40):
                await asyncio.sleep(0.5)
                terbuka = await sesi.evaluasi(
                    "!!document.querySelector('button[aria-label=\"Kembali\"]')"
                )
                if terbuka:
                    break
            if not terbuka:
                print("Halaman pengaturan tidak terbuka.", file=sys.stderr)
                return 2
            await asyncio.sleep(1.0)

            # ---- Kembali ke beranda ----
            print(f"[kembali] {await sesi.evaluasi(SKRIP_KEMBALI)}")
            if not await tunggu_beranda(sesi):
                print("Tidak kembali ke beranda.", file=sys.stderr)
                return 2
            await asyncio.sleep(2.5)

            sesudah = await sesi.evaluasi(SKRIP_UKUR)
            print("[sesudah]")
            for nama, nilai in (sesudah or {}).items():
                print(f"   {nama:16s} {nilai}")

            beda = bandingkan(sebelum or {}, sesudah or {})
            print()
            if beda:
                print(f"HASIL: GAGAL - tata letak bergeser setelah kembali ({len(beda)}):")
                for b in beda:
                    print(f"   - {b}")
                return 1
            print("HASIL: tata letak kembali persis seperti semula.")
            return 0
    finally:
        proses.terminate()
        try:
            proses.wait(timeout=10)
        except Exception:
            proses.kill()


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765"
    sys.exit(asyncio.run(jalankan(url)))
