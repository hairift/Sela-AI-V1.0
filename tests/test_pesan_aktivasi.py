"""Pesan aktivasi tidak boleh tampil dalam Bahasa Mandarin di antarmuka web.

Mesin aktivasi berasal dari py-xiaozhi dan mengirim pesan berbahasa Mandarin.
Pesan itu dipakai bersama jalur QML, jadi berkas aslinya dibiarkan apa adanya -
penerjemahan dilakukan di perbatasan antarmuka web (``src/ui/web/server.py``).

SELA hanya berbahasa Indonesia. Satu aksara Han yang lolos ke layar adalah
cacat, sekalipun hanya pada pesan status.
"""

import re

import pytest

from src.ui.web.server import _TERJEMAHAN_AKTIVASI, _pesan_aktivasi

# Seluruh pesan yang bisa dikirim ``src/activation/service.py``.
PESAN_MESIN = [
    "v1协议初始化完成",
    "初始化失败",
    "设备需要激活",
    "设备已激活",
    "已自动修复激活状态",
    "服务器取消授权，需要重新激活",
    "保持本地激活状态",
]

HAN = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")


@pytest.mark.parametrize("pesan", PESAN_MESIN)
def test_setiap_pesan_mesin_diterjemahkan(pesan):
    hasil = {"local_activated": True, "server_activated": True}
    keluaran = _pesan_aktivasi(pesan, hasil)
    assert keluaran, f"pesan {pesan!r} menjadi kosong"
    assert not HAN.search(keluaran), f"pesan {pesan!r} masih beraksara Han"


def test_pesan_terkenal_diterjemahkan_persis():
    assert _pesan_aktivasi("设备已激活", {}) == "Perangkat sudah aktif"
    assert _pesan_aktivasi("设备需要激活", {}) == "Perangkat perlu diaktifkan"


def test_pesan_belum_dikenal_dijawab_dari_penanda_status():
    """Pesan asing beraksara Han tetap tidak boleh bocor ke layar."""
    hasil = {"need_activation_ui": True}
    keluaran = _pesan_aktivasi("某个新提示", hasil)
    assert not HAN.search(keluaran)
    assert "diaktifkan" in keluaran.lower()


def test_pesan_tanpa_aksara_han_diteruskan():
    """Pesan yang sudah Indonesia (mis. dari server) tidak diubah."""
    assert _pesan_aktivasi("Perangkat siap dipakai", {}) == "Perangkat siap dipakai"


def test_pesan_kosong_tetap_kosong():
    assert _pesan_aktivasi("", {}) == ""
    assert _pesan_aktivasi(None, {}) == ""


def test_peta_terjemahan_tidak_menyisakan_aksara_han():
    for kunci, nilai in _TERJEMAHAN_AKTIVASI.items():
        assert HAN.search(kunci), f"{kunci!r} bukan pesan Mandarin"
        assert not HAN.search(nilai), f"terjemahan {kunci!r} masih beraksara Han"
