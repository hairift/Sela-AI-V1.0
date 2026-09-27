"""Periksa alur aktivasi pengguna BARU (perangkat yang belum terdaftar).

Pertanyaan pengguna: "kenapa aplikasi yang baru di-download langsung bisa
mengakses AI-nya, padahal py-xiaozhi mengirim kode untuk masuk ke server
xiaozhi.me/console/agents?"

Jawabannya bergantung pada dua hal:
  1. status aktivasi LOKAL (berkas efuse.json), dan
  2. status aktivasi di SERVER (jawaban OTA).

Skrip ini menjalankan alur aktivasi yang sesungguhnya dengan direktori data
yang KOSONG - persis seperti pengguna yang baru memasang aplikasi - lalu
mencetak hasilnya. Dengan begitu bisa dibuktikan apakah halaman kode
aktivasi benar-benar muncul untuk perangkat baru, tanpa perlu menebak.

Pemakaian:
    python scripts/cek_alur_aktivasi.py            # data dir sementara
    python scripts/cek_alur_aktivasi.py --nyata    # pakai data dir pengguna
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path

# Skrip dijalankan dari mana saja; pastikan akar proyek bisa diimpor.
AKAR = Path(__file__).resolve().parent.parent
if str(AKAR) not in sys.path:
    sys.path.insert(0, str(AKAR))


async def jalankan(data_dir: str) -> int:
    os.environ["XIAOZHI_DATA_DIR"] = data_dir

    from src.activation.service import ActivationService
    from src.utils.config_manager import initialize_config, reset_config

    reset_config()
    config = initialize_config()

    print(f"Direktori data : {data_dir}")
    print(f"Berkas config  : {config.config_file if hasattr(config, 'config_file') else '?'}")
    print(f"ACTIVATION_VERSION: {config.get_config('SYSTEM_OPTIONS.NETWORK.ACTIVATION_VERSION', 'v1')}")
    print(f"OTA URL        : {config.get_config('SYSTEM_OPTIONS.NETWORK.OTA_VERSION_URL', '-')}")
    print(f"AUTHORIZATION  : {config.get_config('SYSTEM_OPTIONS.NETWORK.AUTHORIZATION_URL', '-')}")

    efuse = Path(data_dir) / "config" / "efuse.json"
    print(f"efuse.json ada : {efuse.is_file()}")
    if efuse.is_file():
        print(f"  isi          : {efuse.read_text(encoding='utf-8')[:200]}")

    # WAJIB lewat create(): di situlah _async_init() menyiapkan jalur efuse dan
    # membuat efuse.json. Konstruktor biasa (ActivationService()) tidak
    # melakukannya, sehingga perangkat tampak tanpa identitas.
    service = await ActivationService.create()
    hasil = await service.initialize()

    print("\n--- HASIL initialize() ---")
    for kunci in (
        "success",
        "need_activation_ui",
        "message",
        "local_activated",
        "server_activated",
        "status_consistent",
        "activation_version",
        "error",
    ):
        if kunci in hasil:
            print(f"  {kunci:22s} = {hasil[kunci]}")

    data = service.get_activation_data()
    print("\n--- DATA AKTIVASI (yang dikirim ke antarmuka) ---")
    if not data:
        print("  (kosong - tidak ada kode aktivasi)")
    else:
        aman = {k: v for k, v in data.items() if k not in {"challenge", "hmac_key"}}
        for k, v in aman.items():
            print(f"  {k:22s} = {v}")

    efuse_setelah = Path(data_dir) / "config" / "efuse.json"
    if efuse_setelah.is_file():
        print("\nefuse.json setelah initialize():")
        print(f"  {efuse_setelah.read_text(encoding='utf-8')[:300]}")

    print()
    if hasil.get("need_activation_ui"):
        print("KESIMPULAN: perangkat BARU -> halaman kode aktivasi MUNCUL. Sesuai harapan.")
        return 0
    print("KESIMPULAN: perangkat dianggap sudah aktif -> halaman kode DILEWATI.")
    print("            Ini benar bila perangkat sudah terdaftar di server xiaozhi.")
    return 0


if __name__ == "__main__":
    if "--nyata" in sys.argv:
        from src.utils.resource_finder import get_data_dir

        sys.exit(asyncio.run(jalankan(str(get_data_dir()))))
    with tempfile.TemporaryDirectory(prefix="sela-aktivasi-") as tmp:
        sys.exit(asyncio.run(jalankan(tmp)))
