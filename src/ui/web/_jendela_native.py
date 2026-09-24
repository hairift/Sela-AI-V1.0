"""Jendela native pywebview untuk SELA, dijalankan sebagai proses terpisah.

Dijalankan oleh ``launcher._open_pywebview``. Tugasnya sederhana:

1. Buka jendela pywebview.
2. Begitu jendela benar-benar tampil, tulis berkas penanda "siap" yang
   ditunggu proses induk.
3. Bila pembuatan jendela gagal (mis. runtime WebView2 rusak), tulis berkas
   penanda "gagal" lalu keluar dengan kode galat.

Dipisah ke proses tersendiri supaya kegagalan WebView2 — yang membuat
``webview.start()`` menggantung dengan jendela kosong — tidak ikut
menggantung aplikasi utama. Proses induk cukup menunggu penanda.
"""

from __future__ import annotations

import os
import sys


def main() -> int:
    if len(sys.argv) < 4:
        print("pemakaian: _jendela_native.py <url> <judul> <berkas-penanda> [lebar] [tinggi]")
        return 2

    url = sys.argv[1]
    judul = sys.argv[2]
    penanda = sys.argv[3]
    lebar = int(sys.argv[4]) if len(sys.argv) > 4 else 1280
    tinggi = int(sys.argv[5]) if len(sys.argv) > 5 else 800

    def tulis(isi: str) -> None:
        try:
            with open(penanda, "w", encoding="utf-8") as f:
                f.write(isi)
        except Exception:
            pass

    try:
        import webview  # type: ignore
    except Exception as e:  # pragma: no cover - bergantung lingkungan
        tulis(f"gagal:impor:{e}")
        return 3

    try:
        jendela = webview.create_window(
            judul, url, width=lebar, height=tinggi, min_size=(900, 600)
        )
    except Exception as e:  # pragma: no cover
        tulis(f"gagal:buat:{e}")
        return 4

    # Penanda "siap" hanya ditulis setelah HALAMAN SELESAI DIMUAT, bukan sekadar
    # setelah loop GUI hidup. Bila runtime WebView2 rusak, jendela tetap terbuka
    # tetapi kosong dan peristiwa ini tidak pernah terjadi — itulah yang dulu
    # membuat pengguna menatap jendela putih.
    def saat_selesai_muat() -> None:
        tulis("siap")

    try:
        jendela.events.loaded += saat_selesai_muat
    except Exception:
        pass

    try:
        webview.start()
    except Exception as e:  # pragma: no cover
        tulis(f"gagal:mulai:{e}")
        return 5
    finally:
        # Jendela ditutup pengguna; pastikan penanda tidak tertinggal.
        try:
            os.remove(penanda)
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
