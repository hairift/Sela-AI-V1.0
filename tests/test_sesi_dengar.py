"""Uji sesi dengar antarmuka web: mikrofon tidak boleh terbuka sendiri.

Latar masalah nyata (laporan pengguna, v1.0.15):

1. Saat aplikasi baru dipasang / halaman disegarkan, tombol mikrofon sudah
   berada di posisi "merekam" padahal pengguna belum menekan apa pun.
2. Setelah berbicara lalu menekan tombol, hasil suaranya TIDAK dihasilkan;
   sedangkan menekan mikrofon secara manual berhasil.

Sebabnya satu: ``ConversationSession._on_audio_channel_opened`` menaikkan
status ke ``LISTENING`` setiap kanal audio dibuka. Itu bawaan kiblat dan benar
untuk mode gui/cli/gpio (yang memakai tombol fisik / pintasan papan tik).
Antarmuka web menyambung protokol saat aplikasi dibuka (``UI_AUTO_CONNECT``)
hanya supaya indikator status hijau - jadi sesi dengar "hantu" langsung terbuka.

Akibat berantainya: klik mikrofon pertama pengguna justru menutup sesi hantu
itu (bukan membuka rekaman baru), sehingga tidak ada audio yang terekam dan
jawaban tidak pernah muncul.

Uji di berkas ini mengunci perbaikan itu agar tidak kembali.
"""

import pytest


class _Viewport:
    def __init__(self):
        self.buttons = []
        self.auto_modes = []
        self._auto = False

    def set_button_text(self, text):
        self.buttons.append(text)

    def set_status(self, status, connected=True):
        pass

    def set_emotion(self, emotion):
        pass

    def set_chat_text(self, text):
        pass

    def set_auto_mode(self, auto_mode):
        self._auto = auto_mode
        self.auto_modes.append(auto_mode)

    def is_auto_mode(self):
        return self._auto

    async def start(self, mode="cli"):
        pass


class _Cmd:
    """PluginCommands palsu yang mencatat setiap perintah."""

    def __init__(self, log):
        self.log = log

    async def connect_protocol(self, keep_idle=False):
        self.log.append(("connect", keep_idle))
        return True

    async def start_listening(self, mode):
        self.log.append(("listen", mode))

    async def stop_listening(self):
        self.log.append("stop")

    async def abort_speaking(self, reason):
        self.log.append(("abort", reason))

    async def send_wake_word_detected(self, text):
        self.log.append(("detect", text))

    def request_shutdown(self):
        pass


class _Ctx:
    def __init__(self, *, listening=False, speaking=False, capture=False):
        self._listening = listening
        self._speaking = speaking
        self._capture = capture

    def is_listening(self):
        return self._listening

    def is_speaking(self):
        return self._speaking

    def should_capture_audio(self):
        return self._capture

    def get_config(self):
        class C:
            def get_config(self, k, d=None):
                return False  # AEC off

        return C()


def _buat(ctx=None, log=None):
    from src.plugins.ui_presenter import UiPresenter
    from src.plugins.ui_session import SessionActions

    log = log if log is not None else []
    ctx = ctx if ctx is not None else _Ctx()
    return SessionActions(ctx, _Cmd(log), UiPresenter(_Viewport())), log


# ---------------------------------------------------------------------------
# 1. Menyambung awal TIDAK membuka mikrofon
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auto_connect_meminta_keep_idle():
    """Sambungan awal saat aplikasi dibuka harus memakai keep_idle.

    Tanpa keep_idle, kanal audio yang terbuka menaikkan status ke LISTENING
    dan tombol mikrofon tampak merekam sendiri.
    """
    session, log = _buat()
    await session.auto_connect()

    assert log == [("connect", True)], (
        "auto_connect harus connect dengan keep_idle=True supaya tidak "
        f"masuk LISTENING; tercatat: {log}"
    )


@pytest.mark.asyncio
async def test_auto_connect_tidak_memulai_listen():
    """Tidak boleh ada perintah listen yang terbit dari sambungan awal."""
    session, log = _buat()
    await session.auto_connect()

    assert not any(
        isinstance(x, tuple) and x[0] == "listen" for x in log
    ), f"auto_connect tidak boleh membuka sesi dengar; tercatat: {log}"


# ---------------------------------------------------------------------------
# 2. Siap siaga (setiap pindah halaman) TIDAK membuka mikrofon
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_siap_siaga_tidak_membuka_mikrofon():
    """``siap_siaga`` hanya memulihkan sambungan.

    Sebelumnya ia memanggil ``_ensure_listen_session()``, sehingga sekadar
    berpindah halaman (atau memuat halaman pertama, karena App.jsx
    memanggilnya di useEffect mount) sudah menyalakan rekaman.
    """
    session, log = _buat()
    await session.siap_siaga()

    assert ("connect", True) in log, f"sambungan harus dipulihkan; log: {log}"
    assert not any(
        isinstance(x, tuple) and x[0] == "listen" for x in log
    ), f"siap_siaga tidak boleh membuka mikrofon; tercatat: {log}"


@pytest.mark.asyncio
async def test_siap_siaga_idempoten():
    """Boleh dipanggil berkali-kali tanpa efek samping."""
    session, log = _buat()
    for _ in range(3):
        await session.siap_siaga()

    assert not any(
        isinstance(x, tuple) and x[0] == "listen" for x in log
    ), f"panggilan berulang tidak boleh membuka mikrofon; log: {log}"


# ---------------------------------------------------------------------------
# 3. Alur tombol mikrofon: klik pertama rekam, klik kedua kirim
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_klik_mikrofon_pertama_selalu_membuka_sesi_baru():
    """Klik pertama membuka sesi rekam BARU - bukan menutup sesi hantu.

    Inilah inti bug "sudah bicara tapi tidak ada hasil": dulu klik pertama
    mengirim ``stop`` karena sesi hantu dari sambungan awal masih dianggap
    aktif, sehingga tidak ada audio yang terekam.
    """
    from src.constants.constants import ListeningMode

    session, log = _buat()
    await session.manual_toggle()

    assert session.manual_recording is True
    assert ("connect", True) in log
    assert ("listen", ListeningMode.MANUAL) in log, (
        f"klik pertama harus MEMBUKA sesi rekam; tercatat: {log}"
    )
    assert "stop" not in log, (
        f"klik pertama tidak boleh menutup apa pun; tercatat: {log}"
    )


@pytest.mark.asyncio
async def test_klik_mikrofon_kedua_mengirim_dan_menutup():
    """Klik kedua menutup rekaman supaya server memproses hasilnya."""
    from src.constants.constants import ListeningMode

    session, log = _buat()
    await session.manual_toggle()
    log.clear()
    await session.manual_toggle()

    assert session.manual_recording is False
    assert ("listen", ListeningMode.MANUAL) not in log, (
        "klik kedua tidak boleh membuka sesi dengar baru"
    )
    assert "stop" in log, (
        f"klik kedua harus menutup rekaman agar hasilnya dikirim; log: {log}"
    )


@pytest.mark.asyncio
async def test_klik_ketiga_membuka_lagi():
    """Siklus berikutnya dimulai bersih: rekam lagi, bukan mengirim ulang."""
    session, log = _buat()
    await session.manual_toggle()
    await session.manual_toggle()
    log.clear()
    await session.manual_toggle()

    assert session.manual_recording is True
    assert not any(
        isinstance(x, tuple) and x[0] == "listen" for x in log
    ) is False, f"klik ketiga harus membuka sesi rekam lagi; log: {log}"


@pytest.mark.asyncio
async def test_klik_mikrofon_saat_speaking_hanya_menghentikan():
    """Selagi SELA bicara, klik mikrofon menghentikannya dulu.

    Pengguna tidak boleh merekam di atas suara SELA sendiri, dan klik itu
    tidak boleh dihitung sebagai "mulai merekam".
    """
    ctx = _Ctx(speaking=True)
    session, log = _buat(ctx=ctx)
    await session.manual_toggle()

    assert session.manual_recording is False
    assert any(isinstance(x, tuple) and x[0] == "abort" for x in log), (
        f"klik saat bicara harus menghentikan suara SELA; log: {log}"
    )
    assert not any(
        isinstance(x, tuple) and x[0] == "listen" for x in log
    ), f"klik saat bicara tidak boleh membuka rekaman; log: {log}"


@pytest.mark.asyncio
async def test_mikrofon_tidak_terbuka_bila_sambungan_gagal():
    """Bila sambungan gagal, jangan tinggalkan UI dalam keadaan "merekam"."""
    from src.plugins.ui_presenter import UiPresenter
    from src.plugins.ui_session import SessionActions

    log = []

    class _CmdGagal(_Cmd):
        async def connect_protocol(self, keep_idle=False):
            self.log.append(("connect", keep_idle))
            return False

    session = SessionActions(_Ctx(), _CmdGagal(log), UiPresenter(_Viewport()))
    await session.manual_toggle()

    assert session.manual_recording is False, (
        "sambungan gagal tidak boleh meninggalkan UI dalam keadaan merekam"
    )
    assert not any(
        isinstance(x, tuple) and x[0] == "listen" for x in log
    ), f"tidak boleh membuka sesi dengar tanpa sambungan; log: {log}"


# ---------------------------------------------------------------------------
# 4. Status LISTENING semu tidak dipercaya saat mengirim teks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kirim_teks_membuka_ulang_sesi_bila_capture_belum_jalan():
    """Status listeNTING saja bukan bukti sesi dengar hidup.

    Protokol menaikkan status ke LISTENING begitu kanal audio terbuka. Bila
    keadaan semu itu dipercaya, ``detect`` dikirim tanpa sesi dan jawaban
    tidak pernah datang.
    """
    from src.constants.constants import ListeningMode

    ctx = _Ctx(listening=True, capture=False)
    session, log = _buat(ctx=ctx)
    await session.send_text("halo")

    assert ("listen", ListeningMode.MANUAL) in log, (
        "sesi dengar harus dibuka ulang bila capture belum jalan; "
        f"tercatat: {log}"
    )
    assert log[-1] == ("detect", "halo"), f"teks tetap harus terkirim; log: {log}"


@pytest.mark.asyncio
async def test_kirim_teks_tidak_membuka_ulang_bila_sesi_sudah_hidup():
    """Bila rekaman benar-benar jalan, cukup kirim - tanpa listen ulang."""
    ctx = _Ctx(listening=True, capture=True)
    session, log = _buat(ctx=ctx)
    await session.send_text("halo")

    assert log == [("detect", "halo")], f"tidak perlu listen ulang; log: {log}"


# ---------------------------------------------------------------------------
# 5. connect_protocol(keep_idle) di ConversationSession
# ---------------------------------------------------------------------------


def _buat_session(connect_ok=True):
    """ConversationSession dengan EventBus nyata dan protokol palsu.

    Protokol palsu menirukan kiblat: saat ``connect()`` berhasil, kanal audio
    terbuka sehingga ``AUDIO_CHANNEL_OPENED`` dipancarkan lewat EventBus -
    persis alur yang dulu membocorkan state LISTENING ke antarmuka web.
    """
    from src.bootstrap.session import ConversationSession
    from src.core.event_bus import EventBus, Events

    states = []
    bus = EventBus()

    class FakeProtocolManager:
        protocol = object()

        def is_audio_channel_opened(self):
            return False

        async def connect(self):
            if connect_ok:
                await bus.emit(Events.AUDIO_CHANNEL_OPENED)
            return connect_ok

    class FakeState:
        def set_keep_listening(self, v):
            pass

        async def set_device_state(self, s):
            states.append(s)

    class FakePlugins:
        async def notify_protocol_connected(self, p):
            pass

    session = ConversationSession(
        state=FakeState(),
        protocol=FakeProtocolManager(),  # type: ignore[arg-type]
        plugins=FakePlugins(),  # type: ignore[arg-type]
        event_bus=bus,
    )
    session.bind_events(bus)
    return session, states, bus, Events


@pytest.mark.asyncio
async def test_connect_protocol_keep_idle_menjaga_idle():
    """Sambungan dengan keep_idle tidak menaikkan state ke LISTENING."""
    from src.constants.constants import DeviceState

    session, states, _bus, _ev = _buat_session()
    await session.connect_protocol(keep_idle=True)

    assert states == [DeviceState.IDLE], (
        f"keep_idle harus menahan state di IDLE; tercatat: {states}"
    )


@pytest.mark.asyncio
async def test_connect_protocol_bawaan_naik_ke_listening():
    """Tanpa keep_idle, perilaku kiblat tetap: kanal terbuka -> LISTENING.

    Mode gui/cli/gpio memang mengandalkan perilaku ini, jadi perbaikannya
    tidak boleh menghapusnya.
    """
    from src.constants.constants import DeviceState

    session, states, _bus, _ev = _buat_session()
    await session.connect_protocol()

    assert states == [DeviceState.LISTENING], (
        f"tanpa keep_idle, kiblat menaikkan ke LISTENING; tercatat: {states}"
    )


@pytest.mark.asyncio
async def test_keep_idle_dibersihkan_bila_sambungan_gagal():
    """Sambungan gagal harus membersihkan penanda keep_idle.

    Kalau penanda tertinggal, percobaan berikutnya - yang justru ingin
    menyambung SAMBIL mendengar - ikut terpaksa IDLE, sehingga pengguna tidak
    bisa merekam sama sekali. Itu cacat baru yang lebih buruk dari aslinya.
    """
    session, states, bus, Events = _buat_session(connect_ok=False)
    await session.connect_protocol(keep_idle=True)

    assert states == [], f"sambungan gagal tidak mengubah state; tercatat: {states}"
    assert session._keep_idle_on_channel_open is False, (
        "penanda keep_idle harus dibersihkan setelah sambungan gagal"
    )

    # Percobaan berikutnya tanpa keep_idle harus kembali ke perilaku normal.
    async def _connect_berhasil():
        await bus.emit(Events.AUDIO_CHANNEL_OPENED)
        return True

    session.protocol.connect = _connect_berhasil  # type: ignore[method-assign]
    await session.connect_protocol()
    assert states[-1].name == "LISTENING", (
        f"setelah kegagalan, sambungan berikutnya harus bisa masuk LISTENING; "
        f"tercatat: {states}"
    )
