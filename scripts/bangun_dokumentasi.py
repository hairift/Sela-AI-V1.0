#!/usr/bin/env python3
"""Bangun situs dokumentasi SELA AI dari berkas Markdown di folder docs/.

Menghasilkan situs statis (HTML + CSS) yang siap dipublikasikan ke GitHub Pages.
Tidak memerlukan Node.js maupun generator situs pihak ketiga - cukup paket
`markdown` yang kecil dan murni Python.

Pemakaian:
    python scripts/bangun_dokumentasi.py            # keluaran ke _site/
    python scripts/bangun_dokumentasi.py --keluaran build_docs
"""

from __future__ import annotations

import argparse
import html
import re
import shutil
import sys
from pathlib import Path

try:
    import markdown
except ImportError:
    print(
        "Paket 'markdown' belum terpasang.\n"
        "Pasang dengan:  pip install markdown",
        file=sys.stderr,
    )
    raise SystemExit(1)

AKAR = Path(__file__).resolve().parent.parent

# Urutan tampil di sidebar: berkas pertama adalah halaman depan.
URUTAN = [
    "README.md",
    "docs/INSTALASI.md",
    "docs/BUILD.md",
    "docs/PERBAIKAN.md",
    "docs/ARSITEKTUR.md",
    "docs/PENGUJIAN.md",
    "LICENSE",
    "NOTICE",
]

JUDUL_SITUS = "SELA AI — Dokumentasi"
SUBTITUL = "Asisten kampus UCIC berbasis suara"

GAYA = """
:root {
  --biru: #3a5ff0;
  --biru-terang: #5a7fff;
  --teks: #1f2937;
  --teks-lembut: #6b7280;
  --garis: #e5e7eb;
  --latar: #f8faff;
  --kartu: #ffffff;
  --kode: #f3f4f6;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  font-family: Inter, -apple-system, "Segoe UI", Roboto, sans-serif;
  color: var(--teks);
  background: var(--latar);
  line-height: 1.7;
}
.kerangka { display: flex; min-height: 100vh; }
.samping {
  width: 290px; flex: 0 0 290px;
  background: var(--kartu);
  border-right: 1px solid var(--garis);
  padding: 26px 18px;
  position: sticky; top: 0; height: 100vh; overflow-y: auto;
}
.merek { display: block; margin-bottom: 4px; }
.merek b {
  font-size: 22px; letter-spacing: .32em; color: var(--teks);
  display: block; margin-bottom: 2px;
}
.merek span { font-size: 12px; color: var(--teks-lembut); }
.samping nav { margin-top: 22px; display: flex; flex-direction: column; gap: 2px; }
.samping nav a {
  display: block; padding: 9px 12px; border-radius: 10px;
  color: var(--teks-lembut); text-decoration: none; font-size: 14px;
}
.samping nav a:hover { background: var(--latar); color: var(--teks); }
.samping nav a.aktif {
  background: #eef2ff; color: var(--biru); font-weight: 600;
}
.utama { flex: 1; min-width: 0; padding: 44px 52px 90px; }
.isi { max-width: 900px; margin: 0 auto; }
h1, h2, h3, h4 { line-height: 1.3; color: var(--teks); }
h1 { font-size: 30px; margin: 0 0 18px; }
h2 {
  font-size: 21px; margin: 40px 0 14px; padding-bottom: 8px;
  border-bottom: 1px solid var(--garis);
}
h3 { font-size: 17px; margin: 28px 0 10px; }
p { margin: 12px 0; }
a { color: var(--biru); }
code {
  background: var(--kode); padding: 2px 6px; border-radius: 6px;
  font-size: .88em; font-family: "Cascadia Code", Consolas, monospace;
}
pre {
  background: #0f172a; color: #e2e8f0; padding: 16px 18px;
  border-radius: 12px; overflow-x: auto; font-size: 13px; line-height: 1.6;
}
pre code { background: none; padding: 0; color: inherit; font-size: inherit; }
table {
  border-collapse: collapse; width: 100%; margin: 18px 0; font-size: 14px;
  background: var(--kartu); border-radius: 10px; overflow: hidden;
}
th, td { border: 1px solid var(--garis); padding: 9px 13px; text-align: left; }
th { background: var(--latar); font-weight: 600; }
blockquote {
  margin: 16px 0; padding: 12px 18px; border-left: 4px solid var(--biru-terang);
  background: #eef2ff; border-radius: 0 10px 10px 0; color: #374151;
}
ul, ol { padding-left: 24px; }
li { margin: 5px 0; }
img { max-width: 100%; border-radius: 12px; border: 1px solid var(--garis); }
hr { border: none; border-top: 1px solid var(--garis); margin: 34px 0; }
.kaki {
  margin-top: 60px; padding-top: 18px; border-top: 1px solid var(--garis);
  font-size: 12px; color: var(--teks-lembut);
}
@media (max-width: 860px) {
  .kerangka { flex-direction: column; }
  .samping { width: auto; flex: none; height: auto; position: static; border-right: none; border-bottom: 1px solid var(--garis); }
  .utama { padding: 26px 20px 60px; }
}
"""


def judul_dari(markdown_teks: str, cadangan: str) -> str:
    """Ambil judul H1 pertama sebagai label sidebar."""
    for baris in markdown_teks.splitlines():
        if baris.startswith("# "):
            return baris[2:].strip()
    return cadangan


def kumpulkan_berkas() -> list[tuple[Path, str]]:
    """Kumpulkan berkas dokumentasi yang ada, sesuai URUTAN."""
    hasil: list[tuple[Path, str]] = []
    for relatif in URUTAN:
        jalur = AKAR / relatif
        if jalur.is_file():
            hasil.append((jalur, relatif))
    # Tambahan: seluruh berkas docs/*.md yang belum tercantum.
    for jalur in sorted((AKAR / "docs").glob("*.md")):
        relatif = f"docs/{jalur.name}"
        if relatif not in [r for _, r in hasil]:
            hasil.append((jalur, relatif))
    return hasil


def nama_keluaran(relatif: str) -> str:
    """README.md -> index.html, docs/INSTALASI.md -> instalasi.html"""
    if relatif == "README.md":
        return "index.html"
    batang = Path(relatif).name
    if batang.lower() == "license":
        return "lisensi.html"
    if batang.lower() == "notice":
        return "notice.html"
    return re.sub(r"[^a-z0-9]+", "-", batang.lower().replace(".md", "")) + ".html"


def bangun(keluaran: Path) -> int:
    berkas = kumpulkan_berkas()
    if not berkas:
        print("Tidak ada berkas dokumentasi yang ditemukan.", file=sys.stderr)
        return 1

    if keluaran.exists():
        shutil.rmtree(keluaran)
    keluaran.mkdir(parents=True, exist_ok=True)

    # Salin hanya aset yang dipakai dokumen (tangkapan layar), bukan seluruh
    # folder assets/ yang memuat suara & emoji aplikasi.
    sumber_docs = AKAR / "docs"
    if sumber_docs.is_dir():
        tujuan_docs = keluaran / "docs"
        tujuan_docs.mkdir(parents=True, exist_ok=True)
        for item in sumber_docs.iterdir():
            if item.is_dir() and item.name == "tangkapan-layar":
                shutil.copytree(item, tujuan_docs / item.name, dirs_exist_ok=True)

    md = markdown.Markdown(
        extensions=["extra", "toc", "sane_lists", "attr_list"],
        extension_configs={"toc": {"permalink": False}},
    )

    halaman: list[tuple[str, str, str]] = []  # (nama keluaran, label, judul)
    for jalur, relatif in berkas:
        teks = jalur.read_text(encoding="utf-8")
        nama = nama_keluaran(relatif)
        label = judul_dari(teks, relatif)
        # Ringkas label sidebar agar tidak terlalu panjang.
        label = label.split("—")[0].split("(")[0].strip()[:42]
        halaman.append((nama, label, relatif))

    for nama, _, relatif in halaman:
        teks = (AKAR / relatif).read_text(encoding="utf-8")
        md.reset()
        isi_html = md.convert(teks)

        # Susun menu sidebar (di luar f-string agar tidak memakai backslash).
        baris_menu = []
        for n, l, _ in halaman:
            kelas = ' class="aktif"' if n == nama else ""
            baris_menu.append(
                f'<a href="{n}"{kelas}>{html.escape(l)}</a>'
            )
        menu = "\n".join(baris_menu)

        dokumen = f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(SUBTITUL)} — {html.escape(JUDUL_SITUS)}</title>
<style>{GAYA}</style>
</head>
<body>
<div class="kerangka">
  <aside class="samping">
    <a class="merek" href="index.html"><b>SELA</b><span>{html.escape(SUBTITUL)}</span></a>
    <nav>
{menu}
    </nav>
  </aside>
  <main class="utama">
    <article class="isi">
{isi_html}
      <div class="kaki">
        SELA AI &middot; Universitas Catur Insan Cendekia (UCIC) &middot;
        Perangkat lunak kepemilikan &mdash; lihat halaman Lisensi.
      </div>
    </article>
  </main>
</div>
</body>
</html>
"""
        (keluaran / nama).write_text(dokumen, encoding="utf-8")

    # Tanda agar GitHub Pages tidak memproses dengan Jekyll.
    (keluaran / ".nojekyll").write_text("", encoding="utf-8")

    print(f"Situs dokumentasi dibangun: {keluaran}")
    print(f"Halaman: {len(halaman)}")
    for nama, label, _ in halaman:
        print(f"  - {nama:22} {label}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Bangun situs dokumentasi SELA AI")
    p.add_argument(
        "--keluaran",
        default="_site",
        help="Folder keluaran (default: _site)",
    )
    arg = p.parse_args()
    return bangun((AKAR / arg.keluaran).resolve())


if __name__ == "__main__":
    raise SystemExit(main())
