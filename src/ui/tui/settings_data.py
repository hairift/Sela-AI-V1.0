"""TUI 设置：配置字段定义与读写（接 ConfigManager + CONFIG_CHANGED）."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.logging import get_logger
from src.utils.config_manager import get_config

logger = get_logger()


@dataclass(frozen=True)
class SettingField:
    """一个可编辑配置项."""

    path: str
    label: str
    kind: str = "str"  # str | int | bool | choice
    choices: tuple[str, ...] = ()
    help: str = ""


# 第一期：系统 / 音频 / 摄像头 / 唤醒词
SETTING_SECTIONS: list[tuple[str, list[SettingField]]] = [
    (
        "Sistem",
        [
            SettingField(
                "SYSTEM_OPTIONS.NETWORK.OTA_VERSION_URL",
                "OTA URL",
                help="Alamat konfigurasi OTA / aktivasi",
            ),
            SettingField(
                "SYSTEM_OPTIONS.NETWORK.WEBSOCKET_URL",
                "WebSocket URL",
                help="Alamat layanan WebSocket",
            ),
            SettingField(
                "SYSTEM_OPTIONS.DEVICE_ID",
                "ID perangkat",
                help="Device-Id (biasanya MAC)",
            ),
            SettingField(
                "SYSTEM_OPTIONS.CLIENT_ID",
                "ID klien",
                help="Client-Id",
            ),
        ],
    ),
    (
        "Audio",
        [
            SettingField(
                "AUDIO_DEVICES.input_device_name",
                "Nama perangkat input",
                help="Cocokkan mikrofon berdasarkan nama (ID berubah saat hot-plug)",
            ),
            SettingField(
                "AUDIO_DEVICES.output_device_name",
                "Nama perangkat output",
                help="Cocokkan pengeras suara/headset berdasarkan nama",
            ),
            SettingField(
                "AUDIO_DEVICES.opus_output_sample_rate",
                "Laju sampel keluaran Opus",
                kind="choice",
                choices=("24000", "16000"),
                help="Resmi 24000 / pihak ketiga umumnya 16000",
            ),
            SettingField(
                "AUDIO_DEVICES.frame_duration",
                "Durasi bingkai (ms)",
                kind="choice",
                choices=("20", "40", "60"),
                help="20 latensi rendah / 60 CPU rendah",
            ),
        ],
    ),
    (
        "Kamera",
        [
            SettingField(
                "CAMERA.backend",
                "Backend pengambilan gambar",
                kind="choice",
                choices=("auto", "opencv", "picamera2"),
                help="auto: coba OpenCV dahulu, lalu CSI Pi",
            ),
            SettingField(
                "CAMERA.device",
                "Jalur perangkat",
                help="mis. /dev/video0; bila diisi, dipakai sebelum index",
            ),
            SettingField(
                "CAMERA.camera_index",
                "Index perangkat",
                kind="int",
                help="Index numerik OpenCV",
            ),
            SettingField(
                "CAMERA.frame_width",
                "Lebar",
                kind="int",
            ),
            SettingField(
                "CAMERA.frame_height",
                "Tinggi",
                kind="int",
            ),
        ],
    ),
    (
        "Kata bangun",
        [
            SettingField(
                "WAKE_WORD_OPTIONS.USE_WAKE_WORD",
                "Aktifkan kata bangun",
                kind="bool",
            ),
            SettingField(
                "WAKE_WORD_OPTIONS.WAKE_WORD",
                "Kata bangun",
                help="mis. SELA",
            ),
            SettingField(
                "WAKE_WORD_OPTIONS.WAKE_WORD_LANG",
                "Bahasa",
                kind="choice",
                choices=("zh", "en"),
            ),
        ],
    ),
]


def load_setting_values() -> dict[str, str]:
    """读取当前配置为字符串表（path -> 显示值）."""
    cfg = get_config()
    values: dict[str, str] = {}
    for _section, fields in SETTING_SECTIONS:
        for f in fields:
            raw = cfg.get_config(f.path, "")
            if f.kind == "bool":
                values[f.path] = "true" if bool(raw) else "false"
            elif raw is None:
                values[f.path] = ""
            else:
                values[f.path] = str(raw)
    return values


def parse_field_value(field: SettingField, text: str) -> Any:
    """把输入框字符串转成配置值."""
    s = (text or "").strip()
    if field.kind == "int":
        if s == "":
            return 0
        return int(s)
    if field.kind == "bool":
        return s.lower() in ("1", "true", "yes", "on", "Ya")
    if field.kind == "choice":
        if field.choices and s not in field.choices:
            # 仍写入用户值，由上层校验提示
            return s
        if field.path.endswith("opus_output_sample_rate") or field.path.endswith(
            "frame_duration"
        ):
            try:
                return int(s)
            except ValueError:
                return s
        return s
    return s


def save_settings(values: dict[str, str]) -> tuple[bool, str]:
    """批量写配置并落盘.

    Returns:
        (ok, message)
    """
    cfg = get_config()
    updates: dict[str, Any] = {}
    try:
        for _section, fields in SETTING_SECTIONS:
            for f in fields:
                if f.path not in values:
                    continue
                updates[f.path] = parse_field_value(f, values[f.path])
        if not updates:
            return True, "Tidak ada perubahan"
        ok = cfg.update_configs(updates)
        if not ok:
            return False, "Gagal menyimpan (kesalahan tulis disk)"
        logger.info(f"TUI menyimpan {len(updates)} item konfigurasi")
        return True, f"{len(updates)} item tersimpan"
    except Exception as e:
        logger.error(f"TUI gagal menyimpan konfigurasi: {e}", exc_info=True)
        return False, f"Gagal menyimpan: {e}"
