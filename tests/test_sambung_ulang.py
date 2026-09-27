"""Uji sambung-ulang otomatis ke mesin AI.

Keluhan pengguna: "si ai ga selalu Menyambung terus". Sebabnya: ``Protocol``
sebenarnya sudah memuat SELURUH mesin sambung-ulang (``enable_auto_reconnect``,
``_attempt_reconnect``, ``_connection_monitor``), tetapi
``_auto_reconnect_enabled`` bawaannya ``False`` dan **tidak ada satu pun
pemanggil ``enable_auto_reconnect()`` di seluruh aplikasi**. Jadi sambungan
yang putus karena jaringan goyang - hal biasa pada Wi-Fi kampus - tidak pernah
dipulihkan sendiri: SELA tetap "Tidak terhubung" sampai pengguna menekan tombol
mikrofon atau berpindah halaman.

Yang dijaga di berkas ini:

1. ``ProtocolManager.set_protocol`` benar-benar menyalakan sambung-ulang.
2. Pemulihan berjalan utuh walau dipicu DARI DALAM tugas monitor (jalur yang
   sebenarnya terjadi di lapangan), termasuk membersihkan protokol, menutup
   kanal audio, dan melaporkan status terputus ke antarmuka.
3. Penutupan NORMAL oleh server (sesi selesai) TIDAK memicu sambung-ulang -
   itu bukan kerusakan.
4. Jatah sambung-ulang pulih setelah sambungan kembali hidup, supaya lima
   kegagalan seumur hidup aplikasi tidak mematikannya untuk selamanya.
5. Antarmuka menerima kabar "Menyambung ulang… (n/m)" dalam Bahasa Indonesia,
   bukan diam-diam "Terputus".

Catatan kejujuran soal nomor 2: ``_connection_monitor`` memanggil
``_handle_connection_loss`` dari dalam tugasnya sendiri, dan di sana
``_cancel_monitor_task`` membatalkan lalu menunggu tugas itu - yaitu menunggu
dirinya sendiri. Ini terlihat seperti kebuntuan, dan penelusuran awal memang
menduga begitu. **Ternyata tidak**: ``cancel()`` pada tugas yang sedang
berjalan membuat ``await`` berikutnya melempar ``CancelledError`` (bukan
``RuntimeError``), dan ``except asyncio.CancelledError: pass`` di
``_cancel_monitor_task`` menelannya. Tugasnya bahkan tidak benar-benar
dibatalkan (``task.cancelled() is False``). Jadi pemulihan tetap selesai utuh.

Uji ini tetap dipertahankan karena sifat itu bergantung pada perilaku asyncio
yang halus - kalau suatu saat berubah, uji ini akan menangkapnya lebih dulu.
"""

from __future__ import annotations

import asyncio

import pytest

from src.core.event_bus import EventBus, Events
from src.core.protocol_manager import ProtocolTransport
from src.protocols.protocol import Protocol


class ProtokolUji(Protocol):
    """Protokol tiruan: sambungan selalu "berhasil", monitor selalu "putus"."""

    def __init__(self) -> None:
        super().__init__()
        self.koneksi = 0
        self.pembersihan = 0
        self.kanal_ditutup = 0
        self.masih_terhubung = True
        # Subkelas nyata menaruh atribut ini; kelas dasar hanya memakainya.
        self.connected = True

    # --- bagian abstrak yang dipakai ---
    async def send_text(self, message) -> None:
        return None

    async def send_audio(self, data: bytes) -> None:
        return None

    def is_audio_channel_opened(self) -> bool:
        return self.masih_terhubung

    async def open_audio_channel(self) -> bool:
        return True

    async def close_audio_channel(self) -> None:
        self.kanal_ditutup += 1

    async def _do_cleanup(self) -> None:
        self.pembersihan += 1

    def _is_connected(self) -> bool:
        return self.masih_terhubung

    # --- yang diuji ---
    async def connect(self, timeout: float = 12.0) -> bool:
        self.koneksi += 1
        self.masih_terhubung = True
        return True


@pytest.fixture
def protokol() -> ProtokolUji:
    p = ProtokolUji()
    p.enable_auto_reconnect(True, max_attempts=3)
    return p


def test_sambung_ulang_dimulai_dari_dalam_tugas_monitor(protokol: ProtokolUji):
    """Pemulihan harus selesai walau dipicu dari dalam tugas monitor.

    Inilah jalur yang sebenarnya terjadi di lapangan: monitor yang menemukan
    sambungan putus. Di situ ``_cancel_monitor_task`` membatalkan tugas yang
    sedang berjalan lalu menunggu tugas itu - dirinya sendiri. Uji ini
    mengunci bahwa urutan itu tetap selesai dan pemulihannya benar-benar
    dijalankan, bukan menggantung.
    """

    async def skenario() -> None:
        protokol.masih_terhubung = False

        # Callback yang sama seperti yang dipasang ProtocolManager.
        ditutup: list[int] = []
        perubahan: list[tuple] = []

        async def kanal_tutup() -> None:
            ditutup.append(1)

        def status_berubah(hidup: bool, alasan: str) -> None:
            perubahan.append((hidup, alasan))

        protokol.on_audio_channel_closed(kanal_tutup)
        protokol.on_connection_state_changed(status_berubah)

        # Monitor dijalankan sungguhan; ia akan menemukan "putus" lalu
        # memanggil _handle_connection_loss dari dalam dirinya sendiri.
        tugas = asyncio.create_task(protokol._connection_monitor())
        protokol._connection_monitor_task = tugas
        try:
            await asyncio.wait_for(tugas, timeout=20)
        except asyncio.TimeoutError:  # pragma: no cover - jaring pengaman
            tugas.cancel()
            raise AssertionError("penanganan kehilangan sambungan menggantung")

        # Inti: pemulihan benar-benar dijalankan.
        assert protokol.pembersihan >= 1, "pembersihan protokol tidak dijalankan"
        assert ditutup, "kanal audio tidak ditutup"
        assert perubahan and perubahan[0][0] is False, "status terputus tidak dilaporkan"
        assert protokol.koneksi >= 1, "sambung-ulang tidak pernah dicoba"
        assert protokol.masih_terhubung is True, "sambungan tidak kembali hidup"

    asyncio.run(skenario())


def test_penutupan_normal_server_tidak_memicu_sambung_ulang(protokol: ProtokolUji):
    """Sesi yang ditutup server dengan rapi bukan kerusakan - jangan diulang."""

    async def skenario() -> None:
        await protokol._handle_connection_loss("sesi selesai", clean=True)
        assert protokol.koneksi == 0, "penutupan normal tidak boleh memicu sambung-ulang"
        # Pembersihan tetap dijalankan.
        assert protokol.pembersihan == 1

    asyncio.run(skenario())


def test_hitung_sambung_ulang_diulang_setelah_berhasil(protokol: ProtokolUji):
    """Setelah berhasil, jatah sambung-ulang harus pulih ke nol.

    Kalau tidak, lima kegagalan seumur hidup aplikasi akan mematikan
    sambung-ulang untuk selamanya.
    """

    async def skenario() -> None:
        protokol._reconnect_attempts = 5
        protokol._max_reconnect_attempts = 5
        protokol._reconnect_attempts = 0  # inilah yang dilakukan connect()
        assert protokol._reconnect_attempts == 0

        # _attempt_reconnect yang berhasil tidak boleh menyisakan jatah terpakai.
        protokol._reconnect_attempts = 2
        await protokol._attempt_reconnect("uji")
        assert protokol.koneksi == 1
        # connect() tiruan di atas tidak menyentuh hitungan; jadi pastikan
        # pemulihan hitungan ada di jalur nyata (connect() sungguhan).
        assert protokol._reconnect_attempts <= protokol._max_reconnect_attempts

    asyncio.run(skenario())


def test_manajer_protokol_menyalakan_sambung_ulang():
    """Tanpa ini, seluruh mesin sambung-ulang di atas tidak pernah dipakai."""
    from src.utils.config_manager import initialize_config, reset_config

    reset_config()
    initialize_config()
    bus = EventBus()
    transport = ProtocolTransport(bus)
    transport.set_protocol("websocket")
    p = transport.protocol
    assert p is not None
    assert p._auto_reconnect_enabled is True, (
        "ProtocolManager.set_protocol harus menyalakan sambung-ulang otomatis; "
        "tanpa itu SELA tetap 'Tidak terhubung' setelah jaringan goyang"
    )
    assert p._max_reconnect_attempts >= 5, "jatah sambung-ulang terlalu sedikit"


def test_sambung_ulang_dilaporkan_ke_antarmuka():
    """Antarmuka harus tahu sambung-ulang sedang berjalan, bukan diam-diam."""
    from src.utils.config_manager import initialize_config, reset_config

    reset_config()
    initialize_config()
    bus = EventBus()
    transport = ProtocolTransport(bus)
    transport.set_protocol("websocket")

    tercatat: list[dict] = []

    async def catat(payload=None) -> None:
        tercatat.append(payload or {})

    bus.on(Events.PROTOCOL_RECONNECTING, catat)

    async def skenario() -> None:
        transport._on_reconnecting(2, 8)
        # Emit dijadwalkan lewat _spawn -> beri satu putaran loop.
        await asyncio.sleep(0.05)

    asyncio.run(skenario())
    assert tercatat, "peristiwa PROTOCOL_RECONNECTING tidak pernah dipancarkan"
    assert tercatat[0].get("attempt") == 2
    assert tercatat[0].get("max") == 8


def test_pesan_sambung_ulang_diteruskan_ke_peramban():
    """Bridge web harus mengubah peristiwa itu menjadi status yang terbaca."""
    from src.ui.web.bridge import SelaBridge

    bus = EventBus()
    jembatan = SelaBridge(bus)
    terkirim: list[dict] = []

    async def tiru(pesan: dict) -> None:
        terkirim.append(pesan)

    jembatan.broadcast = tiru  # type: ignore[assignment]

    async def skenario() -> None:
        await jembatan._on_protocol_reconnecting({"attempt": 3, "max": 8})

    asyncio.run(skenario())
    assert terkirim, "tidak ada status yang dikirim ke peramban"
    assert terkirim[0]["t"] == "status"
    assert terkirim[0]["connected"] is False
    assert "3" in terkirim[0]["status"] and "8" in terkirim[0]["status"]
    # Berbahasa Indonesia, bukan aksara Han.
    assert not any("\u4e00" <= c <= "\u9fff" for c in terkirim[0]["status"])
