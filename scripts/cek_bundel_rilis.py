"""Periksa bundel rilis: kait uji harus mati, fitur tetap ada.

Dijalankan terhadap bundel produksi (tanpa VITE_SELA_UJI) untuk memastikan
kait uji yang dipakai scripts/cek_visualizer_subtitle.py TIDAK ikut terbit,
sementara visualizer audio dan subtitle tetap terpasang.
"""

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

CH = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]


def cari():
    for k in CH:
        if pathlib.Path(k).exists():
            return k


def pb():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


async def wsu(port):
    for _ in range(60):
        try:
            raw = urllib.request.urlopen(
                f"http://127.0.0.1:{port}/json", timeout=1
            ).read()
            for t in json.loads(raw):
                if t.get("type") == "page" and t.get("webSocketDebuggerUrl"):
                    return t["webSocketDebuggerUrl"]
        except Exception:
            pass
        await asyncio.sleep(0.5)


class C:
    def __init__(s, w):
        s.w = w
        s.i = 0

    async def k(s, m, p=None):
        s.i += 1
        c = s.i
        await s.w.send(json.dumps({"id": c, "method": m, "params": p or {}}))
        while True:
            r = json.loads(await s.w.recv())
            if r.get("id") == c:
                return r

    async def e(s, x):
        r = await s.k(
            "Runtime.evaluate",
            {"expression": x, "returnByValue": True, "awaitPromise": True},
        )
        d = r.get("result", {})
        if "exceptionDetails" in d:
            return "EXC: " + str(d["exceptionDetails"].get("text"))
        return d.get("result", {}).get("value")


async def main(url):
    ch = cari()
    port = pb()
    prof = tempfile.mkdtemp(prefix="sela-rilis-")
    proc = subprocess.Popen(
        [
            ch,
            "--headless=new",
            f"--remote-debugging-port={port}",
            f"--user-data-dir={prof}",
            "--no-first-run",
            "--disable-gpu",
            "--window-size=1280,900",
            url,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    galat = []
    try:
        w = await wsu(port)
        async with websockets.connect(w, max_size=16 * 1024 * 1024) as ws:
            c = C(ws)
            await c.k("Runtime.enable")
            await c.k("Page.enable")
            await asyncio.sleep(6.0)

            kait = {
                n: await c.e(f"typeof window.{n}")
                for n in (
                    "__selaUjiLip",
                    "__selaUjiSubtitle",
                    "__selaUjiBerhenti",
                    "__selaUjiMulaiBicara",
                )
            }
            print("kait uji:", kait)
            for n, t in kait.items():
                if t != "undefined":
                    galat.append(f"kait uji {n} ikut terbit ({t}) - bundel kotor")

            viz = await c.e(
                "!!document.querySelector('[data-visualizer-audio=\"1\"]')"
            )
            print("visualizer ada:", viz)
            if not viz:
                galat.append("visualizer tidak ada di bundel rilis")

            sub = await c.e("!!document.querySelector('[data-subtitle-ai=\"1\"]')")
            print("subtitle (idle, harus tidak tampil):", sub)

            han = await c.e(
                "(() => /[\\u4e00-\\u9fff\\u3400-\\u4dbf]/.test(document.body.innerText||''))()"
            )
            print("ada aksara Han:", han)
            if han:
                galat.append("bundel rilis memuat aksara Han")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        shutil.rmtree(prof, ignore_errors=True)

    print("")
    if galat:
        print("[HASIL] GAGAL:")
        for g in galat:
            print("  -", g)
        return 1
    print("[HASIL] LULUS - bundel rilis bersih dari kait uji, fitur terpasang.")
    return 0


asyncio.run(main(sys.argv[1]))
