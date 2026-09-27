"""Uji pemilihan identitas perangkat (MAC).

Identitas perangkat dipakai untuk meminta kode aktivasi ke server xiaozhi.
Sebelumnya diambil dari adaptor jaringan PERTAMA yang bukan loopback. Di
komputer yang memasang VirtualBox/VMware/Hyper-V/WSL, adaptor pertama justru
adaptor VIRTUAL dengan MAC ``0a:00:27:00:00:10`` - nilai yang SAMA di semua
komputer yang memasang perangkat lunak itu. Akibatnya:

  * perangkat baru dianggap "sudah terdaftar" oleh server, sehingga halaman
    kode aktivasi tidak pernah muncul (keluhan pengguna), dan
  * banyak pengguna berbagi satu identitas perangkat.

Uji ini mengunci janji bahwa adaptor fisik yang dipilih, bukan adaptor virtual.
"""

from __future__ import annotations

import socket
import types

import pytest

from src.activation.identity import DeviceIdentity
from src.utils.config_manager import initialize_config, reset_config


@pytest.fixture(scope="module", autouse=True)
def _konfigurasi() -> None:
    reset_config()
    initialize_config()


def _snic(family, address):
    return types.SimpleNamespace(family=family, address=address)


def _tiru_jaringan(monkeypatch, antarmuka: dict[str, list], aktif: set[str] | None = None):
    """Pasang daftar adaptor jaringan tiruan."""
    monkeypatch.setattr(
        "src.activation.identity.psutil.net_if_addrs", lambda: antarmuka, raising=True
    )
    monkeypatch.setattr(
        "src.activation.identity.psutil.net_if_stats",
        lambda: {
            nama: types.SimpleNamespace(isup=(aktif is None or nama in aktif))
            for nama in antarmuka
        },
        raising=True,
    )


def test_mac_virtual_mengenali_adaptor_buatan():
    d = DeviceIdentity()
    for mac in (
        "0a:00:27:00:00:10",  # VirtualBox host-only
        "08:00:27:1a:2b:3c",  # VirtualBox NAT
        "00:50:56:c0:00:08",  # VMware
        "00:15:5d:00:1b:2c",  # Hyper-V / WSL
        "52:54:00:12:34:56",  # QEMU
        "02:42:ac:11:00:02",  # Docker
    ):
        assert d._mac_virtual(mac), f"{mac} seharusnya dikenali sebagai adaptor virtual"
    for mac in ("b0:a4:60:52:a1:84", "00:1a:2b:3c:4d:5e", "f4:8c:50:11:22:33"):
        assert not d._mac_virtual(mac), f"{mac} adalah adaptor fisik, bukan virtual"


def test_adaptor_virtual_dilewati(monkeypatch):
    """Adaptor VirtualBox tidak boleh dipakai sebagai identitas perangkat."""
    _tiru_jaringan(
        monkeypatch,
        {
            "lo": [_snic(psutil_family_link(), "00:00:00:00:00:00")],
            "Ethernet": [_snic(psutil_family_link(), "0A-00-27-00-00-10")],
            "Wi-Fi": [
                _snic(socket.AF_INET, "192.168.1.20"),
                _snic(psutil_family_link(), "B0-A4-60-52-A1-84"),
            ],
        },
        aktif={"Wi-Fi", "Ethernet"},
    )
    d = DeviceIdentity()
    assert d._get_primary_mac_address() == "b0:a4:60:52:a1:84"


def test_adaptor_fisik_dengan_ip_diutamakan(monkeypatch):
    """Adaptor fisik yang membawa IPv4 nyata menang atas yang hanya link-local."""
    _tiru_jaringan(
        monkeypatch,
        {
            "Ethernet 2": [
                _snic(socket.AF_INET, "169.254.10.5"),
                _snic(psutil_family_link(), "aa:bb:cc:dd:ee:01"),
            ],
            "Wi-Fi": [
                _snic(socket.AF_INET, "10.0.0.7"),
                _snic(psutil_family_link(), "aa:bb:cc:dd:ee:02"),
            ],
        },
        aktif={"Wi-Fi", "Ethernet 2"},
    )
    d = DeviceIdentity()
    assert d._get_primary_mac_address() == "aa:bb:cc:dd:ee:02"


def test_adaptor_mati_dilewati(monkeypatch):
    """Adaptor yang tidak aktif jangan dipakai selama ada yang aktif."""
    _tiru_jaringan(
        monkeypatch,
        {
            "Ethernet": [_snic(psutil_family_link(), "aa:bb:cc:dd:ee:01")],
            "Wi-Fi": [_snic(psutil_family_link(), "aa:bb:cc:dd:ee:02")],
        },
        aktif={"Wi-Fi"},
    )
    d = DeviceIdentity()
    assert d._get_primary_mac_address() == "aa:bb:cc:dd:ee:02"


def test_hanya_ada_adaptor_virtual_tetap_punya_identitas(monkeypatch):
    """Di dalam mesin virtual, perangkat tetap harus punya identitas."""
    _tiru_jaringan(
        monkeypatch,
        {"Ethernet": [_snic(psutil_family_link(), "0A-00-27-00-00-10")]},
        aktif={"Ethernet"},
    )
    d = DeviceIdentity()
    assert d._get_primary_mac_address() == "0a:00:27:00:00:10"


def test_efuse_lama_tidak_diubah(monkeypatch, tmp_path):
    """Pemasangan yang sudah ada memakai identitas lamanya - tidak ada aktivasi ulang.

    Perbaikan pemilihan MAC hanya berlaku untuk perangkat BARU. Berkas
    efuse.json yang sudah ada tetap dipertahankan apa adanya.
    """
    monkeypatch.setenv("XIAOZHI_DATA_DIR", str(tmp_path))
    d = DeviceIdentity()
    d.init_paths()
    # Tulis efuse lama seolah dari pemasangan sebelumnya.
    d._save_efuse_data(
        {
            "mac_address": "0a:00:27:00:00:10",
            "serial_number": "SN-LAMA-0a0027000010",
            "hmac_key": "kunci-lama",
            "activation_status": True,
        }
    )
    d2 = DeviceIdentity()
    d2.init_paths()
    d2.ensure_efuse_file()
    data = d2.load_efuse_data()
    assert data["mac_address"] == "0a:00:27:00:00:10"
    assert data["serial_number"] == "SN-LAMA-0a0027000010"
    assert data["activation_status"] is True


def psutil_family_link():
    """Keluarga alamat MAC menurut psutil (AF_LINK / AF_PACKET)."""
    import psutil

    return psutil.AF_LINK
