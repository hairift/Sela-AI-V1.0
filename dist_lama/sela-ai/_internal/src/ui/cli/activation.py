"""Alur aktivasi perangkat untuk mode CLI.

Dipakai juga oleh mode `web`, karena tahap aktivasi berjalan sebelum
antarmuka web dibuka. Seluruh teks di sini berbahasa Indonesia.
"""

from datetime import datetime

from src.constants.system import SystemConstants
from src.logging import get_logger
from src.ui.shared.activation import BaseActivation

logger = get_logger()


class CliActivation(BaseActivation):
    """Penangan aktivasi perangkat untuk mode CLI.

    Mewarisi BaseActivation; hanya menimpa cara menampilkan ke terminal.
    """

    def __init__(self, activation_service, init_result: dict):
        super().__init__(activation_service, init_result)

    async def run(self) -> bool:
        self._print_header()

        if not self.needs_activation():
            self._log("Perangkat sudah aktif, tidak perlu tindakan lanjutan")
            self._print_success()
            return True

        self._print_device_info()
        try:
            return await self._core_activate()
        except KeyboardInterrupt:
            self._log("\nAktivasi dibatalkan oleh pengguna")
            return False

    # ---- Metode tampilan BaseActivation ----

    def _show_code(self, data: dict) -> None:
        self._print_activation_info(data)

    def _show_result(self, success: bool) -> None:
        if success:
            self._print_success()
        else:
            self._print_failure()

    def _show_error(self, msg: str) -> None:
        self._log(msg)

    # ---- Pembantu tampilan terminal ----

    def _print_header(self):
        print("\n" + "=" * 60)
        print(f"{SystemConstants.APP_DISPLAY_NAME} - Aktivasi Perangkat")
        print("=" * 60)

    def _print_device_info(self):
        """Tampilkan informasi perangkat."""
        serial = self._service.get_serial_number() or "--"
        mac = self._service.get_mac_address() or "--"
        status = self._service.get_activation_status()

        print("\nInformasi perangkat:")
        print(f"  Nomor seri: {serial}")
        print(f"  Alamat MAC: {mac}")

        local = status.get("local_activated", False)
        server = status.get("server_activated", False)
        consistent = status.get("status_consistent", True)

        if not consistent:
            status_text = (
                "Perlu aktivasi ulang" if local and not server else "Sudah diperbaiki otomatis"
            )
        else:
            status_text = "Sudah aktif" if local else "Belum aktif"

        print(f"  Status: {status_text}")

    def _print_activation_info(self, data: dict):
        """Tampilkan informasi aktivasi beserta kode."""
        code = data.get("code", "------")
        message = data.get("message", "Silakan kunjungi xiaozhi.me dan masukkan kode aktivasi")

        print("\n" + "-" * 60)
        print("INFORMASI AKTIVASI")
        print("-" * 60)
        print(f"Kode aktivasi: {' '.join(code)}")
        print(f"Keterangan   : {message}")
        print("-" * 60)
        print("\nLangkah aktivasi:")
        print("  1. Buka peramban dan kunjungi xiaozhi.me")
        print("  2. Masuk ke akun Anda")
        print("  3. Pilih menu tambah perangkat")
        print(f"  4. Masukkan kode aktivasi: {code}")
        print("  5. Konfirmasi penambahan perangkat")
        print("\nKode juga sudah disalin ke papan klip dan dibacakan lewat suara.")

    def _print_success(self):
        print("\n" + "=" * 60)
        print("AKTIVASI PERANGKAT BERHASIL")
        print("=" * 60)
        print("Perangkat sudah ditambahkan ke akun Anda")
        print(f"Sedang menjalankan {SystemConstants.APP_DISPLAY_NAME}...")
        print("=" * 60 + "\n")

    def _print_failure(self):
        print("\n" + "=" * 60)
        print("AKTIVASI PERANGKAT GAGAL")
        print("=" * 60)
        print("Kemungkinan penyebab:")
        print("  - Koneksi jaringan tidak stabil")
        print("  - Kode aktivasi salah atau sudah kedaluwarsa")
        print("  - Server sedang tidak tersedia")
        print("\nCara mengatasi:")
        print("  - Periksa koneksi jaringan")
        print("  - Jalankan ulang aplikasi untuk mendapat kode baru")
        print("  - Pastikan kode aktivasi dimasukkan dengan benar")
        print("  - Periksa lingkungan: python main.py --doctor")
        print("=" * 60 + "\n")

    def _log(self, message: str):
        """Cetak log dengan stempel waktu."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
        logger.info(message)
