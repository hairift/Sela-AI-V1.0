"""Cari bentuk pesan protokol yang menerima teks panjang.

Server xiaozhi (``api.tenclass.net``) menolak teks panjang pada jalur
``listen/detect``: "Detect is only for wake words, do not send long texts."
Skrip ini terhubung LANGSUNG ke server memakai kredensial perangkat, lalu
mencoba beberapa bentuk pesan untuk menemukan jalur yang menerima teks
sepanjang apa pun.

Pemakaian:
    python scripts/uji_jalur_teks.py
"""

from __future__ import annotations

import asyncio
import json
import pathlib
import sys
import time

import websockets

TEKS_PANJANG = "bagaimana cara saya mendaftar sebagai mahasiswa baru di UCIC tahun ini"


def muat_konfigurasi() -> dict:
    jalur = pathlib.Path.home() / "AppData/Local/sela-ai/sela-ai/config/config.json"
    if not jalur.is_file():
        jalur = pathlib.Path("config/config.json")
    return json.loads(jalur.read_text(encoding="utf-8"))


async def uji(ws, judul: str, pesan: dict, tunggu: float = 18.0) -> dict:
    """Kirim satu pesan, catat apakah server menolak atau menjawab."""
    print(f"\n--- {judul} ---")
    ringkas = {k: (str(v)[:50] + "..." if len(str(v)) > 50 else v) for k, v in pesan.items()}
    print(f"    kirim: {json.dumps(ringkas, ensure_ascii=False)}")

    await ws.send(json.dumps(pesan))

    peringatan = []
    jawaban = []
    akhir = time.monotonic() + tunggu
    while time.monotonic() < akhir:
        try:
            mentah = await asyncio.wait_for(ws.recv(), timeout=akhir - time.monotonic())
        except asyncio.TimeoutError:
            break
        try:
            m = json.loads(mentah)
        except Exception:
            continue
        t = m.get("type")
        if t == "alert":
            peringatan.append(str(m.get("message"))[:100])
            break
        if t == "tts" and m.get("text"):
            jawaban.append(str(m["text"])[:100])
        if t == "tts" and m.get("state") == "stop":
            break

    if peringatan:
        print(f"    DITOLAK : {peringatan[0]}")
    elif jawaban:
        print(f"    DITERIMA: {jawaban[0]}")
    else:
        print("    (tanpa tanggapan)")
    return {"judul": judul, "ditolak": bool(peringatan), "jawaban": jawaban}


async def main() -> int:
    cfg = muat_konfigurasi()
    net = cfg["SYSTEM_OPTIONS"]["NETWORK"]
    url = net["WEBSOCKET_URL"]
    token = net.get("WEBSOCKET_ACCESS_TOKEN", "test-token")
    device_id = cfg["SYSTEM_OPTIONS"].get("DEVICE_ID", "0a:00:27:00:00:10")
    client_id = cfg["SYSTEM_OPTIONS"].get("CLIENT_ID", "")

    headers = {
        "Authorization": f"Bearer {token}",
        "Protocol-Version": "1",
        "Device-Id": device_id,
        "Client-Id": client_id,
    }
    print(f"menghubungi {url}")

    try:
        ws = await websockets.connect(url, additional_headers=headers, max_size=8 * 1024 * 1024)
    except Exception as e:
        print(f"GAGAL menyambung: {type(e).__name__}: {e}")
        return 1

    async with ws:
        # Sapaan pembuka.
        await ws.send(json.dumps({
            "type": "hello",
            "version": 1,
            "transport": "websocket",
            "features": {"mcp": True},
            "audio_params": {"format": "opus", "sample_rate": 16000, "channels": 1, "frame_duration": 20},
        }))

        sid = None
        akhir = time.monotonic() + 10
        while time.monotonic() < akhir and not sid:
            try:
                m = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
            except Exception:
                break
            if m.get("type") == "hello":
                sid = m.get("session_id")
                print(f"sesi: {sid}")

        dasar = {"session_id": sid}
        hasil = []

        # 1. Jalur yang dipakai sekarang (acuan, pasti ditolak untuk teks panjang).
        hasil.append(await uji(ws, "A. listen/detect (jalur sekarang)", {
            **dasar, "type": "listen", "state": "detect", "text": TEKS_PANJANG,
        }))
        await asyncio.sleep(1)

        # 2. detect + mode manual.
        hasil.append(await uji(ws, "B. listen/detect + mode manual", {
            **dasar, "type": "listen", "state": "detect", "text": TEKS_PANJANG, "mode": "manual",
        }))
        await asyncio.sleep(1)

        # 3. Tipe pesan "text" langsung.
        hasil.append(await uji(ws, "C. type=text", {
            **dasar, "type": "text", "text": TEKS_PANJANG,
        }))
        await asyncio.sleep(1)

        # 4. Mulai sesi manual lalu kirim teks sebagai pesan terpisah.
        hasil.append(await uji(ws, "D. listen/start manual lalu text", {
            **dasar, "type": "listen", "state": "start", "mode": "manual",
        }, tunggu=4))
        await asyncio.sleep(1)
        hasil.append(await uji(ws, "E. text setelah sesi manual", {
            **dasar, "type": "text", "text": TEKS_PANJANG,
        }))
        await asyncio.sleep(1)

        # 6. Tipe "message".
        hasil.append(await uji(ws, "F. type=message", {
            **dasar, "type": "message", "content": TEKS_PANJANG,
        }))

    print("\n=== RINGKASAN ===")
    for h in hasil:
        tanda = "DITOLAK " if h["ditolak"] else ("DITERIMA" if h["jawaban"] else "DIAM    ")
        print(f"  {tanda}  {h['judul']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
