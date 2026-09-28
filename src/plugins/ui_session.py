"""界面上的按键、发文本、模式切换等，转成协议调用."""

from typing import TYPE_CHECKING

from src.constants.constants import AbortReason, DeviceState, ListeningMode
from src.core.event_bus import Events
from src.logging import get_logger

if TYPE_CHECKING:
    from src.bootstrap.protocols import PluginCommands, PluginContext
    from src.plugins.ui_presenter import UiPresenter

logger = get_logger()


class SessionActions:
    """会话相关操作."""

    def __init__(
        self,
        ctx: "PluginContext",
        cmd: "PluginCommands",
        presenter: "UiPresenter",
    ) -> None:
        self._ctx = ctx
        self._cmd = cmd
        self._ui = presenter
        self._manual_recording = False
        self._auto_mode = False
        # 自动模式下是否已经开始对话（按钮显示「停止对话」）
        self._auto_session_active = False

    @property
    def auto_mode(self) -> bool:
        return self._auto_mode

    @property
    def auto_session_active(self) -> bool:
        return self._auto_session_active

    @property
    def manual_recording(self) -> bool:
        return self._manual_recording

    def subscribe(self, bus) -> None:
        bus.on(Events.UI_BUTTON_PRESS, self.press)
        bus.on(Events.UI_BUTTON_RELEASE, self.release)
        bus.on(Events.UI_MANUAL_TOGGLE, self.manual_toggle)
        bus.on(Events.UI_AUTO_TOGGLE, self.auto_toggle)
        bus.on(Events.UI_AUTO_START, self.auto_session_toggle)
        bus.on(Events.UI_ABORT_REQUEST, self.abort)
        bus.on(Events.UI_SEND_TEXT, self.send_text_from_event)
        bus.on(Events.UI_QUIT_REQUEST, self.request_shutdown)
        bus.on(Events.UI_AUTO_CONNECT, self.auto_connect)
        bus.on(Events.UI_READY_REQUEST, self.siap_siaga)
        logger.info("SessionActions 已订阅 UI 用户操作事件")

    async def auto_connect(self, _data=None) -> None:
        """Sambungkan protokol TANPA membuka mikrofon.

        Dipakai antarmuka web saat aplikasi dibuka, supaya indikator status
        langsung menunjukkan "Terhubung" dan obrolan teks siap dipakai. Mikrofon
        tetap baru dibuka ketika pengguna menekan tombol atau memanggil kata
        bangun, sehingga perilaku asli py-xiaozhi tidak berubah.

        ``connect_protocol(keep_idle=True)`` penting di sini. Bawaan kiblat
        menaikkan sesi ke LISTENING begitu kanal audio terbuka; bila itu
        dibiarkan, aplikasi yang baru dibuka (atau halaman yang baru disegarkan)
        langsung tampak sedang merekam padahal pengguna belum menekan apa pun -
        dan klik mikrofon pertamanya justru menutup sesi hantu itu sehingga
        hasil suaranya tidak pernah terkirim.
        """
        try:
            if self._ctx.is_listening() or self._ctx.is_speaking():
                return
            ok = await self._cmd.connect_protocol(keep_idle=True)
            if ok:
                logger.info("Sambungan awal ke mesin AI berhasil (mikrofon tetap tertutup)")
            else:
                logger.warning(
                    "Sambungan awal ke mesin AI belum berhasil; "
                    "akan dicoba lagi saat pengguna mulai berbicara"
                )
        except Exception as e:
            logger.warning(f"Sambungan awal gagal: {e}")

    def on_device_state_changed(self, state) -> None:
        # 手动录音中途被拉出 listening，复位按钮
        if state != DeviceState.LISTENING and self._manual_recording:
            self._manual_recording = False
            if not self._auto_mode:
                self._ui.set_button_text("Tahan lalu bicara")

        if self._auto_mode and state == DeviceState.IDLE and self._auto_session_active:
            self._auto_session_active = False
            self._ui.set_button_text("Mulai bicara")
        elif self._auto_mode and state in (DeviceState.LISTENING, DeviceState.SPEAKING):
            if not self._auto_session_active:
                self._auto_session_active = True
            self._ui.set_button_text("Hentikan")

    async def request_shutdown(self, _data=None) -> None:
        self._cmd.request_shutdown()

    def _listen_mode(self) -> ListeningMode:
        if not self._auto_mode:
            return ListeningMode.MANUAL
        aec = self._ctx.get_config().get_config("AEC_OPTIONS.ENABLED", True)
        return ListeningMode.REALTIME if aec else ListeningMode.AUTO_STOP

    async def _ensure_listen_session(self) -> bool:
        """Pastikan ada sesi dengar yang benar-benar hidup sebelum kirim teks.

        Server sering membuang ``detect`` yang dikirim selagi idle, jadi sesi
        dengar dibuka lebih dulu ("先听再发"). Yang perlu dijaga: status
        LISTENING saja BUKAN bukti sesi itu ada. Bawaan kiblat menaikkan status
        ke LISTENING setiap kanal audio dibuka (``_on_audio_channel_opened``),
        termasuk saat aplikasi web baru dibuka dan belum ada sesi dengar sama
        sekali. Bila keadaan semu itu dipercaya, ``detect`` dikirim tanpa sesi
        dan jawabannya tidak pernah datang. Karena itu sesi selalu dibuka ulang
        bila perekaman belum benar-benar berjalan.
        """
        if self._ctx.is_listening() and self._ctx.should_capture_audio():
            return True
        if not await self._cmd.connect_protocol(keep_idle=True):
            logger.warning("无法建立协议连接，取消会话操作")
            return False
        mode = self._listen_mode()
        await self._cmd.start_listening(mode)
        if self._auto_mode:
            self._auto_session_active = True
            self._ui.set_button_text("Hentikan")
        logger.debug(f"已开启 listen 会话: mode={mode}")
        return True

    async def send_text_from_event(self, data) -> None:
        if hasattr(data, "text"):
            text = data.text
        elif isinstance(data, dict):
            text = data.get("text", "")
        elif isinstance(data, str):
            text = data
        else:
            logger.warning(f"无效的发送文本数据: {type(data)}")
            return
        await self.send_text(text)

    async def send_text(self, text: str) -> None:
        text = (text or "").strip()
        if not text:
            return

        logger.info(f"发送文本: {text[:40]}{'...' if len(text) > 40 else ''}")

        if self._ctx.is_speaking():
            await self._cmd.abort_speaking(AbortReason.USER_INTERRUPTION)

        if not await self._ensure_listen_session():
            return

        # Panjang teks sudah dibatasi di antarmuka (lihat MAKS_PANJANG_TEKS di
        # webui), sehingga jalur listen/detect milik server selalu menerima
        # teks yang bisa dijawab. Pertanyaan sepanjang apa pun tetap aman lewat
        # jalur suara karena tidak melewati batas ini.
        await self._cmd.send_wake_word_detected(text)

    async def press(self, _data=None) -> None:
        await self._cmd.connect_protocol()
        await self._cmd.start_listening(ListeningMode.MANUAL)

    async def release(self, _data=None) -> None:
        await self._cmd.stop_listening()

    async def manual_toggle(self, _data=None) -> None:
        """Tombol mikrofon utama: klik pertama mulai merekam, klik kedua kirim.

        Ini SATU-SATUNYA jalur yang boleh membuka mikrofon di antarmuka web.
        Sebelumnya aplikasi bisa sudah berada di LISTENING saat halaman dibuka
        (lihat ``auto_connect``), sehingga klik pertama pengguna malah menutup
        sesi hantu itu dan suaranya tidak pernah terkirim - gejalanya: "sudah
        bicara, tapi tidak ada hasil". Sekarang setiap klik pertama selalu
        membuka sesi rekam yang BARU dan bersih, jadi hasilnya selalu terkirim.
        """
        if self._ctx.is_speaking():
            # Selagi SELA bicara, klik mikrofon berarti menghentikannya dulu
            # supaya pengguna tidak berbicara di atas suara SELA.
            await self._cmd.abort_speaking(AbortReason.USER_INTERRUPTION)
            self._manual_recording = False
            self._ui.set_button_text("Tahan lalu bicara")
            return

        if not self._manual_recording:
            self._manual_recording = True
            logger.debug("手动模式：开始录音")
            self._ui.set_button_text("Kirim")
            if not await self._cmd.connect_protocol(keep_idle=True):
                self._manual_recording = False
                self._ui.set_button_text("Tahan lalu bicara")
                logger.warning("Mikrofon tidak bisa dibuka: sambungan gagal")
                return
            await self._cmd.start_listening(ListeningMode.MANUAL)
        else:
            self._manual_recording = False
            logger.debug("手动模式：停止录音并发送")
            self._ui.set_button_text("Tahan lalu bicara")
            # Selalu tutup sesi rekam. Bila sesi itu ternyata sudah tidak ada
            # (mis. server memutusnya sendiri), perintah ini tidak berbahaya -
            # dan yang penting jawaban atas rekaman tadi tetap dihasilkan.
            await self._cmd.stop_listening()

    async def auto_toggle(self, _data=None) -> None:
        # 只切自动/手动，不自动开始听
        self._auto_mode = not self._auto_mode
        if not self._auto_mode:
            self._auto_session_active = False
        if self._auto_mode and self._manual_recording:
            self._manual_recording = False
        self._ui.set_auto_mode(self._auto_mode)
        logger.debug(f"模式切换: {'自动' if self._auto_mode else '手动'}")

    async def siap_siaga(self, _data=None) -> None:
        """Pastikan SAMBUNGAN siap - tanpa membuka mikrofon.

        Dipanggil antarmuka setiap kali pengguna berpindah halaman (mis. keluar
        dari Pengaturan) dan sekali saat halaman pertama dimuat. Sebelumnya,
        keluar dari Pengaturan kadang meninggalkan sambungan dalam keadaan
        setengah siap sehingga SELA tidak menanggapi sampai aplikasi dijalankan
        ulang; handler ini menambalnya.

        Sejak v1.0.15 mikrofon TIDAK dibuka di sini. Dulu ``siap_siaga``
        memanggil ``_ensure_listen_session()``, sehingga sekadar membuka atau
        menyegarkan halaman sudah menyalakan rekaman - pengguna melihat tombol
        mikrofon "merekam" tanpa pernah menekannya. Membuka mikrofon sekarang
        hanya terjadi lewat ``manual_toggle`` (klik tombol mikrofon) atau saat
        pengguna mengirim teks.
        """
        try:
            if self._ctx.is_speaking():
                # Sedang menjawab; jangan diganggu.
                return
            # keep_idle: sambungan pulih, tetapi mikrofon tetap tertutup sampai
            # pengguna benar-benar memintanya.
            await self._cmd.connect_protocol(keep_idle=True)
            logger.debug("Siap siaga: sambungan dipastikan aktif (mikrofon tetap tertutup)")
        except Exception as e:
            logger.warning(f"Siap siaga gagal: {e}")

    async def auto_session_toggle(self, _data=None) -> None:
        # 主按钮：开始对话 / 停止对话
        if self._auto_session_active or self._ctx.is_listening() or self._ctx.is_speaking():
            await self._stop_auto_session()
            return

        if not await self._ensure_listen_session():
            return
        logger.debug("自动模式：开始对话")

    async def _stop_auto_session(self) -> None:
        # 先 stop 清 keep_listening，再 abort，免得打断后又被续听拉回去
        try:
            if self._ctx.is_speaking():
                await self._cmd.stop_listening()
                await self._cmd.abort_speaking(AbortReason.USER_INTERRUPTION)
            else:
                await self._cmd.stop_listening()
        finally:
            self._auto_session_active = False
            self._ui.set_button_text("Mulai bicara")
            logger.debug("自动模式：停止对话")

    async def abort(self, _data=None) -> None:
        await self._cmd.abort_speaking(AbortReason.USER_INTERRUPTION)
