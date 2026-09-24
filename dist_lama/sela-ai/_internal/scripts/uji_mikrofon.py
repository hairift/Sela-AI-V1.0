"""Uji alur tombol mikrofon: manual_toggle -> rekam -> kirim -> jawaban.

Membantu mendiagnosis keluhan "tombol mikrofon tidak berfungsi": kita kirim
perintah yang sama dengan yang dikirim antarmuka web, lalu catat seluruh
perubahan status yang datang dari mesin AI.

Pemakaian:
    python scripts/uji_mikrofon.py
"""

from __future__ import annotations

import asyncio
import json
import socket
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


async def pantau(ws, detik: float, judul: str) -> None:
    print(f"\n--- {judul} ---")
    akhir = time.monotonic() + detik
    while time.monotonic() < akhir:
        try:
            mentah = await asyncio.wait_for(ws.recv(), timeout=akhir - time.monotonic())
        except asyncio.TimeoutError:
            break
        try:
            m = json.loads(mentah)
        except Exception:
            continue
        t = m.get("t")
        if t in ("state", "status", "button_text", "notice", "chat", "emotion"):
            isi = {k: v for k, v in m.items() if k != "t"}
            print(f"   [{t}] {json.dumps(isi, ensure_ascii=False)[:140]}")


async def main() -> int:
    alamat = cari_alamat()
    if not alamat:
        print("Aplikasi SELA tidak berjalan.")
        return 1
    print("alamat:", alamat)

    async with websockets.connect(alamat, max_size=8 * 1024 * 1024) as ws:
        try:
            snap = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
            print("snapshot:", {k: snap.get(k) for k in ("t", "connected", "deviceState")})
        except Exception:
            pass

        await ws.send(json.dumps({"t": "manual_toggle"}))
        await pantau(ws, 8, "manual_toggle #1 (mulai rekam)")

        await ws.send(json.dumps({"t": "manual_toggle"}))
        await pantau(ws, 14, "manual_toggle #2 (stop & kirim)")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
