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


@pytest.fixture
def _data_terpisah(tmp_path, monkeypatch):
    """Arahkan direktori data ke tmp_path - WAJIB untuk setiap uji tulis-berkas.

    ``get_user_data_dir`` dibungkus ``lru_cache``, jadi menyetel
    ``XIAOZHI_DATA_DIR`` saja TIDAK cukup: nilai lama sudah tersimpan di cache
    (fixture modul di atas memanggil ``initialize_config()`` lebih dulu).
    Tanpa ``cache_clear()`` uji akan menulis ke direktori data ASLI milik
    pengguna - pernah terjadi, dan sempat menyisihkan ``efuse.json`` asli.
    """
    from src.utils import resource_finder as rf

    monkeypatch.setenv("XIAOZHI_DATA_DIR", str(tmp_path))
    rf.get_user_data_dir.cache_clear()
    yield tmp_path
    rf.get_user_data_dir.cache_clear()


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


def test_efuse_lama_tidak_diubah(_data_terpisah):
    """Pemasangan yang sudah ada memakai identitas lamanya - tidak ada aktivasi ulang.

    Perbaikan pemilihan MAC hanya berlaku untuk perangkat BARU. Berkas
    efuse.json yang sudah ada tetap dipertahankan apa adanya.
    """
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


# --- Identitas tidak sah: penjelasan + pembuatan ulang ----------------------
#
# Inilah keadaan nyata yang membuat pengguna tidak pernah melihat kode
# aktivasi: efuse.json berisi MAC adaptor VirtualBox (sama di semua komputer)
# dengan ``hmac_key`` yang jelas ditulis tangan. Server xiaozhi melihat MAC itu
# sudah terdaftar, jadi tidak pernah mengirim kode - dan dasbor xiaozhi.me
# pengguna tetap kosong.


def _tulis_efuse(data: dict):
    """Tulis efuse ke direktori data SEMENTARA (lihat fixture ``_data_terpisah``)."""
    d = DeviceIdentity()
    d.init_paths()
    d._save_efuse_data(data)
    d2 = DeviceIdentity()
    d2.init_paths()
    return d2


def test_identitas_virtual_dilaporkan_mencurigakan(_data_terpisah):
    d = _tulis_efuse(
        {
            "mac_address": "0a:00:27:00:00:10",
            "serial_number": "SN-LAMA-0a0027000010",
            "hmac_key": "kunci-lama",
            "activation_status": True,
        },
    )
    alasan = d.identitas_mencurigakan()
    assert alasan, "identitas adaptor virtual harus dilaporkan"
    assert "virtual" in alasan.lower()


def test_kunci_hmac_pendek_dilaporkan(_data_terpisah):
    """Kunci HMAC pendek = tanda berkas ditulis di luar aplikasi."""
    d = _tulis_efuse(
        {
            "mac_address": "b0:a4:60:52:a1:84",
            "serial_number": "SN-ABC123-b0a46052a184",
            "hmac_key": "kunci-lama",
            "activation_status": True,
        },
    )
    assert "HMAC" in d.identitas_mencurigakan()


def test_identitas_wajar_tidak_dilaporkan(_data_terpisah):
    d = _tulis_efuse(
        {
            "mac_address": "b0:a4:60:52:a1:84",
            "serial_number": "SN-ABC123-b0a46052a184",
            "hmac_key": "0b64426cedd5d965601df6a37430550151f8a5fc290ee3c1e0d13a33c5724fb2",
            "activation_status": True,
        },
    )
    assert d.identitas_mencurigakan() == ""


def test_reset_menyisihkan_bukan_menghapus(_data_terpisah):
    """Berkas lama harus tetap ada sebagai cadangan - bukan dihapus."""
    d = _tulis_efuse(
        {
            "mac_address": "0a:00:27:00:00:10",
            "serial_number": "SN-LAMA-0a0027000010",
            "hmac_key": "kunci-lama",
            "activation_status": True,
        },
    )
    cadangan = d.reset_identity()
    assert cadangan is not None and cadangan.exists(), "cadangan tidak dibuat"
    assert "kunci-lama" in cadangan.read_text(encoding="utf-8")
    # efuse.json aktif sudah tidak ada -> identitas berikutnya dibuat dari nol.
    assert not (_data_terpisah / "config" / "efuse.json").exists()


def test_setelah_reset_identitas_dibuat_ulang_dari_adaptor_fisik(_data_terpisah, monkeypatch):
    d = _tulis_efuse(
        {
            "mac_address": "0a:00:27:00:00:10",
            "serial_number": "SN-LAMA-0a0027000010",
            "hmac_key": "kunci-lama",
            "activation_status": True,
        },
    )
    _tiru_jaringan(
        monkeypatch,
        {
            "Wi-Fi": [
                _snic(socket.AF_INET, "192.168.1.20"),
                _snic(psutil_family_link(), "B0-A4-60-52-A1-84"),
            ],
        },
        aktif={"Wi-Fi"},
    )
    d.reset_identity()

    baru = DeviceIdentity()
    baru.init_paths()
    baru.ensure_efuse_file()
    data = baru.load_efuse_data()

    assert data["mac_address"] == "b0:a4:60:52:a1:84", "MAC fisik tidak dipakai"
    assert data["mac_address"] != "0a:00:27:00:00:10", "MAC virtual masih terpakai"
    assert len(str(data["hmac_key"])) == 64, "kunci HMAC tidak dibuat ulang"
    assert data["activation_status"] is False, "perangkat baru harus belum aktif"
    assert baru.identitas_mencurigakan() == "", "identitas baru masih dianggap mencurigakan"


def test_reset_tanpa_berkas_tidak_gagal(_data_terpisah):
    d = DeviceIdentity()
    d.init_paths()
    assert d.reset_identity() is None


def test_uji_tidak_menyentuh_direktori_data_asli(_data_terpisah):
    """Penjaga: uji identitas WAJIB memakai direktori sementara.

    Tanpa ini, uji tulis-berkas bisa menyisihkan ``efuse.json`` milik pengguna
    dan membuat perangkat kehilangan identitasnya.
    """
    from src.utils.resource_finder import get_user_data_dir

    nyata = get_user_data_dir()
    assert str(nyata).startswith(str(_data_terpisah)), (
        f"uji menulis ke direktori data asli: {nyata}"
    )


# --- Permukaan web ----------------------------------------------------------


def test_rute_identitas_baru_terdaftar():
    """Antarmuka harus punya jalan meminta identitas baru.

    Tanpa rute ini, pengguna yang identitasnya tidak sah tidak punya cara
    mendapatkan kode aktivasi - persis keluhan "tidak muncul kode apa-apa".
    """
    from src.core.event_bus import EventBus
    from src.ui.web.bridge import SelaBridge
    from src.ui.web.server import SelaWebServer

    server = SelaWebServer(SelaBridge(EventBus()))
    app = server.build_app()
    jalur = {
        (r.method, r.resource.canonical)
        for r in app.router.routes()
        if r.resource is not None and hasattr(r.resource, "canonical")
    }
    assert ("POST", "/api/perangkat/identitas-baru") in jalur, (
        "rute pembuatan identitas baru tidak terdaftar"
    )
    assert ("GET", "/api/perangkat") in jalur
    assert ("POST", "/api/perangkat/periksa") in jalur
