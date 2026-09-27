"""Periksa perilaku kamera SELA di peramban sungguhan (Chrome + CDP).

Yang diperiksa - semuanya butuh bukti dari DOM, bukan dugaan:

  1. Kartu kamera tampil dan kameranya benar-benar terbuka (video mengalir).
  2. Tombol PANAH melipat kartu jadi pil kecil - bukan mematikan kamera.
  3. Saat terlipat: kartu masih ada di DOM tetapi tersembunyi, video masih
     mengalir, DAN bingkai hidup masih dikirim ke mesin AI. Inilah yang membuat
     SELA tetap bisa menjawab "saya lagi ngapain?" walau kartunya disembunyikan.
  4. Pil kecil membentangkan kartu kembali.
  5. Saklar induk di Pengaturan mematikan kamera SEPENUHNYA: kartu hilang DAN
     pil kecil pun tidak ada, jadi tidak ada jalan masuk.
  6. Tombol "Ambil Foto" menaruh foto sebagai LAMPIRAN di kotak teks, bukan
     langsung jadi gelembung percakapan.

Chrome dijalankan dengan kamera palsu (``--use-fake-device-for-media-stream``)
supaya getUserMedia berhasil walau mesin ini tidak punya kamera.

Pemakaian:
    python scripts/cek_kamera_ui.py [url-dasar]
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

BATAS_TUNGGU_S = 60.0


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


async def muat_halaman(sesi: Sesi, url: str) -> None:
    await sesi.kirim("Page.navigate", {"url": url})
    for _ in range(40):
        await asyncio.sleep(0.5)
        siap = await sesi.evaluasi("!!document.getElementById('kolom-pesan')")
        if siap:
            return
    raise RuntimeError("antarmuka SELA tidak selesai dimuat")


async def jalankan(url_dasar: str) -> int:
    if not await tunggu_aplikasi(url_dasar):
        print(
            "Aplikasi SELA belum melayani. Jalankan main.py --skip-activation.",
            file=sys.stderr,
        )
        return 2

    chrome = cari_chrome()
    if not chrome:
        print("Chrome tidak ditemukan.", file=sys.stderr)
        return 2

    port = port_bebas()
    profil = tempfile.mkdtemp(prefix="sela-kamera-")
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
            # Kamera palsu supaya getUserMedia berhasil tanpa perangkat nyata.
            "--use-fake-ui-for-media-stream",
            "--use-fake-device-for-media-stream",
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profil}",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    lulus: list[str] = []
    gagal: list[str] = []

    def catat(ok: bool, judul: str, bukti: str = "") -> None:
        (lulus if ok else gagal).append(judul)
        tanda = "OK   " if ok else "GAGAL"
        print(f"  {tanda} {judul}" + (f"  [{bukti}]" if bukti else ""))

    dasar = url_dasar.rstrip("/") + "/"

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

            # ---- Keadaan awal: saklar induk menyala ----
            await sesi.evaluasi("localStorage.removeItem('sela_kamera_melayang');"
                                "localStorage.removeItem('sela_kamera_terbuka');"
                                "localStorage.removeItem('sela_kamera_posisi'); 1")
            await muat_halaman(sesi, dasar)

            ada_kartu = await sesi.evaluasi(
                "!!document.querySelector('[data-kamera=\"1\"]')"
            )
            catat(bool(ada_kartu), "Kartu kamera tampil saat kamera dinyalakan")

            # Tunggu kamera benar-benar terbuka.
            lebar = 0
            for _ in range(30):
                await asyncio.sleep(0.5)
                lebar = await sesi.evaluasi(
                    "(() => { const v = document.querySelector('[data-kamera=\"1\"] video');"
                    " return v ? v.videoWidth : 0 })()"
                ) or 0
                if lebar:
                    break
            catat(lebar > 0, "Kamera benar-benar terbuka", f"videoWidth={lebar}px")

            # ---- Tombol panah melipat kartu jadi pil kecil ----
            # Kartu TIDAK dilepas dari React (kalau dilepas, getUserMedia mati
            # dan SELA berhenti melihat). Ia hanya disembunyikan secara visual.
            await sesi.evaluasi(
                "document.querySelector('[data-kamera-lipat=\"1\"]').click(); 1"
            )
            await asyncio.sleep(0.6)
            kartu_masih_ada = await sesi.evaluasi(
                "!!document.querySelector('[data-kamera=\"1\"]')"
            )
            kartu_tersembunyi = await sesi.evaluasi(
                "(() => { const k = document.querySelector('[data-kamera=\"1\"]');"
                " return k ? k.getAttribute('data-kamera-tersembunyi') : null })()"
            )
            pil_muncul = await sesi.evaluasi(
                "!!document.querySelector('[data-kamera-ikon=\"1\"]')"
            )
            catat(
                bool(kartu_masih_ada) and kartu_tersembunyi == "1" and bool(pil_muncul),
                "Tombol panah melipat kartu jadi pil kecil",
                f"kartu={bool(kartu_masih_ada)} tersembunyi={kartu_tersembunyi} "
                f"pil={bool(pil_muncul)}",
            )

            # ---- Saat tersembunyi, video HARUS tetap mengalir ----
            lebar_sembunyi = 0
            for _ in range(20):
                await asyncio.sleep(0.5)
                lebar_sembunyi = await sesi.evaluasi(
                    "(() => { const v = document.querySelector('[data-kamera=\"1\"] video');"
                    " return v ? v.videoWidth : 0 })()"
                ) or 0
                if lebar_sembunyi:
                    break
            catat(
                lebar_sembunyi > 0,
                "Video tetap mengalir walau kartu disembunyikan",
                f"videoWidth={lebar_sembunyi}px",
            )

            # ---- Dan bingkai hidup tetap dikirim ke mesin AI ----
            await sesi.evaluasi(
                "(() => { window.__bingkai = 0;"
                " if (window.__spionBingkai) return 1;"
                " const asli = WebSocket.prototype.send;"
                " WebSocket.prototype.send = function (d) {"
                "   try { if (typeof d === 'string' && d.indexOf('kamera_bingkai') >= 0)"
                "     window.__bingkai += 1; } catch (e) {}"
                "   return asli.apply(this, arguments); };"
                " window.__spionBingkai = true; return 1 })()"
            )
            # Jeda bingkai hidup 5 detik; beri ruang 14 detik supaya kebal lambat.
            await asyncio.sleep(14)
            jumlah_bingkai = await sesi.evaluasi("window.__bingkai || 0") or 0
            catat(
                jumlah_bingkai > 0,
                "Bingkai hidup tetap dikirim ke mesin AI saat kartu disembunyikan",
                f"bingkai={jumlah_bingkai} dalam 14 dtk",
            )

            # ---- Pil kecil membentangkan kembali ----
            await sesi.evaluasi(
                "document.querySelector('[data-kamera-ikon=\"1\"]').click(); 1"
            )
            await asyncio.sleep(0.6)
            kartu_kembali = await sesi.evaluasi(
                "(() => { const k = document.querySelector('[data-kamera=\"1\"]');"
                " if (!k) return null; return k.getAttribute('data-kamera-tersembunyi') })()"
            )
            catat(
                kartu_kembali == "0",
                "Pil kecil membentangkan kartu kembali",
                f"tersembunyi={kartu_kembali}",
            )

            # ---- Saklar induk OFF: tidak ada kartu, tidak ada ikon ----
            await sesi.evaluasi("localStorage.setItem('sela_kamera_melayang','0'); 1")
            await muat_halaman(sesi, dasar)
            await asyncio.sleep(1.0)
            kartu_mati = await sesi.evaluasi(
                "!!document.querySelector('[data-kamera=\"1\"]')"
            )
            ikon_mati = await sesi.evaluasi(
                "!!document.querySelector('[data-kamera-ikon=\"1\"]')"
            )
            catat(
                not kartu_mati and not ikon_mati,
                "Saklar induk mati: kartu DAN ikon kecil sama-sama hilang",
                f"kartu={bool(kartu_mati)} ikon={bool(ikon_mati)}",
            )

            # ---- Nyalakan lagi, lalu uji lampiran foto ----
            await sesi.evaluasi("localStorage.setItem('sela_kamera_melayang','1'); 1")
            await muat_halaman(sesi, dasar)
            await asyncio.sleep(2.0)

            # Buka panel obrolan kalau tertutup (ikon kamera ada di beranda).
            await sesi.evaluasi(
                "(() => { const b = document.getElementById('kolom-pesan');"
                " if (b) b.scrollIntoView(); return 1 })()"
            )
            await asyncio.sleep(0.5)

            jumlah_gelembung_sebelum = await sesi.evaluasi(
                "document.querySelectorAll('[data-peran]').length"
            ) or 0

            diambil = await sesi.evaluasi(
                "(() => { const b = document.querySelector('[data-kamera-ambil=\"1\"]');"
                " if (!b) return 'tombol-tidak-ada'; b.click(); return 'ok' })()"
            )
            await asyncio.sleep(1.5)

            ada_lampiran = await sesi.evaluasi(
                "!!document.querySelector('[data-lampiran=\"1\"]')"
            )
            jumlah_gelembung_sesudah = await sesi.evaluasi(
                "document.querySelectorAll('[data-peran]').length"
            ) or 0

            catat(
                diambil == "ok",
                "Tombol Ambil Foto bisa ditekan",
                str(diambil),
            )
            catat(
                bool(ada_lampiran),
                "Foto masuk sebagai lampiran di kotak teks",
            )
            catat(
                jumlah_gelembung_sesudah == jumlah_gelembung_sebelum,
                "Foto TIDAK langsung jadi gelembung percakapan",
                f"gelembung {jumlah_gelembung_sebelum} -> {jumlah_gelembung_sesudah}",
            )

            galat = [g for g in sesi.galat if g]
            catat(not galat, "Tidak ada galat JS", f"temuan={len(galat)}")
            for g in galat[:5]:
                print(f"        - {g}")

    finally:
        proses.terminate()
        try:
            proses.wait(timeout=10)
        except Exception:
            proses.kill()

    print()
    if gagal:
        print(f"LULUS {len(lulus)} pemeriksaan, GAGAL {len(gagal)}:")
        for g in gagal:
            print(f"  - {g}")
        return 1
    print(f"LULUS {len(lulus)} pemeriksaan, GAGAL 0.")
    return 0


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765"
    sys.exit(asyncio.run(jalankan(url)))
