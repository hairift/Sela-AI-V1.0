"""Periksa perilaku percakapan SELA di peramban sungguhan (Chrome + CDP).

Yang diperiksa - semuanya butuh bukti dari DOM, bukan dugaan:

  1. Avatar pengguna (``user.png``) dan SELA (``sela.png``) benar-benar termuat.
  2. Kotak teks punya batas panjang (``maxlength``) sesuai MAKS_PANJANG_TEKS.
  3. Selagi SELA berbicara, gelembung menampilkan **visualizer audio**
     (ditandai ``data-visualizer``), bukan teks.
  4. Setelah suara selesai, teks muncul dengan efek mengetik dan berakhir utuh.
  5. Jawaban tampil sebagai SATU gelembung (bukan banyak gelembung kecil).
  6. Tidak ada karakter markdown mentah (``**``) yang ikut terlihat.
  7. Papan langkah alat muncul saat mesin AI memanggil alat.
  8. Baris "tanya lanjut" muncul di bawah jawaban.
  9. Kartu peta muncul untuk jawaban yang menyebut alamat kampus.
 10. Kartu kamera melayang tampil dan kameranya benar-benar terbuka.

Pemakaian:
    python scripts/cek_percakapan_baru.py [url-dasar]
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

from uji_asap_ui import CHROME_KANDIDAT, Sesi, cari_chrome, port_bebas

# Pertanyaan yang memicu tool pengetahuan kampus (dan karena itu memuat alamat).
PERTANYAAN = "Kontak dan lokasi UCIC?"

# Berapa lama menunggu jawaban lengkap (mesin AI membacakan dengan suara dulu).
BATAS_TUNGGU_S = 150.0


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


async def potret(sesi: Sesi, nama: str) -> str:
    """Simpan tangkapan layar sebagai bukti visual."""
    hasil = await sesi.kirim("Page.captureScreenshot", {"format": "png"})
    data = hasil.get("data")
    if not data:
        return ""
    jalur = pathlib.Path(tempfile.gettempdir()) / nama
    jalur.write_bytes(base64.b64decode(data))
    return str(jalur)


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
    profil = tempfile.mkdtemp(prefix="sela-obrol-")
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
            # Kamera palsu: Chrome menyediakan perangkat uji sehingga
            # getUserMedia berhasil walau mesin ini tidak punya kamera.
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
            await sesi.kirim("Emulation.setDeviceMetricsOverride",
                             {"width": 1280, "height": 900, "deviceScaleFactor": 1,
                              "mobile": False})

            await sesi.kirim("Page.navigate", {"url": url_dasar.rstrip("/") + "/"})
            for _ in range(40):
                await asyncio.sleep(1)
                siap = await sesi.evaluasi(
                    "!!document.getElementById('kolom-pesan')"
                )
                if siap:
                    break

            # ---------- 1. Batas teks & kartu kamera ----------
            # Avatar baru muncul setelah ada pesan, jadi diperiksa belakangan.
            await asyncio.sleep(2)
            info = await sesi.evaluasi(
                """(() => {
                  const input = document.getElementById('kolom-pesan');
                  const kamera = document.querySelector('[data-kamera="1"]');
                  const video = kamera ? kamera.querySelector('video') : null;
                  return JSON.stringify({
                    maxlength: input ? input.getAttribute('maxlength') : null,
                    kamera: !!kamera,
                    video: !!video,
                  });
                })()"""
            )
            d = json.loads(info)
            catat(d["maxlength"] == "24", "Kotak teks punya batas panjang",
                  f"maxlength={d['maxlength']}")
            catat(d["kamera"], "Kartu kamera melayang tampil")
            await asyncio.sleep(3)
            videoW = await sesi.evaluasi(
                """(() => {
                  const v = document.querySelector('[data-kamera="1"] video');
                  return v ? v.videoWidth : 0;
                })()"""
            )
            catat(bool(videoW), "Kamera kartu benar-benar terbuka",
                  f"lebar video={videoW}px")

            # ---------- 2. Kirim pertanyaan lokasi kampus ----------
            print(f"\n  ... mengirim: {PERTANYAAN!r} (menunggu jawaban)")
            await sesi.evaluasi(
                f"window.__selaKirim && window.__selaKirim({json.dumps(PERTANYAAN)})"
            )

            terlihat = {
                "visualizer": False,
                "alat": False,
                "peta": False,
                "saran": False,
                "papanAlatLabel": "",
            }
            akhir = time.time() + BATAS_TUNGGU_S
            jawaban_selesai = False
            while time.time() < akhir:
                await asyncio.sleep(0.25)
                status = await sesi.evaluasi(
                    """(() => {
                      const vis = document.querySelector('[data-visualizer="1"]');
                      const alat = document.querySelector('[data-alat="1"]');
                      const peta = document.querySelector('[data-peta="1"]');
                      const saran = document.querySelector('[data-saran="1"]');
                      const tuntas = document.querySelector(
                        '[data-peran="assistant"][data-muat="0"][data-selesai="1"]'
                      );
                      return JSON.stringify({
                        vis: !!vis,
                        alat: !!alat,
                        alatLabel: alat ? (alat.innerText || '').split('\\n')[0] : '',
                        peta: !!peta,
                        saran: !!saran,
                        tuntas: !!tuntas,
                        jumlahAsisten: document.querySelectorAll(
                          '[data-peran="assistant"][data-muat="0"]'
                        ).length,
                      });
                    })()"""
                )
                try:
                    s = json.loads(status)
                except Exception:
                    continue
                terlihat["visualizer"] |= s["vis"]
                terlihat["alat"] |= s["alat"]
                terlihat["peta"] |= s["peta"]
                terlihat["saran"] |= s["saran"]
                if s["alatLabel"]:
                    terlihat["papanAlatLabel"] = s["alatLabel"]
                if s["tuntas"]:
                    jawaban_selesai = True
                    break

            catat(jawaban_selesai, "Jawaban selesai tampil (efek mengetik tuntas)")
            catat(terlihat["visualizer"],
                  "Visualizer audio tampil selagi SELA berbicara")
            catat(terlihat["alat"],
                  "Papan langkah alat muncul saat mesin AI memanggil alat",
                  terlihat["papanAlatLabel"])

            # Diagnostik: keadaan DOM saat jawaban selesai, supaya kegagalan
            # bisa ditelusuri tanpa menebak.
            diag = await sesi.evaluasi(
                """(() => {
                  const saran = document.querySelectorAll('[data-saran="1"]');
                  const gelembung = [...document.querySelectorAll('[data-peran="assistant"]')];
                  const terakhir = gelembung[gelembung.length - 1];
                  const gambar = [...document.images].map(i => ({
                    src: i.getAttribute('src'),
                    selesai: i.complete,
                    w: i.naturalWidth,
                  }));
                  return JSON.stringify({
                    jumlahBarisSaran: saran.length,
                    jumlahGelembungAsisten: gelembung.length,
                    dataSelesai: terakhir ? terakhir.getAttribute('data-selesai') : null,
                    dataBicara: terakhir ? terakhir.getAttribute('data-bicara') : null,
                    tombolDiGelembung: terakhir
                      ? [...terakhir.querySelectorAll('button')]
                          .map(b => (b.innerText || '').trim())
                          .slice(0, 4)
                      : [],
                    gambar,
                  });
                })()"""
            )
            print(f"  Diagnostik       : {diag}")
            catat(terlihat["saran"], "Baris tanya lanjut muncul di bawah jawaban")

            # ---------- 3. Pemeriksaan isi jawaban ----------
            # Tunggu avatar benar-benar ter-decode (berkas 280-320 KB). Dipakai
            # ".some()" karena gelembung lama bisa tergulir keluar layar dan
            # gambarnya (loading="lazy") belum diunduh.
            avatar = {"sela": 0, "user": 0}
            for _ in range(20):
                await asyncio.sleep(0.5)
                avatar = json.loads(
                    await sesi.evaluasi(
                        """(() => {
                          const lebar = (sel) => Math.max(
                            0,
                            ...[...document.querySelectorAll(sel)]
                              .map(i => i.naturalWidth)
                          );
                          return JSON.stringify({
                            sela: lebar('img[src="/sela.png"]'),
                            user: lebar('img[src="/user.png"]'),
                          });
                        })()"""
                    )
                )
                if avatar["sela"] and avatar["user"]:
                    break

            ringkas = await sesi.evaluasi(
                """(() => {
                  const semua = [...document.querySelectorAll('[data-peran]')];
                  const asisten = semua.filter(
                    e => e.dataset.peran === 'assistant' && e.dataset.muat === '0'
                  );
                  const pengguna = semua.filter(e => e.dataset.peran === 'user');
                  const teks = asisten.map(e => e.innerText || '').join('\\n');
                  const petaIframe = document.querySelector(
                    '[data-peta="1"] iframe'
                  );
                  return JSON.stringify({
                    jumlahAsisten: asisten.length,
                    jumlahPengguna: pengguna.length,
                    bintangMentah: (teks.match(/\\*\\*/g) || []).length,
                    panjangTeks: teks.length,
                    cuplikan: teks.slice(0, 220).replace(/\\n/g, ' | '),
                    petaSrc: petaIframe ? petaIframe.getAttribute('src') : '',
                  });
                })()"""
            )
            r = json.loads(ringkas)
            catat(avatar["sela"] > 0, "Avatar SELA (sela.png) termuat",
                  f"lebar={avatar['sela']}px")
            catat(avatar["user"] > 0, "Avatar pengguna (user.png) termuat",
                  f"lebar={avatar['user']}px")
            catat(r["jumlahAsisten"] == 1, "Jawaban tampil sebagai SATU gelembung",
                  f"jumlah gelembung asisten={r['jumlahAsisten']}")
            catat(r["bintangMentah"] == 0, "Tidak ada markdown mentah (**) terlihat",
                  f"temuan={r['bintangMentah']}")
            catat("openstreetmap" in (r["petaSrc"] or ""),
                  "Peta memakai OpenStreetMap (tanpa kunci API)",
                  (r["petaSrc"] or "")[:70])
            catat(terlihat["peta"] or ("openstreetmap" in (r["petaSrc"] or "")),
                  "Kartu peta muncul untuk jawaban berisi alamat kampus")

            print(f"\n  Cuplikan jawaban: {r['cuplikan']}")
            print(f"  Panjang jawaban : {r['panjangTeks']} karakter")

            foto = await potret(sesi, "sela_percakapan_baru.png")
            if foto:
                print(f"  Tangkapan layar : {foto}")

    finally:
        proses.terminate()
        try:
            proses.wait(timeout=10)
        except Exception:
            proses.kill()
        shutil.rmtree(profil, ignore_errors=True)

    print()
    print(f"LULUS {len(lulus)} pemeriksaan, GAGAL {len(gagal)}.")
    if gagal:
        for g in gagal:
            print(f"  - {g}")
        return 1
    return 0


if __name__ == "__main__":
    dasar = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765"
    raise SystemExit(asyncio.run(jalankan(dasar)))
