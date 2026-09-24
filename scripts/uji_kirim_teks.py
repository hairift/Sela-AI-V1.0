"""Cari tahu jalur protokol mana yang menerima teks panjang.

Server xiaozhi menolak teks panjang pada jalur ``listen/detect`` dengan pesan
"Detect is only for wake words, do not send long texts." Skrip ini mencoba
beberapa bentuk pesan dan mencatat mana yang diterima, supaya aplikasi bisa
memakai jalur yang benar untuk tombol pertanyaan cepat.

Pemakaian:
    python scripts/uji_kirim_teks.py
"""

from __future__ import annotations

import asyncio
import json
import socket
import sys
import time

import websockets


def cari_alamat() -> str | None:
    for port in range(8765, 8780):
        s = socket.socket()
        s.settimeout(0.3)
        try:
            s.connect(("127.0.0.1", port))
            s.close()
            return f"ws://127.0.0.1:{port}/ws"
        except Exception:
            s.close()
    return None


# Panjang teks yang akan diuji.
TEKS_PENDEK = "halo sela"
TEKS_PANJANG = "bagaimana cara saya mendaftar sebagai mahasiswa baru di UCIC tahun ini"


async def coba(ws, judul: str, teks: str, tunggu: float = 60.0) -> dict:
    """Kirim teks lewat perintah antarmuka, catat tanggapan mesin AI."""
    print(f"\n--- {judul} ({len(teks)} karakter) ---")
    print(f"    teks: {teks[:60]}{'...' if len(teks) > 60 else ''}")

    await ws.send(json.dumps({"t": "send_text", "text": teks}))

    peringatan = []
    jawaban = []
    akhir = time.monotonic() + tunggu
    while time.monotonic() < akhir:
        try:
            mentah = await asyncio.wait_for(
                ws.recv(), timeout=akhir - time.monotonic()
            )
        except asyncio.TimeoutError:
            break
        try:
            m = json.loads(mentah)
        except Exception:
            continue
        t = m.get("t")
        if t == "notice":
            peringatan.append(str(m.get("text"))[:120])
        elif t == "chat" and m.get("role") == "assistant":
            teks = str(m.get("text"))
            jawaban.append(teks[:120])
            # Jawaban sudah mulai berdatangan; cukup tunggu kalimat pertama.
            if len(teks) > 8:
                break
        # CATATAN: jangan keluar saat status menjadi "Siap". Pada jalur suara
        # panjang, status itu muncul begitu rekaman ditutup — jauh sebelum
        # jawaban datang — sehingga uji akan kehilangan jawabannya.

    if peringatan:
        print(f"    PERINGATAN: {peringatan[0]}")
    if jawaban:
        print(f"    jawaban   : {jawaban[0]}")
    if not peringatan and not jawaban:
        print("    (tidak ada tanggapan)")

    return {
        "panjang": len(teks),
        "peringatan": peringatan,
        "jawaban": jawaban,
        "berhasil": bool(jawaban) and not peringatan,
    }


async def main() -> int:
    alamat = cari_alamat()
    if not alamat:
        print("Aplikasi SELA tidak berjalan.")
        return 1
    print("alamat:", alamat)

    hasil = []
    async with websockets.connect(alamat, max_size=8 * 1024 * 1024) as ws:
        try:
            await asyncio.wait_for(ws.recv(), timeout=5)
        except Exception:
            pass

        hasil.append(await coba(ws, "teks pendek (acuan)", TEKS_PENDEK))
        await asyncio.sleep(2)
        hasil.append(await coba(ws, "teks panjang (gejala)", TEKS_PANJANG))

    print("\n=== ringkasan ===")
    for h in hasil:
        tanda = "DITERIMA" if h["berhasil"] else "DITOLAK "
        print(f"  {tanda} {h['panjang']:3} karakter")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
