"""Pengujian alur aktivasi untuk mode ``web``.

Pengguna baru harus bisa melihat kode aktivasi tanpa terminal: aplikasi hasil
paket berjalan ``console=False``, jadi kode tidak boleh hanya dicetak ke stdout.
"""

import asyncio
import os

import pytest

os.environ.setdefault("SELA_NO_WINDOW", "1")

from src.activation.factory import create_activation_ui  # noqa: E402
from src.ui.web.activation import WebActivation, _cari_port  # noqa: E402


class _LayananPalsu:
    """ActivationService tiruan yang mencatat pemanggilan."""

    def __init__(self, kode="123456", sukses=True):
        self.kode = kode
        self.sukses = sukses
        self.dipanggil = False

    def get_activation_data(self):
        return {"code": self.kode, "challenge": "c", "message": "Masukkan kode"}

    def get_serial_number(self):
        return "SN-001"

    def get_mac_address(self):
        return "AA:BB:CC:DD:EE:FF"

    def get_activation_status(self):
        return {"local_activated": False, "server_activated": False, "status_consistent": True}

    async def activate(self, data=None):
        self.dipanggil = True
        await asyncio.sleep(0.05)
        return self.sukses


def _buat(sukses=True):
    return WebActivation(_LayananPalsu(sukses=sukses), {"need_activation_ui": True})


def test_factory_mengarahkan_web_ke_web_activation():
    ui = create_activation_ui("web", _LayananPalsu(), {"need_activation_ui": True})
    assert isinstance(ui, WebActivation)


def test_factory_cli_tetap_cli():
    from src.ui.cli.activation import CliActivation

    ui = create_activation_ui("cli", _LayananPalsu(), {"need_activation_ui": True})
    assert isinstance(ui, CliActivation)


def test_port_kandidat_masuk_akal():
    port = _cari_port()
    assert port == 0 or 8000 < port < 70000


def test_halaman_memuat_kode_dan_langkah():
    ui = _buat()
    ui._kode = "987654"
    resp = asyncio.run(ui._halaman(None))
    assert resp.status == 200
    assert "text/html" in resp.content_type
    body = resp.text
    assert "987654" in body
    assert "xiaozhi.me" in body
    assert "Kode aktivasi" in body


def test_status_json_awal_menunggu():
    ui = _buat()
    ui._kode = "123456"
    resp = asyncio.run(ui._status_json(None))
    assert resp.status == 200
    assert "no-store" in resp.headers.get("Cache-Control", "")
    data = __import__("json").loads(resp.text)
    assert data["status"] == "menunggu"
    assert data["kode"] == "123456"


def test_run_menyalakan_server_lalu_selesai():
    """Server benar-benar hidup saat menunggu, dan mati setelah selesai."""

    async def skenario():
        ui = _buat(sukses=True)
        # Percepat jeda tampil hasil supaya uji tidak lambat.
        import src.ui.web.activation as mod

        asli = mod._JEDA_TAMPIL_SUKSES
        mod._JEDA_TAMPIL_SUKSES = 0
        try:
            tugas = asyncio.create_task(ui.run())
            # Tunggu server siap.
            for _ in range(100):
                if ui._port:
                    break
                await asyncio.sleep(0.02)

            assert ui._port, "server aktivasi tidak pernah menyala"
            url = ui.url
            assert url.startswith("http://127.0.0.1:")

            # Server benar-benar melayani permintaan.
            from aiohttp import ClientSession

            async with ClientSession() as sesi:
                async with sesi.get(f"http://127.0.0.1:{ui._port}/status") as r:
                    assert r.status == 200
                    isi = await r.json()
                    assert isi["kode"] == "123456"

            hasil = await tugas
            assert hasil is True
            assert ui._runner is None, "server tidak dimatikan setelah aktivasi"
        finally:
            mod._JEDA_TAMPIL_SUKSES = asli

    asyncio.run(skenario())


def test_run_mengembalikan_false_saat_gagal():
    async def skenario():
        import src.ui.web.activation as mod

        asli = mod._JEDA_TAMPIL_GAGAL
        mod._JEDA_TAMPIL_GAGAL = 0
        try:
            ui = _buat(sukses=False)
            hasil = await ui.run()
            assert hasil is False
            assert ui._status == "gagal"
            assert ui._runner is None
        finally:
            mod._JEDA_TAMPIL_GAGAL = asli

    asyncio.run(skenario())


def test_run_langsung_true_bila_tidak_perlu_aktivasi():
    ui = WebActivation(_LayananPalsu(), {"need_activation_ui": False})
    assert asyncio.run(ui.run()) is True


def test_tanpa_data_aktivasi_tidak_membuka_server():
    ui = WebActivation(_LayananPalsu(), {"need_activation_ui": True})
    ui._service.get_activation_data = lambda: None
    assert asyncio.run(ui.run()) is False
    assert ui._runner is None


def test_tombol_lewati_membiarkan_aplikasi_dibuka():
    """Pengguna yang belum siap mendaftar TIDAK boleh terkunci.

    ``start_app`` keluar dengan kode 1 bila aktivasi gagal, jadi tanpa jalan
    keluar ini perangkat yang belum terdaftar membuat aplikasi tidak bisa
    dibuka sama sekali. Tombol "Lewati dulu" harus membuat ``run()`` mengembalikan
    True dan meneruskan aplikasi.
    """

    class _LayananMenggantung:
        """Aktivasi yang tidak pernah selesai - meniru menunggu kode."""

        def __init__(self):
            self.dibatalkan = False

        def get_activation_data(self):
            return {"code": "112233", "challenge": "c", "message": "Masukkan kode"}

        def get_serial_number(self):
            return "SN-001"

        def get_mac_address(self):
            return "AA:BB:CC:DD:EE:FF"

        def get_activation_status(self):
            return {
                "local_activated": False,
                "server_activated": False,
                "status_consistent": True,
            }

        async def activate(self, data=None):
            try:
                await asyncio.sleep(300)
            except asyncio.CancelledError:
                self.dibatalkan = True
                raise
            return False

    async def skenario():
        import src.ui.web.activation as mod

        asli = mod._JEDA_TAMPIL_SUKSES
        mod._JEDA_TAMPIL_SUKSES = 0
        try:
            layanan = _LayananMenggantung()
            ui = WebActivation(layanan, {"need_activation_ui": True})
            tugas = asyncio.create_task(ui.run())

            for _ in range(200):
                if ui._port:
                    break
                await asyncio.sleep(0.02)
            assert ui._port, "server aktivasi tidak pernah menyala"

            from aiohttp import ClientSession

            async with ClientSession() as sesi:
                async with sesi.post(
                    f"http://127.0.0.1:{ui._port}/lewati"
                ) as r:
                    assert r.status == 200
                    assert (await r.json())["ok"] is True

            hasil = await asyncio.wait_for(tugas, timeout=10)
            assert hasil is True, "melewati aktivasi harus meneruskan aplikasi"
            assert ui._status == "dilewati"
            assert layanan.dibatalkan, "penantian aktivasi tidak dihentikan"
            assert ui._runner is None, "server aktivasi tidak dimatikan"
        finally:
            mod._JEDA_TAMPIL_SUKSES = asli

    asyncio.run(skenario())


def test_halaman_aktivasi_punya_tombol_lewati():
    """Tombolnya harus benar-benar ada di halaman, bukan hanya di backend."""
    ui = _buat()
    ui._kode = "445566"
    resp = asyncio.run(ui._halaman(None))
    body = resp.text
    assert "Lewati dulu" in body
    assert "/lewati" in body or "'lewati'" in body
    assert "Perangkat &amp; Aktivasi" in body
