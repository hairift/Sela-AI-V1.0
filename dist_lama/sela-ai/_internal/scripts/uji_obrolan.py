"""Uji cepat: kirim teks ke SELA lewat WebSocket dan lihat jawabannya.

Dipakai untuk memastikan rantai lengkap berjalan - antarmuka web, jembatan
EventBus, protokol ke mesin AI, dan bahasa jawaban.

Pemakaian:
    python scripts/uji_obrolan.py "Halo SELA, siapa kamu?"
"""

from __future__ import annotations

import asyncio
import json
import sys

import websockets

ALAMAT_DEFAULT = "ws://127.0.0.1:8765/ws"


def cari_alamat() -> str:
    """Temukan port antarmuka SELA yang benar-benar aktif.

    Aplikasi otomatis pindah port bila 8765 terpakai, jadi jangan berasumsi.
    """
    if len(sys.argv) > 2:
        return f"ws://127.0.0.1:{sys.argv[2]}/ws"

    import socket

    for port in range(8765, 8780):
        s = socket.socket()
        s.settimeout(0.3)
        try:
            s.connect(("127.0.0.1", port))
            s.close()
            return f"ws://127.0.0.1:{port}/ws"
        except Exception:
            s.close()
            continue
    return ALAMAT_DEFAULT


async def main() -> int:
    pertanyaan = sys.argv[1] if len(sys.argv) > 1 else "Halo SELA, siapa kamu?"
    alamat = cari_alamat()
    print(f"[alamat] {alamat}")

    async with websockets.connect(alamat, max_size=8 * 1024 * 1024) as ws:
        # Pesan pertama selalu snapshot status.
        try:
            awal = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
            print(f"[status awal] {awal.get('t')} -> connected={awal.get('connected')}")
        except Exception:
            pass

        print(f"[kirim] {pertanyaan}")
        await ws.send(json.dumps({"t": "send_text", "text": pertanyaan}))

        batas = asyncio.get_running_loop().time() + 45
        jawaban: list[str] = []
        while asyncio.get_running_loop().time() < batas:
            try:
                mentah = await asyncio.wait_for(
                    ws.recv(), timeout=batas - asyncio.get_running_loop().time()
                )
            except asyncio.TimeoutError:
                break
            try:
                pesan = json.loads(mentah)
            except Exception:
                continue
            jenis = pesan.get("t")
            if jenis == "chat":
                peran = pesan.get("role")
                teks = (pesan.get("text") or "").strip()
                if not teks:
                    continue
                if peran == "assistant":
                    # Lewati gema STT: teks yang sama persis dengan pertanyaan.
                    if teks.lower() == pertanyaan.strip().lower():
                        print(f"[gema STT] {teks}")
                        continue
                    jawaban.append(teks)
                    print(f"[jawaban] {teks}")
                else:
                    print(f"[pengguna] {teks}")
            elif jenis == "status":
                print(f"[status] {pesan.get('status')} (connected={pesan.get('connected')})")
            elif jenis == "emotion":
                print(f"[emosi] {pesan.get('emotion')}")
            elif jenis == "notice":
                print(f"[catatan] {pesan.get('text')}")

        if not jawaban:
            print("[hasil] TIDAK ADA JAWABAN DARI MODEL")
            return 1

        gabung = " ".join(jawaban)
        han = sum(1 for c in gabung if "\u4e00" <= c <= "\u9fff")
        print()
        print(f"[hasil] panjang jawaban: {len(gabung)} karakter")
        print(f"[hasil] aksara Mandarin: {han}")
        print("[hasil] " + ("JAWABAN BERBAHASA INDONESIA" if han == 0 else "MASIH ADA AKSARA MANDARIN"))
        return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
