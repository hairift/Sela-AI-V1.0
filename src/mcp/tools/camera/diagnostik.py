"""Diagnostik kamera untuk halaman pengaturan.

Setara dengan CameraTab pada py-xiaozhi (versi QML): memilih kamera dan
mengujinya. Dipakai oleh server antarmuka web lewat /api/camera.

Semua fungsi di sini bersifat *best-effort*: bila OpenCV atau kamera tidak
tersedia (mis. di server tanpa perangkat), fungsi mengembalikan hasil berisi
keterangan, bukan melempar pengecualian - supaya halaman pengaturan tetap
bisa dibuka.
"""

from __future__ import annotations

from src.logging import get_logger

logger = get_logger()


def _nama_ramah(nama: str, index, key: str) -> str:
    """Nama kamera yang enak dibaca dan berbahasa Indonesia.

    OpenCV/OS kadang memberi nama generik beraksara Han (mis. "摄像头 0").
    Antarmuka SELA hanya berbahasa Indonesia, jadi nama seperti itu diganti
    menjadi "Kamera <index>".
    """
    teks = (nama or "").strip()
    if not teks:
        return f"Kamera {index if index is not None else key}"
    if any("\u4e00" <= ch <= "\u9fff" for ch in teks):
        return f"Kamera {index if index is not None else key}"
    return teks


def daftar_kamera() -> list[dict]:
    """Daftar kamera yang terdeteksi.

    Returns:
        Daftar dict {key, name, kind, index, path}. Kosong bila tidak ada
        kamera atau OpenCV tidak terpasang.
    """
    try:
        from src.mcp.tools.camera.capture_backend import list_camera_devices

        perangkat = list_camera_devices()
    except Exception as e:
        logger.debug(f"Daftar kamera tidak tersedia: {e}")
        return []

    hasil: list[dict] = []
    for d in perangkat:
        try:
            kunci = getattr(d, "key", "")
            indeks = getattr(d, "index", None)
            hasil.append(
                {
                    "key": kunci,
                    "name": _nama_ramah(getattr(d, "name", ""), indeks, kunci),
                    "kind": getattr(d, "kind", ""),
                    "index": indeks,
                    "path": getattr(d, "path", None),
                }
            )
        except Exception:
            continue
    return hasil


def _pesan_bersih(detail: str, cadangan: str) -> str:
    """Pesan kesalahan yang aman ditampilkan ke pengguna.

    Pengecualian internal bisa memuat teks Mandarin (mis. pesan dari
    ConfigManager atau OpenCV). Antarmuka SELA hanya berbahasa Indonesia, jadi
    teks seperti itu diganti dengan pesan cadangan; detail aslinya tetap
    dicatat ke log untuk penelusuran.
    """
    teks = str(detail or "").strip()
    if not teks:
        return cadangan
    if any("\u4e00" <= ch <= "\u9fff" for ch in teks):
        logger.debug(f"Detail internal (disembunyikan dari pengguna): {teks}")
        return cadangan
    return teks


def uji_kamera() -> dict:
    """Uji kamera: buka, ambil satu bingkai, laporkan ukurannya.

    Returns:
        dict dengan kunci ``ok`` dan pesan berbahasa Indonesia yang bisa
        langsung ditampilkan di halaman pengaturan.
    """
    try:
        from src.mcp.tools.camera.capture_backend import capture_jpeg
    except Exception as e:
        return {
            "ok": False,
            "error": _pesan_bersih(
                e,
                "Modul kamera tidak tersedia. Pasang 'opencv-python' bila ingin "
                "memakai kamera.",
            ),
        }

    try:
        bingkai = capture_jpeg()
    except Exception as e:
        return {
            "ok": False,
            "error": _pesan_bersih(e, "Kamera gagal dibuka. Periksa perangkat kamera."),
        }

    if not bingkai:
        return {
            "ok": False,
            "error": (
                "Kamera tidak menghasilkan gambar. Periksa: (1) kamera terpasang "
                "dan tidak dipakai aplikasi lain; (2) indeks kamera sudah benar; "
                "(3) izin akses kamera diberikan. Di Linux periksa '/dev/video*' "
                "dan keanggotaan grup 'video'."
            ),
        }

    return {
        "ok": True,
        "ukuran": len(bingkai),
        "pesan": f"Kamera berfungsi. Satu bingkai berhasil diambil ({len(bingkai)} bita).",
    }
