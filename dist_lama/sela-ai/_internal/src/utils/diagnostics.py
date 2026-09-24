"""自检工具 SELA AI (`--doctor`).

Memeriksa satu per satu titik yang paling sering membuat aplikasi gagal di
Windows ("tidak mau terbuka") dan Linux ("terbuka tapi suara tidak merespons"),
lalu mencetak laporan yang bisa langsung dibaca pengguna.

Pemakaian::

    python main.py --doctor

Semua pemeriksaan dibuat *best-effort*: satu kegagalan tidak menghentikan
pemeriksaan berikutnya, supaya laporan tetap lengkap.
"""

from __future__ import annotations

import importlib
import os
import platform
import socket
import sys
from pathlib import Path
from typing import Callable, Optional

OK = "[ OK ]"
WARN = "[WARN]"
FAIL = "[GAGAL]"

_results: list[tuple[str, str, str]] = []


def _record(status: str, name: str, detail: str = "") -> None:
    _results.append((status, name, detail))
    line = f"{status} {name}"
    if detail:
        line += f"\n        {detail}"
    print(line, flush=True)


def _check(name: str, fn: Callable[[], str]) -> None:
    """Jalankan satu pemeriksaan; exception apa pun jadi WARN, bukan crash."""
    try:
        detail = fn() or ""
        _record(OK, name, detail)
    except AssertionError as e:
        _record(FAIL, name, str(e))
    except Exception as e:  # pragma: no cover - 诊断工具本身不能崩
        _record(WARN, name, f"{type(e).__name__}: {e}")


# ----------------------------------------------------------------------
# Pemeriksaan
# ----------------------------------------------------------------------
def _check_python() -> str:
    v = sys.version_info
    if v < (3, 10):
        raise AssertionError(
            f"Python {v.major}.{v.minor} terlalu tua - butuh 3.10-3.12"
        )
    if v >= (3, 13):
        return (
            f"Python {v.major}.{v.minor}.{v.micro} - di atas 3.12 belum resmi "
            "didukung sherpa-onnx; bila ada error, pakai Python 3.11/3.12"
        )
    return f"Python {v.major}.{v.minor}.{v.micro}"


def _check_platform() -> str:
    return (
        f"{platform.system()} {platform.release()} | {platform.machine()} | "
        f"frozen={getattr(sys, 'frozen', False)}"
    )


def _check_packages() -> str:
    wajib = ["numpy", "sounddevice", "aiohttp", "websockets", "requests", "opuslib"]
    opsional = ["sherpa_onnx", "cv2", "PySide6", "qasync", "mutagen", "psutil"]
    hilang = []
    for mod in wajib:
        try:
            importlib.import_module(mod)
        except Exception:
            hilang.append(mod)
    if hilang:
        raise AssertionError(
            "Paket wajib belum terpasang: " + ", ".join(hilang) +
            "  -> jalankan: pip install -r requirements.txt"
        )
    opt_hilang = []
    for mod in opsional:
        try:
            importlib.import_module(mod)
        except Exception:
            opt_hilang.append(mod)
    if opt_hilang:
        return f"wajib lengkap; opsional belum ada: {', '.join(opt_hilang)}"
    return "semua paket inti & opsional tersedia"


def _check_opus() -> str:
    """Opus wajib untuk suara. Kegagalan di sini = suara tidak jalan."""
    from src.utils.opus_loader import setup_opus
    from src.utils.resource_finder import get_lib_path

    path = get_lib_path("libopus")
    if path is None:
        raise AssertionError(
            "libopus tidak ditemukan di libs/libopus/<platform>/<arch>/. "
            "Linux: sudo apt install libopus0  |  macOS: brew install opus"
        )
    if not setup_opus():
        raise AssertionError(
            f"libopus ditemukan di {path} tapi gagal dimuat (kemungkinan arsitektur "
            "tidak cocok, mis. library x64 di sistem arm64)"
        )
    return f"dimuat dari {path}"


def _check_aec() -> str:
    """AEC opsional: bila gagal, hanya gema yang berkurang kualitasnya."""
    from src.utils.resource_finder import get_lib_path

    try:
        from src.utils.config_manager import get_config

        enabled = bool(get_config().get_config("AEC_OPTIONS.ENABLED", False))
    except Exception:
        enabled = False

    path = get_lib_path("webrtc_apm")
    if path is None:
        return "AEC nonaktif / library webrtc_apm tidak ada (opsional, tidak fatal)"
    if not enabled:
        return f"library ada ({path}) tetapi AEC dimatikan di config"
    return f"AEC aktif, library: {path}"


def _check_audio_devices() -> str:
    """Titik paling sering jadi penyebab 'suara tidak merespons' di Linux."""
    try:
        import sounddevice as sd
    except Exception as e:
        raise AssertionError(f"sounddevice tidak bisa di-import: {e}")

    try:
        devices = sd.query_devices()
    except Exception as e:
        raise AssertionError(
            "PortAudio tidak bisa membaca daftar perangkat "
            f"({e}). Linux: sudo apt install libportaudio2 portaudio19-dev"
        )

    inputs = [d for d in devices if d.get("max_input_channels", 0) > 0]
    outputs = [d for d in devices if d.get("max_output_channels", 0) > 0]
    if not inputs:
        raise AssertionError(
            "Tidak ada perangkat input (mikrofon) terdeteksi -> fitur suara tidak akan merespons. "
            "Linux: pastikan user ada di grup 'audio' dan PulseAudio/PipeWire berjalan."
        )
    if not outputs:
        raise AssertionError("Tidak ada perangkat output (speaker) terdeteksi")

    try:
        default_in, default_out = sd.default.device
    except Exception:
        default_in = default_out = None

    return (
        f"{len(inputs)} input, {len(outputs)} output | default in={default_in} out={default_out}"
    )


def _check_config() -> str:
    from src.utils.config_manager import get_config
    from src.utils.resource_finder import get_user_data_dir

    cfg = get_config()
    ws = cfg.get_config("SYSTEM_OPTIONS.NETWORK.WEBSOCKET_URL", None)
    token = cfg.get_config("SYSTEM_OPTIONS.NETWORK.WEBSOCKET_ACCESS_TOKEN", None)
    device_id = cfg.get_config("SYSTEM_OPTIONS.DEVICE_ID", None)
    status = "sudah" if (ws and token) else "BELUM"
    return (
        f"data={get_user_data_dir()} | device_id={'ada' if device_id else 'kosong'} | "
        f"sesi server {status} terkonfigurasi"
    )


def _check_webui() -> str:
    from src.utils.resource_finder import get_app_root

    dist = get_app_root() / "webui" / "dist"
    index = dist / "index.html"
    if not index.is_file():
        raise AssertionError(
            f"Antarmuka web belum dibangun ({dist}). Jalankan: cd webui && npm install && npm run build"
        )
    return f"antarmuka web siap di {dist}"


def _check_network() -> str:
    host = "api.tenclass.net"
    try:
        socket.create_connection((host, 443), timeout=6).close()
    except Exception as e:
        raise AssertionError(
            f"Tidak bisa menjangkau {host}:443 ({e}). Fitur suara butuh koneksi internet "
            "ke layanan AI (kecuali server mandiri)."
        )
    return f"{host}:443 dapat dijangkau"


def _check_write_access() -> str:
    from src.utils.resource_finder import get_user_data_dir

    probe = get_user_data_dir() / ".sela-write-test"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except Exception as e:
        raise AssertionError(f"Direktori data tidak bisa ditulis: {e}")
    return f"{get_user_data_dir()} dapat ditulis"


def _check_port() -> str:
    port = int(os.environ.get("SELA_WEBUI_PORT", "8765"))
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.5)
        if s.connect_ex(("127.0.0.1", port)) == 0:
            return f"port {port} sedang terpakai (server lain berjalan?)"
        return f"port {port} bebas"


# ----------------------------------------------------------------------
def run_diagnostics() -> int:
    """Jalankan seluruh pemeriksaan. Mengembalikan exit code."""
    from src.constants.system import SystemConstants

    print("=" * 68)
    print(f"  {SystemConstants.APP_DISPLAY_NAME} - Pemeriksaan Lingkungan (--doctor)")
    print("=" * 68)

    try:
        from src.utils.config_manager import initialize_config

        initialize_config()
    except Exception as e:
        print(f"{WARN} Konfigurasi belum bisa dimuat: {e}")

    _check("Versi Python", _check_python)
    _check("Platform", _check_platform)
    _check("Hak tulis data pengguna", _check_write_access)
    # Opus harus dimuat SEBELUM memeriksa paket: `import opuslib` gagal bila
    # library Opus belum ditemukan, dan pemuatan itu memang tugas setup_opus().
    _check("Library Opus (wajib untuk suara)", _check_opus)
    _check("Paket Python", _check_packages)
    _check("AEC / webrtc_apm", _check_aec)
    _check("Perangkat audio", _check_audio_devices)
    _check("Konfigurasi & akun", _check_config)
    _check("Antarmuka web", _check_webui)
    _check("Jaringan ke layanan AI", _check_network)
    _check("Port antarmuka web", _check_port)

    gagal = [r for r in _results if r[0] == FAIL]
    warn = [r for r in _results if r[0] == WARN]

    print("-" * 68)
    print(f"Ringkasan: {len(_results)} diperiksa, {len(gagal)} gagal, {len(warn)} peringatan")
    if gagal:
        print("\nPerbaiki dulu item [GAGAL] di atas - itu penyebab fitur tidak jalan.")
        return 1
    if warn:
        print("\nTidak ada kegagalan fatal. Peringatan di atas bisa diabaikan bila fitur jalan.")
    else:
        print("\nSemua pemeriksaan lolos. Mesin AI siap dipakai.")
    return 0
