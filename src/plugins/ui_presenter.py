"""把状态/协议消息画到界面上."""

from typing import TYPE_CHECKING, Optional

from src.constants.constants import DeviceState
from src.logging import get_logger

if TYPE_CHECKING:
    from src.ui.shared.viewport import ViewPort

logger = get_logger()


class UiPresenter:
    """写界面：对话、音乐、状态、表情、按钮等."""

    STATE_TEXT_MAP = {
        DeviceState.IDLE: "Siap",
        DeviceState.LISTENING: "Mendengarkan...",
        DeviceState.SPEAKING: "Berbicara...",
    }

    MUSIC_STATE_TEXT = {
        "playing": "Sedang diputar: {song}",
        "paused": "Dijeda: {song}",
        "stopped": "Dihentikan: {song}",
        "completed": "Selesai diputar: {song}",
    }

    def __init__(self, viewport: Optional["ViewPort"] = None) -> None:
        self._vp = viewport

    def bind(self, viewport: Optional["ViewPort"]) -> None:
        self._vp = viewport

    @property
    def viewport(self) -> Optional["ViewPort"]:
        return self._vp

    def set_chat_text(self, text: str) -> None:
        if self._vp:
            self._vp.set_chat_text(text)

    def set_music_line(self, text: str) -> None:
        if self._vp:
            self._vp.set_music_line(text)

    def set_emotion(self, emotion: str) -> None:
        if self._vp:
            self._vp.set_emotion(emotion)

    def set_status(self, status: str, connected: bool = True) -> None:
        if self._vp:
            self._vp.set_status(status, connected)

    def set_button_text(self, text: str) -> None:
        if not self._vp:
            return
        setter = getattr(self._vp, "set_button_text", None)
        if callable(setter):
            setter(text)

    def set_auto_mode(self, auto_mode: bool) -> None:
        if self._vp:
            self._vp.set_auto_mode(auto_mode)

    def show_device_state(self, state) -> None:
        if status_text := self.STATE_TEXT_MAP.get(state):
            self.set_emotion("neutral")
            self.set_status(status_text, connected=True)

    def show_network_error(self) -> None:
        self.set_status("Tidak terhubung", connected=False)

    def show_music_state(self, data) -> None:
        try:
            from src.mcp.tools.music.events import MusicStateData

            if not isinstance(data, MusicStateData):
                logger.warning(f"Data status musik tidak sah: {type(data)}")
                return

            template = self.MUSIC_STATE_TEXT.get(data.state)
            if not template:
                return
            text = template.format(song=data.song)
            self.set_music_line(text)
            logger.debug(f"UI memperbarui status musik: {data.state}")
        except Exception as e:
            logger.error(f"Gagal menangani perubahan status musik: {e}", exc_info=True)

    def show_music_lyrics(self, data) -> None:
        try:
            from src.mcp.tools.music.events import MusicLyricsData

            if not isinstance(data, MusicLyricsData):
                logger.warning(f"Data lirik tidak sah: {type(data)}")
                return
            self.set_music_line(data.text)
        except Exception as e:
            logger.error(f"Gagal menangani pembaruan lirik: {e}", exc_info=True)

    def show_protocol_message(self, message) -> None:
        if not isinstance(message, dict):
            return
        msg_type = message.get("type")
        if msg_type in ("tts", "stt"):
            if text := message.get("text"):
                self.set_chat_text(text)
        elif msg_type == "llm":
            if emotion := message.get("emotion"):
                self.set_emotion(emotion)
        elif msg_type == "alert":
            # Server mengirim peringatan (mis. pesan terlalu panjang, sesi belum
            # siap, atau kesalahan lain). Sebelumnya pesan ini diabaikan
            # sehingga pengguna hanya melihat "tidak ada jawaban" tanpa sebab.
            pesan = (
                message.get("message")
                or message.get("text")
                or message.get("reason")
                or "Peringatan dari mesin AI"
            )
            logger.warning(f"Peringatan mesin AI: {pesan} | {message}")
            ramah = _pesan_server_ke_indonesia(str(pesan))
            try:
                self.set_status(ramah, connected=False)
            except Exception:
                pass
            try:
                self.set_chat_text(f"⚠ {ramah}")
            except Exception:
                pass


# Terjemahan pesan galat server AI yang paling sering muncul, supaya pengguna
# mendapat penjelasan yang bisa ditindaklanjuti alih-alih teks Inggris mentah.
_PESAN_SERVER = (
    (
        "detect is only for wake words",
        "Pesan terlalu panjang untuk mesin AI. Coba tulis lebih singkat, "
        "atau gunakan tombol mikrofon untuk berbicara.",
    ),
    (
        "duplicate tool names",
        "Terjadi bentrok nama alat internal. Silakan jalankan ulang aplikasi.",
    ),
    (
        "session",
        "Sesi dengan mesin AI terputus. Coba kirim ulang pesan Anda.",
    ),
)


def _pesan_server_ke_indonesia(pesan: str) -> str:
    """Ubah pesan galat server menjadi kalimat Indonesia yang jelas."""
    teks = pesan.lower()
    for pola, terjemahan in _PESAN_SERVER:
        if pola in teks:
            return terjemahan
    return pesan
