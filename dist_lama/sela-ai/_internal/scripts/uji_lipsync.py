"""Uji lipsync: pastikan data bukaan mulut benar-benar mengalir saat AI bicara.

Mengirim teks ke SELA, lalu mencatat pesan `lip` yang datang. Bila nilai
`v` selalu 0, berarti mulut avatar tidak akan bergerak.

Pemakaian:
    python scripts/uji_lipsync.py "halo sela"
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


async def main() -> int:
    pertanyaan = sys.argv[1] if len(sys.argv) > 1 else "halo sela"
    alamat = cari_alamat()
    if not alamat:
        print("Aplikasi SELA tidak berjalan.")
        return 1
    print("alamat:", alamat)

    async with websockets.connect(alamat, max_size=8 * 1024 * 1024) as ws:
        try:
            await asyncio.wait_for(ws.recv(), timeout=4)
        except Exception:
            pass

        print(f"[kirim] {pertanyaan}")
        await ws.send(json.dumps({"t": "send_text", "text": pertanyaan}))

        jumlah_lip = 0
        maks_v = 0.0
        viseme_terlihat: set[str] = set()
        keadaan: set[str] = set()
        akhir = time.monotonic() + 40

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
            if t == "lip":
                jumlah_lip += 1
                v = float(m.get("v") or 0)
                maks_v = max(maks_v, v)
                if v > 0.01:
                    viseme_terlihat.add(str(m.get("viseme")))
            elif t == "state":
                keadaan.add(str(m.get("state")))
            elif t == "chat" and m.get("role") == "assistant":
                print(f"[jawaban] {str(m.get('text'))[:100]}")

        print()
        print(f"paket lip diterima : {jumlah_lip}")
        print(f"bukaan mulut maks  : {maks_v:.3f}")
        print(f"viseme terlihat    : {sorted(viseme_terlihat) or '(tidak ada)'}")
        print(f"state yang muncul  : {sorted(keadaan)}")
        if maks_v > 0.01:
            print("\nHASIL: LIPSYNC BERFUNGSI - data bukaan mulut mengalir.")
            return 0
        print("\nHASIL: LIPSYNC TIDAK BERFUNGSI - bukaan mulut selalu 0.")
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
